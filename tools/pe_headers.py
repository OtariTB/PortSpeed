"""Static, bounded PE metadata parsing. Never loads or executes the image.

Layout reference: https://learn.microsoft.com/en-us/windows/win32/debug/pe-format
This is not a general purpose PE validator or a runtime dependency resolver.
"""
import struct


def inspect_pe(data):
    def unpack(fmt, off):
        size = struct.calcsize(fmt)
        if off < 0 or off + size > len(data):
            raise ValueError('truncated PE field')
        return struct.unpack_from(fmt, data, off)

    if data[:2] != b'MZ':
        raise ValueError('missing DOS signature')
    pe, = unpack('<I', 0x3c)
    if data[pe:pe + 4] != b'PE\0\0':
        raise ValueError('missing PE signature')
    machine, count, timestamp, _, _, opt_size, flags = unpack('<HHIIIHH', pe + 4)
    opt = pe + 24
    if opt + opt_size > len(data):
        raise ValueError('truncated optional header')
    magic, = unpack('<H', opt)
    if magic not in (0x10b, 0x20b):
        raise ValueError('unsupported optional header')
    is64 = magic == 0x20b
    directory_off = 112 if is64 else 96
    if opt_size < directory_off:
        raise ValueError('short optional header')
    image_base, = unpack('<Q' if is64 else '<I', opt + (24 if is64 else 28))
    entry, = unpack('<I', opt + 16)
    headers_size, = unpack('<I', opt + 60)
    ndirs, = unpack('<I', opt + directory_off - 4)
    if count > 96:
        raise ValueError('section count exceeds inspection limit')
    sections = []
    for i in range(count):
        off = opt + opt_size + 40 * i
        name, vs, va, rs, rp, _, _, _, _, sf = unpack('<8sIIIIIIHHI', off)
        sections.append(dict(name=name.rstrip(b'\0').decode('ascii', 'replace'),
                             virtual_size=vs, rva=va, raw_size=rs, raw_offset=rp,
                             characteristics=hex(sf)))

    def rva_offset(rva, size=1):
        if rva < headers_size and rva + size <= min(headers_size, len(data)):
            return rva
        for s in sections:
            delta = rva - s['rva']
            if 0 <= delta and delta + size <= s['raw_size']:
                off = s['raw_offset'] + delta
                if off + size <= len(data):
                    return off
        raise ValueError('RVA not backed by file bytes')

    def name_at(rva):
        result = bytearray()
        for i in range(4096):
            b = data[rva_offset(rva + i)]
            if not b:
                return result.decode('ascii', 'replace')
            result.append(b)
        raise ValueError('unterminated import name')

    def directory(index):
        if index >= ndirs:
            return 0, 0
        if directory_off + 8 * (index + 1) > opt_size:
            raise ValueError('directory outside optional header')
        return unpack('<II', opt + directory_off + index * 8)

    result = dict(machine=hex(machine), bits=64 if is64 else 32,
                  coff_timestamp_raw=timestamp, entry_rva=hex(entry), image_base=hex(image_base),
                  characteristics=hex(flags), sections=sections, imports=[], delay_imports=[], warnings=[])
    for key, index, width in [('imports', 1, 20), ('delay_imports', 13, 32)]:
        try:
            rva, size = directory(index)
            if not rva:
                continue
            terminated = False
            for i in range(min(size // width, 4096)):
                fields = unpack('<' + 'I' * (width // 4), rva_offset(rva + i * width, width))
                if not any(fields):
                    terminated = True
                    break
                name_rva = fields[3] if index == 1 else fields[1]
                if index == 13 and not fields[0] & 1:
                    name_rva -= image_base
                result[key].append(name_at(name_rva))
            if not terminated:
                result['warnings'].append(key + ': no terminator within bounded directory')
        except ValueError as exc:
            result['warnings'].append(key + ': ' + str(exc))
    return result
