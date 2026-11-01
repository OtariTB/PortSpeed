"""Automated tests for DirectSound 8 COM interfaces, vtables, and AudioRing streaming pipeline.

Verifies:
1. COM object vtables and IAT binding in linear guest memory.
2. Dual-buffer architecture (Primary buffer vs Looping Secondary streaming buffer).
3. Circular Lock() splitting across ring boundary into two discrete regions.
4. Unlock() PCM conversion (16-bit signed integer to float32) and AudioRing write pointer progression.
5. GetCurrentPosition() smooth play cursor progression and write cursor lead.
6. Play(), Stop(), and GetStatus() lifecycle state transitions.
"""

import struct
import unittest
from tools.guest_dsound import (
    GuestDSound,
    DSOUND_DIRECTSOUNDCREATE_IAT_VA,
    DSOUND_GUEST_DSOUND_ADDR, DSOUND_GUEST_DSOUND_VTBL,
    DSOUND_GUEST_PRIMARY_BUF_ADDR, DSOUND_GUEST_PRIMARY_BUF_VTBL,
    DSOUND_GUEST_SECONDARY_BUF_ADDR,
    DSOUND_GUEST_PCM_DATA_ADDR, DSOUND_GUEST_PCM_DATA_SIZE,
    DSOUND_GUEST_AUDIO_RING_ADDR,
    AUDIO_RING_MAGIC, AUDIO_RING_VERSION, AUDIO_RING_FRAMES, AUDIO_RATE,
    DS_OK, DSBCAPS_PRIMARYBUFFER, DSBCAPS_GLOBALFOCUS, DSBCAPS_GETCURRENTPOSITION2,
    DSBPLAY_LOOPING, DSBSTATUS_PLAYING, DSBSTATUS_LOOPING,
    DSBLOCK_ENTIREBUFFER
)


