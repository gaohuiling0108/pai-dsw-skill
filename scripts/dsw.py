#!/usr/bin/env python3
"""
PAI-DSW Unified CLI Tool
统一命令行入口，支持实例名称模糊搜索和彩色输出
"""

import argparse
import json
import sys
import os
import subprocess
from typing import Optional, List

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
    
    # 背景色
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    
    @classmethod
    def disable(cls):
        """禁用颜色（用于非终端输出）"""
        cls.RESET = ''
        cls.BOLD = ''
        cls.RED = ''
        cls.GREEN = ''
        cls.YELLOW = ''
        cls.BLUE = ''
        cls.MAGENTA = ''
        cls.CYAN = ''
        cls.WHITE = ''
        cls.BG_RED = ''
        cls.BG_GREEN = ''
        cls.BG_YELLOW = ''


def colorize(text: str, color: str) -> str:
    """添加颜色"""
    return f"{color}{text}{Colors.RESET}"


def print_header(title: str):
    """打印标题头"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*50}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.WHITE}  {title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*50}{Colors.RESET}\n")


def print_success(text: str):
    """打印成功消息"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text: str):
    """打印错误消息"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}", file=sys.stderr)


def print_warning(text: str):
    """打印警告消息"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def print_info(text: str):
    """打印信息"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")


def status_badge(status: str) -> str:
    """状态徽章"""
    status_colors = {
        'Running': Colors.GREEN,
        'Pending': Colors.YELLOW,
        'Starting': Colors.YELLOW,
        'Stopping': Colors.YELLOW,
        'Stopped': Colors.RED,
        'Failed': Colors.BG_RED,
        'Deleted': Colors.MAGENTA,
    }
    color = status_colors.get(status, Colors.WHITE)
    return f"{color}{status}{Colors.RESET}"


# 脚本目录（解析符号链接）
SCRIPT_PATH = os.path.abspath(__file__)
if os.path.islink(SCRIPT_PATH):
    SCRIPT_PATH = os.path.realpath(SCRIPT_PATH)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)


def run_script(script_name: str, args: list, capture_output: bool = False) -> int:
    """
    运行指定的脚本
    
    Args:
        script_name: 脚本名称（不含 .py）
        args: 传递给脚本的参数列表
        capture_output: 是否捕获输出
    
    Returns:
        退出码
    """
    script_path = os.path.join(SCRIPT_DIR, f"{script_name}.py")
    cmd = ['python3', script_path] + args
    
    if capture_output:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    else:
        return subprocess.run(cmd).returncode


def get_instances_json() -> List[dict]:
    """获取实例列表（JSON 格式）"""
    script_path = os.path.join(SCRIPT_DIR, "list_instances.py")
    result = subprocess.run(
        ['python3', script_path, '--format', 'json'],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return []
    return []


def resolve_instance(identifier: str) -> Optional[str]:
    """
    解析实例标识符（支持 ID 或名称模糊匹配）
    返回实例 ID
    """
    # 如果看起来像 ID（以 dsw- 开头或包含多个连字符）
    if identifier.startswith('dsw-') or identifier.count('-') >= 2:
        return identifier
    
    # 否则按名称模糊搜索
    instances = get_instances_json()
    matches = []
    
    for inst in instances:
        name = inst.get('InstanceName', '')
        instance_id = inst.get('InstanceId', '')
        
        # 完全匹配
        if name == identifier:
            return instance_id
        
        # 模糊匹配（名称包含标识符）
        if identifier.lower() in name.lower():
            matches.append((instance_id, name))
    
    if len(matches) == 0:
        print_error(f"未找到名称包含 '{identifier}' 的实例")
        return None
    elif len(matches) == 1:
        instance_id, name = matches[0]
        print_info(f"匹配到实例: {name} ({instance_id})")
        return instance_id
    else:
        print_error(f"找到多个匹配的实例:")
        for instance_id, name in matches:
            print(f"  - {name} ({instance_id})")
        print_info("请使用更精确的名称或直接使用实例 ID")
        return None


def cmd_list(args):
    """列出实例"""
    print_header("PAI-DSW 实例列表")
    
    script_args = ['--format', args.format]
    if args.region:
        script_args.extend(['--region', args.region])
    if args.workspace:
        script_args.extend(['--workspace', args.workspace])
    
    return run_script('list_instances', script_args)


def cmd_get(args):
    """查询实例详情"""
    instance_id = resolve_instance(args.instance)
    if not instance_id:
        return 1
    
    print_header(f"实例详情: {instance_id}")
    return run_script('get_instance', [instance_id, '--format', args.format])


def cmd_start(args):
    """启动实例"""
    instance_id = resolve_instance(args.instance)
    if not instance_id:
        return 1
    
    print_header(f"启动实例: {instance_id}")
    print_info("正在启动...")
    
    return run_script('start_instance', [instance_id])


def cmd_stop(args):
    """停止实例"""
    instance_id = resolve_instance(args.instance)
    if not instance_id:
        return 1
    
    print_header(f"停止实例: {instance_id}")
    
    # 确认
    if not args.force:
        confirm = input(f"{Colors.YELLOW}确认要停止实例 {instance_id} 吗？(yes/no): {Colors.RESET}")
        if confirm.lower() not in ['yes', 'y']:
            print_info("已取消")
            return 0
    
    print_info("正在停止...")
    return run_script('stop_instance', [instance_id, '--force'])


def cmd_delete(args):
    """删除实例"""
    instance_id = resolve_instance(args.instance)
    if not instance_id:
        return 1
    
    print_header(f"删除实例: {instance_id}")
    print_warning("⚠️ 删除操作不可恢复！")
    
    # 确认
    if not args.force:
        confirm = input(f"{Colors.BG_RED}请输入 'delete' 确认删除: {Colors.RESET}")
        if confirm != 'delete':
            print_info("已取消")
            return 0
    
    print_info("正在删除...")
    return run_script('delete_instance', [instance_id, '--force'])


def cmd_create(args):
    """创建实例"""
    print_header(f"创建实例: {args.name}")
    
    script_args = ['--name', args.name, '--image', args.image, '--type', args.type]
    if args.labels:
        script_args.extend(['--labels', args.labels])
    
    return run_script('create_instance', script_args)


def cmd_snapshot(args):
    """创建快照"""
    instance_id = resolve_instance(args.instance)
    if not instance_id:
        return 1
    
    print_header(f"创建快照: {args.name}")
    
    script_args = [instance_id, args.name]
    if args.description:
        script_args.extend(['--description', args.description])
    
    return run_script('create_snapshot', script_args)


def cmd_snapshots(args):
    """列出快照"""
    instance_id = resolve_instance(args.instance)
    if not instance_id:
        return 1
    
    print_header(f"实例快照: {instance_id}")
    return run_script('list_snapshots', [instance_id, '--format', args.format])


def cmd_specs(args):
    """列出可用规格"""
    print_header("可用 ECS 规格")
    
    script_args = ['--format', args.format]
    if args.gpu:
        script_args.append('--gpu')
    if args.cpu:
        script_args.append('--cpu')
    
    return run_script('list_ecs_specs', script_args)


def cmd_update(args):
    """更新实例规格"""
    instance_id = resolve_instance(args.instance)
    if not instance_id:
        return 1
    
    print_header(f"更新实例: {instance_id}")
    
    # 确认
    if not args.force:
        print_warning("更新实例规格可能需要重启实例")
        confirm = input(f"{Colors.YELLOW}确认要更新吗？(yes/no): {Colors.RESET}")
        if confirm.lower() not in ['yes', 'y']:
            print_info("已取消")
            return 0
    
    script_args = [instance_id]
    if args.spec:
        script_args.extend(['--spec', args.spec])
    if args.cpu:
        script_args.extend(['--cpu', str(args.cpu)])
    if args.memory:
        script_args.extend(['--memory', str(args.memory)])
    if args.gpu is not None:
        script_args.extend(['--gpu', str(args.gpu)])
    if args.labels:
        script_args.extend(['--labels', args.labels])
    
    script_args.append('--force')
    
    return run_script('update_instance', script_args)


def cmd_metrics(args):
    """实例资源监控"""
    instance_id = resolve_instance(args.instance)
    if not instance_id:
        return 1
    
    print_header(f"资源监控: {instance_id}")
    
    script_args = [instance_id]
    if args.type != 'all':
        script_args.extend(['--type', args.type])
    if args.start:
        script_args.extend(['--start', args.start])
    if args.end:
        script_args.extend(['--end', args.end])
    if args.summary:
        script_args.append('--summary')
    # get_instance_metrics.py 不支持 --format 参数，移除
    
    return run_script('get_instance_metrics', script_args)


def cmd_search(args):
    """搜索实例（按名称/标签）"""
    print_header(f"搜索实例: {args.query}")
    
    instances = get_instances_json()
    
    results = []
    query_lower = args.query.lower()
    
    for inst in instances:
        name = inst.get('InstanceName', '').lower()
        instance_id = inst.get('InstanceId', '').lower()
        labels = inst.get('Labels', {}) or {}
        label_str = ' '.join([f"{k}:{v}" for k, v in labels.items()]).lower()
        
        if (query_lower in name or 
            query_lower in instance_id or 
            query_lower in label_str):
            results.append(inst)
    
    if not results:
        print_warning(f"未找到匹配 '{args.query}' 的实例")
        return 0
    
    print(f"\n找到 {len(results)} 个匹配的实例:\n")
    
    # 表格输出
    print(f"{'实例ID':<40} {'名称':<30} {'状态':<12} {'规格':<20}")
    print("-" * 102)
    
    for inst in results:
        instance_id = inst.get('InstanceId', 'N/A')
        name = inst.get('InstanceName', 'N/A')
        status = inst.get('Status', 'Unknown')
        spec = inst.get('InstanceType', 'N/A') or 'N/A'
        
        print(f"{instance_id:<40} {name:<30} {status_badge(status):<20} {spec:<20}")
    
    return 0


def cmd_status(args):
    """显示当前实例状态（如果在 DSW 实例中运行）"""
    print_header("当前实例状态")
    
    # 获取当前实例 ID
    hostname = os.getenv('HOSTNAME', '')
    if hostname.startswith('dsw-'):
        print_info(f"当前实例 ID: {hostname}")
        return run_script('get_instance', [hostname])
    else:
        print_warning("不在 DSW 实例环境中运行")
        print_info("如需查询特定实例，请使用: dsw get <instance>")
        return 0


def cmd_workspaces(args):
    """列出工作空间"""
    print_header("PAI 工作空间列表")
    
    script_args = ['--format', args.format]
    if args.region:
        script_args.extend(['--region', args.region])
    
    return run_script('list_workspaces', script_args)


def cmd_images(args):
    """列出可用镜像"""
    print_header("可用镜像列表")
    
    script_args = ['--format', args.format]
    if args.type != 'all':
        script_args.extend(['--type', args.type])
    if args.search:
        script_args.extend(['--search', args.search])
    if args.region:
        script_args.extend(['--region', args.region])
    
    return run_script('list_images', script_args)


def cmd_cost(args):
    """成本估算"""
    print_header("实例成本估算")
    
    script_args = ['--format', args.format]
    if args.instance:
        script_args.extend(['--instance', args.instance])
    if args.region:
        script_args.extend(['--region', args.region])
    
    return run_script('estimate_cost', script_args)


def cmd_env(args):
    """环境检测"""
    print_header("实例环境检测")
    
    script_args = []
    if args.json:
        script_args.append('--json')
    
    return run_script('check_environment', script_args)


def cmd_diagnose(args):
    """实例诊断"""
    print_header("实例诊断")
    
    script_args = []
    if args.json:
        script_args.append('--json')
    
    return run_script('diagnose', script_args)


def cmd_datasets(args):
    """数据集挂载信息"""
    print_header("数据集挂载信息")
    
    script_args = ['--format', args.format]
    if args.instance:
        script_args.insert(0, args.instance)
    
    return run_script('list_datasets', script_args)


def cmd_trends(args):
    """资源趋势分析"""
    print_header("资源趋势分析")
    
    script_args = []
    if args.instance:
        script_args.extend(['--instance', args.instance])
    if args.days:
        script_args.extend(['--days', str(args.days)])
    if args.start:
        script_args.extend(['--start', args.start])
    if args.end:
        script_args.extend(['--end', args.end])
    if args.interval:
        script_args.extend(['--interval', str(args.interval)])
    if args.save:
        script_args.append('--save')
    if args.compare:
        script_args.append('--compare')
    if args.format != 'text':
        script_args.extend(['--format', args.format])
    
    return run_script('analyze_trends', script_args)


def cmd_regions(args):
    """列出所有可用区域"""
    print_header("PAI-DSW 可用区域")
    
    script_args = ['--format', args.format]
    if args.check:
        script_args.append('--check')
    
    return run_script('multi_region', ['list-regions'] + script_args)


def cmd_detect_region(args):
    """检测当前区域"""
    print_header("区域自动检测")
    
    script_args = []
    if args.json:
        script_args.append('--json')
    
    return run_script('multi_region', ['detect'] + script_args)


def cmd_cross_region(args):
    """跨区域实例管理"""
    print_header("跨区域实例管理")
    
    script_args = ['list-all', '--format', args.format]
    if args.regions:
        script_args.extend(['--regions', args.regions])
    if args.workspace:
        script_args.extend(['--workspace', args.workspace])
    if args.stats:
        script_args.append('--stats')
    
    return run_script('multi_region', script_args)


def cmd_compare_regions(args):
    """比较区域性能"""
    print_header("区域性能比较")
    
    script_args = ['compare']
    if args.regions:
        script_args.extend(['--regions', args.regions])
    if args.json:
        script_args.append('--json')
    
    return run_script('multi_region', script_args)


def cmd_search_all(args):
    """跨区域搜索实例"""
    print_header(f"跨区域搜索: {args.query}")
    
    script_args = ['search', args.query]
    if args.workspace:
        script_args.extend(['--workspace', args.workspace])
    
    return run_script('multi_region', script_args)


def cmd_gpu_usage(args):
    """检查所有 GPU 实例的使用率"""
    print_header("GPU 实例使用率检查")
    
    from dsw_utils import create_client, get_workspace_id
    from alibabacloud_pai_dsw20220101 import models as dsw_models
    import subprocess
    
    client = create_client(args.region)
    
    try:
        workspace_id = get_workspace_id(allow_interactive=False)
    except:
        workspace_id = None
    
    if not workspace_id:
        print_error("需要设置工作空间 ID")
        return 1
    
    # 获取所有实例
    request = dsw_models.ListInstancesRequest()
    request.workspace_id = workspace_id
    response = client.list_instances(request)
    
    # GPU 规格关键词
    gpu_specs = ['gn', 'gn6', 'gn7', 'gn8', 'gn6i', 'gn7i', 'gn8i', 'p3', 'p4']
    
    high_usage = []
    gpu_instances = []
    
    for inst in response.body.instances:
        ecs_spec = inst.ecs_spec or ''
        is_gpu = any(spec in ecs_spec.lower() for spec in gpu_specs)
        
        if is_gpu and inst.status == 'Running':
            gpu_instances.append((inst.instance_id, inst.instance_name))
    
    if not gpu_instances:
        print_info("没有运行中的 GPU 实例")
        return 0
    
    print(f"检查 {len(gpu_instances)} 个 GPU 实例...\n")
    
    for instance_id, name in gpu_instances:
        # 获取 GPU 使用率
        try:
            result = subprocess.run(
                ['python3', 'get_instance_metrics.py', instance_id, '--region', args.region or '', '--summary'],
                capture_output=True, text=True, cwd=SCRIPT_DIR
            )
            
            # 解析 GPU 使用率
            import re
            gpu_usage = None
            for line in result.stdout.split('\n'):
                if 'gpu' in line.lower() and '%' in line and 'gpu-memory' not in line.lower():
                    match = re.search(r':\s*(\d+\.?\d*)%', line)
                    if match:
                        gpu_usage = float(match.group(1))
                        break
            
            if gpu_usage is not None:
                if gpu_usage >= 80:
                    print(f"  {colorize(name, Colors.YELLOW)} ({instance_id[:20]}...): GPU {colorize(f'{gpu_usage:.2f}%', Colors.RED)} ⚠️")
                    high_usage.append({'name': name, 'id': instance_id, 'usage': gpu_usage})
                else:
                    print(f"  {name} ({instance_id[:20]}...): GPU {gpu_usage:.2f}% ✅")
            else:
                print(f"  {name}: 无法获取 GPU 数据")
                
        except Exception as e:
            print(f"  {name}: 检查失败")
    
    print()
    
    if high_usage:
        print_warning(f"GPU 使用率超过 80% 的实例 ({len(high_usage)} 个):")
        for item in high_usage:
            print(f"  - {item['name']}: {item['usage']:.2f}%")
    else:
        print_success("没有 GPU 使用率超过 80% 的实例")
    
    return 0


def cmd_info(args):
    """显示完整实例信息（详情 + 资源 + 快照）"""
    instance_id = resolve_instance(args.instance)
    if not instance_id:
        return 1
    
    print_header(f"实例完整信息: {instance_id}")
    
    # 详情
    print(f"\n📋 基本信息")
    ret = run_script('get_instance', [instance_id])
    
    # 资源监控
    print(f"\n📊 资源使用")
    ret2 = run_script('get_instance_metrics', [instance_id, '--summary'])
    
    # 快照
    print(f"\n📸 快照列表")
    ret3 = run_script('list_snapshots', [instance_id])
    
    return max(ret, ret2, ret3)


def cmd_config(args):
    """配置命令"""
    import importlib
    env_detector = importlib.import_module('env_detector')
    
    if args.config_command == 'init':
        # 交互式配置
        config = env_detector.setup_interactive()
        if config:
            print_success("配置完成！")
            return 0
        return 1
    
    elif args.config_command == 'show':
        # 显示当前配置
        env_detector.print_environment_info()
        return 0
    
    elif args.config_command == 'set':
        # 设置配置项
        config = env_detector.load_config()
        config[args.key] = args.value
        if env_detector.save_config(config):
            print_success(f"已设置 {args.key} = {args.value}")
            return 0
        return 1
    
    elif args.config_command == 'workspace':
        # 设置默认工作空间
        if args.workspace_id:
            config = env_detector.load_config()
            config['workspace_id'] = args.workspace_id
            if env_detector.save_config(config):
                print_success(f"已设置默认工作空间: {args.workspace_id}")
                return 0
            return 1
        else:
            # 列出工作空间供选择
            print_info("获取工作空间列表...")
            try:
                from dsw_utils import create_client
                from alibabacloud_pai_dsw20220101 import models as dsw_models
                
                client = create_client()
                request = dsw_models.ListWorkspacesRequest()
                response = client.list_workspaces(request)
                
                if response.body and response.body.workspaces:
                    config = env_detector.load_config()
                    current_ws = config.get('workspace_id', '')
                    
                    print("\n可用工作空间：")
                    for i, ws in enumerate(response.body.workspaces, 1):
                        current = " (当前)" if current_ws == ws.workspace_id else ""
                        print(f"  {i}. {ws.workspace_name} ({ws.workspace_id}){current}")
                    
                    choice = input("\n请选择工作空间编号: ").strip()
                    if choice.isdigit():
                        idx = int(choice) - 1
                        if 0 <= idx < len(response.body.workspaces):
                            selected = response.body.workspaces[idx]
                            config['workspace_id'] = selected.workspace_id
                            env_detector.save_config(config)
                            print_success(f"已设置默认工作空间: {selected.workspace_name}")
                            return 0
            except Exception as e:
                print_error(f"获取工作空间失败: {e}")
                return 1
    
    else:
        # 默认显示配置
        env_detector.print_environment_info()
        return 0


def cmd_tags(args):
    """列出实例标签"""
    instance_id = resolve_instance(args.instance)
    if not instance_id:
        return 1
    
    print_header(f"实例标签: {instance_id}")
    
    script_args = [instance_id]
    if args.format:
        script_args.extend(['--format', args.format])
    
    return run_script('manage_tags', ['list'] + script_args)


def cmd_tag_add(args):
    """添加标签到实例"""
    instance_id = resolve_instance(args.instance)
    if not instance_id:
        return 1
    
    print_header(f"添加标签: {instance_id}")
    
    script_args = ['add', instance_id, args.tags]
    if args.force:
        script_args.append('--force')
    
    return run_script('manage_tags', script_args)


def cmd_tag_remove(args):
    """从实例删除标签"""
    instance_id = resolve_instance(args.instance)
    if not instance_id:
        return 1
    
    print_header(f"删除标签: {instance_id}")
    
    script_args = ['remove', instance_id, args.keys]
    if args.force:
        script_args.append('--force')
    
    return run_script('manage_tags', script_args)


def cmd_tag_set(args):
    """设置实例标签（替换所有）"""
    instance_id = resolve_instance(args.instance)
    if not instance_id:
        return 1
    
    print_header(f"设置标签: {instance_id}")
    
    script_args = ['set', instance_id, args.tags]
    if args.force:
        script_args.append('--force')
    
    return run_script('manage_tags', script_args)


def cmd_tag_batch_add(args):
    """批量添加标签"""
    print_header("批量添加标签")
    
    script_args = ['batch-add', args.tags]
    if args.instances:
        script_args.extend(['--instances', args.instances])
    if args.query:
        script_args.extend(['--query', args.query])
    if args.force:
        script_args.append('--force')
    
    return run_script('manage_tags', script_args)


def cmd_tag_batch_remove(args):
    """批量删除标签"""
    print_header("批量删除标签")
    
    script_args = ['batch-remove', args.keys]
    if args.instances:
        script_args.extend(['--instances', args.instances])
    if args.query:
        script_args.extend(['--query', args.query])
    if args.force:
        script_args.append('--force')
    
    return run_script('manage_tags', script_args)


def cmd_tag_filter(args):
    """按标签筛选实例"""
    print_header(f"标签筛选: {args.filter}")
    
    script_args = ['filter', args.filter]
    if args.has_key:
        script_args.extend(['--has-key', args.has_key])
    if args.format:
        script_args.extend(['--format', args.format])
    
    return run_script('manage_tags', script_args)


def cmd_tag_export(args):
    """导出所有实例标签"""
    print_header("导出实例标签")
    
    script_args = ['export']
    if args.format:
        script_args.extend(['--format', args.format])
    
    return run_script('manage_tags', script_args)


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description='PAI-DSW 统一命令行工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw list                        # 列出所有实例
  dsw get my-instance             # 查询实例详情（支持名称模糊匹配）
  dsw start my-inst               # 启动实例
  dsw stop dsw-12345              # 停止实例
  dsw search gpu                  # 搜索名称包含 "gpu" 的实例
  dsw create --name test --image modelscope:1.34.0 --type ecs.g6.large
  dsw workspaces                  # 列出工作空间
  dsw images --search pytorch     # 搜索 PyTorch 镜像
  dsw cost                        # 成本估算
  dsw env                         # 环境检测
  dsw diagnose                    # 实例诊断
  dsw info my-instance            # 完整实例信息

多区域操作:
  dsw regions                     # 列出所有可用区域
  dsw regions --check             # 测试区域连接性
  dsw detect-region               # 检测当前区域
  dsw cross-region                # 跨区域列出所有实例
  dsw cross-region --stats        # 跨区域实例统计
  dsw compare-regions             # 比较区域性能
  dsw search-all gpu-training     # 跨区域搜索实例

标签管理:
  dsw tags dsw-123456             # 查看实例标签
  dsw tag-add my-inst env=prod    # 添加标签
  dsw tag-remove my-inst env      # 删除标签
  dsw tag-set my-inst env=dev     # 设置标签（替换所有）
  dsw tag-batch-add team=ml --query gpu  # 批量添加标签
  dsw tag-filter env=prod         # 按标签筛选实例
  dsw tag-export --format json    # 导出所有标签

实例标识符支持:
  - 完整实例 ID (如: dsw-123456-abcde)
  - 实例名称模糊匹配 (如: my-instance 或 my)
"""
    )
    
    parser.add_argument('--no-color', action='store_true', help='禁用彩色输出')
    parser.add_argument('--format', choices=['table', 'json'], default='table', help='输出格式')
    parser.add_argument('--region', help='区域 ID')
    parser.add_argument('--workspace', help='工作空间 ID')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # config 命令
    config_parser = subparsers.add_parser(
        'config',
        help='配置管理',
        description='管理 PAI-DSW Skill 的配置，支持交互式配置、显示配置、设置配置项等。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
子命令:
  dsw config init              # 交互式初始化配置（推荐新用户使用）
  dsw config show              # 显示当前配置和环境信息
  dsw config set <key> <value> # 设置配置项
  dsw config workspace         # 选择/设置默认工作空间

配置项:
  access_key_id     - 阿里云 AccessKey ID
  access_key_secret - 阿里云 AccessKey Secret
  region            - 默认区域
  workspace_id      - 默认工作空间 ID

配置文件位置:
  ~/.dsw/config.json

示例:
  # 首次使用，交互式配置
  dsw config init
  
  # 查看当前配置
  dsw config show
  
  # 设置默认区域
  dsw config set region ap-southeast-1
  
  # 设置默认工作空间
  dsw config workspace
"""
    )
    config_subparsers = config_parser.add_subparsers(dest='config_command', help='配置子命令')
    
    # config init
    config_init_parser = config_subparsers.add_parser('init', help='交互式初始化配置')
    
    # config show
    config_show_parser = config_subparsers.add_parser('show', help='显示当前配置')
    
    # config set
    config_set_parser = config_subparsers.add_parser('set', help='设置配置项')
    config_set_parser.add_argument('key', help='配置项名称')
    config_set_parser.add_argument('value', help='配置项值')
    
    # config workspace
    config_workspace_parser = config_subparsers.add_parser('workspace', help='设置默认工作空间')
    config_workspace_parser.add_argument('workspace_id', nargs='?', help='工作空间 ID（不指定则交互选择）')
    
    # list 命令
    list_parser = subparsers.add_parser(
        'list', 
        help='列出所有实例',
        description='列出当前区域下的所有 DSW 实例，显示实例 ID、名称、状态和规格信息。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw list                      # 以表格形式列出所有实例
  dsw list --format json        # 以 JSON 格式输出
  dsw list --region cn-shanghai # 指定区域
  dsw list --workspace ws-xxx   # 指定工作空间

输出字段:
  InstanceId     - 实例唯一标识符
  InstanceName   - 实例名称
  Status         - 实例状态 (Running/Stopped/Pending 等)
  InstanceType   - ECS 规格类型
  GpuCount       - GPU 数量
  CreateTime     - 创建时间
"""
    )
    list_parser.add_argument('--format', dest='format_override', choices=['table', 'json'], help='输出格式 (table/json)')
    
    # get 命令
    get_parser = subparsers.add_parser(
        'get', 
        help='查询实例详情',
        description='查询指定实例的详细信息，包括配置、状态、网络等。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw get dsw-123456-abcde     # 使用实例 ID 查询
  dsw get my-instance           # 使用实例名称查询
  dsw get my-inst --format json # JSON 格式输出

参数:
  instance - 实例 ID 或名称（支持模糊匹配）

输出信息:
  实例 ID、名称、状态、规格、镜像、GPU 配置
  创建时间、过期时间、工作空间
  网络配置（VPC、安全组）
  存储配置（系统盘、数据盘）
"""
    )
    get_parser.add_argument('instance', help='实例 ID 或名称（支持模糊匹配）')
    
    # start 命令
    start_parser = subparsers.add_parser(
        'start', 
        help='启动实例',
        description='启动一个已停止的 DSW 实例。实例必须处于 Stopped 状态才能启动。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw start dsw-123456-abcde   # 使用实例 ID 启动
  dsw start my-instance        # 使用实例名称启动
  dsw start gpu                # 模糊匹配名称包含 "gpu" 的实例

注意事项:
  - 仅 Stopped 状态的实例可以启动
  - 启动过程通常需要 1-3 分钟
  - 启动后会自动分配新的网络资源

相关命令:
  dsw stop <instance>   # 停止实例
  dsw get <instance>    # 查询实例状态
"""
    )
    start_parser.add_argument('instance', help='实例 ID 或名称（支持模糊匹配）')
    
    # stop 命令
    stop_parser = subparsers.add_parser(
        'stop', 
        help='停止实例',
        description='停止一个正在运行的 DSW 实例。停止后实例数据保留，但会释放计算资源。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw stop dsw-123456-abcde    # 交互式确认后停止
  dsw stop my-instance -f      # 跳过确认直接停止
  dsw stop training --force    # 强制停止（无需确认）

注意事项:
  - 停止前请确保重要数据已保存
  - 停止后仍会产生存储费用
  - 实例必须处于 Running 状态
  - 停止过程通常需要 1-2 分钟

相关命令:
  dsw start <instance>   # 启动实例
  dsw delete <instance>  # 删除实例（不可恢复）
"""
    )
    stop_parser.add_argument('instance', help='实例 ID 或名称（支持模糊匹配）')
    stop_parser.add_argument('--force', '-f', action='store_true', help='跳过确认直接执行')
    
    # delete 命令
    delete_parser = subparsers.add_parser(
        'delete', 
        help='删除实例',
        description='永久删除一个 DSW 实例。此操作不可恢复，请谨慎操作！',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw delete dsw-123456-abcde   # 交互式确认后删除
  dsw delete my-instance -f     # 跳过确认直接删除（危险！）

⚠️ 警告:
  - 删除操作不可恢复！
  - 所有数据将永久丢失
  - 建议删除前创建快照备份

删除前建议:
  1. 备份重要数据到 OSS
  2. 创建快照: dsw snapshot <instance> <snapshot-name>
  3. 确认实例已停止

相关命令:
  dsw snapshot <instance> <name>  # 创建快照
  dsw stop <instance>             # 停止实例
"""
    )
    delete_parser.add_argument('instance', help='实例 ID 或名称（支持模糊匹配）')
    delete_parser.add_argument('--force', '-f', action='store_true', help='跳过确认直接执行（危险操作）')
    
    # create 命令
    create_parser = subparsers.add_parser(
        'create', 
        help='创建实例',
        description='创建一个新的 DSW 实例。需要指定名称、镜像和规格。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 创建 CPU 实例
  dsw create -n my-notebook -i modelscope:1.34.0 -t ecs.g6.large

  # 创建 GPU 实例
  dsw create -n gpu-training -i pytorch:2.0.0 -t ecs.gn6v-c8g1.16xlarge

  # 带标签的实例
  dsw create -n test -i pytorch:latest -t ecs.g6.large -l '{"env":"dev","team":"ml"}'

参数说明:
  --name, -n     实例名称（必填，建议使用英文和连字符）
  --image, -i    镜像 ID（使用 images 命令查看可用镜像）
  --type, -t     ECS 规格（使用 specs 命令查看可用规格）
  --labels, -l   标签，JSON 格式，用于分类管理

快速查询:
  dsw images              # 查看可用镜像
  dsw specs --gpu         # 查看 GPU 规格
  dsw specs --cpu         # 查看 CPU 规格

相关命令:
  dsw images              # 列出可用镜像
  dsw specs               # 列出可用规格
  dsw workspaces          # 列出工作空间
"""
    )
    create_parser.add_argument('--name', '-n', required=True, help='实例名称（必填，建议英文+连字符）')
    create_parser.add_argument('--image', '-i', required=True, help='镜像 ID（使用 images 命令查看）')
    create_parser.add_argument('--type', '-t', required=True, help='实例规格（使用 specs 命令查看）')
    create_parser.add_argument('--labels', '-l', help='标签，JSON 格式，如: \'{"env":"dev"}\'')
    
    # snapshot 命令
    snapshot_parser = subparsers.add_parser(
        'snapshot', 
        help='创建快照',
        description='为实例创建快照备份。快照可以用于恢复实例状态或创建新实例。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw snapshot dsw-123456-abcde backup-20240107
  dsw snapshot my-instance daily-snap -d "每日备份"
  dsw snapshot gpu-train pre-upgrade --description "升级前备份"

参数说明:
  instance     实例 ID 或名称
  name         快照名称（建议包含日期或用途）
  --description, -d   快照描述信息

注意事项:
  - 快照创建过程中实例可能短暂暂停
  - 快照存储会产生额外费用
  - 建议在重要变更前创建快照

相关命令:
  dsw snapshots <instance>  # 查看实例快照列表
"""
    )
    snapshot_parser.add_argument('instance', help='实例 ID 或名称（支持模糊匹配）')
    snapshot_parser.add_argument('name', help='快照名称（建议包含日期或用途）')
    snapshot_parser.add_argument('--description', '-d', help='快照描述信息')
    
    # snapshots 命令
    snapshots_parser = subparsers.add_parser(
        'snapshots', 
        help='列出实例快照',
        description='列出指定实例的所有快照，包括快照 ID、名称、状态和创建时间。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw snapshots dsw-123456-abcde
  dsw snapshots my-instance --format json

输出字段:
  SnapshotId    - 快照唯一标识符
  SnapshotName  - 快照名称
  Status        - 快照状态 (Available/Creating 等)
  Size          - 快照大小
  CreateTime    - 创建时间

相关命令:
  dsw snapshot <instance> <name>  # 创建快照
"""
    )
    snapshots_parser.add_argument('instance', help='实例 ID 或名称（支持模糊匹配）')
    
    # specs 命令
    specs_parser = subparsers.add_parser(
        'specs', 
        help='列出可用 ECS 规格',
        description='列出当前区域可用的 ECS 实例规格，包括 CPU、GPU、内存等信息。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw specs                  # 列出所有规格
  dsw specs --gpu            # 仅显示 GPU 规格
  dsw specs --cpu            # 仅显示 CPU 规格
  dsw specs --format json    # JSON 格式输出

常见规格类型:
  CPU 实例:
    ecs.g6.large      - 2vCPU, 8GB 内存
    ecs.g6.xlarge     - 4vCPU, 16GB 内存
    ecs.g6.2xlarge    - 8vCPU, 32GB 内存

  GPU 实例:
    ecs.gn6v-c8g1.16xlarge  - V100, 1 GPU
    ecs.gn7-c12g1.24xlarge  - A10, 1 GPU
    ecs.gn6e-c12g1.24xlarge - V100-32G, 1 GPU

相关命令:
  dsw create -t <spec>  # 使用指定规格创建实例
  dsw cost              # 成本估算
"""
    )
    specs_parser.add_argument('--gpu', action='store_true', help='仅显示 GPU 规格')
    specs_parser.add_argument('--cpu', action='store_true', help='仅显示 CPU 规格')
    
    # update 命令
    update_parser = subparsers.add_parser(
        'update', 
        help='更新实例规格',
        description='修改运行中或已停止实例的规格配置，如 CPU、内存、GPU 等。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 更改实例规格
  dsw update dsw-123456-abcde --spec ecs.g6.2xlarge

  # 调整 CPU 和内存
  dsw update my-instance --cpu 8 --memory 32

  # 添加 GPU
  dsw update gpu-test --gpu 2 -f

  # 更新标签
  dsw update my-inst --labels '{"env":"prod"}'

参数说明:
  --spec, -s     完整的 ECS 规格类型
  --cpu          CPU 核数
  --memory       内存大小 (GB)
  --gpu          GPU 数量
  --labels, -l   标签，JSON 格式
  --force, -f    跳过确认直接执行

注意事项:
  - 更新规格可能需要重启实例
  - 某些规格变更不可逆（如降配）
  - GPU 实例更改 GPU 数量需要实例处于停止状态

相关命令:
  dsw specs               # 查看可用规格
  dsw stop <instance>     # 停止实例
  dsw start <instance>    # 启动实例
"""
    )
    update_parser.add_argument('instance', help='实例 ID 或名称（支持模糊匹配）')
    update_parser.add_argument('--spec', '-s', help='新的 ECS 规格类型')
    update_parser.add_argument('--cpu', type=int, help='CPU 核数')
    update_parser.add_argument('--memory', type=int, help='内存大小 (GB)')
    update_parser.add_argument('--gpu', type=int, help='GPU 数量')
    update_parser.add_argument('--labels', '-l', help='标签，JSON 格式')
    update_parser.add_argument('--force', '-f', action='store_true', help='跳过确认直接执行')
    
    # metrics 命令
    metrics_parser = subparsers.add_parser(
        'metrics', 
        help='实例资源监控',
        description='查询实例的资源使用情况，包括 CPU、内存、GPU 利用率等。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 查看所有指标
  dsw metrics dsw-123456-abcde

  # 仅查看 CPU 指标
  dsw metrics my-instance --type cpu

  # 仅查看 GPU 指标
  dsw metrics gpu-train --type gpu

  # 指定时间范围
  dsw metrics my-inst --start 2024-01-01T00:00:00Z --end 2024-01-02T00:00:00Z

  # 仅显示摘要
  dsw metrics my-instance --summary

参数说明:
  --type       指标类型: cpu/memory/gpu/all (默认: all)
  --start      开始时间，ISO 格式 (如: 2024-01-01T00:00:00Z)
  --end        结束时间，ISO 格式
  --summary    仅显示摘要信息，不显示详细数据点

输出指标:
  CPU: cpu_utilization (利用率 %)
  内存: memory_utilization (利用率 %), memory_used (使用量 GB)
  GPU: gpu_utilization (计算利用率 %), gpu_memory_utilization (显存利用率 %)

相关命令:
  dsw get <instance>    # 查看实例详情
  dsw cost              # 成本估算
"""
    )
    metrics_parser.add_argument('instance', help='实例 ID 或名称（支持模糊匹配）')
    metrics_parser.add_argument('--type', choices=['cpu', 'memory', 'gpu', 'all'], default='all', help='指标类型: cpu/memory/gpu/all (默认: all)')
    metrics_parser.add_argument('--start', help='开始时间，ISO 格式 (如: 2024-01-01T00:00:00Z)')
    metrics_parser.add_argument('--end', help='结束时间，ISO 格式')
    metrics_parser.add_argument('--summary', action='store_true', help='仅显示摘要')
    
    # search 命令
    search_parser = subparsers.add_parser(
        'search', 
        help='搜索实例',
        description='按名称、ID 或标签搜索实例，支持模糊匹配。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw search gpu              # 搜索名称包含 "gpu" 的实例
  dsw search training         # 搜索名称包含 "training" 的实例
  dsw search env:prod         # 搜索标签包含 "env:prod" 的实例
  dsw search dsw-12345        # 搜索 ID 包含指定字符的实例

搜索范围:
  - 实例名称 (InstanceName)
  - 实例 ID (InstanceId)
  - 标签 (Labels)

相关命令:
  dsw list     # 列出所有实例
  dsw get      # 查看实例详情
"""
    )
    search_parser.add_argument('query', help='搜索关键词（支持名称/ID/标签模糊匹配）')
    
    # status 命令
    status_parser = subparsers.add_parser(
        'status', 
        help='显示当前实例状态',
        description='显示当前运行的 DSW 实例的状态信息。仅在 DSW 实例内部运行时有效。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw status    # 在 DSW 实例中运行，显示当前实例信息

使用场景:
  - 在 DSW 实例终端中快速查看当前实例状态
  - 脚本中获取当前实例 ID 和配置

输出信息:
  - 当前实例 ID（从环境变量 HOSTNAME 获取）
  - 实例详情（规格、状态、镜像等）

注意:
  此命令仅在 DSW 实例内部运行时有效。
  如需查询其他实例，请使用: dsw get <instance>

相关命令:
  dsw get <instance>   # 查询指定实例详情
  dsw env              # 环境检测
  dsw diagnose         # 实例诊断
"""
    )
    
    # workspaces 命令
    workspaces_parser = subparsers.add_parser(
        'workspaces', 
        help='列出工作空间',
        description='列出当前账号下所有 PAI 工作空间，工作空间用于组织和管理 AI 资源。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw workspaces              # 列出所有工作空间
  dsw workspaces --format json # JSON 格式输出
  dsw workspaces --region cn-shanghai # 指定区域

输出字段:
  WorkspaceId    - 工作空间 ID
  WorkspaceName  - 工作空间名称
  Status         - 状态
 CreateTime      - 创建时间

用途:
  - 创建实例时需要指定工作空间
  - 工作空间用于资源隔离和权限管理

相关命令:
  dsw create --workspace <id>  # 在指定工作空间创建实例
"""
    )
    workspaces_parser.add_argument('--format', dest='format_override', choices=['table', 'json'], help='输出格式 (table/json)')
    
    # images 命令
    images_parser = subparsers.add_parser(
        'images', 
        help='列出可用镜像',
        description='列出可用的 DSW 镜像，包括官方镜像和自定义镜像。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw images                      # 列出所有镜像
  dsw images --type official      # 仅显示官方镜像
  dsw images --type custom        # 仅显示自定义镜像
  dsw images --search pytorch     # 搜索包含 "pytorch" 的镜像
  dsw images --search tensorflow --format json

常见官方镜像:
  modelscope:1.34.0      - ModelScope 最新版
  pytorch:2.0.0          - PyTorch 2.0
  tensorflow:2.12.0      - TensorFlow 2.12
  pyodps:latest          - PyODPS 数据分析

镜像类型:
  official - 阿里云官方维护的镜像
  custom   - 用户自定义镜像

相关命令:
  dsw create -i <image>  # 使用指定镜像创建实例
"""
    )
    images_parser.add_argument('--type', choices=['all', 'official', 'custom'], default='all',
                              help='镜像类型: all(全部)/official(官方)/custom(自定义)')
    images_parser.add_argument('--search', '-s', help='搜索关键词（匹配镜像名称）')
    
    # cost 命令
    cost_parser = subparsers.add_parser(
        'cost', 
        help='成本估算',
        description='估算 DSW 实例的运行成本，包括计算资源和存储费用。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw cost                          # 估算当前实例成本
  dsw cost --instance dsw-123456    # 估算指定实例成本
  dsw cost --format json            # JSON 格式输出

输出信息:
  - 按小时计费价格
  - 按月预估成本
  - 存储费用（系统盘+数据盘）
  - GPU 费用（如有）

计费说明:
  - DSW 实例按实际运行时间计费
  - 停止状态仅收取存储费用
  - GPU 实例费用较高，建议合理使用

节省成本建议:
  - 不使用时及时停止实例
  - 使用自动停止功能
  - 选择合适的规格，避免资源浪费

相关命令:
  dsw stop <instance>   # 停止实例以节省成本
  dsw specs             # 查看规格和价格
"""
    )
    cost_parser.add_argument('--instance', '-i', help='指定实例 ID（不指定则使用当前实例）')
    
    # env 命令
    env_parser = subparsers.add_parser(
        'env', 
        help='环境检测',
        description='检测当前 DSW 实例的环境配置，包括依赖、权限、网络等。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw env           # 检测当前环境（表格输出）
  dsw env --json    # JSON 格式输出（便于脚本解析）

检测项目:
  ✓ Python 版本和环境
  ✓ 已安装的核心包（numpy, torch, tensorflow 等）
  ✓ GPU 可用性和 CUDA 版本
  ✓ 网络连接状态
  ✓ OSS 挂载状态
  ✓ PAI SDK 配置
  ✓ RAM 角色凭证

使用场景:
  - 实例启动后快速检查环境
  - 排查环境配置问题
  - 验证依赖安装情况

相关命令:
  dsw diagnose    # 实例诊断（更详细的诊断）
  dsw status      # 当前实例状态
"""
    )
    env_parser.add_argument('--json', action='store_true', help='JSON 格式输出')
    
    # diagnose 命令
    diag_parser = subparsers.add_parser(
        'diagnose', 
        help='实例诊断',
        description='对 DSW 实例进行全面诊断，发现并报告潜在问题。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw diagnose           # 运行诊断（表格输出）
  dsw diagnose --json    # JSON 格式输出

诊断项目:
  🔌 网络连接
      - 外网连接状态
      - API 服务可达性
      - OSS 连接状态

  💾 存储状态
      - 磁盘空间使用率
      - 数据盘挂载状态
      - OSS 挂载状态

  🔐 权限检查
      - RAM 角色配置
      - OSS 访问权限
      - PAI 服务权限

  📦 资源状态
      - CPU/内存使用率
      - GPU 状态（如适用）
      - 进程健康检查

  ⚠️ 常见问题
      - 过期实例警告
      - 资源瓶颈警告
      - 配置错误警告

相关命令:
  dsw env          # 快速环境检测
  dsw metrics      # 资源监控
"""
    )
    diag_parser.add_argument('--json', action='store_true', help='JSON 格式输出')
    
    # datasets 命令
    datasets_parser = subparsers.add_parser(
        'datasets', 
        help='数据集挂载信息',
        description='显示实例的数据集挂载信息，包括已挂载的数据集和挂载路径。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw datasets                        # 显示当前实例的数据集挂载
  dsw datasets dsw-123456-abcde        # 显示指定实例的数据集挂载
  dsw datasets my-instance --format json

输出字段:
  DatasetId      - 数据集 ID
  DatasetName    - 数据集名称
  MountPath      - 挂载路径
  Size           - 数据集大小
  Type           - 数据集类型

常见挂载路径:
  /mnt/data/     - 默认数据盘挂载点
  /mnt/dataset/  - 数据集挂载点
  /mnt/workspace/ - 工作空间挂载点

相关命令:
  dsw get <instance>    # 查看实例详情
"""
    )
    datasets_parser.add_argument('instance', nargs='?', help='实例 ID 或名称（不指定则使用当前实例）')
    
    # gpu-usage 命令
    gpu_usage_parser = subparsers.add_parser(
        'gpu-usage',
        help='检查所有 GPU 实例使用率',
        description='批量检查工作空间内所有 GPU 实例的 GPU 使用率，识别高负载实例。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw gpu-usage                  # 检查所有 GPU 实例
  dsw gpu-usage --region cn-hangzhou

输出说明:
  ✅ 正常 - GPU 使用率 < 80%
  ⚠️ 高负载 - GPU 使用率 >= 80%

使用场景:
  - 日常巡检
  - 资源利用率监控
  - 发现高负载实例
"""
    )
    gpu_usage_parser.add_argument('--region', help='区域 ID')
    
    # info 命令
    info_parser = subparsers.add_parser(
        'info', 
        help='显示完整实例信息',
        description='一次性显示实例的完整信息，包括详情、资源使用和快照列表。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw info dsw-123456-abcde    # 显示实例完整信息
  dsw info my-instance          # 使用名称查询

输出内容:
  📋 基本信息
      - 实例 ID、名称、状态
      - 规格配置（CPU/GPU/内存）
      - 镜像信息
      - 创建时间、过期时间
      - 网络配置

  📊 资源使用
      - CPU 利用率
      - 内存使用率
      - GPU 使用率（如适用）

  📸 快照列表
      - 已创建的快照
      - 快照状态和大小

适用场景:
  - 快速了解实例全面状态
  - 问题排查前的信息收集
  - 实例健康检查

相关命令:
  dsw get <instance>     # 仅查看基本信息
  dsw metrics <instance> # 仅查看资源监控
  dsw snapshots <instance> # 仅查看快照
"""
    )
    info_parser.add_argument('instance', help='实例 ID 或名称（支持模糊匹配）')
    
    # trends 命令
    trends_parser = subparsers.add_parser(
        'trends',
        help='资源趋势分析',
        description='分析实例的资源使用趋势，识别模式、异常和优化机会。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw trends                         # 分析当前实例过去 7 天
  dsw trends --instance dsw-123456   # 分析指定实例
  dsw trends --days 14               # 分析过去 14 天
  dsw trends --days 7 --compare      # 与上一周对比
  dsw trends --save                  # 保存数据到历史文件
  dsw trends --format json           # JSON 格式输出

参数说明:
  --instance    实例 ID（不指定则使用当前实例）
  --days        分析天数（默认: 7）
  --start       开始日期 (YYYY-MM-DD)
  --end         结束日期 (YYYY-MM-DD)
  --interval    采集间隔小时数（默认: 1）
  --save        保存采集数据
  --compare     与上一周期对比

输出内容:
  📊 资源统计
      - CPU/内存/GPU 平均、最小、最大使用率
      - 峰值使用时段

  🔍 模式分析
      - 高/低负载时段统计
      - 异常波动检测

  💡 优化建议
      - 成本优化建议
      - 性能优化建议
      - 资源配置建议

历史数据存储:
  数据保存在 ~/.dsw-history/ 目录

相关命令:
  dsw metrics      # 实时资源监控
  dsw cost         # 成本估算
"""
    )
    trends_parser.add_argument('--instance', '-i', help='实例 ID（不指定则使用当前实例）')
    trends_parser.add_argument('--days', type=int, default=7, help='分析天数（默认: 7）')
    trends_parser.add_argument('--start', help='开始日期 (YYYY-MM-DD)')
    trends_parser.add_argument('--end', help='结束日期 (YYYY-MM-DD)')
    trends_parser.add_argument('--interval', type=int, default=1, help='采集间隔小时数')
    trends_parser.add_argument('--save', action='store_true', help='保存采集数据')
    trends_parser.add_argument('--compare', action='store_true', help='与上一周期对比')
    trends_parser.add_argument('--format', '-f', choices=['text', 'json', 'csv'], default='text', help='输出格式')
    
    # regions 命令
    regions_parser = subparsers.add_parser(
        'regions',
        help='列出所有可用区域',
        description='列出 PAI-DSW 支持的所有区域，包括区域名称、端点和可用状态。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw regions                    # 列出所有区域
  dsw regions --check            # 测试各区域连接性
  dsw regions --format json      # JSON 格式输出

输出字段:
  区域 ID      - 区域标识符（如 cn-hangzhou）
  区域名称    - 区域中文名称
  状态        - 可用/不可用
  延迟        - API 响应延迟（--check 时显示）
  特性        - 支持的特性（gpu/cpu/spot）

支持的区域:
  国内:
    cn-hangzhou    - 华东1（杭州）
    cn-shanghai    - 华东2（上海）
    cn-beijing     - 华北2（北京）
    cn-shenzhen    - 华南1（深圳）
    cn-hongkong    - 中国香港
    
  亚太:
    ap-northeast-1 - 日本东京
    ap-southeast-1 - 新加坡
    
  欧美:
    us-west-1      - 美国西部1（硅谷）
    us-east-1      - 美国东部1（弗吉尼亚）
    eu-central-1   - 德国法兰克福

相关命令:
  dsw detect-region       # 检测当前区域
  dsw compare-regions     # 比较区域性能
  dsw cross-region        # 跨区域实例管理
"""
    )
    regions_parser.add_argument('--check', action='store_true', help='测试区域连接性')
    
    # detect-region 命令
    detect_region_parser = subparsers.add_parser(
        'detect-region',
        help='检测当前区域',
        description='自动检测当前 DSW 实例所在的区域。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw detect-region          # 检测当前区域
  dsw detect-region --json   # JSON 格式输出

检测方式:
  1. 环境变量 ALIBABA_CLOUD_REGION_ID
  2. 环境变量 REGION
  3. 从 DSW 实例元数据获取
  4. 从可用区推断

输出信息:
  - 区域 ID
  - 区域名称
  - 端点地址
  - 支持的特性

相关命令:
  dsw regions           # 列出所有区域
  dsw cross-region      # 跨区域实例管理
"""
    )
    detect_region_parser.add_argument('--json', action='store_true', help='JSON 格式输出')
    
    # cross-region 命令
    cross_region_parser = subparsers.add_parser(
        'cross-region',
        help='跨区域实例管理',
        description='跨区域查询和管理 DSW 实例，支持查询多个区域的实例列表。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw cross-region                      # 查询所有区域的实例
  dsw cross-region --stats              # 显示统计信息
  dsw cross-region --regions cn-hangzhou,cn-shanghai  # 指定区域
  dsw cross-region --workspace ws-xxx   # 指定工作空间
  dsw cross-region --format json        # JSON 格式输出

参数说明:
  --regions, -r     指定区域（逗号分隔，不指定则查询所有）
  --workspace, -w   工作空间 ID（使用 "all" 查询所有工作空间）
  --stats           显示按区域统计信息

输出内容:
  - 各区域的实例列表
  - 实例 ID、名称、状态、规格
  - 区域汇总统计（--stats）

使用场景:
  - 查看全局资源分布
  - 发现跨区域运行的成本
  - 资源迁移规划

相关命令:
  dsw regions           # 列出所有区域
  dsw search-all        # 跨区域搜索实例
  dsw compare-regions   # 比较区域性能
"""
    )
    cross_region_parser.add_argument('--regions', '-r', help='指定区域（逗号分隔）')
    cross_region_parser.add_argument('--workspace', '-w', help='工作空间 ID（使用 "all" 查询所有）')
    cross_region_parser.add_argument('--stats', action='store_true', help='显示统计信息')
    
    # compare-regions 命令
    compare_regions_parser = subparsers.add_parser(
        'compare-regions',
        help='比较区域性能',
        description='比较不同区域的 API 响应性能，帮助选择最优区域。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw compare-regions                           # 比较主要区域性能
  dsw compare-regions --regions cn-hangzhou,cn-shanghai
  dsw compare-regions --json                    # JSON 格式输出

参数说明:
  --regions, -r   指定比较的区域（逗号分隔）
  --json          JSON 格式输出

输出内容:
  - 各区域 API 响应延迟
  - 性能排名（🥇🥈🥉）
  - 不可用区域列表

使用场景:
  - 选择延迟最低的区域
  - 评估跨区域操作成本
  - 故障排查时检查区域可用性

注意:
  - 延迟受网络环境影响
  - 建议在相同环境下多次测试

相关命令:
  dsw regions          # 列出所有区域
  dsw cross-region     # 跨区域实例管理
"""
    )
    compare_regions_parser.add_argument('--regions', '-r', help='指定区域（逗号分隔）')
    compare_regions_parser.add_argument('--json', action='store_true', help='JSON 格式输出')
    
    # search-all 命令
    search_all_parser = subparsers.add_parser(
        'search-all',
        help='跨区域搜索实例',
        description='在所有区域中搜索匹配的实例，适合查找跨区域部署的资源。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw search-all gpu-training        # 搜索名称包含 "gpu-training" 的实例
  dsw search-all dsw-12345           # 搜索 ID 包含 "dsw-12345" 的实例
  dsw search-all prod --workspace all  # 搜索所有工作空间

参数说明:
  query            搜索关键词（匹配实例名称或 ID）
  --workspace, -w  工作空间 ID（使用 "all" 查询所有工作空间）

搜索范围:
  - 实例名称 (InstanceName)
  - 实例 ID (InstanceId)

输出内容:
  - 匹配实例的详细信息
  - 所在区域
  - 当前状态

使用场景:
  - 查找全局唯一实例
  - 资源迁移前定位
  - 跨区域资产管理

相关命令:
  dsw search        # 当前区域搜索
  dsw cross-region  # 跨区域实例列表
"""
    )
    search_all_parser.add_argument('query', help='搜索关键词（匹配实例名称或 ID）')
    search_all_parser.add_argument('--workspace', '-w', help='工作空间 ID（使用 "all" 查询所有）')
    
    # tags 命令
    tags_parser = subparsers.add_parser(
        'tags',
        help='列出实例标签',
        description='列出指定实例的所有标签，以表格或 JSON 格式显示。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw tags dsw-123456              # 列出实例标签
  dsw tags my-instance             # 使用名称查询
  dsw tags dsw-123456 --format json # JSON 格式输出

输出内容:
  - 实例 ID 和名称
  - 所有标签键值对

相关命令:
  dsw tag-add <instance> <tags>   # 添加标签
  dsw tag-remove <instance> <keys> # 删除标签
  dsw tag-filter <filter>          # 按标签筛选
"""
    )
    tags_parser.add_argument('instance', help='实例 ID 或名称（支持模糊匹配）')
    
    # tag-add 命令
    tag_add_parser = subparsers.add_parser(
        'tag-add',
        help='添加标签到实例',
        description='为一个或多个实例添加标签。标签可用于分类、筛选和管理实例。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw tag-add dsw-123456 env=prod
  dsw tag-add my-instance env=prod,team=ml
  dsw tag-add dsw-123456 '{"env":"prod"}' -f

标签格式:
  key=value,key2=value2    - 简单格式
  '{"key":"value"}'        - JSON 格式

标签命名规则:
  - 区分大小写
  - 支持字母、数字、连字符、下划线
  - 最大长度: 键 128 字符，值 256 字符

使用场景:
  - 标识环境（env=dev/prod）
  - 标记团队（team=ml/backend）
  - 标记用途（purpose=training/inference）

相关命令:
  dsw tags <instance>              # 查看标签
  dsw tag-remove <instance> <keys> # 删除标签
  dsw tag-filter env=prod          # 按标签筛选
"""
    )
    tag_add_parser.add_argument('instance', help='实例 ID 或名称（支持模糊匹配）')
    tag_add_parser.add_argument('tags', help='标签（格式: key=value,key2=value2 或 JSON）')
    tag_add_parser.add_argument('--force', '-f', action='store_true', help='跳过确认')
    
    # tag-remove 命令
    tag_remove_parser = subparsers.add_parser(
        'tag-remove',
        help='从实例删除标签',
        description='从指定实例删除一个或多个标签。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw tag-remove dsw-123456 env
  dsw tag-remove my-instance env,team
  dsw tag-remove dsw-123456 temp -f

参数说明:
  instance   实例 ID 或名称
  keys       要删除的标签键（逗号分隔多个）
  --force    跳过确认直接执行

相关命令:
  dsw tags <instance>          # 查看标签
  dsw tag-add <instance> <tags> # 添加标签
"""
    )
    tag_remove_parser.add_argument('instance', help='实例 ID 或名称（支持模糊匹配）')
    tag_remove_parser.add_argument('keys', help='要删除的标签键（逗号分隔）')
    tag_remove_parser.add_argument('--force', '-f', action='store_true', help='跳过确认')
    
    # tag-set 命令
    tag_set_parser = subparsers.add_parser(
        'tag-set',
        help='设置实例标签（替换所有）',
        description='替换实例的所有标签。注意：此操作会清除现有标签！',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw tag-set dsw-123456 env=prod,team=ml
  dsw tag-set my-instance env=dev
  dsw tag-set dsw-123456 ''  # 清除所有标签

⚠️ 警告:
  此命令会替换所有标签，现有标签将被清除！

相关命令:
  dsw tags <instance>              # 查看标签
  dsw tag-add <instance> <tags>    # 添加标签（保留现有）
"""
    )
    tag_set_parser.add_argument('instance', help='实例 ID 或名称（支持模糊匹配）')
    tag_set_parser.add_argument('tags', help='新标签（格式: key=value 或空字符串清除所有）')
    tag_set_parser.add_argument('--force', '-f', action='store_true', help='跳过确认')
    
    # tag-batch-add 命令
    tag_batch_add_parser = subparsers.add_parser(
        'tag-batch-add',
        help='批量添加标签',
        description='为多个实例批量添加标签。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 指定实例列表
  dsw tag-batch-add env=prod --instances dsw-123,dsw-456

  # 通过名称模糊匹配
  dsw tag-batch-add team=ml --query gpu

  # 批量标记
  dsw tag-batch-add env=prod,team=ml --instances dsw-123,dsw-456 -f

参数说明:
  tags          要添加的标签
  --instances   实例 ID 列表（逗号分隔）
  --query       按名称/ID 模糊匹配实例
  --force       跳过确认

使用场景:
  - 批量标记环境
  - 批量分配团队标签
  - 批量标记项目

相关命令:
  dsw tag-batch-remove <keys>  # 批量删除标签
  dsw tag-filter <filter>      # 按标签筛选
"""
    )
    tag_batch_add_parser.add_argument('tags', help='要添加的标签（格式: key=value,key2=value2）')
    tag_batch_add_parser.add_argument('--instances', '-i', help='实例 ID 列表（逗号分隔）')
    tag_batch_add_parser.add_argument('--query', '-q', help='按名称/ID 模糊匹配实例')
    tag_batch_add_parser.add_argument('--force', '-f', action='store_true', help='跳过确认')
    
    # tag-batch-remove 命令
    tag_batch_remove_parser = subparsers.add_parser(
        'tag-batch-remove',
        help='批量删除标签',
        description='从多个实例批量删除标签。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw tag-batch-remove temp --instances dsw-123,dsw-456
  dsw tag-batch-remove env,team --query test
  dsw tag-batch-remove old-tag --instances dsw-123,dsw-456 -f

参数说明:
  keys          要删除的标签键（逗号分隔）
  --instances   实例 ID 列表（逗号分隔）
  --query       按名称/ID 模糊匹配实例
  --force       跳过确认

相关命令:
  dsw tag-batch-add <tags>     # 批量添加标签
  dsw tag-export               # 导出标签
"""
    )
    tag_batch_remove_parser.add_argument('keys', help='要删除的标签键（逗号分隔）')
    tag_batch_remove_parser.add_argument('--instances', '-i', help='实例 ID 列表（逗号分隔）')
    tag_batch_remove_parser.add_argument('--query', '-q', help='按名称/ID 模糊匹配实例')
    tag_batch_remove_parser.add_argument('--force', '-f', action='store_true', help='跳过确认')
    
    # tag-filter 命令
    tag_filter_parser = subparsers.add_parser(
        'tag-filter',
        help='按标签筛选实例',
        description='根据标签键值对筛选实例。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 按标签值筛选
  dsw tag-filter env=prod
  dsw tag-filter env=prod,team=ml

  # 按标签键筛选（不管值）
  dsw tag-filter env --has-key

  # 组合筛选
  dsw tag-filter team=ml --has-key gpu

参数说明:
  filter       标签筛选条件（key=value 或仅 key）
  --has-key    额外要求拥有此键（可组合）

输出:
  匹配的实例列表，包括 ID、名称、状态和匹配的标签

相关命令:
  dsw tag-export               # 导出所有标签
  dsw list                     # 列出所有实例
"""
    )
    tag_filter_parser.add_argument('filter', help='标签筛选条件（key=value 或仅 key）')
    tag_filter_parser.add_argument('--has-key', help='额外要求拥有此键')
    
    # tag-export 命令
    tag_export_parser = subparsers.add_parser(
        'tag-export',
        help='导出所有实例标签',
        description='导出所有实例的标签信息，支持表格、JSON 和 CSV 格式。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw tag-export                  # 表格格式
  dsw tag-export --format json    # JSON 格式
  dsw tag-export --format csv     # CSV 格式（适合导入 Excel）

输出内容:
  - 所有实例列表
  - 每个实例的标签
  - 所有唯一的标签键

使用场景:
  - 标签审计
  - 资源盘点
  - 导出报表

相关命令:
  dsw tag-filter <filter>  # 按标签筛选
  dsw list                 # 列出所有实例
"""
    )
    tag_export_parser.add_argument('--format', '-f', choices=['table', 'json', 'csv'], default='table', help='输出格式')
    
    args = parser.parse_args()
    
    # 禁用颜色
    if args.no_color or not sys.stdout.isatty():
        Colors.disable()
    
    # 未指定命令，显示帮助
    if not args.command:
        parser.print_help()
        return 0
    
    # 调度命令
    commands = {
        'config': cmd_config,
        'list': cmd_list,
        'get': cmd_get,
        'start': cmd_start,
        'stop': cmd_stop,
        'delete': cmd_delete,
        'create': cmd_create,
        'snapshot': cmd_snapshot,
        'snapshots': cmd_snapshots,
        'specs': cmd_specs,
        'update': cmd_update,
        'metrics': cmd_metrics,
        'search': cmd_search,
        'status': cmd_status,
        'workspaces': cmd_workspaces,
        'images': cmd_images,
        'cost': cmd_cost,
        'env': cmd_env,
        'diagnose': cmd_diagnose,
        'datasets': cmd_datasets,
        'gpu-usage': cmd_gpu_usage,
        'info': cmd_info,
        'trends': cmd_trends,
        'regions': cmd_regions,
        'detect-region': cmd_detect_region,
        'cross-region': cmd_cross_region,
        'compare-regions': cmd_compare_regions,
        'search-all': cmd_search_all,
        'tags': cmd_tags,
        'tag-add': cmd_tag_add,
        'tag-remove': cmd_tag_remove,
        'tag-set': cmd_tag_set,
        'tag-batch-add': cmd_tag_batch_add,
        'tag-batch-remove': cmd_tag_batch_remove,
        'tag-filter': cmd_tag_filter,
        'tag-export': cmd_tag_export,
    }
    
    cmd_func = commands.get(args.command)
    if cmd_func:
        return cmd_func(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())