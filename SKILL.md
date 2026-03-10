---
name: pai-dsw
description: PAI-DSW实例管理专家技能，支持实例全生命周期管理、工作空间/镜像管理、资源监控、成本估算、环境检测、故障诊断等。自动从DSW实例获取RAM角色凭证，无需手动配置AccessKey。
---

# PAI-DSW Skill 🚀

阿里云 PAI-DSW (Data Science Workshop) 实例管理专家技能。

## 功能概览

| 功能分类 | 脚本 | 功能 | 状态 |
|---------|------|------|------|
| **实例管理** | `list_instances.py` | 列出工作空间内所有实例 | ✅ |
| | `get_instance.py` | 查询实例详情 | ✅ |
| | `create_instance.py` | 创建实例 | ✅ |
| | `start_instance.py` | 启动实例 | ✅ |
| | `stop_instance.py` | 停止实例 | ✅ |
| | `delete_instance.py` | 删除实例 | ✅ |
| | `update_instance.py` | 更新实例规格 | ✅ |
| **批量操作** | `stop_instances.py` | 批量停止实例 | ✅ |
| | `delete_instances.py` | 批量删除实例 | ✅ |
| **资源监控** | `get_instance_metrics.py` | 实例资源监控 (CPU/内存/GPU) | ✅ |
| | `estimate_cost.py` | 成本估算 | ✅ |
| | `check_environment.py` | 环境检测 | ✅ |
| | `diagnose.py` | 故障诊断 | ✅ |
| | `get_resource_stats.py` | 资源组统计 | ✅ |
| **成本优化** | `create_idle_culler.py` | 空闲自动关机 | ✅ |
| | `create_shutdown_timer.py` | 定时关机 | ✅ |
| **运维诊断** | `get_instance_events.py` | 实例事件查询 | ✅ |
| | `list_system_logs.py` | 系统日志查询 | ✅ |
| **快照管理** | `create_snapshot.py` | 创建快照/自定义镜像 | ✅ |
| | `list_snapshots.py` | 列出实例快照 | ✅ |
| **镜像管理** | `list_images.py` | 列出可用镜像 | ✅ |
| **工作空间** | `list_workspaces.py` | 列出工作空间 | ✅ |
| **数据管理** | `list_datasets.py` | 数据集挂载信息 | ✅ |
| **规格查询** | `list_ecs_specs.py` | 列出可用 ECS 规格 | ✅ |
| **工具** | `dsw.py` | 统一命令行入口 | ✅ |
| | `dsw_utils.py` | 通用凭证模块 | ✅ |

## 快速开始

### 统一命令行工具 (推荐)

```bash
# 进入脚本目录
cd ~/.openclaw/workspace/skills/pai-dsw/scripts

# 列出所有命令
./dsw.py --help

# 列出实例
./dsw.py list

# 查询实例详情（支持名称模糊匹配）
./dsw.py get my-instance

# 启动实例
./dsw.py start my-inst

# 查看完整信息
./dsw.py info my-instance
```

### 环境准备

#### 方式一：在 DSW 实例中运行（推荐）

在阿里云 DSW 实例中运行时，会自动从 RAM 角色获取临时凭证，无需任何配置：

```bash
./dsw.py list  # 直接使用，自动获取凭证
```

#### 方式二：在非 DSW 环境运行（本地/其他服务器）

**选项 A：交互式配置（推荐新用户）**

```bash
# 运行配置向导
./dsw.py config init

# 按提示输入：
# - AccessKey ID
# - AccessKey Secret  
# - 默认区域
# - 工作空间 ID（可选）
```

**选项 B：配置文件**

创建 `~/.dsw/config.json`：

```json
{
  "access_key_id": "LTAI...",
  "access_key_secret": "...",
  "region": "ap-southeast-1",
  "workspace_id": "265816"
}
```

**选项 C：环境变量**

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID=<your-access-key-id>
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<your-access-key-secret>
export ALIBABA_CLOUD_REGION_ID=ap-southeast-1
export PAI_WORKSPACE_ID=<your-workspace-id>
```

#### 配置管理命令

```bash
# 查看当前配置和环境信息
./dsw.py config show

