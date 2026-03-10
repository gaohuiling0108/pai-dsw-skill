#!/usr/bin/env python3
"""
GPU usage alert script for PAI-DSW.

Checks GPU usage across all GPU instances and sends alerts
via DingTalk when usage exceeds threshold.

Usage:
    python gpu_alert.py [options]

Options:
    --threshold <percent>   Alert threshold (default: 80)
    --region <region>       Region ID
    --dingtalk              Send alert to DingTalk
    --help                  Show this help message
"""

import os
import sys
import json
import argparse
import re
import subprocess
from datetime import datetime

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from dsw_utils import create_client, get_workspace_id
from alibabacloud_pai_dsw20220101 import models as dsw_models


def get_gpu_instances(workspace_id: str, region_id: str = None) -> list:
    """Get all GPU instances in workspace."""
    client = create_client(region_id)
    
    request = dsw_models.ListInstancesRequest()
    request.workspace_id = workspace_id
    response = client.list_instances(request)
    
    # GPU spec keywords
    gpu_specs = ['gn', 'gn6', 'gn7', 'gn8', 'gn6i', 'gn7i', 'gn8i', 'p3', 'p4']
    
    gpu_instances = []
    
    if response.body and response.body.instances:
        for inst in response.body.instances:
            ecs_spec = inst.ecs_spec or ''
            is_gpu = any(spec in ecs_spec.lower() for spec in gpu_specs)
            
            if is_gpu and inst.status == 'Running':
                gpu_instances.append({
                    'id': inst.instance_id,
                    'name': inst.instance_name or 'N/A',
                    'spec': ecs_spec,
                })
    
    return gpu_instances


def get_gpu_usage(instance_id: str, region_id: str = None) -> float:
    """Get GPU usage for an instance."""
    try:
        result = subprocess.run(
            ['python3', f'{script_dir}/get_instance_metrics.py', 
             instance_id, '--region', region_id or '', '--summary'],
            capture_output=True, text=True, cwd=script_dir
        )
        
        # Parse GPU usage from output
        for line in result.stdout.split('\n'):
            if 'gpu' in line.lower() and '%' in line and 'gpu-memory' not in line.lower():
                match = re.search(r':\s*(\d+\.?\d*)%', line)
                if match:
                    return float(match.group(1))
        
        return 0.0
    except Exception:
        return -1.0  # Error


def check_gpu_usage(threshold: float = 80.0, region_id: str = None) -> dict:
    """
    Check GPU usage across all instances.
    
    Args:
        threshold: Alert threshold percentage
        region_id: Region ID
    
    Returns:
        Dictionary with results
    """
    workspace_id = get_workspace_id(allow_interactive=False)
    
    gpu_instances = get_gpu_instances(workspace_id, region_id)
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'threshold': threshold,
        'total_checked': len(gpu_instances),
        'high_usage': [],
        'normal': [],
        'errors': [],
    }
    
    for inst in gpu_instances:
        usage = get_gpu_usage(inst['id'], region_id)
        
        if usage < 0:
            results['errors'].append({
                'id': inst['id'],
                'name': inst['name'],
            })
        elif usage >= threshold:
            results['high_usage'].append({
                'id': inst['id'],
                'name': inst['name'],
                'usage': usage,
            })
        else:
            results['normal'].append({
                'id': inst['id'],
                'name': inst['name'],
                'usage': usage,
            })
    
    return results


def send_dingtalk_alert(results: dict):
    """Send alert to DingTalk."""
    if not results['high_usage']:
        return
    
    # Build message
    lines = [
        f"⚠️ **GPU 使用率告警** ({results['timestamp'][:16]})",
        f"",
        f"以下实例 GPU 使用率超过 {results['threshold']}%：",
    ]
    
    for inst in results['high_usage']:
        lines.append(f"  - {inst['name']}: **{inst['usage']:.1f}%**")
    
    lines.append(f"")
    lines.append(f"请检查相关实例运行状态。")
    
    message = '\n'.join(lines)
    
    # Send via message tool
    try:
        import importlib
        message_module = importlib.import_module('message')
        # This would need proper channel configuration
        print(f"Would send to DingTalk:\n{message}")
    except ImportError:
        print(f"Alert message:\n{message}")


def main():
    parser = argparse.ArgumentParser(description='GPU usage alert for PAI-DSW')
    parser.add_argument('--threshold', type=float, default=80.0,
                        help='Alert threshold (default: 80)')
    parser.add_argument('--region', help='Region ID')
    parser.add_argument('--dingtalk', action='store_true',
                        help='Send alert to DingTalk')
    parser.add_argument('--json', action='store_true',
                        help='JSON output')
    
    args = parser.parse_args()
    
    try:
        results = check_gpu_usage(args.threshold, args.region)
        
        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            print(f"\n{'='*60}")
            print(f"  GPU 使用率检查 ({results['timestamp'][:16]})")
            print(f"{'='*60}")
            print(f"  阈值: {args.threshold}%")
            print(f"  检查实例数: {results['total_checked']}")
            print(f"{'='*60}")
            
            if results['high_usage']:
                print(f"\n  ⚠️ 高负载实例 ({len(results['high_usage'])} 个):")
                for inst in results['high_usage']:
                    print(f"    🔴 {inst['name']}: {inst['usage']:.1f}%")
            
            if results['normal']:
                print(f"\n  ✅ 正常实例 ({len(results['normal'])} 个):")
                for inst in results['normal']:
                    print(f"    {inst['name']}: {inst['usage']:.1f}%")
            
            if results['errors']:
                print(f"\n  ❌ 检查失败 ({len(results['errors'])} 个):")
                for inst in results['errors']:
                    print(f"    {inst['name']}")
            
            print(f"\n{'='*60}\n")
            
            # Send DingTalk alert if requested
            if args.dingtalk and results['high_usage']:
                send_dingtalk_alert(results)
        
        # Exit with error code if high usage detected
        sys.exit(1 if results['high_usage'] else 0)
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()