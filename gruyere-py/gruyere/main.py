from dataclasses import dataclass
import signal
import subprocess
import sys
from typing import List, Optional

from readchar import readkey, key
from rich.color import Color
from rich.console import Console, Group
from rich.live import Live
from rich.style import Style
from rich.panel import Panel
from rich.text import Text
from rich import box


@dataclass
class Process:
    pid: int
    port: int | str
    user: str
    command: str


SELECTED_COLOR = Style(color="#EE6FF8", bold=True)

signal.signal(signal.SIGINT, lambda _, __: sys.exit(0))


def _clear_screen():
    """Clear the entire screen and scroll buffer using ANSI escape codes."""
    sys.stdout.write("\033[2J\033[3J\033[H")
    sys.stdout.flush()


def _parse_port(port_str: str) -> int | str:
    try:
        return int(port_str)
    except (ValueError, IndexError):
        return port_str


def _get_processes() -> list[Process]:
    raw_processes = subprocess.run(
        ["lsof", "-i", "-P", "-n", "-sTCP:LISTEN"], capture_output=True, text=True
    )
    processes: list[Process] = []

    for line in raw_processes.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 9:
            pid = int(parts[1])
            user = parts[2]
            command = parts[0]
            port = _parse_port(parts[8].split(":")[-1])
            process = Process(pid=pid, port=port, user=user, command=command)
            processes.append(process)

    return processes


def _kill_process(pid: int):
    subprocess.run(["kill", "-9", str(pid)])


