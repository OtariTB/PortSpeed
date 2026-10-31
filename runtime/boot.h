/* Need for Speed ProStreet - Engine Boot & Lifecycle Orchestrator Header.
 *
 * Coordinates memory initialization, IAT binding, static initializers,
 * command-line setup, and invocation of the authentic main() (sub_004afee0).
 */
#ifndef PROSTREET_BOOT_H
#define PROSTREET_BOOT_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "cpu.h"
#include "memory.h"
#include "crt.h"
#include "win32.h"
#include "initterm.h"

#ifdef __cplusplus
extern "C" {
#endif

/* --------------------------------------------------------------------------
 * Boot Constants & Addresses
 * -------------------------------------------------------------------------- */
#define GUEST_MAIN_ENTRY_VA       0x004afee0u
#define GUEST_SAFEMODE_CHECK_VA   0x004afea0u
#define GUEST_DUMMY_RETURN_VA     0x00828ae0u

#define GUEST_GLOBAL_SAFEMODE     0x00ac7378u
#define GUEST_GLOBAL_EVENTS       0x00bbad1cu
#define GUEST_GLOBAL_QUIT         0x00abae68u

/* Boot lifecycle stages */
typedef enum {
    BOOT_STAGE_UNINITIALIZED   = 0,
    BOOT_STAGE_MEMORY_READY     = 1,
    BOOT_STAGE_IAT_BOUND        = 2,
    BOOT_STAGE_HOOKS_INSTALLED  = 3,
    BOOT_STAGE_INITTERM_DONE    = 4,
    BOOT_STAGE_MAIN_ENTERED     = 5,
    BOOT_STAGE_MAIN_EXITED      = 6
} boot_stage_t;

/* Subsystem boot status */
typedef struct {
    boot_stage_t stage;
    int argc;
    bool is_safemode;
    uint32_t c_init_result;
    uint32_t cpp_ctors_count;
    uint32_t event_handles[4];
    uint32_t engine_object_ptr;
    int exit_code;
} boot_status_t;

/* Get current boot status */
const boot_status_t *boot_get_status(void);

/* Reset boot subsystem status (useful for test isolation) */
void boot_reset_status(void);

/* Individual boot lifecycle phases */
bool boot_init_memory(const uint8_t *pe_bytes, size_t pe_size);
void boot_bind_iats(void);
void boot_install_hooks(void);
bool boot_run_initializers(CPU *c);
void boot_setup_arguments(CPU *c, int argc, const char **argv);
int boot_invoke_main(CPU *c, bool dry_run);

/* Complete end-to-end boot chain */
int boot_engine(const uint8_t *pe_bytes, size_t pe_size, int argc, const char **argv, bool dry_run);

#ifdef __cplusplus
}
#endif

#endif /* PROSTREET_BOOT_H */

