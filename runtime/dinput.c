/* Need for Speed ProStreet - DirectInput 8 COM Interface Shim Implementation.
 *
 * Implements DirectInput8Create entrypoint, IDirectInput8A (11 methods),
 * IDirectInputDevice8A (32 methods), and IDirectInputEffect (14 methods) COM vtables,
 * providing zero-latency gamepad, racing wheel, and touch controls bridging from the browser.
 */
#include "dinput.h"
#include <stdio.h>
#include <string.h>

/* Static Device & Shared State */
static dinput_shared_state_t s_shared_state;
static bool                  s_device_acquired = false;
static uint32_t              s_dinput_ref_count = 0;
static uint32_t              s_device_ref_count = 0;
static uint32_t              s_effect_ref_count = 0;

/* Standard GUID Definitions */
static const dinput_guid_t s_guid_iunknown = {
    0x00000000u, 0x0000, 0x0000, { 0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46 }
};

static const dinput_guid_t s_guid_idirectinput8a = {
    0xBF798030u, 0x483A, 0x4DA2, { 0xAA, 0x99, 0x5D, 0x64, 0xED, 0x36, 0x97, 0x00 }
};

static const dinput_guid_t s_guid_x_axis = {
    0xA36D02E0u, 0xC9F3, 0x11CF, { 0xBF, 0xC7, 0x44, 0x45, 0x53, 0x54, 0x00, 0x00 }
};
static const dinput_guid_t s_guid_y_axis = {
    0xA36D02E1u, 0xC9F3, 0x11CF, { 0xBF, 0xC7, 0x44, 0x45, 0x53, 0x54, 0x00, 0x00 }
};
static const dinput_guid_t s_guid_z_axis = {
    0xA36D02E2u, 0xC9F3, 0x11CF, { 0xBF, 0xC7, 0x44, 0x45, 0x53, 0x54, 0x00, 0x00 }
};
static const dinput_guid_t s_guid_rz_axis = {
    0xA36D02E5u, 0xC9F3, 0x11CF, { 0xBF, 0xC7, 0x44, 0x45, 0x53, 0x54, 0x00, 0x00 }
};
static const dinput_guid_t s_guid_pov = {
    0xA36D02F2u, 0xC9F3, 0x11CF, { 0xBF, 0xC7, 0x44, 0x45, 0x53, 0x54, 0x00, 0x00 }
};
static const dinput_guid_t s_guid_button = {
    0xA36D02F0u, 0xC9F3, 0x11CF, { 0xBF, 0xC7, 0x44, 0x45, 0x53, 0x54, 0x00, 0x00 }
};

/* --------------------------------------------------------------------------
 * Shared State Helper Functions
 * -------------------------------------------------------------------------- */
void dinput_set_connected(bool connected) {
    s_shared_state.connected = connected ? 1 : 0;
    s_shared_state.sequence++;
    dinput_sync_shared_state_to_guest();
}

void dinput_set_device_type(uint32_t dev_type) {
    s_shared_state.device_type = (int32_t)dev_type;
    s_shared_state.sequence++;
    dinput_sync_shared_state_to_guest();
}

void dinput_set_gamepad_axes(int32_t steer_lx, int32_t throttle_rz, int32_t brake_lz) {
    s_shared_state.joystate.lX  = steer_lx;
    s_shared_state.joystate.lRz = throttle_rz;
    s_shared_state.joystate.lZ  = brake_lz;
    s_shared_state.sequence++;
    dinput_sync_shared_state_to_guest();
}

void dinput_set_button(uint32_t button_idx, bool pressed) {
    if (button_idx < 128u) {
        s_shared_state.joystate.rgbButtons[button_idx] = pressed ? 0x80u : 0x00u;
        s_shared_state.sequence++;
        dinput_sync_shared_state_to_guest();
    }
}

void dinput_set_pov(uint32_t hat_idx, uint32_t pov_val) {
    if (hat_idx < 4u) {
        s_shared_state.joystate.rgdwPOV[hat_idx] = pov_val;
        s_shared_state.sequence++;
        dinput_sync_shared_state_to_guest();
    }
}