# 设置配置项
./dsw.py config set region cn-hangzhou
./dsw.py config set workspace_id 123456

# 选择默认工作空间（交互式）
./dsw.py config workspace
```

#### 凭证优先级

1. 环境变量 (`ALIBABA_CLOUD_ACCESS_KEY_ID`, `ALIBABA_CLOUD_ACCESS_KEY_SECRET`)
2. 配置文件 (`~/.dsw/config.json`)
3. DSW RAM 角色凭证 URI（DSW 实例内）
4. 交互式输入

## 详细命令说明

### 实例管理

#### 列出实例
```bash
# 表格格式
./dsw.py list

# JSON 格式
./dsw.py list --format json
```

#### 查询实例详情
```bash
# 使用实例 ID
./dsw.py get dsw-384188-5549877f88-2bdft

# 使用名称（模糊匹配）
./dsw.py get my-instance
```

#### 创建实例
```bash
./dsw.py create --name my-instance \
    --image modelscope:1.34.0-pytorch2.9.1-gpu \
    --type ecs.g6.large \
    --labels '{"env":"dev","team":"ml"}'
```

#### 启动/停止/删除实例
```bash
./dsw.py start my-instance
./dsw.py stop my-instance        # 需要确认
./dsw.py stop my-instance -f     # 跳过确认
./dsw.py delete my-instance      # 需要输入 'delete' 确认
./dsw.py delete my-instance -f   # 跳过确认
```

#### 更新实例规格
```bash
./dsw.py update my-instance --spec ecs.g6.xlarge
./dsw.py update my-instance --cpu 8 --memory 32
./dsw.py update my-instance --labels '{"env":"prod"}'
```

### 资源监控

#### 实例资源监控
```bash
# 获取所有指标
./dsw.py metrics my-instance

# 仅 CPU
./dsw.py metrics my-instance --type cpu

# 仅显示摘要
./dsw.py metrics my-instance --summary
```

#### 成本估算
```bash
# 所有实例成本
./dsw.py cost

# 指定实例
./dsw.py cost --instance my-instance

# JSON 格式
./dsw.py cost --format json
```

### 环境与诊断

#### 环境检测
```bash
./dsw.py env

# 输出包括：
# - 系统信息 (OS, 架构)
# - CPU 信息 (核心数, 型号)
# - 内存信息 (总量, 可用, 使用率)
# - 磁盘信息 (各挂载点使用情况)
# - GPU 信息 (型号, 显存, CUDA 版本)
# - Python 包 (PyTorch, TensorFlow 等)
# - 网络信息 (IP, 连接状态)
# - 关键环境变量
```

#### 故障诊断
```bash
./dsw.py diagnose

# 自动检查：
# - 磁盘空间不足
# - 内存不足
# - GPU 状态异常
# - 网络连接问题
# - 阿里云凭证问题
# - Python 包冲突
# - 异常进程
```

### 镜像与工作空间

#### 列出可用镜像
```bash
# 所有镜像
./dsw.py images

# 仅官方镜像
./dsw.py images --type official

# 仅自定义镜像
./dsw.py images --type custom

# 搜索 PyTorch 镜像
./dsw.py images --search pytorch
```

#### 列出工作空间
```bash
./dsw.py workspaces
```

### 快照管理

#### 创建快照
```bash
./dsw.py snapshot my-instance my-snapshot-name
./dsw.py snapshot my-instance my-snapshot --description "备份说明"
```

#### 列出快照
```bash
./dsw.py snapshots my-instance
```

### 规格查询

```bash
# 所有规格
./dsw.py specs

# 仅 GPU 规格
./dsw.py specs --gpu

# 仅 CPU 规格
./dsw.py specs --cpu
```

### 数据集挂载

```bash
# 当前实例的数据集
./dsw.py datasets

