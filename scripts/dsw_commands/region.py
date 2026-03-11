"""
Multi-region commands: regions, detect-region, cross-region, compare-regions.
"""

from dsw_commands.formatting import print_header
from dsw_commands.helpers import run_script


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
