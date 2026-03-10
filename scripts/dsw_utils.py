#!/usr/bin/env python3
"""
DSW Utilities - Common functions for PAI-DSW scripts.

This module provides:
- Credential retrieval from multiple sources (RAM role, env, config file)
- Client creation with proper configuration
- Workspace ID detection
- API rate limiting and retry support

Supports both DSW instance and non-DSW environments.
"""

import os
import sys
import requests

try:
    from alibabacloud_pai_dsw20220101.client import Client
    from alibabacloud_tea_openapi import models as open_api_models
except ImportError as e:
    print(f"❌ Required packages not installed: {e}")
    print("Install with: pip install alibabacloud-pai-dsw20220101")
    sys.exit(1)

# 导入环境检测模块
try:
    from env_detector import (
        detect_environment, 
        load_config, 
        get_credential_from_config,
        setup_interactive,
        ensure_configured,
        Environment,
        CredentialSource,
        CONFIG_FILE,
    )
    ENV_DETECTOR_AVAILABLE = True
except ImportError:
    ENV_DETECTOR_AVAILABLE = False

# 导入限流模块
try:
    from rate_limiter import RateLimitedClient, RateLimitConfig, RetryStrategy, get_retry_stats
    RATE_LIMITER_AVAILABLE = True
except ImportError:
    RATE_LIMITER_AVAILABLE = False


def get_credentials() -> dict:
    """
    Get credentials from multiple sources.
    
    Priority:
    1. Environment variables (ALIBABA_CLOUD_ACCESS_KEY_ID, ALIBABA_CLOUD_ACCESS_KEY_SECRET)
    2. Config file (~/.dsw/config.json)
    3. RAM role credentials URI (DSW instance)
    4. Interactive setup (if no credentials found)
    
    Returns:
        dict with access_key_id, access_key_secret, security_token
    """
    # Try environment variables first
    access_key_id = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID')
    access_key_secret = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
    security_token = os.getenv('ALIBABA_CLOUD_SECURITY_TOKEN')
    
    if access_key_id and access_key_secret:
        return {
            'access_key_id': access_key_id,
            'access_key_secret': access_key_secret,
            'security_token': security_token
        }
    
    # Try config file
    if ENV_DETECTOR_AVAILABLE:
        creds = get_credential_from_config()
        if creds:
            return creds
    
    # Try credentials URI (for DSW instances with RAM role)
    credentials_uri = os.getenv('ALIBABA_CLOUD_CREDENTIALS_URI')
    if credentials_uri:
        try:
            response = requests.get(credentials_uri, timeout=10)
            if response.status_code == 200:
                creds = response.json()
                if creds.get('Code') == 'Success':
                    return {
                        'access_key_id': creds['AccessKeyId'],
                        'access_key_secret': creds['AccessKeySecret'],
                        'security_token': creds['SecurityToken']
                    }
        except Exception as e:
            print(f"⚠️ Failed to get credentials from URI: {e}", file=sys.stderr)
    
    # No credentials found - provide helpful message
    if ENV_DETECTOR_AVAILABLE:
        print("\n❌ 未找到有效的阿里云凭证配置\n")
        print("请使用以下方式之一配置凭证：\n")
        print("  方式 1: 交互式配置（推荐）")
        print("    dsw config init\n")
        print("  方式 2: 设置环境变量")
        print("    export ALIBABA_CLOUD_ACCESS_KEY_ID=<your-access-key-id>")
        print("    export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<your-access-key-secret>\n")
        print("  方式 3: 配置文件")
        print(f"    创建 {CONFIG_FILE}")
        print("    内容: {\"access_key_id\": \"...\", \"access_key_secret\": \"...\"}\n")
        sys.exit(1)
    else:
        raise Exception(
            "No valid credentials found. Set ALIBABA_CLOUD_ACCESS_KEY_ID and "
            "ALIBABA_CLOUD_ACCESS_KEY_SECRET, or run 'dsw config init' to configure."
        )


