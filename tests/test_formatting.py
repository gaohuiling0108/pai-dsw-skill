#!/usr/bin/env python3
"""
Tests for dsw_commands/formatting.py - Terminal output helpers.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from dsw_commands.formatting import (
    Colors,
    colorize,
    print_header,
    print_success,
    print_error,
    print_warning,
    print_info,
    status_badge,
)


# Keep a backup of original color values to restore after disable tests
_ORIGINAL_COLORS = {attr: getattr(Colors, attr) for attr in dir(Colors)
                    if attr.isupper() and not attr.startswith('_')}


def _restore_colors():
    for attr, val in _ORIGINAL_COLORS.items():
        setattr(Colors, attr, val)


class TestColors:
    """Tests for Colors class."""

    def test_has_ansi_codes(self):
        _restore_colors()  # ensure previous tests haven't disabled colors
        assert '\033[' in Colors.RESET
        assert '\033[' in Colors.GREEN
        assert '\033[' in Colors.RED

    def test_disable_clears_all(self):
        Colors.disable()
        assert Colors.RESET == ''
        assert Colors.GREEN == ''
        assert Colors.RED == ''
        assert Colors.BOLD == ''
        assert Colors.BG_RED == ''
        _restore_colors()

    def test_disable_affects_bg_colors(self):
        Colors.disable()
        assert Colors.BG_GREEN == ''
        assert Colors.BG_YELLOW == ''
        _restore_colors()


class TestColorize:
    """Tests for colorize function."""

    def test_wraps_text(self):
        result = colorize("hello", Colors.GREEN)
        assert result.startswith(Colors.GREEN)
        assert result.endswith(Colors.RESET)
        assert "hello" in result

    def test_with_disabled_colors(self):
        Colors.disable()
        result = colorize("hello", Colors.GREEN)
        assert result == "hello"
        _restore_colors()


class TestPrintHeader:
    """Tests for print_header."""

    def test_contains_title(self, capsys):
        print_header("My Title")
        out = capsys.readouterr().out
        assert "My Title" in out

    def test_contains_separator(self, capsys):
        print_header("Test")
        out = capsys.readouterr().out
        assert "=" in out


class TestPrintSuccess:
    """Tests for print_success."""

    def test_output(self, capsys):
        print_success("done")
        out = capsys.readouterr().out
        assert "done" in out
        assert "\u2713" in out  # checkmark


class TestPrintError:
    """Tests for print_error."""

    def test_goes_to_stderr(self, capsys):
        print_error("fail")
        captured = capsys.readouterr()
        assert "fail" in captured.err
        assert captured.out == ""

    def test_contains_cross(self, capsys):
        print_error("oops")
        assert "\u2717" in capsys.readouterr().err  # cross mark


class TestPrintWarning:
    """Tests for print_warning."""

    def test_output(self, capsys):
        print_warning("caution")
        out = capsys.readouterr().out
        assert "caution" in out


class TestPrintInfo:
    """Tests for print_info."""

    def test_output(self, capsys):
        print_info("note")
        out = capsys.readouterr().out
        assert "note" in out


class TestStatusBadge:
    """Tests for status_badge."""

    def test_running(self):
        badge = status_badge("Running")
        assert "Running" in badge
        assert Colors.GREEN in badge

    def test_stopped(self):
        badge = status_badge("Stopped")
        assert "Stopped" in badge
        assert Colors.RED in badge

    def test_pending(self):
        badge = status_badge("Pending")
        assert Colors.YELLOW in badge

    def test_failed(self):
        badge = status_badge("Failed")
        assert Colors.BG_RED in badge

    def test_unknown_status_uses_white(self):
        badge = status_badge("SomeOther")
        assert "SomeOther" in badge
        assert Colors.WHITE in badge

    def test_all_known_statuses(self):
        for status in ['Running', 'Pending', 'Starting', 'Stopping', 'Stopped', 'Failed', 'Deleted']:
            badge = status_badge(status)
            assert status in badge
