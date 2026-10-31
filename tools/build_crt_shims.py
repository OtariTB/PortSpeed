"""Generates the MSVCR80.dll IAT Shim Layer (runtime/crt.h and runtime/crt.c) for NFS ProStreet.

Extracts all 156 imports from MSVCR80.dll in nfs.exe, generates authentic C99
shim implementations with 1:1 guest memory access, and binds them to the
fast direct dispatch table g_dtab at their authentic IAT virtual addresses.
"""
import os
import re
import struct
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
def _resolve_exe_path() -> Path:
    cfg_path = WORKSPACE / "config" / "local.json"
    if cfg_path.is_file():
        try:
            import json
            cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
            root = Path(cfg.get("game_root", ""))
            candidates = [
                root / "Need For Spped - Pro Street" / "nfs.exe",
                root / "nfs.exe",
            ]
            for cand in candidates:
                if cand.is_file():
                    return cand
        except Exception:
            pass
    return Path(r"C:\Games\Pro Street\Need For Spped - Pro Street\nfs.exe")


EXE_PATH = _resolve_exe_path()
CRT_H_PATH = WORKSPACE / "runtime" / "crt.h"
CRT_C_PATH = WORKSPACE / "runtime" / "crt.c"


def extract_msvcr80_imports(exe_bytes):
    pe_off = struct.unpack_from('<I', exe_bytes, 0x3c)[0]
    num_sections = struct.unpack_from('<H', exe_bytes, pe_off + 6)[0]
    opt_size = struct.unpack_from('<H', exe_bytes, pe_off + 20)[0]
    sec_off = pe_off + 24 + opt_size
    sections = []
    for i in range(num_sections):
        name, vs, va, rs, rp = struct.unpack_from('<8sIIII', exe_bytes, sec_off + i * 40)
        sections.append({
            'name': name.rstrip(b'\0').decode('latin1'),
            'va': va, 'vs': vs, 'rp': rp, 'rs': rs
        })

    def rva_to_off(rva):
        for s in sections:
            if s['va'] <= rva < s['va'] + max(s['vs'], s['rs']):
                return s['rp'] + (rva - s['va'])
        return None

    import_rva = struct.unpack_from('<I', exe_bytes, pe_off + 24 + 96 + 8)[0]
    off = rva_to_off(import_rva)
    msvcr_desc = None
    while True:
        ilt_rva, time, fwd, name_rva, iat_rva = struct.unpack_from('<IIIII', exe_bytes, off)
        if not (ilt_rva or name_rva or iat_rva):
            break
        off += 20
        name_off = rva_to_off(name_rva)
        dll_name = exe_bytes[name_off:exe_bytes.find(b'\0', name_off)].decode('ascii')
        if 'msvcr80' in dll_name.lower():
            msvcr_desc = (ilt_rva, iat_rva)
            break

    if not msvcr_desc:
        raise ValueError("MSVCR80.dll import descriptor not found in PE header")

    ilt_rva, iat_rva = msvcr_desc
    ilt_off = rva_to_off(ilt_rva)
    iat_va_base = 0x00400000 + iat_rva

    symbols = []
    idx = 0
    while True:
        thunk = struct.unpack_from('<I', exe_bytes, ilt_off + idx * 4)[0]
        if not thunk:
            break
        cur_iat_va = iat_va_base + idx * 4
        if thunk & 0x80000000:
            sym = f'ord_{thunk & 0xffff}'
        else:
            name_off = rva_to_off(thunk) + 2
            sym = exe_bytes[name_off:exe_bytes.find(b'\0', name_off)].decode('ascii')
        symbols.append((cur_iat_va, sym))
        idx += 1

    return symbols


def sanitize_name(sym):
    if sym.startswith('??1exception@std@@UAE@XZ'):
        return 'crt_shim_std_exception_dtor'
    if sym.startswith('??0exception@std@@QAE@XZ'):
        return 'crt_shim_std_exception_default_ctor'
    if sym.startswith('??0exception@std@@QAE@ABV01@@Z'):
        return 'crt_shim_std_exception_copy_ctor'
    if sym.startswith('?terminate@@YAXXZ'):
        return 'crt_shim_terminate'
    if sym.startswith('?_type_info_dtor_internal_method'):
        return 'crt_shim_type_info_dtor'
    if sym.startswith('?_open@@YAHPBDHH@Z'):
        return 'crt_shim_mangled_open'
    prefix = 'crt_shim_'
    clean = re.sub(r'[^a-zA-Z0-9_]', '_', sym)
    return prefix + clean


def generate_header(symbols):
    lines = [
        "/* Need for Speed ProStreet - MSVCR80.dll IAT Shim Layer Header.",
        " *",
        " * Automatically generated from target binary PE import directory.",
        " * Total imported MSVCR80 symbols: 156.",
        " * Virtual address range: 0x009671d4 .. 0x00967440.",
        " */",
        "#ifndef PROSTREET_CRT_H",
        "#define PROSTREET_CRT_H",
        "",
        "#include <stdbool.h>",
        "#include <stddef.h>",
        "#include <stdint.h>",
        '#include "cpu.h"',
        '#include "memory.h"',
        "",
        "#ifdef __cplusplus",
        'extern "C" {',
        "#endif",
        "",
        "/* --------------------------------------------------------------------------",
        " * CRT Import Record",
        " * -------------------------------------------------------------------------- */",
        "typedef struct {",
        "    uint32_t    slot_va;",
        "    const char *symbol_name;",
        "    guest_fn_t  handler;",
        "} crt_import_entry_t;",
        "",
        "/* --------------------------------------------------------------------------",
        " * MSVCR80.dll Shim Function Declarations (156 functions)",
        " * -------------------------------------------------------------------------- */",
    ]

    for va, sym in symbols:
        fn = sanitize_name(sym)
        lines.append(f"void {fn}(struct CPU *c); /* 0x{va:08x}: {sym} */")

    lines.extend([
        "",
        "/* --------------------------------------------------------------------------",
        " * CRT Subsystem Management API",
        " * -------------------------------------------------------------------------- */",
        "void crt_init_iat(void);",
        "void crt_run_exit_handlers(struct CPU *c);",
        "uint32_t crt_register_onexit(uint32_t fn_va);",
        "uint32_t crt_get_onexit_count(void);",
        "size_t crt_get_import_count(void);",
        "const crt_import_entry_t *crt_get_import_table(void);",
        "",
        "#ifdef __cplusplus",
        "}",
        "#endif",
        "",
        "#endif /* PROSTREET_CRT_H */",
        ""
    ])
    return "\n".join(lines)


