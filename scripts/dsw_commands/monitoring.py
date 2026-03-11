"""
Monitoring commands: metrics, gpu-usage, trends, cost, status.
"""

import os
import re
import subprocess

from dsw_commands.formatting import (
    Colors, colorize, print_header, print_info, print_error,
    print_warning, print_success,
)
from dsw_commands.helpers import SCRIPT_DIR, run_script, resolve_instance
from exceptions import InstanceNotFoundError, InstanceAmbiguousError


def _resolve_or_fail(identifier):
    """Resolve instance, printing errors on failure."""
    try:
        return resolve_instance(identifier), 0
    except InstanceNotFoundError as e:
        print_error(e.message)
        return None, 1
    except InstanceAmbiguousError as e:
        print_error(e.message)
        for m in e.details["matches"]:
            print(f"  - {m['name']} ({m['id']})")
        print_info("请使用更精确的名称或直接使用实例 ID")
        return None, 1


def cmd_metrics(args):
    """实例资源监控"""
    instance_id, err = _resolve_or_fail(args.instance)
    if err:
        return err

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

    return run_script('get_instance_metrics', script_args)


def cmd_gpu_usage(args):
    """检查所有 GPU 实例的使用率"""
    print_header("GPU 实例使用率检查")

    from dsw_utils import create_client, get_workspace_id
    from alibabacloud_pai_dsw20220101 import models as dsw_models

    client = create_client(args.region)

    try:
        workspace_id = get_workspace_id(allow_interactive=False)
    except:
        workspace_id = None

    if not workspace_id:
        print_error("需要设置工作空间 ID")
        return 1

    # Get all instances
    request = dsw_models.ListInstancesRequest()
    request.workspace_id = workspace_id
    response = client.list_instances(request)

    # GPU spec keywords
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
        try:
            result = subprocess.run(
                ['python3', 'get_instance_metrics.py', instance_id,
                 '--region', args.region or '', '--summary'],
                capture_output=True, text=True, cwd=SCRIPT_DIR,
            )

            gpu_usage = None
            for line in result.stdout.split('\n'):
                if 'gpu' in line.lower() and '%' in line and 'gpu-memory' not in line.lower():
                    match = re.search(r':\s*(\d+\.?\d*)%', line)
                    if match:
                        gpu_usage = float(match.group(1))
                        break

            if gpu_usage is not None:
                if gpu_usage >= 80:
                    print(f"  {colorize(name, Colors.YELLOW)} ({instance_id[:20]}...): "
                          f"GPU {colorize(f'{gpu_usage:.2f}%', Colors.RED)} ⚠️")
                    high_usage.append({'name': name, 'id': instance_id, 'usage': gpu_usage})
                else:
                    print(f"  {name} ({instance_id[:20]}...): GPU {gpu_usage:.2f}% ✅")
            else:
                print(f"  {name}: 无法获取 GPU 数据")

        except Exception:
            print(f"  {name}: 检查失败")

    print()

    if high_usage:
        print_warning(f"GPU 使用率超过 80% 的实例 ({len(high_usage)} 个):")
        for item in high_usage:
            print(f"  - {item['name']}: {item['usage']:.2f}%")
    else:
        print_success("没有 GPU 使用率超过 80% 的实例")

    return 0


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


def cmd_cost(args):
    """成本估算"""
    print_header("实例成本估算")

    script_args = ['--format', args.format]
    if args.instance:
        script_args.extend(['--instance', args.instance])
    if args.region:
        script_args.extend(['--region', args.region])

    return run_script('estimate_cost', script_args)


def cmd_status(args):
    """显示当前实例状态（如果在 DSW 实例中运行）"""
    print_header("当前实例状态")

    hostname = os.getenv('HOSTNAME', '')
    if hostname.startswith('dsw-'):
        print_info(f"当前实例 ID: {hostname}")
        return run_script('get_instance', [hostname])
    else:
        print_warning("不在 DSW 实例环境中运行")
        print_info("如需查询特定实例，请使用: dsw get <instance>")
        return 0
