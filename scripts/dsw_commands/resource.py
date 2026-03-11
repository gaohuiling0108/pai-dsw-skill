"""
Resource & snapshot commands: specs, images, workspaces, datasets, snapshot(s), info.
"""

from dsw_commands.formatting import print_header, print_info, print_error
from dsw_commands.helpers import run_script, resolve_instance
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


def cmd_specs(args):
    """列出可用规格"""
    print_header("可用 ECS 规格")

    script_args = ['--format', args.format]
    if args.gpu:
        script_args.append('--gpu')
    if args.cpu:
        script_args.append('--cpu')

    return run_script('list_ecs_specs', script_args)


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


def cmd_workspaces(args):
    """列出工作空间"""
    print_header("PAI 工作空间列表")

    script_args = ['--format', args.format]
    if args.region:
        script_args.extend(['--region', args.region])

    return run_script('list_workspaces', script_args)


def cmd_datasets(args):
    """数据集挂载信息"""
    print_header("数据集挂载信息")

    script_args = ['--format', args.format]
    if args.instance:
        script_args.insert(0, args.instance)

    return run_script('list_datasets', script_args)


def cmd_snapshot(args):
    """创建快照"""
    instance_id, err = _resolve_or_fail(args.instance)
    if err:
        return err

    print_header(f"创建快照: {args.name}")

    script_args = [instance_id, args.name]
    if args.description:
        script_args.extend(['--description', args.description])

    return run_script('create_snapshot', script_args)


def cmd_snapshots(args):
    """列出快照"""
    instance_id, err = _resolve_or_fail(args.instance)
    if err:
        return err

    print_header(f"实例快照: {instance_id}")
    return run_script('list_snapshots', [instance_id, '--format', args.format])


def cmd_info(args):
    """显示完整实例信息（详情 + 资源 + 快照）"""
    instance_id, err = _resolve_or_fail(args.instance)
    if err:
        return err

    print_header(f"实例完整信息: {instance_id}")

    # Details
    print(f"\n📋 基本信息")
    ret = run_script('get_instance', [instance_id])

    # Metrics
    print(f"\n📊 资源使用")
    ret2 = run_script('get_instance_metrics', [instance_id, '--summary'])

    # Snapshots
    print(f"\n📸 快照列表")
    ret3 = run_script('list_snapshots', [instance_id])

    return max(ret, ret2, ret3)
