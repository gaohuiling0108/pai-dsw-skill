#!/usr/bin/env python3
"""
Multi-Region Support for PAI-DSW
多区域支持模块：区域自动检测、跨区域实例管理

功能:
- 自动检测当前区域
- 列出所有可用区域
- 跨区域查询实例
- 跨区域实例操作
- 区域性能测试
- 区域资源统计
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from alibabacloud_pai_dsw20220101.client import Client
    from alibabacloud_tea_openapi import models as open_api_models
    from alibabacloud_tea_util import models as util_models
    from alibabacloud_pai_dsw20220101 import models as dsw_models
except ImportError as e:
    print(f"❌ 缺少依赖: {e}")
    print("安装: pip install alibabacloud-pai-dsw20220101")
    sys.exit(1)

# 颜色定义
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    
    @classmethod
    def disable(cls):
        for attr in ['RESET', 'BOLD', 'RED', 'GREEN', 'YELLOW', 'BLUE', 
                     'MAGENTA', 'CYAN', 'WHITE']:
            setattr(cls, attr, '')


def colorize(text: str, color: str) -> str:
    return f"{color}{text}{Colors.RESET}"


# PAI-DSW 支持的区域列表
PAI_REGIONS = {
    'cn-hangzhou': {
        'name': '华东1（杭州）',
        'endpoint': 'pai-dsw.cn-hangzhou.aliyuncs.com',
        'status': 'active',
        'features': ['gpu', 'cpu', 'spot'],
    },
    'cn-shanghai': {
        'name': '华东2（上海）',
        'endpoint': 'pai-dsw.cn-shanghai.aliyuncs.com',
        'status': 'active',
        'features': ['gpu', 'cpu', 'spot'],
    },
    'cn-beijing': {
        'name': '华北2（北京）',
        'endpoint': 'pai-dsw.cn-beijing.aliyuncs.com',
        'status': 'active',
        'features': ['gpu', 'cpu', 'spot'],
    },
    'cn-shenzhen': {
        'name': '华南1（深圳）',
        'endpoint': 'pai-dsw.cn-shenzhen.aliyuncs.com',
        'status': 'active',
        'features': ['gpu', 'cpu', 'spot'],
    },
    'cn-hongkong': {
        'name': '中国香港',
        'endpoint': 'pai-dsw.cn-hongkong.aliyuncs.com',
        'status': 'active',
        'features': ['gpu', 'cpu'],
    },
    'cn-qingdao': {
        'name': '华北1（青岛）',
        'endpoint': 'pai-dsw.cn-qingdao.aliyuncs.com',
        'status': 'active',
        'features': ['cpu'],
    },
    'cn-zhangjiakou': {
        'name': '华北3（张家口）',
        'endpoint': 'pai-dsw.cn-zhangjiakou.aliyuncs.com',
        'status': 'active',
        'features': ['gpu', 'cpu'],
    },
    'cn-huhehaote': {
        'name': '华北5（呼和浩特）',
        'endpoint': 'pai-dsw.cn-huhehaote.aliyuncs.com',
        'status': 'active',
        'features': ['gpu', 'cpu'],
    },
    'cn-wulanchabu': {
        'name': '华北6（乌兰察布）',
        'endpoint': 'pai-dsw.cn-wulanchabu.aliyuncs.com',
        'status': 'active',
        'features': ['gpu', 'cpu', 'spot'],
    },
    'ap-northeast-1': {
        'name': '日本东京',
        'endpoint': 'pai-dsw.ap-northeast-1.aliyuncs.com',
        'status': 'active',
        'features': ['gpu', 'cpu'],
    },
    'ap-southeast-1': {
        'name': '新加坡',
        'endpoint': 'pai-dsw.ap-southeast-1.aliyuncs.com',
        'status': 'active',
        'features': ['gpu', 'cpu'],
    },
    'ap-southeast-3': {
        'name': '马来西亚吉隆坡',
        'endpoint': 'pai-dsw.ap-southeast-3.aliyuncs.com',
        'status': 'active',
        'features': ['cpu'],
    },
    'us-west-1': {
        'name': '美国西部1（硅谷）',
        'endpoint': 'pai-dsw.us-west-1.aliyuncs.com',
        'status': 'active',
        'features': ['gpu', 'cpu'],
    },
    'us-east-1': {
        'name': '美国东部1（弗吉尼亚）',
        'endpoint': 'pai-dsw.us-east-1.aliyuncs.com',
        'status': 'active',
        'features': ['gpu', 'cpu'],
    },
    'eu-central-1': {
        'name': '德国法兰克福',
        'endpoint': 'pai-dsw.eu-central-1.aliyuncs.com',
        'status': 'active',
        'features': ['gpu', 'cpu'],
    },
}


def get_credentials() -> dict:
    """获取凭证（从环境变量或元数据服务）"""
    access_key_id = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID')
    access_key_secret = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
    security_token = os.getenv('ALIBABA_CLOUD_SECURITY_TOKEN')
    
    if access_key_id and access_key_secret:
        return {
            'access_key_id': access_key_id,
            'access_key_secret': access_key_secret,
            'security_token': security_token
        }
    
    # 尝试从元数据服务获取
    credentials_uri = os.getenv('ALIBABA_CLOUD_CREDENTIALS_URI')
    if credentials_uri:
        import requests
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
        except Exception:
            pass
    
    raise Exception("未找到有效凭证。请设置 ALIBABA_CLOUD_ACCESS_KEY_ID 和 ALIBABA_CLOUD_ACCESS_KEY_SECRET")


def create_region_client(region_id: str, creds: dict = None) -> Client:
    """创建指定区域的客户端"""
    if creds is None:
        creds = get_credentials()
    
    region_info = PAI_REGIONS.get(region_id)
    if not region_info:
        raise ValueError(f"不支持的区域: {region_id}")
    
    endpoint = region_info['endpoint']
    
    config = open_api_models.Config(
        access_key_id=creds['access_key_id'],
        access_key_secret=creds['access_key_secret'],
        security_token=creds['security_token'],
        endpoint=endpoint,
        region_id=region_id
    )
    
    return Client(config)


def detect_current_region() -> Optional[str]:
    """
    自动检测当前区域
    
    优先级:
    1. 环境变量 ALIBABA_CLOUD_REGION_ID
    2. 环境变量 REGION
    3. 从 DSW 实例元数据获取
    4. 从可用区推断
    
    Returns:
        区域 ID 或 None
    """
    # 1. 环境变量
    region = os.getenv('ALIBABA_CLOUD_REGION_ID') or os.getenv('REGION')
    if region:
        return region
    
    # 2. 从 DSW 实例元数据获取
    try:
        import requests
        # 尝试从 ECS 元数据服务获取区域信息
        metadata_url = "http://100.100.100.200/latest/meta-data/region-id"
        response = requests.get(metadata_url, timeout=2)
        if response.status_code == 200:
            return response.text.strip()
    except Exception:
        pass
    
    # 3. 从可用区推断
    try:
        import requests
        zone_url = "http://100.100.100.200/latest/meta-data/zone-id"
        response = requests.get(zone_url, timeout=2)
        if response.status_code == 200:
            zone = response.text.strip()
            # 从可用区 ID 推断区域 ID
            # 如 cn-hangzhou-i -> cn-hangzhou
            if zone:
                return zone.rsplit('-', 1)[0] if '-' in zone else zone
    except Exception:
        pass
    
    return None


def get_workspace_id() -> str:
    """获取当前工作空间 ID"""
    workspace_id = os.getenv('PAI_WORKSPACE_ID')
    if not workspace_id:
        raise Exception("PAI_WORKSPACE_ID 未设置")
    return workspace_id


def list_instances_in_region(region_id: str, workspace_id: str = None, 
                            creds: dict = None) -> List[Dict]:
    """
    列出指定区域的所有实例
    
    Args:
        region_id: 区域 ID
        workspace_id: 工作空间 ID（可选）
        creds: 凭证（可选）
    
    Returns:
        实例列表
    """
    try:
        client = create_region_client(region_id, creds)
        runtime = util_models.RuntimeOptions()
        
        request = dsw_models.ListInstancesRequest()
        if workspace_id:
            request.workspace_id = workspace_id
        
        all_instances = []
        page_number = 1
        page_size = 100
        
        while True:
            request.page_number = page_number
            request.page_size = page_size
            
            response = client.list_instances_with_options(request, runtime)
            
            if response.body and response.body.instances:
                instances = response.body.instances
                all_instances.extend([
                    {
                        'InstanceId': inst.instance_id,
                        'InstanceName': inst.instance_name,
                        'Status': inst.status,
                        'InstanceType': inst.instance_type,
                        'RegionId': region_id,
                        'RegionName': PAI_REGIONS.get(region_id, {}).get('name', region_id),
                        'GpuCount': inst.gpu_count if hasattr(inst, 'gpu_count') else 0,
                        'CreateTime': inst.create_time if hasattr(inst, 'create_time') else None,
                        'WorkspaceId': inst.workspace_id if hasattr(inst, 'workspace_id') else None,
                    }
                    for inst in instances
                ])
            
            if len(response.body.instances) < page_size:
                break
            page_number += 1
        
        return all_instances
        
    except Exception as e:
        return {'error': str(e), 'region': region_id}


def test_region_connectivity(region_id: str, creds: dict = None) -> Dict:
    """
    测试区域连接性
    
    Returns:
        包含延迟和状态的字典
    """
    result = {
        'region_id': region_id,
        'region_name': PAI_REGIONS.get(region_id, {}).get('name', region_id),
        'status': 'unknown',
        'latency_ms': None,
        'error': None
    }
    
    try:
        start_time = time.time()
        client = create_region_client(region_id, creds)
        
        # 尝试一个简单的 API 调用
        runtime = util_models.RuntimeOptions()
        runtime.read_timeout = 10000  # 10秒超时
        runtime.connect_timeout = 5000  # 5秒连接超时
        
        request = dsw_models.ListInstancesRequest()
        request.page_number = 1
        request.page_size = 1
        
        client.list_instances_with_options(request, runtime)
        
        end_time = time.time()
        latency_ms = round((end_time - start_time) * 1000, 2)
        
        result['status'] = 'available'
        result['latency_ms'] = latency_ms
        
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
    
    return result


def list_available_regions(creds: dict = None, check_connectivity: bool = False) -> List[Dict]:
    """
    列出所有可用区域
    
    Args:
        creds: 凭证
        check_connectivity: 是否测试连接性
    
    Returns:
        区域信息列表
    """
    regions = []
    
    if check_connectivity:
        # 并行测试所有区域
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(test_region_connectivity, region_id, creds): region_id
                for region_id in PAI_REGIONS.keys()
            }
            
            for future in as_completed(futures):
                result = future.result()
                regions.append(result)
    else:
        # 仅返回静态配置
        for region_id, info in PAI_REGIONS.items():
            regions.append({
                'region_id': region_id,
                'region_name': info['name'],
                'status': info['status'],
                'features': info['features'],
                'endpoint': info['endpoint']
            })
    
    return regions


def query_all_regions(workspace_id: str = None, creds: dict = None,
                      regions: List[str] = None) -> Dict[str, List]:
    """
    跨区域查询所有实例
    
    Args:
        workspace_id: 工作空间 ID
        creds: 凭证
        regions: 要查询的区域列表（默认所有区域）
    
    Returns:
        {region_id: [instances]} 字典
    """
    if regions is None:
        regions = list(PAI_REGIONS.keys())
    
    results = {}
    
    # 并行查询所有区域
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(list_instances_in_region, region, workspace_id, creds): region
            for region in regions
        }
        
        for future in as_completed(futures):
            region = futures[future]
            try:
                instances = future.result()
                if isinstance(instances, dict) and 'error' in instances:
                    results[region] = instances
                else:
                    results[region] = instances
            except Exception as e:
                results[region] = {'error': str(e), 'region': region}
    
    return results


def get_region_statistics(instances_by_region: Dict[str, List]) -> Dict:
    """
    计算区域统计信息
    
    Args:
        instances_by_region: 按区域分组的实例
    
    Returns:
        统计信息字典
    """
    stats = {
        'total_instances': 0,
        'total_running': 0,
        'total_stopped': 0,
        'total_gpu_instances': 0,
        'by_region': {}
    }
    
    for region_id, instances in instances_by_region.items():
        if isinstance(instances, dict) and 'error' in instances:
            continue
        
        region_stats = {
            'total': len(instances),
            'running': 0,
            'stopped': 0,
            'gpu_instances': 0,
            'status': 'ok'
        }
        
        for inst in instances:
            status = inst.get('Status', '').lower()
            if status == 'running':
                region_stats['running'] += 1
            elif status in ['stopped', 'deleted']:
                region_stats['stopped'] += 1
            
            if inst.get('GpuCount', 0) > 0:
                region_stats['gpu_instances'] += 1
        
        stats['by_region'][region_id] = region_stats
        stats['total_instances'] += region_stats['total']
        stats['total_running'] += region_stats['running']
        stats['total_stopped'] += region_stats['stopped']
        stats['total_gpu_instances'] += region_stats['gpu_instances']
    
    return stats


def format_region_table(regions: List[Dict], output_format: str = 'table') -> str:
    """格式化区域表格输出"""
    if output_format == 'json':
        return json.dumps(regions, indent=2, ensure_ascii=False)
    
    lines = []
    lines.append(f"\n{Colors.BOLD}{Colors.CYAN}PAI-DSW 可用区域{Colors.RESET}\n")
    
    if not regions:
        lines.append("无可用区域信息")
        return '\n'.join(lines)
    
    # 表头
    header = f"{'区域 ID':<20} {'区域名称':<20} {'状态':<12} {'延迟':<10} {'特性':<20}"
    lines.append(header)
    lines.append('-' * 82)
    
    for r in sorted(regions, key=lambda x: x.get('region_id', '')):
        region_id = r.get('region_id', 'N/A')
        region_name = r.get('region_name', 'N/A')
        
        # 状态着色
        status = r.get('status', 'unknown')
        if status == 'available':
            status_str = colorize('✓ 可用', Colors.GREEN)
        elif status == 'error':
            status_str = colorize('✗ 错误', Colors.RED)
        else:
            status_str = colorize('○ 未知', Colors.YELLOW)
        
        # 延迟
        latency = r.get('latency_ms')
        if latency is not None:
            latency_str = f"{latency}ms"
            if latency < 100:
                latency_str = colorize(latency_str, Colors.GREEN)
            elif latency < 500:
                latency_str = colorize(latency_str, Colors.YELLOW)
            else:
                latency_str = colorize(latency_str, Colors.RED)
        else:
            latency_str = '-'
        
        # 特性
        features = r.get('features', [])
        features_str = ', '.join(features) if features else '-'
        
        line = f"{region_id:<20} {region_name:<20} {status_str:<20} {latency_str:<15} {features_str}"
        lines.append(line)
    
    return '\n'.join(lines)


def format_cross_region_instances(instances_by_region: Dict, output_format: str = 'table') -> str:
    """格式化跨区域实例输出"""
    if output_format == 'json':
        return json.dumps(instances_by_region, indent=2, ensure_ascii=False)
    
    lines = []
    lines.append(f"\n{Colors.BOLD}{Colors.CYAN}跨区域实例列表{Colors.RESET}\n")
    
    total_instances = 0
    
    for region_id in sorted(instances_by_region.keys()):
        data = instances_by_region[region_id]
        
        region_name = PAI_REGIONS.get(region_id, {}).get('name', region_id)
        
        if isinstance(data, dict) and 'error' in data:
            lines.append(f"\n{Colors.RED}✗ {region_name} ({region_id}): {data['error']}{Colors.RESET}")
            continue
        
        if not data:
            lines.append(f"\n{Colors.YELLOW}○ {region_name} ({region_id}): 无实例{Colors.RESET}")
            continue
        
        count = len(data)
        total_instances += count
        running = sum(1 for i in data if i.get('Status', '').lower() == 'running')
        
        lines.append(f"\n{Colors.BOLD}{Colors.GREEN}● {region_name} ({region_id}): {count} 个实例 ({running} 运行中){Colors.RESET}")
        
        # 表格
        header = f"  {'实例 ID':<36} {'名称':<25} {'状态':<12} {'规格':<25}"
        lines.append(header)
        lines.append('  ' + '-' * 98)
        
        for inst in sorted(data, key=lambda x: x.get('InstanceName', '')):
            inst_id = inst.get('InstanceId', 'N/A')
            name = inst.get('InstanceName', 'N/A')[:25]
            status = inst.get('Status', 'Unknown')
            spec = inst.get('InstanceType', 'N/A') or 'N/A'
            
            # 状态着色
            if status.lower() == 'running':
                status_str = colorize(status, Colors.GREEN)
            elif status.lower() in ['stopped', 'deleted']:
                status_str = colorize(status, Colors.RED)
            else:
                status_str = colorize(status, Colors.YELLOW)
            
            line = f"  {inst_id:<36} {name:<25} {status_str:<20} {spec:<25}"
            lines.append(line)
    
    lines.append(f"\n{Colors.BOLD}总计: {total_instances} 个实例{Colors.RESET}")
    
    return '\n'.join(lines)


def format_statistics(stats: Dict, output_format: str = 'table') -> str:
    """格式化统计信息"""
    if output_format == 'json':
        return json.dumps(stats, indent=2, ensure_ascii=False)
    
    lines = []
    lines.append(f"\n{Colors.BOLD}{Colors.CYAN}跨区域实例统计{Colors.RESET}\n")
    
    lines.append(f"总实例数: {Colors.BOLD}{stats['total_instances']}{Colors.RESET}")
    lines.append(f"运行中:   {Colors.GREEN}{stats['total_running']}{Colors.RESET}")
    lines.append(f"已停止:   {Colors.RED}{stats['total_stopped']}{Colors.RESET}")
    lines.append(f"GPU 实例: {Colors.YELLOW}{stats['total_gpu_instances']}{Colors.RESET}")
    
    lines.append(f"\n{Colors.BOLD}按区域分布:{Colors.RESET}\n")
    
    header = f"{'区域':<25} {'总数':<8} {'运行中':<8} {'已停止':<8} {'GPU':<8}"
    lines.append(header)
    lines.append('-' * 57)
    
    for region_id, region_stats in sorted(stats['by_region'].items()):
        region_name = PAI_REGIONS.get(region_id, {}).get('name', region_id)
        line = f"{region_name:<25} {region_stats['total']:<8} {region_stats['running']:<8} {region_stats['stopped']:<8} {region_stats['gpu_instances']:<8}"
        lines.append(line)
    
    return '\n'.join(lines)


# ============ CLI 命令 ============

def cmd_detect(args):
    """检测当前区域"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}区域自动检测{Colors.RESET}\n")
    
    region = detect_current_region()
    
    if region:
        region_info = PAI_REGIONS.get(region, {})
        region_name = region_info.get('name', region)
        
        print(f"{Colors.GREEN}✓ 检测到区域:{Colors.RESET}")
        print(f"  区域 ID: {Colors.BOLD}{region}{Colors.RESET}")
        print(f"  区域名称: {region_name}")
        
        if region_info:
            print(f"  端点: {region_info.get('endpoint', 'N/A')}")
            print(f"  支持特性: {', '.join(region_info.get('features', []))}")
    else:
        print(f"{Colors.YELLOW}⚠ 无法自动检测区域{Colors.RESET}")
        print("请通过以下方式之一设置区域:")
        print("  1. 设置环境变量 ALIBABA_CLOUD_REGION_ID")
        print("  2. 设置环境变量 REGION")
        print("  3. 在命令中使用 --region 参数")
    
    if args.json:
        result = {
            'detected': region is not None,
            'region_id': region,
            'region_info': PAI_REGIONS.get(region) if region else None
        }
        print(f"\n{json.dumps(result, indent=2, ensure_ascii=False)}")
    
    return 0


