"""Generates the Win32 Core Emulation Layer (runtime/win32.h and runtime/win32.c) for NFS ProStreet.

Extracts all 158 core Win32 imports (KERNEL32, USER32, ADVAPI32, WINMM, SHFOLDER,
ole32, RPCRT4, NETAPI32, MSVCP80) and 40 WS2_32 network stubs from nfs.exe,
generates __stdcall-compliant C99 shims, and binds them to g_dtab at authentic IAT VAs.
"""
import os
import re
import struct
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
EXE_PATH = Path(r"C:\Games\Pro Street\Need For Spped - Pro Street\nfs.exe")
WIN32_H_PATH = WORKSPACE / "runtime" / "win32.h"
WIN32_C_PATH = WORKSPACE / "runtime" / "win32.c"

CORE_DLLS = [
    'KERNEL32.dll',
    'USER32.dll',
    'ADVAPI32.dll',
    'WINMM.dll',
    'SHFOLDER.dll',
    'ole32.dll',
    'RPCRT4.dll',
    'NETAPI32.dll',
    'MSVCP80.dll',
    'WS2_32.dll'
]

# Exact stack pop sizes (bytes) for Win32 __stdcall and thiscall functions
ARG_SIZES = {
    # KERNEL32
    'MultiByteToWideChar': 24,
    'SuspendThread': 4,
    'ResumeThread': 4,
    'GetVersionExA': 4,
    'GetLongPathNameA': 12,
    'GetDriveTypeA': 4,
    'GetLogicalDrives': 0,
    'FindClose': 4,
    'FindNextFileA': 8,
    'FindFirstFileA': 8,
    'FreeLibrary': 4,
    'CreateDirectoryA': 8,
    'GetModuleHandleA': 4,
    'GetSystemInfo': 4,
    'Sleep': 4,
    'Process32Next': 8,
    'Process32First': 8,
    'CreateToolhelp32Snapshot': 8,
    'SetErrorMode': 4,
    'GetTickCount': 0,
    'SetThreadPriority': 8,
    'GetSystemTimeAsFileTime': 4,
    'GetCurrentProcessId': 0,
    'GetCurrentThreadId': 0,
    'SetUnhandledExceptionFilter': 4,
    'UnhandledExceptionFilter': 4,
    'GetCurrentProcess': 0,
    'TerminateProcess': 8,
    'CloseHandle': 4,
    'InterlockedExchange': 8,
    'ReleaseMutex': 4,
    'CreateMutexW': 12,
    'GetSystemDirectoryA': 8,
    'LoadLibraryA': 4,
    'LeaveCriticalSection': 4,
    'TryEnterCriticalSection': 4,
    'EnterCriticalSection': 4,
    'DeleteCriticalSection': 4,
    'InitializeCriticalSection': 4,
    'WaitForSingleObject': 8,
    'CreateEventA': 16,
    'GetDiskFreeSpaceExA': 16,
    'SetWaitableTimer': 24,
    'SystemTimeToFileTime': 8,
    'GetSystemTime': 4,
    'CreateWaitableTimerA': 12,
    'DuplicateHandle': 28,
    'GetCurrentThread': 0,
    'TerminateThread': 8,
    'SleepEx': 8,
    'GetThreadPriority': 4,
    'GetExitCodeThread': 8,
    'WriteFile': 20,
    'SetFilePointer': 16,
    'DeleteFileA': 4,
    'MoveFileA': 8,
    'ReadFile': 20,
    'GetFileSize': 8,
    'GetProcAddress': 8,
    'OutputDebugStringA': 4,
    'QueryPerformanceFrequency': 4,
    'SetEvent': 4,
    'InterlockedCompareExchange': 12,
    'PulseEvent': 4,
    'GetPriorityClass': 4,
    'SetPriorityClass': 8,
    'RemoveDirectoryW': 4,
    'CreateDirectoryW': 8,
    'FindNextFileW': 8,
    'FindFirstFileW': 8,
    'WideCharToMultiByte': 32,
    'MoveFileW': 8,
    'DeleteFileW': 4,
    'SetEndOfFile': 4,
    'CreateFileW': 28,
    'IsDebuggerPresent': 0,
    'GetLastError': 0,
    'IsBadReadPtr': 8,
    'QueryPerformanceCounter': 4,
    'CreateThread': 24,
    'GetFileSizeEx': 8,
    'SetFilePointerEx': 16,
    'RaiseException': 16,
    'ReleaseSemaphore': 12,
    'InterlockedDecrement': 4,
    'CreateSemaphoreA': 16,
    'InterlockedExchangeAdd': 8,
    'SetThreadIdealProcessor': 8,
    'TlsGetValue': 4,
    'TlsSetValue': 8,
    'TlsAlloc': 0,
    'CreateMutexA': 12,
    'VirtualProtect': 16,
    'GetCurrentDirectoryA': 8,
    'ResetEvent': 4,
    'CreateFileA': 28,

    # USER32
    'DispatchMessageA': 4,
    'TranslateMessage': 4,
    'GetMessageA': 16,
    'ShowCursor': 4,
    'PeekMessageA': 20,
    'GetClientRect': 8,
    'SetWindowLongA': 12,
    'DestroyWindow': 4,
    'SendInput': 12,
    'SetCapture': 4,
    'SystemParametersInfoA': 16,
    'EnumDisplaySettingsA': 12,
    'EndPaint': 8,
    'BeginPaint': 8,
    'PostQuitMessage': 4,
    'MapVirtualKeyA': 8,
    'ToUnicode': 24,
    'GetForegroundWindow': 0,
    'GetDesktopWindow': 0,
    'GetKeyboardLayout': 4,
    'MapVirtualKeyExA': 12,
    'GetKeyState': 4,
    'IsIconic': 4,
    'MessageBoxA': 16,
    'ReleaseCapture': 0,
    'wvsprintfA': 12,
    'LoadIconA': 8,
    'LoadCursorA': 8,
    'RegisterClassExA': 4,
    'AdjustWindowRect': 12,
    'CreateWindowExA': 48,
    'UpdateWindow': 4,
    'SetCursor': 4,
    'SetFocus': 4,
    'SetForegroundWindow': 4,
    'GetWindowRect': 8,
    'ShowWindow': 8,
    'GetWindowLongA': 8,
    'DefWindowProcA': 16,
    'PostMessageA': 16,

    # ADVAPI32
    'CheckTokenMembership': 12,
    'FreeSid': 4,
    'RegCreateKeyA': 12,
    'RegOpenKeyExA': 20,
    'RegCloseKey': 4,
    'RegSetValueExA': 24,
    'RegQueryValueExA': 24,
    'CryptReleaseContext': 8,
    'CryptGenRandom': 12,
    'CryptAcquireContextA': 20,
    'AllocateAndInitializeSid': 44,

    # SHFOLDER
    'SHGetFolderPathA': 20,

    # RPCRT4
    'UuidToStringA': 8,
    'RpcStringFreeA': 4,

    # ole32
    'CoCreateGuid': 4,

    # MSVCP80 (thiscall)
    '??0?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@QAE@ABV01@@Z': 4,
    '??1?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@QAE@XZ': 0,
    '??0?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@QAE@PBD@Z': 4,

    # WINMM
    'timeEndPeriod': 4,
    'timeGetTime': 0,
    'timeBeginPeriod': 4,

    # NETAPI32
    'Netbios': 4,

    # WS2_32
    'WSACreateEvent': 0,
    'WSACloseEvent': 4,
    'WSASetEvent': 4,
    'WSARecv': 28,
    'WSARecvFrom': 36,
    'WSAResetEvent': 4,
    'WSAWaitForMultipleEvents': 20,
    'WSAGetOverlappedResult': 20,
    'WSAIoctl': 36,
    'ord_1': 12,   # accept
    'ord_2': 12,   # bind
    'ord_3': 4,    # closesocket
    'ord_4': 12,   # connect
    'ord_5': 8,    # getpeername
    'ord_6': 8,    # getsockname
    'ord_7': 20,   # getsockopt
    'ord_8': 4,    # htons
    'ord_9': 4,    # inet_addr
    'ord_10': 4,   # inet_ntoa
    'ord_11': 12,  # ioctlsocket
    'ord_12': 8,   # listen
    'ord_14': 4,   # ntohs
    'ord_15': 16,  # recv
    'ord_16': 24,  # recvfrom
    'ord_17': 20,  # select
    'ord_18': 16,  # send
    'ord_19': 24,  # sendto
    'ord_20': 20,  # setsockopt
    'ord_21': 8,   # shutdown
    'ord_22': 12,  # socket
    'ord_23': 12,  # gethostbyaddr
    'ord_51': 8,   # gethostname
    'ord_52': 4,   # gethostbyname
    'ord_55': 8,   # getpeername
    'ord_56': 8,   # getsockname
    'ord_57': 20,  # getsockopt
    'ord_111': 4,  # WSASetLastError
    'ord_112': 0,  # WSAGetLastError
    'ord_115': 8,  # WSAStartup
    'ord_116': 0   # WSACleanup
}


