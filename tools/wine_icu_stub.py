"""Write a minimal stand-in for Windows' icuuc.dll, for building under Wine only.

Qt 6's Qt6Core.dll imports ~20 ucnv_* functions from icuuc.dll, which ships
with Windows 10/11 but not with Wine. Without it Qt cannot load under Wine, so
PyInstaller cannot analyse it. This stub exports those names; every function
just fails (ucnv_open reports an error), which Qt handles. The app never calls
them. The stub lives in the Wine prefix's system32 and is NOT bundled into the
.exe - on real Windows the system's own icuuc.dll is used.

Usage: python wine_icu_stub.py <output.dll>
"""

import struct
import sys

EXPORTS = [
    "UCNV_FROM_U_CALLBACK_SUBSTITUTE", "UCNV_TO_U_CALLBACK_SUBSTITUTE", "ucnv_cbFromUWriteUChars",
    "ucnv_cbToUWriteUChars", "ucnv_close", "ucnv_countAvailable", "ucnv_fromUCountPending",
    "ucnv_fromUnicode", "ucnv_getAvailableName", "ucnv_getFromUCallBack", "ucnv_getMaxCharSize",
    "ucnv_getName", "ucnv_getStandardName", "ucnv_getToUCallBack", "ucnv_open", "ucnv_reset",
    "ucnv_setFromUCallBack", "ucnv_setToUCallBack", "ucnv_toUCountPending", "ucnv_toUnicode",
]

DLLMAIN = bytes.fromhex("B801000000C3")        # mov eax, 1 ; ret
RETURN_ZERO = bytes.fromhex("31C0C3")           # xor eax, eax ; ret
OPEN_FAILS = bytes.fromhex("C7020400000031C0C3")  # *pErrorCode = U_FILE_ACCESS_ERROR ; return NULL

SECTION_RVA = 0x1000
FILE_ALIGN = 0x200
SECT_ALIGN = 0x1000


def align(n: int, a: int) -> int:
    return (n + a - 1) // a * a


def build() -> bytes:
    code = DLLMAIN.ljust(16, b"\xcc") + RETURN_ZERO.ljust(16, b"\xcc") + OPEN_FAILS.ljust(32, b"\xcc")
    rva_main, rva_zero, rva_open = SECTION_RVA, SECTION_RVA + 16, SECTION_RVA + 32

    names = sorted(EXPORTS, key=lambda s: s.encode())  # the loader binary-searches this list
    n = len(names)
    exp_off = len(code)
    funcs_off = exp_off + 40
    names_off = funcs_off + 4 * n
    ords_off = names_off + 4 * n
    strings_off = ords_off + 2 * n
    strings = b"icuuc.dll\0"
    name_rvas = []
    for name in names:
        name_rvas.append(SECTION_RVA + strings_off + len(strings))
        strings += name.encode() + b"\0"

    export_dir = struct.pack("<IIHHIIIIIII", 0, 0, 0, 0, SECTION_RVA + strings_off, 1, n, n,
                             SECTION_RVA + funcs_off, SECTION_RVA + names_off, SECTION_RVA + ords_off)
    funcs = b"".join(struct.pack("<I", rva_open if name == "ucnv_open" else rva_zero) for name in names)
    section = (code + export_dir + funcs + b"".join(struct.pack("<I", r) for r in name_rvas)
               + b"".join(struct.pack("<H", i) for i in range(n)) + strings)
    virtual_size = len(section)
    raw = section.ljust(align(virtual_size, FILE_ALIGN), b"\0")
    export_size = virtual_size - exp_off

    dos = b"MZ".ljust(0x3C, b"\0") + struct.pack("<I", 0x40)
    coff = struct.pack("<HHIIIHH", 0x8664, 1, 0, 0, 0, 240, 0x2022)
    data_dirs = struct.pack("<II", SECTION_RVA + exp_off, export_size) + b"\0" * 8 * 15
    optional = struct.pack(
        "<HBBIIIIIQIIHHHHHHIIIIHHQQQQII",
        0x20B, 14, 0, len(raw), 0, 0, rva_main, SECTION_RVA, 0x6A400000, SECT_ALIGN, FILE_ALIGN,
        6, 0, 0, 0, 6, 0, 0, SECTION_RVA + align(virtual_size, SECT_ALIGN), FILE_ALIGN, 0, 2, 0,
        0x100000, 0x1000, 0x100000, 0x1000, 0, 16,
    ) + data_dirs
    section_header = struct.pack("<8sIIIIIIHHI", b".text", virtual_size, SECTION_RVA, len(raw), FILE_ALIGN,
                                 0, 0, 0, 0, 0x60000020)
    headers = (dos + b"PE\0\0" + coff + optional + section_header).ljust(FILE_ALIGN, b"\0")
    return headers + raw


if __name__ == "__main__":
    with open(sys.argv[1], "wb") as f:
        f.write(build())