def cmd_list_regions(args):
    """列出所有可用区域"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}查询可用区域{Colors.RESET}\n")
    
    creds = get_credentials()
    
    if args.check:
        print("正在测试各区域连接性...\n")
    
    regions = list_available_regions(creds, check_connectivity=args.check)
    
    print(format_region_table(regions, args.format))
    
    return 0


def cmd_list_all(args):
    """跨区域列出所有实例"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}跨区域查询实例{Colors.RESET}\n")
    
    creds = get_credentials()
    workspace_id = args.workspace or get_workspace_id() if args.workspace != 'all' else None
    
    # 确定要查询的区域
    if args.regions:
        regions = [r.strip() for r in args.regions.split(',')]
        # 验证区域
        invalid = [r for r in regions if r not in PAI_REGIONS]
        if invalid:
            print(f"{Colors.RED}✗ 无效的区域: {', '.join(invalid)}{Colors.RESET}")
            return 1
    else:
        regions = None  # 查询所有区域
    
    print(f"查询区域: {', '.join(regions) if regions else '所有区域'}")
    if workspace_id:
        print(f"工作空间: {workspace_id}")
    print()
    
    instances_by_region = query_all_regions(workspace_id, creds, regions)
    
    if args.stats:
        stats = get_region_statistics(instances_by_region)
        print(format_statistics(stats, args.format))
    else:
        print(format_cross_region_instances(instances_by_region, args.format))
    
    return 0


