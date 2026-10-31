/* PortSpeed - C99 stdio.h declaration header for clangd / IntelliSense */
#ifndef _PORTSPEED_STDIO_H
#define _PORTSPEED_STDIO_H

#include <stddef.h>
#include <stdarg.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct FILE FILE;

extern FILE *stdin;
extern FILE *stdout;
extern FILE *stderr;

#define SEEK_SET 0
#define SEEK_CUR 1
#define SEEK_END 2
#define EOF (-1)

int printf(const char *format, ...);
int fprintf(FILE *stream, const char *format, ...);
int sprintf(char *str, const char *format, ...);
int snprintf(char *str, size_t size, const char *format, ...);
int vsnprintf(char *str, size_t size, const char *format, va_list ap);
int vsprintf(char *str, const char *format, va_list ap);
int vprintf(const char *format, va_list ap);
int vfprintf(FILE *stream, const char *format, va_list ap);

int sscanf(const char *str, const char *format, ...);
int fscanf(FILE *stream, const char *format, ...);

FILE *fopen(const char *pathname, const char *mode);
int fclose(FILE *stream);
size_t fread(void *ptr, size_t size, size_t nmemb, FILE *stream);
size_t fwrite(const void *ptr, size_t size, size_t nmemb, FILE *stream);
int fseek(FILE *stream, long offset, int whence);
long ftell(FILE *stream);
void rewind(FILE *stream);
int fflush(FILE *stream);
int ferror(FILE *stream);
int feof(FILE *stream);
void clearerr(FILE *stream);

int fputs(const char *s, FILE *stream);
int puts(const char *s);
char *fgets(char *s, int size, FILE *stream);
int fputc(int c, FILE *stream);
int fgetc(FILE *stream);

int remove(const char *pathname);
int rename(const char *oldpath, const char *newpath);

#ifdef __cplusplus
}
#endif

#endif /* _PORTSPEED_STDIO_H */

