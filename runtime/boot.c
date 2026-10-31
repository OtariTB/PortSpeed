/* Need for Speed ProStreet - Engine Boot & Lifecycle Orchestrator Implementation.
 *
 * Coordinates memory initialization, IAT binding, static initializers,
 * command-line setup, and invocation of the authentic main() (sub_004afee0).
 */
#include "boot.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static boot_status_t g_boot_status = {
    .stage = BOOT_STAGE_UNINITIALIZED,
    .argc = 0,
    .is_safemode = false,
    .c_init_result = 0,
    .cpp_ctors_count = 0,
    .event_handles = {0, 0, 0, 0},
    .engine_object_ptr = 0,
    .exit_code = 0
};

const boot_status_t *boot_get_status(void) {
    return &g_boot_status;
}

void boot_reset_status(void) {
    memset(&g_boot_status, 0, sizeof(g_boot_status));
    g_boot_status.stage = BOOT_STAGE_UNINITIALIZED;
}

static void hook_safemode_check(CPU *c) {
    c->eax = g_boot_status.is_safemode ? 1u : 0u;
}

static void hook_dos_header_check(CPU *c) {
    c->eax = 0u;
}

static void hook_security_cookie(CPU *c) {
    if (g_mem != NULL) {
        MR32(0x0100f4ccu) = 0xbb40e64eu;
    }
    c->eax = 0u;
}

bool boot_init_memory(const uint8_t *pe_bytes, size_t pe_size) {
    if (!guest_memory_init()) {
        return false;
    }

    if (pe_bytes != NULL && pe_size > 0) {
        if (!guest_memory_load_pe(pe_bytes, pe_size)) {
            return false;
        }
    }

    g_boot_status.stage = BOOT_STAGE_MEMORY_READY;
    return true;
}

void boot_bind_iats(void) {
    crt_init_iat();
    win32_init_iat();
    g_boot_status.stage = BOOT_STAGE_IAT_BOUND;
}

void boot_install_hooks(void) {
    /* Install sub_0082851b hook for atexit registrations */
    initterm_install_hooks();

    /* Write authentic DOS signature 'MZ' at 0x00400000 */
    if (g_mem != NULL) {
        *(uint16_t *)(g_mem + 0x00400000u) = 0x5a4du;
    }

    /* Install hooks into g_dtab */
    uint32_t off_safe = GUEST_SAFEMODE_CHECK_VA - DISPATCH_TEXT_BASE;
    if (off_safe < DISPATCH_TEXT_SIZE) {
        g_dtab[off_safe] = hook_safemode_check;
    }

    uint32_t off_dos = 0x00828b43u - DISPATCH_TEXT_BASE;
    if (off_dos < DISPATCH_TEXT_SIZE) {
        g_dtab[off_dos] = hook_dos_header_check;
    }

    uint32_t off_cookie = 0x00828feeu - DISPATCH_TEXT_BASE;
    if (off_cookie < DISPATCH_TEXT_SIZE) {
        g_dtab[off_cookie] = hook_security_cookie;
    }

    g_boot_status.stage = BOOT_STAGE_HOOKS_INSTALLED;
}

bool boot_run_initializers(CPU *c) {
    if (c == NULL) return false;

    int c_rc = initterm_run_c_initializers(c);
    g_boot_status.c_init_result = (uint32_t)c_rc;
    if (c_rc != 0) {
        return false;
    }

    uint32_t cpp_count = initterm_run_cpp_constructors(c);
    g_boot_status.cpp_ctors_count = cpp_count;
    g_boot_status.stage = BOOT_STAGE_INITTERM_DONE;
    return true;
}

