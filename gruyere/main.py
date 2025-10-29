import os
import signal
import sys
import textwrap
import threading
import time
from dataclasses import dataclass
from typing import Any, List, Optional

import psutil
import typer
from readchar import key, readkey
from rich import box
from rich.color import Color, blend_rgb
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
MAX_DISPLAY_PROCESSES = 4

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
    processes: list[Process] = []
    try:
        # Get all IPv4 and IPv6 connections
        connections: list[Any] = []
        connections.extend(psutil.net_connections(kind="inet"))
        connections.extend(psutil.net_connections(kind="inet6"))
        for conn in connections:
            # Only consider listening connections with a valid PID
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
                proc_connections: list[Any] = []
                proc_connections.extend(proc.net_connections(kind="inet"))
                proc_connections.extend(proc.net_connections(kind="inet6"))
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

    # Deduplicate processes by (pid, port) - same process can listen on IPv4 and IPv6
    seen: set[tuple[int, int | str]] = set()
    unique_processes: list[Process] = []
    for p in processes:
        key = (p.pid, p.port)
        if key not in seen:
            seen.add(key)
            unique_processes.append(p)

    # Sort processes by port number (numeric ports first, then strings)
    unique_processes.sort(key=lambda p: (isinstance(p.port, str), p.port))
    return unique_processes


def kill_process(pid: int):
    proc = psutil.Process(pid)
    proc.kill()


