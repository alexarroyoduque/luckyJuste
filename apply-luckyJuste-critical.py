version = "1.0.0"
original_rom = "rom-harmony-usa.gba"
patched_rom = f"rom-harmony-usa-luckyJuste-critical-{version}.gba"

"""Apply the experimental luckyJuste critical-hit patch to a CLEAN USA ROM.

Formula (integer threshold units):
    equipment_luck = max(0, LCK_ATTR - JusteLevel - 24)
    level_bonus = min(4, max(0, JusteLevel - EnemyLevel) // 10)
    threshold = min(65536, 4096 + equipment_luck * 98 + level_bonus * 655)
    critical = (original_RNG() & 0xFFFF) < threshold

The vanilla Lucky Charm/Ring threshold bonuses and the Platinum Tip second
roll are bypassed. The vanilla caller still doubles critical damage.

The embedded 152-byte ARM7TDMI THUMB stub was assembled with clang targeting
armv4t-none-eabi. It expects the enemy instance pointer in r0. At the known
caller 0x080312CE, r9 holds this pointer, so its original 'mov r0,r7' is
replaced by 'mov r0,r9'. The original BL to 0x08077CAC is preserved.

The original 105-coefficient build was tested in mGBA/GDB. This 98-coefficient revision requires new dynamic verification.
"""

from hashlib import sha1
from pathlib import Path

EXPECTED_SHA1 = "b90da0d9be0b3a0893cd9e2c399056bcf9579e21"
ROM_SIZE = 0x800000
CALLER_OFFSET = 0x0312CE
CRITICAL_ENTRY_OFFSET = 0x077CAC
STUB_OFFSET = 0x7FFD00

EXPECTED_CALLER = bytes.fromhex("38 1C")       # mov r0, r7
PATCHED_CALLER = bytes.fromhex("48 46")        # mov r0, r9 (enemy instance)
EXPECTED_CRITICAL_ENTRY = bytes.fromhex("30 B5 00 04 05 0C 00 24")

# ARM7TDMI THUMB entry: ldr r3, [pc, #0]; bx r3; .word stub_thumb_address
ENTRY_TRAMPOLINE = (bytes.fromhex("00 4B 18 47")
                    + ((0x08000000 + STUB_OFFSET) | 1).to_bytes(4, "little"))

# Standalone Thumb-1 routine, assembled for ARM7TDMI (no Thumb-2/BLX).
# Literal pool contains addresses for Juste level, LCK, enemy DNA pointer,
# 655, 4096, 65536, and vanilla RNG entry (Thumb bit set).
STUB = bytes.fromhex(
    "f0b5041c1d4d2d781d4e3688761b183e00d50026201c3e30007824214843"
    "194909684018007c2f1a00d500270023282f0bd21e2f07d2142f03d20a2f"
    "06d3012304e0022302e0032300e00423622046430d484343f6180d483618"
    "0d48864200d9061c0c4b7a460532964618470004000cb04201d3002000e0"
    "0120f0bd7c87010258850102102b00038f0200000010000000000100790a0008"
)


def verify_range(data: bytearray, offset: int, expected: bytes, label: str) -> None:
    actual = bytes(data[offset:offset + len(expected)])
    if actual != expected:
        raise ValueError(
            f"{label}: incorrect bytes at ROM offset 0x{offset:X}: "
            f"expected {expected.hex(' ')}, got {actual.hex(' ')}"
        )


def apply_patch() -> Path:
    source = Path(original_rom)
    if not source.is_file():
        raise FileNotFoundError(f"Missing input ROM: {source}")

    rom = bytearray(source.read_bytes())
    if len(rom) != ROM_SIZE:
        raise ValueError(f"Expected 0x{ROM_SIZE:X} bytes; got 0x{len(rom):X}")
    digest = sha1(rom).hexdigest()
    if digest != EXPECTED_SHA1:
        raise ValueError(
            f"Expected CLEAN USA ROM SHA-1 {EXPECTED_SHA1}; got {digest}. "
            "Do not run this script on an already patched ROM."
        )

    assert len(STUB) == 0x98, "Unexpected assembled THUMB stub size"
    verify_range(rom, CALLER_OFFSET, EXPECTED_CALLER, "Damage caller")
    verify_range(rom, CRITICAL_ENTRY_OFFSET, EXPECTED_CRITICAL_ENTRY,
                 "Vanilla critical routine")
    verify_range(rom, STUB_OFFSET, b"\xFF" * len(STUB), "Free ROM space")
    if STUB_OFFSET + len(STUB) > len(rom):
        raise ValueError("Stub extends beyond ROM")

    rom[CALLER_OFFSET:CALLER_OFFSET + 2] = PATCHED_CALLER
    rom[CRITICAL_ENTRY_OFFSET:CRITICAL_ENTRY_OFFSET + 8] = ENTRY_TRAMPOLINE
    rom[STUB_OFFSET:STUB_OFFSET + len(STUB)] = STUB

    target = Path(patched_rom)
    target.write_bytes(rom)
    print(f"[OK] {target} ({len(rom)} bytes)")
    print(f"[OK] Critical entry: 0x{0x08000000 + CRITICAL_ENTRY_OFFSET:08X}")
    print(f"[OK] THUMB stub:    0x{0x08000000 + STUB_OFFSET:08X}, {len(STUB)} bytes")
    print("[!] Experimental: verify in mGBA/GDB before distributing.")
    return target


if __name__ == "__main__":
    try:
        apply_patch()
    except (OSError, ValueError) as exc:
        raise SystemExit(f"[ERROR] {exc}") from exc
