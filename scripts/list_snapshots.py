#!/usr/bin/env python3
"""
List snapshots of a PAI-DSW instance.

Usage:
    python list_snapshots.py <instance_id> [options]

Options:
    --region <region>       Region ID (default: from environment)
    --format <format>       Output format: table, json (default: table)
    --help                  Show this help message

Examples:
    # List snapshots for an instance
    python list_snapshots.py dsw-123456

    # JSON output
    python list_snapshots.py dsw-123456 --format json
"""

import os
import sys
import json
import argparse
from datetime import datetime

# Add script directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from dsw_utils import create_client
from alibabacloud_pai_dsw20220101 import models as dsw_models


def list_snapshots(instance_id: str, region_id: str = None) -> list:
    """
    List snapshots of a DSW instance.
    
    Args:
        instance_id: Instance ID
        region_id: Region ID
    
    Returns:
        List of snapshots
    """
    client = create_client(region_id)
    
    request = dsw_models.ListInstanceSnapshotRequest()
    request.instance_id = instance_id
    
    response = client.list_instance_snapshot(request)
    
    snapshots = []
    if response.body and response.body.snapshots:
        for snap in response.body.snapshots:
            snapshots.append({
                'snapshot_id': getattr(snap, 'snapshot_id', None),
                'snapshot_name': getattr(snap, 'snapshot_name', None),
                'status': getattr(snap, 'status', None),
                'progress': getattr(snap, 'progress', None),
                'image_url': getattr(snap, 'image_url', None),
                'image_id': getattr(snap, 'image_id', None),
                'creation_time': getattr(snap, 'creation_time', None),
                'description': getattr(snap, 'description', None),
            })
    
    return snapshots


def format_table(snapshots: list) -> str:
    """Format snapshots as a table."""
    if not snapshots:
        return "No snapshots found for this instance."
    
    # Determine column widths
    id_width = max(len(s['snapshot_id'] or '') for s in snapshots)
    id_width = max(id_width, 10)
    name_width = max(len(s['snapshot_name'] or 'N/A') for s in snapshots)
    name_width = max(name_width, 20)
    status_width = 12
    progress_width = 10
    
    # Header
    header = f"{'Snapshot ID':<{id_width}} {'Name':<{name_width}} {'Status':<{status_width}} {'Progress':>{progress_width}}  Created"
    separator = '-' * len(header)
    
    lines = [separator, header, separator]
    
    for snap in sorted(snapshots, key=lambda x: x['creation_time'] or '', reverse=True):
        name = snap['snapshot_name'] or 'N/A'
        progress = f"{snap['progress']}%" if snap['progress'] else 'N/A'
        created = snap['creation_time'] or 'N/A'
        
        # Truncate if too long
        if len(name) > name_width:
            name = name[:name_width-3] + '...'
        
        line = f"{snap['snapshot_id']:<{id_width}} {name:<{name_width}} {snap['status']:<{status_width}} {progress:>{progress_width}}  {created}"
        lines.append(line)
    
    lines.append(separator)
    lines.append(f"Total: {len(snapshots)} snapshots")
    
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='List snapshots of a PAI-DSW instance')
    parser.add_argument('instance_id', help='Instance ID')
    parser.add_argument('--region', default=os.getenv('ALIBABA_CLOUD_REGION_ID'),
                        help='Region ID')
    parser.add_argument('--format', choices=['table', 'json'], default='table',
                        help='Output format')
    
    args = parser.parse_args()
    
    try:
        snapshots = list_snapshots(
            instance_id=args.instance_id,
            region_id=args.region
        )
        
        if args.format == 'json':
            print(json.dumps(snapshots, indent=2, ensure_ascii=False))
        else:
            print(f"\n{'='*80}")
            print(f"  Snapshots for instance: {args.instance_id}")
            print(f"{'='*80}\n")
            print(format_table(snapshots))
            print()
            
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()