#ifndef PORTSPEED_X86_CPU_H
#define PORTSPEED_X86_CPU_H

#include <stdint.h>
#include <string.h>

typedef struct X86Cpu {
    uint32_t eax;
    uint32_t ecx;
    uint32_t edx;
    uint32_t ebx;
    uint32_t esp;
    uint32_t ebp;
    uint32_t esi;
    uint32_t edi;
    uint32_t zf;
    uint32_t cf;
    uint32_t sf;
    uint32_t of;
    uint32_t heap_ptr;
    uint8_t *mem;
    uint32_t mem_size;
} X86Cpu;

static inline uint8_t rd8(const X86Cpu *c, uint32_t addr) {
    return c->mem[addr];
}

static inline uint16_t rd16(const X86Cpu *c, uint32_t addr) {
    uint16_t v;
    memcpy(&v, &c->mem[addr], sizeof(v));
    return v;
}

static inline uint32_t rd32(const X86Cpu *c, uint32_t addr) {
    uint32_t v;
    memcpy(&v, &c->mem[addr], sizeof(v));
    return v;
}

static inline void wr8(X86Cpu *c, uint32_t addr, uint8_t val) {
    c->mem[addr] = val;
}

static inline void wr32(X86Cpu *c, uint32_t addr, uint32_t val) {
    memcpy(&c->mem[addr], &val, sizeof(val));
}

static inline uint8_t get_lo8(uint32_t r) {
    return (uint8_t)(r & 0xFFu);
}

static inline uint32_t set_lo8(uint32_t r, uint8_t v) {
    return (r & 0xFFFFFF00u) | (uint32_t)v;
}

static inline uint8_t get_hi8(uint32_t r) {
    return (uint8_t)((r >> 8) & 0xFFu);
}

static inline uint32_t set_hi8(uint32_t r, uint8_t v) {
    return (r & 0xFFFF00FFu) | ((uint32_t)v << 8);
}

static inline uint16_t get_lo16(uint32_t r) {
    return (uint16_t)(r & 0xFFFFu);
}

static inline void push32(X86Cpu *c, uint32_t val) {
    c->esp -= 4u;
    wr32(c, c->esp, val);
}

static inline uint32_t pop32(X86Cpu *c) {
    uint32_t val = rd32(c, c->esp);
    c->esp += 4u;
    return val;
}

static inline void set_logic8(X86Cpu *c, uint8_t res) {
    c->cf = 0u;
    c->of = 0u;
    c->zf = (res == 0u) ? 1u : 0u;
    c->sf = (res >> 7) & 1u;
}

static inline void set_logic32(X86Cpu *c, uint32_t res) {
    c->cf = 0u;
    c->of = 0u;
    c->zf = (res == 0u) ? 1u : 0u;
    c->sf = (res >> 31) & 1u;
}

static inline uint8_t sub8_flags(X86Cpu *c, uint8_t a, uint8_t b) {
    uint8_t res = (uint8_t)(a - b);
    c->cf = (a < b) ? 1u : 0u;
    c->zf = (res == 0u) ? 1u : 0u;
    c->sf = (res >> 7) & 1u;
    c->of = (((a ^ b) & (a ^ res)) >> 7) & 1u;
    return res;
}

static inline uint16_t sub16_flags(X86Cpu *c, uint16_t a, uint16_t b) {
    uint16_t res = (uint16_t)(a - b);
    c->cf = (a < b) ? 1u : 0u;
    c->zf = (res == 0u) ? 1u : 0u;
    c->sf = (res >> 15) & 1u;
    c->of = (((a ^ b) & (a ^ res)) >> 15) & 1u;
    return res;
}

static inline uint32_t sub32_flags(X86Cpu *c, uint32_t a, uint32_t b) {
    uint32_t res = a - b;
    c->cf = (a < b) ? 1u : 0u;
    c->zf = (res == 0u) ? 1u : 0u;
    c->sf = (res >> 31) & 1u;
    c->of = (((a ^ b) & (a ^ res)) >> 31) & 1u;
    return res;
}

static inline uint32_t sbb32_flags(X86Cpu *c, uint32_t a, uint32_t b) {
    uint64_t borrow = (uint64_t)(c->cf & 1u);
    uint64_t full = (uint64_t)a - (uint64_t)b - borrow;
    uint32_t res = (uint32_t)full;
    c->cf = ((full >> 32) != 0u) ? 1u : 0u;
    c->zf = (res == 0u) ? 1u : 0u;
    c->sf = (res >> 31) & 1u;
    c->of = (((a ^ b) & (a ^ res)) >> 31) & 1u;
    return res;
}

static inline uint32_t add32_flags(X86Cpu *c, uint32_t a, uint32_t b) {
    uint32_t res = a + b;
    c->cf = (res < a) ? 1u : 0u;
    c->zf = (res == 0u) ? 1u : 0u;
    c->sf = (res >> 31) & 1u;
    c->of = ((~(a ^ b) & (a ^ res)) >> 31) & 1u;
    return res;
}

static inline uint32_t neg32_flags(X86Cpu *c, uint32_t a) {
    uint32_t res = 0u - a;
    c->cf = (a != 0u) ? 1u : 0u;
    c->zf = (res == 0u) ? 1u : 0u;
    c->sf = (res >> 31) & 1u;
    c->of = (a == 0x80000000u) ? 1u : 0u;
    return res;
}

static inline uint32_t shl32_flags(X86Cpu *c, uint32_t v, uint32_t count) {
    uint32_t cnt = count & 0x1Fu;
    if (cnt == 0u) return v;
    uint32_t r = v << cnt;
    c->cf = (v >> (32u - cnt)) & 1u;
    c->zf = (r == 0u) ? 1u : 0u;
    c->sf = (r >> 31) & 1u;
    return r;
}

static inline uint32_t shr32_flags(X86Cpu *c, uint32_t v, uint32_t count) {
    uint32_t cnt = count & 0x1Fu;
    if (cnt == 0u) return v;
    uint32_t r = v >> cnt;
    c->cf = (v >> (cnt - 1u)) & 1u;
    c->zf = (r == 0u) ? 1u : 0u;
    c->sf = (r >> 31) & 1u;
    return r;
}

static inline void crt_memset(X86Cpu *c) {
    uint32_t dst = rd32(c, c->esp);
    uint8_t val = (uint8_t)(rd32(c, c->esp + 4u) & 0xFFu);
    uint32_t count = rd32(c, c->esp + 8u);
    memset(&c->mem[dst], val, count);
    c->eax = dst;
}

static inline void crt_memcpy(X86Cpu *c) {
    uint32_t dst = rd32(c, c->esp);
    uint32_t src = rd32(c, c->esp + 4u);
    uint32_t count = rd32(c, c->esp + 8u);
    memmove(&c->mem[dst], &c->mem[src], count);
    c->eax = dst;
}

static inline void crt_malloc(X86Cpu *c) {
    uint32_t sz = rd32(c, c->esp);
    uint32_t aligned = (c->heap_ptr + 15u) & ~15u;
    c->eax = aligned;
    c->heap_ptr = aligned + ((sz + 15u) & ~15u);
}

static inline void crt_free(X86Cpu *c) {
    (void)c;
}

static inline void crt_security_check_cookie(X86Cpu *c) {
    (void)c;
}

#endif /* PORTSPEED_X86_CPU_H */
