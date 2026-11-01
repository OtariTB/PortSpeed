/* Need for Speed ProStreet - DirectInput 8 COM Interface Shim Header.
 *
 * Provides authentic DirectInput8 COM vtables for IDirectInput8A, IDirectInputDevice8A,
 * and IDirectInputEffect, routing gamepad, racing wheel, and touch inputs from the browser's
 * SharedArrayBuffer directly to recompiled game engine systems.
 */
#ifndef PROSTREET_DINPUT_H
#define PROSTREET_DINPUT_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "cpu.h"

#ifdef __cplusplus
extern "C" {
#endif

/* --------------------------------------------------------------------------
 * DirectInput 8 Return Codes & Error Values
 * -------------------------------------------------------------------------- */
#define DI_OK                       0x00000000u
#define DI_NOEFFECT                 0x00000001u
#define DI_BUFFEROVERFLOW           0x00000001u
#define DIERR_NOTINITIALIZED        0x80070015u
#define DIERR_OTHERAPPHASPRIO       0x80070005u
#define DIERR_INVALIDPARAM          0x80070057u
#define DIERR_NOTACQUIRED           0x8007000Cu
#define DIERR_INPUTLOST             0x8007001Eu
#define DIERR_UNSUPPORTED           0x80004001u
#define E_NOINTERFACE               0x80004002u

/* --------------------------------------------------------------------------
 * DirectInput 8 Device Types & Flags
 * -------------------------------------------------------------------------- */
#define DIRECTINPUT_VERSION         0x0800u

#define DI8DEVCLASS_ALL             0u
#define DI8DEVCLASS_DEVICE          1u
#define DI8DEVCLASS_POINTER         2u
#define DI8DEVCLASS_KEYBOARD        3u
#define DI8DEVCLASS_GAMECTRL        4u

#define DI8DEVTYPE_DEVICE           0x11u
#define DI8DEVTYPE_MOUSE            0x12u
#define DI8DEVTYPE_KEYBOARD         0x13u
#define DI8DEVTYPE_JOYSTICK         0x14u
#define DI8DEVTYPE_GAMEPAD          0x15u
#define DI8DEVTYPE_DRIVING          0x16u

#define DIEDFL_ALLDEVICES           0x00000000u
#define DIEDFL_ATTACHEDONLY         0x00000001u

#define DISCL_EXCLUSIVE             0x00000001u
#define DISCL_NONEXCLUSIVE          0x00000002u
#define DISCL_FOREGROUND            0x00000004u
#define DISCL_BACKGROUND            0x00000008u
#define DISCL_NOWINKEY              0x00000010u

#define DIDC_ATTACHED               0x00000001u
#define DIDC_POLLEDDATAFORMAT       0x00000002u
#define DIDC_EMULATED               0x00000004u
#define DIDC_POLLEDDEVICE           0x00000008u
#define DIDC_FORCEFEEDBACK          0x00000100u
#define DIDC_FFACTUATOR             0x00000200u

#define DIDFT_ALL                   0x00000000u
#define DIDFT_AXIS                  0x00000003u
#define DIDFT_BUTTON                0x0000000Cu
#define DIDFT_POV                   0x00000010u
#define DIDFT_ABSAXIS               0x00000001u
#define DIDFT_RELAXIS               0x00000002u
#define DIDFT_PSHBUTTON             0x00000004u
#define DIDFT_TGLBUTTON             0x00000008u
#define DIDFT_ANYINSTANCE           0x00FFFF00u

#define DIPH_DEVICE                 0u
#define DIPH_BYOFFSET               1u
#define DIPH_BYID                   2u

#define DIPROP_BUFFERSIZE           1u
#define DIPROP_RANGE                4u
#define DIPROP_DEADZONE             5u
#define DIPROP_SATURATION           6u
#define DIPROP_AUTOCENTER           9u

#define DIENUM_STOP                 0u
#define DIENUM_CONTINUE             1u

/* --------------------------------------------------------------------------
 * Guest Linear Memory Address Allocation for DirectInput COM Objects
 * -------------------------------------------------------------------------- */
#define DINPUT_DIRECTINPUT8CREATE_IAT_VA 0x00967030u

#define DINPUT_GUEST_DINPUT8_ADDR        0x02008000u
#define DINPUT_GUEST_DINPUT8_VTBL        0x02008100u

#define DINPUT_GUEST_DEVICE_ADDR         0x02008300u
#define DINPUT_GUEST_DEVICE_VTBL         0x02008400u

#define DINPUT_GUEST_EFFECT_ADDR         0x02008600u
#define DINPUT_GUEST_EFFECT_VTBL         0x02008700u

#define DINPUT_GUEST_SCRATCH_ADDR        0x02009000u
#define DINPUT_GUEST_SHARED_STATE        0x0200A000u

#define DINPUT_DINPUT8_METHOD_BASE_VA    0x00962000u
#define DINPUT_DEVICE_METHOD_BASE_VA     0x00962200u
#define DINPUT_EFFECT_METHOD_BASE_VA     0x00962400u

#define DINPUT_DINPUT8_METHOD_COUNT      11u
#define DINPUT_DEVICE_METHOD_COUNT       32u
#define DINPUT_EFFECT_METHOD_COUNT       14u

/* --------------------------------------------------------------------------
 * DirectInput 8 Structures
 * -------------------------------------------------------------------------- */
typedef struct {
    uint32_t Data1;
    uint16_t Data2;
    uint16_t Data3;
    uint8_t  Data4[8];
} dinput_guid_t;

/* DIDEVICEINSTANCEA (592 / 0x250 bytes) */
typedef struct {
    uint32_t      dwSize;
    dinput_guid_t guidInstance;
    dinput_guid_t guidProduct;
    uint32_t      dwDevType;
    char          tszInstanceName[260];
    char          tszProductName[260];
    dinput_guid_t guidFFDriver;
    uint16_t      wUsagePage;
    uint16_t      wUsage;
} dinput_device_instance_a_t;

/* DIDEVCAPS (44 / 0x2C bytes) */
typedef struct {
    uint32_t dwSize;
    uint32_t dwFlags;
    uint32_t dwDevType;
    uint32_t dwAxes;
    uint32_t dwButtons;
    uint32_t dwPOVs;
    uint32_t dwFFSamplePeriod;
    uint32_t dwFFMinTimeResolution;
    uint32_t dwFirmwareRevision;
    uint32_t dwHardwareRevision;
    uint32_t dwFFDriverVersion;
} dinput_devcaps_t;

/* DIDEVICEOBJECTINSTANCEA (44 / 0x2C bytes) */
typedef struct {
    uint32_t      dwSize;
    dinput_guid_t guidType;
    uint32_t      dwOfs;
    uint32_t      dwType;
    uint32_t      dwFlags;
    char          tszName[260];
    uint32_t      dwFFMaxForce;
    uint32_t      dwFFForceResolution;
    uint16_t      wCollectionNumber;
    uint16_t      wDesignatorIndex;
    uint16_t      wUsagePage;
    uint16_t      wUsage;
    uint32_t      dwDimension;
    uint16_t      wExponent;
    uint16_t      wReportId;
} dinput_device_object_instance_a_t;

/* Property Headers */
typedef struct {
    uint32_t dwSize;
    uint32_t dwHeaderSize;
    uint32_t dwObj;
    uint32_t dwHow;
} dinput_propheader_t;

typedef struct {
    dinput_propheader_t diph;
    uint32_t dwData;
} dinput_propdword_t;

typedef struct {
    dinput_propheader_t diph;
    int32_t  lMin;
    int32_t  lMax;
} dinput_proprange_t;

/* DIJOYSTATE2 (272 / 0x110 bytes) */
typedef struct {
    int32_t  lX;                   /* 0x00: Steering Left/Right (-32768..32767) */
    int32_t  lY;                   /* 0x04: Y Axis */
    int32_t  lZ;                   /* 0x08: Z Axis / Left Trigger / Brake */
    int32_t  lRx;                  /* 0x0C: X Rotation */
    int32_t  lRy;                  /* 0x10: Y Rotation */
    int32_t  lRz;                  /* 0x14: Z Rotation / Right Trigger / Throttle */
    int32_t  rglSlider[2];         /* 0x18: Sliders */
    uint32_t rgdwPOV[4];          /* 0x20: POV Hats (degrees*100, or 0xFFFFFFFF) */
    uint8_t  rgbButtons[128];     /* 0x30: 128 Buttons (0x80 if pressed, 0x00 if released) */
    int32_t  lVX;                  /* 0xB0: Velocity X */
    int32_t  lVY;                  /* 0xB4: Velocity Y */
    int32_t  lVZ;                  /* 0xB8: Velocity Z */
    int32_t  lVRx;                 /* 0xBC: Angular Velocity X */
    int32_t  lVRy;                 /* 0xC0: Angular Velocity Y */
    int32_t  lVRz;                 /* 0xC4: Angular Velocity Z */
    int32_t  rglVSlider[2];        /* 0xC8: Velocity Sliders */
    int32_t  lAX;                  /* 0xD0: Acceleration X */
    int32_t  lAY;                  /* 0xD4: Acceleration Y */
    int32_t  lAZ;                  /* 0xD8: Acceleration Z */
    int32_t  lARx;                 /* 0xDC: Angular Accel X */
    int32_t  lARy;                 /* 0xE0: Angular Accel Y */
    int32_t  lARz;                 /* 0xE4: Angular Accel Z */
    int32_t  rglASlider[2];        /* 0xE8: Accel Sliders */
    int32_t  lFX;                  /* 0xF0: Force X */
    int32_t  lFY;                  /* 0xF4: Force Y */
    int32_t  lFZ;                  /* 0xF8: Force Z */
    int32_t  lFRx;                 /* 0xFC: Torque X */
    int32_t  lFRy;                 /* 0x100: Torque Y */
    int32_t  lFRz;                 /* 0x104: Torque Z */
    int32_t  rglFSlider[2];        /* 0x108: Force Sliders */
} dinput_joystate2_t;

/* Shared Input Buffer for Browser <-> WebAssembly */
typedef struct {
    uint32_t           sequence;       /* Lock-free update sequence counter */
    int32_t            connected;      /* 1 = Controller connected */
    int32_t            device_type;    /* 0x14 = Joystick, 0x15 = Gamepad, 0x16 = Driving Wheel */
    dinput_joystate2_t joystate;       /* Gamepad / Wheel analog and button states */
    uint8_t            keyboard[256];  /* 256 virtual key down states (0x80 = pressed) */
} dinput_shared_state_t;

/* --------------------------------------------------------------------------
 * Lifecycle & Initialization API
 * -------------------------------------------------------------------------- */
void dinput_init_iat(void);
void dinput_init(void);

/* DirectInput8Create Export / Shim */
void dinput_shim_DirectInput8Create(CPU *c);

/* State Manipulation API */
void dinput_set_connected(bool connected);
void dinput_set_device_type(uint32_t dev_type);
void dinput_set_gamepad_axes(int32_t steer_lx, int32_t throttle_rz, int32_t brake_lz);
void dinput_set_button(uint32_t button_idx, bool pressed);
void dinput_set_pov(uint32_t hat_idx, uint32_t pov_val);
void dinput_set_keyboard_key(uint32_t vk, bool pressed);

dinput_shared_state_t *dinput_get_shared_state(void);
void dinput_sync_shared_state_to_guest(void);

#ifdef __cplusplus
}
#endif

#endif /* PROSTREET_DINPUT_H */

