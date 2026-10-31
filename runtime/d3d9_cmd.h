/* Need for Speed ProStreet - Direct3D 9 Command Stream & Ring Buffer Protocol.
 *
 * Defines the lock-free shared-memory command ring buffer format between the
 * recompiled guest WebAssembly engine (producer) and the browser WebGPU/WebGL2
 * rendering host (consumer).
 *
 * All structures are naturally 4-byte aligned for lock-free 32-bit atomic access
 * over SharedArrayBuffer / Atomics.
 */
#ifndef PROSTREET_D3D9_CMD_H
#define PROSTREET_D3D9_CMD_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* --------------------------------------------------------------------------
 * Magic and Protocol Constants
 * -------------------------------------------------------------------------- */
#define D3D9_RING_MAGIC             0x39443344u   /* "D3D9" in little-endian */
#define D3D9_RING_VERSION           1u
#define D3D9_RING_DEFAULT_CAPACITY  (4u * 1024u * 1024u) /* 4 MB payload */
#define D3D9_RING_HEADER_SIZE       64u           /* Cache line padded header */

/* --------------------------------------------------------------------------
 * Direct3D 9 Command Types (Opcodes)
 * -------------------------------------------------------------------------- */
typedef enum {
    D3DCMD_NOP                          = 0,
    D3DCMD_CLEAR                        = 1,
    D3DCMD_BEGIN_SCENE                  = 2,
    D3DCMD_END_SCENE                    = 3,
    D3DCMD_PRESENT                      = 4,
    D3DCMD_SET_RENDER_STATE             = 5,
    D3DCMD_SET_SAMPLER_STATE            = 6,
    D3DCMD_SET_TEXTURE                  = 7,
    D3DCMD_SET_TRANSFORM                = 8,
    D3DCMD_SET_VIEWPORT                 = 9,
    D3DCMD_SET_STREAM_SOURCE            = 10,
    D3DCMD_SET_INDICES                  = 11,
    D3DCMD_DRAW_PRIMITIVE               = 12,
    D3DCMD_DRAW_INDEXED_PRIMITIVE       = 13,
    D3DCMD_CREATE_VERTEX_BUFFER         = 14,
    D3DCMD_CREATE_INDEX_BUFFER          = 15,
    D3DCMD_CREATE_TEXTURE               = 16,
    D3DCMD_UPDATE_TEXTURE               = 17,
    D3DCMD_DESTROY_RESOURCE             = 18,
    D3DCMD_SET_VERTEX_DECLARATION       = 19,
    D3DCMD_SET_VERTEX_SHADER            = 20,
    D3DCMD_SET_PIXEL_SHADER             = 21,
    D3DCMD_SET_VS_CONSTANTS             = 22,
    D3DCMD_SET_PS_CONSTANTS             = 23,
    D3DCMD_SET_SCISSOR_RECT             = 24,
    D3DCMD_COUNT                        = 25
} d3d9_cmd_type_t;

/* --------------------------------------------------------------------------
 * Shared Ring Buffer Control Header (64 bytes)
 * Located at byte 0 of the SharedArrayBuffer.
 * -------------------------------------------------------------------------- */
typedef struct {
    uint32_t magic;             /* Must match D3D9_RING_MAGIC */
    uint32_t version;           /* Must match D3D9_RING_VERSION */
    uint32_t head;              /* Producer write byte offset into data area */
    uint32_t tail;              /* Consumer read byte offset into data area */
    uint32_t capacity;          /* Capacity of data area in bytes (power of 2) */
    uint32_t frame_index;       /* Monotonic frame count incremented on Present */
    uint32_t dropped_frames;    /* Frame drop count if ring full */
    uint32_t flags;             /* Bit 0: VSync enabled, Bit 1: Paused */
    uint32_t reserved[8];       /* Padding to exactly 64 bytes (cache line aligned) */
} d3d9_ring_header_t;

/* --------------------------------------------------------------------------
 * Command Packet Header (8 bytes)
 * Precedes every command payload in the ring buffer.
 * -------------------------------------------------------------------------- */
