"""
Search commands: search, search-all.
"""

from dsw_commands.formatting import (
    print_header, print_warning, status_badge,
)
from dsw_commands.helpers import run_script, get_instances_json


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

    # Table output
    print(f"{'实例ID':<40} {'名称':<30} {'状态':<12} {'规格':<20}")
    print("-" * 102)

    for inst in results:
        instance_id = inst.get('InstanceId', 'N/A')
        name = inst.get('InstanceName', 'N/A')
        status = inst.get('Status', 'Unknown')
        spec = inst.get('InstanceType', 'N/A') or 'N/A'

        print(f"{instance_id:<40} {name:<30} {status_badge(status):<20} {spec:<20}")

    return 0


def cmd_search_all(args):
    """跨区域搜索实例"""
    print_header(f"跨区域搜索: {args.query}")

    script_args = ['search', args.query]
    if args.workspace:
        script_args.extend(['--workspace', args.workspace])

    return run_script('multi_region', script_args)