void dinput_set_keyboard_key(uint32_t vk, bool pressed) {
    if (vk < 256u) {
        s_shared_state.keyboard[vk] = pressed ? 0x80u : 0x00u;
        s_shared_state.sequence++;
        dinput_sync_shared_state_to_guest();
    }
}

dinput_shared_state_t *dinput_get_shared_state(void) {
    return &s_shared_state;
}

void dinput_sync_shared_state_to_guest(void) {
    if (GUEST_MEM_READY) {
        memcpy(g_mem + DINPUT_GUEST_SHARED_STATE, &s_shared_state, sizeof(dinput_shared_state_t));
    }
}

/* --------------------------------------------------------------------------
 * IDirectInput8A COM VTable Handlers (11 methods)
 * -------------------------------------------------------------------------- */

/* Method 0: QueryInterface(this, riid, ppvObj) */
static void dinput8_QueryInterface(CPU *c) {
    uint32_t this_ptr = MR32(c->esp);
    uint32_t riid     = MR32(c->esp + 4u);
    uint32_t ppvObj   = MR32(c->esp + 8u);

    if (ppvObj == 0u) {
        c->eax = DIERR_INVALIDPARAM;
        c->esp += 12u;
        return;
    }

    /* Support IUnknown and IDirectInput8A */
    if (riid != 0u && GUEST_MEM_READY) {
        if (memcmp(g_mem + riid, &s_guid_iunknown, 16) == 0 ||
            memcmp(g_mem + riid, &s_guid_idirectinput8a, 16) == 0) {
            MR32(ppvObj) = this_ptr;
            s_dinput_ref_count++;
            c->eax = DI_OK;
            c->esp += 12u;
            return;
        }
    }

    MR32(ppvObj) = this_ptr;
    s_dinput_ref_count++;
    c->eax = DI_OK;
    c->esp += 12u;
}

/* Method 1: AddRef(this) */
static void dinput8_AddRef(CPU *c) {
    s_dinput_ref_count++;
    c->eax = s_dinput_ref_count;
    c->esp += 4u;
}

/* Method 2: Release(this) */
static void dinput8_Release(CPU *c) {
    if (s_dinput_ref_count > 0u) {
        s_dinput_ref_count--;
    }
    c->eax = s_dinput_ref_count;
    c->esp += 4u;
}

/* Method 3: CreateDevice(this, rguid, lplpDirectInputDevice, pUnkOuter) */
static void dinput8_CreateDevice(CPU *c) {
    uint32_t ppDevice = MR32(c->esp + 8u);

    if (ppDevice != 0u) {
        MR32(ppDevice) = DINPUT_GUEST_DEVICE_ADDR;
        s_device_ref_count++;
    }

    c->eax = DI_OK;
    c->esp += 16u;
}

/* Method 4: EnumDevices(this, dwDevType, lpCallback, pvRef, dwFlags) */
static void dinput8_EnumDevices(CPU *c) {
    uint32_t lpCallback = MR32(c->esp + 8u);
    uint32_t pvRef      = MR32(c->esp + 12u);

    if (s_shared_state.connected && lpCallback != 0u && GUEST_MEM_READY) {
        /* Populate DIDEVICEINSTANCEA at scratch space */
        dinput_device_instance_a_t *inst = (dinput_device_instance_a_t *)(g_mem + DINPUT_GUEST_SCRATCH_ADDR);
        memset(inst, 0, sizeof(*inst));
        inst->dwSize = (uint32_t)sizeof(dinput_device_instance_a_t);
        
        /* guidInstance: {23F11526-3360-11D0-8215-444553540000} */
        inst->guidInstance.Data1 = 0x23F11526u;
        inst->guidInstance.Data2 = 0x3360u;
        inst->guidInstance.Data3 = 0x11D0u;
        inst->guidInstance.Data4[0] = 0x82; inst->guidInstance.Data4[1] = 0x15;
        inst->guidInstance.Data4[2] = 0x44; inst->guidInstance.Data4[3] = 0x45;
        inst->guidInstance.Data4[4] = 0x53; inst->guidInstance.Data4[5] = 0x54;
        
        /* guidProduct: {028E045E-0000-0000-0000-504944564944} */
        inst->guidProduct.Data1 = 0x028E045Eu;
        inst->guidProduct.Data4[2] = 'P'; inst->guidProduct.Data4[3] = 'I';
        inst->guidProduct.Data4[4] = 'D'; inst->guidProduct.Data4[5] = 'V';
        inst->guidProduct.Data4[6] = 'I'; inst->guidProduct.Data4[7] = 'D';

        inst->dwDevType = (uint32_t)s_shared_state.device_type;
        strncpy(inst->tszInstanceName, "PortSpeed Virtual Controller", sizeof(inst->tszInstanceName) - 1);
        strncpy(inst->tszProductName, "Xbox 360 Controller for Windows", sizeof(inst->tszProductName) - 1);

        /* Invoke guest callback: BOOL CALLBACK(LPCDIDEVICEINSTANCEA lpddi, LPVOID pvRef) */
        uint32_t saved_esp = c->esp;
        c->esp -= 4u; MR32(c->esp) = pvRef;
        c->esp -= 4u; MR32(c->esp) = DINPUT_GUEST_SCRATCH_ADDR;
        c->esp -= 4u; MR32(c->esp) = 0xDEADF00Du; /* Return address sentinel */

        DISPATCH_CALL(c, lpCallback);

        c->esp = saved_esp;
    }

    c->eax = DI_OK;
    c->esp += 20u;
}

