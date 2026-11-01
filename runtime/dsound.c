/* Need for Speed ProStreet - DirectSound COM Interface Shim Implementation.
 *
 * Implements DirectSoundCreate (DSOUND.dll Ordinal 1), IDirectSound8 (11 methods),
 * and IDirectSoundBuffer8 (21 methods) COM vtables, managing primary and secondary
 * audio buffers, and streaming converted float32 stereo frames into the shared AudioRing.
 */
#include "dsound.h"
#include <stdio.h>
#include <string.h>

/* --------------------------------------------------------------------------
 * Internal State
 * -------------------------------------------------------------------------- */
static uint32_t s_dsound_ref_count = 1u;
static uint32_t s_primary_ref_count = 0u;
static uint32_t s_secondary_ref_count = 0u;

static uint32_t s_coop_level = DSSCL_PRIORITY;
static uint32_t s_sample_rate = AUDIO_RATE;
static uint32_t s_channels = 2u;
static uint32_t s_bits_per_sample = 16u;

static uint32_t s_secondary_buffer_bytes = DSOUND_GUEST_PCM_DATA_SIZE;
static uint32_t s_play_cursor_bytes = 0u;

static int32_t  s_volume = 0; /* 0 dB */
static int32_t  s_pan = 0;    /* Center */
static bool     s_is_playing = false;
static bool     s_is_looping = false;

static uint32_t s_frames_written_total = 0u;

/* Static COM GUID definitions */
static const dsound_waveformat_ex_t s_default_format = {
    1u,         /* WAVE_FORMAT_PCM */
    2u,         /* 2 channels (Stereo) */
    AUDIO_RATE, /* 44100 Hz */
    176400u,    /* 44100 * 4 bytes/sec */
    4u,         /* 4-byte block align (16-bit stereo) */
    16u,        /* 16 bits per sample */
    0u          /* cbSize */
};

/* --------------------------------------------------------------------------
 * AudioRing Producer Helpers
 * -------------------------------------------------------------------------- */
static void dsound_push_pcm_chunk(uint32_t guest_ptr, uint32_t byte_count) {
    if (guest_ptr == 0u || byte_count < 4u || !GUEST_MEM_READY) return;

    dsound_audio_ring_t *ring = (dsound_audio_ring_t *)(g_mem + DSOUND_GUEST_AUDIO_RING_ADDR);
    const int16_t *src = (const int16_t *)(g_mem + guest_ptr);
    uint32_t frames_to_push = byte_count / 4u; /* 16-bit stereo: 4 bytes per frame */

    uint32_t w = ring->h[AR_W];
    for (uint32_t i = 0; i < frames_to_push; ++i) {
        uint32_t idx = (w + i) & (AUDIO_RING_FRAMES - 1u);
        float left  = (float)src[i * 2 + 0] * (1.0f / 32768.0f);
        float right = (float)src[i * 2 + 1] * (1.0f / 32768.0f);
        ring->pcm[idx * 2 + 0] = left;
        ring->pcm[idx * 2 + 1] = right;
    }

    ring->h[AR_W] = w + frames_to_push;
    s_frames_written_total += frames_to_push;

    /* Advance internal play cursor smoothly within circular buffer bounds */
    uint32_t buf_sz = s_secondary_buffer_bytes ? s_secondary_buffer_bytes : DSOUND_GUEST_PCM_DATA_SIZE;
    s_play_cursor_bytes = (s_play_cursor_bytes + byte_count) % buf_sz;
}

/* --------------------------------------------------------------------------
 * IDirectSound8 COM VTable Handlers (11 methods)
 * -------------------------------------------------------------------------- */

/* Method 0: QueryInterface(this, riid, ppvObj) */
static void dsound_QueryInterface(CPU *c) {
    uint32_t this_ptr = MR32(c->esp);
    uint32_t ppvObj   = MR32(c->esp + 8u);

    if (ppvObj != 0u) {
        MR32(ppvObj) = this_ptr;
        s_dsound_ref_count++;
    }

    c->eax = DS_OK;
    c->esp += 12u;
}

/* Method 1: AddRef(this) */
static void dsound_AddRef(CPU *c) {
    s_dsound_ref_count++;
    c->eax = s_dsound_ref_count;
    c->esp += 4u;
}

/* Method 2: Release(this) */
static void dsound_Release(CPU *c) {
    if (s_dsound_ref_count > 0u) {
        s_dsound_ref_count--;
    }
    c->eax = s_dsound_ref_count;
    c->esp += 4u;
}

