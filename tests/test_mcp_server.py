#!/usr/bin/env python3
"""
Tests for mcp_server.py - MCP tool handlers.

Since the `mcp` SDK is not installed in the test environment,
we use a FakeServer that captures decorated handlers so they
can be called directly in tests.
"""

import asyncio
import importlib
import json
import os
import sys
import types
import pytest
from unittest.mock import patch, MagicMock

# Add scripts directory to path
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'scripts')
sys.path.insert(0, os.path.abspath(SCRIPTS_DIR))


# ---------------------------------------------------------------------------
# FakeServer: captures handler functions registered via decorators
# ---------------------------------------------------------------------------

_handlers = {}


class FakeServer:
    def __init__(self, name):
        self.name = name

    def list_tools(self):
        def decorator(fn):
            _handlers['list_tools'] = fn
            return fn
        return decorator

    def call_tool(self):
        def decorator(fn):
            _handlers['call_tool'] = fn
            return fn
        return decorator

    def create_initialization_options(self):
        return {}


class FakeTextContent:
    def __init__(self, type, text):
        self.type = type
        self.text = text


class FakeTool:
    def __init__(self, name, description, inputSchema):
        self.name = name
        self.description = description
        self.inputSchema = inputSchema


@pytest.fixture(scope="module", autouse=True)
def setup_mcp_mocks():
    """Replace mcp.* in sys.modules with fakes before importing mcp_server."""
    _handlers.clear()

    # Build a fake mcp.server module
    fake_mcp = types.ModuleType("mcp")
    fake_server_mod = types.ModuleType("mcp.server")
    fake_server_mod.Server = FakeServer
    fake_stdio_mod = types.ModuleType("mcp.server.stdio")
    fake_stdio_mod.stdio_server = MagicMock()
    fake_types_mod = types.ModuleType("mcp.types")
    fake_types_mod.Tool = FakeTool
    fake_types_mod.TextContent = FakeTextContent

    sys.modules["mcp"] = fake_mcp
    sys.modules["mcp.server"] = fake_server_mod
    sys.modules["mcp.server.stdio"] = fake_stdio_mod
    sys.modules["mcp.types"] = fake_types_mod

    # Force re-import mcp_server so it picks up our fakes
    if "mcp_server" in sys.modules:
        del sys.modules["mcp_server"]

    import mcp_server  # noqa: F401

    yield _handlers

    # Cleanup
    if "mcp_server" in sys.modules:
        del sys.modules["mcp_server"]


def _run(coro):
    """Helper to run an async function synchronously."""
    return asyncio.new_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestListTools:
    """Tests for the list_tools handler."""

    def test_returns_all_tools(self, setup_mcp_mocks):
        handler = _handlers['list_tools']
        tools = _run(handler())
        assert len(tools) == 8

    def test_tool_names(self, setup_mcp_mocks):
        tools = _run(_handlers['list_tools']())
        names = {t.name for t in tools}
        expected = {
            'list_instances', 'get_instance', 'start_instance', 'stop_instance',
            'create_instance', 'list_images', 'list_specs', 'get_instance_metrics',
        }
        assert names == expected

    def test_tools_have_descriptions(self, setup_mcp_mocks):
        tools = _run(_handlers['list_tools']())
        for tool in tools:
            assert tool.description, f"{tool.name} has no description"

    def test_tools_have_input_schemas(self, setup_mcp_mocks):
        tools = _run(_handlers['list_tools']())
        for tool in tools:
            assert isinstance(tool.inputSchema, dict)
            assert tool.inputSchema.get("type") == "object"


class TestCallToolListInstances:
    """Tests for call_tool with list_instances."""

    @patch('mcp_server._import_list_instances')
    def test_success(self, mock_import, setup_mcp_mocks):
        mock_fn = MagicMock(return_value=[{"InstanceId": "dsw-1", "Status": "Running"}])
        mock_import.return_value = mock_fn

        results = _run(_handlers['call_tool']("list_instances", {}))
        assert len(results) == 1
        data = json.loads(results[0].text)
        assert data[0]["InstanceId"] == "dsw-1"

    @patch('mcp_server._import_list_instances')
    def test_with_detail_level(self, mock_import, setup_mcp_mocks):
        mock_fn = MagicMock(return_value=[])
        mock_import.return_value = mock_fn

        _run(_handlers['call_tool']("list_instances", {"detail_level": "brief"}))
        mock_fn.assert_called_once_with(format="json", detail_level="brief")

    @patch('mcp_server._import_list_instances')
    def test_default_detail_level(self, mock_import, setup_mcp_mocks):
        mock_fn = MagicMock(return_value=[])
        mock_import.return_value = mock_fn

        _run(_handlers['call_tool']("list_instances", {}))
        mock_fn.assert_called_once_with(format="json", detail_level="summary")


