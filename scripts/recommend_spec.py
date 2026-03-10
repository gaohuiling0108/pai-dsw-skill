#!/usr/bin/env python3
"""
Instance spec recommender for PAI-DSW.

Recommends appropriate instance specs based on workload requirements.

Usage:
    python recommend_spec.py [options]

Options:
    --workload <type>      Workload type: training, inference, dev, data
    --model-size <params>  Model size in billions (e.g., 7, 13, 70)
    --batch-size <size>    Batch size
    --gpu-type <type>      Preferred GPU type: a10, a100, v100
    --region <region>      Region ID
    --help                 Show this help message
"""

import os
import sys
import json
import argparse
from typing import List, Dict, Optional

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from dsw_utils import create_client
from alibabacloud_pai_dsw20220101 import models as dsw_models


# GPU 显存估算规则 (模型参数量 -> 最小显存)
MODEL_GPU_REQUIREMENTS = {
    # (参数量B, 精度) -> 最小显存 GB
    (1, 'fp32'): 8,
    (1, 'fp16'): 4,
    (1, 'int8'): 2,
    (7, 'fp32'): 32,
    (7, 'fp16'): 16,
    (7, 'int8'): 8,
    (7, '4bit'): 4,
    (13, 'fp32'): 56,
    (13, 'fp16'): 28,
    (13, 'int8'): 14,
    (13, '4bit'): 7,
    (30, 'fp32'): 128,
    (30, 'fp16'): 64,
    (30, 'int8'): 32,
    (30, '4bit'): 16,
    (70, 'fp32'): 280,
    (70, 'fp16'): 140,
    (70, 'int8'): 70,
    (70, '4bit'): 35,
}

# GPU 规格信息
GPU_SPECS = {
    'a10': {'memory': 24, 'name': 'NVIDIA A10', 'suitable': ['training', 'inference', 'dev']},
    'a100-40g': {'memory': 40, 'name': 'NVIDIA A100 40GB', 'suitable': ['training', 'inference']},
    'a100-80g': {'memory': 80, 'name': 'NVIDIA A100 80GB', 'suitable': ['training', 'inference']},
    'v100': {'memory': 32, 'name': 'NVIDIA V100', 'suitable': ['training', 'inference']},
    't4': {'memory': 16, 'name': 'NVIDIA T4', 'suitable': ['inference', 'dev']},
}

# 工作负载推荐
WORKLOAD_RECOMMENDATIONS = {
    'training': {
        'description': '模型训练',
        'min_gpu_memory': 16,
        'recommended_gpu': ['a10', 'a100-40g', 'a100-80g'],
        'cpu_gpu_ratio': 4,  # 每个GPU配4核CPU
        'mem_gpu_ratio': 32,  # 每个GPU配32GB内存
    },
    'inference': {
        'description': '模型推理',
        'min_gpu_memory': 8,
        'recommended_gpu': ['t4', 'a10', 'a100-40g'],
        'cpu_gpu_ratio': 2,
        'mem_gpu_ratio': 16,
    },
    'dev': {
        'description': '开发调试',
        'min_gpu_memory': 8,
        'recommended_gpu': ['t4', 'a10'],
        'cpu_gpu_ratio': 4,
        'mem_gpu_ratio': 16,
    },
    'data': {
        'description': '数据处理',
        'min_gpu_memory': 0,  # 不需要GPU
        'recommended_gpu': [],
        'cpu_gpu_ratio': 0,
        'mem_gpu_ratio': 0,
        'cpu_only': True,
    },
}


def get_available_specs(region_id: str = None) -> List[Dict]:
    """Get available ECS specs from API."""
    client = create_client(region_id)
    
    specs = []
    
    for accelerator_type in ['CPU', 'GPU']:
        try:
            request = dsw_models.ListEcsSpecsRequest()
            request.accelerator_type = accelerator_type
            response = client.list_ecs_specs(request)
            
            if response.body and response.body.ecs_specs:
                for spec in response.body.ecs_specs:
                    # Try different possible field names
                    gpu_count = getattr(spec, 'gpu', 0) or getattr(spec, 'gpu_count', 0)
                    gpu_type = getattr(spec, 'gpu_type', None)
                    gpu_memory = getattr(spec, 'gpu_memory_size', 0) or getattr(spec, 'gpu_memory', 0)
                    
                    # Infer GPU memory from spec name if not provided
                    if gpu_count > 0 and gpu_memory == 0:
                        # Known GPU memory by spec prefix
                        spec_name = getattr(spec, 'instance_type', '').lower()
                        if 'gn7i' in spec_name or 'gn7' in spec_name:
                            gpu_memory = 24  # A10
                            if not gpu_type:
                                gpu_type = 'A10'
                        elif 'gn6i' in spec_name:
                            gpu_memory = 16  # T4
                            if not gpu_type:
                                gpu_type = 'T4'
                        elif 'gn6v' in spec_name:
                            gpu_memory = 32  # V100
                            if not gpu_type:
                                gpu_type = 'V100'
                        elif 'gn6e' in spec_name:
                            gpu_memory = 32  # V100
                            if not gpu_type:
                                gpu_type = 'V100'
                    
                    specs.append({
                        'ecs_spec': getattr(spec, 'instance_type', 'N/A'),
                        'cpu': getattr(spec, 'cpu', 0),
                        'memory': getattr(spec, 'memory', 0),
                        'gpu_count': gpu_count,
                        'gpu_type': gpu_type,
                        'gpu_memory': gpu_memory,
                        'price': getattr(spec, 'price', 0),
                        'is_available': getattr(spec, 'is_available', False),
                    })
        except Exception:
            pass
    
    # Fallback: use known specs if API returns empty
    if not specs:
        specs = get_default_specs()
    
    return specs