/* Method 3: CreateSoundBuffer(this, lpDSBufferDesc, lplpDirectSoundBuffer, pUnkOuter) */
static void dsound_CreateSoundBuffer(CPU *c) {
    uint32_t lpDesc = MR32(c->esp + 4u);
    uint32_t lplpBuf = MR32(c->esp + 8u);

    if (lplpBuf != 0u && lpDesc != 0u) {
        uint32_t dwFlags = MR32(lpDesc + 4u);
        if (dwFlags & DSBCAPS_PRIMARYBUFFER) {
            MR32(lplpBuf) = DSOUND_GUEST_PRIMARY_BUF_ADDR;
            s_primary_ref_count++;
        } else {
            MR32(lplpBuf) = DSOUND_GUEST_SECONDARY_BUF_ADDR;
            s_secondary_ref_count++;
            uint32_t bytes = MR32(lpDesc + 8u);
            if (bytes != 0u) {
                s_secondary_buffer_bytes = bytes;
            }
        }
    }

    c->eax = DS_OK;
    c->esp += 16u;
}

/* Method 4: GetCaps(this, lpDSCaps) */
static void dsound_GetCaps(CPU *c) {
    uint32_t lpCaps = MR32(c->esp + 4u);

    if (lpCaps != 0u && GUEST_MEM_READY) {
        dsound_caps_t *caps = (dsound_caps_t *)(g_mem + lpCaps);
        memset(caps, 0, sizeof(*caps));
        caps->dwSize = (uint32_t)sizeof(dsound_caps_t);
        caps->dwFlags = 0x00000001u | 0x00000004u | 0x00000008u; /* Primary/Secondary 16-bit Stereo */
        caps->dwMinSecondarySampleRate = 4000u;
        caps->dwMaxSecondarySampleRate = 48000u;
        caps->dwPrimaryBuffers = 1u;
        caps->dwMaxHwMixingAllBuffers = 16u;
        caps->dwFreeHwMixingAllBuffers = 16u;
    }

    c->eax = DS_OK;
    c->esp += 8u;
}

/* Method 5: DuplicateSoundBuffer(this, lpDSOld, lplpDSNew) */
static void dsound_DuplicateSoundBuffer(CPU *c) {
    uint32_t lplpDSNew = MR32(c->esp + 8u);
    if (lplpDSNew != 0u) {
        MR32(lplpDSNew) = DSOUND_GUEST_SECONDARY_BUF_ADDR;
        s_secondary_ref_count++;
    }
    c->eax = DS_OK;
    c->esp += 12u;
}

/* Method 6: SetCooperativeLevel(this, hwnd, dwLevel) */
static void dsound_SetCooperativeLevel(CPU *c) {
    uint32_t dwLevel = MR32(c->esp + 8u);
    s_coop_level = dwLevel;
    c->eax = DS_OK;
    c->esp += 12u;
}

/* Method 7: Compact(this) */
static void dsound_Compact(CPU *c) {
    c->eax = DS_OK;
    c->esp += 4u;
}

/* Method 8: GetSpeakerConfig(this, pdwSpeakerConfig) */
static void dsound_GetSpeakerConfig(CPU *c) {
    uint32_t pdwConfig = MR32(c->esp + 4u);
    if (pdwConfig != 0u) {
        MR32(pdwConfig) = DSSPEAKER_STEREO;
    }
    c->eax = DS_OK;
    c->esp += 8u;
}

/* Method 9: SetSpeakerConfig(this, dwSpeakerConfig) */
static void dsound_SetSpeakerConfig(CPU *c) {
    c->eax = DS_OK;
    c->esp += 8u;
}

/* Method 10: Initialize(this, pcGuidDevice) */
static void dsound_Initialize(CPU *c) {
    c->eax = DS_OK;
    c->esp += 8u;
}

/* --------------------------------------------------------------------------
 * IDirectSoundBuffer8 COM VTable Handlers (21 methods)
 * -------------------------------------------------------------------------- */

/* Method 0: QueryInterface(this, riid, ppvObj) */
static void buf_QueryInterface(CPU *c) {
    uint32_t this_ptr = MR32(c->esp);
    uint32_t ppvObj   = MR32(c->esp + 8u);

    if (ppvObj != 0u) {
        MR32(ppvObj) = this_ptr;
    }

    c->eax = DS_OK;
    c->esp += 12u;
}