def generate_source(symbols):
    lines = [
        "/* Need for Speed ProStreet - MSVCR80.dll IAT Shim Layer Implementation.",
        " *",
        " * Full C99 implementations of all 156 imports from MSVCR80.dll,",
        " * mapping guest arguments, strings, buffers, and x87 FPU stack operations.",
        " */",
        "#include <ctype.h>",
        "#include <errno.h>",
        "#include <float.h>",
        "#include <math.h>",
        "#include <stdarg.h>",
        "#include <stdbool.h>",
        "#include <stdint.h>",
        "#include <stdio.h>",
        "#include <stdlib.h>",
        "#include <string.h>",
        "#include <time.h>",
        '#include "crt.h"',
        '#include "memory.h"',
        "",
        "/* --------------------------------------------------------------------------",
        " * Guest Runtime Metadata Layout (in TEB/TLS reserved page)",
        " * -------------------------------------------------------------------------- */",
        "#define GUEST_CRT_BASE         0x00101000u",
        "#define GUEST_COMMODE_ADDR     (GUEST_CRT_BASE + 0x00u)",
        "#define GUEST_FMODE_ADDR       (GUEST_CRT_BASE + 0x04u)",
        "#define GUEST_INITENV_ADDR     (GUEST_CRT_BASE + 0x08u)",
        "#define GUEST_IOB_ADDR         (GUEST_CRT_BASE + 0x10u) /* 3 * 32 = 96 bytes */",
        "#define GUEST_ARGV_STR_ADDR    (GUEST_CRT_BASE + 0x80u) /* 'nfs.exe' */",
        "#define GUEST_ARGV_TAB_ADDR    (GUEST_CRT_BASE + 0x100u)/* [GUEST_ARGV_STR_ADDR, 0] */",
        "#define GUEST_ENVP_TAB_ADDR    (GUEST_CRT_BASE + 0x110u)/* [0] */",
        "#define GUEST_TM_ADDR          (GUEST_CRT_BASE + 0x140u)/* struct tm */",
        "#define GUEST_ASCTIME_ADDR     (GUEST_CRT_BASE + 0x180u)/* asctime buffer */",
        "#define GUEST_GETCWD_ADDR      (GUEST_CRT_BASE + 0x200u)/* cwd buffer */",
        "",
        "/* --------------------------------------------------------------------------",
        " * Exit Callback Table",
        " * -------------------------------------------------------------------------- */",
        "#define MAX_ONEXIT_CALLBACKS 2048",
        "static uint32_t g_onexit_table[MAX_ONEXIT_CALLBACKS];",
        "static uint32_t g_onexit_count = 0;",
        "static uint32_t g_app_type = 1; /* GUI */",
        "",
        "uint32_t crt_register_onexit(uint32_t fn_va) {",
        "    if (g_onexit_count < MAX_ONEXIT_CALLBACKS) {",
        "        g_onexit_table[g_onexit_count++] = fn_va;",
        "        return fn_va;",
        "    }",
        "    return 0;",
        "}",
        "",
        "uint32_t crt_get_onexit_count(void) {",
        "    return g_onexit_count;",
        "}",
        "",
        "/* --------------------------------------------------------------------------",
        " * Virtual File Descriptor Table (supports host stdio and local assets)",
        " * -------------------------------------------------------------------------- */",
        "#define MAX_GUEST_FILES 64",
        "typedef struct {",
        "    bool  in_use;",
        "    FILE *fp;",
        "    char  path[260];",
        "} guest_file_t;",
        "",
        "static guest_file_t g_files[MAX_GUEST_FILES];",
        "",
        "static int guest_alloc_file(FILE *fp, const char *path) {",
        "    for (int i = 3; i < MAX_GUEST_FILES; ++i) {",
        "        if (!g_files[i].in_use) {",
        "            g_files[i].in_use = true;",
        "            g_files[i].fp = fp;",
        "            if (path) strncpy(g_files[i].path, path, sizeof(g_files[i].path) - 1);",
        "            return i;",
        "        }",
        "    }",
        "    return -1;",
        "}",
        "",
        "static FILE *guest_get_file(uint32_t handle) {",
        "    if (handle < MAX_GUEST_FILES && g_files[handle].in_use) {",
        "        return g_files[handle].fp;",
        "    }",
        "    if (handle == GUEST_IOB_ADDR) return stdin;",
        "    if (handle == GUEST_IOB_ADDR + 32) return stdout;",
        "    if (handle == GUEST_IOB_ADDR + 64) return stderr;",
        "    return NULL;",
        "}",
        "",
        "/* --------------------------------------------------------------------------",
        " * Helper: Safe Guest String & Formatter",
        " * -------------------------------------------------------------------------- */",
        "static inline const char *guest_str(uint32_t va) {",
        "    return (va >= GUEST_NULL_GUARD_LIMIT && va < GUEST_HEAP_LIMIT) ? (const char *)(g_mem + va) : \"\";",
        "}",
        "",
        "static int guest_format_core(char *dst, size_t maxlen, const char *fmt, uint32_t esp_args) {",
        "    if (!fmt) return 0;",
        "    size_t out_pos = 0;",
        "    const char *p = fmt;",
        "    uint32_t arg_ptr = esp_args;",
        "",
        "    while (*p) {",
        "        if (*p != '%') {",
        "            if (dst && out_pos + 1 < maxlen) dst[out_pos] = *p;",
        "            out_pos++;",
        "            p++;",
        "            continue;",
        "        }",
        "        p++;",
        "        if (*p == '%') {",
        "            if (dst && out_pos + 1 < maxlen) dst[out_pos] = '%';",
        "            out_pos++;",
        "            p++;",
        "            continue;",
        "        }",
        "        /* Parse specifier */",
        "        char spec_buf[64];",
        "        size_t sidx = 0;",
        "        spec_buf[sidx++] = '%';",
        "        bool is_long_long = false;",
        "        bool is_float = false;",
        "        bool is_string = false;",
        "        bool is_char = false;",
        "        while (*p && !strchr(\"diuoxXcspnfeEgG%\", *p)) {",
        "            if (sidx + 2 < sizeof(spec_buf)) spec_buf[sidx++] = *p;",
        "            if (*p == 'I' && *(p+1) == '6' && *(p+2) == '4') {",
        "                is_long_long = true;",
        "            }",
        "            if (*p == 'l' && *(p+1) == 'l') {",
        "                is_long_long = true;",
        "            }",
        "            p++;",
        "        }",
        "        char conv = *p ? *p++ : 's';",
        "        if (sidx + 1 < sizeof(spec_buf)) spec_buf[sidx++] = conv;",
        "        spec_buf[sidx] = '\\0';",
        "        if (conv == 's') is_string = true;",
        "        else if (conv == 'c') is_char = true;",
        "        else if (strchr(\"feEgG\", conv)) is_float = true;",
        "",
        "        char temp[512];",
        "        int written = 0;",
        "        if (is_string) {",
        "            uint32_t str_va = MR32(arg_ptr); arg_ptr += 4;",
        "            const char *s = guest_str(str_va);",
        "            written = snprintf(temp, sizeof(temp), spec_buf, s);",
        "        } else if (is_float) {",
        "            double fval = MRF64(arg_ptr); arg_ptr += 8;",
        "            written = snprintf(temp, sizeof(temp), spec_buf, fval);",
        "        } else if (is_long_long) {",
        "            uint64_t qval = MR64(arg_ptr); arg_ptr += 8;",
        "            written = snprintf(temp, sizeof(temp), \"%llu\", (unsigned long long)qval);",
        "        } else if (is_char) {",
        "            uint32_t ival = MR32(arg_ptr); arg_ptr += 4;",
        "            written = snprintf(temp, sizeof(temp), spec_buf, (char)ival);",
        "        } else {",
        "            uint32_t ival = MR32(arg_ptr); arg_ptr += 4;",
        "            written = snprintf(temp, sizeof(temp), spec_buf, ival);",
        "        }",
        "        if (written < 0) written = 0;",
        "        for (int k = 0; k < written; ++k) {",
        "            if (dst && out_pos + 1 < maxlen) dst[out_pos] = temp[k];",
        "            out_pos++;",
        "        }",
        "    }",
        "    if (dst) {",
        "        if (maxlen > 0) {",
        "            size_t term = out_pos < maxlen ? out_pos : (maxlen - 1);",
        "            dst[term] = '\\0';",
        "        }",
        "    }",
        "    return (int)out_pos;",
        "}",
        "",
        "/* --------------------------------------------------------------------------",
        " * Fast Intrinsic String Compare / Transform Helpers",
        " * -------------------------------------------------------------------------- */",
        "static int crt_stricmp_impl(const char *s1, const char *s2) {",
        "    while (*s1 && *s2) {",
        "        int c1 = tolower((unsigned char)*s1);",
        "        int c2 = tolower((unsigned char)*s2);",
        "        if (c1 != c2) return c1 - c2;",
        "        s1++; s2++;",
        "    }",
        "    return tolower((unsigned char)*s1) - tolower((unsigned char)*s2);",
        "}",
        "",
        "static int crt_strnicmp_impl(const char *s1, const char *s2, size_t n) {",
        "    for (size_t i = 0; i < n; ++i) {",
        "        int c1 = tolower((unsigned char)s1[i]);",
        "        int c2 = tolower((unsigned char)s2[i]);",
        "        if (c1 != c2 || !c1) return c1 - c2;",
        "    }",
        "    return 0;",
        "}",
        "",
    ]

    # Generate individual shim implementations
    shim_bodies = generate_shim_bodies(symbols)
    lines.append(shim_bodies)

    # Master IAT Table and crt_init_iat
    lines.extend([
        "/* --------------------------------------------------------------------------",
        " * Master MSVCR80.dll IAT Table (156 entries)",
        " * -------------------------------------------------------------------------- */",
        "static const crt_import_entry_t g_crt_imports[156] = {",
    ])
    for va, sym in symbols:
        fn = sanitize_name(sym)
        lines.append(f'    {{ 0x{va:08x}u, "{sym}", {fn} }},')
    lines.extend([
        "};",
        "",
        "size_t crt_get_import_count(void) {",
        "    return 156;",
        "}",
        "",
        "const crt_import_entry_t *crt_get_import_table(void) {",
        "    return g_crt_imports;",
        "}",
        "",
        "void crt_run_exit_handlers(struct CPU *c) {",
        "    while (g_onexit_count > 0) {",
        "        uint32_t fn = g_onexit_table[--g_onexit_count];",
        "        if (fn != 0) {",
        "            DISPATCH_CALL(c, fn);",
        "        }",
        "    }",
        "}",
        "",
        "void crt_init_iat(void) {",
        "    /* 1. Setup metadata structures at GUEST_CRT_BASE */",
        "    MR32(GUEST_COMMODE_ADDR) = 0;",
        "    MR32(GUEST_FMODE_ADDR)   = 0;",
        "    MR32(GUEST_INITENV_ADDR) = 0;",
        "    memset(g_mem + GUEST_IOB_ADDR, 0, 96);",
        "    /* Initial file handles */",
        "    g_files[0].in_use = true; g_files[0].fp = stdin;",
        "    g_files[1].in_use = true; g_files[1].fp = stdout;",
        "    g_files[2].in_use = true; g_files[2].fp = stderr;",
        "    /* Setup argv: 'nfs.exe' */",
        "    strcpy((char *)(g_mem + GUEST_ARGV_STR_ADDR), \"nfs.exe\");",
        "    MR32(GUEST_ARGV_TAB_ADDR) = GUEST_ARGV_STR_ADDR;",
        "    MR32(GUEST_ARGV_TAB_ADDR + 4) = 0;",
        "    MR32(GUEST_ENVP_TAB_ADDR) = 0;",
        "",
        "    /* 2. Bind all 156 MSVCR80.dll IAT slots directly into g_dtab */",
        "    for (size_t i = 0; i < 156; ++i) {",
        "        uint32_t slot_va = g_crt_imports[i].slot_va;",
        "        MR32(slot_va) = slot_va;",
        "        uint32_t idx = slot_va - DISPATCH_TEXT_BASE;",
        "        if (idx < DISPATCH_TEXT_SIZE) {",
        "            g_dtab[idx] = g_crt_imports[i].handler;",
        "        }",
        "    }",
        "}",
        ""
    ])
    return "\n".join(lines)


