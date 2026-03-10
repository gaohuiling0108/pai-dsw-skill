#!/usr/bin/env python3
"""
Create instance snapshot (custom image) from a running DSW instance.

This script creates a snapshot of a running DSW instance, which can be used
as a custom image for future instance creation.

Required parameters:
- instance_id: The ID of the source instance
- snapshot_name: Name for the snapshot/custom image
- description: Description for the snapshot (optional)

The snapshot will be stored in the ACR registry and can be used as an image_url
in future CreateInstance requests.
"""

import os
import sys
import json
import time
from alibabacloud_pai_dsw20220101.client import Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_pai_dsw20220101 import models as dsw_models
from alibabacloud_tea_util.models import RuntimeOptions


def get_credentials():
    """Get credentials from ALIBABA_CLOUD_CREDENTIALS_URI environment variable."""
    credentials_uri = os.environ.get('ALIBABA_CLOUD_CREDENTIALS_URI')
    if not credentials_uri:
        raise Exception("ALIBABA_CLOUD_CREDENTIALS_URI environment variable not found")
    
    import requests
    response = requests.get(credentials_uri)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch credentials: HTTP {response.status_code}")
    
    creds = response.json()
    if creds.get('Code') != 'Success':
        raise Exception(f"Failed to get valid credentials: {creds.get('Message', 'Unknown error')}")
    
    return creds


def create_client(region_id="cn-beijing"):
    """Create PAI-DSW client with proper authentication."""
    creds = get_credentials()
    
    config = open_api_models.Config(
        access_key_id=creds['AccessKeyId'],
        access_key_secret=creds['AccessKeySecret'],
        security_token=creds['SecurityToken'],
        region_id=region_id
    )
    
    return Client(config)


def create_instance_snapshot(instance_id, snapshot_name, description=None, region_id="cn-beijing"):
    """
    Create a snapshot (custom image) from a running DSW instance.
    
    Args:
        instance_id (str): ID of the source instance
        snapshot_name (str): Name for the snapshot
        description (str, optional): Description for the snapshot
        region_id (str): Region ID (default: cn-beijing)
    
    Returns:
        dict: Snapshot creation response containing snapshot_id and image_url
    """
    client = create_client(region_id)
    
    # Construct the image URL for the custom repository
    # Format: dsw-registry-vpc.{region}.cr.aliyuncs.com/pai/{snapshot_name}:{snapshot_name}
    image_url = f"dsw-registry-vpc.{region_id}.cr.aliyuncs.com/pai/{snapshot_name}:{snapshot_name}"
    
    # Create the snapshot request
    request = dsw_models.CreateInstanceSnapshotRequest(
        snapshot_name=snapshot_name,
        snapshot_description=description,
        image_url=image_url
    )
    
    runtime = RuntimeOptions()
    
    try:
        response = client.create_instance_snapshot_with_options(instance_id, request, None, runtime)
        
        if response.body and response.body.success:
            return {
                'snapshot_id': response.body.snapshot_id,
                'instance_id': response.body.instance_id,
                'image_url': image_url,
                'snapshot_name': snapshot_name,
                'description': description
            }
        else:
            error_msg = getattr(response.body, 'message', 'Unknown error')
            raise Exception(f"Snapshot creation failed: {error_msg}")
            
    except Exception as e:
        raise Exception(f"Error creating snapshot: {e}")


def main():
    """Main function for command-line usage."""
    if len(sys.argv) < 3:
        print("Usage: python create_snapshot.py <instance_id> <snapshot_name> [description]")
        sys.exit(1)
    
    instance_id = sys.argv[1]
    snapshot_name = sys.argv[2]
    description = sys.argv[3] if len(sys.argv) > 3 else None
    
    try:
        print(f"Creating snapshot from instance: {instance_id}")
        print(f"Snapshot name: {snapshot_name}")
        if description:
            print(f"Description: {description}")
        
        result = create_instance_snapshot(instance_id, snapshot_name, description)
        
        print("\n✅ Successfully created snapshot!")
        print(f"   Snapshot ID: {result['snapshot_id']}")
        print(f"   Snapshot Name: {result['snapshot_name']}")
        print(f"   Image URL: {result['image_url']}")
        if result['description']:
            print(f"   Description: {result['description']}")
        
        print(f"\n🎉 You can now use this custom image in future DSW instances.")
        print(f"   Image URL: {result['image_url']}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()