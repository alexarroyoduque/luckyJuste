from pathlib import Path

# Applies the luckyJuste patch to the USA Harmony of Dissonance ROM
# Run with: python apply-luckyJuste.py
version = "1.0.0"
original_rom = "rom-harmony-usa.gba"
patched_rom = f"rom-harmony-usa-luckyJuste-drop-{version}.gba"

# ------------------------------------------------------------------------------
# 1. DROP ROUTINE PATCH POINTS
# ------------------------------------------------------------------------------
PATCH_OFFSET_DROP2 = 0x031456  # Rare drop
PATCH_OFFSET_DROP1 = 0x0314A0  # Normal drop; 0x03149E is the previous instruction

# Original 10 bytes replaced at each patch point.
EXPECTED_DROP2 = bytes.fromhex("79 20 F8 F7 40 F9 00 28 04 D0")
EXPECTED_DROP1 = bytes.fromhex("79 20 F8 F7 1B F9 00 28 05 D0")

# ------------------------------------------------------------------------------
# 2. VERIFIED FREE SPACE AT THE END OF THE ROM
# ------------------------------------------------------------------------------
# The clean USA ROM has a large block of 0xFF bytes at the end.
# Use two separate areas and verify they are free before writing.
# Each routine uses 0x34 bytes (52 bytes).
STUB_SIZE = 0x34
STUB_DROP2_OFFSET = 0x7FFF80
STUB_DROP1_OFFSET = 0x7FFFC0

LCK_ADDR = 0x02018558
LEVEL_ADDR = 0x0201877C

# Skip the vanilla Rare Ring bonus branches and resume at the original
# no-ring comparison paths. Bit 0 = 1 selects THUMB mode.
RETURN_DROP2 = 0x0803146B  # resume at cmp r4, r6 (0x0803146A)
RETURN_DROP1 = 0x080314B7  # resume at ldrh r1,[r7,#8] (0x080314B6)

# ------------------------------------------------------------------------------
# 3. RARE RING: +22 LCK
# ------------------------------------------------------------------------------
RARE_RING_BASE_OFFSET = 0x4B2C0C
LCK_BYTE_OFFSET = RARE_RING_BASE_OFFSET + 9
NEW_LCK_VALUE = 22


def gba_thumb_addr(rom_offset: int) -> int:
    """Convert a ROM offset to a GBA THUMB address (bit 0 = 1)."""
    return (0x08000000 + rom_offset) | 1


def make_entry_stub(patch_offset: int, target_rom_offset: int) -> bytes:
    """
    Build a THUMB trampoline of EXACTLY 10 bytes.

    IMPORTANT: the 32-bit address literal must be 4-byte aligned.
    The two patch points have different alignment:

      PATCH % 4 == 2:
          nop
          ldr r0, [pc, #0]
          bx  r0
          .word target      ; aligned

      PATCH % 4 == 0:
          ldr r0, [pc, #0]
          bx  r0
          .word target      ; aligned
          nop

    This avoids the unaligned LDR problem from the older version, which could rotate
    the address bytes and cause a jump to an invalid address.
    """
    target = gba_thumb_addr(target_rom_offset).to_bytes(4, "little")

    if patch_offset % 4 == 2:
        entry = (
            bytes.fromhex("C0 46") +  # nop
            bytes.fromhex("00 48") +  # ldr r0, [pc, #0]
            bytes.fromhex("00 47") +  # bx  r0
            target
        )
    elif patch_offset % 4 == 0:
        entry = (
            bytes.fromhex("00 48") +  # ldr r0, [pc, #0]
            bytes.fromhex("00 47") +  # bx  r0
            target +
            bytes.fromhex("C0 46")    # nop (padding to 10 bytes)
        )
    else:
        raise ValueError(f"Invalid or unaligned THUMB offset: 0x{patch_offset:X}")

    if len(entry) != 10:
        raise AssertionError("The trampoline must be exactly 10 bytes")
    return entry


def make_drop_stub(return_addr: int) -> bytes:
    """THUMB: r6 += (LCK total - level - 24), without multiplier."""
    # Keep the original 0x34-byte stub layout and literal locations.
    code = bytes.fromhex(
        "09 48"  # +00 ldr r0, [pc, #36] -> LCK
        "01 88"  # +02 ldrh r1, [r0]
        "09 48"  # +04 ldr r0, [pc, #36] -> level
        "00 78"  # +06 ldrb r0, [r0]
        "09 1A"  # +08 subs r1, r1, r0
        "18 39"  # +0A subs r1, #24 (natural luck baseline)
        "76 18"  # +0C adds r6, r6, r1 (equipment luck x1)
        "08 48"  # +0E ldr r0, [pc, #32] -> return address at +30
        "00 47"  # +10 bx r0
        + "C0 46" * 11  # +12..+27 nop padding
    )
    stub = (code + LCK_ADDR.to_bytes(4, "little")
            + LEVEL_ADDR.to_bytes(4, "little")
            + return_addr.to_bytes(4, "little"))
    assert len(stub) == STUB_SIZE
    return stub


