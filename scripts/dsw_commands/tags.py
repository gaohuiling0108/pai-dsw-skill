"""
Tag management commands.
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


def cmd_tags(args):
    """列出实例标签"""
    instance_id, err = _resolve_or_fail(args.instance)
    if err:
        return err

    print_header(f"实例标签: {instance_id}")

    script_args = [instance_id]
    if args.format:
        script_args.extend(['--format', args.format])

    return run_script('manage_tags', ['list'] + script_args)


def cmd_tag_add(args):
    """添加标签到实例"""
    instance_id, err = _resolve_or_fail(args.instance)
    if err:
        return err

    print_header(f"添加标签: {instance_id}")

    script_args = ['add', instance_id, args.tags]
    if args.force:
        script_args.append('--force')

    return run_script('manage_tags', script_args)


def cmd_tag_remove(args):
    """从实例删除标签"""
    instance_id, err = _resolve_or_fail(args.instance)
    if err:
        return err

    print_header(f"删除标签: {instance_id}")

    script_args = ['remove', instance_id, args.keys]
    if args.force:
        script_args.append('--force')

    return run_script('manage_tags', script_args)


def cmd_tag_set(args):
    """设置实例标签（替换所有）"""
    instance_id, err = _resolve_or_fail(args.instance)
    if err:
        return err

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