class TestCallToolGetInstance:
    """Tests for call_tool with get_instance."""

    @patch('mcp_server._import_get_instance')
    @patch('mcp_server._resolve')
    def test_success(self, mock_resolve, mock_import, setup_mcp_mocks):
        mock_resolve.return_value = "dsw-123"
        mock_fn = MagicMock(return_value={"InstanceId": "dsw-123", "Status": "Running"})
        mock_import.return_value = mock_fn

        results = _run(_handlers['call_tool']("get_instance", {"instance": "my-inst"}))
        mock_resolve.assert_called_once_with("my-inst")
        data = json.loads(results[0].text)
        assert data["InstanceId"] == "dsw-123"

    @patch('mcp_server._import_get_instance')
    @patch('mcp_server._resolve')
    def test_not_found(self, mock_resolve, mock_import, setup_mcp_mocks):
        mock_resolve.return_value = "dsw-123"
        mock_fn = MagicMock(return_value=None)
        mock_import.return_value = mock_fn

        results = _run(_handlers['call_tool']("get_instance", {"instance": "dsw-123"}))
        data = json.loads(results[0].text)
        assert data["error"] == "INSTANCE_NOT_FOUND"

    @patch('mcp_server._import_get_instance')
    @patch('mcp_server._resolve')
    def test_detail_level_full(self, mock_resolve, mock_import, setup_mcp_mocks):
        mock_resolve.return_value = "dsw-1"
        mock_fn = MagicMock(return_value={})
        mock_import.return_value = mock_fn

        _run(_handlers['call_tool']("get_instance", {"instance": "dsw-1", "detail_level": "full"}))
        mock_fn.assert_called_once_with("dsw-1", detail_level="full")


class TestCallToolStartStop:
    """Tests for start_instance and stop_instance tools."""

    @patch('mcp_server._import_start_instance')
    @patch('mcp_server._resolve')
    def test_start(self, mock_resolve, mock_import, setup_mcp_mocks):
        mock_resolve.return_value = "dsw-1"
        mock_fn = MagicMock(return_value={"status": "ok"})
        mock_import.return_value = mock_fn

        results = _run(_handlers['call_tool']("start_instance", {"instance": "test"}))
        mock_resolve.assert_called_once_with("test")
        mock_fn.assert_called_once_with("dsw-1")
        data = json.loads(results[0].text)
        assert data["status"] == "ok"

    @patch('mcp_server._import_stop_instance')
    @patch('mcp_server._resolve')
    def test_stop(self, mock_resolve, mock_import, setup_mcp_mocks):
        mock_resolve.return_value = "dsw-2"
        mock_fn = MagicMock(return_value={"stopped": True})
        mock_import.return_value = mock_fn

        results = _run(_handlers['call_tool']("stop_instance", {"instance": "dsw-2"}))
        data = json.loads(results[0].text)
        assert data["stopped"] is True


class TestCallToolCreate:
    """Tests for create_instance tool."""

    @patch('mcp_server._import_create_instance')
    def test_create_basic(self, mock_import, setup_mcp_mocks):
        mock_fn = MagicMock(return_value={"instance_id": "dsw-new"})
        mock_import.return_value = mock_fn

        args = {"name": "test-inst", "image": "pytorch:2.0", "instance_type": "ecs.g6.large"}
        results = _run(_handlers['call_tool']("create_instance", args))
        mock_fn.assert_called_once_with(
            name="test-inst", image_id="pytorch:2.0",
            instance_type="ecs.g6.large", labels=None,
        )
        data = json.loads(results[0].text)
        assert data["instance_id"] == "dsw-new"

    @patch('mcp_server._import_create_instance')
    def test_create_with_labels(self, mock_import, setup_mcp_mocks):
        mock_fn = MagicMock(return_value={})
        mock_import.return_value = mock_fn

        args = {
            "name": "x", "image": "img", "instance_type": "ecs.g6.large",
            "labels": {"env": "test", "team": "ml"},
        }
        _run(_handlers['call_tool']("create_instance", args))
        call_kwargs = mock_fn.call_args[1]
        # labels should be JSON-encoded
        parsed = json.loads(call_kwargs["labels"])
        assert parsed == {"env": "test", "team": "ml"}


