/* PortSpeed - C99 stdlib.h declaration header for clangd / IntelliSense */
#ifndef _PORTSPEED_STDLIB_H
#define _PORTSPEED_STDLIB_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

void *malloc(size_t size);
void *calloc(size_t nmemb, size_t size);
void *realloc(void *ptr, size_t size);
void free(void *ptr);

void abort(void);
void exit(int status);
int atexit(void (*function)(void));

int atoi(const char *nptr);
long atol(const char *nptr);
long long atoll(const char *nptr);
double atof(const char *nptr);
long strtol(const char *nptr, char **endptr, int base);
unsigned long strtoul(const char *nptr, char **endptr, int base);
double strtod(const char *nptr, char **endptr);

int abs(int j);
long labs(long j);
long long llabs(long long j);

void qsort(void *base, size_t nmemb, size_t size, int (*compar)(const void *, const void *));
void *bsearch(const void *key, const void *base, size_t nmemb, size_t size, int (*compar)(const void *, const void *));

char *getenv(const char *name);
int system(const char *command);

int rand(void);
void srand(unsigned int seed);

#ifdef __cplusplus
}
#endif

#endif /* _PORTSPEED_STDLIB_H */

