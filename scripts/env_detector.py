#!/usr/bin/env python3
"""
Environment Detector for PAI-DSW Skill.

Detects the runtime environment and available credential sources.
Provides unified configuration for both DSW and non-DSW environments.
"""

import os
import sys
import json
import platform
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, List

# 配置文件路径
CONFIG_DIR = Path.home() / '.dsw'
CONFIG_FILE = CONFIG_DIR / 'config.json'


class Environment(Enum):
    """运行环境类型"""
    DSW_INSTANCE = "dsw_instance"      # 阿里云 DSW 实例
    LOCAL = "local"                     # 本地开发环境
    OTHER_CLOUD = "other_cloud"         # 其他云环境
    UNKNOWN = "unknown"


class CredentialSource(Enum):
    """凭证来源"""
    RAM_ROLE = "ram_role"               # DSW RAM 角色
    ENVIRONMENT = "environment"         # 环境变量
    CONFIG_FILE = "config_file"         # 配置文件
    INTERACTIVE = "interactive"         # 交互式输入
    NONE = "none"                       # 无可用凭证


@dataclass
class EnvironmentInfo:
    """环境信息"""
    environment: Environment = Environment.UNKNOWN
    is_dsw: bool = False
    hostname: str = ""
    region: Optional[str] = None
    workspace_id: Optional[str] = None
    credential_source: CredentialSource = CredentialSource.NONE
    available_sources: List[CredentialSource] = field(default_factory=list)
    config_exists: bool = False
    config_path: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'environment': self.environment.value,
            'is_dsw': self.is_dsw,
            'hostname': self.hostname,
            'region': self.region,
            'workspace_id': self.workspace_id,
            'credential_source': self.credential_source.value,
            'available_sources': [s.value for s in self.available_sources],
            'config_exists': self.config_exists,
            'config_path': self.config_path,
        }


def detect_environment() -> EnvironmentInfo:
    """
    检测当前运行环境。
    
    Returns:
        EnvironmentInfo: 环境信息对象
    """
    info = EnvironmentInfo()
    info.hostname = os.getenv('HOSTNAME', platform.node())
    
    # 检测是否在 DSW 实例中
    info.is_dsw = _is_dsw_instance()
    
    if info.is_dsw:
        info.environment = Environment.DSW_INSTANCE
    elif _is_other_cloud():
        info.environment = Environment.OTHER_CLOUD
    else:
        info.environment = Environment.LOCAL
    
    # 检测可用凭证来源
    info.available_sources = _detect_available_credential_sources()
    
    # 确定最佳凭证来源
    info.credential_source = _determine_best_credential_source(info.available_sources)
    
    # 检测配置文件
    info.config_exists = CONFIG_FILE.exists()
    info.config_path = str(CONFIG_FILE) if info.config_exists else None
    
    # 从配置文件加载默认值
    if info.config_exists:
        config = load_config()
        info.region = config.get('region')
        info.workspace_id = config.get('workspace_id')
    
    # 环境变量覆盖
    env_region = os.getenv('ALIBABA_CLOUD_REGION_ID') or os.getenv('REGION')
    if env_region:
        info.region = env_region
    
    env_workspace = os.getenv('PAI_WORKSPACE_ID')
    if env_workspace:
        info.workspace_id = env_workspace
    
    return info


def _is_dsw_instance() -> bool:
    """
    检测是否在 DSW 实例中运行。
    
    DSW 实例特征：
    - 存在 ALIBABA_CLOUD_CREDENTIALS_URI 环境变量
    - hostname 以 dsw- 开头
    - 存在 PAI_WORKSPACE_ID 环境变量
    """
    # 检查 DSW 特有环境变量
    if os.getenv('ALIBABA_CLOUD_CREDENTIALS_URI'):
        return True
    
    # 检查 hostname
    hostname = os.getenv('HOSTNAME', '')
    if hostname.startswith('dsw-'):
        return True
    
    # 检查 PAI 环境变量组合
    if os.getenv('PAI_WORKSPACE_ID') and os.getenv('ALIBABA_CLOUD_REGION_ID'):
        return True
    
    return False


