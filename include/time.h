/* PortSpeed - C99 time.h declaration header for clangd / IntelliSense */
#ifndef _PORTSPEED_TIME_H
#define _PORTSPEED_TIME_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef long long time_t;
typedef long long clock_t;

struct tm {
    int tm_sec;
    int tm_min;
    int tm_hour;
    int tm_mday;
    int tm_mon;
    int tm_year;
    int tm_wday;
    int tm_yday;
    int tm_isdst;
};

time_t time(time_t *tloc);
clock_t clock(void);
double difftime(time_t time1, time_t time0);
time_t mktime(struct tm *timeptr);

struct tm *gmtime(const time_t *timer);
struct tm *localtime(const time_t *timer);
char *asctime(const struct tm *timeptr);
char *ctime(const time_t *timer);
size_t strftime(char *s, size_t maxsize, const char *format, const struct tm *timeptr);

#ifdef __cplusplus
}
#endif

#endif /* _PORTSPEED_TIME_H */