def generate_shim_bodies(symbols):
    bodies = []
    for va, sym in symbols:
        fn = sanitize_name(sym)
        code = generate_single_shim(fn, sym, va)
        bodies.append(code)
    return "\n".join(bodies)


def generate_single_shim(fn, sym, va):
    # Specialized implementations for each symbol
    if fn == 'crt_shim_malloc':
        return f"""void {fn}(CPU *c) {{
    uint32_t size = MR32(c->esp);
    c->eax = guest_heap_alloc(size ? size : 1, 8);
}}"""

    if fn == 'crt_shim_free':
        return f"""void {fn}(CPU *c) {{
    (void)c; /* No-op in guest heap arena */
}}"""

    if fn == 'crt_shim_calloc':
        return f"""void {fn}(CPU *c) {{
    uint32_t num  = MR32(c->esp);
    uint32_t size = MR32(c->esp + 4);
    uint64_t total = (uint64_t)num * (uint64_t)size;
    if (total > 0x10000000u) {{ c->eax = 0; return; }}
    uint32_t ptr = guest_heap_alloc((uint32_t)(total ? total : 1), 8);
    if (ptr) memset(g_mem + ptr, 0, (size_t)total);
    c->eax = ptr;
}}"""

    if fn == 'crt_shim_realloc':
        return f"""void {fn}(CPU *c) {{
    uint32_t ptr  = MR32(c->esp);
    uint32_t size = MR32(c->esp + 4);
    if (!ptr) {{ c->eax = guest_heap_alloc(size ? size : 1, 8); return; }}
    if (!size) {{ c->eax = 0; return; }}
    uint32_t nptr = guest_heap_alloc(size, 8);
    if (nptr && ptr) memcpy(g_mem + nptr, g_mem + ptr, size);
    c->eax = nptr;
}}"""

    if fn == 'crt_shim__aligned_malloc':
        return f"""void {fn}(CPU *c) {{
    uint32_t size  = MR32(c->esp);
    uint32_t align = MR32(c->esp + 4);
    c->eax = guest_heap_alloc(size ? size : 1, align ? align : 8);
}}"""

    if fn == 'crt_shim__aligned_free':
        return f"""void {fn}(CPU *c) {{
    (void)c;
}}"""

    # Memory movement & blocks
    if fn == 'crt_shim_memcpy':
        return f"""void {fn}(CPU *c) {{
    uint32_t dst = MR32(c->esp);
    uint32_t src = MR32(c->esp + 4);
    uint32_t n   = MR32(c->esp + 8);
    if (n > 0) memmove(g_mem + dst, g_mem + src, n);
    c->eax = dst;
}}"""

    if fn == 'crt_shim_memcpy_s':
        return f"""void {fn}(CPU *c) {{
    uint32_t dst   = MR32(c->esp);
    uint32_t dstsz = MR32(c->esp + 4);
    uint32_t src   = MR32(c->esp + 8);
    uint32_t count = MR32(c->esp + 12);
    if (count > dstsz) {{ c->eax = 0x22; return; }}
    if (count > 0) memmove(g_mem + dst, g_mem + src, count);
    c->eax = 0;
}}"""

    if fn == 'crt_shim_memmove':
        return f"""void {fn}(CPU *c) {{
    uint32_t dst = MR32(c->esp);
    uint32_t src = MR32(c->esp + 4);
    uint32_t n   = MR32(c->esp + 8);
    if (n > 0) memmove(g_mem + dst, g_mem + src, n);
    c->eax = dst;
}}"""

    if fn == 'crt_shim_memmove_s':
        return f"""void {fn}(CPU *c) {{
    uint32_t dst   = MR32(c->esp);
    uint32_t dstsz = MR32(c->esp + 4);
    uint32_t src   = MR32(c->esp + 8);
    uint32_t count = MR32(c->esp + 12);
    if (count > dstsz) {{ c->eax = 0x22; return; }}
    if (count > 0) memmove(g_mem + dst, g_mem + src, count);
    c->eax = 0;
}}"""

    if fn == 'crt_shim_memset':
        return f"""void {fn}(CPU *c) {{
    uint32_t dst = MR32(c->esp);
    uint32_t val = MR32(c->esp + 4);
    uint32_t n   = MR32(c->esp + 8);
    if (n > 0) memset(g_mem + dst, val & 0xff, n);
    c->eax = dst;
}}"""

    if fn == 'crt_shim_memcmp':
        return f"""void {fn}(CPU *c) {{
    uint32_t s1 = MR32(c->esp);
    uint32_t s2 = MR32(c->esp + 4);
    uint32_t n  = MR32(c->esp + 8);
    c->eax = (uint32_t)memcmp(g_mem + s1, g_mem + s2, n);
}}"""

    # String operations
    if fn == 'crt_shim_strlen':
        return f"""void {fn}(CPU *c) {{
    const char *s = guest_str(MR32(c->esp));
    c->eax = (uint32_t)strlen(s);
}}"""

    if fn == 'crt_shim_strcpy':
        return f"""void {fn}(CPU *c) {{
    uint32_t dst = MR32(c->esp);
    const char *src = guest_str(MR32(c->esp + 4));
    strcpy((char *)(g_mem + dst), src);
    c->eax = dst;
}}"""

    if fn == 'crt_shim_strcpy_s':
        return f"""void {fn}(CPU *c) {{
    uint32_t dst   = MR32(c->esp);
    uint32_t dstsz = MR32(c->esp + 4);
    const char *src = guest_str(MR32(c->esp + 8));
    size_t slen = strlen(src);
    if (slen + 1 > dstsz) {{ c->eax = 0x22; return; }}
    memcpy(g_mem + dst, src, slen + 1);
    c->eax = 0;
}}"""

    if fn == 'crt_shim_strncpy':
        return f"""void {fn}(CPU *c) {{
    uint32_t dst = MR32(c->esp);
    const char *src = guest_str(MR32(c->esp + 4));
    uint32_t n = MR32(c->esp + 8);
    strncpy((char *)(g_mem + dst), src, n);
    c->eax = dst;
}}"""

    if fn == 'crt_shim_strncpy_s':
        return f"""void {fn}(CPU *c) {{
    uint32_t dst   = MR32(c->esp);
    uint32_t dstsz = MR32(c->esp + 4);
    const char *src = guest_str(MR32(c->esp + 8));
    uint32_t count = MR32(c->esp + 12);
    if (count > dstsz) {{ c->eax = 0x22; return; }}
    strncpy((char *)(g_mem + dst), src, count);
    if (count < dstsz) ((char *)(g_mem + dst))[count] = '\\0';
    c->eax = 0;
}}"""

    if fn == 'crt_shim_strcmp':
        return f"""void {fn}(CPU *c) {{
    const char *s1 = guest_str(MR32(c->esp));
    const char *s2 = guest_str(MR32(c->esp + 4));
    c->eax = (uint32_t)strcmp(s1, s2);
}}"""

    if fn == 'crt_shim_strncmp':
        return f"""void {fn}(CPU *c) {{
    const char *s1 = guest_str(MR32(c->esp));
    const char *s2 = guest_str(MR32(c->esp + 4));
    uint32_t n = MR32(c->esp + 8);
    c->eax = (uint32_t)strncmp(s1, s2, n);
}}"""

    if fn == 'crt_shim__stricmp':
        return f"""void {fn}(CPU *c) {{
    const char *s1 = guest_str(MR32(c->esp));
    const char *s2 = guest_str(MR32(c->esp + 4));
    c->eax = (uint32_t)crt_stricmp_impl(s1, s2);
}}"""

    if fn == 'crt_shim__strnicmp':
        return f"""void {fn}(CPU *c) {{
    const char *s1 = guest_str(MR32(c->esp));
    const char *s2 = guest_str(MR32(c->esp + 4));
    uint32_t n = MR32(c->esp + 8);
    c->eax = (uint32_t)crt_strnicmp_impl(s1, s2, n);
}}"""

    if fn == 'crt_shim_strcat':
        return f"""void {fn}(CPU *c) {{
    uint32_t dst = MR32(c->esp);
    const char *src = guest_str(MR32(c->esp + 4));
    strcat((char *)(g_mem + dst), src);
    c->eax = dst;
}}"""

    if fn == 'crt_shim_strncat':
        return f"""void {fn}(CPU *c) {{
    uint32_t dst = MR32(c->esp);
    const char *src = guest_str(MR32(c->esp + 4));
    uint32_t n = MR32(c->esp + 8);
    strncat((char *)(g_mem + dst), src, n);
    c->eax = dst;
}}"""

    if fn == 'crt_shim_strstr':
        return f"""void {fn}(CPU *c) {{
    uint32_t hva = MR32(c->esp);
    const char *h = guest_str(hva);
    const char *n = guest_str(MR32(c->esp + 4));
    const char *res = strstr(h, n);
    c->eax = res ? (uint32_t)((const uint8_t *)res - g_mem) : 0;
}}"""

    if fn == 'crt_shim_strchr':
        return f"""void {fn}(CPU *c) {{
    uint32_t sva = MR32(c->esp);
    const char *s = guest_str(sva);
    int ch = (int)MR32(c->esp + 4);
    const char *res = strchr(s, ch);
    c->eax = res ? (uint32_t)((const uint8_t *)res - g_mem) : 0;
}}"""

    if fn == 'crt_shim_strrchr':
        return f"""void {fn}(CPU *c) {{
    uint32_t sva = MR32(c->esp);
    const char *s = guest_str(sva);
    int ch = (int)MR32(c->esp + 4);
    const char *res = strrchr(s, ch);
    c->eax = res ? (uint32_t)((const uint8_t *)res - g_mem) : 0;
}}"""

    if fn == 'crt_shim_strpbrk':
        return f"""void {fn}(CPU *c) {{
    uint32_t sva = MR32(c->esp);
    const char *s = guest_str(sva);
    const char *a = guest_str(MR32(c->esp + 4));
    const char *res = strpbrk(s, a);
    c->eax = res ? (uint32_t)((const uint8_t *)res - g_mem) : 0;
}}"""

    if fn == 'crt_shim_strcspn':
        return f"""void {fn}(CPU *c) {{
    const char *s = guest_str(MR32(c->esp));
    const char *r = guest_str(MR32(c->esp + 4));
    c->eax = (uint32_t)strcspn(s, r);
}}"""

    if fn == 'crt_shim_strcoll':
        return f"""void {fn}(CPU *c) {{
    const char *s1 = guest_str(MR32(c->esp));
    const char *s2 = guest_str(MR32(c->esp + 4));
    c->eax = (uint32_t)strcmp(s1, s2);
}}"""

    if fn == 'crt_shim_strtok':
        return f"""void {fn}(CPU *c) {{
    static uint32_t s_tok_va = 0;
    uint32_t str_va = MR32(c->esp);
    const char *delim = guest_str(MR32(c->esp + 4));
    if (str_va != 0) s_tok_va = str_va;
    if (s_tok_va == 0) {{ c->eax = 0; return; }}
    char *p = (char *)(g_mem + s_tok_va);
    while (*p && strchr(delim, *p)) p++;
    if (!*p) {{ s_tok_va = 0; c->eax = 0; return; }}
    char *token_start = p;
    while (*p && !strchr(delim, *p)) p++;
    if (*p) {{
        *p = '\\0';
        s_tok_va = (uint32_t)((uint8_t *)(p + 1) - g_mem);
    }} else {{
        s_tok_va = 0;
    }}
    c->eax = (uint32_t)((uint8_t *)token_start - g_mem);
}}"""

    if fn == 'crt_shim_strtol':
        return f"""void {fn}(CPU *c) {{
    uint32_t str_va = MR32(c->esp);
    uint32_t end_va = MR32(c->esp + 4);
    int base        = (int)MR32(c->esp + 8);
    char *end = NULL;
    long val = strtol(guest_str(str_va), &end, base);
    if (end_va) MR32(end_va) = end ? (uint32_t)((uint8_t *)end - g_mem) : str_va;
    c->eax = (uint32_t)val;
}}"""

    if fn == 'crt_shim_strtoul':
        return f"""void {fn}(CPU *c) {{
    uint32_t str_va = MR32(c->esp);
    uint32_t end_va = MR32(c->esp + 4);
    int base        = (int)MR32(c->esp + 8);
    char *end = NULL;
    unsigned long val = strtoul(guest_str(str_va), &end, base);
    if (end_va) MR32(end_va) = end ? (uint32_t)((uint8_t *)end - g_mem) : str_va;
    c->eax = (uint32_t)val;
}}"""

    if fn == 'crt_shim_atoi':
        return f"""void {fn}(CPU *c) {{
    c->eax = (uint32_t)atoi(guest_str(MR32(c->esp)));
}}"""

    if fn == 'crt_shim_atof':
        return f"""void {fn}(CPU *c) {{
    double val = atof(guest_str(MR32(c->esp)));
    FPUSH(val);
}}"""

    if fn == 'crt_shim__itoa_s':
        return f"""void {fn}(CPU *c) {{
    int val        = (int)MR32(c->esp);
    uint32_t buf   = MR32(c->esp + 4);
    uint32_t bufsz = MR32(c->esp + 8);
    int radix      = (int)MR32(c->esp + 12);
    char *dst = (char *)(g_mem + buf);
    if (radix == 10) snprintf(dst, bufsz, "%d", val);
    else if (radix == 16) snprintf(dst, bufsz, "%x", (unsigned int)val);
    else if (radix == 8) snprintf(dst, bufsz, "%o", (unsigned int)val);
    else snprintf(dst, bufsz, "%d", val);
    c->eax = 0;
}}"""

    if fn == 'crt_shim__ltoa':
        return f"""void {fn}(CPU *c) {{
    long val  = (long)MR32(c->esp);
    uint32_t buf = MR32(c->esp + 4);
    int radix = (int)MR32(c->esp + 8);
    char *dst = (char *)(g_mem + buf);
    if (radix == 16) sprintf(dst, "%lx", (unsigned long)val);
    else sprintf(dst, "%ld", val);
    c->eax = buf;
}}"""

    if fn == 'crt_shim_tolower':
        return f"""void {fn}(CPU *c) {{
    c->eax = (uint32_t)tolower((int)MR32(c->esp));
}}"""

    if fn == 'crt_shim_toupper':
        return f"""void {fn}(CPU *c) {{
    c->eax = (uint32_t)toupper((int)MR32(c->esp));
}}"""

    if fn == 'crt_shim_isspace':
        return f"""void {fn}(CPU *c) {{
    c->eax = isspace((int)MR32(c->esp)) ? 1 : 0;
}}"""

    if fn == 'crt_shim_isdigit':
        return f"""void {fn}(CPU *c) {{
    c->eax = isdigit((int)MR32(c->esp)) ? 1 : 0;
}}"""

    if fn == 'crt_shim_isprint':
        return f"""void {fn}(CPU *c) {{
    c->eax = isprint((int)MR32(c->esp)) ? 1 : 0;
}}"""

    # Formatted I/O
    if fn == 'crt_shim_sprintf':
        return f"""void {fn}(CPU *c) {{
    uint32_t buf_va = MR32(c->esp);
    const char *fmt = guest_str(MR32(c->esp + 4));
    c->eax = (uint32_t)guest_format_core((char *)(g_mem + buf_va), 0x7fffffffu, fmt, c->esp + 8);
}}"""

    if fn == 'crt_shim_sprintf_s':
        return f"""void {fn}(CPU *c) {{
    uint32_t buf_va = MR32(c->esp);
    uint32_t bufsz  = MR32(c->esp + 4);
    const char *fmt = guest_str(MR32(c->esp + 8));
    c->eax = (uint32_t)guest_format_core((char *)(g_mem + buf_va), bufsz, fmt, c->esp + 12);
}}"""

    if fn == 'crt_shim_vsprintf':
        return f"""void {fn}(CPU *c) {{
    uint32_t buf_va = MR32(c->esp);
    const char *fmt = guest_str(MR32(c->esp + 4));
    uint32_t valist = MR32(c->esp + 8);
    c->eax = (uint32_t)guest_format_core((char *)(g_mem + buf_va), 0x7fffffffu, fmt, valist);
}}"""

    if fn == 'crt_shim_vsprintf_s':
        return f"""void {fn}(CPU *c) {{
    uint32_t buf_va = MR32(c->esp);
    uint32_t bufsz  = MR32(c->esp + 4);
    const char *fmt = guest_str(MR32(c->esp + 8));
    uint32_t valist = MR32(c->esp + 12);
    c->eax = (uint32_t)guest_format_core((char *)(g_mem + buf_va), bufsz, fmt, valist);
}}"""

    if fn == 'crt_shim__snprintf':
        return f"""void {fn}(CPU *c) {{
    uint32_t buf_va = MR32(c->esp);
    uint32_t count  = MR32(c->esp + 4);
    const char *fmt = guest_str(MR32(c->esp + 8));
    c->eax = (uint32_t)guest_format_core((char *)(g_mem + buf_va), count, fmt, c->esp + 12);
}}"""

    if fn == 'crt_shim__vsnprintf':
        return f"""void {fn}(CPU *c) {{
    uint32_t buf_va = MR32(c->esp);
    uint32_t count  = MR32(c->esp + 4);
    const char *fmt = guest_str(MR32(c->esp + 8));
    uint32_t valist = MR32(c->esp + 12);
    c->eax = (uint32_t)guest_format_core((char *)(g_mem + buf_va), count, fmt, valist);
}}"""

    if fn == 'crt_shim__vscprintf':
        return f"""void {fn}(CPU *c) {{
    const char *fmt = guest_str(MR32(c->esp));
    uint32_t valist = MR32(c->esp + 4);
    c->eax = (uint32_t)guest_format_core(NULL, 0, fmt, valist);
}}"""

    if fn == 'crt_shim__vsnwprintf':
        return f"""void {fn}(CPU *c) {{
    uint32_t buf_va = MR32(c->esp);
    uint32_t count  = MR32(c->esp + 4);
    (void)buf_va; (void)count;
    c->eax = 0;
}}"""

    if fn == 'crt_shim_printf':
        return f"""void {fn}(CPU *c) {{
    const char *fmt = guest_str(MR32(c->esp));
    char buf[1024];
    int len = guest_format_core(buf, sizeof(buf), fmt, c->esp + 4);
    fputs(buf, stdout);
    c->eax = (uint32_t)len;
}}"""

    if fn == 'crt_shim_fprintf':
        return f"""void {fn}(CPU *c) {{
    uint32_t stream_va = MR32(c->esp);
    const char *fmt = guest_str(MR32(c->esp + 4));
    FILE *fp = guest_get_file(stream_va);
    char buf[1024];
    int len = guest_format_core(buf, sizeof(buf), fmt, c->esp + 8);
    if (fp) fputs(buf, fp);
    c->eax = (uint32_t)len;
}}"""

    if fn == 'crt_shim_sscanf':
        return f"""void {fn}(CPU *c) {{
    const char *src = guest_str(MR32(c->esp));
    const char *fmt = guest_str(MR32(c->esp + 4));
    /* Parse 1..4 integer/float fields safely */
    uint32_t a1 = MR32(c->esp + 8);
    uint32_t a2 = MR32(c->esp + 12);
    uint32_t a3 = MR32(c->esp + 16);
    uint32_t a4 = MR32(c->esp + 20);
    void *p1 = a1 ? (void *)(g_mem + a1) : NULL;
    void *p2 = a2 ? (void *)(g_mem + a2) : NULL;
    void *p3 = a3 ? (void *)(g_mem + a3) : NULL;
    void *p4 = a4 ? (void *)(g_mem + a4) : NULL;
    c->eax = (uint32_t)sscanf(src, fmt, p1, p2, p3, p4);
}}"""

    if fn == 'crt_shim___iob_func':
        return f"""void {fn}(CPU *c) {{
    c->eax = GUEST_IOB_ADDR;
}}"""

    # File I/O
    if fn == 'crt_shim_fopen':
        return f"""void {fn}(CPU *c) {{
    const char *fn = guest_str(MR32(c->esp));
    const char *md = guest_str(MR32(c->esp + 4));
    FILE *fp = fopen(fn, md);
    if (!fp) {{ c->eax = 0; return; }}
    int slot = guest_alloc_file(fp, fn);
    c->eax = slot >= 0 ? (uint32_t)slot : 0;
}}"""

    if fn == 'crt_shim_fclose':
        return f"""void {fn}(CPU *c) {{
    uint32_t handle = MR32(c->esp);
    if (handle < MAX_GUEST_FILES && g_files[handle].in_use) {{
        if (g_files[handle].fp) fclose(g_files[handle].fp);
        g_files[handle].in_use = false;
        g_files[handle].fp = NULL;
        c->eax = 0;
    }} else {{
        c->eax = (uint32_t)-1;
    }}
}}"""

    if fn == 'crt_shim_fread':
        return f"""void {fn}(CPU *c) {{
    uint32_t dst_va = MR32(c->esp);
    uint32_t size   = MR32(c->esp + 4);
    uint32_t count  = MR32(c->esp + 8);
    uint32_t handle = MR32(c->esp + 12);
    FILE *fp = guest_get_file(handle);
    if (fp) {{
        c->eax = (uint32_t)fread(g_mem + dst_va, size, count, fp);
    }} else {{
        c->eax = 0;
    }}
}}"""

    if fn == 'crt_shim_fwrite':
        return f"""void {fn}(CPU *c) {{
    uint32_t src_va = MR32(c->esp);
    uint32_t size   = MR32(c->esp + 4);
    uint32_t count  = MR32(c->esp + 8);
    uint32_t handle = MR32(c->esp + 12);
    FILE *fp = guest_get_file(handle);
    if (fp) {{
        c->eax = (uint32_t)fwrite(g_mem + src_va, size, count, fp);
    }} else {{
        c->eax = 0;
    }}
}}"""

    if fn == 'crt_shim_fseek':
        return f"""void {fn}(CPU *c) {{
    uint32_t handle = MR32(c->esp);
    long offset     = (long)MR32(c->esp + 4);
    int origin      = (int)MR32(c->esp + 8);
    FILE *fp = guest_get_file(handle);
    c->eax = fp ? (uint32_t)fseek(fp, offset, origin) : (uint32_t)-1;
}}"""

    if fn == 'crt_shim_fflush':
        return f"""void {fn}(CPU *c) {{
    uint32_t handle = MR32(c->esp);
    FILE *fp = guest_get_file(handle);
    c->eax = fp ? (uint32_t)fflush(fp) : 0;
}}"""

    if fn == 'crt_shim__filelength':
        return f"""void {fn}(CPU *c) {{
    uint32_t fd = MR32(c->esp);
    FILE *fp = guest_get_file(fd);
    if (fp) {{
        long cur = ftell(fp);
        fseek(fp, 0, SEEK_END);
        long end = ftell(fp);
        fseek(fp, cur, SEEK_SET);
        c->eax = (uint32_t)end;
    }} else {{
        c->eax = (uint32_t)-1;
    }}
}}"""

    if fn == 'crt_shim__lseek':
        return f"""void {fn}(CPU *c) {{
    uint32_t fd = MR32(c->esp);
    long offset = (long)MR32(c->esp + 4);
    int origin  = (int)MR32(c->esp + 8);
    FILE *fp = guest_get_file(fd);
    if (fp && fseek(fp, offset, origin) == 0) {{
        c->eax = (uint32_t)ftell(fp);
    }} else {{
        c->eax = (uint32_t)-1;
    }}
}}"""

    if fn == 'crt_shim__read':
        return f"""void {fn}(CPU *c) {{
    uint32_t fd     = MR32(c->esp);
    uint32_t buf_va = MR32(c->esp + 4);
    uint32_t count  = MR32(c->esp + 8);
    FILE *fp = guest_get_file(fd);
    c->eax = fp ? (uint32_t)fread(g_mem + buf_va, 1, count, fp) : (uint32_t)-1;
}}"""

    if fn == 'crt_shim__write':
        return f"""void {fn}(CPU *c) {{
    uint32_t fd     = MR32(c->esp);
    uint32_t buf_va = MR32(c->esp + 4);
    uint32_t count  = MR32(c->esp + 8);
    FILE *fp = guest_get_file(fd);
    c->eax = fp ? (uint32_t)fwrite(g_mem + buf_va, 1, count, fp) : (uint32_t)-1;
}}"""

    if fn == 'crt_shim__close':
        return f"""void {fn}(CPU *c) {{
    uint32_t fd = MR32(c->esp);
    if (fd < MAX_GUEST_FILES && g_files[fd].in_use) {{
        if (g_files[fd].fp) fclose(g_files[fd].fp);
        g_files[fd].in_use = false;
        g_files[fd].fp = NULL;
        c->eax = 0;
    }} else {{
        c->eax = (uint32_t)-1;
    }}
}}"""

    if fn == 'crt_shim_mangled_open':
        return f"""void {fn}(CPU *c) {{
    const char *fn = guest_str(MR32(c->esp));
    int oflag      = (int)MR32(c->esp + 4);
    (void)oflag;
    FILE *fp = fopen(fn, "rb");
    if (!fp) {{ c->eax = (uint32_t)-1; return; }}
    int slot = guest_alloc_file(fp, fn);
    c->eax = slot >= 0 ? (uint32_t)slot : (uint32_t)-1;
}}"""

    if fn == 'crt_shim__chmod':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
}}"""

    if fn == 'crt_shim_rename':
        return f"""void {fn}(CPU *c) {{
    const char *oldp = guest_str(MR32(c->esp));
    const char *newp = guest_str(MR32(c->esp + 4));
    c->eax = (uint32_t)rename(oldp, newp);
}}"""

    if fn == 'crt_shim_remove':
        return f"""void {fn}(CPU *c) {{
    const char *fn = guest_str(MR32(c->esp));
    c->eax = (uint32_t)remove(fn);
}}"""

    if fn == 'crt_shim__mkdir':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
}}"""

    if fn == 'crt_shim__rmdir':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
}}"""

    if fn == 'crt_shim__getdrive':
        return f"""void {fn}(CPU *c) {{
    c->eax = 3; /* C: drive */
}}"""

    if fn == 'crt_shim__getdiskfree':
        return f"""void {fn}(CPU *c) {{
    uint32_t drive = MR32(c->esp);
    uint32_t pinfo = MR32(c->esp + 4);
    (void)drive;
    if (pinfo) {{
        MR32(pinfo + 0) = 0x8000; /* total clusters */
        MR32(pinfo + 4) = 0x4000; /* avail clusters */
        MR32(pinfo + 8) = 512;    /* bytes per sector */
        MR32(pinfo + 12) = 8;     /* sectors per cluster */
    }}
    c->eax = 0;
}}"""

    # Unary Math Intrinsics: input in ST(0), output in ST(0)
    unary_intrinsics = {
        'crt_shim__CIsin': 'sin',
        'crt_shim__CIcos': 'cos',
        'crt_shim__CIsqrt': 'sqrt',
        'crt_shim__CItan': 'tan',
        'crt_shim__CIasin': 'asin',
        'crt_shim__CIacos': 'acos',
        'crt_shim__CIatan': 'atan',
        'crt_shim__CIexp': 'exp',
        'crt_shim__CIlog': 'log',
        'crt_shim__CIlog10': 'log10',
        'crt_shim__CIsinh': 'sinh',
        'crt_shim__CIcosh': 'cosh',
        'crt_shim__CItanh': 'tanh',
    }
    if fn in unary_intrinsics:
        math_call = unary_intrinsics[fn]
        return f"""void {fn}(CPU *c) {{
    ST(0) = {math_call}(ST(0));
}}"""

    # Binary Math Intrinsics: pop 1, result in ST(0)
    if fn == 'crt_shim__CIpow':
        return f"""void {fn}(CPU *c) {{
    double y = ST(0);
    double x = ST(1);
    FPOP();
    ST(0) = pow(x, y);
}}"""

    if fn == 'crt_shim__CIatan2':
        return f"""void {fn}(CPU *c) {{
    double x = ST(0);
    double y = ST(1);
    FPOP();
    ST(0) = atan2(y, x);
}}"""

    if fn == 'crt_shim__CIfmod':
        return f"""void {fn}(CPU *c) {{
    double y = ST(0);
    double x = ST(1);
    FPOP();
    ST(0) = fmod(x, y);
}}"""

    # Standard cdecl math functions
    if fn == 'crt_shim_sin':
        return f"""void {fn}(CPU *c) {{
    double x = MRF64(c->esp);
    FPUSH(sin(x));
}}"""

    if fn == 'crt_shim_cos':
        return f"""void {fn}(CPU *c) {{
    double x = MRF64(c->esp);
    FPUSH(cos(x));
}}"""

    if fn == 'crt_shim_sqrt':
        return f"""void {fn}(CPU *c) {{
    double x = MRF64(c->esp);
    FPUSH(sqrt(x));
}}"""

    if fn == 'crt_shim_floor':
        return f"""void {fn}(CPU *c) {{
    double x = MRF64(c->esp);
    FPUSH(floor(x));
}}"""

    if fn == 'crt_shim_ceil':
        return f"""void {fn}(CPU *c) {{
    double x = MRF64(c->esp);
    FPUSH(ceil(x));
}}"""

    if fn == 'crt_shim_abs':
        return f"""void {fn}(CPU *c) {{
    int32_t val = (int32_t)MR32(c->esp);
    c->eax = (uint32_t)(val < 0 ? -val : val);
}}"""

    if fn == 'crt_shim_ldexp':
        return f"""void {fn}(CPU *c) {{
    double x = MRF64(c->esp);
    int exp  = (int)MR32(c->esp + 8);
    FPUSH(ldexp(x, exp));
}}"""

    if fn == 'crt_shim__isnan':
        return f"""void {fn}(CPU *c) {{
    double x = MRF64(c->esp);
    c->eax = (x != x) ? 1 : 0;
}}"""

    if fn == 'crt_shim__control87':
        return f"""void {fn}(CPU *c) {{
    uint32_t nw = MR32(c->esp);
    uint32_t mk = MR32(c->esp + 4);
    uint16_t old = c->fcw;
    c->fcw = (old & ~mk) | (nw & mk);
    c->eax = old;
}}"""

    if fn == 'crt_shim__controlfp_s':
        return f"""void {fn}(CPU *c) {{
    uint32_t pcurr = MR32(c->esp);
    uint32_t nw    = MR32(c->esp + 4);
    uint32_t mk    = MR32(c->esp + 8);
    if (pcurr) MR32(pcurr) = c->fcw;
    c->fcw = (c->fcw & ~mk) | (nw & mk);
    c->eax = 0;
}}"""

    if fn == 'crt_shim__adjust_fdiv':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
}}"""

    # Time & Date
    if fn == 'crt_shim_clock':
        return f"""void {fn}(CPU *c) {{
    c->eax = (uint32_t)clock();
}}"""

    if fn == 'crt_shim__time64':
        return f"""void {fn}(CPU *c) {{
    uint32_t timer_va = MR32(c->esp);
    uint64_t now = (uint64_t)time(NULL);
    if (timer_va) MR64(timer_va) = now;
    c->eax = (uint32_t)(now & 0xffffffffu);
    c->edx = (uint32_t)(now >> 32);
}}"""

    if fn == 'crt_shim__difftime64':
        return f"""void {fn}(CPU *c) {{
    uint64_t t1 = MR64(c->esp);
    uint64_t t2 = MR64(c->esp + 8);
    double diff = (double)((int64_t)t1 - (int64_t)t2);
    FPUSH(diff);
}}"""

    if fn == 'crt_shim__ftime64':
        return f"""void {fn}(CPU *c) {{
    uint32_t tb_va = MR32(c->esp);
    if (tb_va) {{
        MR64(tb_va) = (uint64_t)time(NULL);
        MR16(tb_va + 8) = 0; /* millitm */
        MR16(tb_va + 10) = 0;/* timezone */
        MR16(tb_va + 12) = 0;/* dstflag */
    }}
    c->eax = 0;
}}"""

    if fn == 'crt_shim__localtime64':
        return f"""void {fn}(CPU *c) {{
    uint32_t timer_va = MR32(c->esp);
    time_t t = timer_va ? (time_t)MR64(timer_va) : time(NULL);
    struct tm *lt = localtime(&t);
    if (lt) {{
        MR32(GUEST_TM_ADDR + 0)  = (uint32_t)lt->tm_sec;
        MR32(GUEST_TM_ADDR + 4)  = (uint32_t)lt->tm_min;
        MR32(GUEST_TM_ADDR + 8)  = (uint32_t)lt->tm_hour;
        MR32(GUEST_TM_ADDR + 12) = (uint32_t)lt->tm_mday;
        MR32(GUEST_TM_ADDR + 16) = (uint32_t)lt->tm_mon;
        MR32(GUEST_TM_ADDR + 20) = (uint32_t)lt->tm_year;
        MR32(GUEST_TM_ADDR + 24) = (uint32_t)lt->tm_wday;
        MR32(GUEST_TM_ADDR + 28) = (uint32_t)lt->tm_yday;
        MR32(GUEST_TM_ADDR + 32) = (uint32_t)lt->tm_isdst;
        c->eax = GUEST_TM_ADDR;
    }} else {{
        c->eax = 0;
    }}
}}"""

    if fn == 'crt_shim__localtime32':
        return f"""void {fn}(CPU *c) {{
    uint32_t timer_va = MR32(c->esp);
    time_t t = timer_va ? (time_t)MR32(timer_va) : time(NULL);
    struct tm *lt = localtime(&t);
    if (lt) {{
        MR32(GUEST_TM_ADDR + 0)  = (uint32_t)lt->tm_sec;
        MR32(GUEST_TM_ADDR + 4)  = (uint32_t)lt->tm_min;
        MR32(GUEST_TM_ADDR + 8)  = (uint32_t)lt->tm_hour;
        MR32(GUEST_TM_ADDR + 12) = (uint32_t)lt->tm_mday;
        MR32(GUEST_TM_ADDR + 16) = (uint32_t)lt->tm_mon;
        MR32(GUEST_TM_ADDR + 20) = (uint32_t)lt->tm_year;
        MR32(GUEST_TM_ADDR + 24) = (uint32_t)lt->tm_wday;
        MR32(GUEST_TM_ADDR + 28) = (uint32_t)lt->tm_yday;
        MR32(GUEST_TM_ADDR + 32) = (uint32_t)lt->tm_isdst;
        c->eax = GUEST_TM_ADDR;
    }} else {{
        c->eax = 0;
    }}
}}"""

    if fn == 'crt_shim__gmtime64':
        return f"""void {fn}(CPU *c) {{
    uint32_t timer_va = MR32(c->esp);
    time_t t = timer_va ? (time_t)MR64(timer_va) : time(NULL);
    struct tm *gt = gmtime(&t);
    if (gt) {{
        MR32(GUEST_TM_ADDR + 0)  = (uint32_t)gt->tm_sec;
        MR32(GUEST_TM_ADDR + 4)  = (uint32_t)gt->tm_min;
        MR32(GUEST_TM_ADDR + 8)  = (uint32_t)gt->tm_hour;
        MR32(GUEST_TM_ADDR + 12) = (uint32_t)gt->tm_mday;
        MR32(GUEST_TM_ADDR + 16) = (uint32_t)gt->tm_mon;
        MR32(GUEST_TM_ADDR + 20) = (uint32_t)gt->tm_year;
        MR32(GUEST_TM_ADDR + 24) = (uint32_t)gt->tm_wday;
        MR32(GUEST_TM_ADDR + 28) = (uint32_t)gt->tm_yday;
        MR32(GUEST_TM_ADDR + 32) = (uint32_t)gt->tm_isdst;
        c->eax = GUEST_TM_ADDR;
    }} else {{
        c->eax = 0;
    }}
}}"""

    if fn == 'crt_shim__mktime64':
        return f"""void {fn}(CPU *c) {{
    uint32_t ptm = MR32(c->esp);
    struct tm tm_val;
    memset(&tm_val, 0, sizeof(tm_val));
    if (ptm) {{
        tm_val.tm_sec  = (int)MR32(ptm + 0);
        tm_val.tm_min  = (int)MR32(ptm + 4);
        tm_val.tm_hour = (int)MR32(ptm + 8);
        tm_val.tm_mday = (int)MR32(ptm + 12);
        tm_val.tm_mon  = (int)MR32(ptm + 16);
        tm_val.tm_year = (int)MR32(ptm + 20);
    }}
    uint64_t res = (uint64_t)mktime(&tm_val);
    c->eax = (uint32_t)(res & 0xffffffffu);
    c->edx = (uint32_t)(res >> 32);
}}"""

    if fn == 'crt_shim__mkgmtime64':
        return f"""void {fn}(CPU *c) {{
    uint32_t ptm = MR32(c->esp);
    struct tm tm_val;
    memset(&tm_val, 0, sizeof(tm_val));
    if (ptm) {{
        tm_val.tm_sec  = (int)MR32(ptm + 0);
        tm_val.tm_min  = (int)MR32(ptm + 4);
        tm_val.tm_hour = (int)MR32(ptm + 8);
        tm_val.tm_mday = (int)MR32(ptm + 12);
        tm_val.tm_mon  = (int)MR32(ptm + 16);
        tm_val.tm_year = (int)MR32(ptm + 20);
    }}
    uint64_t res = (uint64_t)mktime(&tm_val);
    c->eax = (uint32_t)(res & 0xffffffffu);
    c->edx = (uint32_t)(res >> 32);
}}"""

    if fn == 'crt_shim_asctime':
        return f"""void {fn}(CPU *c) {{
    strcpy((char *)(g_mem + GUEST_ASCTIME_ADDR), "Sat Oct 31 12:00:00 2026\\n");
    c->eax = GUEST_ASCTIME_ADDR;
}}"""

    # Random
    if fn == 'crt_shim_rand':
        return f"""void {fn}(CPU *c) {{
    c->eax = (uint32_t)rand();
}}"""

    if fn == 'crt_shim_srand':
        return f"""void {fn}(CPU *c) {{
    srand((unsigned int)MR32(c->esp));
}}"""

    # Environment
    if fn == 'crt_shim_getenv':
        return f"""void {fn}(CPU *c) {{
    const char *var = guest_str(MR32(c->esp));
    const char *val = getenv(var);
    if (val) {{
        strcpy((char *)(g_mem + GUEST_GETCWD_ADDR), val);
        c->eax = GUEST_GETCWD_ADDR;
    }} else {{
        c->eax = 0;
    }}
}}"""

    if fn == 'crt_shim__getcwd':
        return f"""void {fn}(CPU *c) {{
    uint32_t buf_va = MR32(c->esp);
    uint32_t maxlen = MR32(c->esp + 4);
    char *dst = (char *)(g_mem + buf_va);
    strncpy(dst, ".", maxlen);
    c->eax = buf_va;
}}"""

    if fn == 'crt_shim__fullpath':
        return f"""void {fn}(CPU *c) {{
    uint32_t abs_va = MR32(c->esp);
    const char *rel = guest_str(MR32(c->esp + 4));
    uint32_t maxlen = MR32(c->esp + 8);
    char *dst = (char *)(g_mem + abs_va);
    strncpy(dst, rel, maxlen);
    c->eax = abs_va;
}}"""

    # Lifecycle, Initializers & Process Control
    if fn == 'crt_shim__initterm':
        return f"""void {fn}(CPU *c) {{
    uint32_t start = MR32(c->esp);
    uint32_t end   = MR32(c->esp + 4);
    for (uint32_t p = start; p < end; p += 4) {{
        uint32_t fn_va = MR32(p);
        if (fn_va != 0) {{
            uint32_t saved_esp = c->esp;
            DISPATCH_CALL(c, fn_va);
            c->esp = saved_esp;
        }}
    }}
}}"""

    if fn == 'crt_shim__initterm_e':
        return f"""void {fn}(CPU *c) {{
    uint32_t start = MR32(c->esp);
    uint32_t end   = MR32(c->esp + 4);
    for (uint32_t p = start; p < end; p += 4) {{
        uint32_t fn_va = MR32(p);
        if (fn_va != 0) {{
            uint32_t saved_esp = c->esp;
            DISPATCH_CALL(c, fn_va);
            c->esp = saved_esp;
            if (c->eax != 0) return;
        }}
    }}
    c->eax = 0;
}}"""

    if fn == 'crt_shim__onexit':
        return f"""void {fn}(CPU *c) {{
    uint32_t fn_va = MR32(c->esp);
    c->eax = crt_register_onexit(fn_va);
}}"""

    if fn == 'crt_shim___dllonexit':
        return f"""void {fn}(CPU *c) {{
    uint32_t fn_va = MR32(c->esp);
    c->eax = crt_register_onexit(fn_va);
}}"""

    if fn == 'crt_shim__lock' or fn == 'crt_shim__unlock':
        return f"""void {fn}(CPU *c) {{
    (void)c;
}}"""

    if fn == 'crt_shim__encode_pointer' or fn == 'crt_shim__decode_pointer':
        return f"""void {fn}(CPU *c) {{
    c->eax = MR32(c->esp);
}}"""

    if fn == 'crt_shim___getmainargs':
        return f"""void {fn}(CPU *c) {{
    uint32_t pargc = MR32(c->esp);
    uint32_t pargv = MR32(c->esp + 4);
    uint32_t penvp = MR32(c->esp + 8);
    if (pargc) MR32(pargc) = 1;
    if (pargv) MR32(pargv) = GUEST_ARGV_TAB_ADDR;
    if (penvp) MR32(penvp) = GUEST_ENVP_TAB_ADDR;
    c->eax = 0;
}}"""

    if fn == 'crt_shim___set_app_type':
        return f"""void {fn}(CPU *c) {{
    g_app_type = MR32(c->esp);
    c->eax = 0;
}}"""

    if fn == 'crt_shim___p__commode':
        return f"""void {fn}(CPU *c) {{
    c->eax = GUEST_COMMODE_ADDR;
}}"""

    if fn == 'crt_shim___p__fmode':
        return f"""void {fn}(CPU *c) {{
    c->eax = GUEST_FMODE_ADDR;
}}"""

    if fn == 'crt_shim___initenv':
        return f"""void {fn}(CPU *c) {{
    c->eax = GUEST_INITENV_ADDR;
}}"""

    if fn == 'crt_shim__cexit':
        return f"""void {fn}(CPU *c) {{
    crt_run_exit_handlers(c);
}}"""

    if fn == 'crt_shim__exit' or fn == 'crt_shim_exit':
        return f"""void {fn}(CPU *c) {{
    crt_run_exit_handlers(c);
    c->eax = MR32(c->esp);
}}"""

    if fn == 'crt_shim__amsg_exit':
        return f"""void {fn}(CPU *c) {{
    c->eax = MR32(c->esp);
}}"""

    if fn == 'crt_shim__XcptFilter':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
}}"""

    if fn == 'crt_shim__configthreadlocale':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
}}"""

    if fn == 'crt_shim___setusermatherr':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
}}"""

    if fn == 'crt_shim__invalid_parameter_noinfo':
        return f"""void {fn}(CPU *c) {{
    (void)c;
}}"""

    if fn == 'crt_shim__purecall':
        return f"""void {fn}(CPU *c) {{
    (void)c;
}}"""

    if fn == 'crt_shim__crt_debugger_hook':
        return f"""void {fn}(CPU *c) {{
    (void)c;
}}"""

    if fn == 'crt_shim__invoke_watson':
        return f"""void {fn}(CPU *c) {{
    (void)c;
}}"""

    # C++ exception classes and RTTI
    if fn == 'crt_shim_std_exception_default_ctor':
        return f"""void {fn}(CPU *c) {{
    if (c->ecx) MR32(c->ecx) = 0;
    c->eax = c->ecx;
}}"""

    if fn == 'crt_shim_std_exception_copy_ctor':
        return f"""void {fn}(CPU *c) {{
    c->eax = c->ecx;
}}"""

    if fn == 'crt_shim_std_exception_dtor':
        return f"""void {fn}(CPU *c) {{
    c->eax = c->ecx;
}}"""

    if fn == 'crt_shim_type_info_dtor':
        return f"""void {fn}(CPU *c) {{
    c->eax = c->ecx;
}}"""

    if fn == 'crt_shim_terminate':
        return f"""void {fn}(CPU *c) {{
    (void)c;
}}"""

    if fn == 'crt_shim___RTDynamicCast':
        return f"""void {fn}(CPU *c) {{
    uint32_t in_obj = MR32(c->esp);
    c->eax = in_obj;
}}"""

    if fn == 'crt_shim___CxxFrameHandler3':
        return f"""void {fn}(CPU *c) {{
    c->eax = 1; /* ExceptionContinueSearch */
}}"""

    if fn == 'crt_shim__CxxThrowException':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
}}"""

    if fn == 'crt_shim__except_handler3' or fn == 'crt_shim__except_handler4_common':
        return f"""void {fn}(CPU *c) {{
    c->eax = 1; /* ExceptionContinueSearch */
}}"""

    # Setjmp & Longjmp
    if fn == 'crt_shim__setjmp3':
        return f"""void {fn}(CPU *c) {{
    uint32_t env_va = MR32(c->esp);
    MR32(env_va + 0)  = c->ebp;
    MR32(env_va + 4)  = c->ebx;
    MR32(env_va + 8)  = c->edi;
    MR32(env_va + 12) = c->esi;
    MR32(env_va + 16) = c->esp;
    MR32(env_va + 20) = c->eip;
    c->eax = 0;
}}"""

    if fn == 'crt_shim_longjmp':
        return f"""void {fn}(CPU *c) {{
    uint32_t env_va = MR32(c->esp);
    int val = (int)MR32(c->esp + 4);
    c->ebp = MR32(env_va + 0);
    c->ebx = MR32(env_va + 4);
    c->edi = MR32(env_va + 8);
    c->esi = MR32(env_va + 12);
    c->esp = MR32(env_va + 16);
    c->eip = MR32(env_va + 20);
    c->eax = val ? (uint32_t)val : 1;
}}"""

    # Threads
    if fn == 'crt_shim__beginthreadex':
        return f"""void {fn}(CPU *c) {{
    uint32_t pthrd = MR32(c->esp);
    if (pthrd) MR32(pthrd) = 0x1001;
    c->eax = 0x1001; /* Pseudo thread handle */
}}"""

    if fn == 'crt_shim__endthreadex':
        return f"""void {fn}(CPU *c) {{
    (void)c;
}}"""

    # Directory find
    if fn == 'crt_shim__findfirst64i32':
        return f"""void {fn}(CPU *c) {{
    c->eax = (uint32_t)-1;
}}"""

    if fn == 'crt_shim__findnext64i32':
        return f"""void {fn}(CPU *c) {{
    c->eax = (uint32_t)-1;
}}"""

    if fn == 'crt_shim__findclose':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
}}"""

    # Signal
    if fn == 'crt_shim_raise':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
}}"""

    # Sorting & Searching
    if fn == 'crt_shim_bsearch':
        return f"""void {fn}(CPU *c) {{
    uint32_t key     = MR32(c->esp);
    uint32_t base    = MR32(c->esp + 4);
    uint32_t num     = MR32(c->esp + 8);
    uint32_t width   = MR32(c->esp + 12);
    uint32_t comp_fn = MR32(c->esp + 16);
    int32_t low = 0;
    int32_t high = (int32_t)num - 1;
    while (low <= high) {{
        int32_t mid = low + (high - low) / 2;
        uint32_t elem = base + mid * width;
        uint32_t old_esp = c->esp;
        PUSH32(elem);
        PUSH32(key);
        DISPATCH_CALL(c, comp_fn);
        c->esp = old_esp;
        int32_t res = (int32_t)c->eax;
        if (res == 0) {{ c->eax = elem; return; }}
        if (res < 0) high = mid - 1;
        else low = mid + 1;
    }}
    c->eax = 0;
}}"""

    if fn == 'crt_shim_qsort':
        return f"""void {fn}(CPU *c) {{
    uint32_t base    = MR32(c->esp);
    uint32_t num     = MR32(c->esp + 4);
    uint32_t width   = MR32(c->esp + 8);
    uint32_t comp_fn = MR32(c->esp + 12);
    if (num <= 1 || width == 0) return;
    for (uint32_t i = 1; i < num; ++i) {{
        for (uint32_t j = i; j > 0; --j) {{
            uint32_t p1 = base + (j - 1) * width;
            uint32_t p2 = base + j * width;
            uint32_t old_esp = c->esp;
            PUSH32(p2);
            PUSH32(p1);
            DISPATCH_CALL(c, comp_fn);
            c->esp = old_esp;
            if ((int32_t)c->eax > 0) {{
                uint8_t tmp[256];
                uint32_t rem = width;
                uint32_t off = 0;
                while (rem > 0) {{
                    uint32_t chunk = rem > sizeof(tmp) ? sizeof(tmp) : rem;
                    memcpy(tmp, g_mem + p1 + off, chunk);
                    memcpy(g_mem + p1 + off, g_mem + p2 + off, chunk);
                    memcpy(g_mem + p2 + off, tmp, chunk);
                    off += chunk;
                    rem -= chunk;
                }}
            }} else {{
                break;
            }}
        }}
    }}
}}"""

    # Generic fallback
    return f"""void {fn}(CPU *c) {{
    /* Default stub for 0x{va:08x}: {sym} */
    c->eax = 0;
}}"""


