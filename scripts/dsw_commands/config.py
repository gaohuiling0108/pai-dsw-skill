"""
Configuration management command.
"""

from dsw_commands.formatting import (
    print_header, print_info, print_success, print_error,
)


def cmd_config(args):
    """配置命令"""
    import importlib
    env_detector = importlib.import_module('env_detector')

    if args.config_command == 'init':
        # Interactive setup
        config = env_detector.setup_interactive()
        if config:
            print_success("配置完成！")
            return 0
        return 1

    elif args.config_command == 'show':
        # Show current config
        env_detector.print_environment_info()
        return 0

    elif args.config_command == 'set':
        # Set config item
        config = env_detector.load_config()
        config[args.key] = args.value
        if env_detector.save_config(config):
            print_success(f"已设置 {args.key} = {args.value}")
            return 0
        return 1

    elif args.config_command == 'workspace':
        # Set default workspace
        if args.workspace_id:
            config = env_detector.load_config()
            config['workspace_id'] = args.workspace_id
            if env_detector.save_config(config):
                print_success(f"已设置默认工作空间: {args.workspace_id}")
                return 0
            return 1
        else:
            # List workspaces for interactive selection
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
        # Default: show config
        env_detector.print_environment_info()
        return 0