class TestCallToolListImages:
    """Tests for list_images tool."""

    @patch('mcp_server._import_list_images')
    def test_returns_filtered_fields(self, mock_import, setup_mcp_mocks):
        mock_fn = MagicMock(return_value=[
            {"ImageId": "img-1", "ImageName": "PyTorch", "Framework": "pytorch",
             "AcceleratorType": "GPU", "Extra": "should-be-filtered"},
        ])
        mock_import.return_value = mock_fn

        results = _run(_handlers['call_tool']("list_images", {}))
        data = json.loads(results[0].text)
        assert len(data) == 1
        assert "ImageId" in data[0]
        assert "Extra" not in data[0]


class TestCallToolListSpecs:
    """Tests for list_specs tool."""

    @patch('mcp_server._import_list_ecs_specs')
    def test_success(self, mock_import, setup_mcp_mocks):
        mock_fn = MagicMock(return_value=[{"InstanceType": "ecs.g6.large", "Cpu": 2}])
        mock_import.return_value = mock_fn

        results = _run(_handlers['call_tool']("list_specs", {"gpu_only": True}))
        mock_fn.assert_called_once_with(gpu_only=True)
        data = json.loads(results[0].text)
        assert data[0]["Cpu"] == 2


class TestCallToolMetrics:
    """Tests for get_instance_metrics tool."""

    @patch('mcp_server._import_get_metrics')
    @patch('mcp_server._resolve')
    def test_success(self, mock_resolve, mock_import, setup_mcp_mocks):
        mock_resolve.return_value = "dsw-1"
        mock_fn = MagicMock(return_value={"cpu": 45.5})
        mock_import.return_value = mock_fn

        results = _run(_handlers['call_tool'](
            "get_instance_metrics", {"instance": "dsw-1", "metric_type": "cpu"}
        ))
        mock_fn.assert_called_once_with("dsw-1", metric_type="cpu")
        data = json.loads(results[0].text)
        assert data["cpu"] == 45.5


class TestCallToolErrorHandling:
    """Tests for error handling in call_tool."""

    def test_unknown_tool(self, setup_mcp_mocks):
        results = _run(_handlers['call_tool']("nonexistent_tool", {}))
        data = json.loads(results[0].text)
        assert data["error"] == "UNKNOWN_TOOL"

    @patch('mcp_server._resolve')
    def test_dsw_error_returns_structured(self, mock_resolve, setup_mcp_mocks):
        from exceptions import InstanceNotFoundError
        mock_resolve.side_effect = InstanceNotFoundError("my-inst")

        results = _run(_handlers['call_tool']("get_instance", {"instance": "my-inst"}))
        data = json.loads(results[0].text)
        assert data["error"] == "INSTANCE_NOT_FOUND"
        assert "my-inst" in data["message"]

    @patch('mcp_server._resolve')
    def test_ambiguous_error(self, mock_resolve, setup_mcp_mocks):
        from exceptions import InstanceAmbiguousError
        mock_resolve.side_effect = InstanceAmbiguousError("gpu", [
            {"id": "dsw-1", "name": "gpu-1"}, {"id": "dsw-2", "name": "gpu-2"}
        ])

        results = _run(_handlers['call_tool']("start_instance", {"instance": "gpu"}))
        data = json.loads(results[0].text)
        assert data["error"] == "INSTANCE_AMBIGUOUS"
        assert len(data["details"]["matches"]) == 2

    @patch('mcp_server._import_list_instances')
    def test_generic_exception(self, mock_import, setup_mcp_mocks):
        mock_fn = MagicMock(side_effect=RuntimeError("unexpected"))
        mock_import.return_value = mock_fn

        results = _run(_handlers['call_tool']("list_instances", {}))
        data = json.loads(results[0].text)
        assert data["error"] == "INTERNAL_ERROR"
        assert "unexpected" in data["message"]
