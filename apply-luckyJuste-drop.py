from pathlib import Path

# luckyJuste drop patch with equipment LCK ratio x0.50. Apply ONLY to a clean USA ROM.
version = "1.0.0"
original_rom = "rom-harmony-usa.gba"
patched_rom = f"rom-harmony-usa-luckyJuste-drop-{version}.gba"

DROP2_HOOK = 0x031456
DROP1_HOOK = 0x0314A0
DROP2_STUB = 0x7FFE80
DROP1_STUB = 0x7FFF00
STUB_SIZE = 0x48

# Assembled for ARM7TDMI Thumb; first 0x30 bytes are code.
# Logic: r6 += floor(max(0, total_lck - level - 24) / 2).
# Then call the original equipped-item check (0x080296DC), and jump
# to the EXISTING equipped or unequipped branch, without rewriting it.
CODE = bytes.fromhex(
    "0B 48 01 88 0B 48 00 78 09 1A 18 39 00 D5 00 21 "
    "49 08 C0 46 C0 46 C0 46 76 18 79 20 07 4A 96 46 "
    "05 4B 18 47 00 28 01 D0 05 48 00 47 05 48 00 47"
)
assert len(CODE) == 0x30


def thumb(rom_offset):
    return (0x08000000 + rom_offset) | 1


def require(rom, offset, expected, label):
    found = bytes(rom[offset:offset + len(expected)])
    if found != expected:
        raise ValueError(f"{label} at 0x{offset:X}: expected {expected.hex(' ')}, got {found.hex(' ')}")


def entry(hook, stub):
    target = thumb(stub).to_bytes(4, "little")
    if hook % 4 == 2:
        return bytes.fromhex("C0 46 00 48 00 47") + target
    if hook % 4 == 0:
        return bytes.fromhex("00 48 00 47") + target + bytes.fromhex("C0 46")
    raise ValueError("Unaligned hook")


def make_stub(offset, equipped_return, plain_return):
    words = (
        0x02018558,              # +0x30 LCK
        0x0201877C,              # +0x34 level
        0x080296DD,              # +0x38 original equipment-check function (Thumb)
        thumb(offset + 0x24),   # +0x3C return from equipment-check
        equipped_return,        # +0x40 original equipped-item bonus branch
        plain_return,           # +0x44 original no-bonus comparison branch
    )
    result = CODE + b"".join(w.to_bytes(4, "little") for w in words)
    assert len(result) == STUB_SIZE
    return result


def main():
    rom = bytearray(Path(original_rom).read_bytes())
    if len(rom) != 0x800000:
        raise ValueError("Expected 8 MiB USA ROM")
    require(rom, DROP2_HOOK, bytes.fromhex("79 20 F8 F7 40 F9 00 28 04 D0"), "Drop 2 hook")
    require(rom, DROP1_HOOK, bytes.fromhex("79 20 F8 F7 1B F9 00 28 05 D0"), "Drop 1 hook")
    require(rom, 0x031460, bytes.fromhex("30 1C 10 30 84 42"), "Original rare bonus")
    require(rom, 0x0314AA, bytes.fromhex("30 1C 20 30 84 42"), "Original normal bonus")
    for offset in (DROP2_STUB, DROP1_STUB):
        require(rom, offset, b"\xff" * STUB_SIZE, "Stub free space")
    for hook, offset, equipped, plain in (
        (DROP2_HOOK, DROP2_STUB, 0x08031461, 0x0803146B),
        (DROP1_HOOK, DROP1_STUB, 0x080314AB, 0x080314B7),
    ):
        rom[offset:offset + STUB_SIZE] = make_stub(offset, equipped, plain)
        rom[hook:hook + 10] = entry(hook, offset)
    Path(patched_rom).write_bytes(rom)
    print(f"Created {patched_rom}")
    print("Bonus = floor(max(0, LCK_total - level - 24) / 2)")
    print("Original equipped-item checks and item stats unchanged")


if __name__ == "__main__":
    main()
