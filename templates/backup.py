#!/usr/bin/env python3
"""
PAI-DSW 定时备份脚本模板

功能：
1. 定期为指定实例创建快照
2. 支持备份保留策略（自动清理旧备份）
3. 支持多个实例批量备份
4. 详细的备份日志记录

使用方法：
1. 复制此脚本到工作目录
2. 修改配置参数
3. 设置定时任务（crontab）定期执行

示例 crontab：
# 每天凌晨 2 点执行备份
0 2 * * * python3 /path/to/backup.py >> /var/log/dsw_backup.log 2>&1

# 每 6 小时执行一次
0 */6 * * * python3 /path/to/backup.py >> /var/log/dsw_backup.log 2>&1

# 每周一凌晨 3 点执行周备份
0 3 * * 1 python3 /path/to/backup.py --mode weekly >> /var/log/dsw_backup.log 2>&1
"""

import os
import sys
import json
import time
import subprocess
import argparse
from datetime import datetime, timedelta
from typing import Optional, Dict, List

# ============================================================
# 配置区域 - 根据实际情况修改
# ============================================================

# 要备份的实例列表（ID 或名称）
BACKUP_INSTANCES = [
    "my-instance-1",
    "my-instance-2",
]

# 备份保留策略
RETENTION_POLICY = {
    "hourly": 24,    # 保留最近 24 个小时备份
    "daily": 7,      # 保留最近 7 天的每日备份
    "weekly": 4,     # 保留最近 4 周的每周备份
    "monthly": 12,   # 保留最近 12 个月的每月备份
}

# 备份名称前缀
BACKUP_PREFIX = "auto-backup"

# 默认备份模式
DEFAULT_MODE = "daily"  # hourly, daily, weekly, monthly

# 备份描述模板
BACKUP_DESCRIPTION = "自动备份 - {mode} - {timestamp}"

# 日志文件路径
LOG_FILE = os.path.expanduser("~/.dsw_backup.log")

# 是否启用详细输出
VERBOSE = True

# ============================================================
# 核心逻辑
# ============================================================

def log(message: str, level: str = "INFO"):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{level}] {message}"
    
    if VERBOSE or level in ["ERROR", "WARN", "SUCCESS"]:
        print(log_line)
    
    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_line + "\n")
    except Exception as e:
        print(f"无法写入日志文件: {e}")