/* Method 1: AddRef(this) */
static void buf_AddRef(CPU *c) {
    uint32_t this_ptr = MR32(c->esp);
    if (this_ptr == DSOUND_GUEST_PRIMARY_BUF_ADDR) {
        s_primary_ref_count++;
        c->eax = s_primary_ref_count;
    } else {
        s_secondary_ref_count++;
        c->eax = s_secondary_ref_count;
    }
    c->esp += 4u;
}

/* Method 2: Release(this) */
static void buf_Release(CPU *c) {
    uint32_t this_ptr = MR32(c->esp);
    if (this_ptr == DSOUND_GUEST_PRIMARY_BUF_ADDR) {
        if (s_primary_ref_count > 0u) s_primary_ref_count--;
        c->eax = s_primary_ref_count;
    } else {
        if (s_secondary_ref_count > 0u) s_secondary_ref_count--;
        c->eax = s_secondary_ref_count;
    }
    c->esp += 4u;
}

/* Method 3: GetCaps(this, lpDSBufferCaps) */
static void buf_GetCaps(CPU *c) {
    uint32_t this_ptr = MR32(c->esp);
    uint32_t lpCaps   = MR32(c->esp + 4u);

    if (lpCaps != 0u && GUEST_MEM_READY) {
        dsound_buffer_caps_t *caps = (dsound_buffer_caps_t *)(g_mem + lpCaps);
        caps->dwSize = (uint32_t)sizeof(dsound_buffer_caps_t);
        if (this_ptr == DSOUND_GUEST_PRIMARY_BUF_ADDR) {
            caps->dwFlags = DSBCAPS_PRIMARYBUFFER;
            caps->dwBufferBytes = 0u;
        } else {
            caps->dwFlags = DSBCAPS_GETCURRENTPOSITION2 | DSBCAPS_GLOBALFOCUS | DSBCAPS_CTRLVOLUME;
            caps->dwBufferBytes = s_secondary_buffer_bytes ? s_secondary_buffer_bytes : DSOUND_GUEST_PCM_DATA_SIZE;
        }
        caps->dwUnlockTransferRate = 0u;
        caps->dwPlayCpuOverhead = 0u;
    }

    c->eax = DS_OK;
    c->esp += 8u;
}

/* Method 4: GetCurrentPosition(this, lpdwCurrentPlayCursor, lpdwCurrentWriteCursor) */
static void buf_GetCurrentPosition(CPU *c) {
    uint32_t pplay  = MR32(c->esp + 4u);
    uint32_t pwrite = MR32(c->esp + 8u);
    uint32_t buf_sz = s_secondary_buffer_bytes ? s_secondary_buffer_bytes : DSOUND_GUEST_PCM_DATA_SIZE;

    uint32_t play_pos  = s_play_cursor_bytes % buf_sz;
    /* Safe write lead ahead of play cursor (2048 bytes ~11.6 ms at 44.1 kHz stereo) */
    uint32_t write_pos = (play_pos + 2048u) % buf_sz;

    if (pplay != 0u)  MR32(pplay)  = play_pos;
    if (pwrite != 0u) MR32(pwrite) = write_pos;

    c->eax = DS_OK;
    c->esp += 12u;
}

/* Method 5: GetFormat(this, lpwfxFormat, dwSizeAllocated, lpdwSizeWritten) */
static void buf_GetFormat(CPU *c) {
    uint32_t lpwfx   = MR32(c->esp + 4u);
    uint32_t psize   = MR32(c->esp + 12u);

    if (lpwfx != 0u && GUEST_MEM_READY) {
        memcpy(g_mem + lpwfx, &s_default_format, sizeof(s_default_format));
    }
    if (psize != 0u) {
        MR32(psize) = (uint32_t)sizeof(dsound_waveformat_ex_t);
    }

    c->eax = DS_OK;
    c->esp += 16u;
}

/* Method 6: GetVolume(this, plVolume) */
static void buf_GetVolume(CPU *c) {
    uint32_t pvol = MR32(c->esp + 4u);
    if (pvol != 0u) {
        MR32(pvol) = (uint32_t)s_volume;
    }
    c->eax = DS_OK;
    c->esp += 8u;
}

/* Method 7: GetPan(this, plPan) */
static void buf_GetPan(CPU *c) {
    uint32_t ppan = MR32(c->esp + 4u);
    if (ppan != 0u) {
        MR32(ppan) = (uint32_t)s_pan;
    }
    c->eax = DS_OK;
    c->esp += 8u;
}