/* Method 5: GetDeviceStatus(this, rguid) */
static void dinput8_GetDeviceStatus(CPU *c) {
    c->eax = DI_OK;
    c->esp += 8u;
}

/* Method 6: RunControlPanel(this, hwndOwner, dwFlags) */
static void dinput8_RunControlPanel(CPU *c) {
    c->eax = DI_OK;
    c->esp += 12u;
}

/* Method 7: Initialize(this, hinst, dwVersion) */
static void dinput8_Initialize(CPU *c) {
    c->eax = DI_OK;
    c->esp += 12u;
}

/* Method 8: FindDevice(this, rguid, pszName, pguidInstance) */
static void dinput8_FindDevice(CPU *c) {
    c->eax = DI_OK;
    c->esp += 16u;
}

/* Method 9: EnumDevicesBySemantics(this, ptszUserName, lpdiActionFormat, lpCallback, pvRef, dwFlags) */
static void dinput8_EnumDevicesBySemantics(CPU *c) {
    c->eax = DI_OK;
    c->esp += 24u;
}

/* Method 10: ConfigureDevices(this, lpdiCallback, lpdiCDParams, dwFlags, pvRef) */
static void dinput8_ConfigureDevices(CPU *c) {
    c->eax = DI_OK;
    c->esp += 20u;
}

/* --------------------------------------------------------------------------
 * IDirectInputDevice8A COM VTable Handlers (32 methods)
 * -------------------------------------------------------------------------- */

/* Method 0: QueryInterface(this, riid, ppvObj) */
static void dev_QueryInterface(CPU *c) {
    uint32_t this_ptr = MR32(c->esp);
    uint32_t ppvObj   = MR32(c->esp + 8u);
    if (ppvObj != 0u) {
        MR32(ppvObj) = this_ptr;
        s_device_ref_count++;
    }
    c->eax = DI_OK;
    c->esp += 12u;
}

/* Method 1: AddRef(this) */
static void dev_AddRef(CPU *c) {
    s_device_ref_count++;
    c->eax = s_device_ref_count;
    c->esp += 4u;
}

/* Method 2: Release(this) */
static void dev_Release(CPU *c) {
    if (s_device_ref_count > 0u) {
        s_device_ref_count--;
    }
    c->eax = s_device_ref_count;
    c->esp += 4u;
}

