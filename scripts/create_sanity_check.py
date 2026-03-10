#!/usr/bin/env python3
"""
Create sanity check task for PAI-DSW instance.

Usage:
    python create_sanity_check.py <instance_id> [options]

Options:
    --region <region>     Region ID
    --help                Show this help message
"""

import os
import sys
import argparse

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from dsw_utils import create_client
from alibabacloud_pai_dsw20220101 import models as dsw_models


def create_sanity_check(instance_id: str, region_id: str = None) -> dict:
    """Create sanity check task for a DSW instance."""
    client = create_client(region_id)
    
    request = dsw_models.CreateSanityCheckTaskRequest()
    request.instance_id = instance_id
    
    response = client.create_sanity_check_task(request)
    
    return {
        'instance_id': instance_id,
        'task_id': response.body.task_id if response.body else None,
        'success': response.status_code == 200,
    }


def main():
    parser = argparse.ArgumentParser(description='Create sanity check task for PAI-DSW instance')
    parser.add_argument('instance_id', help='Instance ID')
    parser.add_argument('--region', default=os.getenv('ALIBABA_CLOUD_REGION_ID'),
                        help='Region ID')
    
    args = parser.parse_args()
    
    try:
        print(f"\n🔍 Creating sanity check task for: {args.instance_id}")
        result = create_sanity_check(args.instance_id, args.region)
        
        if result['success']:
            print(f"✅ Sanity check task created!")
            print(f"   Task ID: {result['task_id']}")
        else:
            print(f"❌ Failed to create sanity check task")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()