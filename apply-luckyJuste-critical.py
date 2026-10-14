#!/usr/bin/env python3
"""Apply luckyJuste linear critical patch to a clean Harmony of Dissonance USA ROM.

The requested linear bonus passes through (equipment LCK=0, bonus=0%) and
(equipment LCK=30, bonus=4.69%). To avoid floating point on ARM7TDMI, the
Thumb stub uses bonus_units = 102*x + (x >> 1). This is a close integer
approximation: at x=30, bonus=3075/65536*100 = 4.6920776 percentage points.

EQUIPMENT_LCK = max(0, LCK_ATTR - JusteLevel - 24).
Primary threshold = min(65536, 4096 + bonus_units).
No enemy-level bonus. No Lucky Charm/Ring hardcoded effects.
Platinum Tip: on a failed primary roll, attack ID 2..5 with flag 0x80
gets the original conditional second roll (RNG & 0xF003) == 0.

New stub is 132 bytes at ROM offset 0x7FFD00 (GBA 0x087FFD00).
The old ranges GDB breakpoints inside the stub are NOT compatible with
this version because code offsets have changed. Rebuild/update that script.
"""
from hashlib import sha1
from pathlib import Path

VERSION = "1.0.0"
INPUT_ROM = "rom-harmony-usa.gba"
OUTPUT_ROM = f"rom-harmony-usa-luckyJuste-critical-{VERSION}.gba"
EXPECTED_SHA1 = "b90da0d9be0b3a0893cd9e2c399056bcf9579e21"
ROM_SIZE = 0x800000
CALLER_OFFSET = 0x0312CE
ENTRY_OFFSET = 0x077CAC
STUB_OFFSET = 0x7FFD00
EXPECTED_CALLER = bytes.fromhex("38 1C")
EXPECTED_ENTRY = bytes.fromhex("30 B5 00 04 05 0C 00 24")
ENTRY_TRAMPOLINE = bytes.fromhex("00 4B 18 47") + (
    (0x08000000 + STUB_OFFSET) | 1
).to_bytes(4, "little")

# Thumb-1 bytes assembled for armv4t from critical-linear-stub.s.
STUB = bytes.fromhex(
    'f0b5041c18480588184800782d1a183d00d5002566202e1c'
    '464368083618144836181448864200d9061c134b7a460732'
    '964618470004000cb04212d3a01e03280dd80e4800688021'
    '084208d00a4b7a460532964618470a490840002801d00020'
    'f0bd0120f0bd0000588501027c8701020010000000000100'
    '790a00082885010203f00000'
)


def bonus_units(equipment_lck: int) -> int:
    x = max(0, int(equipment_lck))
    return 102 * x + (x >> 1)


def threshold(lck_total: int, juste_level: int) -> int:
    x = max(0, int(lck_total) - int(juste_level) - 24)
    return min(65536, 4096 + bonus_units(x))


def verify(rom: bytes, offset: int, expected: bytes, label: str) -> None:
    if rom[offset:offset + len(expected)] != expected:
        raise ValueError(f"{label}: unexpected bytes at 0x{offset:X}; use clean USA ROM")


def apply_patch() -> Path:
    rom = bytearray(Path(INPUT_ROM).read_bytes())
    if len(rom) != ROM_SIZE:
        raise ValueError(f"Wrong ROM size: {len(rom)}")
    if sha1(rom).hexdigest() != EXPECTED_SHA1:
        raise ValueError("Wrong USA ROM SHA-1; use clean unmodified ROM")
    verify(rom, CALLER_OFFSET, EXPECTED_CALLER, "Caller")
    verify(rom, ENTRY_OFFSET, EXPECTED_ENTRY, "Critical entry")
    verify(rom, STUB_OFFSET, b"\xff" * len(STUB), "Stub free space")
    if STUB_OFFSET + len(STUB) > ROM_SIZE:
        raise ValueError("Stub exceeds ROM")
    # Caller remains vanilla: r0 receives attack ID for Platinum Tip gate.
    rom[ENTRY_OFFSET:ENTRY_OFFSET + 8] = ENTRY_TRAMPOLINE
    rom[STUB_OFFSET:STUB_OFFSET + len(STUB)] = STUB
    out = Path(OUTPUT_ROM)
    out.write_bytes(rom)
    print(f"[OK] {out}; stub {len(STUB)} bytes at 0x087FFD00")
    for x in (0, 10, 20, 30, 40, 63):
        t = 4096 + bonus_units(x)
        print(f"  LCK equip {x:2d}: bonus {bonus_units(x):4d}, critical {t/65536*100:.5f}%")
    print("[NOTE] Old ranges GDB script requires updated internal addresses.")
    print("[NOTE] Test with mGBA/GDB before distribution.")
    return out


if __name__ == "__main__":
    try:
        apply_patch()
    except (OSError, ValueError) as exc:
        raise SystemExit(f"[ERROR] {exc}") from exc
