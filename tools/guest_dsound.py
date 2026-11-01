"""DirectSound 8 Python simulation model and guest memory interface.

Provides Python emulation and memory binding for DirectSoundCreate,
IDirectSound8, IDirectSoundBuffer8 COM vtables, circular streaming buffer math,
and AudioRing float32 PCM conversion, mirroring runtime/dsound.c and runtime/dsound.h.
"""

import struct
from typing import Optional, Tuple, List

# Protocol Addresses matching runtime/dsound.h
DSOUND_DIRECTSOUNDCREATE_IAT_VA = 0x00967038

DSOUND_GUEST_DSOUND_ADDR        = 0x0200B000
DSOUND_GUEST_DSOUND_VTBL        = 0x0200B100

DSOUND_GUEST_PRIMARY_BUF_ADDR   = 0x0200B200
DSOUND_GUEST_PRIMARY_BUF_VTBL   = 0x0200B300

DSOUND_GUEST_SECONDARY_BUF_ADDR = 0x0200B400
DSOUND_GUEST_SECONDARY_BUF_VTBL = 0x0200B500

DSOUND_GUEST_PCM_DATA_ADDR      = 0x02010000
DSOUND_GUEST_PCM_DATA_SIZE      = 131072  # 128 KiB circular buffer

DSOUND_GUEST_AUDIO_RING_ADDR    = 0x02030000
DSOUND_GUEST_AUDIO_RING_SIZE    = (64 * 4 + 16384 * 2 * 4)  # 131328 bytes

DSOUND_DSOUND_METHOD_BASE_VA    = 0x00962600
DSOUND_BUFFER_METHOD_BASE_VA    = 0x00962800

# AudioRing Header Constants & Offsets
AUDIO_RING_MAGIC                = 0x4E415544  # 'NAUD'
AUDIO_RING_VERSION              = 1
AUDIO_RING_FRAMES               = 16384
AUDIO_RATE                      = 44100

AR_MAGIC                        = 0
AR_VERSION                      = 1
AR_FRAMES                       = 2
AR_RATE                         = 3
AR_W                            = 4
AR_R                            = 5
AR_TARGET                       = 6

# DirectSound Constants
DS_OK                           = 0x00000000
DSERR_INVALIDPARAM              = 0x80070057
DSERR_UNSUPPORTED               = 0x80004001

DSBCAPS_PRIMARYBUFFER           = 0x00000001
DSBCAPS_STATIC                  = 0x00000002
DSBCAPS_CTRLVOLUME              = 0x00000080
DSBCAPS_GLOBALFOCUS             = 0x00008000
DSBCAPS_GETCURRENTPOSITION2     = 0x00010000

DSBPLAY_LOOPING                 = 0x00000001
DSBSTATUS_PLAYING               = 0x00000001
DSBSTATUS_LOOPING               = 0x00000002

DSBLOCK_ENTIREBUFFER            = 0x00000002


