#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# NeoMint OS — One-Shot Installer for Linux Mint
#
# Usage:
#   chmod +x install.sh
#   ./install.sh
#
# Tested on: Linux Mint 21.x (Ubuntu 22.04 base)
# ──────────────────────────────────────────────────────────────
set -euo pipefail

NEOMINT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OLLAMA_BASE_MODEL="qwen2.5:3b"
PYTHON_MIN_MINOR=11
VENV_DIR=".venv"

# ── Colors & helpers ──────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${GREEN}[NeoMint]${NC} $*"; }
warn()    { echo -e "${YELLOW}[NeoMint]${NC} $*"; }
error()   { echo -e "${RED}[NeoMint ERROR]${NC} $*" >&2; }
section() { echo -e "\n${CYAN}${BOLD}── $* ──${NC}"; }

banner() {
    echo -e "${GREEN}${BOLD}"
    echo "  _   _            __  __ _       _   "
    echo " | \\ | | ___  ___ |  \\/  (_)_ __ | |_ "
    echo " |  \\| |/ _ \\/ _ \\| |\\/| | | '_ \\| __|"
    echo " | |\\  |  __/ (_) | |  | | | | | | |_ "
    echo " |_| \\_|\\___|\\___/|_|  |_|_|_| |_|\\__|"
    echo ""
    echo "  Local LLM-Powered OS Interaction Layer"
    echo -e "${NC}"
}

# ── Pre-flight checks ────────────────────────────────────────

check_os() {
    section "Checking operating system"
    if [[ ! -f /etc/os-release ]]; then
        error "Cannot detect OS. This installer requires Linux Mint or an Ubuntu/Debian derivative."
        exit 1
    fi
    # shellcheck source=/dev/null
    source /etc/os-release
    if [[ "${ID:-}" != "linuxmint" && "${ID_LIKE:-}" != *"ubuntu"* && "${ID_LIKE:-}" != *"debian"* ]]; then
        error "Unsupported OS: ${PRETTY_NAME:-unknown}"
        error "NeoMint requires Linux Mint or an Ubuntu/Debian-based distribution."
        exit 1
    fi
    info "Detected OS: ${PRETTY_NAME:-Linux}"
}

# ── System dependencies ──────────────────────────────────────

install_system_deps() {
    section "Installing system dependencies"
    sudo apt-get update -qq
    sudo apt-get install -y -qq \
        curl \
        git \
        build-essential \
        software-properties-common \
        xclip \
        xdotool \
        libssl-dev \
        pkg-config \
        > /dev/null
    info "System dependencies installed."
}

# ── Python 3.11+ ─────────────────────────────────────────────

ensure_python() {
    section "Ensuring Python 3.11+"

    if command -v python3.11 &>/dev/null; then
        PYTHON_BIN="python3.11"
    elif command -v python3 &>/dev/null; then
        local py_minor
        py_minor=$(python3 -c "import sys; print(sys.version_info.minor)")
        if (( py_minor >= PYTHON_MIN_MINOR )); then
            PYTHON_BIN="python3"
        else
            warn "Found Python 3.${py_minor}, need 3.${PYTHON_MIN_MINOR}+. Installing..."
            sudo add-apt-repository -y ppa:deadsnakes/ppa
            sudo apt-get update -qq
            sudo apt-get install -y -qq python3.11 python3.11-venv python3.11-dev > /dev/null
            PYTHON_BIN="python3.11"
        fi
    else
        warn "Python 3 not found. Installing Python 3.11..."
        sudo add-apt-repository -y ppa:deadsnakes/ppa
        sudo apt-get update -qq
        sudo apt-get install -y -qq python3.11 python3.11-venv python3.11-dev > /dev/null
        PYTHON_BIN="python3.11"
    fi

    info "Using: $($PYTHON_BIN --version)"
}

# ── Ollama ────────────────────────────────────────────────────

install_ollama() {
    section "Installing Ollama"

    if command -v ollama &>/dev/null; then
        info "Ollama already installed: $(ollama --version)"
    else
        info "Downloading and installing Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh
        info "Ollama installed."
    fi

    if ! systemctl is-active --quiet ollama 2>/dev/null; then
        info "Starting Ollama service..."
        sudo systemctl enable ollama
        sudo systemctl start ollama
        sleep 3
    fi
    info "Ollama service is running."

    info "Pulling base model: ${OLLAMA_BASE_MODEL} (this may take several minutes)..."
    ollama pull "${OLLAMA_BASE_MODEL}"
    info "Model ready: ${OLLAMA_BASE_MODEL}"
}

# ── MCP Server ────────────────────────────────────────────────

