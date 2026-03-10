#!/usr/bin/env python3
"""
List all DSW instances in a workspace.

Usage:
    python list_instances.py [options]

Options:
    --region <region>       Region ID (default: from environment or cn-hangzhou)
    --workspace <id>        Workspace ID (default: from environment)
    --format <json|table>   Output format (default: json)
    --help                  Show this help message

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

# Add script directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from dsw_utils import create_client, get_workspace_id
from alibabacloud_pai_dsw20220101 import models as dsw_models


def list_instances(client=None, region_id: str = None, workspace_id: str = None, format: str = 'json') -> list:
    """
    List all DSW instances.
    
    Args:
        client: PAI-DSW client (optional, will create if not provided)
        region_id: Region ID
        workspace_id: Workspace ID
        format: Output format ('json' or 'table')
    
    Returns:
        List of instance dictionaries (or prints table if format='table')
    """
    if client is None:
        client = create_client(region_id)
    
    if workspace_id is None:
        workspace_id = get_workspace_id()
    
    request = dsw_models.ListInstancesRequest(workspace_id=workspace_id)
    response = client.list_instances(request)
    
    instances = []
    if response.body and response.body.instances:
        for inst in response.body.instances:
            instances.append({
                'InstanceId': inst.instance_id,
                'InstanceName': inst.instance_name,
                'Status': inst.status,
                'InstanceType': getattr(inst, 'instance_type', None),
                'EcsSpec': getattr(inst, 'ecs_spec', None),
                'ImageUrl': getattr(inst, 'image_url', None),
                'CreationTime': getattr(inst, 'creation_time', None),
                'Labels': getattr(inst, 'labels', {}),
            })
    
    if format == 'table':
        print(f"\n{'Instance ID':<40} {'Name':<30} {'Status':<15} {'Type':<20}")
        print("-" * 105)
        for inst in instances:
            print(f"{inst['InstanceId']:<40} {inst['InstanceName']:<30} {inst['Status']:<15} {inst['InstanceType'] or 'N/A':<20}")
        return instances
    
    return instances


def main():
    parser = argparse.ArgumentParser(description='List PAI-DSW instances')
    parser.add_argument('--region', default=os.getenv('ALIBABA_CLOUD_REGION_ID'),
                        help='Region ID (default: from environment)')
    parser.add_argument('--workspace', default=os.getenv('PAI_WORKSPACE_ID'),
                        help='Workspace ID (default: from environment)')
    parser.add_argument('--format', choices=['json', 'table'], default='table',
                        help='Output format (default: table)')
    
    args = parser.parse_args()
    
    try:
        client = create_client(args.region)
        instances = list_instances(client=client, workspace_id=args.workspace, format=args.format)
        
        if args.format == 'json':
            print(json.dumps(instances, indent=2, ensure_ascii=False))
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()