/* Method 3: GetCapabilities(this, lpDIDevCaps) */
static void dev_GetCapabilities(CPU *c) {
    uint32_t lpCaps = MR32(c->esp + 4u);
    if (lpCaps != 0u && GUEST_MEM_READY) {
        dinput_devcaps_t *caps = (dinput_devcaps_t *)(g_mem + lpCaps);
        caps->dwSize = (uint32_t)sizeof(dinput_devcaps_t);
        caps->dwFlags = DIDC_ATTACHED | DIDC_EMULATED | DIDC_POLLEDDATAFORMAT | DIDC_FORCEFEEDBACK;
        caps->dwDevType = (uint32_t)s_shared_state.device_type;
        caps->dwAxes = 6u;       /* X, Y, Z, Rx, Ry, Rz */
        caps->dwButtons = 16u;
        caps->dwPOVs = 1u;
        caps->dwFFSamplePeriod = 1000u;
        caps->dwFFMinTimeResolution = 1000u;
    }
    c->eax = DI_OK;
    c->esp += 8u;
}

/* Method 4: EnumObjects(this, lpCallback, pvRef, dwFlags) */
static void dev_EnumObjects(CPU *c) {
    uint32_t lpCallback = MR32(c->esp + 4u);
    uint32_t pvRef      = MR32(c->esp + 8u);

    if (lpCallback != 0u && GUEST_MEM_READY) {
        uint32_t scratch = DINPUT_GUEST_SCRATCH_ADDR + 0x300u;
        dinput_device_object_instance_a_t *obj = (dinput_device_object_instance_a_t *)(g_mem + scratch);

        typedef struct {
            const dinput_guid_t *guid;
            uint32_t type;
            uint32_t ofs;
            const char *name;
        } obj_spec_t;

        static const obj_spec_t specs[] = {
            { &s_guid_x_axis,  DIDFT_AXIS | (0 << 8),   0u,  "X Axis" },
            { &s_guid_y_axis,  DIDFT_AXIS | (1 << 8),   4u,  "Y Axis" },
            { &s_guid_z_axis,  DIDFT_AXIS | (2 << 8),   8u,  "Z Axis" },
            { &s_guid_rz_axis, DIDFT_AXIS | (3 << 8),  20u,  "Z Rotation" },
            { &s_guid_pov,     DIDFT_POV  | (0 << 8),  32u,  "POV Hat 1" },
            { &s_guid_button,  DIDFT_BUTTON | (0 << 8), 48u, "Button 0" },
            { &s_guid_button,  DIDFT_BUTTON | (1 << 8), 49u, "Button 1" },
            { &s_guid_button,  DIDFT_BUTTON | (2 << 8), 50u, "Button 2" },
            { &s_guid_button,  DIDFT_BUTTON | (3 << 8), 51u, "Button 3" },
            { &s_guid_button,  DIDFT_BUTTON | (4 << 8), 52u, "Button 4" },
            { &s_guid_button,  DIDFT_BUTTON | (5 << 8), 53u, "Button 5" },
            { &s_guid_button,  DIDFT_BUTTON | (6 << 8), 54u, "Button 6" },
            { &s_guid_button,  DIDFT_BUTTON | (7 << 8), 55u, "Button 7" },
            { &s_guid_button,  DIDFT_BUTTON | (8 << 8), 56u, "Button 8" },
            { &s_guid_button,  DIDFT_BUTTON | (9 << 8), 57u, "Button 9" }
        };

        for (size_t i = 0; i < sizeof(specs) / sizeof(specs[0]); ++i) {
            memset(obj, 0, sizeof(*obj));
            obj->dwSize = (uint32_t)sizeof(dinput_device_object_instance_a_t);
            obj->guidType = *specs[i].guid;
            obj->dwType = specs[i].type;
            obj->dwOfs  = specs[i].ofs;
            strncpy(obj->tszName, specs[i].name, sizeof(obj->tszName) - 1);

            uint32_t saved_esp = c->esp;
            c->esp -= 4u; MR32(c->esp) = pvRef;
            c->esp -= 4u; MR32(c->esp) = scratch;
            c->esp -= 4u; MR32(c->esp) = 0xDEADF00Du;

            DISPATCH_CALL(c, lpCallback);

            uint32_t ret = c->eax;
            c->esp = saved_esp;
            if (ret == DIENUM_STOP) break;
        }
    }

    c->eax = DI_OK;
    c->esp += 16u;
}

/* Method 5: GetProperty(this, rguid, pdiph) */
static void dev_GetProperty(CPU *c) {
    c->eax = DI_OK;
    c->esp += 12u;
}