class GuestDSound:
    """Emulates DirectSound runtime COM objects and circular buffer streaming."""

    def __init__(self, memory: bytearray):
        self.mem = memory
        self.sample_rate = AUDIO_RATE
        self.channels = 2
        self.bits_per_sample = 16
        self.secondary_buffer_bytes = DSOUND_GUEST_PCM_DATA_SIZE
        self.play_cursor_bytes = 0
        self.volume = 0
        self.pan = 0
        self.is_playing = False
        self.is_looping = False
        self.frames_written_total = 0
        self.init()

    def init(self) -> None:
        """Initializes COM vtables, IAT slots, and shared AudioRing header."""
        # 1. Bind DirectSoundCreate IAT
        struct.pack_into('<I', self.mem, DSOUND_DIRECTSOUNDCREATE_IAT_VA, DSOUND_DIRECTSOUNDCREATE_IAT_VA)

        # 2. DirectSound COM Object and VTable (11 methods)
        struct.pack_into('<I', self.mem, DSOUND_GUEST_DSOUND_ADDR, DSOUND_GUEST_DSOUND_VTBL)
        for i in range(11):
            struct.pack_into('<I', self.mem, DSOUND_GUEST_DSOUND_VTBL + i * 4, DSOUND_DSOUND_METHOD_BASE_VA + i * 4)

        # 3. Primary Buffer COM Object and VTable (21 methods)
        struct.pack_into('<I', self.mem, DSOUND_GUEST_PRIMARY_BUF_ADDR, DSOUND_GUEST_PRIMARY_BUF_VTBL)
        for i in range(21):
            struct.pack_into('<I', self.mem, DSOUND_GUEST_PRIMARY_BUF_VTBL + i * 4, DSOUND_BUFFER_METHOD_BASE_VA + i * 4)

        # 4. Secondary Buffer COM Object
        struct.pack_into('<I', self.mem, DSOUND_GUEST_SECONDARY_BUF_ADDR, DSOUND_GUEST_PRIMARY_BUF_VTBL)

        # 5. Shared AudioRing Header
        base = DSOUND_GUEST_AUDIO_RING_ADDR
        # Clear header (64 * 4 = 256 bytes)
        self.mem[base:base + 256] = b'\x00' * 256
        struct.pack_into('<I', self.mem, base + AR_MAGIC * 4, AUDIO_RING_MAGIC)
        struct.pack_into('<I', self.mem, base + AR_VERSION * 4, AUDIO_RING_VERSION)
        struct.pack_into('<I', self.mem, base + AR_FRAMES * 4, AUDIO_RING_FRAMES)
        struct.pack_into('<I', self.mem, base + AR_RATE * 4, AUDIO_RATE)
        struct.pack_into('<I', self.mem, base + AR_W * 4, 0)
        struct.pack_into('<I', self.mem, base + AR_R * 4, 0)
        struct.pack_into('<I', self.mem, base + AR_TARGET * 4, 2048)

    def direct_sound_create(self) -> int:
        """Returns the guest pointer to IDirectSound8."""
        return DSOUND_GUEST_DSOUND_ADDR

    def create_sound_buffer(self, flags: int, buffer_bytes: int = 0) -> int:
        """Emulates IDirectSound8::CreateSoundBuffer."""
        if flags & DSBCAPS_PRIMARYBUFFER:
            return DSOUND_GUEST_PRIMARY_BUF_ADDR
        else:
            if buffer_bytes > 0:
                self.secondary_buffer_bytes = buffer_bytes
            return DSOUND_GUEST_SECONDARY_BUF_ADDR

    def set_format(self, channels: int, sample_rate: int, bits_per_sample: int) -> int:
        """Emulates IDirectSoundBuffer::SetFormat."""
        self.channels = channels
        self.sample_rate = sample_rate
        self.bits_per_sample = bits_per_sample
        return DS_OK

    def lock(self, offset: int, want_bytes: int, flags: int = 0) -> Tuple[int, int, int, int]:
        """Emulates IDirectSoundBuffer::Lock with circular wrapping into two regions."""
        buf_sz = self.secondary_buffer_bytes or DSOUND_GUEST_PCM_DATA_SIZE
        if flags & DSBLOCK_ENTIREBUFFER:
            offset = 0
            want_bytes = buf_sz

        offset = offset % buf_sz
        if want_bytes == 0 or want_bytes > buf_sz:
            want_bytes = buf_sz

        avail = buf_sz - offset
        b1 = min(want_bytes, avail)
        b2 = want_bytes - b1

        ptr1 = DSOUND_GUEST_PCM_DATA_ADDR + offset
        ptr2 = DSOUND_GUEST_PCM_DATA_ADDR if b2 > 0 else 0
        return (ptr1, b1, ptr2, b2)

    def unlock(self, ptr1: int, bytes1: int, ptr2: int = 0, bytes2: int = 0) -> int:
        """Emulates IDirectSoundBuffer::Unlock, converting PCM and pushing to AudioRing."""
        if ptr1 and bytes1:
            self._push_pcm_chunk(ptr1, bytes1)
        if ptr2 and bytes2:
            self._push_pcm_chunk(ptr2, bytes2)
        return DS_OK

    def _push_pcm_chunk(self, guest_ptr: int, byte_count: int) -> None:
        """Converts 16-bit stereo PCM chunk to float32 and updates AudioRing."""
        if byte_count < 4:
            return

        frames_to_push = byte_count // 4
        base = DSOUND_GUEST_AUDIO_RING_ADDR
        pcm_base = base + 256  # 64 uint32 header = 256 bytes

        w = struct.unpack_from('<I', self.mem, base + AR_W * 4)[0]

        for i in range(frames_to_push):
            src_off = guest_ptr + i * 4
            s16_l, s16_r = struct.unpack_from('<hh', self.mem, src_off)
            f_left = s16_l * (1.0 / 32768.0)
            f_right = s16_r * (1.0 / 32768.0)

            idx = (w + i) & (AUDIO_RING_FRAMES - 1)
            struct.pack_into('<ff', self.mem, pcm_base + idx * 8, f_left, f_right)

        new_w = (w + frames_to_push) & 0xFFFFFFFF
        struct.pack_into('<I', self.mem, base + AR_W * 4, new_w)
        self.frames_written_total += frames_to_push

        buf_sz = self.secondary_buffer_bytes or DSOUND_GUEST_PCM_DATA_SIZE
        self.play_cursor_bytes = (self.play_cursor_bytes + byte_count) % buf_sz

    def get_current_position(self) -> Tuple[int, int]:
        """Emulates IDirectSoundBuffer::GetCurrentPosition."""
        buf_sz = self.secondary_buffer_bytes or DSOUND_GUEST_PCM_DATA_SIZE
        play_pos = self.play_cursor_bytes % buf_sz
        write_pos = (play_pos + 2048) % buf_sz
        return (play_pos, write_pos)

    def play(self, looping: bool = True) -> int:
        """Emulates IDirectSoundBuffer::Play."""
        self.is_playing = True
        self.is_looping = looping
        return DS_OK

    def stop(self) -> int:
        """Emulates IDirectSoundBuffer::Stop."""
        self.is_playing = False
        return DS_OK

    def get_status(self) -> int:
        """Emulates IDirectSoundBuffer::GetStatus."""
        status = 0
        if self.is_playing:
            status |= DSBSTATUS_PLAYING
            if self.is_looping:
                status |= DSBSTATUS_LOOPING
        return status

    def get_audio_ring_header(self) -> dict:
        """Reads and unpacks the AudioRing header fields."""
        base = DSOUND_GUEST_AUDIO_RING_ADDR
        fields = ["magic", "version", "frames", "rate", "w", "r", "target"]
        vals = struct.unpack_from('<7I', self.mem, base)
        return dict(zip(fields, vals))