def create_client(region_id: str = None, with_rate_limit: bool = True) -> Client:
    """
    Create PAI-DSW client with proper authentication.
    
    Supports both DSW and non-DSW environments.
    
    Args:
        region_id: Region ID (default: from config/env or cn-hangzhou)
        with_rate_limit: 是否启用限流功能（默认启用）
    
    Returns:
        PAI-DSW Client instance（如果启用限流，返回 RateLimitedClient 包装）
    """
    if region_id is None:
        region_id = get_region_id()
    
    creds = get_credentials()
    
    # Build endpoint based on region
    endpoint = f"pai-dsw.{region_id}.aliyuncs.com"
    
    config = open_api_models.Config(
        access_key_id=creds['access_key_id'],
        access_key_secret=creds['access_key_secret'],
        security_token=creds['security_token'],
        endpoint=endpoint,
        region_id=region_id
    )
    
    client = Client(config)
    
    # 如果启用限流且限流模块可用，返回包装客户端
    if with_rate_limit and RATE_LIMITER_AVAILABLE:
        rate_config = get_rate_limit_config()
        return RateLimitedClient(
            client,
            max_retries=rate_config['max_retries'],
            backoff_factor=rate_config['backoff_factor'],
            base_delay=rate_config['base_delay'],
            max_delay=rate_config['max_delay'],
            strategy=rate_config['strategy'],
            rate_limit=rate_config['rate_limit'],
            period=rate_config['period'],
        )
    
    return client


def get_region_id() -> str:
    """
    Get region ID from multiple sources.
    
    Priority:
    1. Environment variable (ALIBABA_CLOUD_REGION_ID, REGION)
    2. Config file
    3. Default (cn-hangzhou)
    
    Returns:
        Region ID string
    """
    # Environment variables
    region = os.getenv('ALIBABA_CLOUD_REGION_ID') or os.getenv('REGION')
    if region:
        return region
    
    # Config file
    if ENV_DETECTOR_AVAILABLE:
        config = load_config()
        if config.get('region'):
            return config['region']
    
    # Default
    return 'cn-hangzhou'


def get_workspace_id(allow_interactive: bool = True) -> str:
    """
    Get workspace ID from multiple sources.
    
    Priority:
    1. Environment variable (PAI_WORKSPACE_ID)
    2. Config file
    3. Interactive selection (if allow_interactive=True)
    
    Args:
        allow_interactive: 是否允许交互式选择
    
    Returns:
        Workspace ID string
    
    Raises:
        Exception: 如果无法获取工作空间ID
    """
    # Environment variable
    workspace_id = os.getenv('PAI_WORKSPACE_ID')
    if workspace_id:
        return workspace_id
    
    # Config file
    if ENV_DETECTOR_AVAILABLE:
        config = load_config()
        if config.get('workspace_id'):
            return config['workspace_id']
    
    # Interactive
    if allow_interactive:
        print("\n⚠️ 未设置工作空间ID\n")
        print("请选择：")
        print("  1. 输入工作空间ID")
        print("  2. 列出可用工作空间")
        print("  3. 退出\n")
        
        choice = input("请选择 [1/2/3]: ").strip()
        
        if choice == '1':
            workspace_id = input("请输入工作空间ID: ").strip()
            if workspace_id:
                # 保存到配置
                if ENV_DETECTOR_AVAILABLE:
                    config = load_config()
                    config['workspace_id'] = workspace_id
                    from env_detector import save_config
                    save_config(config)
                    print(f"✅ 工作空间已保存: {workspace_id}")
                return workspace_id
        elif choice == '2':
            # 尝试列出工作空间
            try:
                client = create_client()
                from alibabacloud_pai_dsw20220101 import models as dsw_models
                request = dsw_models.ListWorkspacesRequest()
                response = client.list_workspaces(request)
                
                if response.body and response.body.workspaces:
                    print("\n可用工作空间：")
                    for i, ws in enumerate(response.body.workspaces, 1):
                        print(f"  {i}. {ws.workspace_name} ({ws.workspace_id})")
                    
                    ws_choice = input("\n请选择工作空间编号: ").strip()
                    if ws_choice.isdigit():
                        idx = int(ws_choice) - 1
                        if 0 <= idx < len(response.body.workspaces):
                            selected = response.body.workspaces[idx]
                            workspace_id = selected.workspace_id
                            # 保存
                            if ENV_DETECTOR_AVAILABLE:
                                config = load_config()
                                config['workspace_id'] = workspace_id
                                from env_detector import save_config
                                save_config(config)
                                print(f"✅ 已选择工作空间: {selected.workspace_name} ({workspace_id})")
                            return workspace_id
            except Exception as e:
                print(f"❌ 无法列出工作空间: {e}")
    
    raise Exception(
        "PAI_WORKSPACE_ID not found. Set environment variable, "
        "add to config file, or run 'dsw config workspace'."
    )


