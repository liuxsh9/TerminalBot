## ADDED Requirements

### Requirement: Bot initialization
The system SHALL initialize a Telegram Bot using the configured Bot Token from environment variables or configuration file.

#### Scenario: Successful initialization
- **WHEN** the application starts with a valid TELEGRAM_BOT_TOKEN
- **THEN** the bot connects to Telegram API and begins listening for messages

#### Scenario: Missing token
- **WHEN** the application starts without TELEGRAM_BOT_TOKEN configured
- **THEN** the system exits with an error message indicating the missing configuration

### Requirement: User authentication
The system SHALL only respond to messages from authorized Telegram user IDs configured in the whitelist.

#### Scenario: Authorized user sends command
- **WHEN** a user with ID in AUTHORIZED_USERS sends a message
- **THEN** the system processes the command and responds

#### Scenario: Unauthorized user sends command
- **WHEN** a user with ID not in AUTHORIZED_USERS sends a message
- **THEN** the system ignores the message or responds with "Unauthorized"

### Requirement: Command handling
The system SHALL support the following commands: /start, /help, /list, /connect, /disconnect, /send.

#### Scenario: User sends /start
- **WHEN** authorized user sends /start
- **THEN** the system responds with a welcome message and available commands

#### Scenario: User sends /help
- **WHEN** authorized user sends /help
- **THEN** the system responds with command usage instructions

#### Scenario: User sends /list
- **WHEN** authorized user sends /list
- **THEN** the system responds with available tmux sessions and their panes

#### Scenario: User sends /connect with session identifier
- **WHEN** authorized user sends /connect <session>:<window>.<pane>
- **THEN** the system connects to the specified tmux pane and begins streaming output

#### Scenario: User sends /disconnect
- **WHEN** authorized user sends /disconnect while connected to a session
- **THEN** the system stops streaming output from the current session

### Requirement: Text input forwarding
The system SHALL forward non-command text messages to the connected terminal session.

#### Scenario: User sends text while connected
- **WHEN** authorized user sends a text message (not starting with /) while connected to a session
- **THEN** the system sends the text followed by Enter key to the connected tmux pane

#### Scenario: User sends text while not connected
- **WHEN** authorized user sends a text message while not connected to any session
- **THEN** the system responds with "Not connected to any session. Use /connect first."

### Requirement: Output message formatting
The system SHALL format terminal output for readability in Telegram, using monospace formatting.

#### Scenario: Terminal produces output
- **WHEN** the connected terminal produces new output
- **THEN** the system sends the output wrapped in monospace code blocks

#### Scenario: Output exceeds Telegram limit
- **WHEN** the output exceeds 4000 characters
- **THEN** the system truncates the output and indicates "[truncated]"
