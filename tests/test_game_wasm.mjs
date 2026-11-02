// tests/test_game_wasm.mjs - Genuine WebAssembly Engine Startup Test Harness
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { WASI } from 'wasi';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..');

const WASM_PATH = path.join(ROOT, 'build', 'game.wasm');
const CFG_PATH = path.join(ROOT, 'config', 'local.json');

function getNfsExePath() {
    if (fs.existsSync(CFG_PATH)) {
        try {
            const raw = fs.readFileSync(CFG_PATH, 'utf8').replace(/^\uFEFF/, '');
            const cfg = JSON.parse(raw);
            const p1 = path.join(cfg.game_root, 'Need For Spped - Pro Street', 'nfs.exe');
            if (fs.existsSync(p1)) return p1;
            const p2 = path.join(cfg.game_root, 'nfs.exe');
            if (fs.existsSync(p2)) return p2;
        } catch (e) {}
    }
    const defaultPaths = [
        'C:\\Users\\tabat\\OneDrive\\Desktop\\Need-for-Speed-Pro-Street-SteamRIP.com\\Need For Spped - Pro Street\\nfs.exe',
        'C:\\Games\\Pro Street\\Need For Spped - Pro Street\\nfs.exe',
    ];
    for (const p of defaultPaths) {
        if (fs.existsSync(p)) return p;
    }
    return defaultPaths[0];
}

const NFS_EXE_PATH = getNfsExePath();

function parsePEHeaders(buf) {
    const e_lfanew = buf.readUInt32LE(0x3c);
    const numSections = buf.readUInt16LE(e_lfanew + 6);
    const optHeaderSize = buf.readUInt16LE(e_lfanew + 20);
    const secHeadersOffset = e_lfanew + 24 + optHeaderSize;

    const sections = [];
    for (let i = 0; i < numSections; i++) {
        const off = secHeadersOffset + i * 40;
        let name = buf.toString('latin1', off, off + 8).replace(/\0.*$/, '');
        const virtSize = buf.readUInt32LE(off + 8);
        const virtAddr = buf.readUInt32LE(off + 12);
        const rawSize = buf.readUInt32LE(off + 16);
        const rawOffset = buf.readUInt32LE(off + 20);
        sections.push({ name, virtSize, virtAddr, rawSize, rawOffset });
    }
    return sections;
}

