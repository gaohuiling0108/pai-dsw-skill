#!/usr/bin/env python3
"""
Pytest fixtures and shared test utilities for PAI-DSW tests.
"""

import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Mock SDK modules before any script imports (SDK may not be installed in CI)
# ---------------------------------------------------------------------------
_SDK_MODULES = [
    'alibabacloud_pai_dsw20220101',
    'alibabacloud_pai_dsw20220101.client',
    'alibabacloud_pai_dsw20220101.models',
    'alibabacloud_tea_openapi',
    'alibabacloud_tea_openapi.models',
    'alibabacloud_tea_util',
    'alibabacloud_tea_util.models',
    'alibabacloud_credentials',
    'alibabacloud_credentials.client',
]

for _mod in _SDK_MODULES:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# Add scripts directory to path
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'scripts')
sys.path.insert(0, os.path.abspath(SCRIPTS_DIR))


# ============================================================================
# Mock Data
# ============================================================================

MOCK_INSTANCE = {
    "InstanceId": "dsw-123456-abcde",
    "InstanceName": "test-instance",
    "Status": "Running",
    "InstanceType": "ecs.g6.large",
    "GpuCount": 0,
    "ImageId": "modelscope:1.34.0",
    "WorkspaceId": "ws-12345",
    "CreateTime": "2024-01-01T00:00:00Z",
    "ExpiredTime": "2024-12-31T23:59:59Z",
    "Labels": {"env": "test", "team": "ml"},
    "VpcId": "vpc-12345",
    "SecurityGroupId": "sg-12345",
    "SystemDiskSize": 100,
    "DataDiskSize": 500
}

MOCK_INSTANCES_LIST = [
    MOCK_INSTANCE,
    {
        "InstanceId": "dsw-789012-xyz",
        "InstanceName": "gpu-training",
        "Status": "Stopped",
        "InstanceType": "ecs.gn6v-c8g1.16xlarge",
        "GpuCount": 1,
        "ImageId": "pytorch:2.0.0",
        "WorkspaceId": "ws-12345",
        "CreateTime": "2024-01-15T00:00:00Z",
        "ExpiredTime": "2024-12-31T23:59:59Z",
        "Labels": {"env": "prod", "team": "ml"},
    },
    {
        "InstanceId": "dsw-345678-def",
        "InstanceName": "dev-notebook",
        "Status": "Running",
        "InstanceType": "ecs.g6.xlarge",
        "GpuCount": 0,
        "ImageId": "tensorflow:2.12.0",
        "WorkspaceId": "ws-12345",
        "CreateTime": "2024-02-01T00:00:00Z",
        "ExpiredTime": "2024-12-31T23:59:59Z",
        "Labels": {"env": "dev"},
    }
]

MOCK_WORKSPACE = {
    "WorkspaceId": "ws-12345",
    "WorkspaceName": "ml-team",
    "Status": "Active",
    "CreateTime": "2024-01-01T00:00:00Z"
}

MOCK_IMAGE = {
    "ImageId": "modelscope:1.34.0",
    "ImageName": "ModelScope 1.34.0",
    "ImageType": "Official",
    "GpuType": "CPU",
    "CreateTime": "2024-01-01T00:00:00Z"
}

MOCK_SPEC = {
    "InstanceType": "ecs.g6.large",
    "Cpu": 2,
    "Memory": 8,
    "GpuType": None,
    "GpuCount": 0
}

MOCK_SNAPSHOT = {
    "SnapshotId": "snap-12345",
    "SnapshotName": "daily-backup",
    "Status": "Available",
    "Size": 50,
    "CreateTime": "2024-01-01T00:00:00Z"
}

MOCK_METRICS = {
    "cpu_utilization": {
        "avg": 45.5,
        "max": 80.0,
        "min": 10.0,
        "data": [
            {"timestamp": "2024-01-01T00:00:00Z", "value": 45.5}
        ]
    },
    "memory_utilization": {
        "avg": 60.0,
        "max": 75.0,
        "min": 40.0,
        "data": [
            {"timestamp": "2024-01-01T00:00:00Z", "value": 60.0}
        ]
    }
}

