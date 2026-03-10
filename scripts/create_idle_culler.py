#!/usr/bin/env python3
"""
Create idle instance culler for PAI-DSW instance.

Automatically stops the instance after it has been idle for a specified time.
This helps reduce costs by preventing unused instances from running.

Usage:
    python create_idle_culler.py <instance_id> --idle-minutes <minutes> [options]

Options:
    --idle-minutes <minutes>  Idle time before stopping (default: 30)
    --region <region>         Region ID
    --help                    Show this help message

Examples:
    # Stop after 30 minutes of idle
    python create_idle_culler.py dsw-123456 --idle-minutes 30

    # Stop after 1 hour of idle
    python create_idle_culler.py dsw-123456 --idle-minutes 60
"""

import os
import sys
import argparse

# Add script directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from dsw_utils import create_client
from alibabacloud_pai_dsw20220101 import models as dsw_models


def create_idle_culler(
    instance_id: str,
    idle_minutes: int = 30,
    region_id: str = None
) -> dict:
    """
    Create idle instance culler for a DSW instance.
    
    Args:
        instance_id: Instance ID
        idle_minutes: Minutes of idle time before stopping
        region_id: Region ID
    
    Returns:
        Result dictionary
    """
    client = create_client(region_id)
    
    request = dsw_models.CreateIdleInstanceCullerRequest()
    request.instance_id = instance_id
    request.idle_time_in_minutes = idle_minutes
    
    response = client.create_idle_instance_culler(instance_id, request)
    
    return {
        'instance_id': instance_id,
        'idle_minutes': idle_minutes,
        'success': response.status_code == 200,
        'request_id': response.body.request_id if response.body else None
    }


def main():
    parser = argparse.ArgumentParser(
        description='Create idle instance culler for PAI-DSW instance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Stop after 30 minutes of idle
  python create_idle_culler.py dsw-123456 --idle-minutes 30

  # Stop after 1 hour of idle
  python create_idle_culler.py dsw-123456 --idle-minutes 60
"""
    )
    parser.add_argument('instance_id', help='Instance ID')
    parser.add_argument('--idle-minutes', type=int, default=30,
                        help='Idle time before stopping in minutes (default: 30)')
    parser.add_argument('--region', default=os.getenv('ALIBABA_CLOUD_REGION_ID'),
                        help='Region ID')
    
    args = parser.parse_args()
    
    try:
        print(f"\n⏱️  Creating idle culler for instance: {args.instance_id}")
        print(f"   Will stop after {args.idle_minutes} minutes of idle time")
        
        result = create_idle_culler(
            instance_id=args.instance_id,
            idle_minutes=args.idle_minutes,
            region_id=args.region
        )
        
        if result['success']:
            print(f"\n✅ Idle culler created successfully!")
            print(f"   Instance will automatically stop after {args.idle_minutes} minutes of idle")
        else:
            print(f"\n❌ Failed to create idle culler", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()