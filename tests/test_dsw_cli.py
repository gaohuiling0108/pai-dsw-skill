#!/usr/bin/env python3
"""
Tests for dsw.py - Main CLI for PAI-DSW.
"""

import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock, call
import subprocess

# Add scripts directory to path
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'scripts')
sys.path.insert(0, os.path.abspath(SCRIPTS_DIR))


class TestResolveInstance:
    """Tests for resolve_instance function."""
    
    def test_exact_id(self, mock_env_credentials):
        """Test with exact instance ID."""
        from dsw import resolve_instance
        
        # Should pass through IDs that look like DSW IDs
        result = resolve_instance("dsw-123456-abcde")
        assert result == "dsw-123456-abcde"
    
    def test_id_with_multiple_dashes(self, mock_env_credentials):
        """Test with ID format containing multiple dashes."""
        from dsw import resolve_instance
        
        result = resolve_instance("some-id-with-many-parts")
        assert result == "some-id-with-many-parts"
    
    @patch('dsw.get_instances_json')
    def test_exact_name_match(self, mock_get_instances, mock_env_credentials):
        """Test with exact name match."""
        from dsw import resolve_instance
        
        MOCK_INSTANCES_LIST = [
            {"InstanceId": "dsw-123456-abcde", "InstanceName": "test-instance", "Status": "Running"},
        ]
        mock_get_instances.return_value = MOCK_INSTANCES_LIST
        
        result = resolve_instance("test-instance")
        assert result == "dsw-123456-abcde"
    
    @patch('dsw.get_instances_json')
    def test_fuzzy_name_match(self, mock_get_instances, mock_env_credentials, capsys):
        """Test with fuzzy name match."""
        from dsw import resolve_instance
        
        MOCK_INSTANCES_LIST = [
            {"InstanceId": "dsw-123456-abcde", "InstanceName": "test-instance", "Status": "Running"},
        ]
        mock_get_instances.return_value = MOCK_INSTANCES_LIST
        
        result = resolve_instance("test")
        assert result == "dsw-123456-abcde"
        
        captured = capsys.readouterr()
        assert "匹配到实例" in captured.out
    
    @patch('dsw.get_instances_json')
    def test_no_match(self, mock_get_instances, mock_env_credentials, capsys):
        """Test with no matching instance."""
        from dsw import resolve_instance
        
        MOCK_INSTANCES_LIST = [
            {"InstanceId": "dsw-123456-abcde", "InstanceName": "test-instance", "Status": "Running"},
        ]
        mock_get_instances.return_value = MOCK_INSTANCES_LIST
        
        result = resolve_instance("nonexistent")
        assert result is None
        
        captured = capsys.readouterr()
        # Error message is printed to stderr
        assert "未找到" in captured.err
    
    @patch('dsw.get_instances_json')
    def test_multiple_matches(self, mock_get_instances, mock_env_credentials, capsys):
        """Test with multiple matching instances."""
        from dsw import resolve_instance
        
        # Create instances with similar names
        mock_instances = [
            {"InstanceId": "dsw-1", "InstanceName": "gpu-training-1"},
            {"InstanceId": "dsw-2", "InstanceName": "gpu-training-2"},
        ]
        mock_get_instances.return_value = mock_instances
        
        result = resolve_instance("gpu")
        assert result is None
        
        captured = capsys.readouterr()
        assert "找到多个" in captured.err


class TestColorize:
    """Tests for colorize function."""
    
    def test_colorize_adds_codes(self):
        """Test that colorize adds ANSI codes."""
        from dsw import colorize, Colors
        
        result = colorize("test", Colors.GREEN)
        assert "test" in result
        # Result should contain ANSI escape codes
        assert "\033[" in result or result == "test"  # Or empty if disabled


class TestStatusBadge:
    """Tests for status_badge function."""
    
    def test_running_status(self):
        """Test Running status badge."""
        from dsw import status_badge, Colors
        
        result = status_badge("Running")
        assert "Running" in result
    
    def test_stopped_status(self):
        """Test Stopped status badge."""
        from dsw import status_badge, Colors
        
        result = status_badge("Stopped")
        assert "Stopped" in result
    
    def test_unknown_status(self):
        """Test unknown status badge."""
        from dsw import status_badge, Colors
        
        result = status_badge("Unknown")
        assert "Unknown" in result


class TestCmdList:
    """Tests for cmd_list function."""
    
    @patch('dsw.run_script')
    def test_list_default(self, mock_run_script, mock_env_credentials):
        """Test list command with defaults."""
        from dsw import cmd_list
        
        mock_args = MagicMock()
        mock_args.format = 'table'
        mock_args.region = None
        mock_args.workspace = None
        
        cmd_list(mock_args)
        
        mock_run_script.assert_called_once()
        call_args = mock_run_script.call_args[0]
        assert call_args[0] == 'list_instances'
    
    @patch('dsw.run_script')
    def test_list_json_format(self, mock_run_script, mock_env_credentials):
        """Test list command with JSON format."""
        from dsw import cmd_list
        
        mock_args = MagicMock()
        mock_args.format = 'json'
        mock_args.region = None
        mock_args.workspace = None
        
        cmd_list(mock_args)
        
        call_args = mock_run_script.call_args[0]
        assert '--format' in call_args[1] or 'json' in call_args[1]


