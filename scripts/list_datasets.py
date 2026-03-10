#!/usr/bin/env python3
"""
列出 DSW 数据集挂载信息
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dsw_utils import create_client, print_table, colorize, Colors

try:
    from alibabacloud_pai_dsw20220101 import models as dsw_models
except ImportError:
    print("❌ 请安装: pip install alibabacloud-pai-dsw20220101")
    sys.exit(1)


def get_instance_datasets(instance_id: str, region_id: str = None, format: str = 'table'):
    """
    获取实例的数据集挂载信息
    
    Args:
        instance_id: 实例 ID
        region_id: 区域 ID
        format: 输出格式
    """
    try:
        client = create_client(region_id)
        
        # 获取实例详情
        request = dsw_models.GetInstanceRequest()
        response = client.get_instance(instance_id, request)
        
        if response.status_code != 200:
            print(f"❌ 获取实例失败: {response.status_code}")
            return
        
        instance = response.body
        
        # 提取数据集信息
        datasets = []
        
        # 从环境变量或配置中提取
        # DSW 实例的 NAS/OSS 挂载通常在实例配置中
        
        if format == 'json':
            result = {
                'InstanceId': instance_id,
                'InstanceName': instance.instance_name,
                'Datasets': datasets
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return
        
        print(f"\n📁 实例数据集挂载信息")
        print("="*50)
        print(f"实例 ID: {instance_id}")
        print(f"实例名称: {instance.instance_name or 'N/A'}")
        
        # 检查常用挂载点
        print(f"\n本地挂载点:")
        
        mount_points = [
            '/mnt/workspace',
            '/mnt/data',
            '/mnt/nas',
            '/mnt/oss',
            '/home/admin/workspace'
        ]
        
        for mp in mount_points:
            if os.path.exists(mp):
                # 获取挂载信息
                result = os.popen(f'df -h {mp} 2>/dev/null | tail -1').read().strip()
                if result:
                    parts = result.split()
                    if len(parts) >= 6:
                        print(f"\n  {mp}:")
                        print(f"    容量: {parts[1]}")
                        print(f"    已用: {parts[2]} ({parts[4]})")
                        print(f"    可用: {parts[3]}")
                        print(f"    设备: {parts[0]}")
        
        # 检查 OSS 挂载
        print(f"\nOSS 配置:")
        oss_config = os.popen('cat /etc/ossfs.conf 2>/dev/null').read()
        if oss_config:
            print(f"  {oss_config[:200]}...")
        else:
            print(f"  未检测到 OSS 挂载配置")
        
        # 检查 NAS 挂载
        print(f"\nNAS 配置:")
        nas_mounts = os.popen('mount | grep nfs').read()
        if nas_mounts:
            for line in nas_mounts.split('\n'):
                if line.strip():
                    print(f"  {line}")
        else:
            print(f"  未检测到 NAS 挂载")
        
        print()
        
    except Exception as e:
        print(f"❌ 错误: {e}")


def main():
    parser = argparse.ArgumentParser(description='列出 DSW 实例数据集挂载信息')
    parser.add_argument('instance', nargs='?', help='实例 ID (默认当前实例)')
    parser.add_argument('--region', '-r', help='区域 ID')
    parser.add_argument('--format', choices=['table', 'json'], default='table', help='输出格式')
    
    args = parser.parse_args()
    
    instance_id = args.instance
    if not instance_id:
        # 尝试获取当前实例 ID
        instance_id = os.getenv('HOSTNAME', '')
        if not instance_id.startswith('dsw-'):
            print("❌ 请指定实例 ID 或在 DSW 实例中运行")
            sys.exit(1)
    
    get_instance_datasets(instance_id, args.region, args.format)


if __name__ == '__main__':
    main()