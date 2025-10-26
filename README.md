# Gruyère 🧀

A tiny, beautiful TUI program for viewing and killing processes listening on ports.

![Gruyère Screenshot](https://raw.githubusercontent.com/savannahostrowski/gruyere/main/gruyere.gif)

**Install:**
```bash
uv tool install gruyere
# or
pipx install gruyere
# or
pip install gruyere
```

**Usage:**
```bash
gruyere                    # Show processes with clean app names
gruyere --details          # Show full command details
gruyere --port 8000        # Filter by specific port
gruyere --user username    # Filter by specific user
```

### Controls

- `↑`/`k`: Move up
- `↓`/`j`: Move down
- `/`: Filter processes
- `ENTER`: Kill selected process
- `q`: Quit

## Features

- 🎨 Beautiful gradient UI with rich colors
- 🔍 Filter processes by command name, port, or user
- 📱 Clean app names by default, with optional `--details` flag to show full command strings
- ⌨️ Vim-style navigation (j/k) or arrow keys
- 💀 Kill processes with confirmation dialog
- 📄 Pagination for many processes

## Requirements

- macOS, Linux, or Windows
- Python 3.13+

**Note:** On macOS, the program will run without elevated privileges but will only show processes owned by the current user. For system-wide process information, run with `sudo`. On Windows, you may need to run as Administrator to see all processes.

## License

MIT
