#!/usr/bin/env python3
"""
Create a PAI-DSW instance with proper workspace and image configuration.

This script handles:
- Workspace ID detection from environment/config
- Image URI resolution via AIWorkSpace API
- Proper API parameter mapping
"""

import os
import sys
import json
from typing import Optional, Dict, Any

# Add the skill directory to Python path
skill_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, skill_dir)

try:
    from alibabacloud_pai_dsw20220101.client import Client
    from alibabacloud_pai_dsw20220101 import models
    from alibabacloud_tea_openapi import models as open_api_models
    from alibabacloud_tea_util import models as util_models
except ImportError as e:
    print(f"❌ Required packages not installed: {e}")
    print("Install with: pip install alibabacloud_pai_dsw20220101")
    sys.exit(1)

from dsw_utils import (
    get_credentials as _get_creds,
    get_region_id,
    get_workspace_id as _get_workspace_id,
)


def resolve_image_uri(image_name: str, region_id: str = None) -> str:
    """
    Resolve an image name to its full image URI via AIWorkSpace API.
    
    Supports:
    - Full URI (returned as-is): dsw-registry-vpc.xxx.cr.aliyuncs.com/pai/modelscope:xxx
    - Short name: modelscope:1.34.0-pytorch2.9.1-gpu-py311-cu124-ubuntu22.04
    
    Args:
        image_name: Image name or full URI
        region_id: Region ID for API call
    
    Returns:
        Full image URI for DSW instance creation
    """
    # Already a full URI
    if image_name.startswith(('dsw-registry-vpc', 'registry-vpc')):
        return image_name
    
    # Try to resolve via AIWorkSpace API
    try:
        from list_images import _create_workspace_client
        from alibabacloud_aiworkspace20210204 import models as ws_models
        
        client = _create_workspace_client(region_id)
        req = ws_models.ListImagesRequest(
            labels='system.supported.dsw=true',
            query=image_name,
            verbose=False,
            page_size=100,
        )
        resp = client.list_images(req)
        
        # Look for exact name match first
        for img in (resp.body.images or []):
            if img.name == image_name:
                print(f"  ✅ 镜像已验证: {img.name}")
                return img.image_uri
        
        # If no exact match, try prefix match (e.g. "modelscope:1.34.0" -> latest matching)
        for img in (resp.body.images or []):
            if img.name and img.name.startswith(image_name):
                print(f"  ℹ️ 镜像模糊匹配: {image_name} -> {img.name}")
                return img.image_uri
        
        print(f"  ⚠️ 未在 API 中找到镜像 '{image_name}'，将尝试直接构建 URI", file=sys.stderr)
        
    except ImportError:
        print(f"  ⚠️ AIWorkSpace SDK 未安装，将直接构建镜像 URI", file=sys.stderr)
    except Exception as e:
        print(f"  ⚠️ 镜像查询失败 ({e})，将直接构建 URI", file=sys.stderr)
    
    # Fallback: construct URI manually
    return _format_image_url(image_name, region_id or get_region_id())


def _format_image_url(image_name: str, region: str) -> str:
    """Fallback: construct image URL from name and region."""
    if ':' in image_name:
        parts = image_name.split(':', 1)
        name = parts[0]
        tag = parts[1]
    else:
        name = 'modelscope'
        tag = image_name
    
    if not name:
        name = 'modelscope'
    
    registry = f'dsw-registry-vpc.{region}.cr.aliyuncs.com'
    return f'{registry}/pai/{name}:{tag}'

