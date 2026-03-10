#!/usr/bin/env python3
"""
Get resource group statistics for PAI-DSW.

Note: Uses ListInstances API to compute statistics since 
GetResourceGroupStatistics API has backend issues.

Usage:
    python get_resource_stats.py [options]

Options:
    --region <region>     Region ID
    --format <format>     Output format: table, json (default: table)
    --help                Show this help message
"""

import os
import sys
import json
import argparse

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from dsw_utils import create_client, get_workspace_id
from alibabacloud_pai_dsw20220101 import models as dsw_models


def get_resource_stats(workspace_id: str, region_id: str = None) -> dict:
    """
    Get resource group statistics by aggregating instance data.
    
    Args:
        workspace_id: Workspace ID
        region_id: Region ID
    
    Returns:
        Statistics dictionary
    """
    client = create_client(region_id)
    
    # 获取所有实例
    request = dsw_models.ListInstancesRequest()
    request.workspace_id = workspace_id
    
    response = client.list_instances(request)
    
    stats = {
        'total_instances': 0,
        'running_instances': 0,
        'stopped_instances': 0,
        'failed_instances': 0,
        'total_cpu': 0,
        'total_memory': 0,
        'total_gpu': 0,
        'running_cpu': 0,
        'running_memory': 0,
        'running_gpu': 0,
        'gpu_instances': 0,
        'cpu_instances': 0,
    }
    
    if response.body and response.body.instances:
        stats['total_instances'] = len(response.body.instances)
        
        # GPU 规格关键词
        gpu_specs = ['gn', 'gn6', 'gn7', 'gn8', 'gn6i', 'gn7i', 'gn8i', 'p3', 'p4']
        
        for inst in response.body.instances:
            status = inst.status or 'Unknown'
            ecs_spec = inst.ecs_spec or ''
            
            # 状态统计
            if status == 'Running':
                stats['running_instances'] += 1
            elif status == 'Stopped':
                stats['stopped_instances'] += 1
            elif status == 'Failed':
                stats['failed_instances'] += 1
            
            # 判断是否为 GPU 实例
            is_gpu = any(spec in ecs_spec.lower() for spec in gpu_specs)
            
            if is_gpu:
                stats['gpu_instances'] += 1
            else:
                stats['cpu_instances'] += 1
            
            # 从规格名称估算资源（粗略估算）
            # ecs.g6.large -> 2核4G
            # ecs.g6.xlarge -> 4核16G
            # ecs.g6.2xlarge -> 8核32G
            # GPU 规格通常在名称中包含 GPU 数量信息
            
            if ecs_spec:
                try:
                    parts = ecs_spec.split('.')
                    if len(parts) >= 3:
                        size = parts[-1]  # large, xlarge, 2xlarge, etc.
                        
                        # CPU 核心估算
                        cpu_cores = {
                            'large': 2,
                            'xlarge': 4,
                            '2xlarge': 8,
                            '3xlarge': 12,
                            '4xlarge': 16,
                            '6xlarge': 24,
                            '8xlarge': 32,
                            '9xlarge': 36,
                            '10xlarge': 40,
                            '12xlarge': 48,
                            '16xlarge': 64,
                            '18xlarge': 72,
                            '24xlarge': 96,
                            '32xlarge': 128,
                        }.get(size, 4)
                        
                        # 内存估算 (GB)
                        memory_gb = cpu_cores * 4  # 粗略估计
                        
                        stats['total_cpu'] += cpu_cores
                        stats['total_memory'] += memory_gb
                        
                        if status == 'Running':
                            stats['running_cpu'] += cpu_cores
                            stats['running_memory'] += memory_gb
                        
                        # GPU 估算
                        if is_gpu:
                            # 从规格名称提取 GPU 数量
                            if 'c16g1' in ecs_spec:
                                gpu_count = 1
                            elif 'c24g1' in ecs_spec:
                                gpu_count = 1
                            elif 'c24g2' in ecs_spec:
                                gpu_count = 2
                            elif 'c32g2' in ecs_spec:
                                gpu_count = 2
                            elif 'c48g2' in ecs_spec:
                                gpu_count = 2
                            elif 'c72g4' in ecs_spec:
                                gpu_count = 4
                            elif 'c96g4' in ecs_spec:
                                gpu_count = 4
                            elif 'c144g8' in ecs_spec:
                                gpu_count = 8
                            else:
                                gpu_count = 1  # 默认1个
                            
                            stats['total_gpu'] += gpu_count
                            if status == 'Running':
                                stats['running_gpu'] += gpu_count
                                
                except Exception:
                    pass
    
    return stats


def main():
    parser = argparse.ArgumentParser(description='Get PAI-DSW resource group statistics')
    parser.add_argument('--workspace', default=os.getenv('PAI_WORKSPACE_ID'),
                        help='Workspace ID')
    parser.add_argument('--region', default=os.getenv('ALIBABA_CLOUD_REGION_ID'),
                        help='Region ID')
    parser.add_argument('--format', choices=['table', 'json'], default='table',
                        help='Output format')
    
    args = parser.parse_args()
    
    if not args.workspace:
        try:
            args.workspace = get_workspace_id(allow_interactive=False)
        except:
            print("❌ Error: Workspace ID required. Set PAI_WORKSPACE_ID or use --workspace", file=sys.stderr)
            sys.exit(1)
    
    try:
        stats = get_resource_stats(workspace_id=args.workspace, region_id=args.region)
        
        if args.format == 'json':
            print(json.dumps(stats, indent=2, ensure_ascii=False))
        else:
            print(f"\n{'='*60}")
            print("  PAI-DSW Resource Group Statistics")
            print(f"{'='*60}\n")
            
            print("  Instance Summary:")
            print(f"    Total:      {stats['total_instances']}")
            print(f"    Running:    {stats['running_instances']}")
            print(f"    Stopped:    {stats['stopped_instances']}")
            print(f"    Failed:     {stats['failed_instances']}")
            
            print("\n  Instance Types:")
            print(f"    CPU Instances: {stats['cpu_instances']}")
            print(f"    GPU Instances: {stats['gpu_instances']}")
            
            print("\n  Total Resources (Estimated):")
            print(f"    CPU:   {stats['total_cpu']} cores")
            print(f"    Memory: {stats['total_memory']} GB")
            print(f"    GPU:   {stats['total_gpu']}")
            
            print("\n  Running Resources:")
            print(f"    CPU:   {stats['running_cpu']} cores")
            print(f"    Memory: {stats['running_memory']} GB")
            print(f"    GPU:   {stats['running_gpu']}")
            
            print(f"\n{'='*60}\n")
            
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()