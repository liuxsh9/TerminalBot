#!/bin/bash
# TerminalBot Installation Script
# Detects environment and installs using the best deployment method

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored messages
info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

# Environment detection variables
HAS_NODE="no"
HAS_PM2="no"
HAS_SYSTEMD="no"
HAS_LAUNCHD="no"
PLATFORM=""

# Detect environment
detect_environment() {
    info "Detecting environment..."

    # Check for Node.js
    if command -v node &> /dev/null; then
        HAS_NODE="yes"
        NODE_VERSION=$(node --version)
        success "Node.js detected: $NODE_VERSION"
    fi

    # Check for PM2
    if command -v pm2 &> /dev/null; then
        HAS_PM2="yes"
        PM2_VERSION=$(pm2 --version)
        success "PM2 detected: v$PM2_VERSION"
    fi

    # Detect platform
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        PLATFORM="linux"
        info "Platform: Linux"

        # Check for systemd
        if command -v systemctl &> /dev/null; then
            HAS_SYSTEMD="yes"
            success "systemd available"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        PLATFORM="macos"
        info "Platform: macOS"
        HAS_LAUNCHD="yes"
        success "launchd available"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        PLATFORM="windows"
        warning "Windows detected. Please use WSL for best compatibility."
    else
        PLATFORM="unknown"
        warning "Unknown platform: $OSTYPE"
    fi
}

# Check dependencies
check_dependencies() {
    info "Checking dependencies..."

    local all_ok="yes"

    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | grep -oE '[0-9]+\.[0-9]+')
        PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
        PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

        if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
            success "Python $PYTHON_VERSION (>= 3.10)"
        else
            error "Python 3.10+ required, found $PYTHON_VERSION"
            all_ok="no"
        fi
    else
        error "Python 3 not found"
        all_ok="no"
    fi

    # Check tmux
    if command -v tmux &> /dev/null; then
        success "tmux installed"
    else
        error "tmux not found. Install with: sudo apt install tmux (Linux) or brew install tmux (macOS)"
        all_ok="no"
    fi

    # Check uv
    if command -v uv &> /dev/null; then
        success "uv installed"
    else
        warning "uv not found"
        read -p "Install uv now? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            info "Installing uv..."
            curl -LsSf https://astral.sh/uv/install.sh | sh
            export PATH="$HOME/.local/bin:$PATH"
            success "uv installed"
        else
            error "uv is required. Install from: https://github.com/astral-sh/uv"
            all_ok="no"
        fi
    fi

    # Check .env file
    if [ -f ".env" ]; then
        if grep -q "TELEGRAM_BOT_TOKEN=" .env && grep -q "AUTHORIZED_USERS=" .env; then
            success ".env file configured"
        else
            warning ".env file exists but may be incomplete"
            info "Ensure TELEGRAM_BOT_TOKEN and AUTHORIZED_USERS are set"
        fi
    else
        warning ".env file not found"
        if [ -f ".env.example" ]; then
            read -p "Create .env from .env.example? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                cp .env.example .env
                success ".env created"
                warning "Please edit .env and set TELEGRAM_BOT_TOKEN and AUTHORIZED_USERS"
                all_ok="no"
            else
                error ".env is required"
                all_ok="no"
            fi
        else
            error ".env.example not found"
            all_ok="no"
        fi
    fi

    if [ "$all_ok" = "no" ]; then
        error "Please fix the issues above and run the installer again"
        exit 1
    fi
}

# Recommend deployment method
recommend_method() {
    if [ "$HAS_PM2" = "yes" ]; then
        echo "pm2"
    elif [ "$HAS_NODE" = "yes" ]; then
        echo "install-pm2"
    elif [ "$PLATFORM" = "linux" ] && [ "$HAS_SYSTEMD" = "yes" ]; then
        echo "systemd"
    elif [ "$PLATFORM" = "macos" ]; then
        echo "launchd"
    else
        echo "fallback"
    fi
}

