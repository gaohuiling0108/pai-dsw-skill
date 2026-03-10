#!/usr/bin/env python3
"""
Get resource metrics of a PAI-DSW instance.

Usage:
    python get_instance_metrics.py <instance_id> [options]

Options:
    --region <region>       Region ID (default: from environment)
    --start <time>          Start time (default: 1 hour ago, format: YYYY-MM-DDTHH:MM:SSZ)
    --end <time>            End time (default: now, format: YYYY-MM-DDTHH:MM:SSZ)
    --type <type>           Metric type: cpu, memory, gpu, gpu-memory (default: all)
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
from datetime import datetime, timedelta

# Add script directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from dsw_utils import create_client
from alibabacloud_pai_dsw20220101 import models as dsw_models

# 正确的 metric_type 值映射
METRIC_TYPE_MAP = {
    'cpu': 'CpuCoreUsage',
    'memory': 'MemoryUsage',
    'gpu': 'GpuCoreUsage',
    'gpu-memory': 'GpuMemoryUsage',
    'network-in': 'NetworkInputRate',
    'network-out': 'NetworkOutputRate',
    'disk-read': 'DiskReadRate',
    'disk-write': 'DiskWriteRate',
}

# 默认查询的指标类型
DEFAULT_METRIC_TYPES = ['cpu', 'memory', 'gpu', 'gpu-memory']


def get_instance_metrics(
    instance_id: str,
    region_id: str = None,
    start_time: str = None,
    end_time: str = None,
    metric_type: str = None
) -> dict:
    """
    Get resource metrics of a DSW instance.
    
    Args:
        instance_id: Instance ID
        region_id: Region ID
        start_time: Start time (ISO format)
        end_time: End time (ISO format)
        metric_type: Metric type (cpu, memory, gpu, gpu-memory). If None, fetch all types.
    
    Returns:
        Metrics dictionary
    """
    client = create_client(region_id)
    
    # Default time range: last 1 hour
    if end_time is None:
        end_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    if start_time is None:
        start = datetime.utcnow() - timedelta(hours=1)
        start_time = start.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    result = {
        'instance_id': instance_id,
        'start_time': start_time,
        'end_time': end_time,
        'metrics': {}
    }
    
    # Determine which metric types to fetch
    types_to_fetch = [metric_type] if metric_type else DEFAULT_METRIC_TYPES
    
    for mt in types_to_fetch:
        api_metric_type = METRIC_TYPE_MAP.get(mt, mt)
        request = dsw_models.GetInstanceMetricsRequest(
            start_time=start_time,
            end_time=end_time,
            metric_type=api_metric_type
        )
        
        try:
            response = client.get_instance_metrics(instance_id, request)
            
            if response.body and hasattr(response.body, 'pod_metrics') and response.body.pod_metrics:
                for pod in response.body.pod_metrics:
                    pod_id = pod.pod_id
                    if pod_id not in result['metrics']:
                        result['metrics'][pod_id] = {}
                    
                    data_points = []
                    if pod.metrics:
                        for m in pod.metrics:
                            data_points.append({
                                'time': m.time,
                                'value': m.value
                            })
                    
                    result['metrics'][pod_id][mt] = {
                        'metric_type': api_metric_type,
                        'data_points': data_points,
                        'count': len(data_points)
                    }
        except Exception as e:
            print(f"Warning: Failed to get {mt} metrics: {e}", file=sys.stderr)
    
    return result


def main():
    parser = argparse.ArgumentParser(description='Get PAI-DSW instance resource metrics')
    parser.add_argument('instance_id', help='Instance ID')
    parser.add_argument('--region', default=os.getenv('ALIBABA_CLOUD_REGION_ID'),
                        help='Region ID (default: from environment)')
    parser.add_argument('--start', help='Start time (ISO format, default: 1 hour ago)')
    parser.add_argument('--end', help='End time (ISO format, default: now)')
    parser.add_argument('--type', dest='metric_type', 
                        choices=['cpu', 'memory', 'gpu', 'gpu-memory', 'network-in', 'network-out', 'disk-read', 'disk-write'],
                        help='Metric type (default: all)')
    parser.add_argument('--summary', action='store_true',
                        help='Show summary only')
    
    args = parser.parse_args()
    
    try:
        result = get_instance_metrics(
            args.instance_id,
            args.region,
            args.start,
            args.end,
            args.metric_type
        )
        
        if args.summary:
            print(f"\n{'='*70}")
            print(f"  Instance Metrics Summary: {args.instance_id}")
            print(f"{'='*70}")
            print(f"  Time Range: {result['start_time']} ~ {result['end_time']}")
            print(f"{'='*70}")
            
            for pod_id, metrics in result['metrics'].items():
                print(f"\n  Pod: {pod_id}")
                for metric_name, data in metrics.items():
                    if data['data_points']:
                        latest = data['data_points'][-1]['value']
                        print(f"    {metric_name:15} : {latest:.2f}% ({data['count']} points)")
            
            print(f"\n{'='*70}\n")
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()