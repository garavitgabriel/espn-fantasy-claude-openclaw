#!/usr/bin/env bash
# ESPN Fantasy Baseball — OpenClaw installer
# Usage: ./install-openclaw.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo -e "${BOLD}ESPN Fantasy Baseball — OpenClaw Setup${NC}\n"

# ─── Step 1: Check for uv ───────────────────────────────────────────────────
echo -e "${BOLD}[1/5]${NC} Checking for uv..."
if ! command -v uv &>/dev/null; then
    echo -e "${YELLOW}uv not found. Installing...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    echo -e "${GREEN}uv installed.${NC}"
else
    echo -e "${DIM}uv $(uv --version) found.${NC}"
fi

# ─── Step 2: Install dependencies ───────────────────────────────────────────
echo -e "\n${BOLD}[2/5]${NC} Installing dependencies..."
cd "$SCRIPT_DIR"
uv sync 2>&1 | tail -1
echo -e "${GREEN}Dependencies installed.${NC}"

# ─── Step 3: Register MCP server ────────────────────────────────────────────
echo -e "\n${BOLD}[3/5]${NC} Registering MCP server with OpenClaw..."

MCP_CONFIG="{\"command\":\"uv\",\"args\":[\"run\",\"--project\",\"$SCRIPT_DIR\",\"espn-mcp\"]}"

if command -v openclaw &>/dev/null; then
    openclaw mcp set espn-baseball "$MCP_CONFIG" 2>/dev/null && \
        echo -e "${GREEN}MCP server registered.${NC}" || \
        echo -e "${YELLOW}Could not register automatically. See manual steps below.${NC}"
else
    echo -e "${YELLOW}openclaw CLI not found. Add this to your OpenClaw config manually:${NC}"
    echo -e "${DIM}"
    echo '  "espn-baseball": {'
    echo '    "command": "uv",'
    echo "    \"args\": [\"run\", \"--project\", \"$SCRIPT_DIR\", \"espn-mcp\"]"
    echo '  }'
    echo -e "${NC}"
fi

# ─── Step 4: Copy skills ────────────────────────────────────────────────────
echo -e "\n${BOLD}[4/5]${NC} Copying skills..."

OPENCLAW_WORKSPACE="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"
SKILLS_DEST="$OPENCLAW_WORKSPACE/skills"
mkdir -p "$SKILLS_DEST"

SKILL_COUNT=0
for skill_dir in "$SCRIPT_DIR"/skills/*/; do
    if [ -d "$skill_dir" ]; then
        skill_name=$(basename "$skill_dir")
        cp -r "$skill_dir" "$SKILLS_DEST/$skill_name"
        SKILL_COUNT=$((SKILL_COUNT + 1))
    fi
done
echo -e "${GREEN}${SKILL_COUNT} skills copied to ${SKILLS_DEST}${NC}"

# ─── Step 5: Next steps ─────────────────────────────────────────────────────
echo -e "\n${BOLD}[5/5]${NC} Almost done! Next steps:\n"
echo -e "  ${BOLD}1.${NC} Set your ESPN credentials (pick one):"
echo -e ""
echo -e "     ${BOLD}Browser login (easiest):${NC}"
echo -e "     ${DIM}uv sync --extra browser && uv run playwright install chromium${NC}"
echo -e "     ${DIM}uv run --project $SCRIPT_DIR espn auth login${NC}"
echo -e ""
echo -e "     ${BOLD}Manual token:${NC}"
echo -e "     ${DIM}uv run --project $SCRIPT_DIR espn auth token <ESPN_S2> <ESPN_SWID>${NC}"
echo -e "     Get cookies from: ESPN Fantasy > DevTools > Application > Cookies"
echo -e ""
echo -e "  ${BOLD}2.${NC} Restart OpenClaw gateway:"
echo -e "     ${DIM}openclaw gateway restart${NC}"
echo -e ""
echo -e "  ${BOLD}3.${NC} Try it out:"
echo -e '     "Show my fantasy baseball standings"'
echo -e ""
echo -e "${GREEN}${BOLD}Setup complete!${NC}"
