#!/usr/bin/env python3
"""
Update a PAI-DSW instance (change specs, labels, etc).

Usage:
    python update_instance.py <instance_id> [options]

Options:
    --spec <ecs_spec>       New ECS specification (e.g., ecs.g6.large)
    --cpu <cores>           CPU cores
    --memory <gb>           Memory in GB
    --gpu <count>           GPU count
    --labels <json>         Labels in JSON format
    --region <region>       Region ID
    --force                 Skip confirmation
    --help                  Show this help message

Examples:
    # Upgrade instance spec
    python update_instance.py dsw-123456 --spec ecs.g6.xlarge

    # Update labels
    python update_instance.py dsw-123456 --labels '{"env":"prod","team":"ml"}'
"""

import os
import sys
import json
import argparse

# Add script directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from dsw_utils import create_client
from alibabacloud_pai_dsw20220101 import models as dsw_models


def update_instance(
    instance_id: str,
    ecs_spec: str = None,
    cpu: int = None,
    memory: int = None,
    gpu: int = None,
    labels: dict = None,
    region_id: str = None
) -> dict:
    """
    Update a DSW instance.
    
    Args:
        instance_id: Instance ID
        ecs_spec: New ECS specification
        cpu: CPU cores
        memory: Memory in GB
        gpu: GPU count
        labels: Instance labels
        region_id: Region ID
    
    Returns:
        Update result
    """
    client = create_client(region_id)
    
    request = dsw_models.UpdateInstanceRequest()
    
    # Set resource specs
    if ecs_spec or cpu or memory or gpu:
        resource = dsw_models.UpdateInstanceRequestRequestedResource()
        if ecs_spec:
            resource.ecs_spec = ecs_spec
        if cpu:
            resource.cpu = cpu
        if memory:
            resource.memory = memory
        if gpu:
            resource.gpu_count = gpu
        request.requested_resource = resource
    
    # Set labels
    if labels:
        label_list = [
            dsw_models.UpdateInstanceRequestLabels(
                key=k,
                value=v
            ) for k, v in labels.items()
        ]
        request.labels = label_list
    
    response = client.update_instance(instance_id, request)
    
    return {
        'instance_id': instance_id,
        'request_id': response.body.request_id if response.body else None,
        'success': response.status_code == 200
    }


def main():
    parser = argparse.ArgumentParser(description='Update a PAI-DSW instance')
    parser.add_argument('instance_id', help='Instance ID to update')
    parser.add_argument('--spec', dest='ecs_spec', help='New ECS specification')
    parser.add_argument('--cpu', type=int, help='CPU cores')
    parser.add_argument('--memory', type=int, help='Memory in GB')
    parser.add_argument('--gpu', type=int, help='GPU count')
    parser.add_argument('--labels', help='Labels in JSON format')
    parser.add_argument('--region', default=os.getenv('ALIBABA_CLOUD_REGION_ID'),
                        help='Region ID')
    parser.add_argument('--force', action='store_true', help='Skip confirmation')
    
    args = parser.parse_args()
    
    # Parse labels
    labels = None
    if args.labels:
        try:
            labels = json.loads(args.labels)
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON for labels: {args.labels}", file=sys.stderr)
            sys.exit(1)
    
    # Check if any update specified
    if not any([args.ecs_spec, args.cpu, args.memory, args.gpu, labels]):
        print("❌ No update specified. Use --spec, --cpu, --memory, --gpu, or --labels", file=sys.stderr)
        sys.exit(1)
    
    # Confirmation
    if not args.force:
        print(f"\n⚠️  About to update instance: {args.instance_id}")
        if args.ecs_spec:
            print(f"   ECS Spec: {args.ecs_spec}")
        if args.cpu:
            print(f"   CPU: {args.cpu} cores")
        if args.memory:
            print(f"   Memory: {args.memory} GB")
        if args.gpu:
            print(f"   GPU: {args.gpu}")
        if labels:
            print(f"   Labels: {labels}")
        
        confirm = input("\nProceed? (y/N): ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            sys.exit(0)
    
    try:
        result = update_instance(
            instance_id=args.instance_id,
            ecs_spec=args.ecs_spec,
            cpu=args.cpu,
            memory=args.memory,
            gpu=args.gpu,
            labels=labels,
            region_id=args.region
        )
        
        if result['success']:
            print(f"\n✅ Instance updated successfully!")
            print(f"   Instance ID: {result['instance_id']}")
            print(f"   Request ID: {result['request_id']}")
        else:
            print(f"\n❌ Failed to update instance", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()