#!/usr/bin/env python3
"""
DSW 实例诊断工具
诊断常见问题并提供解决建议
"""

import os
import sys
import subprocess
import json
from typing import List, Dict, Tuple

# 颜色定义
class Colors:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'


def run_command(cmd: str) -> Tuple[bool, str]:
    """运行命令返回成功状态和输出"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        return result.returncode == 0, result.stdout.strip() + result.stderr.strip()
    except Exception as e:
        return False, str(e)


def check_disk_space() -> Dict:
    """检查磁盘空间"""
    issues = []
    
    success, output = run_command("df -h | grep -E '^/dev'")
    if success:
        lines = output.split('\n')
        for line in lines:
            parts = line.split()
            if len(parts) >= 6:
                mount = parts[5]
                use_percent = int(parts[4].replace('%', ''))
                
                if use_percent > 90:
                    issues.append({
                        'level': 'critical',
                        'message': f'{mount} 磁盘使用率 {use_percent}%，空间不足！',
                        'suggestion': '清理不需要的文件，或联系管理员扩容'
                    })
                elif use_percent > 80:
                    issues.append({
                        'level': 'warning',
                        'message': f'{mount} 磁盘使用率 {use_percent}%，空间紧张',
                        'suggestion': '建议清理临时文件'
                    })
    
    return {'name': '磁盘空间', 'issues': issues}


def check_memory() -> Dict:
    """检查内存"""
    issues = []
    
    try:
        with open('/proc/meminfo', 'r') as f:
            content = f.read()
        
        total = 0
        available = 0
        
        for line in content.split('\n'):
            if line.startswith('MemTotal:'):
                total = int(line.split()[1])
            elif line.startswith('MemAvailable:'):
                available = int(line.split()[1])
        
        if total > 0:
            used_percent = (1 - available / total) * 100
            
            if used_percent > 95:
                issues.append({
                    'level': 'critical',
                    'message': f'内存使用率 {used_percent:.1f}%，严重不足！',
                    'suggestion': '检查内存泄漏，重启不必要的进程'
                })
            elif used_percent > 85:
                issues.append({
                    'level': 'warning',
                    'message': f'内存使用率 {used_percent:.1f}%，较为紧张',
                    'suggestion': '注意内存使用，避免大内存任务'
                })
    except:
        pass
    
    return {'name': '内存使用', 'issues': issues}


def check_gpu() -> Dict:
    """检查 GPU 状态"""
    issues = []
    
    success, output = run_command('nvidia-smi')
    
    if not success:
        # 没有检测到 GPU，不一定是问题
        return {'name': 'GPU 状态', 'issues': []}
    
    # 检查 GPU 内存使用
    success, output = run_command('nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits')
    
    if success:
        lines = output.strip().split('\n')
        for i, line in enumerate(lines):
            parts = line.split(',')
            if len(parts) == 2:
                used = int(parts[0].strip())
                total = int(parts[1].strip())
                percent = (used / total) * 100
                
                if percent > 95:
                    issues.append({
                        'level': 'warning',
                        'message': f'GPU {i} 显存使用率 {percent:.1f}%',
                        'suggestion': '清理 GPU 显存，检查是否有残留进程'
                    })
    
    # 检查 GPU 进程
    success, output = run_command('nvidia-smi --query-compute-apps=pid --format=csv,noheader')
    if success and output.strip():
        pids = [p.strip() for p in output.strip().split('\n') if p.strip()]
        if len(pids) > 10:
            issues.append({
                'level': 'info',
                'message': f'GPU 上有 {len(pids)} 个进程运行中',
                'suggestion': '如有异常进程，可使用 nvidia-smi 查看'
            })
    
    return {'name': 'GPU 状态', 'issues': issues}


def check_network() -> Dict:
    """检查网络连接"""
    issues = []
    
    # 检查外网连接
    success, _ = run_command('ping -c 1 -W 2 8.8.8.8')
    
    if not success:
        issues.append({
            'level': 'warning',
            'message': '无法连接外网',
            'suggestion': '检查网络配置或联系管理员'
        })
    
    # 检查 DNS
    success, _ = run_command('nslookup aliyun.com')
    
    if not success:
        issues.append({
            'level': 'warning',
            'message': 'DNS 解析可能有问题',
            'suggestion': '检查 /etc/resolv.conf 配置'
        })
    
    return {'name': '网络连接', 'issues': issues}


def check_credentials() -> Dict:
    """检查阿里云凭证"""
    issues = []
    
    # 检查环境变量
    access_key = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID')
    credentials_uri = os.getenv('ALIBABA_CLOUD_CREDENTIALS_URI')
    
    if access_key:
        # 有 AK，检查是否过期
        import requests
        if credentials_uri:
            try:
                resp = requests.get(credentials_uri, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('Code') != 'Success':
                        issues.append({
                            'level': 'critical',
                            'message': 'RAM 角色凭证获取失败',
                            'suggestion': '检查实例 RAM 角色配置'
                        })
            except Exception as e:
                issues.append({
                    'level': 'warning',
                    'message': f'凭证服务连接失败: {str(e)[:50]}',
                    'suggestion': '可能是临时网络问题'
                })
    
    return {'name': '阿里云凭证', 'issues': issues}


def check_python_env() -> Dict:
    """检查 Python 环境"""
    issues = []
    
    # 检查 pip 是否可用
    success, output = run_command('pip --version')
    if not success:
        issues.append({
            'level': 'warning',
            'message': 'pip 不可用',
            'suggestion': '安装 pip: python -m ensurepip'
        })
    
    # 检查常见包冲突
    success, output = run_command('pip check 2>&1')
    if success and output and 'no broken' not in output.lower():
        # 有包冲突
        conflicts = [line for line in output.split('\n') if line.strip()]
        if len(conflicts) > 3:
            issues.append({
                'level': 'warning',
                'message': f'检测到 {len(conflicts)} 个包依赖冲突',
                'suggestion': '运行 pip check 查看详情，建议重建虚拟环境'
            })
    
    return {'name': 'Python 环境', 'issues': issues}


def check_processes() -> Dict:
    """检查异常进程"""
    issues = []
    
    # 检查僵尸进程
    success, output = run_command('ps aux | awk \'{if($8=="Z") print}\' | wc -l')
    if success:
        try:
            zombie_count = int(output.strip())
            if zombie_count > 5:
                issues.append({
                    'level': 'warning',
                    'message': f'检测到 {zombie_count} 个僵尸进程',
                    'suggestion': '僵尸进程通常无害，但过多可能表明进程管理问题'
                })
        except:
            pass
    
    # 检查高 CPU 进程
    success, output = run_command('ps aux --sort=-%cpu | head -5')
    # 这里只做信息提示，不报警
    
    return {'name': '进程状态', 'issues': issues}


def run_diagnostics():
    """运行所有诊断"""
    checks = [
        check_disk_space,
        check_memory,
        check_gpu,
        check_network,
        check_credentials,
        check_python_env,
        check_processes,
    ]
    
    results = []
    for check in checks:
        results.append(check())
    
    return results


def print_diagnostics_report():
    """打印诊断报告"""
    print("\n" + "="*60)
    print(f"{Colors.BOLD}🔍 DSW 实例诊断报告{Colors.RESET}")
    print("="*60)
    
    results = run_diagnostics()
    
    total_issues = 0
    critical_count = 0
    warning_count = 0
    
    for result in results:
        name = result['name']
        issues = result['issues']
        
        if issues:
            total_issues += len(issues)
            for issue in issues:
                if issue['level'] == 'critical':
                    critical_count += 1
                elif issue['level'] == 'warning':
                    warning_count += 1
    
    # 汇总
    print(f"\n📊 诊断汇总")
    print("-"*40)
    if total_issues == 0:
        print(f"{Colors.GREEN}✅ 未发现问题{Colors.RESET}")
    else:
        if critical_count > 0:
            print(f"{Colors.RED}🔴 严重问题: {critical_count} 个{Colors.RESET}")
        if warning_count > 0:
            print(f"{Colors.YELLOW}🟡 警告: {warning_count} 个{Colors.RESET}")
        
        print(f"\n详细信息:")
        
        for result in results:
            name = result['name']
            issues = result['issues']
            
            if issues:
                print(f"\n{Colors.CYAN}▶ {name}{Colors.RESET}")
                for issue in issues:
                    level = issue['level']
                    message = issue['message']
                    suggestion = issue['suggestion']
                    
                    if level == 'critical':
                        icon = f"{Colors.RED}🔴{Colors.RESET}"
                    elif level == 'warning':
                        icon = f"{Colors.YELLOW}🟡{Colors.RESET}"
                    else:
                        icon = f"{Colors.BLUE}ℹ️{Colors.RESET}"
                    
                    print(f"  {icon} {message}")
                    print(f"     💡 {suggestion}")
    
    print("\n" + "="*60)
    
    if critical_count > 0:
        print(f"{Colors.RED}⚠️  发现严重问题，建议尽快处理！{Colors.RESET}")
    elif warning_count > 0:
        print(f"{Colors.YELLOW}💡 建议处理上述警告项{Colors.RESET}")
    else:
        print(f"{Colors.GREEN}✅ 系统状态良好{Colors.RESET}")
    
    print("="*60 + "\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='DSW 实例诊断')
    parser.add_argument('--json', action='store_true', help='JSON 格式输出')
    
    args = parser.parse_args()
    
    if args.json:
        results = run_diagnostics()
        output = []
        for result in results:
            if result['issues']:
                output.append(result)
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print_diagnostics_report()


if __name__ == '__main__':
    main()