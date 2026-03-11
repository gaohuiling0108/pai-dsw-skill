"""
Diagnostic commands: env, diagnose.
"""

from dsw_commands.formatting import print_header
from dsw_commands.helpers import run_script


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