/* Method 6: SetProperty(this, rguid, pdiph) */
static void dev_SetProperty(CPU *c) {
    c->eax = DI_OK;
    c->esp += 12u;
}

/* Method 7: Acquire(this) */
static void dev_Acquire(CPU *c) {
    s_device_acquired = true;
    c->eax = DI_OK;
    c->esp += 4u;
}

/* Method 8: Unacquire(this) */
static void dev_Unacquire(CPU *c) {
    s_device_acquired = false;
    c->eax = DI_OK;
    c->esp += 4u;
}

/* Method 9: GetDeviceState(this, cbData, lpvData) */
static void dev_GetDeviceState(CPU *c) {
    uint32_t cbData  = MR32(c->esp + 4u);
    uint32_t lpvData = MR32(c->esp + 8u);

    if (lpvData != 0u && GUEST_MEM_READY) {
        uint32_t copy_len = cbData < (uint32_t)sizeof(dinput_joystate2_t) ? cbData : (uint32_t)sizeof(dinput_joystate2_t);
        memcpy(g_mem + lpvData, &s_shared_state.joystate, copy_len);
    }

    c->eax = DI_OK;
    c->esp += 12u;
}

/* Method 10: GetDeviceData(this, cbObjectData, rgdod, pdwInOut, dwFlags) */
static void dev_GetDeviceData(CPU *c) {
    uint32_t pdwInOut = MR32(c->esp + 12u);
    if (pdwInOut != 0u) {
        MR32(pdwInOut) = 0u;
    }
    c->eax = DI_OK;
    c->esp += 20u;
}

/* Method 11: SetDataFormat(this, lpdf) */
static void dev_SetDataFormat(CPU *c) {
    c->eax = DI_OK;
    c->esp += 8u;
}

/* Method 12: SetEventNotification(this, hEvent) */
static void dev_SetEventNotification(CPU *c) {
    c->eax = DI_OK;
    c->esp += 8u;
}

/* Method 13: SetCooperativeLevel(this, hwnd, dwFlags) */
static void dev_SetCooperativeLevel(CPU *c) {
    c->eax = DI_OK;
    c->esp += 12u;
}

/* Method 14: GetObjectInfo(this, pdidoi, dwObj, dwHow) */
static void dev_GetObjectInfo(CPU *c) {
    c->eax = DI_OK;
    c->esp += 16u;
}

/* Method 15: GetDeviceInfo(this, pdidi) */
static void dev_GetDeviceInfo(CPU *c) {
    c->eax = DI_OK;
    c->esp += 8u;
}

/* Method 16: RunControlPanel(this, hwndOwner, dwFlags) */
static void dev_RunControlPanel(CPU *c) {
    c->eax = DI_OK;
    c->esp += 12u;
}

/* Method 17: Initialize(this, hinst, dwVersion, rguid) */
static void dev_Initialize(CPU *c) {
    c->eax = DI_OK;
    c->esp += 16u;
}

/* Method 18: CreateEffect(this, rguid, lpeff, ppdeff, punkOuter) */
static void dev_CreateEffect(CPU *c) {
    uint32_t ppdeff = MR32(c->esp + 12u);
    if (ppdeff != 0u) {
        MR32(ppdeff) = DINPUT_GUEST_EFFECT_ADDR;
        s_effect_ref_count++;
    }
    c->eax = DI_OK;
    c->esp += 20u;
}

/* Method 19: EnumEffects(this, lpCallback, pvRef, dwEffType) */
static void dev_EnumEffects(CPU *c) {
    c->eax = DI_OK;
    c->esp += 16u;
}

/* Method 20: GetEffectInfo(this, pdei, rguid) */
static void dev_GetEffectInfo(CPU *c) {
    c->eax = DI_OK;
    c->esp += 12u;
}

/* Method 21: GetForceFeedbackState(this, pdwOut) */
static void dev_GetForceFeedbackState(CPU *c) {
    uint32_t pdwOut = MR32(c->esp + 4u);
    if (pdwOut != 0u) {
        MR32(pdwOut) = 0u;
    }
    c->eax = DI_OK;
    c->esp += 8u;
}

