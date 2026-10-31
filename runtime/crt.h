/* Need for Speed ProStreet - MSVCR80.dll IAT Shim Layer Header.
 *
 * Automatically generated from target binary PE import directory.
 * Total imported MSVCR80 symbols: 156.
 * Virtual address range: 0x009671d4 .. 0x00967440.
 */
#ifndef PROSTREET_CRT_H
#define PROSTREET_CRT_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "cpu.h"
#include "memory.h"

#ifdef __cplusplus
extern "C" {
#endif

/* --------------------------------------------------------------------------
 * Guest Runtime Metadata Layout (in TEB/TLS reserved page)
 * -------------------------------------------------------------------------- */
#define GUEST_CRT_BASE         0x00101000u
#define GUEST_COMMODE_ADDR     (GUEST_CRT_BASE + 0x00u)
#define GUEST_FMODE_ADDR       (GUEST_CRT_BASE + 0x04u)
#define GUEST_INITENV_ADDR     (GUEST_CRT_BASE + 0x08u)
#define GUEST_IOB_ADDR         (GUEST_CRT_BASE + 0x10u) /* 3 * 32 = 96 bytes */
#define GUEST_ARGV_STR_ADDR    (GUEST_CRT_BASE + 0x80u) /* 'nfs.exe' */
#define GUEST_ARGV_TAB_ADDR    (GUEST_CRT_BASE + 0x100u)/* [GUEST_ARGV_STR_ADDR, 0] */
#define GUEST_ENVP_TAB_ADDR    (GUEST_CRT_BASE + 0x110u)/* [0] */
#define GUEST_TM_ADDR          (GUEST_CRT_BASE + 0x140u)/* struct tm */
#define GUEST_ASCTIME_ADDR     (GUEST_CRT_BASE + 0x180u)/* asctime buffer */
#define GUEST_GETCWD_ADDR      (GUEST_CRT_BASE + 0x200u)/* cwd buffer */

/* --------------------------------------------------------------------------
 * CRT Import Record
 * -------------------------------------------------------------------------- */
typedef struct {
    uint32_t    slot_va;
    const char *symbol_name;
    guest_fn_t  handler;
} crt_import_entry_t;

/* --------------------------------------------------------------------------
 * MSVCR80.dll Shim Function Declarations (156 functions)
 * -------------------------------------------------------------------------- */
void crt_shim__endthreadex(struct CPU *c); /* 0x009671d4: _endthreadex */
void crt_shim__beginthreadex(struct CPU *c); /* 0x009671d8: _beginthreadex */
void crt_shim_bsearch(struct CPU *c); /* 0x009671dc: bsearch */
void crt_shim__vsnwprintf(struct CPU *c); /* 0x009671e0: _vsnwprintf */
void crt_shim_getenv(struct CPU *c); /* 0x009671e4: getenv */
void crt_shim__findclose(struct CPU *c); /* 0x009671e8: _findclose */
void crt_shim__findnext64i32(struct CPU *c); /* 0x009671ec: _findnext64i32 */
void crt_shim__findfirst64i32(struct CPU *c); /* 0x009671f0: _findfirst64i32 */
void crt_shim__getdiskfree(struct CPU *c); /* 0x009671f4: _getdiskfree */
void crt_shim_memmove_s(struct CPU *c); /* 0x009671f8: memmove_s */
void crt_shim_std_exception_dtor(struct CPU *c); /* 0x009671fc: ??1exception@std@@UAE@XZ */
void crt_shim_std_exception_default_ctor(struct CPU *c); /* 0x00967200: ??0exception@std@@QAE@XZ */
void crt_shim_std_exception_copy_ctor(struct CPU *c); /* 0x00967204: ??0exception@std@@QAE@ABV01@@Z */
void crt_shim_memmove(struct CPU *c); /* 0x00967208: memmove */
void crt_shim__invalid_parameter_noinfo(struct CPU *c); /* 0x0096720c: _invalid_parameter_noinfo */
void crt_shim__purecall(struct CPU *c); /* 0x00967210: _purecall */
void crt_shim_free(struct CPU *c); /* 0x00967214: free */
void crt_shim_malloc(struct CPU *c); /* 0x00967218: malloc */
void crt_shim_printf(struct CPU *c); /* 0x0096721c: printf */
void crt_shim__getdrive(struct CPU *c); /* 0x00967220: _getdrive */
void crt_shim_strncat(struct CPU *c); /* 0x00967224: strncat */
void crt_shim_sscanf(struct CPU *c); /* 0x00967228: sscanf */
void crt_shim_isspace(struct CPU *c); /* 0x0096722c: isspace */
void crt_shim_strstr(struct CPU *c); /* 0x00967230: strstr */
void crt_shim_strchr(struct CPU *c); /* 0x00967234: strchr */
void crt_shim_atoi(struct CPU *c); /* 0x00967238: atoi */
void crt_shim_strncpy(struct CPU *c); /* 0x0096723c: strncpy */
void crt_shim_strrchr(struct CPU *c); /* 0x00967240: strrchr */
void crt_shim_atof(struct CPU *c); /* 0x00967244: atof */
void crt_shim_qsort(struct CPU *c); /* 0x00967248: qsort */
void crt_shim_ceil(struct CPU *c); /* 0x0096724c: ceil */
void crt_shim_vsprintf(struct CPU *c); /* 0x00967250: vsprintf */
void crt_shim__isnan(struct CPU *c); /* 0x00967254: _isnan */
void crt_shim_exit(struct CPU *c); /* 0x00967258: exit */
void crt_shim__stricmp(struct CPU *c); /* 0x0096725c: _stricmp */
void crt_shim__exit(struct CPU *c); /* 0x00967260: _exit */
void crt_shim_rand(struct CPU *c); /* 0x00967264: rand */
void crt_shim__CIsqrt(struct CPU *c); /* 0x00967268: _CIsqrt */
void crt_shim___CxxFrameHandler3(struct CPU *c); /* 0x0096726c: __CxxFrameHandler3 */
void crt_shim_memset(struct CPU *c); /* 0x00967270: memset */
void crt_shim_memcpy(struct CPU *c); /* 0x00967274: memcpy */
void crt_shim__CIfmod(struct CPU *c); /* 0x00967278: _CIfmod */
void crt_shim__CIpow(struct CPU *c); /* 0x0096727c: _CIpow */
void crt_shim__CIsin(struct CPU *c); /* 0x00967280: _CIsin */
void crt_shim_tolower(struct CPU *c); /* 0x00967284: tolower */
void crt_shim__CxxThrowException(struct CPU *c); /* 0x00967288: _CxxThrowException */
void crt_shim__CIacos(struct CPU *c); /* 0x0096728c: _CIacos */
void crt_shim__CIatan2(struct CPU *c); /* 0x00967290: _CIatan2 */
void crt_shim__CIcos(struct CPU *c); /* 0x00967294: _CIcos */
void crt_shim___iob_func(struct CPU *c); /* 0x00967298: __iob_func */
void crt_shim_strncmp(struct CPU *c); /* 0x0096729c: strncmp */
void crt_shim_fclose(struct CPU *c); /* 0x009672a0: fclose */
void crt_shim_fopen(struct CPU *c); /* 0x009672a4: fopen */
void crt_shim__CIexp(struct CPU *c); /* 0x009672a8: _CIexp */
void crt_shim_floor(struct CPU *c); /* 0x009672ac: floor */
void crt_shim__CIasin(struct CPU *c); /* 0x009672b0: _CIasin */
void crt_shim_longjmp(struct CPU *c); /* 0x009672b4: longjmp */
void crt_shim__setjmp3(struct CPU *c); /* 0x009672b8: _setjmp3 */
void crt_shim_strcspn(struct CPU *c); /* 0x009672bc: strcspn */
void crt_shim_strcoll(struct CPU *c); /* 0x009672c0: strcoll */
void crt_shim_fprintf(struct CPU *c); /* 0x009672c4: fprintf */
void crt_shim_isprint(struct CPU *c); /* 0x009672c8: isprint */
void crt_shim__CIlog(struct CPU *c); /* 0x009672cc: _CIlog */
void crt_shim__mktime64(struct CPU *c); /* 0x009672d0: _mktime64 */
void crt_shim__getcwd(struct CPU *c); /* 0x009672d4: _getcwd */
void crt_shim___RTDynamicCast(struct CPU *c); /* 0x009672d8: __RTDynamicCast */
void crt_shim_toupper(struct CPU *c); /* 0x009672dc: toupper */
void crt_shim_fseek(struct CPU *c); /* 0x009672e0: fseek */
void crt_shim__chmod(struct CPU *c); /* 0x009672e4: _chmod */
void crt_shim_rename(struct CPU *c); /* 0x009672e8: rename */
void crt_shim_remove(struct CPU *c); /* 0x009672ec: remove */
void crt_shim__ftime64(struct CPU *c); /* 0x009672f0: _ftime64 */
void crt_shim__time64(struct CPU *c); /* 0x009672f4: _time64 */
void crt_shim_strtok(struct CPU *c); /* 0x009672f8: strtok */
void crt_shim_strtoul(struct CPU *c); /* 0x009672fc: strtoul */
void crt_shim__strnicmp(struct CPU *c); /* 0x00967300: _strnicmp */
void crt_shim__mkdir(struct CPU *c); /* 0x00967304: _mkdir */
void crt_shim__ltoa(struct CPU *c); /* 0x00967308: _ltoa */
void crt_shim_strlen(struct CPU *c); /* 0x0096730c: strlen */
void crt_shim_memcmp(struct CPU *c); /* 0x00967310: memcmp */
void crt_shim__snprintf(struct CPU *c); /* 0x00967314: _snprintf */
void crt_shim__vsnprintf(struct CPU *c); /* 0x00967318: _vsnprintf */
void crt_shim_cos(struct CPU *c); /* 0x0096731c: cos */
void crt_shim_sqrt(struct CPU *c); /* 0x00967320: sqrt */
void crt_shim_fflush(struct CPU *c); /* 0x00967324: fflush */
void crt_shim_srand(struct CPU *c); /* 0x00967328: srand */
void crt_shim_strcpy(struct CPU *c); /* 0x0096732c: strcpy */
void crt_shim_calloc(struct CPU *c); /* 0x00967330: calloc */
void crt_shim_strcmp(struct CPU *c); /* 0x00967334: strcmp */
void crt_shim_strcat(struct CPU *c); /* 0x00967338: strcat */
void crt_shim_raise(struct CPU *c); /* 0x0096733c: raise */
void crt_shim_realloc(struct CPU *c); /* 0x00967340: realloc */
void crt_shim_abs(struct CPU *c); /* 0x00967344: abs */
void crt_shim_clock(struct CPU *c); /* 0x00967348: clock */
void crt_shim_strcpy_s(struct CPU *c); /* 0x0096734c: strcpy_s */
void crt_shim_strncpy_s(struct CPU *c); /* 0x00967350: strncpy_s */
void crt_shim_memcpy_s(struct CPU *c); /* 0x00967354: memcpy_s */
void crt_shim_sprintf_s(struct CPU *c); /* 0x00967358: sprintf_s */
void crt_shim_vsprintf_s(struct CPU *c); /* 0x0096735c: vsprintf_s */
void crt_shim__vscprintf(struct CPU *c); /* 0x00967360: _vscprintf */
void crt_shim_strtol(struct CPU *c); /* 0x00967364: strtol */
void crt_shim__itoa_s(struct CPU *c); /* 0x00967368: _itoa_s */
void crt_shim__unlock(struct CPU *c); /* 0x0096736c: _unlock */
void crt_shim__encode_pointer(struct CPU *c); /* 0x00967370: _encode_pointer */
void crt_shim___dllonexit(struct CPU *c); /* 0x00967374: __dllonexit */
void crt_shim__lock(struct CPU *c); /* 0x00967378: _lock */
void crt_shim__onexit(struct CPU *c); /* 0x0096737c: _onexit */
void crt_shim__decode_pointer(struct CPU *c); /* 0x00967380: _decode_pointer */
void crt_shim_terminate(struct CPU *c); /* 0x00967384: ?terminate@@YAXXZ */
void crt_shim__amsg_exit(struct CPU *c); /* 0x00967388: _amsg_exit */
void crt_shim___getmainargs(struct CPU *c); /* 0x0096738c: __getmainargs */
void crt_shim__cexit(struct CPU *c); /* 0x00967390: _cexit */
void crt_shim__XcptFilter(struct CPU *c); /* 0x00967394: _XcptFilter */
void crt_shim___initenv(struct CPU *c); /* 0x00967398: __initenv */
void crt_shim__initterm(struct CPU *c); /* 0x0096739c: _initterm */
void crt_shim__initterm_e(struct CPU *c); /* 0x009673a0: _initterm_e */
void crt_shim__configthreadlocale(struct CPU *c); /* 0x009673a4: _configthreadlocale */
void crt_shim___setusermatherr(struct CPU *c); /* 0x009673a8: __setusermatherr */
void crt_shim__adjust_fdiv(struct CPU *c); /* 0x009673ac: _adjust_fdiv */
void crt_shim___p__commode(struct CPU *c); /* 0x009673b0: __p__commode */
void crt_shim___p__fmode(struct CPU *c); /* 0x009673b4: __p__fmode */
void crt_shim___set_app_type(struct CPU *c); /* 0x009673b8: __set_app_type */
void crt_shim__localtime32(struct CPU *c); /* 0x009673bc: _localtime32 */
void crt_shim__crt_debugger_hook(struct CPU *c); /* 0x009673c0: _crt_debugger_hook */
void crt_shim__except_handler4_common(struct CPU *c); /* 0x009673c4: _except_handler4_common */
void crt_shim_type_info_dtor(struct CPU *c); /* 0x009673c8: ?_type_info_dtor_internal_method@type_info@@QAEXXZ */
void crt_shim__invoke_watson(struct CPU *c); /* 0x009673cc: _invoke_watson */
void crt_shim__controlfp_s(struct CPU *c); /* 0x009673d0: _controlfp_s */
void crt_shim__difftime64(struct CPU *c); /* 0x009673d4: _difftime64 */
void crt_shim_strpbrk(struct CPU *c); /* 0x009673d8: strpbrk */
void crt_shim_asctime(struct CPU *c); /* 0x009673dc: asctime */
void crt_shim__mkgmtime64(struct CPU *c); /* 0x009673e0: _mkgmtime64 */
void crt_shim__gmtime64(struct CPU *c); /* 0x009673e4: _gmtime64 */
void crt_shim_fwrite(struct CPU *c); /* 0x009673e8: fwrite */
void crt_shim__localtime64(struct CPU *c); /* 0x009673ec: _localtime64 */
void crt_shim__fullpath(struct CPU *c); /* 0x009673f0: _fullpath */
void crt_shim__close(struct CPU *c); /* 0x009673f4: _close */
void crt_shim__write(struct CPU *c); /* 0x009673f8: _write */
void crt_shim_mangled_open(struct CPU *c); /* 0x009673fc: ?_open@@YAHPBDHH@Z */
void crt_shim__lseek(struct CPU *c); /* 0x00967400: _lseek */
void crt_shim__read(struct CPU *c); /* 0x00967404: _read */
void crt_shim__filelength(struct CPU *c); /* 0x00967408: _filelength */
void crt_shim__rmdir(struct CPU *c); /* 0x0096740c: _rmdir */
void crt_shim_isdigit(struct CPU *c); /* 0x00967410: isdigit */
void crt_shim__CIlog10(struct CPU *c); /* 0x00967414: _CIlog10 */
void crt_shim__CItan(struct CPU *c); /* 0x00967418: _CItan */
void crt_shim_ldexp(struct CPU *c); /* 0x0096741c: ldexp */
void crt_shim__except_handler3(struct CPU *c); /* 0x00967420: _except_handler3 */
void crt_shim__aligned_malloc(struct CPU *c); /* 0x00967424: _aligned_malloc */
void crt_shim__aligned_free(struct CPU *c); /* 0x00967428: _aligned_free */
void crt_shim__control87(struct CPU *c); /* 0x0096742c: _control87 */
void crt_shim__CItanh(struct CPU *c); /* 0x00967430: _CItanh */
void crt_shim__CIsinh(struct CPU *c); /* 0x00967434: _CIsinh */
void crt_shim__CIcosh(struct CPU *c); /* 0x00967438: _CIcosh */
void crt_shim_sprintf(struct CPU *c); /* 0x0096743c: sprintf */
void crt_shim__CIatan(struct CPU *c); /* 0x00967440: _CIatan */

/* --------------------------------------------------------------------------
 * CRT Subsystem Management API
 * -------------------------------------------------------------------------- */
void crt_init_iat(void);
void crt_run_exit_handlers(struct CPU *c);
uint32_t crt_register_onexit(uint32_t fn_va);
uint32_t crt_get_onexit_count(void);
size_t crt_get_import_count(void);
const crt_import_entry_t *crt_get_import_table(void);

#ifdef __cplusplus
}
#endif

#endif /* PROSTREET_CRT_H */
