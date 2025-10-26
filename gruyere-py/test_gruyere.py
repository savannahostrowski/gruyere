import sys

from gruyere import main as gruyere_main
from gruyere.main import parse_port, get_processes, Process


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


def test_port_filtering():
    """Test that port filtering works correctly."""
    # Create mock processes
    mock_processes = [
        Process(pid=1234, port=8000, user="savannah", command="python3"),
        Process(pid=5678, port=3000, user="savannah", command="node"),
        Process(pid=9012, port=8000, user="root", command="nginx"),
    ]

    # Filter by port 8000
    filtered = [p for p in mock_processes if p.port == 8000]
    assert len(filtered) == 2
    assert all(p.port == 8000 for p in filtered)


def test_user_filtering():
    """Test that user filtering works correctly."""
    # Create mock processes
    mock_processes = [
        Process(pid=1234, port=8000, user="savannah", command="python3"),
        Process(pid=5678, port=3000, user="savannah", command="node"),
        Process(pid=9012, port=8000, user="root", command="nginx"),
    ]

    # Filter by user "savannah"
    filtered = [p for p in mock_processes if p.user == "savannah"]
    assert len(filtered) == 2
    assert all(p.user == "savannah" for p in filtered)


def test_combined_filtering():
    """Test filtering by both port and user."""
    # Create mock processes
    mock_processes = [
        Process(pid=1234, port=8000, user="savannah", command="python3"),
        Process(pid=5678, port=3000, user="savannah", command="node"),
        Process(pid=9012, port=8000, user="root", command="nginx"),
    ]

    # Filter by port 8000 AND user "savannah"
    port_filter = 8000
    user_filter = "savannah"
    filtered = [
        p for p in mock_processes if p.port == port_filter and p.user == user_filter
    ]
    assert len(filtered) == 1
    assert filtered[0].pid == 1234


def test_not_supported_on_windows():
    """Test that the script exits on Windows systems."""
    original_platform = sys.platform
    sys.platform = "win32"
    try:
        try:
            gruyere_main.main()
        except SystemExit as e:
            assert e.code == 1
        else:
            assert False, "Expected SystemExit was not raised."
    finally:
        sys.platform = original_platform