void boot_setup_arguments(CPU *c, int argc, const char **argv) {
    if (c == NULL) return;

    if (argc < 1 || argv == NULL) {
        static const char *default_argv[] = { "nfs.exe" };
        argc = 1;
        argv = default_argv;
    }

    g_boot_status.argc = argc;
    g_boot_status.is_safemode = false;
    for (int i = 0; i < argc; i++) {
        if (argv[i] && _stricmp(argv[i], "-safemode") == 0) {
            g_boot_status.is_safemode = true;
            break;
        }
    }

    if (g_mem == NULL) return;

    /* Write argument strings into guest heap memory */
    uint32_t str_cur = 0x00102000u;
    uint32_t arg_ptrs[64];
    int count = argc < 64 ? argc : 64;

    for (int i = 0; i < count; i++) {
        const char *s = argv[i] ? argv[i] : "";
        size_t len = strlen(s) + 1;
        memcpy(g_mem + str_cur, s, len);
        arg_ptrs[i] = str_cur;
        str_cur += (uint32_t)((len + 3u) & ~3u);
    }

    /* Write argv table [arg0_ptr, arg1_ptr, ..., 0] at GUEST_ARGV_TAB_ADDR (0x00102100) */
    uint32_t tab_va = GUEST_ARGV_TAB_ADDR;
    for (int i = 0; i < count; i++) {
        MR32(tab_va) = arg_ptrs[i];
        tab_va += 4;
    }
    MR32(tab_va) = 0u;

    /* Write envp table [0] at GUEST_ENVP_TAB_ADDR (0x00102200) */
    MR32(GUEST_ENVP_TAB_ADDR) = 0u;

    /* Populate MSVC CRT global variables for __getmainargs */
    MR32(0x00b33a64u) = (uint32_t)argc;
    MR32(0x00b33a6cu) = GUEST_ARGV_TAB_ADDR;
    MR32(0x00b33a68u) = GUEST_ENVP_TAB_ADDR;

    /* Set up stack frame for sub_004afee0(argc, argv, envp) */
    c->esp = GUEST_STACK_TOP;
    c->esp -= 4; MR32(c->esp) = GUEST_ENVP_TAB_ADDR;
    c->esp -= 4; MR32(c->esp) = GUEST_ARGV_TAB_ADDR;
    c->esp -= 4; MR32(c->esp) = (uint32_t)argc;
    c->esp -= 4; MR32(c->esp) = GUEST_DUMMY_RETURN_VA;
}

int boot_invoke_main(CPU *c, bool dry_run) {
    if (c == NULL) return -1;

    g_boot_status.stage = BOOT_STAGE_MAIN_ENTERED;

    if (dry_run) {
        /* 1. Safe mode evaluation */
        if (g_boot_status.is_safemode && g_mem != NULL) {
            MR32(GUEST_GLOBAL_SAFEMODE) = 1u;
        }

        /* 2. Emulate CreateEventA creation of 4 synchronization events */
        if (g_mem != NULL) {
            for (int i = 0; i < 4; i++) {
                c->esp -= 16;
                MR32(c->esp) = 0u;
                MR32(c->esp + 4) = 1u;
                MR32(c->esp + 8) = 0u;
                MR32(c->esp + 12) = 0u;
                win32_shim_CreateEventA(c);
                c->esp += 16;
                uint32_t h = c->eax;
                g_boot_status.event_handles[i] = h;
                MR32(GUEST_GLOBAL_EVENTS + (uint32_t)i * 4u) = h;
            }

            /* 3. Allocate 4-byte root engine object */
            uint32_t obj_ptr = guest_heap_alloc(4, 4);
            if (obj_ptr) {
                MR32(obj_ptr) = 0u;
                MR32(0x00bfc024u) = obj_ptr;
                g_boot_status.engine_object_ptr = obj_ptr;

                /* 4. Update TLS array via fs:[0x2c] */
                uint32_t tls_arr = MR32(c->fs_base + 0x2cu);
                uint32_t tls_slot0 = MR32(tls_arr);
                MR32(0x00bfc02cu) = obj_ptr;
                MR32(tls_slot0 + 4u) = obj_ptr;
            }

            /* 5. Set quit flag for clean main loop termination */
            MR32(GUEST_GLOBAL_QUIT) = 1u;

            /* 6. Close event handles */
            for (int i = 0; i < 4; i++) {
                if (g_boot_status.event_handles[i]) {
                    c->esp -= 4;
                    MR32(c->esp) = g_boot_status.event_handles[i];
                    win32_shim_CloseHandle(c);
                    c->esp += 4;
                }
            }

            /* 7. Run exit destructors */
            initterm_run_exit_destructors(c);
        }

        g_boot_status.stage = BOOT_STAGE_MAIN_EXITED;
        g_boot_status.exit_code = 0;
        return 0;
    }

    /* Normal full dispatch of sub_004afee0 */
    DISPATCH_CALL(c, GUEST_MAIN_ENTRY_VA);
    g_boot_status.stage = BOOT_STAGE_MAIN_EXITED;
    g_boot_status.exit_code = (int)c->eax;
    return g_boot_status.exit_code;
}

int boot_engine(const uint8_t *pe_bytes, size_t pe_size, int argc, const char **argv, bool dry_run) {
    boot_reset_status();

    if (!boot_init_memory(pe_bytes, pe_size)) {
        return -1;
    }

    boot_bind_iats();
    boot_install_hooks();

    CPU cpu;
    guest_cpu_init(&cpu, GUEST_MAIN_ENTRY_VA);

    if (!boot_run_initializers(&cpu)) {
        return -2;
    }

    boot_setup_arguments(&cpu, argc, argv);
    return boot_invoke_main(&cpu, dry_run);
}

