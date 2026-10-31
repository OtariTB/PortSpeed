/* Need for Speed ProStreet - Static C++ Initializer Chain & MSVC Hook Header.
 *
 * Maps and executes the 960 static C++ initializers and C runtime initializers
 * located in the authentic .rdata section of nfs.exe, along with the atexit
 * helper (sub_0082851b).
 */
#ifndef PROSTREET_INITTERM_H
#define PROSTREET_INITTERM_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "cpu.h"
#include "memory.h"
#include "crt.h"

#ifdef __cplusplus
extern "C" {
#endif

/* --------------------------------------------------------------------------
 * Authentic Initializer Table Virtual Addresses in .rdata
 * -------------------------------------------------------------------------- */
#define GUEST_XI_A            0x0096a1f8u /* C initializers start */
#define GUEST_XI_Z            0x0096a204u /* C initializers end */
#define GUEST_XC_A            0x00967608u /* C++ constructors start */
#define GUEST_XC_Z            0x0096a1f4u /* C++ constructors end */

/* Total slots: 2811, Non-null constructors: 960 */
#define GUEST_TOTAL_CPP_CTORS 960u

/* Authentic MSVC __onexit / atexit helper hook address */
#define GUEST_SUB_0082851B    0x0082851bu

/* --------------------------------------------------------------------------
 * Subsystem API
 * -------------------------------------------------------------------------- */
/* Install hooks into g_dtab (specifically hooking sub_0082851b) */
void initterm_install_hooks(void);

/* Execute C initializers table (_initterm_e [0x0096a1f8..0x0096a204]). Returns 0 on success. */
int initterm_run_c_initializers(CPU *c);

/* Execute C++ constructors table (_initterm [0x00967608..0x0096a1f4]). Returns number of constructors executed (960). */
uint32_t initterm_run_cpp_constructors(CPU *c);

/* Execute all registered onexit / atexit destructors in reverse order (LIFO) */
void initterm_run_exit_destructors(CPU *c);

/* Hook implementation for sub_0082851b */
void hook_sub_0082851b(CPU *c);

#ifdef __cplusplus
}
#endif

#endif /* PROSTREET_INITTERM_H */

