#!/usr/bin/env python3
"""
PAI-DSW MCP Server

Exposes core DSW operations as standard MCP tools for AI Agent integration.
Communicates via stdio using the Model Context Protocol.

Usage:
    python mcp_server.py

Requires:
    pip install mcp
"""

import json
import os
import sys

# Ensure scripts/ is on the path for local imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from exceptions import DSWError, InstanceNotFoundError, InstanceAmbiguousError
from dsw_utils import filter_response, INSTANCE_DETAIL_FIELDS

# ---------------------------------------------------------------------------
# Lazy imports for standalone scripts (avoids loading SDK at module level)
# ---------------------------------------------------------------------------

def _import_get_instance():
    from get_instance import get_instance
    return get_instance

def _import_list_instances():
    from list_instances import list_instances
    return list_instances

def _import_start_instance():
    from start_instance import start_instance
    return start_instance

def _import_stop_instance():
    from stop_instance import stop_instance
    return stop_instance

def _import_create_instance():
    from create_instance import create_dsw_instance
    return create_dsw_instance

def _import_list_images():
    from list_images import list_images
    return list_images

def _import_list_ecs_specs():
    from list_ecs_specs import list_ecs_specs
    return list_ecs_specs

def _import_get_metrics():
    from get_instance_metrics import get_instance_metrics
    return get_instance_metrics

def _resolve(identifier: str) -> str:
    """Resolve instance name to ID. Raises DSWError on failure."""
    from dsw_commands.helpers import resolve_instance
    return resolve_instance(identifier)


# ---------------------------------------------------------------------------
# MCP Server setup
# ---------------------------------------------------------------------------

server = Server("pai-dsw-skill")


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS = [
    Tool(
        name="list_instances",
        description="列出当前工作空间中的所有 PAI-DSW 实例。返回实例 ID、名称、状态等信息。",
        inputSchema={
            "type": "object",
            "properties": {
                "detail_level": {
                    "type": "string",
                    "enum": ["brief", "summary", "full"],
                    "default": "summary",
                    "description": "返回信息的详细程度。brief=仅ID/名称/状态, summary=核心字段(默认), full=全部字段"
                },
            },
        },
    ),
    Tool(
        name="get_instance",
        description="获取指定 PAI-DSW 实例的详细信息。支持实例 ID 或名称模糊匹配。",
        inputSchema={
            "type": "object",
            "properties": {
                "instance": {
                    "type": "string",
                    "description": "实例 ID (如 dsw-xxx) 或名称 (支持模糊匹配)"
                },
                "detail_level": {
                    "type": "string",
                    "enum": ["brief", "summary", "full"],
                    "default": "full",
                    "description": "返回信息的详细程度"
                },
            },
            "required": ["instance"],
        },
    ),
    Tool(
        name="start_instance",
        description="启动一个已停止的 PAI-DSW 实例。实例必须处于 Stopped 状态。",
        inputSchema={
            "type": "object",
            "properties": {
                "instance": {
                    "type": "string",
                    "description": "实例 ID 或名称"
                },
            },
            "required": ["instance"],
        },
    ),
    Tool(
        name="stop_instance",
        description="停止一个运行中的 PAI-DSW 实例。停止后数据保留，仅释放计算资源。",
        inputSchema={
            "type": "object",
            "properties": {
                "instance": {
                    "type": "string",
                    "description": "实例 ID 或名称"
                },
            },
            "required": ["instance"],
        },
    ),
    Tool(
        name="create_instance",
        description="创建一个新的 PAI-DSW 实例。需要指定名称、镜像和规格。",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "实例名称"},
                "image": {"type": "string", "description": "镜像 ID 或名称"},
                "instance_type": {"type": "string", "description": "ECS 规格类型 (如 ecs.g6.large)"},
                "labels": {
                    "type": "object",
                    "description": "标签键值对 (可选)",
                    "additionalProperties": {"type": "string"},
                },
            },
            "required": ["name", "image", "instance_type"],
        },
    ),
    Tool(
        name="list_images",
        description="列出可用的 PAI-DSW 镜像，包括官方镜像和自定义镜像。",
        inputSchema={
            "type": "object",
            "properties": {
                "image_type": {
                    "type": "string",
                    "enum": ["all", "official", "custom"],
                    "default": "all",
                    "description": "镜像类型"
                },
            },
        },
    ),
    Tool(
        name="list_specs",
        description="列出可用的 ECS 实例规格，包括 CPU/GPU/内存配置信息。",
        inputSchema={
            "type": "object",
            "properties": {
                "gpu_only": {
                    "type": "boolean",
                    "default": False,
                    "description": "仅显示 GPU 规格"
                },
            },
        },
    ),
    Tool(
        name="get_instance_metrics",
        description="获取实例的资源使用指标 (CPU/内存/GPU 利用率)。",
        inputSchema={
            "type": "object",
            "properties": {
                "instance": {
                    "type": "string",
                    "description": "实例 ID 或名称"
                },
                "metric_type": {
                    "type": "string",
                    "enum": ["cpu", "memory", "gpu", "all"],
                    "default": "all",
                    "description": "指标类型"
                },
            },
            "required": ["instance"],
        },
    ),
]


