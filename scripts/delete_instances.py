#!/usr/bin/env python3
"""
Batch delete PAI-DSW instances.

⚠️ WARNING: This operation is irreversible!

Usage:
    python delete_instances.py <instance_id1> <instance_id2> ... [options]

Options:
    --region <region>     Region ID
    --force               Skip confirmation
    --help                Show this help message

Examples:
    # Delete multiple instances (with confirmation)
    python delete_instances.py dsw-123 dsw-456

    # Force delete without confirmation
    python delete_instances.py dsw-123 dsw-456 --force
"""

import os
import sys
import argparse

# Add script directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from dsw_utils import create_client
from alibabacloud_pai_dsw20220101 import models as dsw_models


def delete_instances(instance_ids: list, region_id: str = None) -> dict:
    """
    Delete multiple DSW instances.
    
    Args:
        instance_ids: List of instance IDs
        region_id: Region ID
    
    Returns:
        Result dictionary
    """
    client = create_client(region_id)
    
    request = dsw_models.DeleteInstancesRequest()
    request.instance_ids = instance_ids
    
    response = client.delete_instances(request)
    
    return {
        'success': response.status_code == 200,
        'deleted_count': len(instance_ids),
        'request_id': response.body.request_id if response.body else None
    }


def main():
    parser = argparse.ArgumentParser(
        description='Batch delete PAI-DSW instances (IRREVERSIBLE!)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
⚠️  WARNING: This operation is IRREVERSIBLE!
All data in the instances will be permanently deleted.
"""
    )
    parser.add_argument('instance_ids', nargs='+', help='Instance IDs to delete')
    parser.add_argument('--region', default=os.getenv('ALIBABA_CLOUD_REGION_ID'),
                        help='Region ID')
    parser.add_argument('--force', action='store_true', help='Skip confirmation')
    
    args = parser.parse_args()
    
    # Confirmation
    if not args.force:
        print(f"\n⚠️  WARNING: About to DELETE {len(args.instance_ids)} instances!")
        print("    This operation is IRREVERSIBLE!\n")
        for iid in args.instance_ids:
            print(f"   - {iid}")
        
        print("\nType 'delete' to confirm: ", end='')
        confirm = input()
        if confirm != 'delete':
            print("Cancelled.")
            sys.exit(0)
    
    try:
        print(f"\nDeleting {len(args.instance_ids)} instances...")
        
        result = delete_instances(
            instance_ids=args.instance_ids,
            region_id=args.region
        )
        
        if result['success']:
            print(f"\n✅ Successfully deleted {result['deleted_count']} instances!")
        else:
            print(f"\n❌ Failed to delete instances", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()