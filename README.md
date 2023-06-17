# gruyere 🧀
[![All Contributors](https://img.shields.io/github/all-contributors/savannahostrowski/gruyere?color=bd93f9&style=flat-square)](#contributors)

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

## Contributors
A big thank you to these wonderful humans for their contributions!

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/bfgray3"><img src="https://avatars.githubusercontent.com/u/20310144?v=4?s=100" width="100px;" alt="bernie gray"/><br /><sub><b>bernie gray</b></sub></a><br /><a href="https://github.com/savannahostrowski/gruyere/commits?author=bfgray3" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/techygrrrl"><img src="https://avatars.githubusercontent.com/u/88961088?v=4?s=100" width="100px;" alt="techygrrrl"/><br /><sub><b>techygrrrl</b></sub></a><br /><a href="https://github.com/savannahostrowski/gruyere/commits?author=techygrrrl" title="Code">💻</a></td>
    </tr>
  </tbody>
  <tfoot>
    <tr>
      <td align="center" size="13px" colspan="7">
        <img src="https://raw.githubusercontent.com/all-contributors/all-contributors-cli/1b8533af435da9854653492b1327a23a4dbd0a10/assets/logo-small.svg">
          <a href="https://all-contributors.js.org/docs/en/bot/usage">Add your contributions</a>
        </img>
      </td>
    </tr>
  </tfoot>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->