def get_default_specs() -> List[Dict]:
    """Return default known specs when API is unavailable."""
    return [
        # CPU specs
        {'ecs_spec': 'ecs.g6.large', 'cpu': 2, 'memory': 8, 'gpu_count': 0, 'gpu_type': None, 'gpu_memory': 0, 'price': 0.35, 'is_available': True},
        {'ecs_spec': 'ecs.g6.xlarge', 'cpu': 4, 'memory': 16, 'gpu_count': 0, 'gpu_type': None, 'gpu_memory': 0, 'price': 0.7, 'is_available': True},
        {'ecs_spec': 'ecs.g6.2xlarge', 'cpu': 8, 'memory': 32, 'gpu_count': 0, 'gpu_type': None, 'gpu_memory': 0, 'price': 1.4, 'is_available': True},
        {'ecs_spec': 'ecs.g6.4xlarge', 'cpu': 16, 'memory': 64, 'gpu_count': 0, 'gpu_type': None, 'gpu_memory': 0, 'price': 2.8, 'is_available': True},
        {'ecs_spec': 'ecs.r8i.xlarge', 'cpu': 4, 'memory': 32, 'gpu_count': 0, 'gpu_type': None, 'gpu_memory': 0, 'price': 0.8, 'is_available': True},
        {'ecs_spec': 'ecs.r8i.2xlarge', 'cpu': 8, 'memory': 64, 'gpu_count': 0, 'gpu_type': None, 'gpu_memory': 0, 'price': 1.6, 'is_available': True},
        # GPU specs
        {'ecs_spec': 'ecs.gn6i-c24g1.6xlarge', 'cpu': 24, 'memory': 96, 'gpu_count': 1, 'gpu_type': 'T4', 'gpu_memory': 16, 'price': 6.5, 'is_available': True},
        {'ecs_spec': 'ecs.gn7i-c16g1.4xlarge', 'cpu': 16, 'memory': 64, 'gpu_count': 1, 'gpu_type': 'A10', 'gpu_memory': 24, 'price': 8.5, 'is_available': True},
        {'ecs_spec': 'ecs.gn7-c14g1.4xlarge', 'cpu': 14, 'memory': 56, 'gpu_count': 1, 'gpu_type': 'A10', 'gpu_memory': 24, 'price': 8.0, 'is_available': True},
    ]


def estimate_gpu_memory(model_size: float, precision: str = 'fp16') -> int:
    """
    Estimate GPU memory required for a model.
    
    Args:
        model_size: Model size in billions of parameters
        precision: Precision (fp32, fp16, int8, 4bit)
    
    Returns:
        Required GPU memory in GB
    """
    # Find closest model size
    model_sizes = sorted(set(m[0] for m in MODEL_GPU_REQUIREMENTS.keys()))
    
    closest_size = None
    for size in model_sizes:
        if model_size <= size:
            closest_size = size
            break
    
    if closest_size is None:
        closest_size = model_sizes[-1]  # Largest known
    
    # Get memory requirement
    key = (closest_size, precision)
    if key in MODEL_GPU_REQUIREMENTS:
        return MODEL_GPU_REQUIREMENTS[key]
    
    # Fallback: rough estimate
    bytes_per_param = {'fp32': 4, 'fp16': 2, 'int8': 1, '4bit': 0.5}
    params_bytes = model_size * 1e9 * bytes_per_param.get(precision, 2)
    return int(params_bytes / 1e9 * 1.2)  # 20% overhead


