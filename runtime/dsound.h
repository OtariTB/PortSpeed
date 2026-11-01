/* Need for Speed ProStreet - DirectSound COM Interface Shim Header.
 *
 * Provides authentic DirectSound COM vtables for IDirectSound8 and IDirectSoundBuffer8,
 * managing the primary mix buffer and looping secondary PCM audio stream,
 * and feeding decoded float32 stereo audio frames directly into the browser's AudioWorklet.
 */
#ifndef PROSTREET_DSOUND_H
#define PROSTREET_DSOUND_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "cpu.h"

#ifdef __cplusplus
extern "C" {
#endif

/* --------------------------------------------------------------------------
 * DirectSound Return Codes & Error Values
 * -------------------------------------------------------------------------- */
#define DS_OK                       0x00000000u
#define DSERR_UNSUPPORTED           0x80004001u
#define DSERR_GENERIC               0x80004005u
#define DSERR_OUTOFMEMORY           0x8007000Eu
#define DSERR_INVALIDPARAM          0x80070057u
#define DSERR_ALLOCATED             0x8878000Au
#define DSERR_CONTROLUNAVAIL        0x8878001Eu
#define DSERR_INVALIDCALL           0x88780032u
#define DSERR_PRIOLEVELNEEDED       0x88780046u
#define DSERR_BADFORMAT             0x88780064u
#define DSERR_NODRIVER              0x88780078u
#define DSERR_ALREADYINITIALIZED    0x88780082u
#define DSERR_BUFFERLOST            0x88780096u

/* --------------------------------------------------------------------------
 * DirectSound Buffer Capabilities & Flags
 * -------------------------------------------------------------------------- */
#define DSBCAPS_PRIMARYBUFFER       0x00000001u
#define DSBCAPS_STATIC              0x00000002u
#define DSBCAPS_LOCHARDWARE         0x00000004u
#define DSBCAPS_LOCSOFTWARE         0x00000008u
#define DSBCAPS_CTRL3D              0x00000010u
#define DSBCAPS_CTRLFREQUENCY       0x00000020u
#define DSBCAPS_CTRLPAN             0x00000040u
#define DSBCAPS_CTRLVOLUME          0x00000080u
#define DSBCAPS_CTRLPOSITIONNOTIFY  0x00000100u
#define DSBCAPS_CTRLFX              0x00000200u
#define DSBCAPS_STICKYFOCUS         0x00004000u
#define DSBCAPS_GLOBALFOCUS         0x00008000u
#define DSBCAPS_GETCURRENTPOSITION2 0x00010000u
#define DSBCAPS_MUTE3DATMAXDISTANCE 0x00020000u
#define DSBCAPS_LOCDEFER            0x00040000u

#define DSBPLAY_LOOPING             0x00000001u
#define DSBPLAY_LOCHARDWARE         0x00000002u
#define DSBPLAY_LOCSOFTWARE         0x00000004u
#define DSBPLAY_TERMINATEBY_TIME    0x00000008u
#define DSBPLAY_TERMINATEBY_DISTANCE 0x00000010u
#define DSBPLAY_TERMINATEBY_PRIORITY 0x00000020u

#define DSBSTATUS_PLAYING           0x00000001u
#define DSBSTATUS_BUFFERLOST        0x00000002u
#define DSBSTATUS_LOOPING           0x00000004u

#define DSBLOCK_FROMWRITECURSOR     0x00000001u
#define DSBLOCK_ENTIREBUFFER        0x00000002u

#define DSSCL_NORMAL                0x00000001u
#define DSSCL_PRIORITY              0x00000002u
#define DSSCL_EXCLUSIVE             0x00000003u
#define DSSCL_WRITEPRIMARY          0x00000004u

#define DSSPEAKER_HEADPHONE         0x00000001u
#define DSSPEAKER_MONO              0x00000002u
#define DSSPEAKER_QUAD              0x00000003u
#define DSSPEAKER_STEREO            0x00000004u
#define DSSPEAKER_SURROUND          0x00000005u
#define DSSPEAKER_5POINT1           0x00000006u
#define DSSPEAKER_7POINT1           0x00000007u

/* --------------------------------------------------------------------------
 * DirectSound IAT & Guest Memory Addresses
 * -------------------------------------------------------------------------- */
#define DSOUND_DIRECTSOUNDCREATE_IAT_VA  0x00967038u

#define DSOUND_GUEST_DSOUND_ADDR         0x0200B000u
#define DSOUND_GUEST_DSOUND_VTBL         0x0200B100u

#define DSOUND_GUEST_PRIMARY_BUF_ADDR    0x0200B200u
#define DSOUND_GUEST_PRIMARY_BUF_VTBL    0x0200B300u

#define DSOUND_GUEST_SECONDARY_BUF_ADDR  0x0200B400u
#define DSOUND_GUEST_SECONDARY_BUF_VTBL  0x0200B500u

#define DSOUND_GUEST_PCM_DATA_ADDR       0x0200C000u
#define DSOUND_GUEST_PCM_DATA_SIZE       (88320u)      /* 500 ms at 44.1 kHz 16-bit stereo */

#define DSOUND_GUEST_AUDIO_RING_ADDR     0x02030000u

#define DSOUND_DSOUND_METHOD_BASE_VA     0x00962600u
#define DSOUND_DSOUND_METHOD_COUNT       11u

#define DSOUND_BUFFER_METHOD_BASE_VA     0x00962800u
#define DSOUND_BUFFER_METHOD_COUNT       21u

/* --------------------------------------------------------------------------
 * Shared AudioRing Protocol (WebAssembly Producer <-> AudioWorklet Consumer)
 * -------------------------------------------------------------------------- */
#define AUDIO_RING_MAGIC        0x4E415544u  /* 'NAUD' */
#define AUDIO_RING_VERSION      1u
#define AUDIO_RING_FRAMES       16384u       /* Power of 2: ~372 ms at 44.1 kHz */
#define AUDIO_RATE              44100u       /* ProStreet mixing sample rate */

enum {
    AR_MAGIC = 0,
    AR_VERSION = 1,
    AR_FRAMES = 2,       /* Total ring size in stereo frames */
    AR_RATE = 3,         /* Sample rate in Hz (44100) */
    AR_W = 4,            /* Producer: frames written (monotonically increasing) */
    AR_R = 5,            /* Consumer: frames read by AudioWorklet */
    AR_UNDERRUNS = 6,    /* Underrun quantum count */
    AR_CTX = 7,          /* AudioContext state (0=none, 1=running, 2=suspended) */
    AR_QUANTA = 8,       /* Worklet process() invocations */
    AR_TARGET = 9,       /* Target buffer lead in frames */
    AR_MUTED = 12,       /* 1 = Muted / silence output */
    AR_HDR_WORDS = 32
};

typedef struct {
    uint32_t h[AR_HDR_WORDS];
    float    pcm[AUDIO_RING_FRAMES * 2]; /* Interleaved L, R float32 frames (-1.0f .. 1.0f) */
} dsound_audio_ring_t;

/* --------------------------------------------------------------------------
 * DirectSound Binary Structures (Windows ABI)
 * -------------------------------------------------------------------------- */
#pragma pack(push, 1)

typedef struct {
    uint16_t wFormatTag;        /* 1 = WAVE_FORMAT_PCM */
    uint16_t nChannels;         /* 2 = Stereo */
    uint32_t nSamplesPerSec;    /* 44100 */
    uint32_t nAvgBytesPerSec;   /* 176400 */
    uint16_t nBlockAlign;       /* 4 bytes */
    uint16_t wBitsPerSample;    /* 16 bits */
    uint16_t cbSize;            /* Extra format bytes (0 for standard PCM) */
} dsound_waveformat_ex_t;

typedef struct {
    uint32_t dwSize;
    uint32_t dwFlags;
    uint32_t dwBufferBytes;
    uint32_t dwReserved;
    uint32_t lpwfxFormat;       /* Guest pointer to WAVEFORMATEX */
    uint8_t  guid3DAlgorithm[16];
} dsound_buffer_desc_t;

typedef struct {
    uint32_t dwSize;
    uint32_t dwFlags;
    uint32_t dwMinSecondarySampleRate;
    uint32_t dwMaxSecondarySampleRate;
    uint32_t dwPrimaryBuffers;
    uint32_t dwMaxHwMixingAllBuffers;
    uint32_t dwMaxHwMixingStaticBuffers;
    uint32_t dwMaxHwMixingStreamingBuffers;
    uint32_t dwFreeHwMixingAllBuffers;
    uint32_t dwFreeHwMixingStaticBuffers;
    uint32_t dwFreeHwMixingStreamingBuffers;
    uint32_t dwMaxHw3DAllBuffers;
    uint32_t dwMaxHw3DStaticBuffers;
    uint32_t dwMaxHw3DStreamingBuffers;
    uint32_t dwFreeHw3DAllBuffers;
    uint32_t dwFreeHw3DStaticBuffers;
    uint32_t dwFreeHw3DStreamingBuffers;
    uint32_t dwTotalHwMemBytes;
    uint32_t dwFreeHwMemBytes;
    uint32_t dwMaxContigFreeHwMemBytes;
    uint32_t dwUnlockTransferRateHwBuffers;
    uint32_t dwPlayCpuOverheadSwBuffers;
    uint32_t dwReserved1;
    uint32_t dwReserved2;
} dsound_caps_t;

typedef struct {
    uint32_t dwSize;
    uint32_t dwFlags;
    uint32_t dwBufferBytes;
    uint32_t dwUnlockTransferRate;
    uint32_t dwPlayCpuOverhead;
} dsound_buffer_caps_t;

#pragma pack(pop)

/* --------------------------------------------------------------------------
 * DirectSound Runtime API
 * -------------------------------------------------------------------------- */
void dsound_init_iat(void);
void dsound_init(void);

/* IAT Entrypoint / Shim */
void dsound_shim_DirectSoundCreate(CPU *c);

/* Audio State Inspection Helpers */
bool dsound_is_playing(void);
uint32_t dsound_get_sample_rate(void);
uint32_t dsound_get_frames_written(void);
dsound_audio_ring_t *dsound_get_audio_ring(void);

#ifdef __cplusplus
}
#endif

#endif /* PROSTREET_DSOUND_H */