/* Method 8: GetFrequency(this, pdwFrequency) */
static void buf_GetFrequency(CPU *c) {
    uint32_t pfreq = MR32(c->esp + 4u);
    if (pfreq != 0u) {
        MR32(pfreq) = s_sample_rate;
    }
    c->eax = DS_OK;
    c->esp += 8u;
}

/* Method 9: GetStatus(this, pdwStatus) */
static void buf_GetStatus(CPU *c) {
    uint32_t pstat = MR32(c->esp + 4u);
    if (pstat != 0u) {
        uint32_t status = 0u;
        if (s_is_playing) {
            status |= DSBSTATUS_PLAYING;
            if (s_is_looping) status |= DSBSTATUS_LOOPING;
        }
        MR32(pstat) = status;
    }
    c->eax = DS_OK;
    c->esp += 8u;
}

/* Method 10: Initialize(this, lpDirectSound, lpDSBufferDesc) */
static void buf_Initialize(CPU *c) {
    c->eax = DS_OK;
    c->esp += 12u;
}

/* Method 11: Lock(this, dwOffset, dwBytes, ppv1, pcb1, ppv2, pcb2, dwFlags) */
static void buf_Lock(CPU *c) {
    uint32_t off   = MR32(c->esp + 4u);
    uint32_t want  = MR32(c->esp + 8u);
    uint32_t pp1   = MR32(c->esp + 12u);
    uint32_t pn1   = MR32(c->esp + 16u);
    uint32_t pp2   = MR32(c->esp + 20u);
    uint32_t pn2   = MR32(c->esp + 24u);
    uint32_t flags = MR32(c->esp + 28u);

    uint32_t buf_sz = s_secondary_buffer_bytes ? s_secondary_buffer_bytes : DSOUND_GUEST_PCM_DATA_SIZE;
    if (flags & DSBLOCK_ENTIREBUFFER) {
        off  = 0u;
        want = buf_sz;
    }

    off %= buf_sz;
    if (want == 0u || want > buf_sz) want = buf_sz;

    uint32_t avail = buf_sz - off;
    uint32_t b1 = (want <= avail) ? want : avail;
    uint32_t b2 = want - b1;

    if (pp1 != 0u) MR32(pp1) = DSOUND_GUEST_PCM_DATA_ADDR + off;
    if (pn1 != 0u) MR32(pn1) = b1;

    if (pp2 != 0u) MR32(pp2) = b2 ? DSOUND_GUEST_PCM_DATA_ADDR : 0u;
    if (pn2 != 0u) MR32(pn2) = b2;

    c->eax = DS_OK;
    c->esp += 32u;
}

/* Method 12: Play(this, dwReserved1, dwPriority, dwFlags) */
static void buf_Play(CPU *c) {
    uint32_t dwFlags = MR32(c->esp + 12u);
    s_is_playing = true;
    s_is_looping = (dwFlags & DSBPLAY_LOOPING) != 0u;

    c->eax = DS_OK;
    c->esp += 16u;
}

/* Method 13: SetCurrentPosition(this, dwNewPosition) */
static void buf_SetCurrentPosition(CPU *c) {
    uint32_t dwPos = MR32(c->esp + 4u);
    uint32_t buf_sz = s_secondary_buffer_bytes ? s_secondary_buffer_bytes : DSOUND_GUEST_PCM_DATA_SIZE;
    s_play_cursor_bytes = dwPos % buf_sz;

    c->eax = DS_OK;
    c->esp += 8u;
}

/* Method 14: SetFormat(this, lpcfxFormat) */
static void buf_SetFormat(CPU *c) {
    uint32_t lpcfx = MR32(c->esp + 4u);
    if (lpcfx != 0u && GUEST_MEM_READY) {
        const dsound_waveformat_ex_t *fmt = (const dsound_waveformat_ex_t *)(g_mem + lpcfx);
        if (fmt->nSamplesPerSec != 0u) {
            s_sample_rate = fmt->nSamplesPerSec;
        }
        if (fmt->nChannels != 0u) {
            s_channels = fmt->nChannels;
        }
        if (fmt->wBitsPerSample != 0u) {
            s_bits_per_sample = fmt->wBitsPerSample;
        }
    }

    c->eax = DS_OK;
    c->esp += 8u;
}

/* Method 15: SetVolume(this, lVolume) */
static void buf_SetVolume(CPU *c) {
    s_volume = (int32_t)MR32(c->esp + 4u);
    c->eax = DS_OK;
    c->esp += 8u;
}