def recommend_spec(
    workload: str = 'dev',
    model_size: float = None,
    batch_size: int = 1,
    gpu_type: str = None,
    region_id: str = None,
) -> Dict:
    """
    Recommend instance spec based on requirements.
    
    Args:
        workload: Workload type
        model_size: Model size in billions
        batch_size: Batch size
        gpu_type: Preferred GPU type
        region_id: Region ID
    
    Returns:
        Recommendation dictionary
    """
    result = {
        'workload': workload,
        'model_size': model_size,
        'batch_size': batch_size,
        'recommendations': [],
        'reasoning': [],
    }
    
    # Get workload requirements
    workload_req = WORKLOAD_RECOMMENDATIONS.get(workload, WORKLOAD_RECOMMENDATIONS['dev'])
    result['workload_description'] = workload_req['description']
    
    # Get available specs
    available_specs = get_available_specs(region_id)
    
    if workload_req.get('cpu_only'):
        # CPU-only workload
        result['reasoning'].append("数据处理工作负载不需要 GPU")
        
        cpu_specs = [s for s in available_specs if s['gpu_count'] == 0]
        
        # Recommend based on memory
        if model_size:  # Data size in GB
            required_mem = model_size * 2  # 2x data size
            suitable = [s for s in cpu_specs if s['memory'] >= required_mem]
        else:
            suitable = cpu_specs
        
        for spec in sorted(suitable, key=lambda x: x['price'])[:5]:
            result['recommendations'].append({
                'spec': spec['ecs_spec'],
                'cpu': spec['cpu'],
                'memory': spec['memory'],
                'gpu': 0,
                'price': spec['price'],
                'reason': 'CPU 实例，适合数据处理',
            })
    
    else:
        # GPU workload
        required_gpu_memory = workload_req['min_gpu_memory']
        
        if model_size:
            estimated = estimate_gpu_memory(model_size, 'fp16')
            required_gpu_memory = max(required_gpu_memory, estimated * batch_size)
            result['reasoning'].append(
                f"模型 {model_size}B 参数 + batch {batch_size} 估计需要 {required_gpu_memory}GB GPU 显存"
            )
        
        # Filter GPU specs
        gpu_specs = [s for s in available_specs if s['gpu_count'] > 0]
        
        # Filter by GPU memory
        suitable = [s for s in gpu_specs if s['gpu_memory'] * s['gpu_count'] >= required_gpu_memory]
        
        # Sort by price
        for spec in sorted(suitable, key=lambda x: x['price'])[:5]:
            total_gpu_mem = spec['gpu_memory'] * spec['gpu_count']
            result['recommendations'].append({
                'spec': spec['ecs_spec'],
                'cpu': spec['cpu'],
                'memory': spec['memory'],
                'gpu': spec['gpu_count'],
                'gpu_type': spec['gpu_type'],
                'gpu_memory': spec['gpu_memory'],
                'total_gpu_memory': total_gpu_mem,
                'price': spec['price'],
                'reason': f"GPU 显存 {total_gpu_mem}GB >= {required_gpu_memory}GB 需求",
            })
    
    if not result['recommendations']:
        result['reasoning'].append("⚠️ 未找到满足需求的规格，请考虑降低要求或联系管理员")
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description='Recommend PAI-DSW instance spec',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 推荐训练用规格
  python recommend_spec.py --workload training --model-size 7

  # 推荐推理用规格
  python recommend_spec.py --workload inference --model-size 13 --batch-size 4

  # 推荐开发调试规格
  python recommend_spec.py --workload dev

  # 推荐数据处理规格
  python recommend_spec.py --workload data --model-size 100  # 100GB 数据

工作负载类型:
  training   - 模型训练，需要大量 GPU 显存
  inference  - 模型推理，中等 GPU 需求
  dev        - 开发调试，低 GPU 需求
  data       - 数据处理，不需要 GPU
"""
    )
    parser.add_argument('--workload', choices=['training', 'inference', 'dev', 'data'],
                        default='dev', help='Workload type')
    parser.add_argument('--model-size', type=float, help='Model size in B params / Data size in GB')
    parser.add_argument('--batch-size', type=int, default=1, help='Batch size')
    parser.add_argument('--gpu-type', help='Preferred GPU type')
    parser.add_argument('--region', help='Region ID')
    parser.add_argument('--json', action='store_true', help='JSON output')
    
    args = parser.parse_args()
    
    try:
        result = recommend_spec(
            workload=args.workload,
            model_size=args.model_size,
            batch_size=args.batch_size,
            gpu_type=args.gpu_type,
            region_id=args.region,
        )
        
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"\n{'='*70}")
            print(f"  PAI-DSW 实例规格推荐")
            print(f"{'='*70}")
            
            print(f"\n  工作负载: {result['workload']} ({result['workload_description']})")
            if args.model_size:
                if args.workload == 'data':
                    print(f"  数据大小: {args.model_size}GB")
                else:
                    print(f"  模型大小: {args.model_size}B 参数")
            if args.batch_size > 1:
                print(f"  Batch Size: {args.batch_size}")
            
            print(f"\n  分析过程:")
            for reason in result['reasoning']:
                print(f"    • {reason}")
            
            if result['recommendations']:
                print(f"\n  推荐规格 (按价格排序):")
                for i, rec in enumerate(result['recommendations'], 1):
                    print(f"\n    {i}. {rec['spec']}")
                    print(f"       CPU: {rec['cpu']} 核 | 内存: {rec['memory']}GB", end='')
                    if rec['gpu'] > 0:
                        print(f" | GPU: {rec['gpu']}x {rec['gpu_type']} ({rec['total_gpu_memory']}GB)")
                    else:
                        print()
                    if rec.get('price'):
                        print(f"       价格: ¥{rec['price']:.2f}/小时")
                    print(f"       原因: {rec['reason']}")
            else:
                print(f"\n  ⚠️ 未找到合适的规格")
            
            print(f"\n{'='*70}\n")
            
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()