# ---------------------------------------------------------------------------
# Handler registration
# ---------------------------------------------------------------------------

@server.list_tools()
async def list_tools():
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        if name == "list_instances":
            detail = arguments.get("detail_level", "summary")
            fn = _import_list_instances()
            instances = fn(format="json", detail_level=detail)
            return [TextContent(type="text", text=json.dumps(instances, indent=2, ensure_ascii=False, default=str))]

        elif name == "get_instance":
            detail = arguments.get("detail_level", "full")
            instance_id = _resolve(arguments["instance"])
            fn = _import_get_instance()
            result = fn(instance_id, detail_level=detail)
            if result is None:
                return [TextContent(type="text", text=json.dumps({"error": "INSTANCE_NOT_FOUND", "message": f"实例 {arguments['instance']} 未找到"}))]
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False, default=str))]

        elif name == "start_instance":
            instance_id = _resolve(arguments["instance"])
            fn = _import_start_instance()
            result = fn(instance_id)
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False, default=str))]

        elif name == "stop_instance":
            instance_id = _resolve(arguments["instance"])
            fn = _import_stop_instance()
            result = fn(instance_id)
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False, default=str))]

        elif name == "create_instance":
            fn = _import_create_instance()
            labels = arguments.get("labels")
            labels_json = json.dumps(labels) if labels else None
            result = fn(
                name=arguments["name"],
                image_id=arguments["image"],
                instance_type=arguments["instance_type"],
                labels=labels_json,
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False, default=str))]

        elif name == "list_images":
            fn = _import_list_images()
            image_type = arguments.get("image_type", "all")
            images = fn(image_type=image_type)
            # Trim to essential fields for token efficiency
            brief = []
            for img in (images or []):
                brief.append(filter_response(img, ['ImageId', 'ImageName', 'Framework', 'AcceleratorType']))
            return [TextContent(type="text", text=json.dumps(brief, indent=2, ensure_ascii=False, default=str))]

        elif name == "list_specs":
            fn = _import_list_ecs_specs()
            gpu_only = arguments.get("gpu_only", False)
            specs = fn(gpu_only=gpu_only)
            return [TextContent(type="text", text=json.dumps(specs, indent=2, ensure_ascii=False, default=str))]

        elif name == "get_instance_metrics":
            instance_id = _resolve(arguments["instance"])
            fn = _import_get_metrics()
            metric_type = arguments.get("metric_type", "all")
            result = fn(instance_id, metric_type=metric_type)
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False, default=str))]

        else:
            return [TextContent(type="text", text=json.dumps({"error": "UNKNOWN_TOOL", "message": f"未知工具: {name}"}))]

    except DSWError as e:
        return [TextContent(type="text", text=json.dumps(e.to_dict(), ensure_ascii=False))]
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": "INTERNAL_ERROR", "message": str(e)}, ensure_ascii=False))]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def _main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    import asyncio
    asyncio.run(_main())


if __name__ == "__main__":
    main()