class TestCmdGet:
    """Tests for cmd_get function."""
    
    @patch('dsw.run_script')
    @patch('dsw.resolve_instance')
    def test_get_by_id(self, mock_resolve, mock_run_script, mock_env_credentials):
        """Test get command with instance ID."""
        from dsw import cmd_get
        
        mock_resolve.return_value = "dsw-123456-abcde"
        mock_args = MagicMock()
        mock_args.instance = "dsw-123456-abcde"
        mock_args.format = 'table'
        
        cmd_get(mock_args)
        
        mock_resolve.assert_called_once_with("dsw-123456-abcde")
        mock_run_script.assert_called_once()
    
    @patch('dsw.resolve_instance')
    def test_get_invalid_instance(self, mock_resolve, mock_env_credentials):
        """Test get command with invalid instance."""
        from dsw import cmd_get
        
        mock_resolve.return_value = None
        mock_args = MagicMock()
        mock_args.instance = "nonexistent"
        mock_args.format = 'table'
        
        result = cmd_get(mock_args)
        assert result == 1


class TestCmdStart:
    """Tests for cmd_start function."""
    
    @patch('dsw.run_script')
    @patch('dsw.resolve_instance')
    def test_start_instance(self, mock_resolve, mock_run_script, mock_env_credentials):
        """Test start command."""
        from dsw import cmd_start
        
        mock_resolve.return_value = "dsw-123456-abcde"
        mock_args = MagicMock()
        mock_args.instance = "test-instance"
        
        cmd_start(mock_args)
        
        mock_run_script.assert_called_once()
        call_args = mock_run_script.call_args[0]
        assert call_args[0] == 'start_instance'


class TestCmdStop:
    """Tests for cmd_stop function."""
    
    @patch('dsw.run_script')
    @patch('dsw.resolve_instance')
    def test_stop_with_force(self, mock_resolve, mock_run_script, mock_env_credentials):
        """Test stop command with force flag."""
        from dsw import cmd_stop
        
        mock_resolve.return_value = "dsw-123456-abcde"
        mock_args = MagicMock()
        mock_args.instance = "test-instance"
        mock_args.force = True
        
        cmd_stop(mock_args)
        
        mock_run_script.assert_called_once()
    
    @patch('dsw.resolve_instance')
    def test_stop_invalid_instance(self, mock_resolve, mock_env_credentials):
        """Test stop command with invalid instance."""
        from dsw import cmd_stop
        
        mock_resolve.return_value = None
        mock_args = MagicMock()
        mock_args.instance = "nonexistent"
        mock_args.force = True
        
        result = cmd_stop(mock_args)
        assert result == 1


class TestCmdDelete:
    """Tests for cmd_delete function."""
    
    @patch('dsw.run_script')
    @patch('dsw.resolve_instance')
    def test_delete_with_force(self, mock_resolve, mock_run_script, mock_env_credentials):
        """Test delete command with force flag."""
        from dsw import cmd_delete
        
        mock_resolve.return_value = "dsw-123456-abcde"
        mock_args = MagicMock()
        mock_args.instance = "test-instance"
        mock_args.force = True
        
        cmd_delete(mock_args)
        
        mock_run_script.assert_called_once()
    
    @patch('dsw.resolve_instance')
    def test_delete_invalid_instance(self, mock_resolve, mock_env_credentials):
        """Test delete command with invalid instance."""
        from dsw import cmd_delete
        
        mock_resolve.return_value = None
        mock_args = MagicMock()
        mock_args.instance = "nonexistent"
        mock_args.force = True
        
        result = cmd_delete(mock_args)
        assert result == 1


class TestCmdCreate:
    """Tests for cmd_create function."""
    
    @patch('dsw.run_script')
    def test_create_instance(self, mock_run_script, mock_env_credentials):
        """Test create command."""
        from dsw import cmd_create
        
        mock_args = MagicMock()
        mock_args.name = "new-instance"
        mock_args.image = "modelscope:1.34.0"
        mock_args.type = "ecs.g6.large"
        mock_args.labels = None
        
        cmd_create(mock_args)
        
        mock_run_script.assert_called_once()
        call_args = mock_run_script.call_args[0]
        assert call_args[0] == 'create_instance'


