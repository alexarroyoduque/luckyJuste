from pathlib import Path

ROM_FILE = "rom-harmony-usa.gba"
MIN_FREE_SIZE = 64

data = Path(ROM_FILE).read_bytes()

# Find the last block of consecutive 0xFF bytes
end = len(data)
start = end

while start > 0 and data[start - 1] == 0xFF:
    start -= 1

size = end - start

if size >= MIN_FREE_SIZE:
    print(f"Free block found:")
    print(f"ROM offset:   0x{start:06X}")
    print(f"GBA address:  0x{0x08000000 + start:08X}")
    print(f"End offset:   0x{end - 1:06X}")
    print(f"Size:         {size} bytes (0x{size:X})")
else:
    print(
        f"No final 0xFF block of at least "
        f"{MIN_FREE_SIZE} bytes was found."
    )