def extract_win32_imports(exe_bytes):
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
    dlls = []
    while True:
        ilt_rva, time, fwd, name_rva, iat_rva = struct.unpack_from('<IIIII', exe_bytes, off)
        if not (ilt_rva or name_rva or iat_rva):
            break
        off += 20
        name_off = rva_to_off(name_rva)
        dll_name = exe_bytes[name_off:exe_bytes.find(b'\0', name_off)].decode('ascii')
        dlls.append((dll_name, ilt_rva, iat_rva))

    imports = []
    for dll_name, ilt_rva, iat_rva in dlls:
        if dll_name not in CORE_DLLS:
            continue
        ilt_off = rva_to_off(ilt_rva)
        iat_va = 0x00400000 + iat_rva
        idx = 0
        while True:
            thunk = struct.unpack_from('<I', exe_bytes, ilt_off + idx * 4)[0]
            if not thunk:
                break
            cur_va = iat_va + idx * 4
            if thunk & 0x80000000:
                sname = f'ord_{thunk & 0xffff}'
            else:
                noff = rva_to_off(thunk) + 2
                sname = exe_bytes[noff:exe_bytes.find(b'\0', noff)].decode('ascii')
            imports.append((dll_name, cur_va, sname))
            idx += 1

    return imports


def sanitize_name(sym):
    if sym.startswith('??0?$basic_string'):
        if 'ABV01' in sym:
            return 'win32_shim_std_string_copy_ctor'
        return 'win32_shim_std_string_ctor_cstr'
    if sym.startswith('??1?$basic_string'):
        return 'win32_shim_std_string_dtor'
    clean = re.sub(r'[^a-zA-Z0-9_]', '_', sym)
    return 'win32_shim_' + clean


def generate_header(imports):
    lines = [
        "/* Need for Speed ProStreet - Win32 Core Emulation Layer Header.",
        " *",
        " * Automatically generated from target binary PE import directory.",
        f" * Total imported Win32 functions: {len(imports)}.",
        " * Modules: KERNEL32, USER32, ADVAPI32, WINMM, SHFOLDER, ole32, RPCRT4, NETAPI32, MSVCP80, WS2_32.",
        " */",
        "#ifndef PROSTREET_WIN32_H",
        "#define PROSTREET_WIN32_H",
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
        " * Win32 Import Record",
        " * -------------------------------------------------------------------------- */",
        "typedef struct {",
        "    uint32_t    slot_va;",
        "    const char *dll_name;",
        "    const char *symbol_name;",
        "    guest_fn_t  handler;",
        "    uint32_t    arg_bytes;",
        "} win32_import_entry_t;",
        "",
        "/* --------------------------------------------------------------------------",
        f" * Win32 Function Declarations ({len(imports)} functions)",
        " * -------------------------------------------------------------------------- */",
    ]

    for dll, va, sym in imports:
        fn = sanitize_name(sym)
        lines.append(f"void {fn}(struct CPU *c); /* 0x{va:08x}: {dll}!{sym} */")

    lines.extend([
        "",
        "/* --------------------------------------------------------------------------",
        " * Win32 Subsystem Management API",
        " * -------------------------------------------------------------------------- */",
        "void win32_init_iat(void);",
        "size_t win32_get_import_count(void);",
        "const win32_import_entry_t *win32_get_import_table(void);",
        "void win32_post_key_event(uint32_t vk, bool down);",
        "void win32_set_window_dims(uint32_t width, uint32_t height);",
        "",
        "#ifdef __cplusplus",
        "}",
        "#endif",
        "",
        "#endif /* PROSTREET_WIN32_H */",
        ""
    ])
    return "\n".join(lines)