def cmd_compare_regions(args):
    """比较区域性能"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}区域性能比较{Colors.RESET}\n")
    
    creds = get_credentials()
    
    # 确定要比较的区域
    if args.regions:
        regions = [r.strip() for r in args.regions.split(',')]
        invalid = [r for r in regions if r not in PAI_REGIONS]
        if invalid:
            print(f"{Colors.RED}✗ 无效的区域: {', '.join(invalid)}{Colors.RESET}")
            return 1
    else:
        # 默认比较主要区域
        regions = ['cn-hangzhou', 'cn-shanghai', 'cn-beijing', 'cn-shenzhen']
    
    print(f"比较区域: {', '.join(regions)}\n")
    
    results = []
    for region_id in regions:
        print(f"测试 {region_id}...", end=' ', flush=True)
        result = test_region_connectivity(region_id, creds)
        results.append(result)
        
        if result['status'] == 'available':
            print(f"{Colors.GREEN}✓ {result['latency_ms']}ms{Colors.RESET}")
        else:
            print(f"{Colors.RED}✗ {result['error'][:50]}{Colors.RESET}")
    
    # 排序并显示结果
    print(f"\n{Colors.BOLD}性能排名:{Colors.RESET}\n")
    
    available = [r for r in results if r['status'] == 'available']
    unavailable = [r for r in results if r['status'] != 'available']
    
    available.sort(key=lambda x: x['latency_ms'])
    
    for i, r in enumerate(available, 1):
        region_name = r['region_name']
        latency = r['latency_ms']
        
        medal = '🥇' if i == 1 else ('🥈' if i == 2 else ('🥉' if i == 3 else '  '))
        print(f"{medal} {r['region_id']:<20} {region_name:<20} {latency:>8.2f}ms")
    
    if unavailable:
        print(f"\n{Colors.YELLOW}不可用区域:{Colors.RESET}")
        for r in unavailable:
            print(f"  {r['region_id']}: {r['error'][:50] if r.get('error') else '未知错误'}")
    
    if args.json:
        print(f"\n{json.dumps(results, indent=2, ensure_ascii=False)}")
    
    return 0


def cmd_search_all(args):
    """跨区域搜索实例"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}跨区域搜索: {args.query}{Colors.RESET}\n")
    
    creds = get_credentials()
    workspace_id = args.workspace or get_workspace_id() if args.workspace != 'all' else None
    
    instances_by_region = query_all_regions(workspace_id, creds)
    
    results = []
    query_lower = args.query.lower()
    
    for region_id, instances in instances_by_region.items():
        if isinstance(instances, dict) and 'error' in instances:
            continue
        
        for inst in instances:
            name = inst.get('InstanceName', '').lower()
            inst_id = inst.get('InstanceId', '').lower()
            
            if query_lower in name or query_lower in inst_id:
                results.append(inst)
    
    if not results:
        print(f"{Colors.YELLOW}未找到匹配 '{args.query}' 的实例{Colors.RESET}")
        return 0
    
    print(f"找到 {len(results)} 个匹配的实例:\n")
    
    for inst in results:
        region_id = inst.get('RegionId', 'N/A')
        region_name = inst.get('RegionName', region_id)
        inst_id = inst.get('InstanceId', 'N/A')
        name = inst.get('InstanceName', 'N/A')
        status = inst.get('Status', 'Unknown')
        
        if status.lower() == 'running':
            status_str = colorize(status, Colors.GREEN)
        else:
            status_str = colorize(status, Colors.RED if status.lower() == 'stopped' else Colors.YELLOW)
        
        print(f"  {Colors.BOLD}{inst_id}{Colors.RESET}")
        print(f"    名称: {name}")
        print(f"    区域: {region_name} ({region_id})")
        print(f"    状态: {status_str}")
        print()
    
    return 0


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description='PAI-DSW 多区域管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 检测当前区域
  multi_region.py detect
  
  # 列出所有区域
  multi_region.py list-regions
  
  # 列出所有区域（含连接测试）
  multi_region.py list-regions --check
  
  # 跨区域列出所有实例
  multi_region.py list-all
  
  # 跨区域列出所有实例（含统计）
  multi_region.py list-all --stats
  
  # 指定区域查询
  multi_region.py list-all --regions cn-hangzhou,cn-shanghai
  
  # 比较区域性能
  multi_region.py compare
  
  # 比较指定区域性能
  multi_region.py compare --regions cn-hangzhou,cn-shanghai,cn-beijing
  
  # 跨区域搜索实例
  multi_region.py search gpu-training
