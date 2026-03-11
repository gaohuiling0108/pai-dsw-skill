#!/usr/bin/env python3
"""
Tests for dsw_commands/helpers.py - run_script and related helpers.
"""

import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from dsw_commands.helpers import run_script, get_instances_json, resolve_instance, SCRIPT_DIR
from exceptions import InstanceNotFoundError, InstanceAmbiguousError


class TestScriptDir:
    """Tests for SCRIPT_DIR constant."""

    def test_points_to_scripts(self):
        assert os.path.isdir(SCRIPT_DIR)
        assert SCRIPT_DIR.endswith('scripts')


class TestRunScript:
    """Tests for run_script function."""

    @patch('subprocess.run')
    def test_builds_correct_command(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        run_script('list_instances', ['--format', 'json'])

        call_args = mock_run.call_args[0][0]
        assert call_args[0] == 'python3'
        assert call_args[1].endswith('list_instances.py')
        assert '--format' in call_args
        assert 'json' in call_args

    @patch('subprocess.run')
    def test_returns_returncode(self, mock_run):
        mock_run.return_value = MagicMock(returncode=42)
        result = run_script('some_script', [])
        assert result == 42

    @patch('subprocess.run')
    def test_capture_output_returns_tuple(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout='output', stderr='err'
        )
        rc, out, err = run_script('test_script', ['arg1'], capture_output=True)
        assert rc == 0
        assert out == 'output'
        assert err == 'err'
        # Verify capture_output was passed through
        mock_run.assert_called_once()
        assert mock_run.call_args[1].get('capture_output') is True

    @patch('subprocess.run')
    def test_no_capture_output(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        result = run_script('test_script', [])
        assert isinstance(result, int)

    @patch('subprocess.run')
    def test_empty_args(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        run_script('my_script', [])
        call_args = mock_run.call_args[0][0]
        assert len(call_args) == 2  # python3 + script_path


class TestGetInstancesJson:
    """Tests for get_instances_json function."""

    @patch('subprocess.run')
    def test_success(self, mock_run):
        data = [{"InstanceId": "dsw-1", "InstanceName": "test"}]
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(data))

        result = get_instances_json()
        assert result == data

    @patch('subprocess.run')
    def test_nonzero_returncode(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout='')
        assert get_instances_json() == []

    @patch('subprocess.run')
    def test_invalid_json(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='not json')
        assert get_instances_json() == []

    @patch('subprocess.run')
    def test_empty_stdout(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='')
        assert get_instances_json() == []

    @patch('subprocess.run')
    def test_calls_list_instances_with_json(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='[]')
        get_instances_json()
        cmd = mock_run.call_args[0][0]
        assert 'list_instances.py' in cmd[1]
        assert '--format' in cmd
        assert 'json' in cmd


class TestResolveInstance:
    """Tests for resolve_instance with edge cases."""

    def test_dsw_id_passthrough(self):
        assert resolve_instance("dsw-abc-def") == "dsw-abc-def"

    def test_multi_dash_id_passthrough(self):
        assert resolve_instance("some-thing-id") == "some-thing-id"

    def test_single_word_not_passthrough(self):
        """Single word without enough dashes triggers name search."""
        with patch('dsw_commands.helpers.get_instances_json', return_value=[]):
            with pytest.raises(InstanceNotFoundError):
                resolve_instance("myname")

    @patch('dsw_commands.helpers.get_instances_json')
    def test_exact_name_match_preferred(self, mock_json):
        """Exact name match should be returned even if fuzzy matches exist."""
        mock_json.return_value = [
            {"InstanceId": "dsw-1", "InstanceName": "test"},
            {"InstanceId": "dsw-2", "InstanceName": "test-extra"},
        ]
        result = resolve_instance("test")
        assert result == "dsw-1"

    @patch('dsw_commands.helpers.get_instances_json')
    def test_case_insensitive_fuzzy(self, mock_json):
        mock_json.return_value = [
            {"InstanceId": "dsw-1", "InstanceName": "MyGPU-Instance"},
        ]
        result = resolve_instance("mygpu")
        assert result == "dsw-1"

    @patch('dsw_commands.helpers.get_instances_json')
    def test_ambiguous_raises(self, mock_json):
        mock_json.return_value = [
            {"InstanceId": "dsw-1", "InstanceName": "gpu-train-1"},
            {"InstanceId": "dsw-2", "InstanceName": "gpu-train-2"},
        ]
        with pytest.raises(InstanceAmbiguousError) as exc_info:
            resolve_instance("gpu")
        assert len(exc_info.value.details["matches"]) == 2

    @patch('dsw_commands.helpers.get_instances_json')
    def test_empty_instance_list(self, mock_json):
        mock_json.return_value = []
        with pytest.raises(InstanceNotFoundError):
            resolve_instance("anything")