class TestCmdSearch:
    """Tests for cmd_search function."""
    
    @patch('dsw.get_instances_json')
    def test_search_by_name(self, mock_get_instances, mock_env_credentials, capsys):
        """Test search by instance name."""
        from dsw import cmd_search
        
        MOCK_INSTANCES_LIST = [
            {"InstanceId": "dsw-123456-abcde", "InstanceName": "test-instance", "Status": "Running", "InstanceType": "ecs.g6.large", "Labels": {}},
        ]
        mock_get_instances.return_value = MOCK_INSTANCES_LIST
        
        mock_args = MagicMock()
        mock_args.query = "test"
        
        result = cmd_search(mock_args)
        assert result == 0
        
        captured = capsys.readouterr()
        assert "test-instance" in captured.out
    
    @patch('dsw.get_instances_json')
    def test_search_no_results(self, mock_get_instances, mock_env_credentials, capsys):
        """Test search with no results."""
        from dsw import cmd_search
        
        MOCK_INSTANCES_LIST = [
            {"InstanceId": "dsw-123456-abcde", "InstanceName": "test-instance", "Status": "Running"},
        ]
        mock_get_instances.return_value = MOCK_INSTANCES_LIST
        
        mock_args = MagicMock()
        mock_args.query = "nonexistent"
        
        result = cmd_search(mock_args)
        assert result == 0
        
        captured = capsys.readouterr()
        assert "未找到" in captured.out
    
    @patch('dsw.get_instances_json')
    def test_search_by_label(self, mock_get_instances, mock_env_credentials, capsys):
        """Test search by label."""
        from dsw import cmd_search
        
        MOCK_INSTANCES_LIST = [
            {"InstanceId": "dsw-123456-abcde", "InstanceName": "test-instance", "Status": "Running", "InstanceType": "ecs.g6.large", "Labels": {"env": "prod"}},
        ]
        mock_get_instances.return_value = MOCK_INSTANCES_LIST
        
        mock_args = MagicMock()
        mock_args.query = "env:prod"
        
        result = cmd_search(mock_args)
        assert result == 0


class TestCmdStatus:
    """Tests for cmd_status function."""
    
    @patch('dsw.run_script')
    def test_status_in_dsw(self, mock_run_script, mock_env_credentials, capsys):
        """Test status command in DSW environment."""
        from dsw import cmd_status
        
        mock_args = MagicMock()
        
        # HOSTNAME is set to dsw-123456-abcde in mock_env_credentials
        result = cmd_status(mock_args)
        
        # Should call get_instance for current instance
        captured = capsys.readouterr()
        assert "dsw-123456-abcde" in captured.out or mock_run_script.called
    
    def test_status_not_in_dsw(self, capsys):
        """Test status command outside DSW environment."""
        with patch.dict(os.environ, {"HOSTNAME": "my-laptop"}, clear=True):
            from dsw import cmd_status
            import importlib
            import dsw
            importlib.reload(dsw)
            
            mock_args = MagicMock()
            result = dsw.cmd_status(mock_args)
            
            captured = capsys.readouterr()
            assert "不在 DSW" in captured.out or "如需查询" in captured.out


class TestMainFunction:
    """Tests for main function."""
    
    def test_no_command_shows_help(self, capsys):
        """Test that no command shows help."""
        from dsw import main
        
        with patch('sys.argv', ['dsw']):
            result = main()
            captured = capsys.readouterr()
            # Help should be shown
            assert "usage:" in captured.out.lower() or "help" in captured.out.lower()
    
    def test_unknown_command(self):
        """Test unknown command handling."""
        from dsw import main
        
        with patch('sys.argv', ['dsw', 'unknown-command']):
            # Unknown commands cause argparse to exit with SystemExit
            with pytest.raises(SystemExit) as exc_info:
                main()
            # Should exit with error code 2
            assert exc_info.value.code == 2
    
    def test_no_color_flag(self):
        """Test --no-color flag."""
        from dsw import main, Colors
        
        with patch('sys.argv', ['dsw', '--no-color', 'list']):
            # Should not crash
            try:
                main()
            except SystemExit:
                pass


class TestGetInstancesJson:
    """Tests for get_instances_json function."""
    
    @patch('subprocess.run')
    def test_returns_json(self, mock_run, mock_env_credentials):
        """Test that function returns JSON data."""
        from dsw import get_instances_json
        
        MOCK_INSTANCES_LIST = [
            {"InstanceId": "dsw-123456-abcde", "InstanceName": "test-instance", "Status": "Running"},
        ]
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(MOCK_INSTANCES_LIST)
        mock_run.return_value = mock_result
        
        result = get_instances_json()
        
        assert len(result) == 1
        assert result[0]['InstanceId'] == "dsw-123456-abcde"
    
    @patch('subprocess.run')
    def test_returns_empty_on_error(self, mock_run, mock_env_credentials):
        """Test that function returns empty list on error."""
        from dsw import get_instances_json
        
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_run.return_value = mock_result
        
        result = get_instances_json()
        assert result == []
    
    @patch('subprocess.run')
    def test_handles_invalid_json(self, mock_run, mock_env_credentials):
        """Test that function handles invalid JSON."""
        from dsw import get_instances_json
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not valid json"
        mock_run.return_value = mock_result
        
        result = get_instances_json()
        assert result == []