#!/usr/bin/env python3
"""
List system logs for PAI-DSW instance.

Usage:
    python list_system_logs.py <instance_id> [options]

Options:
    --region <region>     Region ID
    --limit <n>           Number of logs to show (default: 50)
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


def list_system_logs(instance_id: str, region_id: str = None, limit: int = 50) -> list:
    """
    List system logs for a DSW instance.
    
    Args:
        instance_id: Instance ID
        region_id: Region ID
        limit: Maximum number of logs
    
    Returns:
        List of log entries
    """
    client = create_client(region_id)
    
    request = dsw_models.ListSystemLogsRequest()
    request.instance_id = instance_id
    
    response = client.list_system_logs(request)
    
    logs = []
    if response.body and response.body.logs:
        for log in response.body.logs[:limit]:
            logs.append({
                'timestamp': getattr(log, 'timestamp', None),
                'level': getattr(log, 'level', None),
                'content': getattr(log, 'content', None),
            })
    
    return logs


def main():
    parser = argparse.ArgumentParser(description='List PAI-DSW instance system logs')
    parser.add_argument('instance_id', help='Instance ID')
    parser.add_argument('--region', default=os.getenv('ALIBABA_CLOUD_REGION_ID'),
                        help='Region ID')
    parser.add_argument('--limit', type=int, default=50,
                        help='Number of logs to show')
    parser.add_argument('--format', choices=['table', 'json'], default='table',
                        help='Output format')
    
    args = parser.parse_args()
    
    try:
        logs = list_system_logs(
            instance_id=args.instance_id,
            region_id=args.region,
            limit=args.limit
        )
        
        if args.format == 'json':
            print(json.dumps(logs, indent=2, ensure_ascii=False))
        else:
            print(f"\n{'='*80}")
            print(f"  System Logs: {args.instance_id} (last {args.limit} entries)")
            print(f"{'='*80}\n")
            
            if logs:
                for log in logs:
                    level = log.get('level', 'INFO')
                    ts = log.get('timestamp', 'N/A')
                    content = log.get('content', '')
                    
                    level_icon = {'ERROR': '❌', 'WARN': '⚠️', 'INFO': 'ℹ️'}.get(level, '•')
                    print(f"  {level_icon} [{ts}] {content}")
            else:
                print("  No logs found.")
            
            print(f"\n{'='*80}\n")
            
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()