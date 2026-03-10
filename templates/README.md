# PAI-DSW 自动化运维模板

本目录包含常用的自动化运维脚本模板，可直接复制使用或根据实际需求修改。

## 📁 模板列表

| 模板 | 说明 | 适用场景 |
|------|------|---------|
| `auto_scaling.py` | 自动扩缩容 | 根据资源使用率自动调整实例规格 |
| `backup.py` | 定时备份 | 定期创建快照，支持保留策略 |

---

## 🔧 auto_scaling.py - 自动扩缩容

### 功能特性

- 📊 监控 CPU/内存/GPU 使用率
- ⬆️ 超过阈值自动升级规格
- ⬇️ 低于阈值自动降级规格
- ⏱️ 冷却时间防止频繁切换
- 📝 完整的操作日志记录

### 使用步骤

```bash
# 1. 复制脚本到工作目录
cp templates/auto_scaling.py ~/auto_scaling.py

# 2. 编辑配置（修改 TARGET_INSTANCE、阈值等）
vim ~/auto_scaling.py

# 3. 测试运行（DRY_RUN 默认开启）
python3 ~/auto_scaling.py

# 4. 确认无误后关闭 DRY_RUN 模式
# 将 DRY_RUN = False

# 5. 设置定时任务（每 5 分钟检查一次）
crontab -e
# 添加：
*/5 * * * * python3 ~/auto_scaling.py >> /var/log/dsw_scaling.log 2>&1
```

### 关键配置项

```python
TARGET_INSTANCE = "my-instance"       # 目标实例
SCALE_UP_THRESHOLD = 80              # 扩容阈值 (%)
SCALE_DOWN_THRESHOLD = 30            # 缩容阈值 (%)
COOLDOWN_MINUTES = 30                # 冷却时间 (分钟)
SPEC_LADDER = [...]                  # 规格升级路径
DRY_RUN = True                       # 干运行模式（测试用）
```

### 规格升级路径

默认提供两条升级路径：

**CPU 实例路径：**
```
ecs.g6.large → ecs.g6.xlarge → ecs.g6.2xlarge → ecs.g6.4xlarge → ecs.g6.8xlarge
```

**GPU 实例路径：**
```
ecs.gn6v-c8g1.4xlarge → ecs.gn6v-c8g1.8xlarge → ecs.gn6v-c8g1.16xlarge
```

根据实际需求修改 `SPEC_LADDER` 和 `GPU_SPEC_LADDER`。

---

## 💾 backup.py - 定时备份

### 功能特性

- 📸 定期创建实例快照
- 🕐 支持多种备份频率（小时/日/周/月）
- 🗑️ 自动清理旧备份（保留策略）
- 📊 备份状态概览
- 🔄 支持批量备份多个实例

### 使用步骤

```bash
# 1. 复制脚本到工作目录
cp templates/backup.py ~/backup.py

# 2. 编辑配置（修改 BACKUP_INSTANCES 等）
vim ~/backup.py

# 3. 测试运行
python3 ~/backup.py --mode daily --status

# 4. 设置定时任务
crontab -e

# 每天凌晨 2 点执行每日备份
0 2 * * * python3 ~/backup.py --mode daily >> /var/log/dsw_backup.log 2>&1

# 每周一凌晨 3 点执行每周备份
0 3 * * 1 python3 ~/backup.py --mode weekly >> /var/log/dsw_backup.log 2>&1

# 每月 1 号凌晨 4 点执行每月备份
0 4 1 * * python3 ~/backup.py --mode monthly >> /var/log/dsw_backup.log 2>&1
```

### 命令选项

```bash
# 执行每日备份（默认）
python3 backup.py --mode daily

# 执行每周备份
python3 backup.py --mode weekly

# 备份单个实例
python3 backup.py --mode daily --instance my-instance

# 仅查看备份状态
python3 backup.py --status

# 仅清理旧备份（不创建新备份）
python3 backup.py --cleanup-only
```

### 保留策略

默认配置：

| 模式 | 保留数量 | 说明 |
|------|---------|------|
| hourly | 24 | 保留最近 24 个小时备份 |
| daily | 7 | 保留最近 7 天的每日备份 |
| weekly | 4 | 保留最近 4 周的每周备份 |
| monthly | 12 | 保留最近 12 个月的每月备份 |

修改 `RETENTION_POLICY` 配置项调整。

### 备份命名规则

```
{BACKUP_PREFIX}-{mode}-{timestamp}
```

示例：
```
auto-backup-daily-20260308-020000
auto-backup-weekly-20260302-030000
```

---

## 🕐 Crontab 快速参考

```bash
# 编辑定时任务
crontab -e

# 查看当前定时任务
crontab -l

# 时间格式
# 分钟 小时 日 月 星期
#  *    *   *   *   *

# 示例
*/5 * * * *     # 每 5 分钟
0 * * * *       # 每小时整点
0 2 * * *       # 每天凌晨 2 点
0 3 * * 1       # 每周一凌晨 3 点
0 4 1 * *       # 每月 1 号凌晨 4 点
```

---

## ⚠️ 注意事项

1. **测试先行**：生产环境使用前，先用 `DRY_RUN=True` 测试
2. **权限确认**：确保 RAM 角色有相应的操作权限
3. **日志监控**：定期检查日志文件，确保脚本正常运行
4. **资源成本**：快照会占用存储空间，注意清理策略
5. **规格变更**：规格变更可能导致实例重启，请合理安排执行时间

---

## 📝 日志文件

- 自动扩缩容日志：`~/.dsw_scaling.log`
- 定时备份日志：`~/.dsw_backup.log`
- 状态文件：`~/.dsw_scaling_state.json`

---

## 🔗 相关文档

- [使用案例库](../references/use-cases.md)
- [故障排查指南](../references/troubleshooting.md)
- [SKILL.md](../SKILL.md) - 完整命令参考