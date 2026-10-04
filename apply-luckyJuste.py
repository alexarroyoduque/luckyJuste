from pathlib import Path

# Applies the luckyJuste patch to the USA Harmony of Dissonance ROM
# Run with: python apply-luckyJuste.py
version = "1.0.0"
original_rom = "rom-harmony-usa.gba"
patched_rom = f"rom-harmony-usa-luckyJuste-{version}.gba"

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

# After replacing 10 bytes, execution returns immediately after them.
# Bit 0 = 1 tells BX to return in THUMB mode.
RETURN_DROP2 = (0x08000000 + PATCH_OFFSET_DROP2 + 10) | 1  # 0x08031461
RETURN_DROP1 = (0x08000000 + PATCH_OFFSET_DROP1 + 10) | 1  # 0x080314AB

# ------------------------------------------------------------------------------
# 3. RARE RING: +24 LCK
# ------------------------------------------------------------------------------
RARE_RING_BASE_OFFSET = 0x4B2C0C
LCK_BYTE_OFFSET = RARE_RING_BASE_OFFSET + 9
NEW_LCK_VALUE = 24


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
    """
    48-byte THUMB routine:

        extra_lck = LCK_ATTR - level - 24
        extra_drop = (
            extra_lck
            + (extra_lck >> 3)
            + (extra_lck >> 4)
            + (extra_lck >> 6)
        )
        r6 += extra_drop

    This is an efficient approximation of x1.20 using only shifts and adds.
    The nominal binary ratio is x1.203125. Each shift truncates independently.

    Registers used:
        r0 = pointer / level / temporary shifted copy of extra_lck
        r1 = LCK, then extra_drop
        r2 = original extra_lck
        r6 = base drop value used by the original routine

    Equivalent assembly:
        ldr  r0, =0x02018558
        ldrh r1, [r0]
        ldr  r0, =0x0201877C
        ldrb r0, [r0]
        subs r1, r1, r0
        subs r1, #24
        movs r2, r1
        movs r0, r2
        lsrs r0, r0, #3
        adds r1, r1, r0
        movs r0, r2
        lsrs r0, r0, #4
        adds r1, r1, r0
        movs r0, r2
        lsrs r0, r0, #6
        adds r1, r1, r0
        adds r6, r6, r1
        ldr  r0, =return_addr
        bx   r0

        .word 0x02018558
        .word 0x0201877C
        .word return_addr
    """
    code = bytes.fromhex(
        "09 48"  # +00 ldr  r0, [pc, #36] -> literal at +40
        "01 88"  # +02 ldrh r1, [r0]
        "09 48"  # +04 ldr  r0, [pc, #36] -> literal at +44
        "00 78"  # +06 ldrb r0, [r0]
        "09 1A"  # +08 subs r1, r1, r0
        "18 39"  # +0A subs r1, #24
        "0A 00"  # +0C movs r2, r1
        "10 00"  # +0E movs r0, r2
        "C0 08"  # +10 lsrs r0, r0, #3
        "09 18"  # +12 adds r1, r1, r0
        "10 00"  # +14 movs r0, r2
        "00 09"  # +16 lsrs r0, r0, #4
        "09 18"  # +18 adds r1, r1, r0
        "10 00"  # +1A movs r0, r2
        "80 09"  # +1C lsrs r0, r0, #6
        "09 18"  # +1E adds r1, r1, r0
        "76 18"  # +20 adds r6, r6, r1
        "03 48"  # +22 ldr  r0, [pc, #12] -> literal at +48? see padding below
        "00 47"  # +24 bx   r0
        "C0 46"  # +26 nop; align literals
    )

    # At +0x28, +0x2C, +0x30. Total size = 0x34 (52 bytes).
    stub = (
        code
        + LCK_ADDR.to_bytes(4, "little")
        + LEVEL_ADDR.to_bytes(4, "little")
        + return_addr.to_bytes(4, "little")
    )

    if len(stub) != STUB_SIZE:
        raise AssertionError(
            f"The routine must be {STUB_SIZE} bytes, but it is {len(stub)}"
        )
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

        # Rare Ring +24 LCK.
        rom_data[LCK_BYTE_OFFSET] = NEW_LCK_VALUE

        print(f"[+] DROP 2 -> stub 0x{STUB_DROP2_OFFSET:X} / GBA 0x{gba_thumb_addr(STUB_DROP2_OFFSET):08X}")
        print(f"[+] DROP 1 -> stub 0x{STUB_DROP1_OFFSET:X} / GBA 0x{gba_thumb_addr(STUB_DROP1_OFFSET):08X}")
        print("[+] Formula: extra_lck = LCK_ATTR - level - 24")
        print("[+] Ratio: extra_drop = extra_lck + (extra_lck >> 3) + (extra_lck >> 4) + (extra_lck >> 6)  # approx x1.20 (nominal x1.203125)")
        print(f"[+] Rare Ring: +{NEW_LCK_VALUE} LCK (offset 0x{LCK_BYTE_OFFSET:X})")

        Path(patched_rom).write_bytes(rom_data)
        print(f"\n[OK] Patched ROM: '{patched_rom}'")

    except FileNotFoundError:
        print(f"[X] File not found: '{original_rom}'.")
    except ValueError as exc:
        print(f"[X] Verification error: {exc}")


if __name__ == "__main__":
    apply_full_patch()
