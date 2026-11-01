/* Need for Speed ProStreet - Static C++ Initializer Chain & MSVC Hook Implementation.
 */
#include "initterm.h"
#include "boot.h"
#include <stdio.h>
#include <string.h>

void hook_sub_0082851b(CPU *c) {
    /* sub_0082851b is the authentic __cdecl atexit / __onexit registration helper:
     *   int __cdecl sub_0082851b(void (*dtor)(void));
     * Arg 0 is at c->esp.
     * Returns 0 on success, non-zero on failure.
     */
    uint32_t dtor_va = MR32(c->esp);
    uint32_t res = crt_register_onexit(dtor_va);
    c->eax = res ? 0 : (uint32_t)-1;
}

void initterm_install_hooks(void) {
    /* Hook sub_0082851b in g_dtab so constructor calls to atexit register reliably */
    uint32_t offset = GUEST_SUB_0082851B - DISPATCH_TEXT_BASE;
    if (offset < DISPATCH_TEXT_SIZE) {
        g_dtab[offset] = hook_sub_0082851b;
    }
}

int initterm_run_c_initializers(CPU *c) {
    /* Run _initterm_e on __xi_a .. __xi_z */
    uint32_t saved_esp = c->esp;
    GUEST_PUSH32(c, GUEST_XI_Z);
    GUEST_PUSH32(c, GUEST_XI_A);
    crt_shim__initterm_e(c);
    c->esp = saved_esp;
    return (int)c->eax;
}

uint32_t initterm_run_cpp_constructors(CPU *c) {
    /* Iterate and count constructors executed */
    uint32_t count = 0;
    for (uint32_t p = GUEST_XC_A; p < GUEST_XC_Z; p += 4) {
        uint32_t fn_va = MR32(p);
        if (fn_va != 0) {
            uint32_t saved_esp = c->esp;
            GUEST_PUSH32(c, GUEST_DUMMY_RETURN_VA);
            DISPATCH_CALL(c, fn_va);
            c->esp = saved_esp;
            count++;
        }
    }
    return count;
}

void initterm_run_exit_destructors(CPU *c) {
    crt_run_exit_handlers(c);
}

