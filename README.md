# Gruyère 🧀

A tiny, beautiful TUI program for viewing and killing processes listening on ports.

![Gruyere Screenshot](gruyere.gif)

## Implementations

This repository contains two implementations of Gruyere:

### Python Version (`gruyere-py/`)

The Python implementation with a rich, colorful TUI.

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
gruyere
```

See [gruyere-py/README.md](gruyere-py/README.md) for more details.

### Go Version (`go/`)

The Go implementation (legacy).

**Build:**
```bash
cd go
go build -o gruyere
```

**Usage:**
```bash
./gruyere
```

## Features

- 🎨 Beautiful gradient UI with rich colors
- 🔍 Filter processes by command name
- ⌨️ Vim-style navigation (j/k) or arrow keys
- 💀 Kill processes with confirmation dialog
- 📄 Pagination for many processes

## Requirements

- macOS or Linux (uses `lsof`)

## License

MIT