def _is_other_cloud() -> bool:
    """检测是否在其他云环境中"""
    # AWS
    if os.getenv('AWS_EXECUTION_ENV') or os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
        return True
    
    # GCP
    if os.getenv('GCP_PROJECT') or os.getenv('GOOGLE_CLOUD_PROJECT'):
        return True
    
    # Azure
    if os.getenv('AZURE_FUNCTIONS_ENVIRONMENT') or os.getenv('WEBSITE_INSTANCE_ID'):
        return True
    
    return False


def _detect_available_credential_sources() -> List[CredentialSource]:
    """检测可用的凭证来源"""
    sources = []
    
    # 检查 RAM 角色 (DSW 特有)
    if os.getenv('ALIBABA_CLOUD_CREDENTIALS_URI'):
        sources.append(CredentialSource.RAM_ROLE)
    
    # 检查环境变量
    if os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID') and os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET'):
        sources.append(CredentialSource.ENVIRONMENT)
    
    # 检查配置文件
    if CONFIG_FILE.exists():
        sources.append(CredentialSource.CONFIG_FILE)
    
    return sources


def _determine_best_credential_source(available: List[CredentialSource]) -> CredentialSource:
    """确定最佳凭证来源（优先级排序）"""
    priority = [
        CredentialSource.RAM_ROLE,      # DSW 内优先使用 RAM 角色
        CredentialSource.CONFIG_FILE,   # 配置文件次之
        CredentialSource.ENVIRONMENT,   # 环境变量
        CredentialSource.INTERACTIVE,   # 交互式输入
    ]
    
    for source in priority:
        if source in available:
            return source
    
    return CredentialSource.NONE


def load_config() -> Dict:
    """
    加载配置文件。
    
    Returns:
        配置字典
    """
    if not CONFIG_FILE.exists():
        return {}
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ 无法加载配置文件: {e}", file=sys.stderr)
        return {}


def save_config(config: Dict) -> bool:
    """
    保存配置文件。
    
    Args:
        config: 配置字典
    
    Returns:
        是否成功
    """
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ 无法保存配置文件: {e}", file=sys.stderr)
        return False


def get_credential_from_config() -> Optional[Dict]:
    """
    从配置文件获取凭证。
    
    Returns:
        凭证字典或 None
    """
    config = load_config()
    
    if 'access_key_id' in config and 'access_key_secret' in config:
        return {
            'access_key_id': config['access_key_id'],
            'access_key_secret': config['access_key_secret'],
            'security_token': config.get('security_token'),
        }
    
    return None


def setup_interactive() -> Dict:
    """
    交互式配置向导。
    
    Returns:
        配置字典
    """
    print("\n" + "=" * 60)
    print("  PAI-DSW Skill 配置向导")
    print("=" * 60)
    print("\n检测到您不在 DSW 实例中运行，需要进行配置。\n")
    
    config = {}
    
    # Access Key ID
    print("请输入阿里云 AccessKey 信息：")
    print("（可在阿里云控制台 -> 右上角头像 -> AccessKey 管理 中获取）\n")
    
    access_key_id = input("AccessKey ID: ").strip()
    if not access_key_id:
        print("❌ AccessKey ID 不能为空")
        return {}
    config['access_key_id'] = access_key_id
    
    # Access Key Secret
    import getpass
    access_key_secret = getpass.getpass("AccessKey Secret (输入隐藏): ").strip()
    if not access_key_secret:
        print("❌ AccessKey Secret 不能为空")
        return {}
    config['access_key_secret'] = access_key_secret
    
    # Region
    print("\n常用区域：")
    regions = [
        ('cn-hangzhou', '华东1（杭州）'),
        ('cn-shanghai', '华东2（上海）'),
        ('cn-beijing', '华北2（北京）'),
        ('cn-shenzhen', '华南1（深圳）'),
        ('ap-southeast-1', '新加坡'),
        ('ap-northeast-1', '东京'),
        ('us-east-1', '美东1（弗吉尼亚）'),
        ('eu-central-1', '德国（法兰克福）'),
    ]
    for i, (code, name) in enumerate(regions, 1):
        print(f"  {i}. {name} ({code})")
    
    region_input = input("\n请输入区域编号或区域ID [默认: cn-hangzhou]: ").strip()
    
    if region_input.isdigit():
        idx = int(region_input) - 1
        if 0 <= idx < len(regions):
            config['region'] = regions[idx][0]
        else:
            config['region'] = 'cn-hangzhou'
    elif region_input:
        config['region'] = region_input
    else:
        config['region'] = 'cn-hangzhou'
    
    # Workspace ID
    workspace_input = input("\n工作空间ID（可选，稍后可通过 dsw config workspace 设置）: ").strip()
    if workspace_input:
        config['workspace_id'] = workspace_input
    
    # 保存配置
    print("\n是否保存配置到 ~/.dsw/config.json？")
    save_choice = input("保存配置？[Y/n]: ").strip().lower()
    
    if save_choice != 'n':
        if save_config(config):
            print("✅ 配置已保存")
        else:
            print("⚠️ 配置保存失败")
    
    print("\n" + "=" * 60)
    
    return config