/* Method 16: SetPan(this, lPan) */
static void buf_SetPan(CPU *c) {
    s_pan = (int32_t)MR32(c->esp + 4u);
    c->eax = DS_OK;
    c->esp += 8u;
}

/* Method 17: SetFrequency(this, dwFrequency) */
static void buf_SetFrequency(CPU *c) {
    uint32_t freq = MR32(c->esp + 4u);
    if (freq != 0u) {
        s_sample_rate = freq;
    }
    c->eax = DS_OK;
    c->esp += 8u;
}

/* Method 18: Stop(this) */
static void buf_Stop(CPU *c) {
    s_is_playing = false;
    c->eax = DS_OK;
    c->esp += 4u;
}

/* Method 19: Unlock(this, pvAudioPtr1, dwAudioBytes1, pvAudioPtr2, dwAudioBytes2) */
static void buf_Unlock(CPU *c) {
    uint32_t p1 = MR32(c->esp + 4u);
    uint32_t n1 = MR32(c->esp + 8u);
    uint32_t p2 = MR32(c->esp + 12u);
    uint32_t n2 = MR32(c->esp + 16u);

    if (p1 != 0u && n1 != 0u) {
        dsound_push_pcm_chunk(p1, n1);
    }
    if (p2 != 0u && n2 != 0u) {
        dsound_push_pcm_chunk(p2, n2);
    }

    c->eax = DS_OK;
    c->esp += 20u;
}

/* Method 20: Restore(this) */
static void buf_Restore(CPU *c) {
    c->eax = DS_OK;
    c->esp += 4u;
}

/* --------------------------------------------------------------------------
 * Dispatch Tables
 * -------------------------------------------------------------------------- */
static const guest_fn_t s_dsound_handlers[DSOUND_DSOUND_METHOD_COUNT] = {
    dsound_QueryInterface,          /* 0: QueryInterface */
    dsound_AddRef,                  /* 1: AddRef */
    dsound_Release,                 /* 2: Release */
    dsound_CreateSoundBuffer,       /* 3: CreateSoundBuffer */
    dsound_GetCaps,                 /* 4: GetCaps */
    dsound_DuplicateSoundBuffer,    /* 5: DuplicateSoundBuffer */
    dsound_SetCooperativeLevel,     /* 6: SetCooperativeLevel */
    dsound_Compact,                 /* 7: Compact */
    dsound_GetSpeakerConfig,        /* 8: GetSpeakerConfig */
    dsound_SetSpeakerConfig,        /* 9: SetSpeakerConfig */
    dsound_Initialize               /* 10: Initialize */
};

static const guest_fn_t s_buffer_handlers[DSOUND_BUFFER_METHOD_COUNT] = {
    buf_QueryInterface,             /* 0: QueryInterface */
    buf_AddRef,                     /* 1: AddRef */
    buf_Release,                    /* 2: Release */
    buf_GetCaps,                    /* 3: GetCaps */
    buf_GetCurrentPosition,         /* 4: GetCurrentPosition */
    buf_GetFormat,                  /* 5: GetFormat */
    buf_GetVolume,                  /* 6: GetVolume */
    buf_GetPan,                     /* 7: GetPan */
    buf_GetFrequency,               /* 8: GetFrequency */
    buf_GetStatus,                  /* 9: GetStatus */
    buf_Initialize,                 /* 10: Initialize */
    buf_Lock,                       /* 11: Lock */
    buf_Play,                       /* 12: Play */
    buf_SetCurrentPosition,         /* 13: SetCurrentPosition */
    buf_SetFormat,                  /* 14: SetFormat */
    buf_SetVolume,                  /* 15: SetVolume */
    buf_SetPan,                     /* 16: SetPan */
    buf_SetFrequency,               /* 17: SetFrequency */
    buf_Stop,                       /* 18: Stop */
    buf_Unlock,                     /* 19: Unlock */
    buf_Restore                     /* 20: Restore */
};

/* --------------------------------------------------------------------------
 * DirectSoundCreate Shim (DSOUND.dll Ordinal 1 at IAT 0x00967038)
 * -------------------------------------------------------------------------- */
void dsound_shim_DirectSoundCreate(CPU *c) {
    uint32_t ppDS = MR32(c->esp + 8u);

    if (ppDS != 0u) {
        MR32(ppDS) = DSOUND_GUEST_DSOUND_ADDR;
        s_dsound_ref_count++;
    }

    c->eax = DS_OK;
    c->esp += 12u;
}

/* --------------------------------------------------------------------------
 * Lifecycle & Initialization API
 * -------------------------------------------------------------------------- */