def _show_pagination_indicator(total: int, selected: int, panels: list[Panel | str]):
    """Add pagination indicator dots to the panels list if needed."""
    if total <= len(panels):
        return

    page = selected // MAX_DISPLAY_PROCESSES
    indicator = ""
    for i in range((total + len(panels) - 1) // len(panels)):
        if i == page:
            indicator += "● "
        else:
            indicator += "○ "

    panels.append(f"  [dim]{indicator}[/dim]")


def _render_processes_table(
    processes: List[Process],
    selected: int,
    show_details: bool = False,
    is_filtering: bool = False,
):
    if not processes:
        if is_filtering:
            no_results_panel = Panel(
                "[dim]No processes found matching your filter.\n\nPress BACKSPACE to clear filter or ENTER to exit filter mode.[/dim]",
                box=box.SIMPLE,
                style="dim",
            )
            help_text = "[bold dim]Commands: ↑/k: Up | ↓/j: Down | BACKSPACE: Clear | ENTER: Exit filter [/bold dim]"
            return Group(no_results_panel, Panel(help_text, box=box.SIMPLE))
        else:
            no_results_panel = Panel(
                "[dim]No processes found.\n\nPress BACKSPACE to clear CLI filters.[/dim]",
                box=box.SIMPLE,
                style="dim",
            )
            help_text = "[bold dim]Commands: BACKSPACE: Clear filters | /: Filter | q: Quit [/bold dim]"
            return Group(
                f"  [dim]Displaying 0 processes[/dim]",
                no_results_panel,
                Panel(help_text, box=box.SIMPLE),
            )

    if len(processes) <= MAX_DISPLAY_PROCESSES:
        display_processes = processes
        display_selected = selected
    else:
        # We need to paginate
        page = selected // MAX_DISPLAY_PROCESSES
        index = selected % MAX_DISPLAY_PROCESSES
        start = page * MAX_DISPLAY_PROCESSES
        end = start + MAX_DISPLAY_PROCESSES
        display_processes = processes[start:end]
        display_selected = index

    panels: list[Panel | str] = []
    for i, process in enumerate(display_processes):
        indicator = "▐" if i == display_selected else " "

        port_line = f"[bold]Port: {process.port} (PID: {process.pid})[/bold]"
        app_line = f"[dim]App: {process.name}, User: {process.user}[/dim]"

        if show_details:
            max_width = 100  # Account for indicator and padding
            indent = " " * 9  # Length of "Details: "

            # Use textwrap for word-aware wrapping
            wrapped_lines = textwrap.wrap(
                process.command,
                width=max_width - len(indent),
                break_long_words=True,
                break_on_hyphens=True,
            )

            wrapped_details: list[str] = []
            if wrapped_lines:
                # First line with "Details: " prefix
                wrapped_details.append(f"[dim]Details: {wrapped_lines[0]}[/dim]")
                # Subsequent lines indented
                for line in wrapped_lines[1:]:
                    wrapped_details.append(f"[dim]{indent}{line}[/dim]")
            else:
                # Empty command
                wrapped_details.append(f"[dim]Details: [/dim]")

            lines = [port_line, app_line] + wrapped_details
        else:
            # Show just clean app name and user
            lines = [port_line, app_line]

        # Add indicator to each line to span the full height
        content = "\n".join(f"{indicator} {line}" for line in lines)

        # All items get a panel with no border
        panel = Panel(
            content,
            style=SELECTED_COLOR if i == display_selected else "",
            box=box.SIMPLE,
        )
        panels.append(panel)

    # Add empty panels to always show 4 slots
    while len(panels) < MAX_DISPLAY_PROCESSES:
        empty_panel = Panel("\n", box=box.SIMPLE, style="")
        panels.append(empty_panel)

    _show_pagination_indicator(len(processes), selected, panels)

    if is_filtering:
        help_text = "[bold dim]Commands: ↑/k: Up | ↓/j: Down | BACKSPACE: Clear | ENTER: Select [/bold dim]"
    else:
        help_text = "[bold dim]Commands: ↑/k: Up | ↓/j: Down | d: Toggle details | ENTER: Kill | /: Filter | q: Quit [/bold dim]"

    process_count = len(processes)
    count_text = f"  [dim]Displaying [bold {SELECTED_COLOR}]{process_count}[/bold {SELECTED_COLOR}] process{'es' if process_count != 1 else ''}[/dim]"

    return Group(count_text, *panels, Panel(help_text, box=box.SIMPLE))


def _colorGrid(x_steps: int, y_steps: int) -> List[List[Style]]:
    """Generate a 2D grid of gradient colors using bilinear interpolation."""
    x0y0, x1y0 = (
        Color.parse("#EE6FF8").get_truecolor(),
        Color.parse("#EDFF82").get_truecolor(),
    )
    x0y1, x1y1 = (
        Color.parse("#643AFF").get_truecolor(),
        Color.parse("#14F9D5").get_truecolor(),
    )

    return [
        [
            Style(
                color=Color.from_triplet(
                    blend_rgb(
                        blend_rgb(x0y0, x1y0, x / (x_steps - 1) if x_steps > 1 else 0),
                        blend_rgb(x0y1, x1y1, x / (x_steps - 1) if x_steps > 1 else 0),
                        y / (y_steps - 1) if y_steps > 1 else 0,
                    )
                )
            )
            for x in range(x_steps)
        ]
        for y in range(y_steps)
    ]


def create_filter_panel(filter_text: str) -> Panel:
    """Create the filter input panel."""
    return Panel(
        f"[bold {SELECTED_COLOR}]Filter:[/bold {SELECTED_COLOR}] {filter_text}[blink]_[/blink]",
        title="Press BACKSPACE on empty to cancel, ENTER to apply",
        border_style=SELECTED_COLOR,
    )


def apply_filter(filter_text: str, all_processes: list[Process]) -> list[Process]:
    """Filter processes by name."""
    if not filter_text:
        return all_processes
    return [p for p in all_processes if filter_text.lower() in p.name.lower()]


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
            border_style=SELECTED_COLOR,
            expand=False,
        )
    )
    while True:
        ch = readkey()
        if ch.lower() == "y":
            return True
        elif ch.lower() == "n" or ch.lower() == "q":
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

    # Make CLI filter parameters mutable
    cli_port = port
    cli_user = user
    cli_command = command

    selected = 0
    filter_text = ""
    is_filtering = False
    running = True
    last_process_refresh = time.time()
    process_refresh_interval = 2.0

    console.clear()
    console.print(Panel(text, box=box.SIMPLE))

    def get_filtered_processes() -> list[Process]:
        """Get processes with all filters applied."""
        nonlocal cli_port, cli_user, cli_command
        all_processes = get_processes()

        if cli_port is not None:
            all_processes = [p for p in all_processes if p.port == cli_port]
        if cli_user is not None:
            all_processes = [p for p in all_processes if p.user == cli_user]
        if cli_command is not None:
            all_processes = [
                p for p in all_processes if cli_command.lower() in p.command.lower()
            ]

        # Apply interactive filter if active
        if is_filtering:
            return apply_filter(filter_text, all_processes)
        else:
            return all_processes

    # Initialize processes
    processes = get_filtered_processes()

    while running:
        process_to_kill = None

        if cli_port is not None:
            console.print(
                Panel(f"[bold]Filtering by port:[/bold] {cli_port}", box=box.SIMPLE)
            )
        if cli_user is not None:
            console.print(
                Panel(f"[bold]Filtering by user:[/bold] {cli_user}", box=box.SIMPLE)
            )

        # Background thread to refresh processes periodically
        live_ref = None  # Will be set inside the Live context

        def refresh_processes_loop():
            nonlocal processes, selected, last_process_refresh
            while running:
                time.sleep(0.1)  # Check every 100ms
                current_time = time.time()
                if current_time - last_process_refresh >= process_refresh_interval:
                    processes = get_filtered_processes()

                    # Adjust selection if it's out of bounds
                    if selected >= len(processes) and processes:
                        selected = len(processes) - 1
                    elif not processes:
                        selected = 0

                    last_process_refresh = current_time

                    # Trigger display update
                    if live_ref is not None:
                        if is_filtering:
                            live_ref.update(
                                Group(
                                    create_filter_panel(filter_text),
                                    _render_processes_table(
                                        processes, selected, details, is_filtering=True
                                    ),
                                )
                            )
                        else:
                            live_ref.update(
                                _render_processes_table(
                                    processes, selected, details, is_filtering=False
                                )
                            )

        refresh_thread = threading.Thread(target=refresh_processes_loop, daemon=True)
        refresh_thread.start()

        with Live(
            _render_processes_table(processes, selected, details),
            console=console,
            refresh_per_second=refresh_rate,
        ) as live:
            live_ref = live  # Make live accessible to the thread
            while ch := readkey():
                needs_update = False

                if ch == key.UP or ch == "k":
                    selected = max(0, selected - 1)
                    needs_update = True
                elif ch == key.DOWN or ch == "j":
                    selected = min(len(processes) - 1, selected + 1)
                    needs_update = True

                # This block handles filtering mode and its specific keys
                if is_filtering and not needs_update:
                    if ch == key.BACKSPACE:
                        if filter_text:
                            # Backspace removes a character
                            filter_text = filter_text[:-1]
                            processes = apply_filter(filter_text, get_processes())
                            selected = 0
                        else:
                            # Backspace on empty filter exits filter mode and clears CLI filters if no results
                            is_filtering = False
                            if not processes and (
                                cli_port is not None
                                or cli_user is not None
                                or cli_command is not None
                            ):
                                # No results with CLI filters - clear them and show all processes
                                cli_port = None
                                cli_user = None
                                cli_command = None
                            processes = get_filtered_processes()
                            selected = 0
                            live.update(
                                _render_processes_table(
                                    processes, selected, details, is_filtering=False
                                )
                            )
                            continue
                    elif ch == key.ENTER:
                        is_filtering = False
                        if processes:
                            # Process selected - will show confirmation
                            process_to_kill = processes[selected]
                        else:
                            # No matches - restore all processes
                            process_to_kill = None
                            processes = get_processes()
                            selected = 0
                        break
                    elif len(ch) == 1 and ch.isprintable():
                        filter_text += ch
                        processes = apply_filter(filter_text, get_processes())
                        selected = 0

                # Update display in filtering mode (after handling all filtering keys or navigation)
                if is_filtering:
                    display = Group(
                        create_filter_panel(filter_text),
                        _render_processes_table(
                            processes, selected, details, is_filtering=True
                        ),
                    )
                    live.update(display)

                # Handle normal mode
                elif not needs_update:
                    # Only handle non-navigation keys in normal mode
                    if ch == "d":
                        details = not details
                        live.update(
                            _render_processes_table(
                                processes, selected, details, is_filtering=False
                            )
                        )
                    elif ch == "/":
                        is_filtering = True
                        filter_text = ""
                        display = Group(
                            create_filter_panel(filter_text),
                            _render_processes_table(
                                processes, selected, details, is_filtering=True
                            ),
                        )
                        live.update(display)
                    elif ch == "q":
                        running = False
                        break
                    elif ch == key.ENTER:
                        # Exit live context to show confirmation view (only if processes exist)
                        if processes:
                            process_to_kill = processes[selected]
                            break
                    elif ch == key.BACKSPACE:
                        # Backspace in normal mode clears CLI filters if no results
                        if not processes and (
                            cli_port is not None
                            or cli_user is not None
                            or cli_command is not None
                        ):
                            cli_port = None
                            cli_user = None
                            cli_command = None
                            processes = get_filtered_processes()
                            selected = 0
                            live.update(
                                _render_processes_table(
                                    processes, selected, details, is_filtering=False
                                )
                            )
                    # Ignore other keys

                # Update display for navigation in normal mode
                elif needs_update:
                    live.update(
                        _render_processes_table(
                            processes, selected, details, is_filtering=False
                        )
                    )

        if running:
            if process_to_kill is not None:
                # Process was selected, show confirmation
                _clear_screen()
                if _show_confirmation_view(console, process_to_kill, text):
                    kill_process(process_to_kill.pid)
                    processes = get_processes()
                    selected = min(selected, len(processes) - 1)

                _clear_screen()
                console.print(Panel(text, box=box.SIMPLE))
            else:
                # No process selected (e.g., pressed ENTER with no matches in filter mode)
                # Just clear and redraw to get back to normal display
                _clear_screen()
                console.print(Panel(text, box=box.SIMPLE))