/* Method 22: SendForceFeedbackCommand(this, dwFlags) */
static void dev_SendForceFeedbackCommand(CPU *c) {
    c->eax = DI_OK;
    c->esp += 8u;
}

/* Method 23: EnumCreatedEffectObjects(this, lpCallback, pvRef, dwFlags) */
static void dev_EnumCreatedEffectObjects(CPU *c) {
    c->eax = DI_OK;
    c->esp += 16u;
}

/* Method 24: Escape(this, pesc) */
static void dev_Escape(CPU *c) {
    c->eax = DI_OK;
    c->esp += 8u;
}

/* Method 25: Poll(this) */
static void dev_Poll(CPU *c) {
    c->eax = DI_OK;
    c->esp += 4u;
}

/* Method 26: SendDeviceData(this, cbObjectData, rgdod, pdwInOut, dwFlags) */
static void dev_SendDeviceData(CPU *c) {
    c->eax = DI_OK;
    c->esp += 20u;
}

/* Method 27: EnumEffectsInFile(this, lpszFileName, lpCallback, pvRef, dwFlags) */
static void dev_EnumEffectsInFile(CPU *c) {
    c->eax = DI_OK;
    c->esp += 20u;
}

/* Method 28: WriteEffectToFile(this, lpszFileName, dwEntries, rgdiFileEft, dwFlags) */
static void dev_WriteEffectToFile(CPU *c) {
    c->eax = DI_OK;
    c->esp += 20u;
}

/* Method 29: BuildActionMap(this, lpdiaf, lpszUserName, dwFlags) */
static void dev_BuildActionMap(CPU *c) {
    c->eax = DI_OK;
    c->esp += 16u;
}

/* Method 30: SetActionMap(this, lpdiaf, lpszUserName, dwFlags) */
static void dev_SetActionMap(CPU *c) {
    c->eax = DI_OK;
    c->esp += 16u;
}

/* Method 31: GetImageInfo(this, lpdiDevImageInfoHeader) */
static void dev_GetImageInfo(CPU *c) {
    c->eax = DI_OK;
    c->esp += 8u;
}

/* --------------------------------------------------------------------------
 * IDirectInputEffect COM VTable Handlers (14 methods)
 * -------------------------------------------------------------------------- */
static void eff_QueryInterface(CPU *c) {
    uint32_t this_ptr = MR32(c->esp);
    uint32_t ppvObj   = MR32(c->esp + 8u);
    if (ppvObj != 0u) MR32(ppvObj) = this_ptr;
    c->eax = DI_OK; c->esp += 12u;
}
static void eff_AddRef(CPU *c) {
    s_effect_ref_count++;
    c->eax = s_effect_ref_count; c->esp += 4u;
}
static void eff_Release(CPU *c) {
    if (s_effect_ref_count > 0u) s_effect_ref_count--;
    c->eax = s_effect_ref_count; c->esp += 4u;
}
static void eff_Initialize(CPU *c) { c->eax = DI_OK; c->esp += 16u; }
static void eff_GetEffectGuid(CPU *c) { c->eax = DI_OK; c->esp += 8u; }
static void eff_GetParameters(CPU *c) { c->eax = DI_OK; c->esp += 12u; }
static void eff_SetParameters(CPU *c) { c->eax = DI_OK; c->esp += 12u; }
static void eff_Start(CPU *c) { c->eax = DI_OK; c->esp += 12u; }
static void eff_Stop(CPU *c) { c->eax = DI_OK; c->esp += 4u; }
static void eff_GetEffectStatus(CPU *c) {
    uint32_t pdwFlags = MR32(c->esp + 4u);
    if (pdwFlags != 0u) MR32(pdwFlags) = 0u;
    c->eax = DI_OK; c->esp += 8u;
}
static void eff_Download(CPU *c) { c->eax = DI_OK; c->esp += 4u; }
static void eff_Unload(CPU *c) { c->eax = DI_OK; c->esp += 4u; }
static void eff_Escape(CPU *c) { c->eax = DI_OK; c->esp += 8u; }