setup_mcp_server() {
    section "Setting up MCP Server"
    local mcp_dir="${NEOMINT_DIR}/mcp-server"

    if [[ ! -d "${mcp_dir}" ]]; then
        error "mcp-server/ directory not found. Is the repo intact?"
        exit 1
    fi

    cd "${mcp_dir}"

    if [[ ! -d "${VENV_DIR}" ]]; then
        info "Creating virtual environment..."
        "${PYTHON_BIN}" -m venv "${VENV_DIR}"
    fi

    # shellcheck source=/dev/null
    source "${VENV_DIR}/bin/activate"
    pip install --upgrade pip -q
    pip install -e ".[dev]" -q
    deactivate

    if [[ ! -f .env ]]; then
        cp .env.example .env
        info "Created mcp-server/.env from template."
    fi

    info "MCP Server setup complete."
    cd "${NEOMINT_DIR}"
}

# ── Agent (Phase 3 — stub) ───────────────────────────────────

setup_agent() {
    section "Setting up Agent"
    local agent_dir="${NEOMINT_DIR}/agent"

    if [[ ! -f "${agent_dir}/pyproject.toml" ]]; then
        info "Agent module not yet built (Phase 3). Skipping."
        return 0
    fi

    cd "${agent_dir}"
    if [[ ! -d "${VENV_DIR}" ]]; then
        "${PYTHON_BIN}" -m venv "${VENV_DIR}"
    fi
    source "${VENV_DIR}/bin/activate"
    pip install --upgrade pip -q
    pip install -e ".[dev]" -q
    deactivate
    info "Agent setup complete."
    cd "${NEOMINT_DIR}"
}

# ── Overlay UI (Phase 4 — stub) ──────────────────────────────

build_overlay_ui() {
    section "Building Overlay UI"
    local ui_dir="${NEOMINT_DIR}/overlay-ui"

    if [[ ! -f "${ui_dir}/package.json" ]]; then
        info "Overlay UI not yet built (Phase 4). Skipping."
        return 0
    fi

    if ! command -v cargo &>/dev/null; then
        info "Installing Rust toolchain..."
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
        # shellcheck source=/dev/null
        source "${HOME}/.cargo/env"
    fi

    if ! command -v node &>/dev/null; then
        info "Installing Node.js 20 LTS..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt-get install -y -qq nodejs > /dev/null
    fi

    cd "${ui_dir}"
    npm install
    npm run tauri build
    info "Overlay UI built."
    cd "${NEOMINT_DIR}"
}

# ── Systemd services (Phase 4 — stub) ────────────────────────

install_services() {
    section "Installing systemd services"

    local service_dir="${NEOMINT_DIR}/services"
    if [[ ! -d "${service_dir}" ]]; then
        info "Systemd service files not yet created (Phase 4). Skipping."
        return 0
    fi

    sudo cp "${service_dir}/neomint-agent.service" /etc/systemd/system/
    sudo cp "${service_dir}/neomint-ui.service" /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable neomint-agent neomint-ui
    info "Systemd services installed and enabled."
}

# ── Environment file ─────────────────────────────────────────

setup_env() {
    section "Setting up environment"
    if [[ ! -f "${NEOMINT_DIR}/.env" ]]; then
        cp "${NEOMINT_DIR}/.env.example" "${NEOMINT_DIR}/.env"
        info "Created root .env from template."
    else
        info "Root .env already exists, skipping."
    fi
}

# ── Smoke test ────────────────────────────────────────────────

smoke_test() {
    section "Running smoke tests"

    info "Testing Ollama connectivity..."
    if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        info "✓ Ollama is responding."
    else
        warn "✗ Ollama is not responding on localhost:11434."
        warn "  Try: sudo systemctl restart ollama"
    fi

    info "Testing MCP server import..."
    local mcp_dir="${NEOMINT_DIR}/mcp-server"
    if "${mcp_dir}/${VENV_DIR}/bin/python" -c "import neomint_mcp; print(f'neomint_mcp v{neomint_mcp.__version__}')" 2>/dev/null; then
        info "✓ MCP server package is importable."
    else
        warn "✗ MCP server package import failed."
        warn "  Try: cd mcp-server && source .venv/bin/activate && pip install -e ."
    fi
}

# ── Success banner ────────────────────────────────────────────

success_banner() {
    echo ""
    echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}${BOLD}  NeoMint installation complete!${NC}"
    echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════${NC}"
    echo ""
    echo "  Next steps:"
    echo "    1. cd ${NEOMINT_DIR}/mcp-server"
    echo "    2. source .venv/bin/activate"
    echo "    3. pytest                          # run tests"
    echo "    4. python cli.py --help            # test tools manually"
    echo ""
    echo "  Ollama model: ollama run ${OLLAMA_BASE_MODEL}"
    echo ""
}

# ── Main ──────────────────────────────────────────────────────

main() {
    banner
    check_os
    install_system_deps
    ensure_python
    install_ollama
    setup_mcp_server
    setup_agent
    build_overlay_ui
    install_services
    setup_env
    smoke_test
    success_banner
}

main "$@"
