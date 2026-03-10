#!/usr/bin/env python3
"""
Get instance events for PAI-DSW instance.

Usage:
    python get_instance_events.py <instance_id> [options]

Options:
    --region <region>     Region ID
    --format <format>     Output format: table, json (default: table)
    --help                Show this help message
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


def get_instance_events(instance_id: str, region_id: str = None) -> list:
    """
    Get events for a DSW instance.
    
    Args:
        instance_id: Instance ID
        region_id: Region ID
    
    Returns:
        List of events
    """
    client = create_client(region_id)
    
    request = dsw_models.GetInstanceEventsRequest()
    response = client.get_instance_events(instance_id, request)
    
    events = []
    if response.body and response.body.events:
        for event in response.body.events:
            events.append({
                'event_type': getattr(event, 'event_type', None),
                'message': getattr(event, 'message', None),
                'reason': getattr(event, 'reason', None),
                'gmt_create_time': getattr(event, 'gmt_create_time', None),
            })
    
    return events


def main():
    parser = argparse.ArgumentParser(description='Get PAI-DSW instance events')
    parser.add_argument('instance_id', help='Instance ID')
    parser.add_argument('--region', default=os.getenv('ALIBABA_CLOUD_REGION_ID'),
                        help='Region ID')
    parser.add_argument('--format', choices=['table', 'json'], default='table',
                        help='Output format')
    
    args = parser.parse_args()
    
    try:
        events = get_instance_events(
            instance_id=args.instance_id,
            region_id=args.region
        )
        
        if args.format == 'json':
            print(json.dumps(events, indent=2, ensure_ascii=False))
        else:
            print(f"\n{'='*80}")
            print(f"  Instance Events: {args.instance_id}")
            print(f"{'='*80}\n")
            
            if events:
                for event in events:
                    print(f"  [{event.get('gmt_create_time', 'N/A')}]")
                    print(f"    Type: {event.get('event_type', 'N/A')}")
                    print(f"    Reason: {event.get('reason', 'N/A')}")
                    print(f"    Message: {event.get('message', 'N/A')}")
                    print()
            else:
                print("  No events found.")
            
            print(f"{'='*80}\n")
            
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()