# Install dependencies
install_deps() {
    info "Installing Python dependencies..."
    uv sync
    success "Dependencies installed"
}

# Install PM2 method
install_pm2() {
    info "Installing with PM2..."

    # Check if PM2 is available
    if [ "$HAS_PM2" = "no" ]; then
        if [ "$HAS_NODE" = "yes" ]; then
            info "Installing PM2 globally..."
            npm install -g pm2
            success "PM2 installed"
        else
            error "Node.js is required for PM2. Install Node.js first."
            exit 1
        fi
    fi

    # Create logs directory
    mkdir -p logs

    # Start with PM2
    info "Starting bot with PM2..."
    pm2 start install/pm2/ecosystem.config.js
    pm2 save

    success "Bot started with PM2"
    echo ""
    info "To enable auto-start on boot, run:"
    echo "  pm2 startup"
    echo "  # Follow the instructions printed by PM2"
    echo ""
    info "Management commands:"
    echo "  pm2 status       - Check status"
    echo "  pm2 logs terminalbot - View logs"
    echo "  pm2 restart terminalbot - Restart bot"
}

# Install systemd method
install_systemd() {
    info "Installing with systemd..."

    # Get absolute path
    PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

    # Create user systemd directory
    mkdir -p ~/.config/systemd/user

    # Copy and customize service file
    SERVICE_FILE=~/.config/systemd/user/terminalbot.service
    cp install/fallback/systemd/terminalbot.service "$SERVICE_FILE"

    # Replace working directory placeholder
    sed -i.bak "s|%h/terminal-bot|$PROJECT_DIR|g" "$SERVICE_FILE"
    rm "$SERVICE_FILE.bak"

    # Create logs directory
    mkdir -p logs

    # Reload, enable, and start
    systemctl --user daemon-reload
    systemctl --user enable terminalbot
    systemctl --user start terminalbot

    # Enable lingering
    loginctl enable-linger "$USER" 2>/dev/null || true

    success "Bot installed as systemd service"
    echo ""
    info "Management commands:"
    echo "  systemctl --user status terminalbot  - Check status"
    echo "  journalctl --user -u terminalbot -f  - View logs"
    echo "  systemctl --user restart terminalbot - Restart bot"
}

# Install launchd method
install_launchd() {
    info "Installing with launchd..."

    # Get absolute path
    PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

    # Customize plist file
    PLIST_FILE=~/Library/LaunchAgents/com.terminalbot.plist
    cp install/fallback/launchd/com.terminalbot.plist "$PLIST_FILE"

    # Replace paths
    sed -i.bak "s|~/terminal-bot|$PROJECT_DIR|g" "$PLIST_FILE"
    rm "$PLIST_FILE.bak"

    # Create logs directory
    mkdir -p logs

    # Load service
    launchctl load "$PLIST_FILE"

    success "Bot installed as launchd service"
    echo ""
    info "Management commands:"
    echo "  launchctl list | grep terminalbot - Check status"
    echo "  tail -f $PROJECT_DIR/logs/output.log - View logs"
    echo "  launchctl stop com.terminalbot - Stop bot"
}

# Install fallback method
install_fallback() {
    info "Installing with restart script..."

    # Make script executable
    chmod +x install/fallback/run_bot.sh

    # Create logs directory
    mkdir -p logs

    success "Restart script configured"
    echo ""
    info "To run the bot:"
    echo "  ./install/fallback/run_bot.sh"
    echo ""
    info "To run in background:"
    echo "  nohup ./install/fallback/run_bot.sh &"
    echo "  # or"
    echo "  screen -dmS terminalbot ./install/fallback/run_bot.sh"
}

