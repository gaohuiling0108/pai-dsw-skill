#!/usr/bin/env python3
"""
Delete a PAI-DSW instance.

Usage:
    python delete_instance.py <instance_id> [options]

Options:
    --region <region>       Region ID (default: from environment)
    --force                  Skip confirmation prompt
    --help                  Show this help message

Environment Variables:
    ALIBABA_CLOUD_ACCESS_KEY_ID     - Access Key ID
    ALIBABA_CLOUD_ACCESS_KEY_SECRET - Access Key Secret  
    ALIBABA_CLOUD_SECURITY_TOKEN    - Security Token (for STS)
    ALIBABA_CLOUD_REGION_ID         - Default region

Warning:
    Deleting an instance is irreversible. All data will be lost.
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


def delete_instance(instance_id: str, region_id: str = None) -> dict:
    """
    Delete a DSW instance.
    
    Args:
        instance_id: Instance ID to delete
        region_id: Region ID
    
    Returns:
        Response dictionary
    """
    client = create_client(region_id)
    
    request = dsw_models.DeleteInstanceRequest()
    response = client.delete_instance(instance_id, request)
    
    return {
        'success': True,
        'instance_id': instance_id,
        'request_id': response.body.request_id if response.body else None
    }


def main():
    parser = argparse.ArgumentParser(description='Delete a PAI-DSW instance')
    parser.add_argument('instance_id', help='Instance ID to delete')
    parser.add_argument('--region', default=os.getenv('ALIBABA_CLOUD_REGION_ID'),
                        help='Region ID (default: from environment)')
    parser.add_argument('--force', action='store_true',
                        help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    # Confirmation prompt (unless --force)
    if not args.force:
        print(f"\n🚨 WARNING: You are about to DELETE instance {args.instance_id}")
        print("This action is IRREVERSIBLE. All data will be permanently lost!")
        try:
            response = input("\nType 'delete' to confirm: ")
            if response.lower() != 'delete':
                print("Operation cancelled.")
                sys.exit(0)
        except EOFError:
            # Non-interactive mode
            print("\nUse --force to skip confirmation in non-interactive mode.")
            sys.exit(1)
    
    try:
        result = delete_instance(args.instance_id, args.region)
        print(f"✅ Instance {args.instance_id} deletion initiated successfully")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ Error deleting instance: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()