/* PortSpeed - C99 math.h declaration header for clangd / IntelliSense */
#ifndef _PORTSPEED_MATH_H
#define _PORTSPEED_MATH_H

#include <float.h>

#ifndef NAN
#define NAN (__builtin_nanf(""))
#endif

#ifndef INFINITY
#define INFINITY (__builtin_inff())
#endif

#ifdef __cplusplus
extern "C" {
#endif

double floor(double x);
float floorf(float x);
double ceil(double x);
float ceilf(float x);
double trunc(double x);
float truncf(float x);
double round(double x);
float roundf(float x);
double nearbyint(double x);
float nearbyintf(float x);

double fabs(double x);
float fabsf(float x);
double sqrt(double x);
float sqrtf(float x);

double sin(double x);
float sinf(float x);
double cos(double x);
float cosf(float x);
double tan(double x);
float tanf(float x);
double asin(double x);
float asinf(float x);
double acos(double x);
float acosf(float x);
double atan(double x);
float atanf(float x);
double atan2(double y, double x);
float atan2f(float y, float x);

double sinh(double x);
double cosh(double x);
double tanh(double x);

double exp(double x);
double log(double x);
double log10(double x);
double pow(double base, double exp);
double ldexp(double x, int exp);
double frexp(double x, int *exp);
double modf(double x, double *iptr);
double fmod(double x, double y);

#ifdef __cplusplus
}
#endif

#endif /* _PORTSPEED_MATH_H */

