"""
dsw_commands - Command handler sub-modules for PAI-DSW CLI.

This package contains all command implementations, organized by functional area.
The dsw.py CLI entry point imports command handlers from here.
"""

# Formatting utilities (re-exported for convenience)
from dsw_commands.formatting import (
    Colors,
    colorize,
    print_header,
    print_success,
    print_error,
    print_warning,
    print_info,
    status_badge,
)

# Helpers
from dsw_commands.helpers import (
    SCRIPT_DIR,
    run_script,
    get_instances_json,
    resolve_instance,
)

# Command handlers - instance management
from dsw_commands.instance import (
    cmd_list,
    cmd_get,
    cmd_start,
    cmd_stop,
    cmd_delete,
    cmd_create,
    cmd_update,
)

# Command handlers - monitoring
from dsw_commands.monitoring import (
    cmd_metrics,
    cmd_gpu_usage,
    cmd_trends,
    cmd_cost,
    cmd_status,
)

# Command handlers - resource / snapshot
from dsw_commands.resource import (
    cmd_specs,
    cmd_images,
    cmd_workspaces,
    cmd_datasets,
    cmd_snapshot,
    cmd_snapshots,
    cmd_info,
)

# Command handlers - search
from dsw_commands.search import (
    cmd_search,
    cmd_search_all,
)

# Command handlers - config
from dsw_commands.config import cmd_config

# Command handlers - tags
from dsw_commands.tags import (
    cmd_tags,
    cmd_tag_add,
    cmd_tag_remove,
    cmd_tag_set,
    cmd_tag_batch_add,
    cmd_tag_batch_remove,
    cmd_tag_filter,
    cmd_tag_export,
)

# Command handlers - region
from dsw_commands.region import (
    cmd_regions,
    cmd_detect_region,
    cmd_cross_region,
    cmd_compare_regions,
)

# Command handlers - diagnostic
from dsw_commands.diagnostic import (
    cmd_env,
    cmd_diagnose,
)