def generate_source(imports):
    lines = [
        "/* Need for Speed ProStreet - Win32 Core Emulation Layer Implementation.",
        " *",
        " * Comprehensive __stdcall C99 shims for KERNEL32, USER32, ADVAPI32, WINMM,",
        " * SHFOLDER, ole32, RPCRT4, NETAPI32, MSVCP80, and WS2_32.",
        " */",
        "#include <stdbool.h>",
        "#include <stdint.h>",
        "#include <stdio.h>",
        "#include <stdlib.h>",
        "#include <string.h>",
        "#include <time.h>",
        '#include "win32.h"',
        '#include "memory.h"',
        "",
        "/* --------------------------------------------------------------------------",
        " * Win32 Handle Manager & Synchronization Primitives",
        " * -------------------------------------------------------------------------- */",
        "#define MAX_WIN32_HANDLES 256",
        "enum {",
        "    HANDLE_FREE = 0,",
        "    HANDLE_FILE,",
        "    HANDLE_MUTEX,",
        "    HANDLE_EVENT,",
        "    HANDLE_SEMAPHORE,",
        "    HANDLE_THREAD,",
        "    HANDLE_PROCESS,",
        "    HANDLE_FIND,",
        "    HANDLE_HWND",
        "};",
        "",
        "typedef struct {",
        "    uint32_t type;",
        "    uint32_t state;",
        "    uint32_t extra;",
        "    char     name[64];",
        "} win32_handle_t;",
        "",
        "static win32_handle_t g_handles[MAX_WIN32_HANDLES];",
        "static uint32_t g_tls_slots[64];",
        "static uint32_t g_tls_bitmap = 0;",
        "static uint32_t g_wnd_proc = 0;",
        "static uint32_t g_win_width = 1280;",
        "static uint32_t g_win_height = 720;",
        "static uint32_t g_msg_queue[16][4]; /* (hwnd, msg, wParam, lParam) */",
        "static uint32_t g_msg_count = 0;",
        "",
        "static uint32_t alloc_handle(uint32_t type, const char *name) {",
        "    for (uint32_t i = 0x10; i < MAX_WIN32_HANDLES; ++i) {",
        "        if (g_handles[i].type == HANDLE_FREE) {",
        "            g_handles[i].type = type;",
        "            g_handles[i].state = 0;",
        "            g_handles[i].extra = 0;",
        "            if (name) strncpy(g_handles[i].name, name, 63);",
        "            return (i << 2) | 0x01; /* Pseudo-Win32 handle */",
        "        }",
        "    }",
        "    return 0x1000; /* Fallback handle */",
        "}",
        "",
        "static inline const char *w32_str(uint32_t va) {",
        "    return (va >= GUEST_NULL_GUARD_LIMIT && va < GUEST_HEAP_LIMIT) ? (const char *)(g_mem + va) : \"\";",
        "}",
        "",
    ]

    # Generate each shim body
    for dll, va, sym in imports:
        fn = sanitize_name(sym)
        pop_bytes = ARG_SIZES.get(sym, 0)
        code = generate_single_win32_shim(fn, sym, dll, va, pop_bytes)
        lines.append(code)

    # Master IAT Table
    lines.extend([
        "",
        "/* --------------------------------------------------------------------------",
        f" * Master Win32 IAT Table ({len(imports)} entries)",
        " * -------------------------------------------------------------------------- */",
        f"static const win32_import_entry_t g_win32_imports[{len(imports)}] = {{",
    ])
    for dll, va, sym in imports:
        fn = sanitize_name(sym)
        pop_bytes = ARG_SIZES.get(sym, 0)
        lines.append(f'    {{ 0x{va:08x}u, "{dll}", "{sym}", {fn}, {pop_bytes}u }},')
    lines.extend([
        "};",
        "",
        f"size_t win32_get_import_count(void) {{ return {len(imports)}; }}",
        "const win32_import_entry_t *win32_get_import_table(void) { return g_win32_imports; }",
        "",
        "void win32_set_window_dims(uint32_t width, uint32_t height) {",
        "    g_win_width = width;",
        "    g_win_height = height;",
        "}",
        "",
        "void win32_post_key_event(uint32_t vk, bool down) {",
        "    if (g_msg_count < 16) {",
        "        g_msg_queue[g_msg_count][0] = 0x00010001u; /* hwnd */",
        "        g_msg_queue[g_msg_count][1] = down ? 0x0100u : 0x0101u; /* WM_KEYDOWN / UP */",
        "        g_msg_queue[g_msg_count][2] = vk; /* wParam */",
        "        g_msg_queue[g_msg_count][3] = 0;  /* lParam */",
        "        g_msg_count++;",
        "    }",
        "}",
        "",
        "void win32_init_iat(void) {",
        "    /* Bind all Win32 IAT slots into linear memory and g_dtab */",
        f"    for (size_t i = 0; i < {len(imports)}; ++i) {{",
        "        uint32_t slot_va = g_win32_imports[i].slot_va;",
        "        MR32(slot_va) = slot_va;",
        "        uint32_t idx = slot_va - DISPATCH_TEXT_BASE;",
        "        if (idx < DISPATCH_TEXT_SIZE) {",
        "            g_dtab[idx] = g_win32_imports[i].handler;",
        "        }",
        "    }",
        "}",
        ""
    ])
    return "\n".join(lines)


