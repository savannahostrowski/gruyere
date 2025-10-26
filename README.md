# Gruyère 🧀

A tiny, beautiful TUI program for viewing and killing processes listening on ports.

![Gruyère Screenshot](gruyere.gif)

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

## Features

- 🎨 Beautiful gradient UI with rich colors
- 🔍 Filter processes by command name
- ⌨️ Vim-style navigation (j/k) or arrow keys
- 💀 Kill processes with confirmation dialog
- 📄 Pagination for many processes

## Requirements

- macOS or Linux (uses `lsof`)

> Note: An earlier version of this TUI was written in Go. You can find the deprecated source code in `go/`.


## License

MIT
