# MiniFlow

A minimal workflow system for creatives; free and open-source.

> NOTE: This is the initial prototype of miniflow, implemented as a python script. It currently ships with the config that I use to control apple music with the transport controls of my d-command controller. I use it with V-Control Pro in midi mode.

---

## Directory Structure

```txt
miniflow/
├── pyproject.toml
├── Makefile
├── README.md
├── config/  # my config
├── deploy/  # os files
├── vendor/  # vendor files
└── src/     # miniflow code
```

---

## Prerequisites

- **Python:** `>= 3.11`
- **Package & Environment Manager:** [`uv`](https://github.com/astral-sh/uv)
- **OS:** macOS (current release target for AppleScript integration)

---

## Quick Start

### 1. Initialize Development Environment

Sync dependencies and install `miniflow` in editable mode inside a local `.venv`:

```bash
uv sync

```

### 2. Run Interactively

Run the application directly in verbose mode to inspect incoming MIDI messages and triggers:

```bash
uv run miniflow -v --config config/macos/dcommand-applemusic.toml

```

### 3. Install CLI Tool & Background Service

Install `miniflow` system-wide as a local CLI tool and register/start the background daemon via `launchd`:

```bash
make install

```

> **Note:** To install a custom configuration preset during setup, specify the `CONFIG` variable:
>
> ```bash
> make install CONFIG=config/macos/your_custom_config.toml
>
> ```

---

## Configuration

Configurations are written in TOML and located in `~/.config/miniflow/config.toml` after installation.

### Example Configuration (`config/macos/dcommand_applemusic.toml`)

```toml
port_name = "V-Control Midi Mode"

[controls."dcommand/main/transport/play"]
label = "Play / Pause"
description = "Toggles playback in Apple Music"
type = "cc"
cc = 21
channel = 3
mode = "toggle"
triggers = [
    { type = "applescript", command = 'tell application "Music" to playpause' }
]

[controls."dcommand/main/transport/stop"]
label = "Stop"
description = "Pauses playback and resets Play LED"
type = "cc"
cc = 22
channel = 3
mode = "momentary"
triggers = [
    { type = "applescript", command = 'tell application "Music" to pause' },
    { type = "set_toggle", target = "dcommand/main/transport/play", state = false }
]

```

---

## Service Management

### View Logs

Logs are written to the default runtime directory:

```bash
# Standard Output
tail -f ~/.local/etc/miniflow/stdout.log

# Standard Error
tail -f ~/.local/etc/miniflow/stderr.log

```

### Uninstall Service & Binary

To stop the daemon, remove the LaunchAgent plist, and uninstall the `miniflow` executable:

```bash
make uninstall

```

---

## License

Released under the [MIT License](./LICENSE).
