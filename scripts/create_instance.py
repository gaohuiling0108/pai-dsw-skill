#!/usr/bin/env python3
"""
Create a PAI-DSW instance with proper workspace and image configuration.

This script handles:
- Workspace ID detection from environment
- Correct image URL formatting for ModelScope images
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
    from alibabacloud_credentials.client import Client as CredentialClient
    from alibabacloud_tea_util import models as util_models
except ImportError as e:
    print(f"❌ Required packages not installed: {e}")
    print("Install with: pip install alibabacloud_pai_dsw20220101")
    sys.exit(1)

def get_credentials() -> open_api_models.Config:
    """Get credentials from environment or metadata service."""
    # Try to get from environment first
    access_key_id = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID')
    access_key_secret = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
    security_token = os.getenv('ALIBABA_CLOUD_SECURITY_TOKEN')
    
    if access_key_id and access_key_secret:
        region = os.getenv('ALIBABA_CLOUD_REGION_ID', 'cn-beijing')
        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            security_token=security_token,
            endpoint=f'pai-dsw.{region}.aliyuncs.com'
        )
        return config
    
    # Try to get from credentials URI
    credentials_uri = os.getenv('ALIBABA_CLOUD_CREDENTIALS_URI')
    if credentials_uri:
        try:
            import requests
            response = requests.get(credentials_uri, timeout=10)
            if response.status_code == 200:
                creds = response.json()
                if creds.get('Code') == 'Success':
                    region = os.getenv('ALIBABA_CLOUD_REGION_ID', 'cn-beijing')
                    config = open_api_models.Config(
                        access_key_id=creds['AccessKeyId'],
                        access_key_secret=creds['AccessKeySecret'],
                        security_token=creds['SecurityToken'],
                        endpoint=f'pai-dsw.{region}.aliyuncs.com'
                    )
                    return config
        except Exception as e:
            print(f"⚠️ Failed to get credentials from URI: {e}")
    
    raise Exception("No valid credentials found")

def get_workspace_id() -> str:
    """Get current workspace ID from environment."""
    workspace_id = os.getenv('PAI_WORKSPACE_ID')
    if not workspace_id:
        raise Exception("PAI_WORKSPACE_ID not found in environment")
    return workspace_id

def format_modelscope_image_url(image_name: str, region: str = 'cn-beijing') -> str:
    """
    Format ModelScope image name to full registry URL.
    
    Args:
        image_name: Image name like "modelscope:1.34.0-pytorch2.9.1-gpu-py311-cu124-ubuntu22.04"
                    or just "1.34.0-pytorch2.9.1-gpu-py311-cu124-ubuntu22.04"
        region: Alibaba Cloud region
    
    Returns:
        Full image URL like "dsw-registry-vpc.cn-beijing.cr.aliyuncs.com/pai/modelscope:1.34.0-pytorch2.9.1-gpu-py311-cu124-ubuntu22.04"
    """
    if image_name.startswith('dsw-registry-vpc'):
        return image_name
    
    # Extract image name and tag
    if ':' in image_name:
        parts = image_name.split(':', 1)
        name = parts[0]
        tag = parts[1]
    else:
        name = 'modelscope'
        tag = image_name
    
    # Default to modelscope if name is empty or just version
    if not name or name == 'modelscope':
        name = 'modelscope'
    
    registry = f'dsw-registry-vpc.{region}.cr.aliyuncs.com'
    namespace = 'pai'
    full_image = f'{registry}/{namespace}/{name}:{tag}'
    return full_image

def create_dsw_instance(
    instance_name: str,
    image_id: str,
    instance_type: str = 'ecs.g6.large',
    workspace_id: Optional[str] = None,
    region_id: str = 'cn-beijing',
    **kwargs
) -> Dict[str, Any]:
    """
    Create a PAI-DSW instance.
    
    Args:
        instance_name: Name of the instance
        image_id: Image ID or name (will be formatted if it's a ModelScope image)
        instance_type: Instance type (default: ecs.g6.large)
        workspace_id: Workspace ID (defaults to current workspace from env)
        region_id: Region ID (default: cn-beijing)
        **kwargs: Additional parameters for CreateInstanceRequest
        
    Returns:
        Dictionary with instance details
    """
    # Get workspace ID
    if workspace_id is None:
        workspace_id = get_workspace_id()
    
    # Format image URL if needed
    if image_id.startswith('modelscope:') or ':' in image_id:
        image_id = format_modelscope_image_url(image_id, region_id)
    
    print(f"Creating DSW instance with parameters:")
    print(f"  Name: {instance_name}")
    print(f"  Workspace ID: {workspace_id}")
    print(f"  Region: {region_id}")
    print(f"  Instance Type: {instance_type}")
    print(f"  Image: {image_id}")
    
    # Get credentials and create client
    config = get_credentials()
    config.region_id = region_id
    client = Client(config)
    
    # Create request
    request = models.CreateInstanceRequest(
        instance_name=instance_name,
        image_url=image_id,  # Use image_url instead of image_id
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
                'image_id': image_id,
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
  python create_instance.py --name my-notebook --image modelscope:1.34.0 --type ecs.g6.large
  
  # 创建 GPU 实例
  python create_instance.py --name gpu-training --image pytorch:2.0.0 --type ecs.gn6v-c8g1.16xlarge
  
  # 带环境变量
  python create_instance.py --name test --image modelscope:latest --type ecs.g6.large --env '{"API_KEY":"xxx"}'

镜像格式:
  modelscope:1.34.0-pytorch2.9.1-cpu-py311-ubuntu22.04
  pytorch:2.0.0-gpu-cu118
  完整URL: dsw-registry-vpc.cn-hangzhou.cr.aliyuncs.com/pai/modelscope:xxx
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
        print(f"   Image: {result['image_id']}")
        
    except Exception as e:
        print(f"\n❌ Failed to create DSW instance: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()