#!/usr/bin/env python3
"""
List available ECS specifications for PAI-DSW instances.

Usage:
    python list_ecs_specs.py [options]

Options:
    --region <region>       Region ID (default: from environment)
    --gpu                   Show only GPU specs
    --cpu                   Show only CPU specs
    --format <format>       Output format: table, json (default: table)
    --help                  Show this help message

Examples:
    # List all specs
    python list_ecs_specs.py

    # List GPU specs only
    python list_ecs_specs.py --gpu

    # JSON output
    python list_ecs_specs.py --format json
"""

import os
import sys
import json
import argparse

# Add script directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from dsw_utils import create_client
from alibabacloud_pai_dsw20220101 import models as dsw_models


def list_ecs_specs(region_id: str = None, gpu_only: bool = False, cpu_only: bool = False) -> list:
    """
    List available ECS specifications.
    
    Args:
        region_id: Region ID
        gpu_only: Show only GPU specs
        cpu_only: Show only CPU specs
    
    Returns:
        List of ECS specifications
    """
    client = create_client(region_id)
    
    specs = []
    
    # Query CPU specs
    if not gpu_only:
        try:
            request = dsw_models.ListEcsSpecsRequest()
            request.accelerator_type = 'CPU'
            response = client.list_ecs_specs(request)
            if response.body and response.body.ecs_specs:
                for spec in response.body.ecs_specs:
                    specs.append({
                        'ecs_spec': getattr(spec, 'instance_type', 'N/A'),
                        'cpu': getattr(spec, 'cpu', 0),
                        'memory': getattr(spec, 'memory', 0),
                        'gpu_count': getattr(spec, 'gpu', 0),
                        'gpu_type': getattr(spec, 'gpu_type', None),
                        'gpu_memory': getattr(spec, 'gpu_memory_size', 0),
                        'price': getattr(spec, 'price', 0),
                        'is_available': getattr(spec, 'is_available', False),
                        'spot_status': getattr(spec, 'spot_stock_status', 'Unknown'),
                    })
        except Exception as e:
            print(f"⚠️ CPU specs query failed: {e}", file=sys.stderr)
    
    # Query GPU specs
    if not cpu_only:
        try:
            request = dsw_models.ListEcsSpecsRequest()
            request.accelerator_type = 'GPU'
            response = client.list_ecs_specs(request)
            if response.body and response.body.ecs_specs:
                for spec in response.body.ecs_specs:
                    specs.append({
                        'ecs_spec': getattr(spec, 'instance_type', 'N/A'),
                        'cpu': getattr(spec, 'cpu', 0),
                        'memory': getattr(spec, 'memory', 0),
                        'gpu_count': getattr(spec, 'gpu', 0),
                        'gpu_type': getattr(spec, 'gpu_type', None),
                        'gpu_memory': getattr(spec, 'gpu_memory_size', 0),
                        'price': getattr(spec, 'price', 0),
                        'is_available': getattr(spec, 'is_available', False),
                        'spot_status': getattr(spec, 'spot_stock_status', 'Unknown'),
                    })
        except Exception as e:
            print(f"⚠️ GPU specs query failed: {e}", file=sys.stderr)
    
    return specs


def format_table(specs: list) -> str:
    """Format specs as a table."""
    if not specs:
        return "No specifications found."
    
    # Determine column widths
    spec_width = max(len(s['ecs_spec']) for s in specs)
    cpu_width = 6
    mem_width = 8
    gpu_width = 5
    gpu_type_width = max(len(s['gpu_type'] or '-') for s in specs)
    gpu_type_width = max(gpu_type_width, 14)
    price_width = 8
    
    # Header
    header = f"{'ECS Spec':<{spec_width}} {'CPU':>{cpu_width}} {'Memory':>{mem_width}} {'GPU':>{gpu_width}} {'GPU Type':<{gpu_type_width}} {'Price/h':>{price_width}}"
    separator = '-' * len(header)
    
    lines = [separator, header, separator]
    
    # Sort by GPU count then CPU
    sorted_specs = sorted(specs, key=lambda x: (-x['gpu_count'], -x['cpu']))
    
    for spec in sorted_specs:
        gpu_type = spec['gpu_type'] or '-'
        price = f"¥{spec['price']:.2f}" if spec['price'] else '-'
        line = f"{spec['ecs_spec']:<{spec_width}} {spec['cpu']:>{cpu_width}} {spec['memory']:>{mem_width}}GB {spec['gpu_count']:>{gpu_width}} {gpu_type:<{gpu_type_width}} {price:>{price_width}}"
        lines.append(line)
    
    lines.append(separator)
    lines.append(f"Total: {len(specs)} specifications")
    
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='List available ECS specifications for PAI-DSW')
    parser.add_argument('--region', default=os.getenv('ALIBABA_CLOUD_REGION_ID'),
                        help='Region ID')
    parser.add_argument('--gpu', action='store_true', help='Show only GPU specs')
    parser.add_argument('--cpu', action='store_true', help='Show only CPU specs')
    parser.add_argument('--format', choices=['table', 'json'], default='table',
                        help='Output format')
    
    args = parser.parse_args()
    
    if args.gpu and args.cpu:
        print("❌ Cannot use --gpu and --cpu together", file=sys.stderr)
        sys.exit(1)
    
    try:
        specs = list_ecs_specs(
            region_id=args.region,
            gpu_only=args.gpu,
            cpu_only=args.cpu
        )
        
        if args.format == 'json':
            print(json.dumps(specs, indent=2, ensure_ascii=False))
        else:
            print(f"\n{'='*90}")
            print("  PAI-DSW Available ECS Specifications")
            print(f"{'='*90}\n")
            
            if args.gpu:
                print("  (GPU specs only)")
            elif args.cpu:
                print("  (CPU specs only)")
            
            print()
            print(format_table(specs))
            print()
            
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()