def print_environment_info(info: EnvironmentInfo = None):
    """打印环境信息"""
    if info is None:
        info = detect_environment()
    
    print("\n" + "=" * 60)
    print("  PAI-DSW Skill 环境信息")
    print("=" * 60)
    
    env_names = {
        Environment.DSW_INSTANCE: "阿里云 DSW 实例 🚀",
        Environment.LOCAL: "本地开发环境 💻",
        Environment.OTHER_CLOUD: "其他云环境 ☁️",
        Environment.UNKNOWN: "未知环境 ❓",
    }
    
    print(f"\n  运行环境: {env_names.get(info.environment, '未知')}")
    print(f"  主机名: {info.hostname}")
    print(f"  区域: {info.region or '未设置'}")
    print(f"  工作空间: {info.workspace_id or '未设置'}")
    
    source_names = {
        CredentialSource.RAM_ROLE: "DSW RAM 角色",
        CredentialSource.ENVIRONMENT: "环境变量",
        CredentialSource.CONFIG_FILE: "配置文件",
        CredentialSource.INTERACTIVE: "交互式输入",
        CredentialSource.NONE: "无可用凭证 ❌",
    }
    
    print(f"\n  凭证来源: {source_names.get(info.credential_source, '未知')}")
    
    if info.available_sources:
        available_names = [source_names.get(s, str(s)) for s in info.available_sources]
        print(f"  可用来源: {', '.join(available_names)}")
    
    if info.config_exists:
        print(f"\n  配置文件: {info.config_path}")
    
    print("\n" + "=" * 60 + "\n")


def ensure_configured() -> bool:
    """
    确保已配置凭证。
    
    Returns:
        是否已配置
    """
    info = detect_environment()
    
    if info.credential_source != CredentialSource.NONE:
        return True
    
    print("\n⚠️ 未检测到有效的阿里云凭证配置")
    print("\n请选择配置方式：")
    print("  1. 交互式配置（推荐）")
    print("  2. 设置环境变量")
    print("  3. 退出")
    
    choice = input("\n请选择 [1/2/3]: ").strip()
    
    if choice == '1':
        config = setup_interactive()
        return bool(config)
    elif choice == '2':
        print("\n请设置以下环境变量：")
        print("  export ALIBABA_CLOUD_ACCESS_KEY_ID=<your-access-key-id>")
        print("  export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<your-access-key-secret>")
        print("  export ALIBABA_CLOUD_REGION_ID=<region-id>")
        print("  export PAI_WORKSPACE_ID=<workspace-id>")
        return False
    else:
        return False


if __name__ == "__main__":
    # 测试环境检测
    info = detect_environment()
    print_environment_info(info)