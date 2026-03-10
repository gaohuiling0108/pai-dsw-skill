# PAI-DSW 使用案例库

本文档提供常见场景的完整命令示例，帮助快速上手 PAI-DSW 管理。

---

## 目录

1. [环境配置（非 DSW 环境）](#1-环境配置非-dsw-环境)
2. [日常运维场景](#2-日常运维场景)
3. [开发调试场景](#3-开发调试场景)
4. [成本优化场景](#4-成本优化场景)
5. [故障排查场景](#5-故障排查场景)
6. [批量管理场景](#6-批量管理场景)
7. [完整工作流示例](#7-完整工作流示例)

---

## 1. 环境配置（非 DSW 环境）

> **注意**: 如果您在阿里云 DSW 实例中运行，可以跳过此章节，凭证会自动获取。

### 1.1 首次使用：交互式配置

在本地电脑或其他服务器上首次使用时，运行配置向导：

```bash
cd ~/.openclaw/workspace/skills/pai-dsw/scripts

# 启动配置向导
./dsw.py config init
```

按提示输入：
- AccessKey ID（从阿里云控制台获取）
- AccessKey Secret
- 默认区域（如 `ap-southeast-1`）
- 工作空间 ID（可选）

### 1.2 查看当前配置

```bash
./dsw.py config show
```

输出示例：
```
============================================================
  PAI-DSW Skill 环境信息
============================================================

  运行环境: 本地开发环境 💻
  主机名: my-laptop
  区域: ap-southeast-1
  工作空间: 265816

  凭证来源: 配置文件
  可用来源: 配置文件, 环境变量

  配置文件: /home/user/.dsw/config.json
============================================================
```

### 1.3 切换工作空间

```bash
# 交互式选择工作空间
./dsw.py config workspace

# 直接设置工作空间 ID
./dsw.py config set workspace_id 123456
```

### 1.4 配置文件位置

配置保存在 `~/.dsw/config.json`，可以手动编辑：

```json
{
  "access_key_id": "LTAI...",
  "access_key_secret": "...",
  "region": "ap-southeast-1",
  "workspace_id": "265816"
}
```

---

## 2. 日常运维场景

### 1.1 查看所有实例状态

**场景**: 每日检查工作空间内所有实例的运行状态。

```bash
cd ~/.openclaw/workspace/skills/pai-dsw/scripts

# 表格格式（人类可读）
./dsw.py list

# JSON 格式（便于脚本处理）
./dsw.py list --format json
```

**输出示例**:
```
==================================================
  PAI-DSW 实例列表
==================================================

实例ID                                    名称                状态        规格
--------------------------------------------------------------------------------
dsw-384188-5b7b85dc48-bvtdp              ml-training         Running     ecs.g6.xlarge
dsw-384188-5549877f88-2bdft              dev-notebook        Stopped     ecs.g6.large
```

### 1.2 快速查看当前实例信息

**场景**: 在 DSW 实例中运行，需要了解当前环境。

```bash
# 查看当前实例状态
./dsw.py status

# 查看完整信息（详情 + 资源 + 快照）
./dsw.py info $(hostname)

# 环境检测
./dsw.py env
```

### 1.3 启动/停止实例

**场景**: 按需启动或停止实例以节省成本。

```bash
# 启动实例（支持名称模糊匹配）
./dsw.py start ml-training

# 停止实例（需要确认）
./dsw.py stop ml-training

# 停止实例（跳过确认）
./dsw.py stop ml-training -f

# 批量停止多个实例
./dsw.py stop dev-1 -f && ./dsw.py stop dev-2 -f
```

### 1.4 搜索实例

**场景**: 按名称或标签快速定位实例。

```bash
# 按名称搜索
./dsw.py search gpu

# 按标签搜索（标签在名称或标签值中）
./dsw.py search prod
./dsw.py search team:ml
```

---

## 2. 开发调试场景

### 2.1 创建新实例

**场景**: 创建一个新的开发环境。

**步骤 1**: 查看可用镜像

```bash
# 查看所有镜像
./dsw.py images

# 搜索 PyTorch 镜像
./dsw.py images --search pytorch

# 仅查看官方镜像
./dsw.py images --type official
```

**步骤 2**: 查看可用规格

```bash
# 所有规格
./dsw.py specs

# 仅 GPU 规格
./dsw.py specs --gpu

# 仅 CPU 规格
./dsw.py specs --cpu
```

**步骤 3**: 创建实例

```bash
# 基本创建
./dsw.py create \
    --name my-dev-env \
    --image modelscope:1.34.0-pytorch2.9.1-gpu \
    --type ecs.g6.large

# 带标签创建
./dsw.py create \
    --name my-dev-env \
    --image modelscope:1.34.0-pytorch2.9.1-gpu \
    --type ecs.g6.large \
    --labels '{"env":"dev","team":"ml","owner":"momo"}'
```

### 2.2 更新实例规格

**场景**: 实例资源不足，需要升级配置。

```bash
# 查看当前规格
./dsw.py get my-instance

# 升级到更大的规格
./dsw.py update my-instance --spec ecs.g6.xlarge

# 或者单独调整 CPU 和内存
./dsw.py update my-instance --cpu 8 --memory 32

# 更新标签
./dsw.py update my-instance --labels '{"env":"prod"}'
```

### 2.3 创建快照备份

**场景**: 在重要修改前创建备份。

```bash
# 创建快照
./dsw.py snapshot my-instance backup-20260307 \
    --description "升级前的备份"

# 查看快照列表
./dsw.py snapshots my-instance
```

### 2.4 查看数据集挂载

**场景**: 确认数据集是否正确挂载。

```bash
# 当前实例
./dsw.py datasets

# 指定实例
./dsw.py datasets my-instance
```

---

## 3. 成本优化场景

### 3.1 查看成本概览

**场景**: 了解当前资源消耗和成本。

```bash
# 所有实例成本
./dsw.py cost

# 指定实例成本
./dsw.py cost --instance my-instance

# JSON 格式（便于分析）
./dsw.py cost --format json
```

### 3.2 找出闲置实例

**场景**: 识别可以停止的闲置实例。

```bash
# 列出所有实例
./dsw.py list

# 查看资源使用情况
./dsw.py metrics my-instance --summary

# 如果 CPU/内存/GPU 使用率都很低，考虑停止
./dsw.py stop my-instance
```

### 3.3 设置自动关机

**场景**: 防止忘记关机导致费用浪费。

**方法 1**: 使用空闲自动关机脚本

```bash
# 创建空闲自动关机（30分钟无活动自动停止）
python3 create_idle_culler.py --idle-time 1800
```

**方法 2**: 使用定时关机脚本

```bash
# 设置每天 22:00 自动关机
python3 create_shutdown_timer.py --time "22:00"
```

### 3.4 选择性价比规格

**场景**: 选择最经济的规格。

```bash
# 查看所有 GPU 规格
./dsw.py specs --gpu

# 比较不同规格的价格
./dsw.py cost --format json | jq '.[] | {spec: .InstanceType, hourly: .HourlyCost}'
```

---

## 4. 故障排查场景

### 4.1 实例无法启动

**场景**: 实例启动失败或卡在 Pending 状态。

**步骤 1**: 检查实例状态

```bash
./dsw.py get my-instance
```

**步骤 2**: 查看实例事件

```bash
python3 get_instance_events.py my-instance
```

**步骤 3**: 查看系统日志

```bash
python3 list_system_logs.py my-instance
```

**步骤 4**: 运行诊断

```bash
./dsw.py diagnose
```

### 4.2 实例运行缓慢

**场景**: 实例响应慢，需要排查原因。

**步骤 1**: 检查资源使用

```bash
# 查看所有资源指标
./dsw.py metrics my-instance

# 仅查看 CPU
./dsw.py metrics my-instance --type cpu

# 仅查看内存
./dsw.py metrics my-instance --type memory

# 仅查看 GPU
./dsw.py metrics my-instance --type gpu
```

**步骤 2**: 检查环境

```bash
./dsw.py env
```

**步骤 3**: 运行诊断

```bash
./dsw.py diagnose
```

**常见原因**:
- 磁盘空间不足 → 清理无用文件
- 内存不足 → 减少数据加载或升级规格
- GPU 显存不足 → 减小 batch size 或升级 GPU 规格

### 4.3 GPU 不可用

**场景**: 代码无法使用 GPU。

**步骤 1**: 检查 GPU 状态

```bash
./dsw.py env | grep -A 20 "GPU"
```

**步骤 2**: 检查 CUDA 环境

```bash
# 在实例内运行
nvidia-smi
nvcc --version
```

**步骤 3**: 检查 PyTorch/TensorFlow

```bash
python3 -c "import torch; print(torch.cuda.is_available())"
python3 -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

### 4.4 网络连接问题

**场景**: 无法访问外部网络或内部服务。

**步骤 1**: 运行诊断

```bash
./dsw.py diagnose
```

**步骤 2**: 检查网络配置

```bash
./dsw.py env | grep -A 10 "网络"
```

**常见原因**:
- 安全组配置问题
- VPC 网络配置问题
- DNS 解析问题

---

## 5. 批量管理场景

### 5.1 批量停止实例

**场景**: 下班前停止所有开发实例。

```bash
# 使用批量停止脚本
python3 stop_instances.py --name-pattern "dev-.*" --force

# 或使用循环
for name in dev-1 dev-2 dev-3; do
    ./dsw.py stop $name -f
done
```

### 5.2 批量删除实例

**场景**: 清理测试环境实例。

```bash
# 使用批量删除脚本
python3 delete_instances.py --name-pattern "test-.*" --force

# 或逐个删除
for name in test-1 test-2 test-3; do
    ./dsw.py delete $name -f
done
```

### 5.3 批量查询资源使用

**场景**: 生成所有实例的资源使用报告。

```bash
# 获取所有实例 ID
INSTANCE_IDS=$(./dsw.py list --format json | jq -r '.[].InstanceId')

# 逐个查询资源
for id in $INSTANCE_IDS; do
    echo "=== $id ==="
    ./dsw.py metrics $id --summary
done
```

### 5.4 批量创建快照

**场景**: 为所有生产实例创建备份。

```bash
# 获取所有生产实例
INSTANCES=$(./dsw.py search prod --format json | jq -r '.[].InstanceId')

# 创建快照
DATE=$(date +%Y%m%d)
for id in $INSTANCES; do
    ./dsw.py snapshot $id "backup-$DATE" --description "定期备份"
done
```

---

## 6. 完整工作流示例

### 6.1 新项目启动流程

**场景**: 从零开始创建一个新的机器学习项目环境。

```bash
# 1. 查看工作空间
./dsw.py workspaces

# 2. 查找合适的镜像
./dsw.py images --search pytorch

# 3. 选择规格
./dsw.py specs --gpu

# 4. 创建实例
./dsw.py create \
    --name ml-project-v1 \
    --image modelscope:1.34.0-pytorch2.9.1-gpu \
    --type ecs.gn6v-c8g1.2xlarge \
    --labels '{"project":"ml-v1","env":"dev","owner":"momo"}'

# 5. 等待实例启动
sleep 60

# 6. 验证环境
./dsw.py env

# 7. 创建初始快照
./dsw.py snapshot ml-project-v1 init-backup \
    --description "初始环境备份"
```

### 6.2 模型训练流程

**场景**: 准备进行大规模模型训练。

```bash
# 1. 检查当前资源
./dsw.py metrics $(hostname) --summary

# 2. 如果资源不足，升级规格
./dsw.py update $(hostname) --spec ecs.gn6v-c8g1.4xlarge

# 3. 等待规格更新完成
sleep 120

# 4. 验证 GPU 可用
./dsw.py env | grep GPU

# 5. 创建训练前快照
./dsw.py snapshot $(hostname) pre-training \
    --description "训练前备份"

# 6. 开始训练...

# 7. 监控资源使用
./dsw.py metrics $(hostname) --type gpu

# 8. 训练完成后创建快照
./dsw.py snapshot $(hostname) post-training \
    --description "训练完成备份"

# 9. 降级规格节省成本
./dsw.py update $(hostname) --spec ecs.g6.large
```

### 6.3 故障排查完整流程

**场景**: 实例出现问题，需要完整排查。

```bash
# 1. 获取实例信息
./dsw.py get my-instance

# 2. 检查资源使用
./dsw.py metrics my-instance

# 3. 运行自动诊断
./dsw.py diagnose

# 4. 检查环境
./dsw.py env

# 5. 查看实例事件
python3 get_instance_events.py my-instance

# 6. 查看系统日志
python3 list_system_logs.py my-instance

# 7. 如果需要，创建快照后重建
./dsw.py snapshot my-instance debug-backup
./dsw.py stop my-instance -f
./dsw.py start my-instance
```

### 6.4 成本优化完整流程

**场景**: 月度成本优化检查。

```bash
# 1. 查看成本概览
./dsw.py cost

# 2. 列出所有实例
./dsw.py list

# 3. 检查每个实例的资源使用
for id in $(./dsw.py list --format json | jq -r '.[].InstanceId'); do
    echo "=== $id ==="
    ./dsw.py metrics $id --summary
done

# 4. 找出低使用率实例
# (手动分析或使用脚本)

# 5. 停止闲置实例
./dsw.py stop idle-instance-1 -f
./dsw.py stop idle-instance-2 -f

# 6. 删除不需要的实例
./dsw.py delete old-test-instance -f

# 7. 设置自动关机
python3 create_idle_culler.py --idle-time 1800

# 8. 再次查看成本
./dsw.py cost
```

---

## 快速参考卡

| 场景 | 命令 |
|------|------|
| 查看所有实例 | `./dsw.py list` |
| 查看实例详情 | `./dsw.py get <instance>` |
| 查看完整信息 | `./dsw.py info <instance>` |
| 启动实例 | `./dsw.py start <instance>` |
| 停止实例 | `./dsw.py stop <instance>` |
| 删除实例 | `./dsw.py delete <instance>` |
| 创建实例 | `./dsw.py create --name <n> --image <i> --type <t>` |
| 查看资源 | `./dsw.py metrics <instance>` |
| 查看成本 | `./dsw.py cost` |
| 环境检测 | `./dsw.py env` |
| 故障诊断 | `./dsw.py diagnose` |
| 查看镜像 | `./dsw.py images` |
| 查看规格 | `./dsw.py specs` |
| 创建快照 | `./dsw.py snapshot <instance> <name>` |
| 搜索实例 | `./dsw.py search <keyword>` |

---

## 注意事项

1. **停止实例**: 会中断所有运行中的进程，请确保已保存工作
2. **删除实例**: 不可恢复，所有数据将丢失，请提前创建快照
3. **创建快照**: 实例需要处于运行状态
4. **成本估算**: 价格仅供参考，实际以阿里云账单为准
5. **规格更新**: 可能需要重启实例

---

*最后更新: 2026-03-07*