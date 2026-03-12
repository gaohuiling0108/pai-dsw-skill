#!/usr/bin/env python3
"""
MCP Server for PAI-DSW Skill.

Provides DSW instance management capabilities via MCP protocol.
"""

import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from dsw_utils import create_client, get_workspace_id, get_region_id
from alibabacloud_pai_dsw20220101 import models as dsw_models

# Create MCP server
server = Server("pai-dsw-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="list_instances",
            description="List all DSW instances in the workspace",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_instance",
            description="Get details of a specific DSW instance",
            inputSchema={
                "type": "object",
                "properties": {
                    "instance_id": {"type": "string", "description": "Instance ID"}
                },
                "required": ["instance_id"]
            }
        ),
        Tool(
            name="start_instance",
            description="Start a stopped DSW instance",
            inputSchema={
                "type": "object",
                "properties": {
                    "instance_id": {"type": "string", "description": "Instance ID"}
                },
                "required": ["instance_id"]
            }
        ),
        Tool(
            name="stop_instance",
            description="Stop a running DSW instance",
            inputSchema={
                "type": "object",
                "properties": {
                    "instance_id": {"type": "string", "description": "Instance ID"}
                },
                "required": ["instance_id"]
            }
        ),
        Tool(
            name="get_gpu_usage",
            description="Get GPU usage for all GPU instances",
            inputSchema={
                "type": "object",
                "properties": {
                    "threshold": {"type": "number", "description": "Alert threshold (default 80)"}
                }
            }
        ),
        Tool(
            name="list_specs",
            description="List available ECS specifications",
            inputSchema={
                "type": "object",
                "properties": {
                    "gpu_only": {"type": "boolean", "description": "Show only GPU specs"}
                }
            }
        ),
        Tool(
            name="list_images",
            description="List available DSW images",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_instance_metrics",
            description="Get resource metrics for an instance",
            inputSchema={
                "type": "object",
                "properties": {
                    "instance_id": {"type": "string", "description": "Instance ID"}
                },
                "required": ["instance_id"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    
    try:
        if name == "list_instances":
            return await _list_instances()
        elif name == "get_instance":
            return await _get_instance(arguments["instance_id"])
        elif name == "start_instance":
            return await _start_instance(arguments["instance_id"])
        elif name == "stop_instance":
            return await _stop_instance(arguments["instance_id"])
        elif name == "get_gpu_usage":
            threshold = arguments.get("threshold", 80)
            return await _get_gpu_usage(threshold)
        elif name == "list_specs":
            gpu_only = arguments.get("gpu_only", False)
            return await _list_specs(gpu_only)
        elif name == "list_images":
            return await _list_images()
        elif name == "get_instance_metrics":
            return await _get_instance_metrics(arguments["instance_id"])
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def _list_instances() -> list[TextContent]:
    """List all instances."""
    client = create_client()
    workspace_id = get_workspace_id()
    
    request = dsw_models.ListInstancesRequest()
    request.workspace_id = workspace_id
    
    response = client.list_instances(request)
    
    instances = []
    if response.body and response.body.instances:
        for inst in response.body.instances:
            instances.append({
                "instance_id": inst.instance_id,
                "instance_name": inst.instance_name,
                "status": inst.status,
                "ecs_spec": inst.ecs_spec,
            })
    
    return [TextContent(type="text", text=json.dumps(instances, indent=2))]


async def _get_instance(instance_id: str) -> list[TextContent]:
    """Get instance details."""
    client = create_client()
    
    request = dsw_models.GetInstanceRequest()
    response = client.get_instance(instance_id, request)
    
    if response.body:
        data = {
            "instance_id": response.body.instance_id,
            "instance_name": response.body.instance_name,
            "status": response.body.status,
            "ecs_spec": response.body.ecs_spec,
            "workspace_id": response.body.workspace_id,
        }
        return [TextContent(type="text", text=json.dumps(data, indent=2))]
    
    return [TextContent(type="text", text="Instance not found")]


async def _start_instance(instance_id: str) -> list[TextContent]:
    """Start an instance."""
    client = create_client()
    
    request = dsw_models.StartInstanceRequest()
    response = client.start_instance(instance_id, request)
    
    return [TextContent(type="text", text=f"Instance {instance_id} started")]


async def _stop_instance(instance_id: str) -> list[TextContent]:
    """Stop an instance."""
    client = create_client()
    
    request = dsw_models.StopInstanceRequest()
    response = client.stop_instance(instance_id, request)
    
    return [TextContent(type="text", text=f"Instance {instance_id} stopped")]


async def _get_gpu_usage(threshold: float) -> list[TextContent]:
    """Get GPU usage for all GPU instances."""
    client = create_client()
    workspace_id = get_workspace_id()
    
    # Get all instances
    request = dsw_models.ListInstancesRequest()
    request.workspace_id = workspace_id
    response = client.list_instances(request)
    
    # GPU spec keywords
    gpu_specs = ['gn', 'gn6', 'gn7', 'gn8', 'gn6i', 'gn7i', 'gn8i', 'p3', 'p4']
    
    results = []
    if response.body and response.body.instances:
        for inst in response.body.instances:
            ecs_spec = inst.ecs_spec or ''
            is_gpu = any(spec in ecs_spec.lower() for spec in gpu_specs)
            
            if is_gpu and inst.status == 'Running':
                results.append({
                    "instance_id": inst.instance_id,
                    "instance_name": inst.instance_name,
                    "status": inst.status,
                    "ecs_spec": ecs_spec,
                })
    
    return [TextContent(type="text", text=json.dumps(results, indent=2))]


async def _list_specs(gpu_only: bool) -> list[TextContent]:
    """List ECS specs."""
    client = create_client()
    
    specs = []
    for accel_type in ['CPU', 'GPU']:
        try:
            request = dsw_models.ListEcsSpecsRequest()
            request.accelerator_type = accel_type
            response = client.list_ecs_specs(request)
            
            if response.body and response.body.ecs_specs:
                for spec in response.body.ecs_specs:
                    if gpu_only and accel_type != 'GPU':
                        continue
                    specs.append({
                        "ecs_spec": getattr(spec, 'instance_type', 'N/A'),
                        "cpu": getattr(spec, 'cpu', 0),
                        "memory": getattr(spec, 'memory', 0),
                        "gpu_count": getattr(spec, 'gpu', 0),
                        "gpu_type": getattr(spec, 'gpu_type', None),
                    })
        except Exception:
            pass
    
    return [TextContent(type="text", text=json.dumps(specs, indent=2))]


async def _list_images() -> list[TextContent]:
    """List available images."""
    # Return common images
    images = [
        {"name": "modelscope:1.34.0-pytorch2.9.1-cpu-py311-ubuntu22.04", "type": "CPU"},
        {"name": "modelscope:1.34.0-pytorch2.9.1-gpu-py311-cu124-ubuntu22.04", "type": "GPU"},
        {"name": "pytorch:2.0.0-gpu-cu118", "type": "GPU"},
        {"name": "tensorflow:2.12.0-gpu", "type": "GPU"},
    ]
    return [TextContent(type="text", text=json.dumps(images, indent=2))]


async def _get_instance_metrics(instance_id: str) -> list[TextContent]:
    """Get instance metrics."""
    client = create_client()
    
    request = dsw_models.GetInstanceMetricsRequest()
    request.instance_id = instance_id
    request.metric_type = 'All'
    
    response = client.get_instance_metrics(instance_id, request)
    
    metrics = {}
    if response.body and response.body.metrics:
        for metric in response.body.metrics:
            name = getattr(metric, 'metric_name', 'unknown')
            value = getattr(metric, 'value', 0)
            metrics[name] = value
    
    return [TextContent(type="text", text=json.dumps(metrics, indent=2))]


async def run():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(run())