def require_bytes(rom: bytearray, offset: int, expected: bytes, label: str) -> None:
    actual = bytes(rom[offset:offset + len(expected)])
    if actual != expected:
        raise ValueError(
            f"{label}: unexpected bytes at 0x{offset:X}.\n"
            f"Expected: {expected.hex(' ')}\n"
            f"Actual:   {actual.hex(' ')}\n"
            "Use a clean, unpatched USA ROM."
        )


def require_free_space(rom: bytearray, offset: int, size: int, label: str) -> None:
    area = rom[offset:offset + size]
    if len(area) != size or any(b != 0xFF for b in area):
        raise ValueError(
            f"{label}: 0x{offset:X}-0x{offset + size - 1:X} is not filled with 0xFF."
        )


def apply_full_patch():
    try:
        rom_data = bytearray(Path(original_rom).read_bytes())
        print(f"[+] Reading original ROM: {original_rom}")

        if len(rom_data) < 0x800000:
            raise ValueError(
                f"ROM is too small: 0x{len(rom_data):X} bytes; expected at least 0x800000."
            )

        require_bytes(rom_data, PATCH_OFFSET_DROP2, EXPECTED_DROP2, "DROP 2")
        require_bytes(rom_data, PATCH_OFFSET_DROP1, EXPECTED_DROP1, "DROP 1")
        require_free_space(rom_data, STUB_DROP2_OFFSET, STUB_SIZE, "Stub DROP 2")
        require_free_space(rom_data, STUB_DROP1_OFFSET, STUB_SIZE, "Stub DROP 1")

        require_bytes(rom_data, 0x03146A, bytes.fromhex("B4 42 0F D2"), "DROP 2 comparison")
        require_bytes(rom_data, 0x0314B6, bytes.fromhex("39 89 B4 42 15 D2"), "DROP 1 comparison")

        stub_drop2 = make_drop_stub(RETURN_DROP2)
        stub_drop1 = make_drop_stub(RETURN_DROP1)
        entry_drop2 = make_entry_stub(PATCH_OFFSET_DROP2, STUB_DROP2_OFFSET)
        entry_drop1 = make_entry_stub(PATCH_OFFSET_DROP1, STUB_DROP1_OFFSET)

        # Write the routines into the verified free areas.
        rom_data[STUB_DROP2_OFFSET:STUB_DROP2_OFFSET + STUB_SIZE] = stub_drop2
        rom_data[STUB_DROP1_OFFSET:STUB_DROP1_OFFSET + STUB_SIZE] = stub_drop1

        # Replace exactly 10 bytes at each patch point with the trampoline.
        rom_data[PATCH_OFFSET_DROP2:PATCH_OFFSET_DROP2 + 10] = entry_drop2
        rom_data[PATCH_OFFSET_DROP1:PATCH_OFFSET_DROP1 + 10] = entry_drop1

        # Rare Ring +22 LCK.
        rom_data[LCK_BYTE_OFFSET] = NEW_LCK_VALUE

        print(f"[+] DROP 2 -> stub 0x{STUB_DROP2_OFFSET:X} / GBA 0x{gba_thumb_addr(STUB_DROP2_OFFSET):08X}")
        print(f"[+] DROP 1 -> stub 0x{STUB_DROP1_OFFSET:X} / GBA 0x{gba_thumb_addr(STUB_DROP1_OFFSET):08X}")
        print("[+] Formula: extra_lck = LCK_ATTR - level - 24")
        print("[+] Ratio: extra_drop = extra_lck  # x1.00")
        print(f"[+] Rare Ring: +{NEW_LCK_VALUE} LCK (offset 0x{LCK_BYTE_OFFSET:X})")

        Path(patched_rom).write_bytes(rom_data)
        print(f"\n[OK] Patched ROM: '{patched_rom}'")

    except FileNotFoundError:
        print(f"[X] File not found: '{original_rom}'.")
    except ValueError as exc:
        print(f"[X] Verification error: {exc}")


if __name__ == "__main__":
    apply_full_patch()