def get_rate_limit_config() -> dict:
    """
    获取限流配置（从环境变量或使用默认值）
    
    Returns:
        限流配置字典
    """
    return {
        'max_retries': int(os.getenv('DSW_MAX_RETRIES', '3')),
        'backoff_factor': float(os.getenv('DSW_BACKOFF_FACTOR', '2.0')),
        'base_delay': float(os.getenv('DSW_BASE_DELAY', '1.0')),
        'max_delay': float(os.getenv('DSW_MAX_DELAY', '60.0')),
        'strategy': RetryStrategy.JITTERED if RATE_LIMITER_AVAILABLE else None,
        'rate_limit': int(os.getenv('DSW_RATE_LIMIT', '20')),
        'period': float(os.getenv('DSW_RATE_PERIOD', '1.0')),
    }


def print_rate_limit_stats():
    """打印限流统计信息"""
    if not RATE_LIMITER_AVAILABLE:
        print("⚠️ 限流模块未加载")
        return
    
    stats = get_retry_stats()
    print("\n📊 API 调用统计:")
    print(f"  总调用: {stats.total_calls}")
    print(f"  成功: {stats.successful_calls}")
    print(f"  失败: {stats.failed_calls}")
    print(f"  重试次数: {stats.total_retries}")
    print(f"  总等待时间: {stats.total_wait_time:.2f}s")
    if stats.last_error:
        print(f"  最后错误: {stats.last_error}")
    if stats.last_retry_time:
        print(f"  最后重试时间: {stats.last_retry_time.strftime('%Y-%m-%d %H:%M:%S')}")


def is_dsw_environment() -> bool:
    """检查是否在 DSW 实例中运行"""
    if ENV_DETECTOR_AVAILABLE:
        info = detect_environment()
        return info.is_dsw
    
    # 简单检查
    return bool(os.getenv('ALIBABA_CLOUD_CREDENTIALS_URI')) or os.getenv('HOSTNAME', '').startswith('dsw-')


def print_environment_info():
    """打印环境信息"""
    if ENV_DETECTOR_AVAILABLE:
        from env_detector import print_environment_info
        print_environment_info()
    else:
        print(f"\n环境信息:")
        print(f"  DSW 环境: {'是' if is_dsw_environment() else '否'}")
        print(f"  区域: {get_region_id()}")
        workspace = os.getenv('PAI_WORKSPACE_ID', '未设置')
        print(f"  工作空间: {workspace}")
        print()


def print_table(headers: list, rows: list, title: str = None):
    """
    打印表格
    
    Args:
        headers: 表头列表
        rows: 数据行列表
        title: 可选标题
    """
    if title:
        print(f"\n{title}\n")
    
    # 计算列宽
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # 打印表头
    header_line = '  '.join(h.ljust(w) for h, w in zip(headers, col_widths))
    print(header_line)
    print('-' * len(header_line))
    
    # 打印数据行
    for row in rows:
        print('  '.join(str(cell).ljust(w) for cell, w in zip(row, col_widths)))


def get_current_instance_id() -> str:
    """Get current DSW instance ID from hostname."""
    hostname = os.getenv('HOSTNAME', '')
    if hostname.startswith('dsw-'):
        return hostname
    return hostname