# 指定实例
./dsw.py datasets my-instance
```

### 完整信息

```bash
# 一键查看实例的详情、资源、快照
./dsw.py info my-instance
```

### 搜索实例

```bash
# 按名称/标签搜索
./dsw.py search gpu
./dsw.py search prod
```

## 技术实现

- **SDK**: 使用官方 SDK `alibabacloud-pai-dsw20220101`
- **认证**: 支持 RAM 角色自动获取临时凭证
- **安全**: 危险操作（停止、删除）需要用户确认
- **友好**: 支持实例名称模糊匹配、彩色输出

## 区域支持

支持所有阿里云 PAI-DSW 区域：
- **中国区**: `cn-hangzhou`, `cn-shanghai`, `cn-beijing`, `cn-shenzhen`, `cn-hongkong` 等
- **海外区**: `ap-southeast-1` (新加坡), `ap-northeast-1` (东京), `us-east-1` (美东) 等

## 常见场景

### 场景 1: 检查实例状态
```bash
./dsw.py status              # 当前实例
./dsw.py info my-instance    # 指定实例完整信息
```

### 场景 2: 调试问题实例
```bash
./dsw.py diagnose            # 自动诊断
./dsw.py env                 # 查看环境
```

### 场景 3: 成本优化
```bash
./dsw.py cost                # 查看成本
./dsw.py list                # 找到闲置实例
./dsw.py stop <闲置实例>      # 停止节省费用
```

### 场景 4: 选择合适的镜像
```bash
./dsw.py images --search pytorch
./dsw.py specs --gpu         # 查看 GPU 规格
```

## API 限流处理

PAI-DSW Skill 内置了 API 限流处理功能，自动处理 API 调用失败和限流场景。

### 功能特性

- **自动重试**: API 调用失败时自动重试，支持多种退避策略
- **请求限速**: 使用令牌桶算法控制请求频率，避免触发限流
- **可配置**: 通过环境变量自定义限流参数

### 配置方式

```bash
# 重试配置
export DSW_MAX_RETRIES=3          # 最大重试次数（默认: 3）
export DSW_BACKOFF_FACTOR=2.0     # 退避因子（默认: 2.0）
export DSW_BASE_DELAY=1.0         # 基础延迟秒数（默认: 1.0）
export DSW_MAX_DELAY=60.0         # 最大延迟秒数（默认: 60.0）

# 限速配置
export DSW_RATE_LIMIT=20          # 时间窗口内最大请求数（默认: 20）
export DSW_RATE_PERIOD=1.0        # 时间窗口秒数（默认: 1.0）
```

### 重试策略

默认使用 **带抖动的指数退避** (JITTERED)，可自动处理：

| 错误类型 | 处理方式 |
|---------|---------|
| 429 Too Many Requests | 自动重试 |
| 500/502/503/504 服务错误 | 自动重试 |
| 连接超时 | 自动重试 |
| 网络错误 | 自动重试 |

### 代码示例

```python
from dsw_utils import create_client

# 创建带限流的客户端（默认启用）
client = create_client()

# 禁用限流（不推荐）
client = create_client(with_rate_limit=False)
```

### 限流统计

查看 API 调用统计：

```python
from dsw_utils import print_rate_limit_stats
print_rate_limit_stats()
```

## 注意事项

- **停止实例**: 会中断所有运行中的进程
- **删除实例**: 不可恢复，所有数据将丢失
- **创建快照**: 实例需要处于运行状态
- **成本估算**: 价格仅供参考，实际以阿里云账单为准
- **限流处理**: 默认启用，可通过环境变量调整参数

## 更新日志

### v2.0 (2026-03-06)
- 🆕 新增工作空间管理
- 🆕 新增镜像管理
- 🆕 新增成本估算
- 🆕 新增环境检测
- 🆕 新增故障诊断
- 🆕 新增数据集挂载信息
- 🆕 新增完整信息命令 (info)
- ✨ 统一 CLI 入口 (dsw.py)
- ✨ 支持实例名称模糊匹配
- ✨ 彩色输出

### v1.0 (2026-03-02)
- 实例 CRUD 操作
- 资源监控
- 快照管理
- 规格查询