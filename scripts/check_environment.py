#!/usr/bin/env python3
"""
DSW 实例环境检测工具
检测当前实例的硬件、软件环境
"""

import os
import sys
import subprocess
import platform
from typing import Dict, List, Any


def run_command(cmd: str) -> str:
    """运行命令并返回输出"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        return result.stdout.strip()
    except:
        return "N/A"


def check_gpu() -> Dict[str, Any]:
    """检测 GPU 信息"""
    gpu_info = {
        'available': False,
        'count': 0,
        'devices': []
    }
    
    # 检查 nvidia-smi
    result = run_command('nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader')
    
    if result and result != "N/A" and "command not found" not in result.lower():
        gpu_info['available'] = True
        lines = result.split('\n')
        gpu_info['count'] = len(lines)
        
        for line in lines:
            if line.strip():
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 3:
                    gpu_info['devices'].append({
                        'name': parts[0],
                        'memory': parts[1],
                        'driver': parts[2]
                    })
    
    # CUDA 版本
    cuda_version = run_command('nvcc --version | grep release')
    if cuda_version:
        import re
        match = re.search(r'release (\d+\.\d+)', cuda_version)
        if match:
            gpu_info['cuda_version'] = match.group(1)
    
    return gpu_info


def check_memory() -> Dict[str, Any]:
    """检测内存信息"""
    mem_info = {}
    
    # 读取 /proc/meminfo
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                parts = line.split(':')
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    mem_info[key] = value
    except:
        pass
    
    total_kb = int(mem_info.get('MemTotal', '0').split()[0])
    available_kb = int(mem_info.get('MemAvailable', '0').split()[0])
    
    return {
        'total_gb': round(total_kb / 1024 / 1024, 1),
        'available_gb': round(available_kb / 1024 / 1024, 1),
        'used_percent': round((1 - available_kb / total_kb) * 100, 1) if total_kb > 0 else 0
    }


def check_disk() -> Dict[str, Any]:
    """检测磁盘信息"""
    disks = []
    
    result = run_command('df -h | grep -E "^/dev"')
    
    if result:
        lines = result.split('\n')
        for line in lines:
            parts = line.split()
            if len(parts) >= 6:
                disks.append({
                    'device': parts[0],
                    'size': parts[1],
                    'used': parts[2],
                    'available': parts[3],
                    'use_percent': parts[4],
                    'mount': parts[5]
                })
    
    return disks


def check_python() -> Dict[str, Any]:
    """检测 Python 环境"""
    py_info = {
        'version': platform.python_version(),
        'implementation': platform.python_implementation(),
        'packages': {}
    }
    
    # 检测常用的深度学习包
    packages = [
        ('torch', 'PyTorch'),
        ('tensorflow', 'TensorFlow'),
        ('numpy', 'NumPy'),
        ('pandas', 'Pandas'),
        ('scipy', 'SciPy'),
        ('sklearn', 'Scikit-learn'),
        ('transformers', 'Transformers'),
        ('accelerate', 'Accelerate'),
        ('diffusers', 'Diffusers'),
        ('xgboost', 'XGBoost'),
        ('lightgbm', 'LightGBM'),
        ('cv2', 'OpenCV'),
        ('PIL', 'Pillow'),
        ('matplotlib', 'Matplotlib'),
    ]
    
    for module, name in packages:
        try:
            mod = __import__(module)
            version = getattr(mod, '__version__', 'unknown')
            py_info['packages'][name] = version
        except ImportError:
            pass
    
    return py_info


def check_network() -> Dict[str, Any]:
    """检测网络信息"""
    network = {
        'hostname': run_command('hostname'),
        'ip_addresses': []
    }
    
    # 获取 IP 地址
    result = run_command("ip addr show | grep 'inet ' | awk '{print $2}' | cut -d'/' -f1")
    if result:
        network['ip_addresses'] = result.split('\n')
    
    # 检查外网连接
    ping_result = run_command('ping -c 1 -W 2 8.8.8.8')
    network['internet'] = '1 received' in ping_result or 'bytes from' in ping_result
    
    return network


def check_environment_variables() -> Dict[str, str]:
    """检测关键环境变量"""
    env_vars = {}
    
    important_vars = [
        'PAI_WORKSPACE_ID',
        'ALIBABA_CLOUD_REGION_ID',
        'ALIBABA_CLOUD_ACCESS_KEY_ID',
        'HOSTNAME',
        'HOME',
        'PATH',
        'CUDA_HOME',
        'LD_LIBRARY_PATH',
        'PYTHONPATH',
    ]
    
    for var in important_vars:
        value = os.getenv(var, '')
        if value:
            # 敏感信息脱敏
            if 'KEY' in var or 'SECRET' in var:
                value = value[:8] + '***' if len(value) > 8 else '***'
            env_vars[var] = value
    
    return env_vars


def print_environment_report():
    """打印环境报告"""
    print("\n" + "="*60)
    print("📊 DSW 实例环境检测报告")
    print("="*60)
    
    # 基本信息
    print("\n🖥️  系统信息")
    print("-"*40)
    print(f"  主机名: {platform.node()}")
    print(f"  系统: {platform.system()} {platform.release()}")
    print(f"  架构: {platform.machine()}")
    print(f"  Python: {platform.python_version()}")
    
    # CPU
    print("\n🔧 CPU 信息")
    print("-"*40)
    cpu_count = os.cpu_count()
    print(f"  核心数: {cpu_count}")
    cpu_model = run_command("lscpu | grep 'Model name' | cut -d':' -f2").strip()
    if cpu_model:
        print(f"  型号: {cpu_model}")
    
    # 内存
    print("\n💾 内存信息")
    print("-"*40)
    mem = check_memory()
    print(f"  总内存: {mem['total_gb']} GB")
    print(f"  可用内存: {mem['available_gb']} GB")
    print(f"  使用率: {mem['used_percent']}%")
    
    # 磁盘
    print("\n💿 磁盘信息")
    print("-"*40)
    disks = check_disk()
    for disk in disks:
        print(f"  {disk['mount']}: {disk['size']} (已用 {disk['use_percent']})")
    
    # GPU
    print("\n🎮 GPU 信息")
    print("-"*40)
    gpu = check_gpu()
    if gpu['available']:
        print(f"  可用: ✅")
        print(f"  数量: {gpu['count']}")
        for i, dev in enumerate(gpu['devices']):
            print(f"  GPU {i}: {dev['name']}")
            print(f"         显存: {dev['memory']}")
            print(f"         驱动: {dev['driver']}")
        if gpu.get('cuda_version'):
            print(f"  CUDA: {gpu['cuda_version']}")
    else:
        print(f"  可用: ❌ 无 GPU")
    
    # Python 包
    print("\n📦 Python 包")
    print("-"*40)
    py = check_python()
    if py['packages']:
        for name, version in py['packages'].items():
            print(f"  {name}: {version}")
    else:
        print("  未检测到常用数据科学包")
    
    # 网络
    print("\n🌐 网络信息")
    print("-"*40)
    net = check_network()
    print(f"  主机名: {net['hostname']}")
    if net['ip_addresses']:
        print(f"  IP地址: {', '.join(net['ip_addresses'])}")
    print(f"  外网连接: {'✅ 正常' if net['internet'] else '❌ 无法连接'}")
    
    # 环境变量
    print("\n📝 关键环境变量")
    print("-"*40)
    env = check_environment_variables()
    for key, value in env.items():
        print(f"  {key}: {value}")
    
    print("\n" + "="*60)
    print("✅ 检测完成")
    print("="*60 + "\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='DSW 实例环境检测')
    parser.add_argument('--json', action='store_true', help='JSON 格式输出')
    
    args = parser.parse_args()
    
    if args.json:
        result = {
            'system': {
                'hostname': platform.node(),
                'system': platform.system(),
                'release': platform.release(),
                'machine': platform.machine(),
                'python_version': platform.python_version(),
            },
            'cpu': {
                'count': os.cpu_count()
            },
            'memory': check_memory(),
            'disk': check_disk(),
            'gpu': check_gpu(),
            'python': check_python(),
            'network': check_network(),
            'environment': check_environment_variables()
        }
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        print_environment_report()


if __name__ == '__main__':
    main()