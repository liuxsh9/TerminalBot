## 1. Project Setup

- [x] 1.1 Create project directory structure (src/, config/, etc.)
- [x] 1.2 Initialize Python project with pyproject.toml or requirements.txt
- [x] 1.3 Add dependencies: python-telegram-bot, libtmux, python-dotenv
- [x] 1.4 Create .env.example with TELEGRAM_BOT_TOKEN and AUTHORIZED_USERS placeholders
- [x] 1.5 Create main entry point (main.py) with basic async structure

## 2. Terminal Capture Module

- [x] 2.1 Create terminal_capture.py module
- [x] 2.2 Implement tmux session discovery (list sessions, windows, panes)
- [x] 2.3 Implement pane content capture using libtmux
- [x] 2.4 Implement change detection (diff between captures)
- [x] 2.5 Implement input injection (send keys to pane)
- [x] 2.6 Implement async polling mechanism with configurable interval

## 3. Session Bridge Module

- [x] 3.1 Create session_bridge.py module
- [x] 3.2 Implement connection mapping (chat_id <-> pane)
- [x] 3.3 Implement output routing to correct Telegram chat
- [x] 3.4 Implement output buffering for rapid bursts
- [x] 3.5 Implement connection lifecycle handling (pane close detection)
- [x] 3.6 Implement error handling and reconnection logic

## 4. Telegram Bot Module

- [x] 4.1 Create telegram_bot.py module
- [x] 4.2 Implement bot initialization with token from environment
- [x] 4.3 Implement user authentication (whitelist check)
- [x] 4.4 Implement /start and /help command handlers
- [x] 4.5 Implement /list command to show available sessions
- [x] 4.6 Implement /connect command to attach to a tmux pane
- [x] 4.7 Implement /disconnect command to detach from session
- [x] 4.8 Implement text message forwarding to connected pane
- [x] 4.9 Implement output formatting (monospace, truncation)

## 5. Integration and Testing

- [x] 5.1 Integrate all modules in main.py
- [x] 5.2 Test session discovery with real tmux sessions
- [x] 5.3 Test output streaming from terminal to Telegram
- [x] 5.4 Test input forwarding from Telegram to terminal
- [x] 5.5 Test error handling (invalid session, disconnection)
- [x] 5.6 Create README.md with setup and usage instructions
