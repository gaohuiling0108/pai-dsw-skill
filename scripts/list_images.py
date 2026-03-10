#!/usr/bin/env python3
"""
列出可用的 DSW 镜像
由于 DSW SDK 不直接支持 ListImages，这里从实例中提取镜像信息
并提供常用官方镜像列表
"""

import argparse
import json
import sys
import os
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dsw_utils import create_client, get_workspace_id, print_table

try:
    from alibabacloud_pai_dsw20220101 import models as dsw_models
except ImportError:
    print("❌ 请安装: pip install alibabacloud-pai-dsw20220101")
    sys.exit(1)


# 常用官方镜像列表（参考阿里云 PAI-DSW 文档）
OFFICIAL_IMAGES = [
    # PyTorch 镜像
    {'name': 'PyTorch 2.9.1 (GPU, CUDA 12.6)', 'image_id': 'pytorch:2.9.1-gpu-py311-cu126-ubuntu22.04', 'type': 'GPU'},
    {'name': 'PyTorch 2.9.1 (CPU)', 'image_id': 'pytorch:2.9.1-cpu-py311-ubuntu22.04', 'type': 'CPU'},
    {'name': 'PyTorch 2.7.1 (GPU, CUDA 12.4)', 'image_id': 'pytorch:2.7.1-gpu-py310-cu124-ubuntu22.04', 'type': 'GPU'},
    {'name': 'PyTorch 2.7.1 (CPU)', 'image_id': 'pytorch:2.7.1-cpu-py310-ubuntu22.04', 'type': 'CPU'},
    
    # TensorFlow 镜像
    {'name': 'TensorFlow 2.16 (GPU, CUDA 12.3)', 'image_id': 'tensorflow:2.16-gpu-py310-cu123-ubuntu22.04', 'type': 'GPU'},
    {'name': 'TensorFlow 2.16 (CPU)', 'image_id': 'tensorflow:2.16-cpu-py310-ubuntu22.04', 'type': 'CPU'},
    
    # ModelScope 镜像
    {'name': 'ModelScope 1.34.0 (GPU)', 'image_id': 'modelscope:1.34.0-pytorch2.9.1-gpu', 'type': 'GPU'},
    {'name': 'ModelScope 1.34.0 (CPU)', 'image_id': 'modelscope:1.34.0-pytorch2.9.1-cpu', 'type': 'CPU'},
    
    # PAI-Blade 镜像
    {'name': 'PAI-Blade (GPU)', 'image_id': 'blade:latest-gpu', 'type': 'GPU'},
    
    # 基础镜像
    {'name': 'Python 3.11 (Ubuntu 22.04)', 'image_id': 'python:3.11-ubuntu22.04', 'type': 'CPU'},
    {'name': 'Python 3.10 (Ubuntu 22.04)', 'image_id': 'python:3.10-ubuntu22.04', 'type': 'CPU'},
    
    # 其他框架
    {'name': 'DeepSpeed 0.15 (GPU)', 'image_id': 'deepspeed:0.15-gpu-py310-cu124', 'type': 'GPU'},
    {'name': 'XGBoost 2.0 (CPU)', 'image_id': 'xgboost:2.0-cpu-py310', 'type': 'CPU'},
]


def list_images(workspace_id: str = None, region_id: str = None, 
                image_type: str = 'all', format: str = 'table', keyword: str = None):
    """
    列出可用镜像
    
    Args:
        workspace_id: 工作空间 ID
        region_id: 区域 ID
        image_type: 镜像类型 (all, official, custom)
        format: 输出格式
        keyword: 搜索关键词
    """
    try:
        all_images = []
        
        # 获取官方镜像
        if image_type in ['all', 'official']:
            for img in OFFICIAL_IMAGES:
                name = img['name']
                if keyword and keyword.lower() not in name.lower() and keyword.lower() not in img['image_id'].lower():
                    continue
                all_images.append({
                    'ImageId': img['image_id'],
                    'Name': name,
                    'Type': 'OFFICIAL',
                    'Category': img['type'],
                    'Source': '阿里云官方'
                })
        
        # 从现有实例中提取自定义镜像
        if image_type in ['all', 'custom']:
            try:
                client = create_client(region_id)
                if not workspace_id:
                    workspace_id = get_workspace_id()
                
                request = dsw_models.ListInstancesRequest(
                    workspace_id=workspace_id,
                    page_number=1,
                    page_size=100
                )
                
                response = client.list_instances(request)
                
                if response.status_code == 200 and response.body.instances:
                    seen_images = set()
                    for inst in response.body.instances:
                        image_id = inst.image_id
                        image_name = inst.image_name or image_id
                        
                        if image_id and image_id not in seen_images:
                            seen_images.add(image_id)
                            
                            if keyword and keyword.lower() not in image_name.lower():
                                continue
                            
                            all_images.append({
                                'ImageId': image_id,
                                'Name': image_name,
                                'Type': 'CUSTOM',
                                'Category': 'Unknown',
                                'Source': '实例快照'
                            })
            except Exception as e:
                print(f"⚠️ 无法获取自定义镜像: {e}", file=sys.stderr)
        
        if format == 'json':
            print(json.dumps(all_images, indent=2, ensure_ascii=False))
            return all_images
        
        if not all_images:
            print("⚠️ 未找到镜像")
            return []
        
        print(f"\n📦 找到 {len(all_images)} 个镜像:\n")
        
        headers = ['镜像ID', '名称', '类型', 'GPU/CPU', '来源']
        rows = []
        
        for img in all_images:
            type_str = "📘 官方" if img['Type'] == 'OFFICIAL' else "🔧 自定义"
            
            rows.append([
                img['ImageId'][:40] + '...' if len(img['ImageId']) > 40 else img['ImageId'],
                img['Name'][:35] + '...' if len(img['Name']) > 35 else img['Name'],
                type_str,
                img['Category'],
                img['Source']
            ])
        
        print_table(headers, rows)
        
        print(f"\n💡 提示:")
        print(f"   - 创建实例时使用镜像ID，如: --image pytorch:2.9.1-gpu-py311-cu126-ubuntu22.04")
        print(f"   - GPU镜像需要选择GPU规格 (如 ecs.gn7-c13g1.2xlarge)")
        print(f"   - CPU镜像选择CPU规格 (如 ecs.g6.large)")
        
        return all_images
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description='列出可用的 DSW 镜像')
    parser.add_argument('--workspace', '-w', help='工作空间 ID')
    parser.add_argument('--region', '-r', help='区域 ID')
    parser.add_argument('--type', choices=['all', 'official', 'custom'], default='all',
                       help='镜像类型 (all/official/custom)')
    parser.add_argument('--format', choices=['table', 'json'], default='table', help='输出格式')
    parser.add_argument('--search', '-s', help='搜索关键词')
    
    args = parser.parse_args()
    
    list_images(
        workspace_id=args.workspace,
        region_id=args.region,
        image_type=args.type,
        format=args.format,
        keyword=args.search
    )


if __name__ == '__main__':
    main()