#!/usr/bin/env python3
"""
Batch stop PAI-DSW instances.

Usage:
    python stop_instances.py <instance_id1> <instance_id2> ... [options]

Options:
    --region <region>     Region ID
    --force               Skip confirmation
    --help                Show this help message

Examples:
    # Stop multiple instances
    python stop_instances.py dsw-123 dsw-456 dsw-789

    # Force stop without confirmation
    python stop_instances.py dsw-123 dsw-456 --force
"""

import os
import sys
import argparse

# Add script directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from dsw_utils import create_client
from alibabacloud_pai_dsw20220101 import models as dsw_models


def stop_instances(instance_ids: list, region_id: str = None) -> dict:
    """
    Stop multiple DSW instances.
    
    Args:
        instance_ids: List of instance IDs
        region_id: Region ID
    
    Returns:
        Result dictionary
    """
    client = create_client(region_id)
    
    request = dsw_models.StopInstancesRequest()
    request.instance_ids = instance_ids
    
    response = client.stop_instances(request)
    
    return {
        'success': response.status_code == 200,
        'stopped_count': len(instance_ids),
        'request_id': response.body.request_id if response.body else None
    }


def main():
    parser = argparse.ArgumentParser(description='Batch stop PAI-DSW instances')
    parser.add_argument('instance_ids', nargs='+', help='Instance IDs to stop')
    parser.add_argument('--region', default=os.getenv('ALIBABA_CLOUD_REGION_ID'),
                        help='Region ID')
    parser.add_argument('--force', action='store_true', help='Skip confirmation')
    
    args = parser.parse_args()
    
    # Confirmation
    if not args.force:
        print(f"\n⚠️  About to stop {len(args.instance_ids)} instances:")
        for iid in args.instance_ids:
            print(f"   - {iid}")
        
        confirm = input("\nProceed? (y/N): ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            sys.exit(0)
    
    try:
        print(f"\nStopping {len(args.instance_ids)} instances...")
        
        result = stop_instances(
            instance_ids=args.instance_ids,
            region_id=args.region
        )
        
        if result['success']:
            print(f"\n✅ Successfully stopped {result['stopped_count']} instances!")
        else:
            print(f"\n❌ Failed to stop instances", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()