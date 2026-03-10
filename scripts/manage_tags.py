#!/usr/bin/env python3
"""
PAI-DSW Instance Tag Management Tool.

This script provides comprehensive tag management capabilities:
- List tags on instances
- Add/remove/update tags
- Batch operations across multiple instances
- Filter instances by tags

Usage:
    python manage_tags.py <command> [options]

Commands:
    list <instance>         List tags on an instance
    add <instance> <tags>   Add tags to an instance
    remove <instance> <keys> Remove tags by keys
    set <instance> <tags>   Set (replace) all tags
    batch-add <tags>        Add tags to multiple instances
    batch-remove <keys>     Remove tags from multiple instances
    filter <tag_filter>     Filter instances by tags
    export                  Export all instance tags
    help                    Show this help message

Tag Format:
    Single tag: key=value or {"key":"value"}
    Multiple tags: key1=value1,key2=value2 or JSON

Examples:
    # List tags
    python manage_tags.py list dsw-123456

    # Add tags
    python manage_tags.py add dsw-123456 env=prod,team=ml
    python manage_tags.py add dsw-123456 '{"env":"prod","team":"ml"}'

    # Remove tags
    python manage_tags.py remove dsw-123456 env,team

    # Set (replace) all tags
    python manage_tags.py set dsw-123456 env=dev,owner=momo

    # Batch add tags to multiple instances
    python manage_tags.py batch-add env=prod --instances dsw-123,dsw-456
    python manage_tags.py batch-add env=prod --query "gpu"  # Apply to instances matching name

    # Batch remove tags
    python manage_tags.py batch-remove temp --instances dsw-123,dsw-456

    # Filter instances by tags
    python manage_tags.py filter env=prod
    python manage_tags.py filter env=prod,team=ml
    python manage_tags.py filter env --has-key  # Has 'env' key regardless of value

    # Export all tags
    python manage_tags.py export --format json
    python manage_tags.py export --format csv

Environment Variables:
    ALIBABA_CLOUD_ACCESS_KEY_ID     - Access Key ID
    ALIBABA_CLOUD_ACCESS_KEY_SECRET - Access Key Secret
    ALIBABA_CLOUD_SECURITY_TOKEN    - Security Token (for STS)
    ALIBABA_CLOUD_REGION_ID         - Default region
    PAI_WORKSPACE_ID                - Default workspace
"""

import os
import sys
import json
import argparse
import csv
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Add script directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from dsw_utils import create_client, get_workspace_id, print_table
from alibabacloud_pai_dsw20220101 import models as dsw_models


def parse_tags(tags_str: str) -> Dict[str, str]:
    """
    Parse tags from string format.
    
    Supports:
    - key=value,key2=value2
    - JSON: {"key":"value","key2":"value2"}
    
    Args:
        tags_str: Tag string
    
    Returns:
        Dictionary of tags
    """
    if not tags_str:
        return {}
    
    # Try JSON format first
    if tags_str.startswith('{'):
        try:
            return json.loads(tags_str)
        except json.JSONDecodeError:
            pass
    
    # Parse key=value format
    tags = {}
    for pair in tags_str.split(','):
        pair = pair.strip()
        if '=' in pair:
            key, value = pair.split('=', 1)
            tags[key.strip()] = value.strip()
        elif pair:  # Key without value
            tags[pair] = ''
    
    return tags


def parse_keys(keys_str: str) -> List[str]:
    """
    Parse tag keys from string.
    
    Args:
        keys_str: Comma-separated keys
    
    Returns:
        List of keys
    """
    if not keys_str:
        return []
    return [k.strip() for k in keys_str.split(',') if k.strip()]


def get_instance(client, instance_id: str) -> dict:
    """Get instance details including labels."""
    response = client.get_instance(instance_id)
    
    if response.body:
        inst = response.body
        labels = {}
        if hasattr(inst, 'labels') and inst.labels:
            for label in inst.labels:
                labels[label.key] = label.value
        
        return {
            'InstanceId': inst.instance_id,
            'InstanceName': inst.instance_name,
            'Status': inst.status,
            'Labels': labels,
        }
    return None


