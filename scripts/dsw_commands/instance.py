"""
Instance management commands: list, get, start, stop, delete, create, update.
"""

from dsw_commands.formatting import (
    Colors, print_header, print_info, print_warning, print_error,
)
from dsw_commands.helpers import run_script, resolve_instance
from exceptions import InstanceNotFoundError, InstanceAmbiguousError


def _resolve_or_fail(identifier):
    """Resolve instance, printing errors on failure. Returns (id, exit_code)."""
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
    instance_id, err = _resolve_or_fail(args.instance)
    if err:
        return err

    print_header(f"实例详情: {instance_id}")
    return run_script('get_instance', [instance_id, '--format', args.format])


def cmd_start(args):
    """启动实例"""
    instance_id, err = _resolve_or_fail(args.instance)
    if err:
        return err

    print_header(f"启动实例: {instance_id}")
    print_info("正在启动...")

    return run_script('start_instance', [instance_id])


def cmd_stop(args):
    """停止实例"""
    instance_id, err = _resolve_or_fail(args.instance)
    if err:
        return err

    print_header(f"停止实例: {instance_id}")

    # Confirmation
    if not args.force:
        confirm = input(f"{Colors.YELLOW}确认要停止实例 {instance_id} 吗？(yes/no): {Colors.RESET}")
        if confirm.lower() not in ['yes', 'y']:
            print_info("已取消")
            return 0

    print_info("正在停止...")
    return run_script('stop_instance', [instance_id, '--force'])


def cmd_delete(args):
    """删除实例"""
    instance_id, err = _resolve_or_fail(args.instance)
    if err:
        return err

    print_header(f"删除实例: {instance_id}")
    print_warning("⚠️ 删除操作不可恢复！")

    # Confirmation
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


def cmd_update(args):
    """更新实例规格"""
    instance_id, err = _resolve_or_fail(args.instance)
    if err:
        return err

    print_header(f"更新实例: {instance_id}")

    # Confirmation
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
