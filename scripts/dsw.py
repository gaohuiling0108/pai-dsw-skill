#!/usr/bin/env python3
"""
PAI-DSW Unified CLI Tool
统一命令行入口，支持实例名称模糊搜索和彩色输出

命令实现已拆分到 dsw_commands/ 子模块。
本文件仅保留 CLI 参数定义和命令路由。
"""

import argparse
import sys
import os

# Ensure scripts/ is on the path for imports
SCRIPT_PATH = os.path.abspath(__file__)
if os.path.islink(SCRIPT_PATH):
    SCRIPT_PATH = os.path.realpath(SCRIPT_PATH)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# Import all command handlers and utilities from dsw_commands
from dsw_commands import (
    # Formatting
    Colors,
    colorize,
    print_header,
    print_success,
    print_error,
    print_warning,
    print_info,
    status_badge,
    # Helpers
    run_script,
    get_instances_json,
    resolve_instance,
    # Instance commands
    cmd_list,
    cmd_get,
    cmd_start,
    cmd_stop,
    cmd_delete,
    cmd_create,
    cmd_update,
    # Monitoring commands
    cmd_metrics,
    cmd_gpu_usage,
    cmd_trends,
    cmd_cost,
    cmd_status,
    # Resource / snapshot commands
    cmd_specs,
    cmd_images,
    cmd_workspaces,
    cmd_datasets,
    cmd_snapshot,
    cmd_snapshots,
    cmd_info,
    # Search commands
    cmd_search,
    cmd_search_all,
    # Config
    cmd_config,
    # Tag commands
    cmd_tags,
    cmd_tag_add,
    cmd_tag_remove,
    cmd_tag_set,
    cmd_tag_batch_add,
    cmd_tag_batch_remove,
    cmd_tag_filter,
    cmd_tag_export,
    # Region commands
    cmd_regions,
    cmd_detect_region,
    cmd_cross_region,
    cmd_compare_regions,
    # Diagnostic commands
    cmd_env,
    cmd_diagnose,
)


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
    config_subparsers.add_parser('init', help='交互式初始化配置')
    
    # config show
    config_subparsers.add_parser('show', help='显示当前配置')
    
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
  dsw update dsw-123456-abcde --spec ecs.g6.2xlarge
  dsw update my-instance --cpu 8 --memory 32
  dsw update gpu-test --gpu 2 -f
  dsw update my-inst --labels '{"env":"prod"}'

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
  dsw metrics dsw-123456-abcde
  dsw metrics my-instance --type cpu
  dsw metrics gpu-train --type gpu
  dsw metrics my-inst --start 2024-01-01T00:00:00Z --end 2024-01-02T00:00:00Z
  dsw metrics my-instance --summary

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

相关命令:
  dsw list     # 列出所有实例
  dsw get      # 查看实例详情
