#!/usr/bin/env python3
"""
Start a PAI-DSW instance.

Usage:
    python start_instance.py <instance_id> [options]

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

from dsw_utils import create_client
from alibabacloud_pai_dsw20220101 import models as dsw_models


def start_instance(instance_id: str, region_id: str = None) -> dict:
    """
    Start a DSW instance.
    
    Args:
        instance_id: Instance ID to start
        region_id: Region ID
    
    Returns:
        Response dictionary
    """
    client = create_client(region_id)
    
    # start_instance only needs instance_id, no request object
    response = client.start_instance(instance_id)
    
    return {
        'success': True,
        'instance_id': instance_id,
        'request_id': response.body.request_id if response.body else None
    }


def main():
    parser = argparse.ArgumentParser(description='Start a PAI-DSW instance')
    parser.add_argument('instance_id', help='Instance ID to start')
    parser.add_argument('--region', default=os.getenv('ALIBABA_CLOUD_REGION_ID'),
                        help='Region ID (default: from environment)')
    
    args = parser.parse_args()
    
    try:
        result = start_instance(args.instance_id, args.region)
        print(f"✅ Instance {args.instance_id} start initiated successfully")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ Error starting instance: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()