/* --------------------------------------------------------------------------
 * DirectInput8 Method Handler Tables
 * -------------------------------------------------------------------------- */
static const guest_fn_t s_dinput8_handlers[DINPUT_DINPUT8_METHOD_COUNT] = {
    dinput8_QueryInterface,         /* 0: QueryInterface */
    dinput8_AddRef,                 /* 1: AddRef */
    dinput8_Release,                /* 2: Release */
    dinput8_CreateDevice,           /* 3: CreateDevice */
    dinput8_EnumDevices,            /* 4: EnumDevices */
    dinput8_GetDeviceStatus,        /* 5: GetDeviceStatus */
    dinput8_RunControlPanel,        /* 6: RunControlPanel */
    dinput8_Initialize,             /* 7: Initialize */
    dinput8_FindDevice,             /* 8: FindDevice */
    dinput8_EnumDevicesBySemantics, /* 9: EnumDevicesBySemantics */
    dinput8_ConfigureDevices        /* 10: ConfigureDevices */
};

static const guest_fn_t s_device_handlers[DINPUT_DEVICE_METHOD_COUNT] = {
    dev_QueryInterface,             /* 0: QueryInterface */
    dev_AddRef,                     /* 1: AddRef */
    dev_Release,                    /* 2: Release */
    dev_GetCapabilities,            /* 3: GetCapabilities */
    dev_EnumObjects,                /* 4: EnumObjects */
    dev_GetProperty,                /* 5: GetProperty */
    dev_SetProperty,                /* 6: SetProperty */
    dev_Acquire,                    /* 7: Acquire */
    dev_Unacquire,                  /* 8: Unacquire */
    dev_GetDeviceState,             /* 9: GetDeviceState */
    dev_GetDeviceData,              /* 10: GetDeviceData */
    dev_SetDataFormat,              /* 11: SetDataFormat */
    dev_SetEventNotification,       /* 12: SetEventNotification */
    dev_SetCooperativeLevel,        /* 13: SetCooperativeLevel */
    dev_GetObjectInfo,              /* 14: GetObjectInfo */
    dev_GetDeviceInfo,              /* 15: GetDeviceInfo */
    dev_RunControlPanel,            /* 16: RunControlPanel */
    dev_Initialize,                 /* 17: Initialize */
    dev_CreateEffect,               /* 18: CreateEffect */
    dev_EnumEffects,                /* 19: EnumEffects */
    dev_GetEffectInfo,              /* 20: GetEffectInfo */
    dev_GetForceFeedbackState,      /* 21: GetForceFeedbackState */
    dev_SendForceFeedbackCommand,   /* 22: SendForceFeedbackCommand */
    dev_EnumCreatedEffectObjects,   /* 23: EnumCreatedEffectObjects */
    dev_Escape,                     /* 24: Escape */
    dev_Poll,                       /* 25: Poll */
    dev_SendDeviceData,             /* 26: SendDeviceData */
    dev_EnumEffectsInFile,          /* 27: EnumEffectsInFile */
    dev_WriteEffectToFile,          /* 28: WriteEffectToFile */
    dev_BuildActionMap,             /* 29: BuildActionMap */
    dev_SetActionMap,               /* 30: SetActionMap */
    dev_GetImageInfo                /* 31: GetImageInfo */
};

static const guest_fn_t s_effect_handlers[DINPUT_EFFECT_METHOD_COUNT] = {
    eff_QueryInterface,             /* 0: QueryInterface */
    eff_AddRef,                     /* 1: AddRef */
    eff_Release,                    /* 2: Release */
    eff_Initialize,                 /* 3: Initialize */
    eff_GetEffectGuid,              /* 4: GetEffectGuid */
    eff_GetParameters,              /* 5: GetParameters */
    eff_SetParameters,              /* 6: SetParameters */
    eff_Start,                      /* 7: Start */
    eff_Stop,                       /* 8: Stop */
    eff_GetEffectStatus,            /* 9: GetEffectStatus */
    eff_Download,                   /* 10: Download */
    eff_Unload,                     /* 11: Unload */
    eff_Escape                      /* 12: Escape */
};

/* --------------------------------------------------------------------------
 * DirectInput8Create Export
 * -------------------------------------------------------------------------- */