typedef struct {
    uint16_t cmd_type;          /* d3d9_cmd_type_t */
    uint16_t flags;             /* Command-specific flags */
    uint32_t payload_bytes;     /* Byte size of payload following header (must be 4-byte aligned) */
} d3d9_cmd_header_t;

/* --------------------------------------------------------------------------
 * Command Payloads
 * -------------------------------------------------------------------------- */

/* D3DCMD_CLEAR (20 bytes) */
typedef struct {
    uint32_t flags;             /* D3DCLEAR_TARGET (1), D3DCLEAR_ZBUFFER (2), D3DCLEAR_STENCIL (4) */
    uint32_t color;             /* ARGB 32-bit integer */
    float    z;                 /* Depth clear value (typically 1.0f) */
    uint32_t stencil;           /* Stencil clear value (typically 0) */
    uint32_t count;             /* Number of rectangles (0 = full viewport) */
} d3d9_cmd_clear_t;

/* D3DCMD_PRESENT (16 bytes) */
typedef struct {
    uint32_t src_rect_x;
    uint32_t src_rect_y;
    uint32_t src_rect_w;
    uint32_t src_rect_h;
} d3d9_cmd_present_t;

/* D3DCMD_SET_RENDER_STATE (8 bytes) */
typedef struct {
    uint32_t state;             /* D3DRENDERSTATETYPE enum */
    uint32_t value;             /* State value */
} d3d9_cmd_set_render_state_t;

/* D3DCMD_SET_SAMPLER_STATE (12 bytes) */
typedef struct {
    uint32_t sampler;           /* Sampler index (0..15) */
    uint32_t type;              /* D3DSAMPLERSTATETYPE enum */
    uint32_t value;             /* Sampler state value */
} d3d9_cmd_set_sampler_state_t;

/* D3DCMD_SET_TEXTURE (8 bytes) */
typedef struct {
    uint32_t stage;             /* Texture stage index (0..7) */
    uint32_t texture_id;        /* Host texture resource ID (0 = unbind) */
} d3d9_cmd_set_texture_t;

/* D3DCMD_SET_TRANSFORM (68 bytes) */
typedef struct {
    uint32_t state;             /* D3DTRANSFORMSTATETYPE (WORLD=256, VIEW=2, PROJ=3) */
    float    matrix[16];        /* 4x4 row-major transform matrix */
} d3d9_cmd_set_transform_t;

/* D3DCMD_SET_VIEWPORT (24 bytes) */
typedef struct {
    uint32_t x;
    uint32_t y;
    uint32_t width;
    uint32_t height;
    float    min_z;
    float    max_z;
} d3d9_cmd_set_viewport_t;

/* D3DCMD_SET_STREAM_SOURCE (16 bytes) */
typedef struct {
    uint32_t stream_number;
    uint32_t buffer_id;         /* Vertex buffer resource ID */
    uint32_t offset;            /* Offset in bytes from start of vertex buffer */
    uint32_t stride;            /* Vertex stride in bytes */
} d3d9_cmd_set_stream_source_t;

/* D3DCMD_SET_INDICES (4 bytes) */
typedef struct {
    uint32_t buffer_id;         /* Index buffer resource ID (0 = unbind) */
} d3d9_cmd_set_indices_t;

/* D3DCMD_DRAW_PRIMITIVE (12 bytes) */
typedef struct {
    uint32_t primitive_type;    /* D3DPRIMITIVETYPE (TRIANGLELIST=4, etc.) */
    uint32_t start_vertex;
    uint32_t primitive_count;
} d3d9_cmd_draw_primitive_t;

/* D3DCMD_DRAW_INDEXED_PRIMITIVE (24 bytes) */
typedef struct {
    uint32_t primitive_type;    /* D3DPRIMITIVETYPE */
    int32_t  base_vertex_index;
    uint32_t min_vertex_index;
    uint32_t num_vertices;
    uint32_t start_index;
    uint32_t primitive_count;
} d3d9_cmd_draw_indexed_primitive_t;