def run_dsw_command(command: str, args: list, capture: bool = True) -> tuple:
    """执行 dsw.py 命令"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dsw_path = os.path.join(script_dir, "..", "scripts", "dsw.py")
    
    cmd = ["python3", dsw_path, command] + args
    result = subprocess.run(cmd, capture_output=capture, text=True)
    
    return result.returncode, result.stdout or "", result.stderr or ""


def get_instance_id(identifier: str) -> Optional[str]:
    """解析实例 ID"""
    code, stdout, stderr = run_dsw_command("get", [identifier, "--format", "json"])
    if code == 0:
        try:
            info = json.loads(stdout)
            return info.get("InstanceId", identifier)
        except json.JSONDecodeError:
            pass
    return identifier


def create_snapshot(instance: str, name: str, description: str = "") -> bool:
    """创建快照"""
    log(f"创建快照: {instance} -> {name}")
    
    args = [instance, name]
    if description:
        args.extend(["--description", description])
    
    code, stdout, stderr = run_dsw_command("snapshot", args)
    
    if code == 0:
        log(f"快照创建成功: {name}", "SUCCESS")
        return True
    else:
        log(f"快照创建失败: {stderr}", "ERROR")
        return False


def list_snapshots(instance: str) -> List[Dict]:
    """列出实例的所有快照"""
    code, stdout, stderr = run_dsw_command("snapshots", [instance, "--format", "json"])
    
    if code == 0:
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            log(f"解析快照列表失败: {stdout}", "ERROR")
    return []


def parse_snapshot_time(snapshot: Dict) -> Optional[datetime]:
    """解析快照创建时间"""
    time_str = snapshot.get("CreationTime") or snapshot.get("CreatedTime")
    if time_str:
        try:
            # 尝试多种时间格式
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"]:
                try:
                    return datetime.strptime(time_str, fmt)
                except ValueError:
                    continue
        except Exception:
            pass
    return None


def get_backup_mode_from_name(name: str) -> Optional[str]:
    """从备份名称推断备份模式"""
    if "-hourly-" in name:
        return "hourly"
    elif "-daily-" in name:
        return "daily"
    elif "-weekly-" in name:
        return "weekly"
    elif "-monthly-" in name:
        return "monthly"
    return None


def cleanup_old_snapshots(instance: str, mode: str):
    """清理旧快照"""
    retention_count = RETENTION_POLICY.get(mode, 7)
    
    log(f"清理旧快照: {instance}, 模式: {mode}, 保留数量: {retention_count}")
    
    # 获取所有快照
    all_snapshots = list_snapshots(instance)
    
    # 筛选当前模式的自动备份快照
    mode_prefix = f"{BACKUP_PREFIX}-{mode}"
    mode_snapshots = [
        s for s in all_snapshots
        if s.get("SnapshotName", "").startswith(mode_prefix)
    ]
    
    # 按创建时间排序（新的在前）
    mode_snapshots.sort(key=lambda s: parse_snapshot_time(s) or datetime.min, reverse=True)
    
    log(f"找到 {len(mode_snapshots)} 个 {mode} 模式的快照")
    
    # 删除超出保留数量的快照
    to_delete = mode_snapshots[retention_count:]
    
    for snapshot in to_delete:
        snapshot_id = snapshot.get("SnapshotId")
        snapshot_name = snapshot.get("SnapshotName", "unknown")
        
        if snapshot_id:
            log(f"删除旧快照: {snapshot_name} ({snapshot_id})")
            code, stdout, stderr = run_dsw_command("delete-snapshot", [snapshot_id, "-f"])
            
            if code == 0:
                log(f"快照删除成功: {snapshot_name}", "SUCCESS")
            else:
                log(f"快照删除失败: {stderr}", "WARN")


def backup_instance(instance: str, mode: str) -> bool:
    """备份单个实例"""
    log(f"开始备份实例: {instance} (模式: {mode})")
    
    # 生成备份名称
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    snapshot_name = f"{BACKUP_PREFIX}-{mode}-{timestamp}"
    
    # 生成描述
    description = BACKUP_DESCRIPTION.format(
        mode=mode,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    # 创建快照
    success = create_snapshot(instance, snapshot_name, description)
    
    if success:
        # 清理旧快照
        cleanup_old_snapshots(instance, mode)
    
    return success


def backup_all_instances(mode: str) -> Dict[str, bool]:
    """备份所有配置的实例"""
    results = {}
    
    log("=" * 50)
    log(f"开始批量备份 - 模式: {mode}, 实例数: {len(BACKUP_INSTANCES)}")
    log("=" * 50)
    
    for instance in BACKUP_INSTANCES:
        success = backup_instance(instance, mode)
        results[instance] = success
    
    # 汇总结果
    success_count = sum(1 for v in results.values() if v)
    fail_count = len(results) - success_count
    
    log("=" * 50)
    log(f"备份完成 - 成功: {success_count}, 失败: {fail_count}")
    log("=" * 50)
    
    return results


def list_backup_status():
    """显示备份状态"""
    log("=" * 50)
    log("备份状态概览")
    log("=" * 50)
    
    for instance in BACKUP_INSTANCES:
        log(f"\n实例: {instance}")
        
        # 获取快照列表
        snapshots = list_snapshots(instance)
        
        # 按模式分组统计
        by_mode = {"hourly": [], "daily": [], "weekly": [], "monthly": []}
        
        for snapshot in snapshots:
            name = snapshot.get("SnapshotName", "")
            if name.startswith(BACKUP_PREFIX):
                mode = get_backup_mode_from_name(name)
                if mode:
                    by_mode[mode].append(snapshot)
        
        # 打印统计
        for mode, snaps in by_mode.items():
            retention = RETENTION_POLICY.get(mode, "N/A")
            log(f"  {mode}: {len(snaps)} 个快照 (保留策略: {retention})")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="PAI-DSW 定时备份脚本")
    parser.add_argument(
        "--mode", "-m",
        choices=["hourly", "daily", "weekly", "monthly"],
        default=DEFAULT_MODE,
        help="备份模式 (default: %(default)s)"
    )
    parser.add_argument(
        "--instance", "-i",
        help="指定单个实例备份（不指定则备份所有配置的实例）"
    )
    parser.add_argument(
        "--status", "-s",
        action="store_true",
        help="显示备份状态概览"
    )
    parser.add_argument(
        "--cleanup-only",
        action="store_true",
        help="仅执行清理，不创建新备份"
    )
    
    args = parser.parse_args()
    
    # 显示状态
    if args.status:
        list_backup_status()
        return
    
    # 单实例备份
    if args.instance:
        if args.cleanup_only:
            cleanup_old_snapshots(args.instance, args.mode)
        else:
            backup_instance(args.instance, args.mode)
        return
    
    # 批量备份
    if args.cleanup_only:
        for instance in BACKUP_INSTANCES:
            cleanup_old_snapshots(instance, args.mode)
    else:
        backup_all_instances(args.mode)


if __name__ == "__main__":
    main()