def _show_pagination_indicator(total: int, selected: int, panels: list[Panel | str]):
    """Add pagination indicator dots to the panels list if needed."""
    if total <= len(panels):
        return

    page = selected // len(panels) % 4
    indicator = ""
    for i in range((total + len(panels) - 1) // len(panels)):
        if i == page:
            indicator += "● "
        else:
            indicator += "○ "

    panels.append(f"  [dim]{indicator}[/dim]")


def _render_processes_table(processes: List[Process], selected: int):
    max_display = 4

    if len(processes) <= max_display:
        display_processes = processes
        display_selected = selected
    else:
        if selected < max_display // 2:
            display_processes = processes[:max_display]
            display_selected = selected
        elif selected >= len(processes) - max_display // 2:
            display_processes = processes[-max_display:]
            display_selected = selected - (len(processes) - max_display)
        else:
            start = selected - max_display // 2
            display_processes = processes[start : start + max_display]
            display_selected = max_display // 2

    panels: list[Panel | str] = []
    for i, process in enumerate(display_processes):
        # Add vertical indicator for selected item
        indicator = "▐ " if i == display_selected else "  "

        port_line = f"{indicator}[bold]Port: {process.port} (PID: {process.pid})[/bold]"
        user_line = (
            f"{indicator}[dim]User: {process.user}, Command: {process.command}[/dim]"
        )
        content = f"{port_line}\n{user_line}"

        # All items get a panel with no border
        panel = Panel(
            content,
            style=SELECTED_COLOR if i == display_selected else "",
            box=box.SIMPLE,
        )
        panels.append(panel)

    # Add empty panels to always show 4 slots
    while len(panels) < max_display:
        empty_panel = Panel("\n", box=box.SIMPLE, style="")
        panels.append(empty_panel)

    _show_pagination_indicator(len(processes), selected, panels)

    help_text = "[bold dim]Commands: ↑/k: Up | ↓/j: Down | ENTER: Kill | /: Filter | q: Quit [/bold dim]"
    return Group(*panels, Panel(help_text, box=box.SIMPLE))


def _colorGrid(x_steps: int, y_steps: int) -> List[List[Style]]:
    """
    Generate a 2D grid of gradient colors using bilinear interpolation.
    Via https://github.com/charmbracelet/lipgloss/blob/776c15f0da16d2b1058a079ec6a08a2e1170d721/examples/layout/main.go#L338
    """
    x0y0 = Color.parse("#EE6FF8")
    x1y0 = Color.parse("#EDFF82")
    x0y1 = Color.parse("#643AFF")
    x1y1 = Color.parse("#14F9D5")

    # Get RGB triplets
    x0y0_rgb = x0y0.get_truecolor()
    x1y0_rgb = x1y0.get_truecolor()
    x0y1_rgb = x0y1.get_truecolor()
    x1y1_rgb = x1y1.get_truecolor()

    grid: List[List[Style]] = []
    for y in range(y_steps):
        row: List[Style] = []
        for x in range(x_steps):
            rx = x / (x_steps - 1) if x_steps > 1 else 0
            ry = y / (y_steps - 1) if y_steps > 1 else 0

            r = int(
                (1 - rx) * (1 - ry) * x0y0_rgb.red
                + rx * (1 - ry) * x1y0_rgb.red
                + (1 - rx) * ry * x0y1_rgb.red
                + rx * ry * x1y1_rgb.red
            )
            g = int(
                (1 - rx) * (1 - ry) * x0y0_rgb.green
                + rx * (1 - ry) * x1y0_rgb.green
                + (1 - rx) * ry * x0y1_rgb.green
                + rx * ry * x1y1_rgb.green
            )
            b = int(
                (1 - rx) * (1 - ry) * x0y0_rgb.blue
                + rx * (1 - ry) * x1y0_rgb.blue
                + (1 - rx) * ry * x0y1_rgb.blue
                + rx * ry * x1y1_rgb.blue
            )

            row.append(Style(color=Color.from_rgb(r, g, b)))
        grid.append(row)

    return grid


def _render_title():
    colors = _colorGrid(1, 5)
    title = "Gruyere"

    desc = "A tiny program for viewing + killing ports"
    divider = "─" * len(desc)
    subtext = "Here's what's running..."

    base_spacing = "                "  # Space between title and description
    desc_start_col = len(title) + len(base_spacing)  # Column where description starts

    # Create layered text effect with white text on colored backgrounds
    text = Text()

    right_texts: List[Optional[str]] = [desc, divider, subtext, None, None]

    for i in range(5):
        indent = " " * (i * 2)
        text.append(indent)
        text.append(title, style=Style(color="white", bgcolor=colors[i][0].color))

        right_text = right_texts[i]
        if right_text is not None:
            text.append(" " * (desc_start_col - len(indent) - len(title)))
            text.append(right_text, style=Style(dim=True))

        text.append("\n")

    return text


def _show_confirmation_view(console: Console, process: Process, title: Text) -> bool:
    # Screen should already be cleared before calling this function
    console.print(Panel(title, box=box.SIMPLE))
    console.print(
        Panel(
            f"[bold]Are you sure you want to kill the process?[/bold]\n\n"
            f"[bold]PID:[/bold] {process.pid}\n"
            f"[bold]Port:[/bold] {process.port}\n"
            f"[bold]User:[/bold] {process.user}\n"
            f"[bold]Command:[/bold] {process.command}\n\n"
            f"[dim]Press Y to confirm, N to cancel.[/dim]",
            border_style="#EE6FF8",
            expand=False,
        )
    )
    while True:
        ch = readkey()
        if ch.lower() == "y":
            return True
        elif ch.lower() == "n":
            return False


def main():
    console = Console()
    text = _render_title()
    processes = _get_processes()
    selected = 0
    filter_text = ""
    is_filtering = False
    running = True

    console.clear()
    console.print(Panel(text, box=box.SIMPLE))

    while running:
        process_to_kill = None

        with Live(
            _render_processes_table(processes, selected),
            console=console,
            refresh_per_second=10,
        ) as live:
            while ch := readkey():
                if is_filtering:
                    if ch == "/":
                        is_filtering = False
                        filter_text = ""
                        processes = _get_processes()
                        live.update(_render_processes_table(processes, selected))
                        continue
                    elif ch == key.UP or ch == "k":
                        selected = max(0, selected - 1)
                    elif ch == key.DOWN or ch == "j":
                        selected = min(len(processes) - 1, selected + 1)
                    elif ch == key.BACKSPACE:
                        filter_text = filter_text[:-1]
                        processes = [
                            p
                            for p in _get_processes()
                            if filter_text.lower() in p.command.lower()
                        ]
                        selected = 0
                    elif ch == key.ENTER:
                        is_filtering = False
                        process_to_kill = processes[selected] if processes else None
                        break
                    elif len(ch) == 1 and ch.isprintable():
                        filter_text += ch
                        processes = [
                            p
                            for p in _get_processes()
                            if filter_text.lower() in p.command.lower()
                        ]
                        selected = 0

                    filter_panel = Panel(
                        f"[bold magenta]Filter:[/bold magenta] {filter_text}[blink]_[/blink]",
                        title="Press / to cancel, ENTER to apply",
                        border_style="magenta",
                    )
                    display = Group(
                        filter_panel, _render_processes_table(processes, selected)
                    )
                    live.update(display)
                else:
                    if ch == key.UP or ch == "k":
                        selected = max(0, selected - 1)
                    elif ch == key.DOWN or ch == "j":
                        selected = min(len(processes) - 1, selected + 1)
                    elif ch == "/":
                        is_filtering = True
                        filter_text = ""
                        filter_panel = Panel(
                            f"[bold magenta]Filter:[/bold magenta] {filter_text}[blink]_[/blink]",
                            title="Press / to cancel, ENTER to apply",
                            border_style="magenta",
                        )
                        display = Group(
                            filter_panel, _render_processes_table(processes, selected)
                        )
                        live.update(display)
                        continue  # Skip the update at the end of the loop
                    elif ch == "q":
                        running = False
                        break
                    elif ch == key.ENTER:
                        # Exit live context to show confirmation view
                        process_to_kill = processes[selected]
                        break
                    live.update(_render_processes_table(processes, selected))

        if process_to_kill is not None:
            _clear_screen()

        if running and process_to_kill is not None:
            if _show_confirmation_view(console, process_to_kill, text):
                _kill_process(process_to_kill.pid)
                processes = _get_processes()
                selected = min(selected, len(processes) - 1)

            _clear_screen()
            console.print(Panel(text, box=box.SIMPLE))