def generate_single_win32_shim(fn, sym, dll, va, pop_bytes):
    # Specialized implementations for Win32 API functions
    # In static recompilation, arguments start directly at c->esp (offset 0).
    # Always pop c->esp += pop_bytes for __stdcall!

    # 1. Synchronization
    if sym == 'InitializeCriticalSection':
        return f"""void {fn}(CPU *c) {{
    uint32_t cs = MR32(c->esp);
    if (cs) memset(g_mem + cs, 0, 24);
    c->esp += {pop_bytes};
}}"""

    if sym == 'EnterCriticalSection':
        return f"""void {fn}(CPU *c) {{
    uint32_t cs = MR32(c->esp);
    if (cs) {{
        MR32(cs + 8) += 1; /* RecursionCount */
        MR32(cs + 12) = 1000; /* OwningThread */
    }}
    c->esp += {pop_bytes};
}}"""

    if sym == 'LeaveCriticalSection':
        return f"""void {fn}(CPU *c) {{
    uint32_t cs = MR32(c->esp);
    if (cs && MR32(cs + 8) > 0) {{
        MR32(cs + 8) -= 1;
    }}
    c->esp += {pop_bytes};
}}"""

    if sym == 'TryEnterCriticalSection':
        return f"""void {fn}(CPU *c) {{
    uint32_t cs = MR32(c->esp);
    if (cs) {{
        MR32(cs + 8) += 1;
        MR32(cs + 12) = 1000;
    }}
    c->eax = 1; /* TRUE */
    c->esp += {pop_bytes};
}}"""

    if sym == 'DeleteCriticalSection':
        return f"""void {fn}(CPU *c) {{
    uint32_t cs = MR32(c->esp);
    if (cs) memset(g_mem + cs, 0, 24);
    c->esp += {pop_bytes};
}}"""

    if sym in ('CreateMutexA', 'CreateMutexW'):
        return f"""void {fn}(CPU *c) {{
    c->eax = alloc_handle(HANDLE_MUTEX, "NFS_Mutex");
    c->esp += {pop_bytes};
}}"""

    if sym == 'ReleaseMutex':
        return f"""void {fn}(CPU *c) {{
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'CreateEventA':
        return f"""void {fn}(CPU *c) {{
    c->eax = alloc_handle(HANDLE_EVENT, "NFS_Event");
    c->esp += {pop_bytes};
}}"""

    if sym in ('SetEvent', 'ResetEvent', 'PulseEvent'):
        return f"""void {fn}(CPU *c) {{
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'CreateSemaphoreA':
        return f"""void {fn}(CPU *c) {{
    c->eax = alloc_handle(HANDLE_SEMAPHORE, "NFS_Sem");
    c->esp += {pop_bytes};
}}"""

    if sym == 'ReleaseSemaphore':
        return f"""void {fn}(CPU *c) {{
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'WaitForSingleObject':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0; /* WAIT_OBJECT_0 */
    c->esp += {pop_bytes};
}}"""

    if sym == 'CloseHandle':
        return f"""void {fn}(CPU *c) {{
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'DuplicateHandle':
        return f"""void {fn}(CPU *c) {{
    uint32_t pTarget = MR32(c->esp + 12);
    if (pTarget) MR32(pTarget) = MR32(c->esp + 4);
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    # 2. Timing
    if sym == 'QueryPerformanceCounter':
        return f"""void {fn}(CPU *c) {{
    uint32_t pCounter = MR32(c->esp);
    if (pCounter) {{
        static uint64_t s_qpc = 1000000;
        s_qpc += 16666; /* ~60 fps tick */
        MR64(pCounter) = s_qpc;
    }}
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'QueryPerformanceFrequency':
        return f"""void {fn}(CPU *c) {{
    uint32_t pFreq = MR32(c->esp);
    if (pFreq) MR64(pFreq) = 1000000ull; /* 1 MHz */
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym in ('GetTickCount', 'timeGetTime'):
        return f"""void {fn}(CPU *c) {{
    static uint32_t s_tick = 50000;
    s_tick += 16;
    c->eax = s_tick;
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetSystemTimeAsFileTime':
        return f"""void {fn}(CPU *c) {{
    uint32_t pFT = MR32(c->esp);
    if (pFT) {{
        MR32(pFT + 0) = 0x80000000u;
        MR32(pFT + 4) = 0x01D38000u;
    }}
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetSystemTime':
        return f"""void {fn}(CPU *c) {{
    uint32_t pST = MR32(c->esp);
    if (pST) {{
        MR16(pST + 0) = 2026; /* wYear */
        MR16(pST + 2) = 10;   /* wMonth */
        MR16(pST + 4) = 6;    /* wDayOfWeek */
        MR16(pST + 6) = 31;   /* wDay */
        MR16(pST + 8) = 12;   /* wHour */
        MR16(pST + 10) = 0;   /* wMinute */
        MR16(pST + 12) = 0;   /* wSecond */
        MR16(pST + 14) = 0;   /* wMilliseconds */
    }}
    c->esp += {pop_bytes};
}}"""

    if sym == 'SystemTimeToFileTime':
        return f"""void {fn}(CPU *c) {{
    uint32_t pFT = MR32(c->esp + 4);
    if (pFT) {{
        MR32(pFT + 0) = 0x80000000u;
        MR32(pFT + 4) = 0x01D38000u;
    }}
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym in ('timeBeginPeriod', 'timeEndPeriod'):
        return f"""void {fn}(CPU *c) {{
    c->eax = 0; /* TIMERR_NOERROR */
    c->esp += {pop_bytes};
}}"""

    if sym in ('Sleep', 'SleepEx'):
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
    c->esp += {pop_bytes};
}}"""

    if sym == 'CreateWaitableTimerA':
        return f"""void {fn}(CPU *c) {{
    c->eax = alloc_handle(HANDLE_EVENT, "Timer");
    c->esp += {pop_bytes};
}}"""

    if sym == 'SetWaitableTimer':
        return f"""void {fn}(CPU *c) {{
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    # 3. Thread Local Storage (TLS)
    if sym == 'TlsAlloc':
        return f"""void {fn}(CPU *c) {{
    for (uint32_t i = 0; i < 64; ++i) {{
        if (!(g_tls_bitmap & (1ull << i))) {{
            g_tls_bitmap |= (1ull << i);
            g_tls_slots[i] = 0;
            c->eax = i;
            c->esp += {pop_bytes};
            return;
        }}
    }}
    c->eax = (uint32_t)-1; /* TLS_OUT_OF_INDEXES */
    c->esp += {pop_bytes};
}}"""

    if sym == 'TlsGetValue':
        return f"""void {fn}(CPU *c) {{
    uint32_t idx = MR32(c->esp);
    c->eax = (idx < 64) ? g_tls_slots[idx] : 0;
    c->esp += {pop_bytes};
}}"""

    if sym == 'TlsSetValue':
        return f"""void {fn}(CPU *c) {{
    uint32_t idx = MR32(c->esp);
    uint32_t val = MR32(c->esp + 4);
    if (idx < 64) g_tls_slots[idx] = val;
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    # 4. Atomic Operations
    if sym == 'InterlockedExchange':
        return f"""void {fn}(CPU *c) {{
    uint32_t pTarget = MR32(c->esp);
    uint32_t val     = MR32(c->esp + 4);
    uint32_t old     = MR32(pTarget);
    MR32(pTarget)    = val;
    c->eax = old;
    c->esp += {pop_bytes};
}}"""

    if sym == 'InterlockedCompareExchange':
        return f"""void {fn}(CPU *c) {{
    uint32_t pDest = MR32(c->esp);
    uint32_t exch  = MR32(c->esp + 4);
    uint32_t comp  = MR32(c->esp + 8);
    uint32_t old   = MR32(pDest);
    if (old == comp) MR32(pDest) = exch;
    c->eax = old;
    c->esp += {pop_bytes};
}}"""

    if sym == 'InterlockedDecrement':
        return f"""void {fn}(CPU *c) {{
    uint32_t pAdd = MR32(c->esp);
    uint32_t res = MR32(pAdd) - 1;
    MR32(pAdd) = res;
    c->eax = res;
    c->esp += {pop_bytes};
}}"""

    if sym == 'InterlockedExchangeAdd':
        return f"""void {fn}(CPU *c) {{
    uint32_t pAdd = MR32(c->esp);
    uint32_t val  = MR32(c->esp + 4);
    uint32_t old  = MR32(pAdd);
    MR32(pAdd)    = old + val;
    c->eax = old;
    c->esp += {pop_bytes};
}}"""

    # 5. Process & Thread Info
    if sym == 'GetCurrentProcess':
        return f"""void {fn}(CPU *c) {{
    c->eax = (uint32_t)-1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetCurrentProcessId':
        return f"""void {fn}(CPU *c) {{
    c->eax = 1000;
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetCurrentThread':
        return f"""void {fn}(CPU *c) {{
    c->eax = (uint32_t)-2;
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetCurrentThreadId':
        return f"""void {fn}(CPU *c) {{
    c->eax = 1000;
    c->esp += {pop_bytes};
}}"""

    if sym == 'CreateThread':
        return f"""void {fn}(CPU *c) {{
    uint32_t pThrdId = MR32(c->esp + 20);
    if (pThrdId) MR32(pThrdId) = 1001;
    c->eax = alloc_handle(HANDLE_THREAD, "WorkerThread");
    c->esp += {pop_bytes};
}}"""

    if sym in ('TerminateThread', 'TerminateProcess'):
        return f"""void {fn}(CPU *c) {{
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'SuspendThread':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
    c->esp += {pop_bytes};
}}"""

    if sym == 'ResumeThread':
        return f"""void {fn}(CPU *c) {{
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'SetThreadPriority':
        return f"""void {fn}(CPU *c) {{
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetThreadPriority':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0; /* THREAD_PRIORITY_NORMAL */
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetExitCodeThread':
        return f"""void {fn}(CPU *c) {{
    uint32_t pCode = MR32(c->esp + 4);
    if (pCode) MR32(pCode) = 0;
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'SetThreadIdealProcessor':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetPriorityClass':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0x20; /* NORMAL_PRIORITY_CLASS */
    c->esp += {pop_bytes};
}}"""

    if sym == 'SetPriorityClass':
        return f"""void {fn}(CPU *c) {{
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'CreateToolhelp32Snapshot':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0x2000;
    c->esp += {pop_bytes};
}}"""

    if sym == 'Process32First':
        return f"""void {fn}(CPU *c) {{
    uint32_t pe = MR32(c->esp + 4);
    if (pe) {{
        MR32(pe + 8)  = 1000; /* th32ProcessID */
        MR32(pe + 20) = 4;    /* cntThreads */
        strcpy((char *)(g_mem + pe + 36), "nfs.exe");
    }}
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'Process32Next':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0; /* No more processes */
    c->esp += {pop_bytes};
}}"""

    # 6. System & Modules
    if sym == 'GetVersionExA':
        return f"""void {fn}(CPU *c) {{
    uint32_t pVer = MR32(c->esp);
    if (pVer) {{
        MR32(pVer + 4)  = 5;    /* dwMajorVersion (Windows XP) */
        MR32(pVer + 8)  = 1;    /* dwMinorVersion */
        MR32(pVer + 12) = 2600; /* dwBuildNumber */
        MR32(pVer + 16) = 2;    /* VER_PLATFORM_WIN32_NT */
        strcpy((char *)(g_mem + pVer + 20), "Service Pack 3");
    }}
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetSystemInfo':
        return f"""void {fn}(CPU *c) {{
    uint32_t pInfo = MR32(c->esp);
    if (pInfo) {{
        MR16(pInfo + 0)  = 0; /* PROCESSOR_ARCHITECTURE_INTEL */
        MR32(pInfo + 4)  = 4096; /* dwPageSize */
        MR32(pInfo + 8)  = 0x00010000; /* lpMinimumApplicationAddress */
        MR32(pInfo + 12) = 0x7FFEFFFF; /* lpMaximumApplicationAddress */
        MR32(pInfo + 20) = 4; /* dwNumberOfProcessors */
        MR32(pInfo + 28) = 586; /* dwProcessorType */
    }}
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetModuleHandleA':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0x00400000u; /* ImageBase */
    c->esp += {pop_bytes};
}}"""

    if sym == 'LoadLibraryA':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0x10000000u; /* Pseudo DLL base */
    c->esp += {pop_bytes};
}}"""

    if sym == 'FreeLibrary':
        return f"""void {fn}(CPU *c) {{
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetProcAddress':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetLastError':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0; /* ERROR_SUCCESS */
    c->esp += {pop_bytes};
}}"""

    if sym == 'SetErrorMode':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
    c->esp += {pop_bytes};
}}"""

    if sym == 'IsDebuggerPresent':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
    c->esp += {pop_bytes};
}}"""

    if sym == 'OutputDebugStringA':
        return f"""void {fn}(CPU *c) {{
    const char *s = w32_str(MR32(c->esp));
    fputs(s, stderr);
    c->esp += {pop_bytes};
}}"""

    if sym == 'VirtualProtect':
        return f"""void {fn}(CPU *c) {{
    uint32_t pOld = MR32(c->esp + 12);
    if (pOld) MR32(pOld) = 0x40; /* PAGE_EXECUTE_READWRITE */
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'IsBadReadPtr':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
    c->esp += {pop_bytes};
}}"""

    if sym in ('SetUnhandledExceptionFilter', 'UnhandledExceptionFilter'):
        return f"""void {fn}(CPU *c) {{
    c->eax = 1; /* EXCEPTION_EXECUTE_HANDLER */
    c->esp += {pop_bytes};
}}"""

    if sym == 'RaiseException':
        return f"""void {fn}(CPU *c) {{
    c->esp += {pop_bytes};
}}"""

    # 7. File & Directory APIs
    if sym in ('CreateFileA', 'CreateFileW'):
        return f"""void {fn}(CPU *c) {{
    c->eax = alloc_handle(HANDLE_FILE, "GameFile");
    c->esp += {pop_bytes};
}}"""

    if sym in ('ReadFile', 'WriteFile'):
        return f"""void {fn}(CPU *c) {{
    uint32_t nBytes = MR32(c->esp + 8);
    uint32_t pDone  = MR32(c->esp + 12);
    if (pDone) MR32(pDone) = nBytes;
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym in ('SetFilePointer', 'SetFilePointerEx'):
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetFileSize':
        return f"""void {fn}(CPU *c) {{
    uint32_t pHigh = MR32(c->esp + 4);
    if (pHigh) MR32(pHigh) = 0;
    c->eax = 0x100000; /* 1 MB default */
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetFileSizeEx':
        return f"""void {fn}(CPU *c) {{
    uint32_t pSize = MR32(c->esp + 4);
    if (pSize) MR64(pSize) = 0x100000ull;
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'SetEndOfFile':
        return f"""void {fn}(CPU *c) {{
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym in ('DeleteFileA', 'DeleteFileW', 'MoveFileA', 'MoveFileW', 'CreateDirectoryA', 'CreateDirectoryW', 'RemoveDirectoryW'):
        return f"""void {fn}(CPU *c) {{
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym in ('FindFirstFileA', 'FindFirstFileW'):
        return f"""void {fn}(CPU *c) {{
    c->eax = (uint32_t)-1; /* INVALID_HANDLE_VALUE */
    c->esp += {pop_bytes};
}}"""

    if sym in ('FindNextFileA', 'FindNextFileW'):
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
    c->esp += {pop_bytes};
}}"""

    if sym == 'FindClose':
        return f"""void {fn}(CPU *c) {{
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetCurrentDirectoryA':
        return f"""void {fn}(CPU *c) {{
    uint32_t len = MR32(c->esp);
    uint32_t buf = MR32(c->esp + 4);
    if (buf && len > 2) strcpy((char *)(g_mem + buf), ".");
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetSystemDirectoryA':
        return f"""void {fn}(CPU *c) {{
    uint32_t buf = MR32(c->esp);
    uint32_t uSz = MR32(c->esp + 4);
    if (buf && uSz > 16) strcpy((char *)(g_mem + buf), "C:\\\\WINDOWS\\\\system32");
    c->eax = 19;
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetLongPathNameA':
        return f"""void {fn}(CPU *c) {{
    const char *src = w32_str(MR32(c->esp));
    uint32_t dst = MR32(c->esp + 4);
    uint32_t max = MR32(c->esp + 8);
    if (dst && max > 0) strncpy((char *)(g_mem + dst), src, max);
    c->eax = (uint32_t)strlen(src);
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetDriveTypeA':
        return f"""void {fn}(CPU *c) {{
    c->eax = 3; /* DRIVE_FIXED */
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetLogicalDrives':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0x0C; /* C: and D: */
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetDiskFreeSpaceExA':
        return f"""void {fn}(CPU *c) {{
    uint64_t free_bytes = 100ull * 1024ull * 1024ull * 1024ull; /* 100 GB */
    uint32_t pFree = MR32(c->esp + 4);
    uint32_t pTotal = MR32(c->esp + 8);
    uint32_t pTotalFree = MR32(c->esp + 12);
    if (pFree) MR64(pFree) = free_bytes;
    if (pTotal) MR64(pTotal) = free_bytes * 2;
    if (pTotalFree) MR64(pTotalFree) = free_bytes;
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'MultiByteToWideChar':
        return f"""void {fn}(CPU *c) {{
    const char *src = w32_str(MR32(c->esp + 8));
    int cbMulti = (int)MR32(c->esp + 12);
    uint32_t dst = MR32(c->esp + 16);
    int cchWide = (int)MR32(c->esp + 20);
    int slen = cbMulti > 0 ? cbMulti : (int)strlen(src);
    if (cchWide == 0) {{
        c->eax = (uint32_t)(slen + 1);
    }} else {{
        for (int i = 0; i < slen && i < cchWide; ++i) {{
            MR16(dst + i * 2) = (uint16_t)(unsigned char)src[i];
        }}
        if (slen < cchWide) MR16(dst + slen * 2) = 0;
        c->eax = (uint32_t)slen;
    }}
    c->esp += {pop_bytes};
}}"""

    if sym == 'WideCharToMultiByte':
        return f"""void {fn}(CPU *c) {{
    uint32_t src = MR32(c->esp + 8);
    int cchWide = (int)MR32(c->esp + 12);
    uint32_t dst = MR32(c->esp + 16);
    int cbMulti = (int)MR32(c->esp + 20);
    int len = cchWide > 0 ? cchWide : 1;
    if (cbMulti == 0) {{
        c->eax = (uint32_t)len;
    }} else {{
        for (int i = 0; i < len && i < cbMulti; ++i) {{
            MR8(dst + i) = (uint8_t)MR16(src + i * 2);
        }}
        c->eax = (uint32_t)len;
    }}
    c->esp += {pop_bytes};
}}"""

    # 8. Windowing & Messaging (USER32)
    if sym == 'RegisterClassExA':
        return f"""void {fn}(CPU *c) {{
    uint32_t lpwcx = MR32(c->esp);
    if (lpwcx) g_wnd_proc = MR32(lpwcx + 8); /* lpfnWndProc */
    c->eax = 0xC001; /* Atom */
    c->esp += {pop_bytes};
}}"""

    if sym == 'CreateWindowExA':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0x00010001u; /* HWND */
    c->esp += {pop_bytes};
}}"""

    if sym in ('DestroyWindow', 'ShowWindow', 'UpdateWindow', 'SetForegroundWindow'):
        return f"""void {fn}(CPU *c) {{
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'SetFocus':
        return f"""void {fn}(CPU *c) {{
    c->eax = MR32(c->esp);
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetForegroundWindow':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0x00010001u;
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetDesktopWindow':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0x00010000u;
    c->esp += {pop_bytes};
}}"""

    if sym in ('GetClientRect', 'GetWindowRect'):
        return f"""void {fn}(CPU *c) {{
    uint32_t pRect = MR32(c->esp + 4);
    if (pRect) {{
        MR32(pRect + 0)  = 0;            /* left */
        MR32(pRect + 4)  = 0;            /* top */
        MR32(pRect + 8)  = g_win_width;  /* right */
        MR32(pRect + 12) = g_win_height; /* bottom */
    }}
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'AdjustWindowRect':
        return f"""void {fn}(CPU *c) {{
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'SetWindowLongA':
        return f"""void {fn}(CPU *c) {{
    c->eax = MR32(c->esp + 8);
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetWindowLongA':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
    c->esp += {pop_bytes};
}}"""

    if sym == 'DefWindowProcA':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
    c->esp += {pop_bytes};
}}"""

    if sym == 'PeekMessageA':
        return f"""void {fn}(CPU *c) {{
    uint32_t pMsg = MR32(c->esp);
    if (g_msg_count > 0 && pMsg) {{
        g_msg_count--;
        MR32(pMsg + 0)  = g_msg_queue[g_msg_count][0]; /* hwnd */
        MR32(pMsg + 4)  = g_msg_queue[g_msg_count][1]; /* message */
        MR32(pMsg + 8)  = g_msg_queue[g_msg_count][2]; /* wParam */
        MR32(pMsg + 12) = g_msg_queue[g_msg_count][3]; /* lParam */
        MR32(pMsg + 16) = (uint32_t)time(NULL);        /* time */
        MR32(pMsg + 20) = 0;                           /* pt.x */
        MR32(pMsg + 24) = 0;                           /* pt.y */
        c->eax = 1;
    }} else {{
        c->eax = 0;
    }}
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetMessageA':
        return f"""void {fn}(CPU *c) {{
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'TranslateMessage':
        return f"""void {fn}(CPU *c) {{
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'DispatchMessageA':
        return f"""void {fn}(CPU *c) {{
    uint32_t pMsg = MR32(c->esp);
    if (g_wnd_proc && pMsg) {{
        uint32_t hwnd = MR32(pMsg + 0);
        uint32_t msg  = MR32(pMsg + 4);
        uint32_t wp   = MR32(pMsg + 8);
        uint32_t lp   = MR32(pMsg + 12);
        uint32_t old_esp = c->esp;
        PUSH32(lp);
        PUSH32(wp);
        PUSH32(msg);
        PUSH32(hwnd);
        DISPATCH_CALL(c, g_wnd_proc);
        c->esp = old_esp;
    }} else {{
        c->eax = 0;
    }}
    c->esp += {pop_bytes};
}}"""

    if sym in ('PostMessageA', 'PostQuitMessage'):
        return f"""void {fn}(CPU *c) {{
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'LoadIconA':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0x00020001u;
    c->esp += {pop_bytes};
}}"""

    if sym == 'LoadCursorA':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0x00020002u;
    c->esp += {pop_bytes};
}}"""

    if sym == 'SetCursor':
        return f"""void {fn}(CPU *c) {{
    c->eax = MR32(c->esp);
    c->esp += {pop_bytes};
}}"""

    if sym == 'ShowCursor':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
    c->esp += {pop_bytes};
}}"""

    if sym == 'SetCapture':
        return f"""void {fn}(CPU *c) {{
    c->eax = MR32(c->esp);
    c->esp += {pop_bytes};
}}"""

    if sym == 'ReleaseCapture':
        return f"""void {fn}(CPU *c) {{
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetKeyState':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
    c->esp += {pop_bytes};
}}"""

    if sym == 'GetKeyboardLayout':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0x04090409u; /* US English */
    c->esp += {pop_bytes};
}}"""

    if sym in ('MapVirtualKeyA', 'MapVirtualKeyExA'):
        return f"""void {fn}(CPU *c) {{
    c->eax = MR32(c->esp);
    c->esp += {pop_bytes};
}}"""

    if sym == 'ToUnicode':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
    c->esp += {pop_bytes};
}}"""

    if sym == 'SendInput':
        return f"""void {fn}(CPU *c) {{
    c->eax = MR32(c->esp);
    c->esp += {pop_bytes};
}}"""

    if sym == 'SystemParametersInfoA':
        return f"""void {fn}(CPU *c) {{
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'EnumDisplaySettingsA':
        return f"""void {fn}(CPU *c) {{
    uint32_t pDev = MR32(c->esp + 8);
    if (pDev) {{
        MR32(pDev + 104) = 32;           /* dmBitsPerPel */
        MR32(pDev + 108) = g_win_width;  /* dmPelsWidth */
        MR32(pDev + 112) = g_win_height; /* dmPelsHeight */
        MR32(pDev + 120) = 60;           /* dmDisplayFrequency */
    }}
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym in ('BeginPaint', 'EndPaint'):
        return f"""void {fn}(CPU *c) {{
    c->eax = 0x00030001u;
    c->esp += {pop_bytes};
}}"""

    if sym == 'IsIconic':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
    c->esp += {pop_bytes};
}}"""

    if sym == 'MessageBoxA':
        return f"""void {fn}(CPU *c) {{
    const char *txt = w32_str(MR32(c->esp + 4));
    const char *cap = w32_str(MR32(c->esp + 8));
    fprintf(stderr, "[MessageBox] %s: %s\\n", cap, txt);
    c->eax = 1; /* IDOK */
    c->esp += {pop_bytes};
}}"""

    if sym == 'wvsprintfA':
        return f"""void {fn}(CPU *c) {{
    uint32_t dst = MR32(c->esp);
    const char *fmt = w32_str(MR32(c->esp + 4));
    if (dst) strcpy((char *)(g_mem + dst), fmt);
    c->eax = (uint32_t)strlen(fmt);
    c->esp += {pop_bytes};
}}"""

    # 9. Registry & Security (ADVAPI32)
    if sym == 'RegOpenKeyExA':
        return f"""void {fn}(CPU *c) {{
    uint32_t phk = MR32(c->esp + 16);
    if (phk) MR32(phk) = 0x80000001u; /* HKEY_CURRENT_USER pseudo */
    c->eax = 0; /* ERROR_SUCCESS */
    c->esp += {pop_bytes};
}}"""

    if sym == 'RegCreateKeyA':
        return f"""void {fn}(CPU *c) {{
    uint32_t phk = MR32(c->esp + 8);
    if (phk) MR32(phk) = 0x80000001u;
    c->eax = 0;
    c->esp += {pop_bytes};
}}"""

    if sym == 'RegCloseKey':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
    c->esp += {pop_bytes};
}}"""

    if sym == 'RegQueryValueExA':
        return f"""void {fn}(CPU *c) {{
    const char *valName = w32_str(MR32(c->esp + 4));
    uint32_t pType = MR32(c->esp + 12);
    uint32_t pData = MR32(c->esp + 16);
    uint32_t pCb   = MR32(c->esp + 20);
    if (pType) MR32(pType) = 1; /* REG_SZ */
    if (pData && pCb && MR32(pCb) > 0) {{
        if (strstr(valName, "Language") || strstr(valName, "Locale")) {{
            strcpy((char *)(g_mem + pData), "English");
        }} else {{
            strcpy((char *)(g_mem + pData), ".");
        }}
    }}
    c->eax = 0; /* ERROR_SUCCESS */
    c->esp += {pop_bytes};
}}"""

    if sym == 'RegSetValueExA':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
    c->esp += {pop_bytes};
}}"""

    if sym == 'CryptAcquireContextA':
        return f"""void {fn}(CPU *c) {{
    uint32_t phProv = MR32(c->esp);
    if (phProv) MR32(phProv) = 0x4000;
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'CryptGenRandom':
        return f"""void {fn}(CPU *c) {{
    uint32_t len = MR32(c->esp + 4);
    uint32_t buf = MR32(c->esp + 8);
    for (uint32_t i = 0; i < len; ++i) MR8(buf + i) = (uint8_t)rand();
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'CryptReleaseContext':
        return f"""void {fn}(CPU *c) {{
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'CheckTokenMembership':
        return f"""void {fn}(CPU *c) {{
    uint32_t pIsMember = MR32(c->esp + 8);
    if (pIsMember) MR32(pIsMember) = 1; /* TRUE */
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'AllocateAndInitializeSid':
        return f"""void {fn}(CPU *c) {{
    uint32_t pSid = MR32(c->esp + 40);
    if (pSid) MR32(pSid) = 0x5000;
    c->eax = 1;
    c->esp += {pop_bytes};
}}"""

    if sym == 'FreeSid':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
    c->esp += {pop_bytes};
}}"""

    # 10. Shell, COM, RPC, Net & C++
    if sym == 'SHGetFolderPathA':
        return f"""void {fn}(CPU *c) {{
    uint32_t pPath = MR32(c->esp + 16);
    if (pPath) strcpy((char *)(g_mem + pPath), ".");
    c->eax = 0; /* S_OK */
    c->esp += {pop_bytes};
}}"""

    if sym == 'CoCreateGuid':
        return f"""void {fn}(CPU *c) {{
    uint32_t pGuid = MR32(c->esp);
    if (pGuid) {{
        for (int i = 0; i < 16; ++i) MR8(pGuid + i) = (uint8_t)rand();
    }}
    c->eax = 0; /* S_OK */
    c->esp += {pop_bytes};
}}"""

    if sym == 'UuidToStringA':
        return f"""void {fn}(CPU *c) {{
    uint32_t pStr = MR32(c->esp + 4);
    uint32_t gstr = guest_heap_alloc(40, 4);
    if (gstr) strcpy((char *)(g_mem + gstr), "00000000-0000-0000-0000-000000000000");
    if (pStr) MR32(pStr) = gstr;
    c->eax = 0; /* RPC_S_OK */
    c->esp += {pop_bytes};
}}"""

    if sym == 'RpcStringFreeA':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0; /* RPC_S_OK */
    c->esp += {pop_bytes};
}}"""

    if sym == 'Netbios':
        return f"""void {fn}(CPU *c) {{
    c->eax = 0; /* NRC_GOODRET */
    c->esp += {pop_bytes};
}}"""

    if fn == 'win32_shim_std_string_copy_ctor':
        return f"""void {fn}(CPU *c) {{
    c->eax = c->ecx;
    c->esp += {pop_bytes};
}}"""

    if fn == 'win32_shim_std_string_dtor':
        return f"""void {fn}(CPU *c) {{
    c->eax = c->ecx;
    c->esp += {pop_bytes};
}}"""

    if fn == 'win32_shim_std_string_ctor_cstr':
        return f"""void {fn}(CPU *c) {{
    c->eax = c->ecx;
    c->esp += {pop_bytes};
}}"""

    # 11. WS2_32 Stubs
    if sym.startswith('WSA') or sym.startswith('ord_'):
        if sym in ('WSAStartup', 'ord_115'):
            return f"""void {fn}(CPU *c) {{
    uint32_t pData = MR32(c->esp + 4);
    if (pData) memset(g_mem + pData, 0, 400);
    c->eax = 0; /* Success */
    c->esp += {pop_bytes};
}}"""
        if sym in ('WSACleanup', 'ord_116'):
            return f"""void {fn}(CPU *c) {{
    c->eax = 0;
    c->esp += {pop_bytes};
}}"""
        if sym in ('ord_8', 'ord_14'): # htons, ntohs
            return f"""void {fn}(CPU *c) {{
    uint32_t val = MR32(c->esp);
    c->eax = ((val & 0xFF) << 8) | ((val >> 8) & 0xFF);
    c->esp += {pop_bytes};
}}"""
        if sym == 'WSAGetLastError' or sym == 'ord_112':
            return f"""void {fn}(CPU *c) {{
    c->eax = 0;
    c->esp += {pop_bytes};
}}"""
        return f"""void {fn}(CPU *c) {{
    c->eax = 0;
    c->esp += {pop_bytes};
}}"""

    # Default fallback
    return f"""void {fn}(CPU *c) {{
    c->eax = 0;
    c->esp += {pop_bytes};
}}"""


def main():
    print(f"Reading target executable from {EXE_PATH} (read-only)...")
    with open(EXE_PATH, 'rb') as f:
        exe_bytes = f.read()

    imports = extract_win32_imports(exe_bytes)
    print(f"Extracted {len(imports)} Win32 core imports.")

    # Generate header
    print(f"Generating {WIN32_H_PATH}...")
    hdr = generate_header(imports)
    with open(WIN32_H_PATH, 'w', encoding='utf-8') as f:
        f.write(hdr)

    # Generate source
    print(f"Generating {WIN32_C_PATH}...")
    src = generate_source(imports)
    with open(WIN32_C_PATH, 'w', encoding='utf-8') as f:
        f.write(src)

    print(f"Successfully generated runtime/win32.h ({len(hdr)} bytes) and runtime/win32.c ({len(src)} bytes)!")


if __name__ == '__main__':
    main()