# Verify installation
verify_installation() {
    info "Verifying installation..."

    sleep 2

    case "$1" in
        pm2)
            if pm2 list | grep -q terminalbot; then
                success "Bot is running"
                pm2 list | grep terminalbot
            else
                warning "Bot may not be running. Check with: pm2 list"
            fi
            ;;
        systemd)
            if systemctl --user is-active --quiet terminalbot; then
                success "Bot is running"
            else
                warning "Bot may not be running. Check with: systemctl --user status terminalbot"
            fi
            ;;
        launchd)
            if launchctl list | grep -q terminalbot; then
                success "Bot is running"
            else
                warning "Bot may not be running. Check with: launchctl list | grep terminalbot"
            fi
            ;;
        fallback)
            success "Script is ready to run"
            ;;
    esac
}

# Interactive menu
show_menu() {
    local recommended=$(recommend_method)

    echo ""
    echo "==============================================="
    echo "  TerminalBot Installation"
    echo "==============================================="
    echo ""
    echo "Choose deployment method:"
    echo ""

    if [ "$HAS_PM2" = "yes" ] || [ "$HAS_NODE" = "yes" ]; then
        if [ "$recommended" = "pm2" ] || [ "$recommended" = "install-pm2" ]; then
            echo "  1) PM2 (Recommended)"
        else
            echo "  1) PM2"
        fi
    fi

    if [ "$HAS_SYSTEMD" = "yes" ]; then
        if [ "$recommended" = "systemd" ]; then
            echo "  2) systemd (Recommended)"
        else
            echo "  2) systemd"
        fi
    fi

    if [ "$HAS_LAUNCHD" = "yes" ]; then
        if [ "$recommended" = "launchd" ]; then
            echo "  3) launchd (Recommended)"
        else
            echo "  3) launchd"
        fi
    fi

    echo "  4) Simple restart script (Fallback)"
    echo ""

    read -p "Enter choice [1-4]: " choice

    case $choice in
        1)
            if [ "$HAS_PM2" = "yes" ] || [ "$HAS_NODE" = "yes" ]; then
                return 0  # PM2
            else
                error "Invalid choice"
                show_menu
            fi
            ;;
        2)
            if [ "$HAS_SYSTEMD" = "yes" ]; then
                return 1  # systemd
            else
                error "Invalid choice"
                show_menu
            fi
            ;;
        3)
            if [ "$HAS_LAUNCHD" = "yes" ]; then
                return 2  # launchd
            else
                error "Invalid choice"
                show_menu
            fi
            ;;
        4)
            return 3  # fallback
            ;;
        *)
            error "Invalid choice"
            show_menu
            ;;
    esac
}

# Main installation flow
main() {
    echo ""
    echo "==============================================="
    echo "  TerminalBot Installer"
    echo "==============================================="
    echo ""

    # Change to script directory
    cd "$(dirname "${BASH_SOURCE[0]}")/.."

    # Detect environment
    detect_environment

    # Check dependencies
    check_dependencies

    # Install Python dependencies
    install_deps

    # Parse command-line arguments
    if [ "$#" -gt 0 ]; then
        case "$1" in
            --pm2)
                install_pm2
                verify_installation pm2
                ;;
            --systemd)
                install_systemd
                verify_installation systemd
                ;;
            --launchd)
                install_launchd
                verify_installation launchd
                ;;
            --fallback)
                install_fallback
                verify_installation fallback
                ;;
            *)
                error "Unknown option: $1"
                echo "Usage: $0 [--pm2|--systemd|--launchd|--fallback]"
                exit 1
                ;;
        esac
    else
        # Interactive mode
        show_menu
        choice=$?

        case $choice in
            0)
                install_pm2
                verify_installation pm2
                ;;
            1)
                install_systemd
                verify_installation systemd
                ;;
            2)
                install_launchd
                verify_installation launchd
                ;;
            3)
                install_fallback
                verify_installation fallback
                ;;
        esac
    fi

    echo ""
    success "Installation complete!"
    echo ""
}

# Run main if not sourced
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