void dinput_shim_DirectInput8Create(CPU *c) {
    uint32_t ppvOut = MR32(c->esp + 12u);

    if (ppvOut != 0u) {
        MR32(ppvOut) = DINPUT_GUEST_DINPUT8_ADDR;
        s_dinput_ref_count++;
    }

    c->eax = DI_OK;
    c->esp += 20u; /* 5 parameters * 4 bytes (__stdcall) */
}

/* --------------------------------------------------------------------------
 * Lifecycle & VTable Registration
 * -------------------------------------------------------------------------- */
void dinput_init_iat(void) {
    uint32_t idx = DINPUT_DIRECTINPUT8CREATE_IAT_VA - DISPATCH_TEXT_BASE;
    if (idx < DISPATCH_TEXT_SIZE) {
        g_dtab[idx] = dinput_shim_DirectInput8Create;
    }
    if (GUEST_MEM_READY) {
        MR32(DINPUT_DIRECTINPUT8CREATE_IAT_VA) = DINPUT_DIRECTINPUT8CREATE_IAT_VA;
    }
}

void dinput_init(void) {
    /* 1. Initialize default shared state */
    memset(&s_shared_state, 0, sizeof(s_shared_state));
    s_shared_state.sequence = 1u;
    s_shared_state.connected = 1;
    s_shared_state.device_type = (int32_t)DI8DEVTYPE_GAMEPAD;
    for (int i = 0; i < 4; ++i) {
        s_shared_state.joystate.rgdwPOV[i] = 0xFFFFFFFFu;
    }

    s_dinput_ref_count = 1u;
    s_device_ref_count = 0u;
    s_effect_ref_count = 0u;
    s_device_acquired = false;

    if (!GUEST_MEM_READY) return;

    /* 2. Bind DirectInput8Create IAT */
    dinput_init_iat();

    /* 3. Set up IDirectInput8A COM object and vtable */
    MR32(DINPUT_GUEST_DINPUT8_ADDR) = DINPUT_GUEST_DINPUT8_VTBL;
    for (uint32_t i = 0; i < DINPUT_DINPUT8_METHOD_COUNT; ++i) {
        uint32_t m_va = DINPUT_DINPUT8_METHOD_BASE_VA + i * 4u;
        MR32(DINPUT_GUEST_DINPUT8_VTBL + i * 4u) = m_va;
        uint32_t idx = m_va - DISPATCH_TEXT_BASE;
        if (idx < DISPATCH_TEXT_SIZE) {
            g_dtab[idx] = s_dinput8_handlers[i];
        }
    }

    /* 4. Set up IDirectInputDevice8A COM object and vtable */
    MR32(DINPUT_GUEST_DEVICE_ADDR) = DINPUT_GUEST_DEVICE_VTBL;
    for (uint32_t i = 0; i < DINPUT_DEVICE_METHOD_COUNT; ++i) {
        uint32_t m_va = DINPUT_DEVICE_METHOD_BASE_VA + i * 4u;
        MR32(DINPUT_GUEST_DEVICE_VTBL + i * 4u) = m_va;
        uint32_t idx = m_va - DISPATCH_TEXT_BASE;
        if (idx < DISPATCH_TEXT_SIZE) {
            g_dtab[idx] = s_device_handlers[i];
        }
    }

    /* 5. Set up IDirectInputEffect COM object and vtable */
    MR32(DINPUT_GUEST_EFFECT_ADDR) = DINPUT_GUEST_EFFECT_VTBL;
    for (uint32_t i = 0; i < DINPUT_EFFECT_METHOD_COUNT; ++i) {
        uint32_t m_va = DINPUT_EFFECT_METHOD_BASE_VA + i * 4u;
        MR32(DINPUT_GUEST_EFFECT_VTBL + i * 4u) = m_va;
        uint32_t idx = m_va - DISPATCH_TEXT_BASE;
        if (idx < DISPATCH_TEXT_SIZE) {
            g_dtab[idx] = s_effect_handlers[i];
        }
    }

    /* 6. Sync initial state into guest memory */
    dinput_sync_shared_state_to_guest();
}