def create_dsw_instance(
    instance_name: str,
    image_id: str,
    instance_type: str = 'ecs.g6.large',
    workspace_id: Optional[str] = None,
    region_id: str = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a PAI-DSW instance.
    
    Args:
        instance_name: Name of the instance
        image_id: Image name or full URI (will be resolved via API)
        instance_type: Instance type (default: ecs.g6.large)
        workspace_id: Workspace ID (defaults to current workspace from env/config)
        region_id: Region ID (default: from env/config)
        **kwargs: Additional parameters for CreateInstanceRequest
        
    Returns:
        Dictionary with instance details
    """
    # Get region and workspace ID from config if not provided
    if region_id is None:
        region_id = get_region_id()
    if workspace_id is None:
        workspace_id = _get_workspace_id()
    
    # Resolve image URI via AIWorkSpace API
    image_uri = resolve_image_uri(image_id, region_id)
    
    print(f"Creating DSW instance with parameters:")
    print(f"  Name: {instance_name}")
    print(f"  Workspace ID: {workspace_id}")
    print(f"  Region: {region_id}")
    print(f"  Instance Type: {instance_type}")
    print(f"  Image: {image_uri}")
    
    # Get credentials and create client
    creds = _get_creds()
    endpoint = f'pai-dsw.{region_id}.aliyuncs.com'
    config = open_api_models.Config(
        access_key_id=creds['access_key_id'],
        access_key_secret=creds['access_key_secret'],
        security_token=creds.get('security_token'),
        endpoint=endpoint,
        region_id=region_id
    )
    client = Client(config)
    
    # Create request
    request = models.CreateInstanceRequest(
        instance_name=instance_name,
        image_url=image_uri,
        ecs_spec=instance_type,
        workspace_id=workspace_id,
        **kwargs
    )
    
    # Create runtime options
    runtime = util_models.RuntimeOptions()
    
    try:
        response = client.create_instance_with_options(request, None, runtime)
        if response.body and response.body.success:
            return {
                'instance_id': response.body.instance_id,
                'instance_name': instance_name,
                'workspace_id': workspace_id,
                'region_id': region_id,
                'image_uri': image_uri,
                'status': 'created'
            }
        else:
            error_msg = getattr(response.body, 'message', 'Unknown error')
            code = getattr(response.body, 'code', 'Unknown')
            raise Exception(f"API Error: {code} - {error_msg}")
            
    except Exception as e:
        raise Exception(f"Failed to create instance: {str(e)}")

def main():
    """Main function for command line usage."""
    import argparse
    import time
    
    parser = argparse.ArgumentParser(
        description='Create PAI-DSW instance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 创建 CPU 实例
  python create_instance.py --name my-notebook --image modelscope:1.34.0-pytorch2.3.1-cpu-py311-ubuntu22.04 --type ecs.g6.large
  
  # 创建 GPU 实例（镜像名称会通过 API 自动解析为完整 URI）
  python create_instance.py --name gpu-training --image modelscope:1.34.0-pytorch2.9.1-gpu-py311-cu124-ubuntu22.04 --type ecs.gn6i-c4g1.xlarge
  
  # 使用完整镜像 URI
  python create_instance.py --name test --image dsw-registry-vpc.cn-hangzhou.cr.aliyuncs.com/pai/modelscope:xxx --type ecs.g6.large

镜像名称:
  可通过 list_images.py --search modelscope 查询可用镜像
"""
    )
    parser.add_argument('--name', required=True, help='Instance name')
    parser.add_argument('--image', required=True, help='Image ID or name')
    parser.add_argument('--type', default='ecs.g6.large', help='Instance type (default: ecs.g6.large)')
    parser.add_argument('--workspace', help='Workspace ID (defaults to current)')
    parser.add_argument('--region', help='Region ID')
    parser.add_argument('--labels', help='Labels in JSON format')
    parser.add_argument('--env', help='Environment variables in JSON format')
    parser.add_argument('--datasets', help='Datasets to mount in JSON format')
    parser.add_argument('--user-command', help='User command to run on start')
    
    args = parser.parse_args()
    
    # Parse optional JSON arguments
    kwargs = {}
    if args.labels:
        try:
            kwargs['labels'] = json.loads(args.labels)
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON for labels", file=sys.stderr)
            sys.exit(1)
    
    if args.env:
        try:
            kwargs['environment_variables'] = json.loads(args.env)
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON for env", file=sys.stderr)
            sys.exit(1)
    
    if args.datasets:
        try:
            kwargs['datasets'] = json.loads(args.datasets)
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON for datasets", file=sys.stderr)
            sys.exit(1)
    
    if args.user_command:
        kwargs['user_command'] = args.user_command
    
    try:
        result = create_dsw_instance(
            instance_name=args.name,
            image_id=args.image,
            instance_type=args.type,
            workspace_id=args.workspace,
            region_id=args.region,
            **kwargs
        )
        
        print(f"\n✅ Successfully created DSW instance!")
        print(f"   Instance ID: {result['instance_id']}")
        print(f"   Instance Name: {result['instance_name']}")
        print(f"   Workspace ID: {result['workspace_id']}")
        print(f"   Region: {result['region_id']}")
        print(f"   Image: {result['image_uri']}")
        
    except Exception as e:
        print(f"\n❌ Failed to create DSW instance: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()