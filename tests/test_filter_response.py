#!/usr/bin/env python3
"""
Tests for dsw_utils.py - filter_response, _ensure_sdk, INSTANCE_DETAIL_FIELDS.
"""

import os
import sys
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from dsw_utils import filter_response, INSTANCE_DETAIL_FIELDS


class TestFilterResponse:
    """Tests for filter_response function."""

    def test_removes_none_values(self):
        data = {"a": 1, "b": None, "c": "hello"}
        result = filter_response(data)
        assert result == {"a": 1, "c": "hello"}

    def test_keeps_falsy_non_none(self):
        """Zero, empty string, False should be kept."""
        data = {"a": 0, "b": "", "c": False, "d": None}
        result = filter_response(data)
        assert result == {"a": 0, "b": "", "c": False}

    def test_with_fields_filter(self):
        data = {"InstanceId": "dsw-1", "InstanceName": "test", "Status": "Running", "Extra": "x"}
        result = filter_response(data, fields=["InstanceId", "Status"])
        assert result == {"InstanceId": "dsw-1", "Status": "Running"}

    def test_fields_and_none_combined(self):
        """Fields filter + None removal together."""
        data = {"a": 1, "b": None, "c": 3}
        result = filter_response(data, fields=["a", "b"])
        # b is None so removed, only a remains
        assert result == {"a": 1}

    def test_list_of_dicts(self):
        data = [
            {"a": 1, "b": None},
            {"a": None, "c": 3},
        ]
        result = filter_response(data)
        assert result == [{"a": 1}, {"c": 3}]

    def test_list_with_fields(self):
        data = [
            {"a": 1, "b": 2, "c": 3},
            {"a": 10, "b": 20, "c": 30},
        ]
        result = filter_response(data, fields=["a", "c"])
        assert result == [{"a": 1, "c": 3}, {"a": 10, "c": 30}]

    def test_non_dict_passthrough(self):
        assert filter_response(42) == 42
        assert filter_response("hello") == "hello"
        assert filter_response(None) is None

    def test_empty_dict(self):
        assert filter_response({}) == {}

    def test_empty_list(self):
        assert filter_response([]) == []

    def test_all_none_dict(self):
        data = {"a": None, "b": None}
        assert filter_response(data) == {}

    def test_fields_none_keeps_all(self):
        """fields=None means keep all (but still strip None)."""
        data = {"a": 1, "b": 2, "c": None}
        result = filter_response(data, fields=None)
        assert result == {"a": 1, "b": 2}


class TestInstanceDetailFields:
    """Tests for INSTANCE_DETAIL_FIELDS mapping."""

    def test_brief_fields(self):
        fields = INSTANCE_DETAIL_FIELDS['brief']
        assert 'InstanceId' in fields
        assert 'InstanceName' in fields
        assert 'Status' in fields
        # Should NOT have extra fields
        assert 'InstanceType' not in fields
        assert 'Labels' not in fields

    def test_summary_fields(self):
        fields = INSTANCE_DETAIL_FIELDS['summary']
        # summary should be a superset of brief
        for f in ['InstanceId', 'InstanceName', 'Status']:
            assert f in fields
        # summary adds more fields
        assert 'InstanceType' in fields or 'EcsSpec' in fields
        assert 'Labels' in fields

    def test_full_is_none(self):
        """full level uses None to indicate keep-all."""
        assert INSTANCE_DETAIL_FIELDS['full'] is None

    def test_integration_brief(self):
        """filter_response + brief fields on realistic data."""
        instance = {
            "InstanceId": "dsw-123",
            "InstanceName": "test",
            "Status": "Running",
            "InstanceType": "ecs.g6.large",
            "GpuCount": 0,
            "CreateTime": "2024-01-01",
            "Labels": {"env": "prod"},
            "VpcId": None,
        }
        result = filter_response(instance, INSTANCE_DETAIL_FIELDS['brief'])
        assert set(result.keys()) == {"InstanceId", "InstanceName", "Status"}

    def test_integration_summary(self):
        instance = {
            "InstanceId": "dsw-123",
            "InstanceName": "test",
            "Status": "Running",
            "InstanceType": "ecs.g6.large",
            "Labels": {"env": "prod"},
            "VpcId": "vpc-abc",
            "SecurityGroupId": "sg-123",
        }
        result = filter_response(instance, INSTANCE_DETAIL_FIELDS['summary'])
        assert "InstanceId" in result
        assert "Labels" in result
        # Fields outside summary should be excluded
        assert "VpcId" not in result
        assert "SecurityGroupId" not in result

    def test_integration_full(self):
        instance = {
            "InstanceId": "dsw-123",
            "InstanceName": "test",
            "Status": "Running",
            "VpcId": "vpc-abc",
            "Extra": None,
        }
        result = filter_response(instance, INSTANCE_DETAIL_FIELDS['full'])
        # full=None keeps all, but still removes None
        assert "InstanceId" in result
        assert "VpcId" in result
        assert "Extra" not in result  # was None


class TestEnsureSDK:
    """Tests for _ensure_sdk function."""

    def test_no_error_when_sdk_available(self):
        """_ensure_sdk should not raise when SDK is mocked in sys.modules."""
        import dsw_utils
        # In test environment, conftest.py mocks the SDK so _SDK_AVAILABLE is True
        # _ensure_sdk should not raise
        dsw_utils._ensure_sdk()  # should not raise

    def test_raises_when_sdk_unavailable(self):
        """_ensure_sdk should raise ImportError when SDK is marked unavailable."""
        import dsw_utils
        original_available = dsw_utils._SDK_AVAILABLE
        original_error = dsw_utils._SDK_IMPORT_ERROR
        try:
            dsw_utils._SDK_AVAILABLE = False
            dsw_utils._SDK_IMPORT_ERROR = ImportError("test error")
            with pytest.raises(ImportError) as exc_info:
                dsw_utils._ensure_sdk()
            assert "test error" in str(exc_info.value)
            assert "pip install" in str(exc_info.value)
        finally:
            dsw_utils._SDK_AVAILABLE = original_available
            dsw_utils._SDK_IMPORT_ERROR = original_error
