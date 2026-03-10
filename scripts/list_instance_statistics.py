#!/usr/bin/env python3
"""
List instance statistics for PAI-DSW workspace.

Aggregates statistics from all instances in the workspace.

Usage:
    python list_instance_statistics.py [options]

Options:
    --region <region>     Region ID
    --format <format>     Output format: table, json (default: table)
    --help                Show this help message
"""

import os
import sys
import json
import argparse
from datetime import datetime
from collections import defaultdict

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from dsw_utils import create_client, get_workspace_id
from alibabacloud_pai_dsw20220101 import models as dsw_models


def list_instance_statistics(workspace_id: str, region_id: str = None) -> dict:
    """
    Get instance statistics for a workspace.
    
    Args:
        workspace_id: Workspace ID
        region_id: Region ID
    
    Returns:
        Statistics dictionary
    """
    client = create_client(region_id)
    
    # Get all instances
    request = dsw_models.ListInstancesRequest()
    request.workspace_id = workspace_id
    response = client.list_instances(request)
    
    # Initialize statistics
    stats = {
        'workspace_id': workspace_id,
        'generated_at': datetime.now().isoformat(),
        'total_instances': 0,
        'by_status': defaultdict(int),
        'by_spec': defaultdict(int),
        'by_instance_type': {'cpu': 0, 'gpu': 0},
        'gpu_details': [],
        'running_instances': [],
        'stopped_instances': [],
        'failed_instances': [],
    }
    
    # GPU spec keywords
    gpu_specs = ['gn', 'gn6', 'gn7', 'gn8', 'gn6i', 'gn7i', 'gn8i', 'p3', 'p4']
    
    if response.body and response.body.instances:
        stats['total_instances'] = len(response.body.instances)
        
        for inst in response.body.instances:
            status = inst.status or 'Unknown'
            ecs_spec = inst.ecs_spec or 'Unknown'
            name = inst.instance_name or 'N/A'
            
            # By status
            stats['by_status'][status] += 1
            
            # By spec
            stats['by_spec'][ecs_spec] += 1
            
            # GPU or CPU
            is_gpu = any(spec in ecs_spec.lower() for spec in gpu_specs)
            if is_gpu:
                stats['by_instance_type']['gpu'] += 1
                stats['gpu_details'].append({
                    'id': inst.instance_id,
                    'name': name,
                    'spec': ecs_spec,
                    'status': status,
                })
            else:
                stats['by_instance_type']['cpu'] += 1
            
            # By status lists
            instance_info = {
                'id': inst.instance_id,
                'name': name,
                'spec': ecs_spec,
            }
            
            if status == 'Running':
                stats['running_instances'].append(instance_info)
            elif status == 'Stopped':
                stats['stopped_instances'].append(instance_info)
            elif status == 'Failed':
                stats['failed_instances'].append(instance_info)
    
    # Convert defaultdict to dict
    stats['by_status'] = dict(stats['by_status'])
    stats['by_spec'] = dict(stats['by_spec'])
    
    return stats


def main():
    parser = argparse.ArgumentParser(description='List PAI-DSW instance statistics')
    parser.add_argument('--workspace', help='Workspace ID')
    parser.add_argument('--region', help='Region ID')
    parser.add_argument('--format', choices=['table', 'json'], default='table',
                        help='Output format')
    
    args = parser.parse_args()
    
    workspace_id = args.workspace
    if not workspace_id:
        try:
            workspace_id = get_workspace_id(allow_interactive=False)
        except:
            print("❌ Error: Workspace ID required", file=sys.stderr)
            sys.exit(1)
    
    try:
        stats = list_instance_statistics(workspace_id, args.region)
        
        if args.format == 'json':
            print(json.dumps(stats, indent=2, ensure_ascii=False))
        else:
            print(f"\n{'='*70}")
            print(f"  PAI-DSW Instance Statistics")
            print(f"{'='*70}")
            print(f"  Workspace: {workspace_id}")
            print(f"  Generated: {stats['generated_at']}")
            print(f"{'='*70}")
            
            # Summary
            print(f"\n  📊 Summary")
            print(f"    Total Instances: {stats['total_instances']}")
            print(f"    CPU Instances: {stats['by_instance_type']['cpu']}")
            print(f"    GPU Instances: {stats['by_instance_type']['gpu']}")
            
            # By Status
            print(f"\n  📈 By Status")
            for status, count in sorted(stats['by_status'].items()):
                print(f"    {status}: {count}")
            
            # GPU Instances
            if stats['gpu_details']:
                print(f"\n  🎮 GPU Instances ({len(stats['gpu_details'])})")
                for gpu in stats['gpu_details']:
                    status_icon = '✅' if gpu['status'] == 'Running' else '⏸️' if gpu['status'] == 'Stopped' else '❌'
                    print(f"    {status_icon} {gpu['name']}: {gpu['spec']} ({gpu['status']})")
            
            # By Spec
            print(f"\n  💻 By Specification")
            for spec, count in sorted(stats['by_spec'].items(), key=lambda x: -x[1]):
                print(f"    {spec}: {count}")
            
            # Failed Instances
            if stats['failed_instances']:
                print(f"\n  ⚠️ Failed Instances ({len(stats['failed_instances'])})")
                for inst in stats['failed_instances']:
                    print(f"    ❌ {inst['name']} ({inst['id'][:20]}...)")
            
            print(f"\n{'='*70}\n")
            
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()