"""
    )
    
    parser.add_argument('--no-color', action='store_true', help='禁用彩色输出')
    parser.add_argument('--format', '-f', choices=['table', 'json'], default='table', help='输出格式')
    parser.add_argument('--workspace', '-w', help='工作空间 ID (使用 "all" 查询所有工作空间)')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # detect 命令
    detect_parser = subparsers.add_parser('detect', help='自动检测当前区域')
    detect_parser.add_argument('--json', action='store_true', help='JSON 格式输出')
    
    # list-regions 命令
    list_regions_parser = subparsers.add_parser('list-regions', help='列出所有可用区域')
    list_regions_parser.add_argument('--check', action='store_true', help='测试区域连接性')
    
    # list-all 命令
    list_all_parser = subparsers.add_parser('list-all', help='跨区域列出所有实例')
    list_all_parser.add_argument('--regions', '-r', help='指定区域（逗号分隔）')
    list_all_parser.add_argument('--stats', action='store_true', help='显示统计信息')
    
    # compare 命令
    compare_parser = subparsers.add_parser('compare', help='比较区域性能')
    compare_parser.add_argument('--regions', '-r', help='指定区域（逗号分隔）')
    compare_parser.add_argument('--json', action='store_true', help='JSON 格式输出')
    
    # search 命令
    search_parser = subparsers.add_parser('search', help='跨区域搜索实例')
    search_parser.add_argument('query', help='搜索关键词')
    
    args = parser.parse_args()
    
    # 禁用颜色
    if args.no_color or not sys.stdout.isatty():
        Colors.disable()
    
    # 调度命令
    commands = {
        'detect': cmd_detect,
        'list-regions': cmd_list_regions,
        'list-all': cmd_list_all,
        'compare': cmd_compare_regions,
        'search': cmd_search_all,
    }
    
    if not args.command:
        parser.print_help()
        return 0
    
    cmd_func = commands.get(args.command)
    if cmd_func:
        try:
            return cmd_func(args)
        except Exception as e:
            print(f"{Colors.RED}✗ 错误: {e}{Colors.RESET}", file=sys.stderr)
            return 1
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())