void dsound_init_iat(void) {
    uint32_t idx = DSOUND_DIRECTSOUNDCREATE_IAT_VA - DISPATCH_TEXT_BASE;
    if (idx < DISPATCH_TEXT_SIZE) {
        g_dtab[idx] = dsound_shim_DirectSoundCreate;
    }
    if (GUEST_MEM_READY) {
        MR32(DSOUND_DIRECTSOUNDCREATE_IAT_VA) = DSOUND_DIRECTSOUNDCREATE_IAT_VA;
    }
}

void dsound_init(void) {
    s_dsound_ref_count = 1u;
    s_primary_ref_count = 0u;
    s_secondary_ref_count = 0u;
    s_sample_rate = AUDIO_RATE;
    s_channels = 2u;
    s_bits_per_sample = 16u;
    s_secondary_buffer_bytes = DSOUND_GUEST_PCM_DATA_SIZE;
    s_play_cursor_bytes = 0u;
    s_volume = 0;
    s_pan = 0;
    s_is_playing = false;
    s_is_looping = false;
    s_frames_written_total = 0u;

    if (!GUEST_MEM_READY) return;

    /* 1. Bind DirectSoundCreate IAT */
    dsound_init_iat();

    /* 2. Set up IDirectSound8 COM Object and VTable (11 methods) */
    MR32(DSOUND_GUEST_DSOUND_ADDR) = DSOUND_GUEST_DSOUND_VTBL;
    for (uint32_t i = 0; i < DSOUND_DSOUND_METHOD_COUNT; ++i) {
        uint32_t m_va = DSOUND_DSOUND_METHOD_BASE_VA + i * 4u;
        MR32(DSOUND_GUEST_DSOUND_VTBL + i * 4u) = m_va;
        uint32_t idx = m_va - DISPATCH_TEXT_BASE;
        if (idx < DISPATCH_TEXT_SIZE) {
            g_dtab[idx] = s_dsound_handlers[i];
        }
    }

    /* 3. Set up Primary IDirectSoundBuffer COM Object and VTable (21 methods) */
    MR32(DSOUND_GUEST_PRIMARY_BUF_ADDR) = DSOUND_GUEST_PRIMARY_BUF_VTBL;
    for (uint32_t i = 0; i < DSOUND_BUFFER_METHOD_COUNT; ++i) {
        uint32_t m_va = DSOUND_BUFFER_METHOD_BASE_VA + i * 4u;
        MR32(DSOUND_GUEST_PRIMARY_BUF_VTBL + i * 4u) = m_va;
        uint32_t idx = m_va - DISPATCH_TEXT_BASE;
        if (idx < DISPATCH_TEXT_SIZE) {
            g_dtab[idx] = s_buffer_handlers[i];
        }
    }

    /* 4. Set up Secondary IDirectSoundBuffer COM Object and VTable (21 methods) */
    MR32(DSOUND_GUEST_SECONDARY_BUF_ADDR) = DSOUND_GUEST_SECONDARY_BUF_VTBL;
    /* Secondary buffer shares the same vtable pointer address */
    MR32(DSOUND_GUEST_SECONDARY_BUF_ADDR) = DSOUND_GUEST_PRIMARY_BUF_VTBL;

    /* 5. Initialize Shared AudioRing Header */
    dsound_audio_ring_t *ring = (dsound_audio_ring_t *)(g_mem + DSOUND_GUEST_AUDIO_RING_ADDR);
    memset(ring, 0, sizeof(*ring));
    ring->h[AR_MAGIC] = AUDIO_RING_MAGIC;
    ring->h[AR_VERSION] = AUDIO_RING_VERSION;
    ring->h[AR_FRAMES] = AUDIO_RING_FRAMES;
    ring->h[AR_RATE] = AUDIO_RATE;
    ring->h[AR_W] = 0u;
    ring->h[AR_R] = 0u;
    ring->h[AR_TARGET] = 2048u; /* ~46 ms target buffer latency */
}

bool dsound_is_playing(void) {
    return s_is_playing;
}

uint32_t dsound_get_sample_rate(void) {
    return s_sample_rate;
}

uint32_t dsound_get_frames_written(void) {
    return s_frames_written_total;
}

dsound_audio_ring_t *dsound_get_audio_ring(void) {
    if (!GUEST_MEM_READY) return NULL;
    return (dsound_audio_ring_t *)(g_mem + DSOUND_GUEST_AUDIO_RING_ADDR);
}

