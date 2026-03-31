#!/usr/bin/env bash
# CNAB PIX Payment System - Mac/Linux Installer
# Usage: curl -sSL https://raw.githubusercontent.com/ribamartins/cnab-vtex/main/install.sh | bash
#    or: chmod +x install.sh && ./install.sh

set -e

REPO_URL="https://github.com/ribamartins/cnab-vtex.git"
INSTALL_DIR="${CNAB_INSTALL_DIR:-$HOME/.local/share/cnab-pix}"
MIN_PYTHON="3.12"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

step()  { echo -e "\n${CYAN}>> $1${NC}"; }
ok()    { echo -e "   ${GREEN}$1${NC}"; }
warn()  { echo -e "   ${YELLOW}$1${NC}"; }
fail()  { echo -e "   ${RED}$1${NC}"; }

echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  CNAB PIX Payment System - Instalador${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""
echo "Diretorio de instalacao: $INSTALL_DIR"

# --- Detect OS ---
OS="$(uname -s)"
case "$OS" in
    Linux*)  PLATFORM="linux";;
    Darwin*) PLATFORM="mac";;
    *)       fail "Sistema nao suportado: $OS"; exit 1;;
esac

# --- 1. Check/Install Python ---
step "Verificando Python..."

PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
        major=$(echo "$ver" | cut -d. -f1)
        minor=$(echo "$ver" | cut -d. -f2)
        min_major=$(echo "$MIN_PYTHON" | cut -d. -f1)
        min_minor=$(echo "$MIN_PYTHON" | cut -d. -f2)
        if [ "$major" -gt "$min_major" ] || { [ "$major" -eq "$min_major" ] && [ "$minor" -ge "$min_minor" ]; }; then
            PYTHON_CMD="$cmd"
            ok "Python $ver encontrado ($cmd)"
            break
        else
            warn "Python $ver encontrado, mas versao minima e $MIN_PYTHON"
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    warn "Python $MIN_PYTHON+ nao encontrado. Instalando..."

    if [ "$PLATFORM" = "mac" ]; then
        if command -v brew &>/dev/null; then
            echo "   Instalando via Homebrew..."
            brew install python@3.12
            PYTHON_CMD="python3"
        else
            fail "Homebrew nao encontrado. Instale Python manualmente:"
            fail "  https://python.org/downloads/"
            fail "  ou instale Homebrew: https://brew.sh"
            exit 1
        fi
    elif [ "$PLATFORM" = "linux" ]; then
        if command -v apt-get &>/dev/null; then
            echo "   Instalando via apt (pode pedir senha sudo)..."
            sudo apt-get update -qq
            sudo apt-get install -y -qq python3.12 python3.12-venv python3-pip
            PYTHON_CMD="python3.12"
        elif command -v dnf &>/dev/null; then
            echo "   Instalando via dnf (pode pedir senha sudo)..."
            sudo dnf install -y python3.12
            PYTHON_CMD="python3.12"
        elif command -v pacman &>/dev/null; then
            echo "   Instalando via pacman (pode pedir senha sudo)..."
            sudo pacman -S --noconfirm python
            PYTHON_CMD="python3"
        else
            fail "Gerenciador de pacotes nao encontrado. Instale Python manualmente:"
            fail "  https://python.org/downloads/"
            exit 1
        fi
    fi

    if [ -z "$PYTHON_CMD" ] || ! command -v "$PYTHON_CMD" &>/dev/null; then
        fail "Falha ao instalar Python. Instale manualmente: https://python.org/downloads/"
        exit 1
    fi
    ok "Python instalado com sucesso"
fi

# --- 2. Check/Install Git ---
step "Verificando Git..."

if command -v git &>/dev/null; then
    ok "Git encontrado: $(git --version)"
else
    warn "Git nao encontrado. Instalando..."

    if [ "$PLATFORM" = "mac" ]; then
        if command -v brew &>/dev/null; then
            brew install git
        else
            xcode-select --install 2>/dev/null || true
            echo "   Instale Xcode Command Line Tools quando solicitado, depois execute este script novamente."
            exit 1
        fi
    elif [ "$PLATFORM" = "linux" ]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get install -y -qq git
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y git
        elif command -v pacman &>/dev/null; then
            sudo pacman -S --noconfirm git
        fi
    fi

    if ! command -v git &>/dev/null; then
        fail "Falha ao instalar Git. Instale manualmente: https://git-scm.com"
        exit 1
    fi
    ok "Git instalado com sucesso"
fi

# --- 3. Clone repository ---
step "Clonando repositorio..."

if [ -f "$INSTALL_DIR/src/main.py" ]; then
    warn "Instalacao existente encontrada. Atualizando..."
    cd "$INSTALL_DIR"
    git pull origin staging 2>&1
    ok "Repositorio atualizado"
else
    rm -rf "$INSTALL_DIR" 2>/dev/null || true
    git clone --branch staging "$REPO_URL" "$INSTALL_DIR" 2>&1
    ok "Repositorio clonado em $INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# Clean up AI/development artifacts (not needed for runtime)
step "Limpando arquivos de desenvolvimento..."
rm -rf .planning/ .claude/ CLAUDE.md tests/ documents/Modelo.xlsx 2>/dev/null || true
ok "Arquivos de desenvolvimento removidos"

# --- 4. Create virtual environment and install dependencies ---
step "Criando ambiente virtual..."

if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
    ok "Ambiente virtual criado"
else
    ok "Ambiente virtual existente"
fi

step "Instalando dependencias..."
venv/bin/pip install --upgrade pip --quiet 2>&1
venv/bin/pip install -r requirements.txt --quiet 2>&1
ok "Dependencias instaladas"

# --- 5. Create launcher script ---
step "Criando launcher..."

LAUNCHER="$INSTALL_DIR/cnab-pix.sh"
cat > "$LAUNCHER" << 'LAUNCHER_EOF'
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
source venv/bin/activate
PYTHONPATH="$SCRIPT_DIR/src" python src/main.py "$@"
LAUNCHER_EOF
chmod +x "$LAUNCHER"
ok "Launcher criado: $LAUNCHER"

# Symlink to PATH
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
ln -sf "$LAUNCHER" "$BIN_DIR/cnab-pix"
ok "Comando 'cnab-pix' disponivel (certifique-se que ~/.local/bin esta no PATH)"

# Mac: create .app bundle (optional)
if [ "$PLATFORM" = "mac" ]; then
    APP_DIR="$HOME/Applications/CNAB PIX.app/Contents/MacOS"
    mkdir -p "$APP_DIR"
    ln -sf "$LAUNCHER" "$APP_DIR/CNAB PIX"
    ok "App criado em ~/Applications/CNAB PIX.app"
fi

# --- Done ---
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Instalacao concluida!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Para iniciar o sistema:"
echo "  cnab-pix"
echo "  ou: $LAUNCHER"
echo ""