"""
    )
    search_parser.add_argument('query', help='搜索关键词（支持名称/ID/标签模糊匹配）')
    
    # status 命令
    subparsers.add_parser(
        'status', 
        help='显示当前实例状态',
        description='显示当前运行的 DSW 实例的状态信息。仅在 DSW 实例内部运行时有效。',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  dsw status    # 在 DSW 实例中运行，显示当前实例信息

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
  dsw images --search pytorch     # 搜索包含 "pytorch" 的镜像

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
  dsw cross-region --regions cn-hangzhou,cn-shanghai

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
  dsw compare-regions
  dsw compare-regions --regions cn-hangzhou,cn-shanghai
  dsw compare-regions --json

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
  dsw search-all prod --workspace all  # 搜索所有工作空间

相关命令:
  dsw search        # 当前区域搜索
  dsw cross-region  # 跨区域实例列表
"""
    )
    search_all_parser.add_argument('query', help='搜索关键词（匹配实例名称或 ID）')
    search_all_parser.add_argument('--workspace', '-w', help='工作空间 ID（使用 "all" 查询所有）')
    
    # tags 命令
    tags_parser = subparsers.add_parser('tags', help='列出实例标签',
        description='列出指定实例的所有标签，以表格或 JSON 格式显示。')
    tags_parser.add_argument('instance', help='实例 ID 或名称（支持模糊匹配）')
    
    # tag-add 命令
    tag_add_parser = subparsers.add_parser('tag-add', help='添加标签到实例',
        description='为一个或多个实例添加标签。标签可用于分类、筛选和管理实例。')
    tag_add_parser.add_argument('instance', help='实例 ID 或名称（支持模糊匹配）')
    tag_add_parser.add_argument('tags', help='标签（格式: key=value,key2=value2 或 JSON）')
    tag_add_parser.add_argument('--force', '-f', action='store_true', help='跳过确认')
    
    # tag-remove 命令
    tag_remove_parser = subparsers.add_parser('tag-remove', help='从实例删除标签',
        description='从指定实例删除一个或多个标签。')
    tag_remove_parser.add_argument('instance', help='实例 ID 或名称（支持模糊匹配）')
    tag_remove_parser.add_argument('keys', help='要删除的标签键（逗号分隔）')
    tag_remove_parser.add_argument('--force', '-f', action='store_true', help='跳过确认')
    
    # tag-set 命令
    tag_set_parser = subparsers.add_parser('tag-set', help='设置实例标签（替换所有）',
        description='替换实例的所有标签。注意：此操作会清除现有标签！')
    tag_set_parser.add_argument('instance', help='实例 ID 或名称（支持模糊匹配）')
    tag_set_parser.add_argument('tags', help='新标签（格式: key=value 或空字符串清除所有）')
    tag_set_parser.add_argument('--force', '-f', action='store_true', help='跳过确认')
    
    # tag-batch-add 命令
    tag_batch_add_parser = subparsers.add_parser('tag-batch-add', help='批量添加标签',
        description='为多个实例批量添加标签。')
    tag_batch_add_parser.add_argument('tags', help='要添加的标签（格式: key=value,key2=value2）')
    tag_batch_add_parser.add_argument('--instances', '-i', help='实例 ID 列表（逗号分隔）')
    tag_batch_add_parser.add_argument('--query', '-q', help='按名称/ID 模糊匹配实例')
    tag_batch_add_parser.add_argument('--force', '-f', action='store_true', help='跳过确认')
    
    # tag-batch-remove 命令
    tag_batch_remove_parser = subparsers.add_parser('tag-batch-remove', help='批量删除标签',
        description='从多个实例批量删除标签。')
    tag_batch_remove_parser.add_argument('keys', help='要删除的标签键（逗号分隔）')
    tag_batch_remove_parser.add_argument('--instances', '-i', help='实例 ID 列表（逗号分隔）')
    tag_batch_remove_parser.add_argument('--query', '-q', help='按名称/ID 模糊匹配实例')
    tag_batch_remove_parser.add_argument('--force', '-f', action='store_true', help='跳过确认')
    
    # tag-filter 命令
    tag_filter_parser = subparsers.add_parser('tag-filter', help='按标签筛选实例',
        description='根据标签键值对筛选实例。')
    tag_filter_parser.add_argument('filter', help='标签筛选条件（key=value 或仅 key）')
    tag_filter_parser.add_argument('--has-key', help='额外要求拥有此键')
    
    # tag-export 命令
    tag_export_parser = subparsers.add_parser('tag-export', help='导出所有实例标签',
        description='导出所有实例的标签信息，支持表格、JSON 和 CSV 格式。')
    tag_export_parser.add_argument('--format', '-f', choices=['table', 'json', 'csv'], help='输出格式')
    
    # ========================================================================
    # 解析参数和命令路由
    # ========================================================================
    args = parser.parse_args()
    
    # 处理颜色
    if args.no_color or not sys.stdout.isatty():
        Colors.disable()
    
    # 未指定命令
    if not args.command:
        parser.print_help()
        return 0
    
    # 命令路由表
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