def get_all_instances(client, workspace_id: str) -> List[dict]:
    """Get all instances with their tags."""
    request = dsw_models.ListInstancesRequest(workspace_id=workspace_id)
    response = client.list_instances(request)
    
    instances = []
    if response.body and response.body.instances:
        for inst in response.body.instances:
            labels = {}
            if hasattr(inst, 'labels') and inst.labels:
                for label in inst.labels:
                    labels[label.key] = label.value
            
            instances.append({
                'InstanceId': inst.instance_id,
                'InstanceName': inst.instance_name,
                'Status': inst.status,
                'Labels': labels,
            })
    
    return instances


def update_instance_tags(
    client,
    instance_id: str,
    tags: Dict[str, str] = None,
    remove_keys: List[str] = None,
    replace_all: bool = False
) -> Tuple[bool, str]:
    """
    Update tags on an instance.
    
    Args:
        client: PAI-DSW client
        instance_id: Instance ID
        tags: Tags to add/update
        remove_keys: Keys to remove
        replace_all: If True, replace all tags with 'tags'
    
    Returns:
        Tuple of (success, message)
    """
    try:
        # Get current instance
        instance = get_instance(client, instance_id)
        if not instance:
            return False, f"Instance {instance_id} not found"
        
        current_labels = instance.get('Labels', {})
        
        # Prepare new labels
        if replace_all:
            new_labels = tags or {}
        else:
            new_labels = current_labels.copy()
            
            # Remove specified keys
            if remove_keys:
                for key in remove_keys:
                    new_labels.pop(key, None)
            
            # Add/update tags
            if tags:
                new_labels.update(tags)
        
        # Update instance
        request = dsw_models.UpdateInstanceRequest()
        
        label_list = [
            dsw_models.UpdateInstanceRequestLabels(
                key=k,
                value=v
            ) for k, v in new_labels.items()
        ]
        request.labels = label_list
        
        response = client.update_instance(instance_id, request)
        
        if response.status_code == 200:
            return True, f"Tags updated for {instance_id}"
        else:
            return False, f"Failed to update tags: HTTP {response.status_code}"
            
    except Exception as e:
        return False, f"Error updating tags: {str(e)}"


