#!/usr/bin/env python3
"""
PAI-DSW 自动扩缩容脚本模板

功能：
1. 监控实例资源使用情况
2. 根据阈值自动升级/降级实例规格
3. 支持冷却时间防止频繁切换
4. 记录操作日志

使用方法：
1. 复制此脚本到工作目录
2. 修改配置参数
3. 设置定时任务（crontab）定期执行

示例 crontab：
# 每 5 分钟检查一次
*/5 * * * * python3 /path/to/auto_scaling.py >> /var/log/dsw_scaling.log 2>&1
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple

# ============================================================
# 配置区域 - 根据实际情况修改
# ============================================================

# 目标实例（ID 或名称）
TARGET_INSTANCE = "my-instance"

# 扩容阈值（资源使用率超过此值触发扩容）
SCALE_UP_THRESHOLD = 80  # %

# 缩容阈值（资源使用率低于此值触发缩容）
SCALE_DOWN_THRESHOLD = 30  # %

# 监控的资源类型
MONITOR_TYPES = ["cpu", "memory"]  # 可选: cpu, memory, gpu

# 冷却时间（避免频繁切换，单位：分钟）
COOLDOWN_MINUTES = 30

# 规格升级路径（按性能排序）
SPEC_LADDER = [
    "ecs.g6.large",      # 2 vCPU, 8GB
    "ecs.g6.xlarge",     # 4 vCPU, 16GB
    "ecs.g6.2xlarge",    # 8 vCPU, 32GB
    "ecs.g6.4xlarge",    # 16 vCPU, 64GB
    "ecs.g6.8xlarge",    # 32 vCPU, 128GB
]

# GPU 规格升级路径（如果需要）
GPU_SPEC_LADDER = [
    "ecs.gn6v-c8g1.4xlarge",   # 1x V100
    "ecs.gn6v-c8g1.8xlarge",   # 2x V100
    "ecs.gn6v-c8g1.16xlarge",  # 4x V100
]

# 状态文件路径（记录上次操作时间）
STATE_FILE = os.path.expanduser("~/.dsw_scaling_state.json")

# 是否启用干运行模式（只打印不执行）
DRY_RUN = True

# 日志文件路径
LOG_FILE = os.path.expanduser("~/.dsw_scaling.log")

# ============================================================
# 核心逻辑
# ============================================================

def log(message: str, level: str = "INFO"):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{level}] {message}"
    print(log_line)
    
    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_line + "\n")
    except Exception as e:
        print(f"无法写入日志文件: {e}")


def run_dsw_command(command: str, args: list, capture: bool = True) -> Tuple[int, str, str]:
    """执行 dsw.py 命令"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dsw_path = os.path.join(script_dir, "..", "scripts", "dsw.py")
    
    cmd = ["python3", dsw_path, command] + args
    result = subprocess.run(cmd, capture_output=capture, text=True)
    
    return result.returncode, result.stdout or "", result.stderr or ""


def get_instance_info(instance: str) -> Optional[Dict]:
    """获取实例信息"""
    code, stdout, stderr = run_dsw_command("get", [instance, "--format", "json"])
    if code == 0:
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            log(f"解析实例信息失败: {stdout}", "ERROR")
    return None


def get_instance_metrics(instance: str, metric_type: str) -> Optional[Dict]:
    """获取实例资源指标"""
    code, stdout, stderr = run_dsw_command("metrics", [instance, "--type", metric_type, "--format", "json"])
    if code == 0:
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            log(f"解析指标数据失败: {stdout}", "ERROR")
    return None


def get_current_spec_index(spec: str, ladder: list) -> int:
    """获取当前规格在升级路径中的索引"""
    try:
        return ladder.index(spec)
    except ValueError:
        return -1