/* D3DCMD_CREATE_VERTEX_BUFFER (20 bytes) */
typedef struct {
    uint32_t buffer_id;
    uint32_t length;            /* Size in bytes */
    uint32_t usage;
    uint32_t fvf;
    uint32_t pool;
} d3d9_cmd_create_vertex_buffer_t;

/* D3DCMD_CREATE_INDEX_BUFFER (20 bytes) */
typedef struct {
    uint32_t buffer_id;
    uint32_t length;            /* Size in bytes */
    uint32_t usage;
    uint32_t format;           /* D3DFMT_INDEX16=101, D3DFMT_INDEX32=102 */
    uint32_t pool;
} d3d9_cmd_create_index_buffer_t;

/* D3DCMD_CREATE_TEXTURE (28 bytes) */
typedef struct {
    uint32_t texture_id;
    uint32_t width;
    uint32_t height;
    uint32_t levels;
    uint32_t usage;
    uint32_t format;           /* D3DFORMAT enum (e.g. DXT1=0x31545844, DXT5=0x35545844) */
    uint32_t pool;
} d3d9_cmd_create_texture_t;

/* D3DCMD_UPDATE_TEXTURE (24 bytes + payload) */
typedef struct {
    uint32_t texture_id;
    uint32_t level;
    uint32_t pitch;
    uint32_t data_bytes;
    uint32_t width;
    uint32_t height;
    /* Followed immediately by data_bytes of raw texture pixels */
} d3d9_cmd_update_texture_t;

/* D3DCMD_DESTROY_RESOURCE (8 bytes) */
typedef struct {
    uint32_t resource_type;     /* 1=VB, 2=IB, 3=Texture, 4=Shader */
    uint32_t resource_id;
} d3d9_cmd_destroy_resource_t;

/* D3DCMD_SET_SCISSOR_RECT (16 bytes) */
typedef struct {
    int32_t left;
    int32_t top;
    int32_t right;
    int32_t bottom;
} d3d9_cmd_set_scissor_rect_t;

/* D3DCMD_SET_VS_CONSTANTS / D3DCMD_SET_PS_CONSTANTS (8 bytes + payload) */
typedef struct {
    uint32_t start_register;
    uint32_t vec4_count;        /* Followed by vec4_count * 16 bytes of floats */
} d3d9_cmd_set_constants_t;

/* --------------------------------------------------------------------------
 * Inline Ring Buffer Helper Declarations
 * -------------------------------------------------------------------------- */

static inline void d3d9_ring_init(void *buffer, uint32_t total_size) {
    if (!buffer || total_size <= D3D9_RING_HEADER_SIZE) return;
    d3d9_ring_header_t *hdr = (d3d9_ring_header_t *)buffer;
    hdr->magic = D3D9_RING_MAGIC;
    hdr->version = D3D9_RING_VERSION;
    hdr->head = 0;
    hdr->tail = 0;
    hdr->capacity = total_size - D3D9_RING_HEADER_SIZE;
    hdr->frame_index = 0;
    hdr->dropped_frames = 0;
    hdr->flags = 1; /* VSync default */
    for (int i = 0; i < 8; ++i) hdr->reserved[i] = 0;
}

static inline uint32_t d3d9_ring_available(const d3d9_ring_header_t *hdr) {
    uint32_t head = hdr->head;
    uint32_t tail = hdr->tail;
    if (head >= tail) {
        return hdr->capacity - (head - tail) - 1u;
    }
    return tail - head - 1u;
}

static inline uint32_t d3d9_ring_pending(const d3d9_ring_header_t *hdr) {
    uint32_t head = hdr->head;
    uint32_t tail = hdr->tail;
    if (head >= tail) {
        return head - tail;
    }
    return hdr->capacity - (tail - head);
}

#ifdef __cplusplus
}
#endif

#endif /* PROSTREET_D3D9_CMD_H */
