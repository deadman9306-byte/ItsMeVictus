#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
#  Zorzer L4 — One-file installer
#  Run:  bash setup.sh
# ──────────────────────────────────────────────────────────────────────────────

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "======================================================================"
echo "  ⚡  ZORZER L4 — SETUP"
echo "======================================================================"
echo ""

# ── 1. Python check ───────────────────────────────────────────────────────────
echo -e "${YELLOW}[1/5] Checking Python...${NC}"
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}✗ Python3 not found. Install it first.${NC}"
    exit 1
fi
PY=$(python3 --version)
echo -e "${GREEN}✓ $PY${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$(command -v python3)"
PYTHON_PACKAGES_DIR="$SCRIPT_DIR/.python-packages"

# ── 2. System Python check ─────────────────────────────────────────────────────
echo -e "${YELLOW}[2/5] Preparing system Python...${NC}"
if [ -z "$PYTHON_BIN" ]; then
    echo -e "${RED}✗ Could not locate python3.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ system Python ready${NC}"

# ── 3. Install dependencies ───────────────────────────────────────────────────
echo -e "${YELLOW}[3/5] Installing dependencies...${NC}"
# Install into a project-local package directory so the app can use plain
# `python3` without modifying Replit's immutable Nix interpreter. A temporary
# virtual environment supplies pip on fresh Repls where neither uv nor pip is
# available from the system interpreter.
BOOTSTRAP_VENV="$(mktemp -d "${TMPDIR:-/tmp}/itsmevictus-setup.XXXXXX")"
cleanup_bootstrap() {
    rm -rf "$BOOTSTRAP_VENV"
}
trap cleanup_bootstrap EXIT

if ! "$PYTHON_BIN" -m venv "$BOOTSTRAP_VENV"; then
    echo -e "${RED}✗ Could not create a temporary installer environment.${NC}"
    exit 1
fi
if ! "$BOOTSTRAP_VENV/bin/python" -m pip install --target \
    "$PYTHON_PACKAGES_DIR" -r "$SCRIPT_DIR/requirements.txt" --upgrade --quiet; then
    echo -e "${RED}✗ Dependency installation failed.${NC}"
    exit 1
fi
if ! PYTHONPATH="$PYTHON_PACKAGES_DIR${PYTHONPATH:+:$PYTHONPATH}" \
    "$PYTHON_BIN" -c 'import flask, flask_cors, requests' &>/dev/null; then
    echo -e "${RED}✗ Dependencies are not importable from system Python.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ flask, flask-cors, requests installed${NC}"

# ── 4. Create proxies folder + blank proxies.txt if missing ───────────────────
echo -e "${YELLOW}[4/5] Setting up proxies folder...${NC}"
PROXY_DIR="$SCRIPT_DIR/proxies"
PROXY_FILE="$PROXY_DIR/proxies.txt"
mkdir -p "$PROXY_DIR"
if [ ! -f "$PROXY_FILE" ]; then
    cat > "$PROXY_FILE" <<'EOF'
# Zorzer Proxy List — one proxy per line
# Supported formats:
#   socks5://host:port
#   socks5://user:pass@host:port
#   host:port
#   host:port:user:pass
EOF
    echo -e "${GREEN}✓ proxies/proxies.txt created (empty — add your SOCKS5 proxies)${NC}"
else
    echo -e "${GREEN}✓ proxies/proxies.txt already exists${NC}"
fi

# ── 5. Config reminder ────────────────────────────────────────────────────────
echo -e "${YELLOW}[5/5] Config check...${NC}"
CONFIG="$SCRIPT_DIR/config.py"
if grep -q "YOUR_SUPABASE_URL" "$CONFIG" 2>/dev/null; then
    echo -e "${RED}⚠  Open Zorzer_L4/config.py and fill in your Supabase URL, key, and table name.${NC}"
else
    echo -e "${GREEN}✓ config.py looks configured${NC}"
fi

echo ""
echo "======================================================================"
echo -e "${GREEN}  ✅  Setup complete!${NC}"
echo ""
echo "  Start the API:"
echo "    python3 $SCRIPT_DIR/main.py"
echo ""
echo "  Or from inside the ItsMeVictus folder:"
echo "    python3 main.py"
echo "======================================================================"
echo ""