def load_state() -> Dict:
    """加载状态文件"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_state(state: Dict):
    """保存状态文件"""
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        log(f"保存状态文件失败: {e}", "ERROR")


def is_in_cooldown(instance: str) -> bool:
    """检查是否在冷却期内"""
    state = load_state()
    last_action = state.get(instance, {}).get("last_action_time")
    
    if last_action:
        last_time = datetime.fromisoformat(last_action)
        cooldown_end = last_time + timedelta(minutes=COOLDOWN_MINUTES)
        
        if datetime.now() < cooldown_end:
            remaining = (cooldown_end - datetime.now()).seconds // 60
            log(f"实例 {instance} 在冷却期内，剩余 {remaining} 分钟")
            return True
    
    return False


def record_action(instance: str, action: str, from_spec: str, to_spec: str):
    """记录操作"""
    state = load_state()
    state[instance] = {
        "last_action_time": datetime.now().isoformat(),
        "last_action": action,
        "from_spec": from_spec,
        "to_spec": to_spec
    }
    save_state(state)
    log(f"记录操作: {instance} {action} {from_spec} -> {to_spec}")


def calculate_avg_usage(metrics: Dict) -> float:
    """计算平均使用率"""
    if not metrics or "data" not in metrics:
        return 0
    
    data_points = metrics.get("data", [])
    if not data_points:
        return 0
    
    values = [d.get("Value", 0) for d in data_points if "Value" in d]
    if not values:
        return 0
    
    return sum(values) / len(values)


def scale_instance(instance: str, new_spec: str, current_spec: str) -> bool:
    """执行规格变更"""
    if DRY_RUN:
        log(f"[DRY RUN] 将实例 {instance} 从 {current_spec} 变更为 {new_spec}", "WARN")
        return True
    
    log(f"执行规格变更: {instance} {current_spec} -> {new_spec}")
    
    code, stdout, stderr = run_dsw_command("update", [instance, "--spec", new_spec])
    
    if code == 0:
        log(f"规格变更成功: {instance}", "SUCCESS")
        return True
    else:
        log(f"规格变更失败: {stderr}", "ERROR")
        return False


def check_and_scale(instance: str):
    """检查资源使用情况并决定是否扩缩容"""
    log(f"检查实例: {instance}")
    
    # 检查冷却期
    if is_in_cooldown(instance):
        return
    
    # 获取实例信息
    instance_info = get_instance_info(instance)
    if not instance_info:
        log(f"无法获取实例 {instance} 的信息", "ERROR")
        return
    
    current_spec = instance_info.get("InstanceType", "")
    status = instance_info.get("Status", "")
    
    if status != "Running":
        log(f"实例 {instance} 状态为 {status}，跳过检查")
        return
    
    # 确定使用哪个规格升级路径
    if "gpu" in current_spec.lower() or "gn" in current_spec.lower():
        spec_ladder = GPU_SPEC_LADDER
    else:
        spec_ladder = SPEC_LADDER
    
    current_index = get_current_spec_index(current_spec, spec_ladder)
    if current_index == -1:
        log(f"当前规格 {current_spec} 不在升级路径中", "WARN")
        return
    
    # 获取资源使用率
    usages = {}
    for metric_type in MONITOR_TYPES:
        metrics = get_instance_metrics(instance, metric_type)
        avg_usage = calculate_avg_usage(metrics)
        usages[metric_type] = avg_usage
        log(f"  {metric_type} 平均使用率: {avg_usage:.1f}%")
    
    # 取所有资源中的最大使用率
    max_usage = max(usages.values()) if usages else 0
    min_usage = min(usages.values()) if usages else 0
    
    # 决策逻辑
    if max_usage >= SCALE_UP_THRESHOLD:
        # 需要扩容
        if current_index < len(spec_ladder) - 1:
            new_spec = spec_ladder[current_index + 1]
            log(f"资源使用率 {max_usage:.1f}% 超过阈值 {SCALE_UP_THRESHOLD}%，触发扩容")
            
            if scale_instance(instance, new_spec, current_spec):
                record_action(instance, "scale_up", current_spec, new_spec)
        else:
            log(f"已达到最高规格，无法继续扩容", "WARN")
    
    elif min_usage <= SCALE_DOWN_THRESHOLD:
        # 需要缩容
        if current_index > 0:
            new_spec = spec_ladder[current_index - 1]
            log(f"资源使用率 {min_usage:.1f}% 低于阈值 {SCALE_DOWN_THRESHOLD}%，触发缩容")
            
            if scale_instance(instance, new_spec, current_spec):
                record_action(instance, "scale_down", current_spec, new_spec)
        else:
            log(f"已达到最低规格，无法继续缩容")
    
    else:
        log(f"资源使用率正常，无需调整")


def main():
    """主函数"""
    log("=" * 50)
    log("PAI-DSW 自动扩缩容检查开始")
    log("=" * 50)
    
    # 支持命令行参数指定实例
    instance = sys.argv[1] if len(sys.argv) > 1 else TARGET_INSTANCE
    
    check_and_scale(instance)
    
    log("检查完成")


if __name__ == "__main__":
    main()