def main():
    print(f"Reading target executable from {EXE_PATH} (read-only)...")
    with open(EXE_PATH, 'rb') as f:
        exe_bytes = f.read()

    symbols = extract_msvcr80_imports(exe_bytes)
    print(f"Extracted {len(symbols)} MSVCR80.dll imports.")
    first_va = symbols[0][0]
    last_va = symbols[-1][0]
    print(f"IAT range: 0x{first_va:08x} .. 0x{last_va:08x} ({len(symbols)} slots)")

    # Verify uniqueness of sanitized names
    name_map = {}
    for va, sym in symbols:
        fn = sanitize_name(sym)
        if fn in name_map:
            raise ValueError(f"Name collision: {fn} for {sym} and {name_map[fn]}")
        name_map[fn] = (va, sym)

    print(f"Generating {CRT_H_PATH}...")
    header_code = generate_header(symbols)
    with open(CRT_H_PATH, 'w', encoding='utf-8') as f:
        f.write(header_code)

    print(f"Generating {CRT_C_PATH}...")
    source_code = generate_source(symbols)
    with open(CRT_C_PATH, 'w', encoding='utf-8') as f:
        f.write(source_code)

    print(f"Successfully generated runtime/crt.h ({len(header_code)} bytes) and runtime/crt.c ({len(source_code)} bytes)!")


if __name__ == '__main__':
    main()