def cmd_list(args):
    """List tags on an instance."""
    client = create_client(args.region)
    
    try:
        instance = get_instance(client, args.instance)
        
        if not instance:
            print(f"❌ Instance {args.instance} not found", file=sys.stderr)
            return 1
        
        labels = instance.get('Labels', {})
        
        if args.format == 'json':
            output = {
                'InstanceId': instance['InstanceId'],
                'InstanceName': instance['InstanceName'],
                'Tags': labels
            }
            print(json.dumps(output, indent=2, ensure_ascii=False))
        else:
            print(f"\n📋 Instance: {instance['InstanceName']}")
            print(f"   ID: {instance['InstanceId']}")
            print(f"\n🏷️  Tags ({len(labels)}):")
            
            if not labels:
                print("   No tags")
            else:
                max_key_len = max(len(k) for k in labels.keys())
                for key, value in sorted(labels.items()):
                    print(f"   {key:<{max_key_len}} = {value}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


def cmd_add(args):
    """Add tags to an instance."""
    client = create_client(args.region)
    tags = parse_tags(args.tags)
    
    if not tags:
        print("❌ No valid tags provided", file=sys.stderr)
        return 1
    
    # Show current tags if not quiet
    if not args.quiet:
        instance = get_instance(client, args.instance)
        if instance:
            current = instance.get('Labels', {})
            print(f"\n📋 Instance: {instance['InstanceName']} ({args.instance})")
            print(f"   Current tags: {current or 'None'}")
            print(f"   Adding: {tags}")
    
    # Confirmation
    if not args.force:
        confirm = input(f"\nAdd tags to {args.instance}? (y/N): ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            return 0
    
    success, message = update_instance_tags(client, args.instance, tags=tags)
    
    if success:
        print(f"✅ {message}")
        return 0
    else:
        print(f"❌ {message}", file=sys.stderr)
        return 1


def cmd_remove(args):
    """Remove tags from an instance."""
    client = create_client(args.region)
    keys = parse_keys(args.keys)
    
    if not keys:
        print("❌ No keys provided", file=sys.stderr)
        return 1
    
    # Show current tags if not quiet
    if not args.quiet:
        instance = get_instance(client, args.instance)
        if instance:
            current = instance.get('Labels', {})
            print(f"\n📋 Instance: {instance['InstanceName']} ({args.instance})")
            print(f"   Current tags: {current or 'None'}")
            print(f"   Removing keys: {keys}")
    
    # Confirmation
    if not args.force:
        confirm = input(f"\nRemove tags from {args.instance}? (y/N): ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            return 0
    
    success, message = update_instance_tags(client, args.instance, remove_keys=keys)
    
    if success:
        print(f"✅ {message}")
        return 0
    else:
        print(f"❌ {message}", file=sys.stderr)
        return 1


def cmd_set(args):
    """Set (replace) all tags on an instance."""
    client = create_client(args.region)
    tags = parse_tags(args.tags)
    
    # Show current tags if not quiet
    if not args.quiet:
        instance = get_instance(client, args.instance)
        if instance:
            current = instance.get('Labels', {})
            print(f"\n📋 Instance: {instance['InstanceName']} ({args.instance})")
            print(f"   Current tags: {current or 'None'}")
            print(f"   New tags: {tags or 'None (clear all)'}")
    
    # Confirmation
    if not args.force:
        confirm = input(f"\nReplace all tags on {args.instance}? (y/N): ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            return 0
    
    success, message = update_instance_tags(client, args.instance, tags=tags, replace_all=True)
    
    if success:
        print(f"✅ {message}")
        return 0
    else:
        print(f"❌ {message}", file=sys.stderr)
        return 1


def cmd_batch_add(args):
    """Add tags to multiple instances."""
    client = create_client(args.region)
    workspace_id = args.workspace or get_workspace_id()
    tags = parse_tags(args.tags)
    
    if not tags:
        print("❌ No valid tags provided", file=sys.stderr)
        return 1
    
    # Get target instances
    instances = []
    if args.instances:
        instances = [{'InstanceId': i, 'InstanceName': i} for i in args.instances.split(',')]
    elif args.query:
        all_instances = get_all_instances(client, workspace_id)
        query_lower = args.query.lower()
        instances = [
            i for i in all_instances
            if query_lower in i['InstanceName'].lower() or query_lower in i['InstanceId'].lower()
        ]
    else:
        print("❌ Specify --instances or --query", file=sys.stderr)
        return 1
    
    if not instances:
        print("❌ No instances found", file=sys.stderr)
        return 1
    
    print(f"\n📋 Adding tags to {len(instances)} instance(s):")
    print(f"   Tags: {tags}")
    for inst in instances:
        print(f"   - {inst.get('InstanceName', inst['InstanceId'])}")
    
    # Confirmation
    if not args.force:
        confirm = input(f"\nProceed? (y/N): ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            return 0
    
    # Process instances
    success_count = 0
    fail_count = 0
    
    for inst in instances:
        instance_id = inst['InstanceId']
        success, message = update_instance_tags(client, instance_id, tags=tags)
        
        if success:
            print(f"  ✅ {instance_id}")
            success_count += 1
        else:
            print(f"  ❌ {instance_id}: {message}")
            fail_count += 1
    
    print(f"\n📊 Results: {success_count} succeeded, {fail_count} failed")
    return 0 if fail_count == 0 else 1


def cmd_batch_remove(args):
    """Remove tags from multiple instances."""
    client = create_client(args.region)
    workspace_id = args.workspace or get_workspace_id()
    keys = parse_keys(args.keys)
    
    if not keys:
        print("❌ No keys provided", file=sys.stderr)
        return 1
    
    # Get target instances
    instances = []
    if args.instances:
        instances = [{'InstanceId': i, 'InstanceName': i} for i in args.instances.split(',')]
    elif args.query:
        all_instances = get_all_instances(client, workspace_id)
        query_lower = args.query.lower()
        instances = [
            i for i in all_instances
            if query_lower in i['InstanceName'].lower() or query_lower in i['InstanceId'].lower()
        ]
    else:
        print("❌ Specify --instances or --query", file=sys.stderr)
        return 1
    
    if not instances:
        print("❌ No instances found", file=sys.stderr)
        return 1
    
    print(f"\n📋 Removing tags from {len(instances)} instance(s):")
    print(f"   Keys: {keys}")
    for inst in instances:
        print(f"   - {inst.get('InstanceName', inst['InstanceId'])}")
    
    # Confirmation
    if not args.force:
        confirm = input(f"\nProceed? (y/N): ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            return 0
    
    # Process instances
    success_count = 0
    fail_count = 0
    
    for inst in instances:
        instance_id = inst['InstanceId']
        success, message = update_instance_tags(client, instance_id, remove_keys=keys)
        
        if success:
            print(f"  ✅ {instance_id}")
            success_count += 1
        else:
            print(f"  ❌ {instance_id}: {message}")
            fail_count += 1
    
    print(f"\n📊 Results: {success_count} succeeded, {fail_count} failed")
    return 0 if fail_count == 0 else 1


def cmd_filter(args):
    """Filter instances by tags."""
    client = create_client(args.region)
    workspace_id = args.workspace or get_workspace_id()
    
    # Parse filter
    filter_tags = parse_tags(args.filter)
    has_key = args.has_key
    
    if not filter_tags and not has_key:
        print("❌ Specify tag filter (key=value) or --has-key", file=sys.stderr)
        return 1
    
    # Get all instances
    all_instances = get_all_instances(client, workspace_id)
    
    # Filter
    results = []
    for inst in all_instances:
        labels = inst.get('Labels', {})
        
        # Check has-key
        if has_key:
            if has_key not in labels:
                continue
        
        # Check tag values
        match = True
        for key, value in filter_tags.items():
            if key not in labels:
                match = False
                break
            if value and labels[key] != value:
                match = False
                break
        
        if match:
            results.append(inst)
    
    if not results:
        print(f"\n⚠️  No instances match the filter")
        return 0
    
    # Output
    if args.format == 'json':
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(f"\n📋 Found {len(results)} matching instance(s):\n")
        
        headers = ['Instance ID', 'Name', 'Status', 'Matching Tags']
        rows = []
        
        for inst in results:
            labels = inst.get('Labels', {})
            
            # Show matching tags
            matching = []
            for key, value in filter_tags.items():
                if key in labels:
                    matching.append(f"{key}={labels[key]}")
            if has_key and has_key in labels:
                matching.append(f"{has_key}={labels[has_key]}")
            
            rows.append([
                inst['InstanceId'],
                inst['InstanceName'],
                inst['Status'],
                ', '.join(matching) or '-'
            ])
        
        print_table(headers, rows)
    
    return 0


def cmd_export(args):
    """Export all instance tags."""
    client = create_client(args.region)
    workspace_id = args.workspace or get_workspace_id()
    
    # Get all instances
    instances = get_all_instances(client, workspace_id)
    
    if not instances:
        print("❌ No instances found", file=sys.stderr)
        return 1
    
    # Collect all unique tag keys
    all_keys = set()
    for inst in instances:
        all_keys.update(inst.get('Labels', {}).keys())
    all_keys = sorted(all_keys)
    
    if args.format == 'json':
        output = {
            'export_time': datetime.now().isoformat(),
            'workspace_id': workspace_id,
            'total_instances': len(instances),
            'instances': [
                {
                    'InstanceId': i['InstanceId'],
                    'InstanceName': i['InstanceName'],
                    'Status': i['Status'],
                    'Tags': i.get('Labels', {})
                }
                for i in instances
            ],
            'tag_keys': all_keys
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    
    elif args.format == 'csv':
        # CSV output
        headers = ['InstanceId', 'InstanceName', 'Status'] + all_keys
        writer = csv.writer(sys.stdout)
        writer.writerow(headers)
        
        for inst in instances:
            labels = inst.get('Labels', {})
            row = [
                inst['InstanceId'],
                inst['InstanceName'],
                inst['Status']
            ]
            for key in all_keys:
                row.append(labels.get(key, ''))
            writer.writerow(row)
    
    else:  # table
        print(f"\n📋 Instance Tags Export")
        print(f"   Workspace: {workspace_id}")
        print(f"   Instances: {len(instances)}")
        print(f"   Unique tag keys: {len(all_keys)}\n")
        
        headers = ['Instance ID', 'Name', 'Status', 'Tags']
        rows = []
        
        for inst in instances:
            labels = inst.get('Labels', {})
            tags_str = ', '.join(f"{k}={v}" for k, v in sorted(labels.items())) if labels else '-'
            
            rows.append([
                inst['InstanceId'],
                inst['InstanceName'],
                inst['Status'],
                tags_str[:50] + '...' if len(tags_str) > 50 else tags_str
            ])
        
        print_table(headers, rows)
        
        if all_keys:
            print(f"\n🏷️  Available tag keys: {', '.join(all_keys)}")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='PAI-DSW Instance Tag Management',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Tag Format:
    key=value,key2=value2    - Simple format
    '{"key":"value"}'        - JSON format

Examples:
    # List tags
    python manage_tags.py list dsw-123456

    # Add tags
    python manage_tags.py add dsw-123456 env=prod,team=ml

    # Remove tags
    python manage_tags.py remove dsw-123456 env,team

    # Batch add tags
    python manage_tags.py batch-add env=prod --instances dsw-123,dsw-456

    # Filter by tags
    python manage_tags.py filter env=prod
    python manage_tags.py filter env --has-key

    # Export all tags
    python manage_tags.py export --format json
"""
    )
    
    parser.add_argument('--region', default=os.getenv('ALIBABA_CLOUD_REGION_ID'),
                        help='Region ID')
    parser.add_argument('--workspace', default=os.getenv('PAI_WORKSPACE_ID'),
                        help='Workspace ID')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # list command
    list_parser = subparsers.add_parser('list', help='List tags on an instance')
    list_parser.add_argument('instance', help='Instance ID')
    list_parser.add_argument('--format', choices=['table', 'json'], default='table',
                            help='Output format')
    
    # add command
    add_parser = subparsers.add_parser('add', help='Add tags to an instance')
    add_parser.add_argument('instance', help='Instance ID')
    add_parser.add_argument('tags', help='Tags to add (key=value,key2=value2)')
    add_parser.add_argument('--force', '-f', action='store_true', help='Skip confirmation')
    add_parser.add_argument('--quiet', '-q', action='store_true', help='Minimal output')
    
    # remove command
    remove_parser = subparsers.add_parser('remove', help='Remove tags from an instance')
    remove_parser.add_argument('instance', help='Instance ID')
    remove_parser.add_argument('keys', help='Tag keys to remove (comma-separated)')
    remove_parser.add_argument('--force', '-f', action='store_true', help='Skip confirmation')
    remove_parser.add_argument('--quiet', '-q', action='store_true', help='Minimal output')
    
    # set command
    set_parser = subparsers.add_parser('set', help='Set (replace) all tags on an instance')
    set_parser.add_argument('instance', help='Instance ID')
    set_parser.add_argument('tags', help='New tags (key=value,key2=value2, or empty to clear)')
    set_parser.add_argument('--force', '-f', action='store_true', help='Skip confirmation')
    set_parser.add_argument('--quiet', '-q', action='store_true', help='Minimal output')
    
    # batch-add command
    batch_add_parser = subparsers.add_parser('batch-add', help='Add tags to multiple instances')
    batch_add_parser.add_argument('tags', help='Tags to add')
    batch_add_parser.add_argument('--instances', '-i', help='Instance IDs (comma-separated)')
    batch_add_parser.add_argument('--query', '-q', help='Filter instances by name/ID')
    batch_add_parser.add_argument('--force', '-f', action='store_true', help='Skip confirmation')
    
    # batch-remove command
    batch_remove_parser = subparsers.add_parser('batch-remove', help='Remove tags from multiple instances')
    batch_remove_parser.add_argument('keys', help='Tag keys to remove')
    batch_remove_parser.add_argument('--instances', '-i', help='Instance IDs (comma-separated)')
    batch_remove_parser.add_argument('--query', '-q', help='Filter instances by name/ID')
    batch_remove_parser.add_argument('--force', '-f', action='store_true', help='Skip confirmation')
    
    # filter command
    filter_parser = subparsers.add_parser('filter', help='Filter instances by tags')
    filter_parser.add_argument('filter', help='Tag filter (key=value or just key)')
    filter_parser.add_argument('--has-key', help='Match instances that have this key')
    filter_parser.add_argument('--format', choices=['table', 'json'], default='table',
                              help='Output format')
    
    # export command
    export_parser = subparsers.add_parser('export', help='Export all instance tags')
    export_parser.add_argument('--format', choices=['table', 'json', 'csv'], default='table',
                              help='Output format')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    commands = {
        'list': cmd_list,
        'add': cmd_add,
        'remove': cmd_remove,
        'set': cmd_set,
        'batch-add': cmd_batch_add,
        'batch-remove': cmd_batch_remove,
        'filter': cmd_filter,
        'export': cmd_export,
    }
    
    cmd_func = commands.get(args.command)
    if cmd_func:
        return cmd_func(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())