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
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"

# ── 2. Virtual environment check ───────────────────────────────────────────────
echo -e "${YELLOW}[2/5] Preparing project virtual environment...${NC}"
if [ ! -x "$PYTHON_BIN" ]; then
    echo "  Creating $VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi
if [ ! -x "$PYTHON_BIN" ]; then
    echo -e "${RED}✗ Could not create a project virtual environment.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ project Python ready${NC}"

# ── 3. Install dependencies ───────────────────────────────────────────────────
echo -e "${YELLOW}[3/5] Installing dependencies...${NC}"
if ! "$PYTHON_BIN" -m pip install -r "$SCRIPT_DIR/requirements.txt" --quiet; then
    echo -e "${RED}✗ Dependency installation failed.${NC}"
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
echo "    $VENV_DIR/bin/python $SCRIPT_DIR/main.py"
echo ""
echo "  Or from inside the Zorzer_L4 folder:"
echo "    .venv/bin/python main.py"
echo "======================================================================"
echo ""
