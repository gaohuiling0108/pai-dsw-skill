"""
Formatting utilities for CLI output.

Provides colored terminal output helpers used by all command modules.
"""

import sys


class Colors:
    """ANSI color codes for terminal output."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'

    # Background colors
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'

    @classmethod
    def disable(cls):
        """Disable colors (for non-terminal output or --no-color flag)."""
        cls.RESET = ''
        cls.BOLD = ''
        cls.RED = ''
        cls.GREEN = ''
        cls.YELLOW = ''
        cls.BLUE = ''
        cls.MAGENTA = ''
        cls.CYAN = ''
        cls.WHITE = ''
        cls.BG_RED = ''
        cls.BG_GREEN = ''
        cls.BG_YELLOW = ''


def colorize(text: str, color: str) -> str:
    """Wrap text with ANSI color codes."""
    return f"{color}{text}{Colors.RESET}"


def print_header(title: str):
    """Print a prominent section header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*50}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.WHITE}  {title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*50}{Colors.RESET}\n")


def print_success(text: str):
    """Print a green success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text: str):
    """Print a red error message to stderr."""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}", file=sys.stderr)


def print_warning(text: str):
    """Print a yellow warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def print_info(text: str):
    """Print a blue info message."""
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")


def status_badge(status: str) -> str:
    """Return status text wrapped in the appropriate color."""
    status_colors = {
        'Running': Colors.GREEN,
        'Pending': Colors.YELLOW,
        'Starting': Colors.YELLOW,
        'Stopping': Colors.YELLOW,
        'Stopped': Colors.RED,
        'Failed': Colors.BG_RED,
        'Deleted': Colors.MAGENTA,
    }
    color = status_colors.get(status, Colors.WHITE)
    return f"{color}{status}{Colors.RESET}"