async function run() {
    console.log('=== PortSpeed WebAssembly Genuine Boot Diagnostic ===');
    console.log('WASM Module:', WASM_PATH);
    if (!fs.existsSync(WASM_PATH)) {
        console.error('[FATAL] build/game.wasm not found. Run tools/build_wasm.py first.');
        process.exit(1);
    }
    if (!fs.existsSync(NFS_EXE_PATH)) {
        console.error('[FATAL] Original nfs.exe not found at:', NFS_EXE_PATH);
        process.exit(1);
    }

    const wasi = new WASI({
        version: 'preview1',
        args: ['nfs.exe'],
        env: process.env,
    });

    const wasmBytes = fs.readFileSync(WASM_PATH);
    const module = new WebAssembly.Module(wasmBytes);
    const instance = new WebAssembly.Instance(module, {
        wasi_snapshot_preview1: wasi.wasiImport,
    });

    wasi.initialize(instance);

    console.log('[1/5] Calling fntab_init() to populate master dispatch table...');
    const t0 = Date.now();
    instance.exports.fntab_init();
    console.log(`      fntab_init completed in ${Date.now() - t0}ms`);

    console.log('[2/5] Loading authentic PE sections into WASM linear memory...');
    const exeBuf = fs.readFileSync(NFS_EXE_PATH);
    const sections = parsePEHeaders(exeBuf);
    const wasmMem = new Uint8Array(instance.exports.memory.buffer);

    for (const sec of sections) {
        if (sec.rawSize > 0 && sec.rawOffset > 0) {
            const data = exeBuf.subarray(sec.rawOffset, sec.rawOffset + sec.rawSize);
            const dst = 0x00400000 + sec.virtAddr;
            wasmMem.set(data, dst);
            console.log(`      Mapped ${sec.name.padEnd(8)} at 0x${dst.toString(16).padStart(8, '0')} (${(sec.rawSize / 1024).toFixed(1)} KB)`);
        }
    }

    // Set DOS header signature 'MZ' at 0x00400000
    wasmMem[0x00400000] = 0x4d; // 'M'
    wasmMem[0x00400001] = 0x5a; // 'Z'

    console.log('[3/5] Setting up TEB (0x00100000) and Guest Stack (0x003FF000)...');
    // TEB self-pointer at fs:[0x18]
    const dv = new DataView(instance.exports.memory.buffer);
    dv.setUint32(0x00100018, 0x00100000, true);
    // Stack base/limit in TEB
    dv.setUint32(0x00100004, 0x00400000, true); // StackBase
    dv.setUint32(0x00100008, 0x00200000, true); // StackLimit

    console.log('[4/5] Binding IAT shims and installing runtime hooks...');
    instance.exports.boot_bind_iats();
    instance.exports.boot_install_hooks();

    // Allocate guest CPU structure in guest heap (0x02000000)
    const CPU_STRUCT_VA = 0x02000000;
    // Zero out CPU struct
    for (let i = 0; i < 512; i++) wasmMem[CPU_STRUCT_VA + i] = 0;
    // Set CPU fields:
    // esp (offset 16) = 0x003ff000
    dv.setUint32(CPU_STRUCT_VA + 16, 0x003ff000, true);
    // eip (offset 32) = 0x004afee0 (GUEST_MAIN_ENTRY_VA)
    dv.setUint32(CPU_STRUCT_VA + 32, 0x004afee0, true);
    // fs_base (offset 36) = 0x00100000
    dv.setUint32(CPU_STRUCT_VA + 36, 0x00100000, true);

    console.log('[5/5] Executing genuine C++ static initializers in WebAssembly...');
    const t_init = Date.now();
    try {
        let count = 0;
        for (let p = 0x00967608; p < 0x0096a1f4; p += 4) {
            const fn_va = dv.getUint32(p, true);
            if (fn_va !== 0) {
                count++;
                const saved_esp = dv.getUint32(CPU_STRUCT_VA + 16, true);
                const esp_next = saved_esp - 4;
                dv.setUint32(CPU_STRUCT_VA + 16, esp_next, true);
                dv.setUint32(esp_next, 0x00828ae0, true);
                const val_before = dv.getUint32(0x967d30, true);
                instance.exports.dispatch_indirect(CPU_STRUCT_VA, fn_va);
                const val_after = dv.getUint32(0x967d30, true);
                if (val_before !== val_after) {
                    console.log("CORRUPTION DETECTED at Ctor " + count + " (0x" + fn_va.toString(16) + ")! 0x967d30 changed from 0x" + val_before.toString(16) + " to 0x" + val_after.toString(16));
                    process.exit(1);
                }
                dv.setUint32(CPU_STRUCT_VA + 16, saved_esp, true);
            }
        }
        console.log("      Constructors executed: " + count + " / 960");
    } catch (err) {
        console.error('[FAIL] Constructor execution trapped:', err);
        dumpCPU(dv, CPU_STRUCT_VA);
        process.exit(1);
    }

    console.log('[6/5] Setting up main() arguments and entering genuine ProStreet main()...');
    instance.exports.boot_setup_arguments(CPU_STRUCT_VA, 1, 0);

    const t_main = Date.now();
    try {
        console.log('      Invoking sub_004afee0 via boot_invoke_main(dry_run = false)...');
        const rc = instance.exports.boot_invoke_main(CPU_STRUCT_VA, false);
        console.log(`      boot_invoke_main returned: ${rc} in ${Date.now() - t_main}ms`);
    } catch (err) {
        console.log('\n================ FIRST WASM RUNTIME FAILURE ================');
        console.log('Trap / Error:', err.message);
        dumpCPU(dv, CPU_STRUCT_VA);
        console.log('============================================================');
    }
}

function dumpCPU(dv, cpu_va) {
    const eax = dv.getUint32(cpu_va + 0, true);
    const ecx = dv.getUint32(cpu_va + 4, true);
    const edx = dv.getUint32(cpu_va + 8, true);
    const ebx = dv.getUint32(cpu_va + 12, true);
    const esp = dv.getUint32(cpu_va + 16, true);
    const ebp = dv.getUint32(cpu_va + 20, true);
    const esi = dv.getUint32(cpu_va + 24, true);
    const edi = dv.getUint32(cpu_va + 28, true);
    const eip = dv.getUint32(cpu_va + 32, true);
    const fs  = dv.getUint32(cpu_va + 36, true);

    console.log(`EAX: 0x${eax.toString(16).padStart(8, '0')}  ECX: 0x${ecx.toString(16).padStart(8, '0')}  EDX: 0x${edx.toString(16).padStart(8, '0')}  EBX: 0x${ebx.toString(16).padStart(8, '0')}`);
    console.log(`ESP: 0x${esp.toString(16).padStart(8, '0')}  EBP: 0x${ebp.toString(16).padStart(8, '0')}  ESI: 0x${esi.toString(16).padStart(8, '0')}  EDI: 0x${edi.toString(16).padStart(8, '0')}`);
    console.log(`EIP: 0x${eip.toString(16).padStart(8, '0')}  FS:  0x${fs.toString(16).padStart(8, '0')}`);

    if (esp >= 0x00200000 && esp < 0x00400000) {
        console.log('Stack Top:');
        for (let o = 0; o < 32; o += 4) {
            const val = dv.getUint32(esp + o, true);
            console.log(`  [ESP+0x${o.toString(16).padStart(2, '0')}]: 0x${val.toString(16).padStart(8, '0')}`);
        }
    }
}

run().catch(err => {
    console.error('[UNHANDLED]', err);
});
