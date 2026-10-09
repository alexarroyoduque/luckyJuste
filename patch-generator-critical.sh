#!/bin/bash

# ============================================================
# Generate the IPS patch for luckyJuste
#
# Expected structure:
#
# project/
# ├── patch-generator.sh
# ├── RomPatcher.js/
# │   └── index.js
# ├── rom-harmony-usa.gba
# └── rom-harmony-usa-luckyJuste-1.0.0.gba
#
# Install RomPatcher.js:
#   git clone https://github.com/marcrobledo/RomPatcher.js.git
#   cd RomPatcher.js
#   npm install
#
# Run:
#   chmod +x patch-generator.sh
#   ./patch-generator-critical.sh
# ============================================================

# Directory containing this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Version
VERSION="1.0.0"

# Source ROMs
ROM_ORIGINAL_USA="$SCRIPT_DIR/rom-harmony-usa.gba"
ROM_PATCHED_USA="$SCRIPT_DIR/rom-harmony-usa-luckyJuste-critical-$VERSION.gba"

# Output patch
PATCH_USA="$SCRIPT_DIR/luckyJuste-critical.ips"

# RomPatcher.js
ROMPATCHER="$SCRIPT_DIR/RomPatcher.js/index.js"

# ============================================================
# DEPENDENCY CHECK
# ============================================================

# Check Node.js
if ! command -v node >/dev/null 2>&1; then
    echo "Error: Node.js is not installed or is not available in PATH." >&2
    exit 1
fi

# Check RomPatcher.js
if [ ! -f "$ROMPATCHER" ]; then
    echo "Error: RomPatcher.js was not found." >&2
    echo "" >&2
    echo "Expected location:" >&2
    echo "  $SCRIPT_DIR/RomPatcher.js" >&2
    echo "" >&2
    echo "Install it with:" >&2
    echo "  cd \"$SCRIPT_DIR\"" >&2
    echo "  git clone https://github.com/marcrobledo/RomPatcher.js.git" >&2
    echo "  cd RomPatcher.js" >&2
    echo "  npm install" >&2
    echo "" >&2
    exit 1
fi

# ============================================================
# CLEANUP
# ============================================================
echo "CLEANUP"

rm -f "$PATCH_USA"
echo "$PATCH_USA"
echo ""


# ============================================================
# GENERATE PATCH
# ============================================================

echo ""
echo "========================================"
echo "GENERATING PATCH"
echo "========================================"
echo ""

if node "$ROMPATCHER" create --format ips \
    "$ROM_ORIGINAL_USA" \
    "$ROM_PATCHED_USA"; then

    GENERATED_PATCH="${ROM_PATCHED_USA%.gba}.ips"

    echo "OK: USA patch generated"

    mv "$GENERATED_PATCH" "$PATCH_USA"

    echo "Patch: $PATCH_USA"
    echo ""
else
    echo "Error: USA patch generation failed." >&2
    exit 1
fi

echo "Process completed."
echo ""