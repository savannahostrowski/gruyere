# gruyere 🧀
A tiny (and pretty) program for viewing + killing ports. 

I created this program so that I could stop trying to remember the command and all the right flags to view processes on listening ports. This program really just wraps `lsof -i -P -n -sTCP:LISTEN` to get the processes and their PIDs. You can select a process and also kill it using the TUI. The process list has filtering enabled as well (useful if you've got a lot going on; just hit `/` and search by port or PID).

It's called "gruyere" because ports reminded me of holes and gruyere is a cheese with many holes! 🧀

![](gruyere.gif)

gruyere makes use of the wonderful [Charm](https://github.com/charmbracelet) libraries:
- [Bubble Tea](https://github.com/charmbracelet/bubbletea)
- [Bubbles](https://github.com/charmbracelet/bubbles)
- [Lip Gloss](https://github.com/charmbracelet/lipgloss)
- [Log](https://github.com/charmbracelet/log)

## Installation
You can install the appropriate binary for your operating system by visiting the [Releases page](https://github.com/savannahostrowski/gruyere/releases).

## Contributing
Contributions are welcome! To get started, check out the [contributing guidelines](CONTRIBUTING.md).