#!/usr/bin/env python3
"""
Tests for exceptions.py - Custom exception hierarchy.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from exceptions import (
    DSWError,
    InstanceNotFoundError,
    InstanceAmbiguousError,
    InstanceStateError,
    CredentialError,
    WorkspaceNotSetError,
    ConfigError,
    APIError,
    RateLimitError,
    ValidationError,
)


class TestDSWError:
    """Tests for DSWError base class."""

    def test_default_code(self):
        err = DSWError("something went wrong")
        assert err.message == "something went wrong"
        assert err.code == "DSW_ERROR"
        assert err.details == {}

    def test_custom_code_and_details(self):
        err = DSWError("bad", code="CUSTOM", details={"key": "val"})
        assert err.code == "CUSTOM"
        assert err.details == {"key": "val"}

    def test_str_equals_message(self):
        err = DSWError("hello")
        assert str(err) == "hello"

    def test_is_exception(self):
        assert issubclass(DSWError, Exception)
        with pytest.raises(DSWError):
            raise DSWError("test")

    def test_to_dict_with_details(self):
        err = DSWError("msg", code="C", details={"a": 1})
        d = err.to_dict()
        assert d == {"error": "C", "message": "msg", "details": {"a": 1}}

    def test_to_dict_without_details(self):
        err = DSWError("msg", code="C")
        d = err.to_dict()
        assert d == {"error": "C", "message": "msg"}
        assert "details" not in d


class TestInstanceNotFoundError:
    """Tests for InstanceNotFoundError."""

    def test_construction(self):
        err = InstanceNotFoundError("my-instance")
        assert "my-instance" in err.message
        assert err.code == "INSTANCE_NOT_FOUND"
        assert err.details == {"identifier": "my-instance"}

    def test_inherits_dsw_error(self):
        assert issubclass(InstanceNotFoundError, DSWError)

    def test_to_dict(self):
        d = InstanceNotFoundError("x").to_dict()
        assert d["error"] == "INSTANCE_NOT_FOUND"
        assert d["details"]["identifier"] == "x"


class TestInstanceAmbiguousError:
    """Tests for InstanceAmbiguousError."""

    def test_construction(self):
        matches = [{"id": "dsw-1", "name": "a"}, {"id": "dsw-2", "name": "b"}]
        err = InstanceAmbiguousError("gpu", matches)
        assert "gpu" in err.message
        assert err.code == "INSTANCE_AMBIGUOUS"
        assert err.details["identifier"] == "gpu"
        assert err.details["matches"] == matches

    def test_to_dict_contains_matches(self):
        matches = [{"id": "dsw-1", "name": "a"}]
        d = InstanceAmbiguousError("x", matches).to_dict()
        assert len(d["details"]["matches"]) == 1


class TestInstanceStateError:
    """Tests for InstanceStateError."""

    def test_construction(self):
        err = InstanceStateError("dsw-123", "Stopped", "Running")
        assert "dsw-123" in err.message
        assert "Stopped" in err.message
        assert "Running" in err.message
        assert err.code == "INSTANCE_STATE_ERROR"
        assert err.details == {
            "instance_id": "dsw-123",
            "current_status": "Stopped",
            "required_status": "Running",
        }


class TestCredentialError:
    """Tests for CredentialError."""

    def test_default_message(self):
        err = CredentialError()
        assert err.code == "CREDENTIAL_ERROR"
        assert "凭证" in err.message

    def test_custom_message(self):
        err = CredentialError("custom msg")
        assert err.message == "custom msg"


class TestWorkspaceNotSetError:
    """Tests for WorkspaceNotSetError."""

    def test_construction(self):
        err = WorkspaceNotSetError()
        assert err.code == "WORKSPACE_NOT_SET"
        assert "PAI_WORKSPACE_ID" in err.message


class TestConfigError:
    """Tests for ConfigError."""

    def test_construction(self):
        err = ConfigError("bad config file")
        assert err.message == "bad config file"
        assert err.code == "CONFIG_ERROR"


class TestAPIError:
    """Tests for APIError."""

    def test_with_status_code(self):
        err = APIError("server error", status_code=500)
        assert err.code == "API_ERROR"
        assert err.details == {"status_code": 500}

    def test_without_status_code(self):
        err = APIError("timeout")
        assert err.details == {}

    def test_inherits_dsw_error(self):
        assert issubclass(APIError, DSWError)


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_default(self):
        err = RateLimitError()
        assert err.code == "RATE_LIMITED"
        assert err.details["status_code"] == 429
        assert "retry_after" not in err.details

    def test_with_retry_after(self):
        err = RateLimitError(retry_after=30)
        assert err.details["retry_after"] == 30
        assert err.details["status_code"] == 429

    def test_inherits_api_error(self):
        assert issubclass(RateLimitError, APIError)


class TestValidationError:
    """Tests for ValidationError."""

    def test_with_field(self):
        err = ValidationError("name too long", field="instance_name")
        assert err.code == "VALIDATION_ERROR"
        assert err.details == {"field": "instance_name"}

    def test_without_field(self):
        err = ValidationError("invalid input")
        assert err.details == {}
        assert err.message == "invalid input"