class TestDirectSound(unittest.TestCase):
    def setUp(self):
        # 640 MB guest linear memory representation
        self.mem = bytearray(0x28000000)
        self.dsound = GuestDSound(self.mem)

    def test_directsound_iat_and_vtables(self):
        """Verify DirectSoundCreate IAT slot, IDirectSound8 and IDirectSoundBuffer8 COM vtables."""
        # 1. IAT entrypoint at 0x00967038
        iat_val = struct.unpack_from('<I', self.mem, DSOUND_DIRECTSOUNDCREATE_IAT_VA)[0]
        self.assertEqual(iat_val, DSOUND_DIRECTSOUNDCREATE_IAT_VA)

        # 2. IDirectSound8 COM object vtable pointer
        ds_vtbl = struct.unpack_from('<I', self.mem, DSOUND_GUEST_DSOUND_ADDR)[0]
        self.assertEqual(ds_vtbl, DSOUND_GUEST_DSOUND_VTBL)

        # 3. Check 11 IDirectSound8 methods
        for i in range(11):
            method_va = struct.unpack_from('<I', self.mem, DSOUND_GUEST_DSOUND_VTBL + i * 4)[0]
            self.assertEqual(method_va, 0x00962600 + i * 4)

        # 4. IDirectSoundBuffer8 Primary COM object vtable pointer
        pbuf_vtbl = struct.unpack_from('<I', self.mem, DSOUND_GUEST_PRIMARY_BUF_ADDR)[0]
        self.assertEqual(pbuf_vtbl, DSOUND_GUEST_PRIMARY_BUF_VTBL)

        # 5. Check 21 IDirectSoundBuffer8 methods
        for i in range(21):
            method_va = struct.unpack_from('<I', self.mem, DSOUND_GUEST_PRIMARY_BUF_VTBL + i * 4)[0]
            self.assertEqual(method_va, 0x00962800 + i * 4)

        # 6. Secondary buffer points to valid buffer vtable
        sbuf_vtbl = struct.unpack_from('<I', self.mem, DSOUND_GUEST_SECONDARY_BUF_ADDR)[0]
        self.assertEqual(sbuf_vtbl, DSOUND_GUEST_PRIMARY_BUF_VTBL)

    def test_audio_ring_header_initialization(self):
        """Verify AudioRing shared memory header layout and parameters."""
        hdr = self.dsound.get_audio_ring_header()
        self.assertEqual(hdr["magic"], AUDIO_RING_MAGIC)       # 'NAUD'
        self.assertEqual(hdr["version"], AUDIO_RING_VERSION)   # 1
        self.assertEqual(hdr["frames"], AUDIO_RING_FRAMES)     # 16384
        self.assertEqual(hdr["rate"], AUDIO_RATE)              # 44100
        self.assertEqual(hdr["w"], 0)                          # initial write cursor
        self.assertEqual(hdr["r"], 0)                          # initial read cursor
        self.assertEqual(hdr["target"], 2048)                  # ~46 ms target latency

    def test_create_sound_buffer_primary_and_secondary(self):
        """Verify CreateSoundBuffer returns correct COM pointers for primary vs secondary."""
        # Primary buffer creation
        p_ptr = self.dsound.create_sound_buffer(DSBCAPS_PRIMARYBUFFER)
        self.assertEqual(p_ptr, DSOUND_GUEST_PRIMARY_BUF_ADDR)

        # Secondary 500ms streaming buffer creation (88,200 bytes)
        sec_bytes = 88200
        flags = DSBCAPS_GETCURRENTPOSITION2 | DSBCAPS_GLOBALFOCUS
        s_ptr = self.dsound.create_sound_buffer(flags, sec_bytes)
        self.assertEqual(s_ptr, DSOUND_GUEST_SECONDARY_BUF_ADDR)
        self.assertEqual(self.dsound.secondary_buffer_bytes, 88200)

    def test_circular_lock_without_wrapping(self):
        """Verify Lock() returns a single contiguous region when request does not cross wrap boundary."""
        # Lock 4096 bytes starting at offset 0 of 88200 byte buffer
        self.dsound.secondary_buffer_bytes = 88200
        ptr1, b1, ptr2, b2 = self.dsound.lock(offset=0, want_bytes=4096)
        self.assertEqual(ptr1, DSOUND_GUEST_PCM_DATA_ADDR)
        self.assertEqual(b1, 4096)
        self.assertEqual(ptr2, 0)
        self.assertEqual(b2, 0)

    def test_circular_lock_with_wrapping(self):
        """Verify Lock() accurately splits into two regions when wrapping around the circular buffer."""
        self.dsound.secondary_buffer_bytes = 88200
        # Buffer ends at 88200. Offset = 86000, want 4000 bytes.
        # Region 1: 86000..88200 (2200 bytes)
        # Region 2: 0..1800 (1800 bytes)
        ptr1, b1, ptr2, b2 = self.dsound.lock(offset=86000, want_bytes=4000)
        self.assertEqual(ptr1, DSOUND_GUEST_PCM_DATA_ADDR + 86000)
        self.assertEqual(b1, 2200)
        self.assertEqual(ptr2, DSOUND_GUEST_PCM_DATA_ADDR)
        self.assertEqual(b2, 1800)
        self.assertEqual(b1 + b2, 4000)

    def test_circular_lock_entire_buffer(self):
        """Verify Lock() with DSBLOCK_ENTIREBUFFER returns entire buffer starting from offset 0."""
        self.dsound.secondary_buffer_bytes = 88200
        ptr1, b1, ptr2, b2 = self.dsound.lock(offset=50000, want_bytes=1000, flags=DSBLOCK_ENTIREBUFFER)
        self.assertEqual(ptr1, DSOUND_GUEST_PCM_DATA_ADDR)
        self.assertEqual(b1, 88200)
        self.assertEqual(ptr2, 0)
        self.assertEqual(b2, 0)

    def test_unlock_pcm_conversion_and_audio_ring_streaming(self):
        """Verify Unlock() accurately translates 16-bit stereo PCM into float32 samples in the AudioRing."""
        # Write test samples into guest PCM buffer:
        # Frame 0: Left = 32767 (max pos), Right = -32768 (max neg)
        # Frame 1: Left = 0 (silence),     Right = 16384 (half scale)
        p1 = DSOUND_GUEST_PCM_DATA_ADDR
        struct.pack_into('<hh', self.mem, p1 + 0, 32767, -32768)
        struct.pack_into('<hh', self.mem, p1 + 4, 0, 16384)

        # Unlock 2 frames (8 bytes)
        rc = self.dsound.unlock(ptr1=p1, bytes1=8, ptr2=0, bytes2=0)
        self.assertEqual(rc, DS_OK)

        # AudioRing write cursor should now be 2
        hdr = self.dsound.get_audio_ring_header()
        self.assertEqual(hdr["w"], 2)

        # Read back float32 samples from AudioRing
        pcm_base = DSOUND_GUEST_AUDIO_RING_ADDR + 256
        f0_l, f0_r = struct.unpack_from('<ff', self.mem, pcm_base + 0)
        f1_l, f1_r = struct.unpack_from('<ff', self.mem, pcm_base + 8)

        self.assertAlmostEqual(f0_l, 32767 / 32768.0, places=5)
        self.assertAlmostEqual(f0_r, -1.0, places=5)
        self.assertAlmostEqual(f1_l, 0.0, places=5)
        self.assertAlmostEqual(f1_r, 16384 / 32768.0, places=5)

    def test_play_stop_and_cursor_tracking(self):
        """Verify Play, Stop, and GetCurrentPosition cursor lead."""
        self.dsound.secondary_buffer_bytes = 88200
        self.assertEqual(self.dsound.get_status(), 0)

        # Start playback looping
        self.dsound.play(looping=True)
        self.assertEqual(self.dsound.get_status(), DSBSTATUS_PLAYING | DSBSTATUS_LOOPING)

        # Check cursor: initial play_pos = 0, write_pos = 2048
        play_pos, write_pos = self.dsound.get_current_position()
        self.assertEqual(play_pos, 0)
        self.assertEqual(write_pos, 2048)

        # Push 4096 bytes via unlock
        p1 = DSOUND_GUEST_PCM_DATA_ADDR
        # Fill with zero samples
        self.mem[p1:p1 + 4096] = b'\x00' * 4096
        self.dsound.unlock(ptr1=p1, bytes1=4096)

        # Play cursor should advance by 4096
        play_pos, write_pos = self.dsound.get_current_position()
        self.assertEqual(play_pos, 4096)
        self.assertEqual(write_pos, 4096 + 2048)

        # Stop playback
        self.dsound.stop()
        self.assertEqual(self.dsound.get_status(), 0)


if __name__ == '__main__':
    unittest.main()