MOCK_CREDENTIALS = {
    "AccessKeyId": "test-access-key-id",
    "AccessKeySecret": "test-access-key-secret",
    "SecurityToken": "test-security-token",
    "Code": "Success"
}


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_env_credentials():
    """Mock environment variable credentials."""
    env_vars = {
        "ALIBABA_CLOUD_ACCESS_KEY_ID": "test-key-id",
        "ALIBABA_CLOUD_ACCESS_KEY_SECRET": "test-key-secret",
        "ALIBABA_CLOUD_SECURITY_TOKEN": "test-token",
        "ALIBABA_CLOUD_REGION_ID": "cn-shanghai",
        "PAI_WORKSPACE_ID": "ws-12345",
        "HOSTNAME": "dsw-123456-abcde"
    }
    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


@pytest.fixture
def mock_metadata_credentials():
    """Mock metadata service credentials (DSW RAM role)."""
    env_vars = {
        "ALIBABA_CLOUD_CREDENTIALS_URI": "http://metadata/example",
        "ALIBABA_CLOUD_REGION_ID": "cn-hangzhou",
        "PAI_WORKSPACE_ID": "ws-12345",
        "HOSTNAME": "dsw-123456-abcde"
    }
    with patch.dict(os.environ, env_vars, clear=True):
        yield env_vars


@pytest.fixture
def mock_dsw_client():
    """Mock PAI-DSW client."""
    client = MagicMock()
    
    # Mock list instances
    list_response = MagicMock()
    list_response.body = MagicMock()
    list_response.body.instances = MagicMock()
    list_response.body.instances.instance = [
        MagicMock(**inst) for inst in MOCK_INSTANCES_LIST
    ]
    client.list_instances.return_value = list_response
    
    # Mock get instance
    get_response = MagicMock()
    get_response.body = MagicMock()
    get_response.body.instance = MagicMock(**MOCK_INSTANCE)
    client.get_instance.return_value = get_response
    
    # Mock create instance
    create_response = MagicMock()
    create_response.body = MagicMock()
    create_response.body.instance_id = "dsw-new-instance-id"
    client.create_instance.return_value = create_response
    
    # Mock start/stop/delete
    client.start_instance.return_value = MagicMock()
    client.stop_instance.return_value = MagicMock()
    client.delete_instance.return_value = MagicMock()
    
    # Mock list workspaces
    ws_response = MagicMock()
    ws_response.body = MagicMock()
    ws_response.body.workspaces = MagicMock()
    ws_response.body.workspaces.workspace = [MagicMock(**MOCK_WORKSPACE)]
    client.list_workspaces.return_value = ws_response
    
    # Mock list images
    img_response = MagicMock()
    img_response.body = MagicMock()
    img_response.body.images = MagicMock()
    img_response.body.images.image = [MagicMock(**MOCK_IMAGE)]
    client.list_images.return_value = img_response
    
    # Mock list specs
    specs_response = MagicMock()
    specs_response.body = MagicMock()
    specs_response.body.ecs_specs = MagicMock()
    specs_response.body.ecs_specs.ecs_spec = [MagicMock(**MOCK_SPEC)]
    client.list_ecs_specs.return_value = specs_response
    
    # Mock snapshots
    snap_response = MagicMock()
    snap_response.body = MagicMock()
    snap_response.body.snapshots = MagicMock()
    snap_response.body.snapshots.snapshot = [MagicMock(**MOCK_SNAPSHOT)]
    client.list_snapshots.return_value = snap_response
    
    return client


@pytest.fixture
def mock_requests_get():
    """Mock requests.get for metadata service."""
    with patch('requests.get') as mock_get:
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = MOCK_CREDENTIALS
        mock_get.return_value = response
        yield mock_get


@pytest.fixture
def capsys_disabled():
    """Disable output capture for debugging."""
    import sys
    yield sys


# ============================================================================
# Test Helpers
# ============================================================================

def assert_json_output(output: str) -> dict:
    """Parse and validate JSON output."""
    try:
        return json.loads(output)
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON output: {e}\nOutput: {output}")


def assert_table_output(output: str, expected_headers: list):
    """Validate table output contains expected headers."""
    lines = output.strip().split('\n')
    if len(lines) < 2:
        pytest.fail(f"Table output too short:\n{output}")
    
    header_line = lines[0]
    for header in expected_headers:
        if header not in header_line:
            pytest.fail(f"Missing header '{header}' in table:\n{header_line}")