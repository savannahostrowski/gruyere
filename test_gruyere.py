import sys

import pytest

from gruyere.main import Process, extract_app_name, get_processes, parse_port


def test_parse_port_with_integer():
    """Test parsing a valid integer port."""
    assert parse_port("8000") == 8000
    assert parse_port("80") == 80
    assert parse_port("3000") == 3000


def test_parse_port_with_string():
    """Test parsing non-integer port strings."""
    assert parse_port("*:8000") == "*:8000"
    assert parse_port("invalid") == "invalid"
    assert parse_port("") == ""


def test_get_processes_returns_list():
    """Test that get_processes returns a list of Process objects."""
    processes = get_processes()
    assert isinstance(processes, list)

    # If there are any processes, verify they're Process objects
    if processes:
        assert isinstance(processes[0], Process)
        assert hasattr(processes[0], "pid")
        assert hasattr(processes[0], "port")
        assert hasattr(processes[0], "user")
        assert hasattr(processes[0], "command")
        assert hasattr(processes[0], "name")


def test_port_filtering():
    """Test that port filtering works correctly."""
    # Create mock processes
    mock_processes = [
        Process(pid=1234, port=8000, user="savannah", command="python3", name="python3"),
        Process(pid=5678, port=3000, user="savannah", command="node", name="node"),
        Process(pid=9012, port=8000, user="root", command="nginx", name="nginx"),
    ]

    # Filter by port 8000
    filtered = [p for p in mock_processes if p.port == 8000]
    assert len(filtered) == 2
    assert all(p.port == 8000 for p in filtered)


def test_user_filtering():
    """Test that user filtering works correctly."""
    # Create mock processes
    mock_processes = [
        Process(pid=1234, port=8000, user="savannah", command="python3", name="python3"),
        Process(pid=5678, port=3000, user="savannah", command="node", name="node"),
        Process(pid=9012, port=8000, user="root", command="nginx", name="nginx"),
    ]

    # Filter by user "savannah"
    filtered = [p for p in mock_processes if p.user == "savannah"]
    assert len(filtered) == 2
    assert all(p.user == "savannah" for p in filtered)


def test_combined_filtering():
    """Test filtering by both port and user."""
    # Create mock processes
    mock_processes = [
        Process(pid=1234, port=8000, user="savannah", command="python3", name="python3"),
        Process(pid=5678, port=3000, user="savannah", command="node", name="node"),
        Process(pid=9012, port=8000, user="root", command="nginx", name="nginx"),
    ]

    # Filter by port 8000 AND user "savannah"
    port_filter = 8000
    user_filter = "savannah"
    filtered = [
        p for p in mock_processes if p.port == port_filter and p.user == user_filter
    ]
    assert len(filtered) == 1
    assert filtered[0].pid == 1234

@pytest.mark.skipif(sys.platform != "darwin", reason="macOS-specific test")
def test_extract_app_name_from_macos_app():
    """Test extracting app names from macOS .app bundles."""
    # Test Visual Studio Code
    cmd = "/Applications/Visual Studio Code.app/Contents/Frameworks/Code Helper (Plugin).app/Contents/MacOS/Code Helper (Plugin)"
    assert extract_app_name(cmd) == "Visual Studio Code"

    # Test Discord
    cmd = "/Applications/Discord.app/Contents/Frameworks/Discord Helper (Renderer).app/Contents/MacOS/Discord Helper (Renderer)"
    assert extract_app_name(cmd) == "Discord"

    # Test app with spaces
    cmd = "/Applications/Elgato Camera Hub.app/Contents/MacOS/Camera Hub --background"
    assert extract_app_name(cmd) == "Elgato Camera Hub"

@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_extract_app_name_from_windows_executable():
    """Test extracting names from Windows executables."""
    # Test Visual Studio Code
    cmd = r"C:\Program Files\Microsoft VS Code\Code.exe --disable-extensions"
    assert extract_app_name(cmd) == "Code"

    # Test Google Chrome
    cmd = r"C:\Program Files\Google\Chrome\Application\chrome.exe --profile-directory=Default"
    assert extract_app_name(cmd) == "chrome"

    # Test app with spaces
    cmd = r"C:\Program Files\Some App\app.exe /arg1 /arg2"
    assert extract_app_name(cmd) == "app"


def test_extract_app_name_from_regular_executable():
    """Test extracting names from regular executables."""
    # Test system executable
    assert extract_app_name("/usr/libexec/rapportd") == "rapportd"

    # Test with arguments
    assert extract_app_name("python3 -m http.server 8000") == "python3"

    # Test with full path
    assert extract_app_name("/usr/bin/node server.js") == "node"


def test_extract_app_name_edge_cases():
    """Test edge cases for app name extraction."""
    # Test empty string
    assert extract_app_name("") == ""

    # Test N/A
    assert extract_app_name("N/A") == "N/A"

    # Test single executable name
    assert extract_app_name("nginx") == "nginx"


def test_process_has_clean_name():
    """Test that Process objects created by get_processes have clean names."""
    processes = get_processes()

    # If there are any processes, verify they have clean names
    if processes:
        # Name should exist and be different from command (unless very simple)
        assert processes[0].name is not None
        assert isinstance(processes[0].name, str)
        # Name should be shorter than or equal to the command
        assert len(processes[0].name) <= len(processes[0].command)
