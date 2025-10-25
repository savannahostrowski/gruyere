# Gruyere

A tiny, beautiful TUI program for viewing and killing processes listening on ports.

## Features

- Beautiful gradient UI with rich colors
- Filter processes by command name  
- Vim-style navigation (j/k) or arrow keys
- Kill processes with confirmation dialog
- Pagination for many processes

## Installation

```bash
uv tool install gruyere
```

Or with pipx:
```bash
pipx install gruyere
```

## Usage

Simply run:

```bash
gruyere
```

### Controls

- Up/k: Move up
- Down/j: Move down
- /: Filter processes
- ENTER: Kill selected process
- q: Quit

## Requirements

- Python 3.12+
- macOS or Linux (uses lsof)

## License

MIT
