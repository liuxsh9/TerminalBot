## ADDED Requirements

### Requirement: Session connection management
The system SHALL maintain a mapping between Telegram chat IDs and connected tmux panes.

#### Scenario: User connects to session
- **WHEN** a user requests connection to a tmux pane
- **THEN** the system stores the mapping of chat_id to pane identifier

#### Scenario: User disconnects
- **WHEN** a user requests disconnection
- **THEN** the system removes the mapping for that chat_id

#### Scenario: Query connection status
- **WHEN** the system checks if a chat_id is connected
- **THEN** it returns the connected pane identifier or None

### Requirement: Output routing
The system SHALL route terminal output to the correct Telegram chat based on connection mapping.

#### Scenario: New output detected
- **WHEN** a connected pane produces new output
- **THEN** the system sends the output to the associated Telegram chat

#### Scenario: Multiple users connected to different panes
- **WHEN** multiple users are connected to different panes
- **THEN** each user receives output only from their connected pane

### Requirement: Connection lifecycle
The system SHALL handle connection lifecycle events properly.

#### Scenario: Pane closes while connected
- **WHEN** a connected tmux pane is closed or destroyed
- **THEN** the system notifies the user and removes the connection

#### Scenario: Reconnection after disconnect
- **WHEN** a user connects to a new pane after disconnecting
- **THEN** the previous connection is fully cleaned up before new connection

### Requirement: Output buffering
The system SHALL buffer rapid output to avoid message flooding.

#### Scenario: Rapid output bursts
- **WHEN** the terminal produces many lines of output in quick succession
- **THEN** the system batches them into fewer messages with reasonable delay

#### Scenario: Slow output
- **WHEN** the terminal produces output slowly (> 2 seconds between lines)
- **THEN** each output is sent as a separate message

### Requirement: Error handling
The system SHALL handle errors gracefully and inform the user.

#### Scenario: tmux connection lost
- **WHEN** the connection to tmux is lost
- **THEN** the system notifies connected users and attempts to reconnect

#### Scenario: Telegram API error
- **WHEN** sending a message to Telegram fails
- **THEN** the system logs the error and retries with exponential backoff
