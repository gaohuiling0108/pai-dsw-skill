#!/usr/bin/env python3
"""
Get detailed information of a PAI-DSW instance.

Usage:
    python get_instance.py <instance_id> [options]

Options:
    --region <region>       Region ID (default: from environment)
    --help                  Show this help message

Environment Variables:
    ALIBABA_CLOUD_ACCESS_KEY_ID     - Access Key ID
    ALIBABA_CLOUD_ACCESS_KEY_SECRET - Access Key Secret  
    ALIBABA_CLOUD_SECURITY_TOKEN    - Security Token (for STS)
    ALIBABA_CLOUD_REGION_ID         - Default region
"""

import os
import sys
import json
import argparse

# Add script directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from dsw_utils import create_client, filter_response, INSTANCE_DETAIL_FIELDS
from alibabacloud_pai_dsw20220101 import models as dsw_models


def get_instance(instance_id: str, region_id: str = None, detail_level: str = 'full') -> dict:
    """
    Get detailed information of a DSW instance.
    
    Args:
        instance_id: Instance ID
        region_id: Region ID
        detail_level: Level of detail to return.
            - 'brief': Only instance_id, instance_name, status
            - 'summary': Core fields (spec, GPU, CPU, memory, creation_time)
            - 'full': All fields (default)
    
    Returns:
        Instance details dictionary (None values stripped)
    """
    client = create_client(region_id)
    
    request = dsw_models.GetInstanceRequest()
    response = client.get_instance(instance_id, request)
    
    if response.body:
        inst = response.body
        result = {
            'instance_id': inst.instance_id,
            'instance_name': inst.instance_name,
            'status': inst.status,
            'instance_type': getattr(inst, 'instance_type', None),
            'ecs_spec': getattr(inst, 'ecs_spec', None),
            'image_url': getattr(inst, 'image_url', None),
            'workspace_id': getattr(inst, 'workspace_id', None),
            'region_id': getattr(inst, 'region_id', None),
            'gpu_count': getattr(inst, 'gpu_count', 0),
            'gpu_type': getattr(inst, 'gpu_type', None),
            'cpu': getattr(inst, 'cpu', 0),
            'memory': getattr(inst, 'memory', 0),
            'vpc_id': getattr(inst, 'vpc_id', None),
            'vswitch_id': getattr(inst, 'vswitch_id', None),
            'security_group_id': getattr(inst, 'security_group_id', None),
            'creation_time': getattr(inst, 'creation_time', None),
            'modified_time': getattr(inst, 'modified_time', None),
            'payment_type': getattr(inst, 'payment_type', None),
            'spot_type': getattr(inst, 'spot_type', None),
            'idle_instance_culler': getattr(inst, 'idle_instance_culler', None),
        }
        fields = INSTANCE_DETAIL_FIELDS.get(detail_level)
        return filter_response(result, fields)
    
    return None


def main():
    parser = argparse.ArgumentParser(description='Get PAI-DSW instance details')
    parser.add_argument('instance_id', help='Instance ID')
    parser.add_argument('--region', default=os.getenv('ALIBABA_CLOUD_REGION_ID'),
                        help='Region ID (default: from environment)')
    parser.add_argument('--format', choices=['table', 'json'], default='table',
                        help='Output format (default: table)')
    parser.add_argument('--detail', choices=['brief', 'summary', 'full'], default='full',
                        help='Detail level: brief/summary/full (default: full)')
    
    args = parser.parse_args()
    
    try:
        result = get_instance(args.instance_id, args.region, detail_level=args.detail)
        
        if result:
            if args.format == 'json':
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(f"\n{'='*60}")
                print(f"  Instance: {result['instance_id']}")
                print(f"{'='*60}")
                print(f"  Name:           {result['instance_name']}")
                print(f"  Status:         {result['status']}")
                print(f"  Instance Type:  {result['instance_type'] or 'N/A'}")
                print(f"  ECS Spec:       {result['ecs_spec'] or 'N/A'}")
                print(f"  CPU:            {result['cpu']} cores")
                print(f"  Memory:         {result['memory']} GB")
                print(f"  GPU:            {result['gpu_count']} x {result['gpu_type'] or 'N/A'}")
                print(f"  Image:          {result['image_url'] or 'N/A'}")
                print(f"  Workspace:      {result['workspace_id']}")
                print(f"  Region:         {result['region_id']}")
                print(f"  VPC:            {result['vpc_id'] or 'N/A'}")
                print(f"  Created:        {result['creation_time']}")
                print(f"  Modified:       {result['modified_time']}")
                print(f"  Payment:        {result['payment_type'] or 'N/A'}")
                print(f"{'='*60}\n")
        else:
            print(f"Instance {args.instance_id} not found", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()