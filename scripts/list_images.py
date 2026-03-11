#!/usr/bin/env python3
"""
列出可用的 DSW 镜像

通过 AIWorkSpace API (ListImages) 动态获取 DSW 可用的镜像列表，
使用 system.supported.dsw=true 标签过滤。
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dsw_utils import get_credentials, get_region_id, get_workspace_id, print_table

try:
    from alibabacloud_aiworkspace20210204.client import Client as WorkspaceClient
    from alibabacloud_aiworkspace20210204 import models as ws_models
    from alibabacloud_tea_openapi import models as open_api_models
    _WS_SDK_AVAILABLE = True
except ImportError:
    _WS_SDK_AVAILABLE = False


def _create_workspace_client(region_id: str = None):
    """创建 AIWorkSpace 客户端"""
    if not _WS_SDK_AVAILABLE:
        raise ImportError(
            "需要安装 AIWorkSpace SDK:\n"
            "  pip install alibabacloud-aiworkspace20210204"
        )
    
    if region_id is None:
        region_id = get_region_id()
    
    creds = get_credentials()
    endpoint = f"aiworkspace.{region_id}.aliyuncs.com"
    
    config = open_api_models.Config(
        access_key_id=creds['access_key_id'],
        access_key_secret=creds['access_key_secret'],
        security_token=creds.get('security_token'),
        endpoint=endpoint,
        region_id=region_id
    )
    return WorkspaceClient(config)


def _fetch_images_from_api(region_id: str = None, keyword: str = None,
                           image_type: str = 'all', workspace_id: str = None):
    """
    通过 AIWorkSpace API 获取 DSW 可用镜像
    
    Args:
        region_id: 区域 ID
        keyword: 搜索关键词（模糊匹配镜像名称和描述）
        image_type: 镜像类型 (all, official, custom)
        workspace_id: 工作空间 ID（获取自定义镜像时需要）
    
    Returns:
        镜像列表
    """
    client = _create_workspace_client(region_id)
    all_images = []
    page_number = 1
    page_size = 100
    
    # 构建标签过滤条件
    labels = 'system.supported.dsw=true'
    if image_type == 'official':
        labels += ',system.official=true'
    
    while True:
        req = ws_models.ListImagesRequest(
            labels=labels,
            verbose=True,
            page_number=page_number,
            page_size=page_size,
        )
        
        # 使用 query 参数进行模糊搜索
        if keyword:
            req.query = keyword
        
        if workspace_id:
            req.workspace_id = workspace_id
        
        resp = client.list_images(req)
        images = resp.body.images or []
        
        for img in images:
            labels_dict = {l.key: l.value for l in (img.labels or [])}
            
            # 判断镜像类型
            is_official = labels_dict.get('system.official', '').lower() == 'true'
            if image_type == 'official' and not is_official:
                continue
            if image_type == 'custom' and is_official:
                continue
            
            chip_type = labels_dict.get('system.chipType', 'Unknown')
            origin = labels_dict.get('system.origin', '')
            
            all_images.append({
                'ImageId': img.name or '',
                'ImageUri': img.image_uri or '',
                'Name': img.name or '',
                'Description': img.description or '',
                'Type': 'OFFICIAL' if is_official else 'CUSTOM',
                'Category': chip_type,
                'Source': origin if origin else ('阿里云官方' if is_official else '自定义'),
                'Labels': labels_dict,
            })
        
        # 分页：如果当前页未满，说明没有更多数据
        total = resp.body.total_count or 0
        if page_number * page_size >= total:
            break
        page_number += 1
    
    return all_images


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
        all_images = _fetch_images_from_api(
            region_id=region_id,
            keyword=keyword,
            image_type=image_type,
            workspace_id=workspace_id,
        )
        
        if format == 'json':
            print(json.dumps(all_images, indent=2, ensure_ascii=False))
            return all_images
        
        if not all_images:
            print("⚠️ 未找到镜像")
            if keyword:
                print(f"   尝试换个关键词，或使用 --type all 查看全部镜像")
            return []
        
        print(f"\n📦 找到 {len(all_images)} 个镜像:\n")
        
        headers = ['镜像名称', '类型', 'GPU/CPU', '来源']
        rows = []
        
        for img in all_images:
            type_str = "📘 官方" if img['Type'] == 'OFFICIAL' else "🔧 自定义"
            name_display = img['Name']
            if len(name_display) > 60:
                name_display = name_display[:57] + '...'
            
            rows.append([
                name_display,
                type_str,
                img['Category'],
                img['Source']
            ])
        
        print_table(headers, rows)
        
        print(f"\n💡 提示:")
        print(f"   - 创建实例时使用镜像名称，如: --image modelscope:1.34.0-pytorch2.9.1-gpu-py311-cu124-ubuntu22.04")
        print(f"   - GPU 镜像需要选择 GPU 规格 (如 ecs.gn6i-c4g1.xlarge)")
        print(f"   - CPU 镜像选择 CPU 规格 (如 ecs.g6.large)")
        print(f"   - 使用 --format json 可查看完整镜像 URI")
        
        return all_images
        
    except ImportError as e:
        print(f"❌ {e}", file=sys.stderr)
        print("   pip install alibabacloud-aiworkspace20210204", file=sys.stderr)
        return []
    except Exception as e:
        print(f"❌ 获取镜像列表失败: {e}", file=sys.stderr)
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
