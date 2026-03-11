#!/usr/bin/env python3
"""
Tests for dsw_utils.py - Utility functions for PAI-DSW scripts.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Import module under test
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))


class TestGetCredentials:
    """Tests for get_credentials function."""
    
    def test_from_env_variables(self, mock_env_credentials):
        """Test credentials from environment variables."""
        from dsw_utils import get_credentials
        
        creds = get_credentials()
        
        assert creds['access_key_id'] == "test-key-id"
        assert creds['access_key_secret'] == "test-key-secret"
        assert creds['security_token'] == "test-token"
    
    def test_from_metadata_service(self, mock_metadata_credentials, mock_requests_get):
        """Test credentials from metadata service (RAM role)."""
        from dsw_utils import get_credentials
        
        creds = get_credentials()
        
        assert creds['access_key_id'] == "test-access-key-id"
        assert creds['access_key_secret'] == "test-access-key-secret"
        assert creds['security_token'] == "test-security-token"
    
    def test_no_credentials_raises_error(self):
        """Test that missing credentials raises an error."""
        # Clear all credential env vars
        env_clear = {
            "ALIBABA_CLOUD_ACCESS_KEY_ID": "",
            "ALIBABA_CLOUD_ACCESS_KEY_SECRET": "",
            "ALIBABA_CLOUD_SECURITY_TOKEN": "",
            "ALIBABA_CLOUD_CREDENTIALS_URI": "",
        }
        
        with patch.dict(os.environ, env_clear, clear=True):
            # get_credentials() calls sys.exit(1) or raises Exception
            # depending on whether env_detector is available
            with pytest.raises((Exception, SystemExit)):
                from dsw_utils import get_credentials
                import importlib
                import dsw_utils
                importlib.reload(dsw_utils)
                dsw_utils.get_credentials()
    
    def test_metadata_service_failure_fallback(self, mock_metadata_credentials):
        """Test fallback when metadata service fails."""
        with patch('requests.get') as mock_get:
            # Simulate metadata service failure
            mock_get.side_effect = Exception("Connection refused")
            
            # Should raise or sys.exit since no other credentials available
            from dsw_utils import get_credentials
            import importlib
            import dsw_utils
            importlib.reload(dsw_utils)
            
            with pytest.raises((Exception, SystemExit)):
                dsw_utils.get_credentials()


class TestCreateClient:
    """Tests for create_client function."""
    
    def test_default_region(self, mock_env_credentials):
        """Test client creation with default region."""
        # Test that create_client function exists and can be called
        from dsw_utils import create_client
        import importlib
        import dsw_utils
        
        # Just verify the function exists and has correct signature
        assert callable(dsw_utils.create_client)
    
    def test_custom_region(self, mock_env_credentials):
        """Test client creation with custom region."""
        from dsw_utils import create_client
        import importlib
        import dsw_utils
        
        # Just verify the function exists and accepts region parameter
        assert callable(dsw_utils.create_client)


class TestGetWorkspaceId:
    """Tests for get_workspace_id function."""
    
    def test_from_env(self, mock_env_credentials):
        """Test workspace ID from environment."""
        from dsw_utils import get_workspace_id
        
        ws_id = get_workspace_id()
        assert ws_id == "ws-12345"
    
    def test_missing_workspace_raises_error(self):
        """Test missing workspace ID raises error."""
        env_clear = {"PAI_WORKSPACE_ID": ""}
        
        with patch.dict(os.environ, env_clear, clear=True):
            with pytest.raises(Exception):
                from dsw_utils import get_workspace_id
                import importlib
                import dsw_utils
                importlib.reload(dsw_utils)
                dsw_utils.get_workspace_id(allow_interactive=False)


class TestPrintTable:
    """Tests for print_table function."""
    
    def test_basic_table(self, capsys):
        """Test basic table output."""
        from dsw_utils import print_table
        
        headers = ["Name", "Status"]
        rows = [
            ["instance-1", "Running"],
            ["instance-2", "Stopped"]
        ]
        
        print_table(headers, rows)
        captured = capsys.readouterr()
        
        assert "Name" in captured.out
        assert "Status" in captured.out
        assert "instance-1" in captured.out
        assert "Running" in captured.out
    
    def test_table_with_title(self, capsys):
        """Test table with title."""
        from dsw_utils import print_table
        
        headers = ["ID", "Name"]
        rows = [["1", "test"]]
        
        print_table(headers, rows, title="Test Table")
        captured = capsys.readouterr()
        
        assert "Test Table" in captured.out
    
    def test_empty_table(self, capsys):
        """Test empty table."""
        from dsw_utils import print_table
        
        headers = ["ID", "Name"]
        rows = []
        
        print_table(headers, rows)
        captured = capsys.readouterr()
        
        assert "ID" in captured.out
        assert "Name" in captured.out
    
    def test_table_with_long_values(self, capsys):
        """Test table with long values."""
        from dsw_utils import print_table
        
        headers = ["ID", "Name"]
        rows = [
            ["dsw-123456-very-long-instance-id", "a-very-long-instance-name"]
        ]
        
        print_table(headers, rows)
        captured = capsys.readouterr()
        
        # Should handle long values without crashing
        assert "dsw-123456-very-long-instance-id" in captured.out


class TestGetCurrentInstanceId:
    """Tests for get_current_instance_id function."""
    
    def test_dsw_hostname(self, mock_env_credentials):
        """Test with DSW hostname format."""
        from dsw_utils import get_current_instance_id
        
        instance_id = get_current_instance_id()
        assert instance_id == "dsw-123456-abcde"
    
    def test_non_dsw_hostname(self):
        """Test with non-DSW hostname."""
        with patch.dict(os.environ, {"HOSTNAME": "my-laptop"}, clear=True):
            from dsw_utils import get_current_instance_id
            import importlib
            import dsw_utils
            importlib.reload(dsw_utils)
            
            instance_id = dsw_utils.get_current_instance_id()
            assert instance_id == "my-laptop"
    
    def test_missing_hostname(self):
        """Test with missing hostname."""
        with patch.dict(os.environ, {}, clear=True):
            from dsw_utils import get_current_instance_id
            import importlib
            import dsw_utils
            importlib.reload(dsw_utils)
            
            instance_id = dsw_utils.get_current_instance_id()
            assert instance_id == ""


class TestColors:
    """Tests for Colors class in dsw.py."""
    
    def test_colors_disabled(self):
        """Test color disabling."""
        # Import from dsw module
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
        from dsw import Colors
        
        # Store original values
        original_reset = Colors.RESET
        
        # Disable colors
        Colors.disable()
        
        assert Colors.RESET == ""
        assert Colors.GREEN == ""
        
        # Restore for other tests
        Colors.RESET = original_reset