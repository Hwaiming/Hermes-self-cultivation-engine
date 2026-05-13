#!/usr/bin/env bash
# Self-Cultivation Engine · Installer
#
# Installs the engine on Linux (SteamOS, Arch, Debian, Ubuntu).
# Writes everything under ~/.local/share/self-cultivation-engine/
# and creates a launcher script in ~/.local/bin/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="${HOME}/.local/share/self-cultivation-engine"
BIN_DIR="${HOME}/.local/bin"

echo "Self-Cultivation Engine Installer"
echo "================================="
echo ""

# ── 1. Detect environment ──
echo "[1/4] Detecting environment..."
OS_ID="$(grep -oP '^ID=\K.*' /etc/os-release 2>/dev/null || echo 'unknown')"
echo "  OS: $OS_ID"

PYTHON_OK=false
if command -v python3 &>/dev/null; then
    PY_VER="$(python3 --version 2>&1)"
    echo "  Python: $PY_VER"
    PYTHON_OK=true
else
    echo "  ERROR: python3 not found"
    echo "  Install: sudo pacman -S python (Arch/SteamOS) or sudo apt install python3 (Debian)"
    exit 1
fi

# ── 2. Copy engine files ──
echo ""
echo "[2/4] Installing engine to ${INSTALL_DIR}..."
mkdir -p "${INSTALL_DIR}" "${BIN_DIR}"

if [[ -d "${SCRIPT_DIR}/engine" ]]; then
    cp -r "${SCRIPT_DIR}/engine" "${INSTALL_DIR}/"
    cp -r "${SCRIPT_DIR}/docs" "${INSTALL_DIR}/"
    cp "${SCRIPT_DIR}/README.md" "${INSTALL_DIR}/" 2>/dev/null || true
    echo "  Engine files copied"
else
    echo "  Run from repo root: bash install.sh"
    echo "  Or: git clone git@github.com:Hwaiming/Hermes-self-cultivation-engine.git && cd Hermes-self-cultivation-engine && bash install.sh"
    exit 1
fi

# ── 3. Check Python deps ──
echo ""
echo "[3/4] Checking Python dependencies..."
for dep in yaml; do
    if python3 -c "import $dep" 2>/dev/null; then
        echo "  $dep: ok"
    else
        echo "  $dep: missing (engine will use stdlib fallback)"
        if [[ "$OS_ID" == "steamos" || "$OS_ID" == "arch" ]]; then
            echo "    Install: sudo pacman -S python-$dep"
        fi
    fi
done

# ── 4. Install command ──
echo ""
echo "[4/4] Installing command..."
cat > "${INSTALL_DIR}/self-cultivation.sh" << 'LAUNCH_EOF'
#!/usr/bin/env bash
# Self-Cultivation Engine launcher
ENGINE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ENGINE_DIR"

case "${1:-help}" in
    check)
        echo "Running self-cultivation check..."
        python3 -m engine.check
        ;;
    status)
        python3 -c "
import sys; sys.path.insert(0, '.')
from engine.detectors.registry import get_registry
d = get_registry().detectors
print(f'Engine: {__import__(\"pathlib\").Path(\".\").resolve()}')
print(f'Detectors: {len(d)} registered')
for name, det in sorted(d.items()):
    print(f'  - {name} ({det.severity.value})')
"
        ;;
    evidence)
        python3 -m engine.check --evidence
        ;;
    fsm)
        python3 -m engine.fsm.runner status
        ;;
    bridge)
        shift
        python3 engine/bridge/scale-bridge.py "$@"
        ;;
    *)
        echo "Self-Cultivation Engine"
        echo ""
        echo "Usage:"
        echo "  self-cultivation check      — Run all detectors"
        echo "  self-cultivation status     — Show engine status"
        echo "  self-cultivation evidence    — Show evidence store"
        echo "  self-cultivation fsm        — Current FSM state"
        echo "  self-cultivation bridge ARGS — SCALE Bridge gate"
        echo ""
        echo "Installed at: ${ENGINE_DIR}"
        ;;
esac
LAUNCH_EOF
chmod +x "${INSTALL_DIR}/self-cultivation.sh"

ln -sf "${INSTALL_DIR}/self-cultivation.sh" "${BIN_DIR}/self-cultivation" 2>/dev/null || true
if [[ ":$PATH:" == *":${BIN_DIR}:"* ]]; then
    echo "  Command installed: self-cultivation"
else
    echo "  Add to PATH: export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo "  Or run directly: ${INSTALL_DIR}/self-cultivation.sh"
fi

# ── Done ──
echo ""
echo "================================="
echo "Installation complete."
echo ""
echo "Try:"
echo "  self-cultivation check"
echo "  self-cultivation status"
echo "================================="
