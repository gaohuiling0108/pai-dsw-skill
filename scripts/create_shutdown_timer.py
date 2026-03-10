#!/usr/bin/env python3
"""
Create shutdown timer for PAI-DSW instance.

Schedule an automatic shutdown time for the instance.

Usage:
    python create_shutdown_timer.py <instance_id> --time <datetime> [options]

Options:
    --time <datetime>     Shutdown time (ISO 8601 format or relative)
    --region <region>     Region ID
    --help                Show this help message

Examples:
    # Shutdown at specific time
    python create_shutdown_timer.py dsw-123456 --time "2026-03-06T22:00:00+08:00"
    
    # Shutdown in 2 hours (relative time)
    python create_shutdown_timer.py dsw-123456 --time "+2h"
"""

import os
import sys
import argparse
from datetime import datetime, timedelta

# Add script directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from dsw_utils import create_client
from alibabacloud_pai_dsw20220101 import models as dsw_models


def parse_time(time_str: str) -> datetime:
    """Parse time string to datetime."""
    # Try relative time (e.g., "+2h", "+30m", "+1d")
    if time_str.startswith('+'):
        unit = time_str[-1].lower()
        value = int(time_str[1:-1])
        
        if unit == 'h':
            return datetime.now() + timedelta(hours=value)
        elif unit == 'm':
            return datetime.now() + timedelta(minutes=value)
        elif unit == 'd':
            return datetime.now() + timedelta(days=value)
        else:
            raise ValueError(f"Unknown time unit: {unit}")
    
    # Try ISO 8601 format
    try:
        return datetime.fromisoformat(time_str)
    except ValueError:
        raise ValueError(f"Invalid time format: {time_str}")


def create_shutdown_timer(
    instance_id: str,
    shutdown_time: datetime,
    region_id: str = None
) -> dict:
    """
    Create shutdown timer for a DSW instance.
    
    Args:
        instance_id: Instance ID
        shutdown_time: When to shutdown
        region_id: Region ID
    
    Returns:
        Result dictionary
    """
    client = create_client(region_id)
    
    request = dsw_models.CreateInstanceShutdownTimerRequest()
    request.instance_id = instance_id
    request.due_time = shutdown_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    response = client.create_instance_shutdown_timer(instance_id, request)
    
    return {
        'instance_id': instance_id,
        'shutdown_time': shutdown_time.isoformat(),
        'success': response.status_code == 200,
        'request_id': response.body.request_id if response.body else None
    }


def main():
    parser = argparse.ArgumentParser(
        description='Create shutdown timer for PAI-DSW instance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Time formats:
  - ISO 8601: "2026-03-06T22:00:00+08:00"
  - Relative: "+2h" (2 hours), "+30m" (30 minutes), "+1d" (1 day)

Examples:
  # Shutdown at specific time
  python create_shutdown_timer.py dsw-123456 --time "2026-03-06T22:00:00+08:00"
  
  # Shutdown in 2 hours
  python create_shutdown_timer.py dsw-123456 --time "+2h"
"""
    )
    parser.add_argument('instance_id', help='Instance ID')
    parser.add_argument('--time', required=True, help='Shutdown time (ISO 8601 or relative like +2h)')
    parser.add_argument('--region', default=os.getenv('ALIBABA_CLOUD_REGION_ID'),
                        help='Region ID')
    
    args = parser.parse_args()
    
    try:
        shutdown_time = parse_time(args.time)
        
        print(f"\n⏰ Creating shutdown timer for instance: {args.instance_id}")
        print(f"   Shutdown scheduled at: {shutdown_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        result = create_shutdown_timer(
            instance_id=args.instance_id,
            shutdown_time=shutdown_time,
            region_id=args.region
        )
        
        if result['success']:
            print(f"\n✅ Shutdown timer created successfully!")
            print(f"   Instance will shutdown at: {shutdown_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"\n❌ Failed to create shutdown timer", file=sys.stderr)
            sys.exit(1)
            
    except ValueError as e:
        print(f"❌ Invalid time format: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()