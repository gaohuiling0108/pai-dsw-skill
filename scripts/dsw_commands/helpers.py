"""
Helper utilities for DSW CLI commands.

Provides script execution, instance JSON fetching, and instance name resolution.
"""

import json
import os
import subprocess
from typing import Optional, List

from dsw_commands.formatting import print_info, print_error

# Resolve script directory (follows symlinks)
_HELPERS_FILE = os.path.abspath(__file__)
if os.path.islink(_HELPERS_FILE):
    _HELPERS_FILE = os.path.realpath(_HELPERS_FILE)
# scripts/ is the parent of dsw_commands/
SCRIPT_DIR = os.path.dirname(os.path.dirname(_HELPERS_FILE))

# Add script dir to path so standalone scripts can be imported
if SCRIPT_DIR not in __import__('sys').path:
    __import__('sys').path.insert(0, SCRIPT_DIR)

from exceptions import InstanceNotFoundError, InstanceAmbiguousError


def run_script(script_name: str, args: list, capture_output: bool = False):
    """
    Run a standalone script by name.

    Args:
        script_name: Script name without .py extension.
        args: Arguments to pass to the script.
        capture_output: If True, return (returncode, stdout, stderr) tuple.

    Returns:
        int (returncode) or tuple (returncode, stdout, stderr).
    """
    script_path = os.path.join(SCRIPT_DIR, f"{script_name}.py")
    cmd = ['python3', script_path] + args

    if capture_output:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    else:
        return subprocess.run(cmd).returncode


def get_instances_json() -> List[dict]:
    """Fetch the instance list as parsed JSON from list_instances.py."""
    script_path = os.path.join(SCRIPT_DIR, "list_instances.py")
    result = subprocess.run(
        ['python3', script_path, '--format', 'json'],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return []
    return []


def resolve_instance(identifier: str) -> str:
    """
    Resolve an instance identifier to an instance ID.

    Supports exact instance IDs and fuzzy name matching.

    Args:
        identifier: Instance ID or (partial) name.

    Returns:
        Resolved instance ID string.

    Raises:
        InstanceNotFoundError: No matching instance found.
        InstanceAmbiguousError: Multiple instances match the name.
    """
    # If it looks like an ID (starts with dsw- or has multiple dashes)
    if identifier.startswith('dsw-') or identifier.count('-') >= 2:
        return identifier

    # Otherwise search by name
    instances = get_instances_json()
    matches = []

    for inst in instances:
        name = inst.get('InstanceName', '')
        instance_id = inst.get('InstanceId', '')

        # Exact match
        if name == identifier:
            return instance_id

        # Fuzzy match (name contains identifier)
        if identifier.lower() in name.lower():
            matches.append((instance_id, name))

    if len(matches) == 0:
        raise InstanceNotFoundError(identifier)
    elif len(matches) == 1:
        instance_id, name = matches[0]
        print_info(f"匹配到实例: {name} ({instance_id})")
        return instance_id
    else:
        raise InstanceAmbiguousError(
            identifier,
            [{"id": mid, "name": mname} for mid, mname in matches],
        )
