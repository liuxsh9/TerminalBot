## ADDED Requirements

### Requirement: tmux session discovery
The system SHALL discover all running tmux sessions, windows, and panes on the local machine.

#### Scenario: List available sessions
- **WHEN** the system queries for available sessions
- **THEN** it returns a list of all tmux sessions with their windows and panes

#### Scenario: No tmux server running
- **WHEN** the system queries for sessions but tmux server is not running
- **THEN** it returns an empty list or appropriate error message

### Requirement: Pane content capture
The system SHALL capture the visible content of a specified tmux pane.

#### Scenario: Capture pane content
- **WHEN** the system requests content from a valid pane
- **THEN** it returns the current visible text in that pane

#### Scenario: Capture from invalid pane
- **WHEN** the system requests content from a non-existent pane
- **THEN** it raises an appropriate error

### Requirement: Change detection
The system SHALL detect when pane content has changed since the last capture.

#### Scenario: Content changed
- **WHEN** the pane content differs from the previous capture
- **THEN** the system identifies the new/changed content

#### Scenario: Content unchanged
- **WHEN** the pane content is identical to the previous capture
- **THEN** the system reports no changes

### Requirement: Input injection
The system SHALL send text input to a specified tmux pane.

#### Scenario: Send text to pane
- **WHEN** the system sends text to a valid pane
- **THEN** the text appears in the pane as if typed by user

#### Scenario: Send text with Enter key
- **WHEN** the system sends text with newline flag
- **THEN** the text is followed by Enter key press

#### Scenario: Send to invalid pane
- **WHEN** the system attempts to send text to a non-existent pane
- **THEN** it raises an appropriate error

### Requirement: Polling mechanism
The system SHALL poll pane content at configurable intervals.

#### Scenario: Polling at default interval
- **WHEN** polling is started without custom interval
- **THEN** the system polls every 1 second

#### Scenario: Polling at custom interval
- **WHEN** polling is started with interval of N seconds
- **THEN** the system polls every N seconds

#### Scenario: Stop polling
- **WHEN** polling is stopped
- **THEN** no further captures are performed until restarted
