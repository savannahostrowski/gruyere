import os
import signal
import sys
from dataclasses import dataclass
from typing import List, Optional

import psutil
import typer
from readchar import key, readkey
from rich import box
from rich.color import Color
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.style import Style
from rich.text import Text


@dataclass
class Process:
    pid: int
    port: int | str
    user: str
    command: str
    name: str


SELECTED_COLOR = Style(color="#EE6FF8", bold=True)

signal.signal(signal.SIGINT, lambda _, __: sys.exit(0))

app = typer.Typer()


def _clear_screen():
    """Clear the entire screen and scroll buffer using ANSI escape codes."""
    sys.stdout.write("\033[2J\033[3J\033[H")
    sys.stdout.flush()


def parse_port(port_str: str) -> int | str:
    """Parse a port string into an integer if possible, otherwise return as-is."""
    try:
        return int(port_str)
    except (ValueError, IndexError):
        return port_str


def extract_app_name(command: str) -> str:
    if not command or command == "N/A":
        return command

    # Handle macOS .app bundles - extract the main app name from the full command string
    if ".app/" in command:
        first_app_end = command.find(".app/") + 4
        path_before_app = command[:first_app_end]
        app_start = path_before_app.rfind("/")
        if app_start != -1:
            app_name = path_before_app[app_start + 1 :]
            return app_name.replace(".app", "")

    # Handle Windows .exe paths - look for .exe to find the executable
    if ".exe" in command:
        exe_end = command.find(".exe") + 4
        path_before_exe = command[:exe_end]
        # Find the last backslash or forward slash
        exe_start = max(path_before_exe.rfind("\\"), path_before_exe.rfind("/"))
        if exe_start != -1:
            exe_name = path_before_exe[exe_start + 1 :]
            return exe_name.replace(".exe", "")

    # For other executables, get the first word/path component
    parts = command.split()
    if not parts:
        return command

    executable = parts[0]
    basename = os.path.basename(executable)

    # Remove common helper suffixes for cleaner names
    basename = (
        basename.replace(" (Plugin)", "")
        .replace(" (Renderer)", "")
        .replace(" (GPU)", "")
    )

    return basename


def get_processes() -> list[Process]:
    """Get a list of processes with their associated ports."""
    processes: list[Process] = []
    try:
        connections = psutil.net_connections(kind="inet")
        for conn in connections:
            if (
                conn.laddr
                and conn.status == psutil.CONN_LISTEN
                and conn.pid is not None
            ):
                pid = conn.pid
                port = parse_port(str(conn.laddr.port))
                try:
                    proc = psutil.Process(pid)
                    user = proc.username()
                    command = (
                        " ".join(proc.cmdline()) if proc.cmdline() else proc.name()
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    user = "N/A"
                    command = "N/A"

                name = extract_app_name(command)
                processes.append(
                    Process(pid=pid, port=port, user=user, command=command, name=name)
                )
    except psutil.AccessDenied:
        # On macOS, net_connections() requires elevated privileges
        # Fall back to checking each process individually
        for proc in psutil.process_iter(["pid"]):
            try:
                pid = proc.info["pid"]
                proc_connections = proc.net_connections(kind="inet")
                for conn in proc_connections:
                    if conn.laddr and conn.status == psutil.CONN_LISTEN:
                        port = parse_port(str(conn.laddr.port))
                        try:
                            user = proc.username()
                            # get last part of command line or name if empty
                            command = (
                                " ".join(proc.cmdline())
                                if proc.cmdline()
                                else proc.name()
                            )
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            user = "N/A"
                            command = "N/A"

                        name = extract_app_name(command)
                        processes.append(
                            Process(
                                pid=pid,
                                port=port,
                                user=user,
                                command=command,
                                name=name,
                            )
                        )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Skip processes we can't access
                continue

    # Sort processes by port number (numeric ports first, then strings)
    processes.sort(key=lambda p: (isinstance(p.port, str), p.port))
    return processes


def kill_process(pid: int):
    proc = psutil.Process(pid)
    proc.kill()


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


def _render_processes_table(
    processes: List[Process], selected: int, show_details: bool = False
):
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
        app_line = f"{indicator}[dim]App: {process.name}, User: {process.user}[/dim]"

        if show_details:
            # Show clean name AND full command details
            details_line = f"{indicator}[dim]Details: {process.command}[/dim]"
            content = f"{port_line}\n{app_line}\n{details_line}"
        else:
            # Show just clean app name and user
            content = f"{port_line}\n{app_line}"

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


@app.command()
def main(
    port: Optional[int] = typer.Option(
        None, "--port", "-p", help="Filter by specific port number"
    ),
    user: Optional[str] = typer.Option(
        None, "--user", "-u", help="Filter by specific user"
    ),
    command: Optional[str] = typer.Option(
        None, "--command", "-c", help="Filter by command substring"
    ),
    refresh_rate: int = typer.Option(
        10, "--refresh-rate", "-r", help="Display refresh rate per second"
    ),
    details: bool = typer.Option(
        False, "--details", "-d", help="Show full command details instead of app name"
    ),
):
    console = Console()
    text = _render_title()
    processes: list[Process] = get_processes()

    if port is not None:
        processes = [p for p in processes if p.port == port]

    if user is not None:
        processes = [p for p in processes if p.user == user]

    if command is not None:
        processes = [p for p in processes if command.lower() in p.command.lower()]

    selected = 0
    filter_text = ""
    is_filtering = False
    running = True

    console.clear()
    console.print(Panel(text, box=box.SIMPLE))

    while running:
        process_to_kill = None

        if port is not None:
            console.print(
                Panel(f"[bold]Filtering by port:[/bold] {port}", box=box.SIMPLE)
            )
        if user is not None:
            console.print(
                Panel(f"[bold]Filtering by user:[/bold] {user}", box=box.SIMPLE)
            )

        with Live(
            _render_processes_table(processes, selected, details),
            console=console,
            refresh_per_second=refresh_rate,
        ) as live:
            while ch := readkey():
                if is_filtering:
                    if ch == "/":
                        is_filtering = False
                        filter_text = ""
                        processes = get_processes()
                        live.update(
                            _render_processes_table(processes, selected, details)
                        )
                        continue
                    elif ch == key.UP or ch == "k":
                        selected = max(0, selected - 1)
                    elif ch == key.DOWN or ch == "j":
                        selected = min(len(processes) - 1, selected + 1)
                    elif ch == key.BACKSPACE:
                        filter_text = filter_text[:-1]
                        processes = [
                            p
                            for p in get_processes()
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
                            for p in get_processes()
                            if filter_text.lower() in p.command.lower()
                        ]
                        selected = 0

                    filter_panel = Panel(
                        f"[bold magenta]Filter:[/bold magenta] {filter_text}[blink]_[/blink]",
                        title="Press / to cancel, ENTER to apply",
                        border_style="magenta",
                    )
                    display = Group(
                        filter_panel,
                        _render_processes_table(processes, selected, details),
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
                            filter_panel,
                            _render_processes_table(processes, selected, details),
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
                    live.update(_render_processes_table(processes, selected, details))

        if process_to_kill is not None:
            _clear_screen()

        if running and process_to_kill is not None:
            if _show_confirmation_view(console, process_to_kill, text):
                kill_process(process_to_kill.pid)
                processes = get_processes()
                selected = min(selected, len(processes) - 1)

            _clear_screen()
            console.print(Panel(text, box=box.SIMPLE))
