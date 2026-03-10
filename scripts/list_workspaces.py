#!/usr/bin/env python3
"""
列出 PAI 工作空间信息
由于 DSW SDK 不直接支持 ListWorkspaces，这里从实例中提取工作空间信息
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


def list_workspaces(region_id: str = None, format: str = 'table'):
    """列出所有工作空间（从实例中提取）"""
    try:
        client = create_client(region_id)
        
        # 获取当前工作空间 ID
        current_workspace_id = None
        try:
            current_workspace_id = get_workspace_id()
        except:
            pass
        
        # 获取所有实例
        request = dsw_models.ListInstancesRequest(
            page_number=1,
            page_size=100
        )
        
        response = client.list_instances(request)
        
        if response.status_code != 200:
            print(f"❌ 请求失败: {response.status_code}")
            return []
        
        instances = response.body.instances
        
        # 按工作空间分组
        workspaces = defaultdict(lambda: {
            'instances': [],
            'running': 0,
            'stopped': 0,
            'failed': 0
        })
        
        for inst in instances:
            ws_id = inst.workspace_id
            ws_name = inst.workspace_name or 'Unknown'
            
            workspaces[ws_id]['name'] = ws_name
            workspaces[ws_id]['instances'].append(inst.instance_id)
            
            if inst.status == 'Running':
                workspaces[ws_id]['running'] += 1
            elif inst.status == 'Stopped':
                workspaces[ws_id]['stopped'] += 1
            else:
                workspaces[ws_id]['failed'] += 1
        
        if format == 'json':
            result = []
            for ws_id, info in workspaces.items():
                result.append({
                    'WorkspaceId': ws_id,
                    'WorkspaceName': info['name'],
                    'TotalInstances': len(info['instances']),
                    'Running': info['running'],
                    'Stopped': info['stopped'],
                    'Failed': info['failed'],
                    'InstanceIds': info['instances']
                })
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return result
        else:
            print(f"\n📋 找到 {len(workspaces)} 个工作空间:\n")
            
            headers = ['工作空间ID', '名称', '实例总数', '运行中', '已停止', '异常']
            rows = []
            
            for ws_id, info in sorted(workspaces.items()):
                total = len(info['instances'])
                current_marker = " ← 当前" if ws_id == current_workspace_id else ""
                
                rows.append([
                    ws_id + current_marker,
                    info['name'],
                    str(total),
                    str(info['running']),
                    str(info['stopped']),
                    str(info['failed'])
                ])
            
            print_table(headers, rows)
            
            if current_workspace_id:
                print(f"\n💡 当前工作空间: {current_workspace_id}")
            
            return list(workspaces.keys())
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description='列出 PAI 工作空间')
    parser.add_argument('--region', help='区域 ID')
    parser.add_argument('--format', choices=['table', 'json'], default='table', help='输出格式')
    
    args = parser.parse_args()
    
    list_workspaces(args.region, args.format)


if __name__ == '__main__':
    main()