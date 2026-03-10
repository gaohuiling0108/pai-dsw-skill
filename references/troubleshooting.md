# PAI-DSW 故障排查指南

本文档提供常见错误代码、问题诊断步骤和解决方案，帮助快速定位和解决问题。

---

## 目录

1. [快速诊断流程](#1-快速诊断流程)
2. [常见错误代码](#2-常见错误代码)
3. [实例问题排查](#3-实例问题排查)
4. [资源问题排查](#4-资源问题排查)
5. [网络问题排查](#5-网络问题排查)
6. [凭证与权限问题](#6-凭证与权限问题)
7. [Python 环境问题](#7-python-环境问题)
8. [API 调用失败排查](#8-api-调用失败排查)
9. [常见问题 FAQ](#9-常见问题-faq)

---

## 1. 快速诊断流程

### 1.1 自动诊断

首先运行自动诊断工具，快速发现常见问题：

```bash
cd ~/.openclaw/workspace/skills/pai-dsw/scripts

# 运行诊断
./dsw.py diagnose
```

**诊断检查项目**：
- ✅ 磁盘空间
- ✅ 内存使用
- ✅ GPU 状态
- ✅ 网络连接
- ✅ 阿里云凭证
- ✅ Python 环境
- ✅ 进程状态

### 1.2 手动诊断流程

如果自动诊断未发现问题，按以下步骤手动排查：

```
Step 1: 检查实例状态
    ./dsw.py status                    # 当前实例
    ./dsw.py get <instance-id>         # 指定实例

Step 2: 检查资源使用
    ./dsw.py metrics <instance-id>     # 资源监控
    ./dsw.py env                       # 环境检测

Step 3: 检查日志
    python3 get_instance_events.py <instance-id>
    python3 list_system_logs.py <instance-id>

Step 4: 检查网络
    ping -c 3 aliyun.com
    curl -I https://pai-dsw.cn-hangzhou.aliyuncs.com

Step 5: 检查凭证
    echo $ALIBABA_CLOUD_ACCESS_KEY_ID
    curl $ALIBABA_CLOUD_CREDENTIALS_URI
```

---

## 2. 常见错误代码

### 2.1 实例操作错误

| 错误代码 | 描述 | 解决方案 |
|---------|------|---------|
| `InvalidInstanceId.NotFound` | 实例不存在 | 检查实例 ID 是否正确，使用 `./dsw.py list` 确认 |
| `IncorrectInstanceStatus` | 实例状态不允许此操作 | 检查实例当前状态，等待状态变更或调整操作顺序 |
| `InstanceLocked` | 实例被锁定 | 检查是否有进行中的操作，等待操作完成 |
| `QuotaExceeded` | 配额不足 | 联系管理员申请配额或删除不需要的实例 |
| `ResourceNotAvailable` | 资源不可用 | 指定的规格或镜像不可用，使用 `./dsw.py specs` 查看可用规格 |

### 2.2 凭证与权限错误

| 错误代码 | 描述 | 解决方案 |
|---------|------|---------|
| `InvalidAccessKeyId.NotFound` | AccessKey 不存在 | 检查 AK 配置，确保正确设置环境变量 |
| `SignatureDoesNotMatch` | 签名错误 | 检查 AccessKeySecret 是否正确 |
| `SecurityTokenExpired` | 临时凭证过期 | 重新获取凭证，RAM 角色凭证会自动刷新 |
| `NoPermission` | 无权限 | 检查 RAM 角色权限，确保有 PAI 相关权限 |
| `UnauthorizedOperation` | 未授权操作 | 检查 RAM 策略，确保有对应操作权限 |

### 2.3 网络与服务错误

| 错误代码 | 描述 | 解决方案 |
|---------|------|---------|
| `ServiceUnavailable` | 服务不可用 | 稍后重试，检查阿里云服务状态 |
| `InternalError` | 内部错误 | 稍后重试，如持续出现请联系支持 |
| `Throttling` | 请求被限流 | 降低请求频率，实现重试机制 |
| `NetworkError` | 网络错误 | 检查网络连接，确认 VPC 和安全组配置 |

### 2.4 镜像与快照错误

| 错误代码 | 描述 | 解决方案 |
|---------|------|---------|
| `ImageNotFound` | 镜像不存在 | 使用 `./dsw.py images` 查看可用镜像 |
| `SnapshotCreateFailed` | 快照创建失败 | 检查实例状态，确保实例正在运行 |
| `SnapshotLimitExceeded` | 快照数量超限 | 删除不需要的快照 |
| `InvalidImageFormat` | 镜像格式错误 | 使用官方推荐镜像格式 |

---

## 3. 实例问题排查

### 3.1 实例无法启动

**症状**: 实例启动失败或卡在 Pending 状态

**排查步骤**:

```bash
# 1. 检查实例详情
./dsw.py get <instance-id>

# 2. 查看实例事件
python3 get_instance_events.py <instance-id>

# 3. 查看系统日志
python3 list_system_logs.py <instance-id>

# 4. 检查资源配额
./dsw.py workspaces
```

**常见原因与解决方案**:

| 原因 | 解决方案 |
|------|---------|
| 资源配额不足 | 联系管理员增加配额，或释放其他实例 |
| 规格不可用 | 换一个可用规格，使用 `./dsw.py specs` 查看 |
| 镜像损坏 | 更换镜像，使用 `./dsw.py images` 查看 |
| 底层资源不足 | 稍后重试，或换一个可用区 |
| 欠费或账户异常 | 检查阿里云账户状态 |

### 3.2 实例无法停止

**症状**: 停止操作卡住或失败

**排查步骤**:

```bash
# 1. 检查实例状态
./dsw.py get <instance-id>

# 2. 强制停止
./dsw.py stop <instance-id> --force

# 3. 检查是否有异常进程
./dsw.py diagnose
```

**常见原因与解决方案**:

| 原因 | 解决方案 |
|------|---------|
| 有进程占用 | 先结束关键进程，再停止 |
| GPU 进程卡住 | 使用 `nvidia-smi` 检查 GPU 进程，kill 后重试 |
| 存储挂载问题 | 检查数据集挂载状态 |
| 系统进程异常 | 联系技术支持 |

### 3.3 实例运行缓慢

**症状**: 实例响应慢，命令执行缓慢

**排查步骤**:

```bash
# 1. 检查资源使用
./dsw.py metrics <instance-id>
./dsw.py metrics <instance-id> --type cpu
./dsw.py metrics <instance-id> --type memory

# 2. 检查环境
./dsw.py env

# 3. 运行诊断
./dsw.py diagnose

# 4. 检查磁盘 I/O
iostat -x 1 5
```

**常见原因与解决方案**:

| 原因 | 解决方案 |
|------|---------|
| 内存不足 | 减少数据加载量，或升级规格 |
| 磁盘空间不足 | 清理不需要的文件，检查 `du -sh /*` |
| 磁盘 I/O 高 | 减少并发 I/O 操作，考虑使用 SSD |
| CPU 资源不足 | 升级规格，或优化代码 |
| 网络延迟高 | 检查网络配置 |

### 3.4 实例连接断开

**症状**: SSH 或 Jupyter 连接断开

**排查步骤**:

```bash
# 1. 检查实例状态
./dsw.py get <instance-id>

# 2. 检查网络
./dsw.py diagnose

# 3. 检查会话状态
# 在实例内运行
ps aux | grep jupyter
netstat -tlnp | grep 8888
```

**常见原因与解决方案**:

| 原因 | 解决方案 |
|------|---------|
| 实例被停止 | 重启实例 |
| 网络波动 | 检查本地网络，稍后重连 |
| 会话超时 | 配置会话保持 |
| 内存溢出导致重启 | 检查内存使用，优化代码 |
| GPU OOM | 减小 batch size |

---

## 4. 资源问题排查

### 4.1 磁盘空间不足

**症状**: 写入文件失败，提示 No space left on device

**诊断命令**:

```bash
# 检查磁盘使用
df -h

# 找出大文件/目录
du -sh /* | sort -rh | head -20

# 找出大文件
find /mnt/workspace -type f -size +100M 2>/dev/null | head -20
```

**解决方案**:

```bash
# 清理 pip 缓存
pip cache purge

# 清理 conda 缓存
conda clean --all

# 清理临时文件
rm -rf /tmp/*

# 清理旧的模型缓存
rm -rf ~/.cache/huggingface/models--*/.locks
rm -rf ~/.cache/torch/hub/checkpoints/*.tar

# 检查并删除不需要的数据
du -sh /mnt/data/*
```

### 4.2 内存不足

**症状**: 进程被 kill，OOM 错误

**诊断命令**:

```bash
# 检查内存使用
free -h
cat /proc/meminfo | grep -E 'Mem|Available'

# 查看内存占用进程
ps aux --sort=-%mem | head -10

# 检查是否有 swap
swapon -s
```

**解决方案**:

```bash
# 1. 结束占用内存的进程
kill -9 <pid>

# 2. 清理缓存（谨慎）
sync && echo 3 > /proc/sys/vm/drop_caches

# 3. 减少数据加载量
# 在代码中减小 batch_size

# 4. 使用更高效的数据格式
# 如使用 .npy 替代 .csv

# 5. 考虑升级规格
./dsw.py update <instance-id> --spec ecs.g6.xlarge
```

### 4.3 GPU 问题

**症状**: GPU 不可用或显存不足

**诊断命令**:

```bash
# 检查 GPU 状态
nvidia-smi

# 检查 CUDA
nvcc --version

# 检查 PyTorch GPU 支持
python3 -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
python3 -c "import torch; print(f'Device count: {torch.cuda.device_count()}')"

# 检查 GPU 进程
nvidia-smi --query-compute-apps=pid,name,used_memory --format=csv
```

**常见问题与解决方案**:

| 问题 | 解决方案 |
|------|---------|
| CUDA not available | 检查 CUDA 版本与 PyTorch 版本是否匹配 |
| GPU 显存不足 | 减小 batch_size，使用梯度累积 |
| GPU 进程残留 | `nvidia-smi` 查看 PID，`kill -9 <pid>` |
| 驱动版本不匹配 | 使用兼容的镜像，或联系支持 |
| GPU 利用率低 | 检查数据加载是否成为瓶颈 |

---

## 5. 网络问题排查

### 5.1 外网连接问题

**症状**: 无法访问外部网站或下载文件

**诊断命令**:

```bash
# 测试外网连接
ping -c 3 8.8.8.8
ping -c 3 aliyun.com

# 测试 DNS
nslookup aliyun.com
dig aliyun.com

# 测试 HTTPS
curl -I https://www.baidu.com

# 检查代理设置
echo $http_proxy
echo $https_proxy
```

**解决方案**:

| 问题 | 解决方案 |
|------|---------|
| 无法 ping 通 | 检查安全组是否允许 ICMP |
| DNS 解析失败 | 检查 `/etc/resolv.conf`，添加公共 DNS |
| HTTPS 连接失败 | 检查证书，或使用 `--insecure` 选项 |
| 代理问题 | 检查代理配置，或清除代理设置 |

### 5.2 内网服务问题

**症状**: 无法访问内部服务或 OSS

**诊断命令**:

```bash
# 测试 OSS 连接
curl -I https://oss-cn-hangzhou.aliyuncs.com

# 测试 PAI 服务
curl -I https://pai-dsw.cn-hangzhou.aliyuncs.com

# 检查 VPC 配置
# 需要在阿里云控制台检查
```

**解决方案**:

| 问题 | 解决方案 |
|------|---------|
| VPC 隔离 | 检查 VPC 配置，确保在同一 VPC |
| 安全组限制 | 检查安全组入站/出站规则 |
| 交换机问题 | 检查交换机配置 |

---

## 6. 凭证与权限问题

### 6.1 凭证获取失败

**症状**: 运行脚本提示 "No valid credentials found"

**诊断命令**:

```bash
# 检查环境变量
echo $ALIBABA_CLOUD_ACCESS_KEY_ID
echo $ALIBABA_CLOUD_ACCESS_KEY_SECRET
echo $ALIBABA_CLOUD_CREDENTIALS_URI

# 测试 RAM 角色凭证（在 DSW 实例中）
curl $ALIBABA_CLOUD_CREDENTIALS_URI
```

**解决方案**:

**场景 1: 在 DSW 实例中运行**

实例应该配置了 RAM 角色，自动获取凭证：

```bash
# 检查是否有 RAM 角色
curl http://100.100.100.200/latest/meta-data/ram/security-credentials/

# 如果返回为空，说明实例未配置 RAM 角色
# 需要在控制台为实例添加 RAM 角色
```

**场景 2: 在本地环境运行**

需要手动配置 AccessKey：

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID=<your-access-key-id>
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<your-access-key-secret>
export ALIBABA_CLOUD_REGION_ID=ap-southeast-1
export PAI_WORKSPACE_ID=<your-workspace-id>
```

### 6.2 权限不足

**症状**: API 返回 NoPermission 或 UnauthorizedOperation

**诊断步骤**:

1. 检查 RAM 角色或用户的权限策略
2. 确认是否有所需的 PAI 权限

**需要的权限**:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "pai-dsw:*"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstanceTypes"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 7. Python 环境问题

### 7.1 包冲突

**症状**: ImportError 或版本冲突

**诊断命令**:

```bash
# 检查包冲突
pip check

# 查看已安装包
pip list | grep <package-name>

# 检查包安装位置
pip show <package-name>
```

**解决方案**:

```bash
# 方案 1: 重新安装冲突的包
pip install --force-reinstall <package>

# 方案 2: 使用虚拟环境
python -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt

# 方案 3: 使用 conda 环境
conda create -n myenv python=3.10
conda activate myenv
```

### 7.2 CUDA 版本不匹配

**症状**: PyTorch/TensorFlow 无法使用 GPU

**诊断命令**:

```bash
# 检查 CUDA 版本
nvcc --version
nvidia-smi  # 显示驱动支持的 CUDA 版本

# 检查 PyTorch CUDA 版本
python -c "import torch; print(torch.version.cuda)"
```

**解决方案**:

```bash
# 安装匹配的 PyTorch 版本
# 访问 https://pytorch.org/get-started/locally/ 获取安装命令

# 例如 CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 例如 CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

---

## 8. API 调用失败排查

### 8.1 通用排查流程

```
1. 确认凭证有效
   - 检查环境变量
   - 测试凭证 URI

2. 确认网络连接
   - ping 服务端点
   - curl 测试 API

3. 确认参数正确
   - 检查区域 ID
   - 检查工作空间 ID
   - 检查实例 ID 格式

4. 检查错误信息
   - 查看完整错误消息
   - 对应错误代码表查找原因

5. 检查限流
   - 是否有大量请求
   - 是否需要添加重试逻辑
```

### 8.2 限流与重试机制

从 v2.1 版本开始，PAI-DSW Skill 内置了 API 限流处理模块，支持自动重试和请求限速。

#### 8.2.1 自动重试（默认启用）

当遇到以下错误时，系统会自动重试：
- `Throttling` / `Too Many Requests` (429)
- `ServiceUnavailable` (503)
- `InternalError` (500)
- `BadGateway` (502)
- `GatewayTimeout` (504)
- 网络连接错误

**使用方式**（已自动集成到 `create_client`）：

```python
from dsw_utils import create_client

# 默认启用限流和重试
client = create_client()

# 所有 API 调用自动带重试和限流
response = client.list_instances(request)
```

#### 8.2.2 手动使用限流模块

```python
from rate_limiter import with_retry, retry_api_call, RateLimiter, RetryStrategy

# 方式1: 装饰器
@with_retry(max_retries=3, backoff_factor=2.0)
def call_api():
    return client.some_method()

# 方式2: 直接调用
result = retry_api_call(
    lambda: client.list_instances(request),
    max_retries=3,
    backoff_factor=2.0,
)

# 方式3: 使用限速器（控制请求频率）
limiter = RateLimiter(rate_limit=10, period=1.0)  # 每秒最多10个请求
with limiter:
    response = client.some_method()
```

#### 8.2.3 环境变量配置

通过环境变量配置限流参数：

```bash
# 最大重试次数（默认: 3）
export DSW_MAX_RETRIES=5

# 退避因子（默认: 2.0）
export DSW_BACKOFF_FACTOR=2.0

# 基础延迟秒数（默认: 1.0）
export DSW_BASE_DELAY=1.0

# 最大延迟秒数（默认: 60.0）
export DSW_MAX_DELAY=60.0

# 每秒最大请求数（默认: 20）
export DSW_RATE_LIMIT=20

# 限流时间窗口秒数（默认: 1.0）
export DSW_RATE_PERIOD=1.0
```

#### 8.2.4 查看限流统计

```python
from dsw_utils import print_rate_limit_stats

# 打印统计信息
print_rate_limit_stats()

# 或直接获取统计对象
from rate_limiter import get_retry_stats
stats = get_retry_stats()
print(f"总调用: {stats.total_calls}")
print(f"成功: {stats.successful_calls}")
print(f"重试: {stats.total_retries}")
```

#### 8.2.5 重试策略说明

系统支持四种重试策略：

| 策略 | 说明 | 适用场景 |
|------|------|---------|
| `FIXED` | 固定间隔重试 | 简单场景 |
| `LINEAR` | 线性递增重试 | 预期快速恢复 |
| `EXPONENTIAL` | 指数退避重试 | 常规使用 |
| `JITTERED` | 带抖动的指数退避（默认） | 避免惊群效应 |

#### 8.2.6 自定义重试逻辑

如果需要更精细的控制，可以参考以下代码：

```python
import time
from rate_limiter import RetryStrategy, retry_api_call

# 使用指数退避策略
result = retry_api_call(
    lambda: client.list_instances(request),
    max_retries=5,
    backoff_factor=2.0,
    base_delay=0.5,
    max_delay=120.0,
    strategy=RetryStrategy.EXPONENTIAL,
    rate_limit=10,  # 每秒最多10个请求
    period=1.0,
)
```

### 8.3 调试技巧

**启用详细日志**:

```python
import logging

# 启用 SDK 调试日志
logging.basicConfig(level=logging.DEBUG)
```

**使用 --debug 参数**:

```bash
# 某些脚本支持 --debug 参数
python3 list_instances.py --debug
```

**检查请求响应**:

```python
# 在代码中打印请求详情
request = dsw_models.ListInstancesRequest(...)
print(f"Request: {request.__dict__}")

response = client.list_instances(request)
print(f"Response: {response.body.__dict__}")
```

---

## 9. 常见问题 FAQ

### Q1: 实例创建后无法连接

**A**: 
1. 等待几分钟让实例完全启动
2. 检查实例状态是否为 Running
3. 检查安全组是否允许访问
4. 尝试重启实例

### Q2: 快照创建失败

**A**:
1. 确保实例处于 Running 状态
2. 检查是否达到快照配额上限
3. 检查磁盘空间是否充足

### Q3: 成本估算不准确

**A**:
成本估算仅供参考，实际费用以阿里云账单为准。差异可能来自：
- 优惠券抵扣
- 预留实例折扣
- 跨月计费周期

### Q4: 批量操作部分失败

**A**:
1. 检查失败的实例状态
2. 查看具体错误信息
3. 使用 `--force` 参数跳过确认
4. 分批处理，避免并发过高

### Q5: 诊断报告显示有问题但实例运行正常

**A**:
诊断报告中的警告（黄色）通常不影响正常运行，但建议关注：
- 磁盘使用率超过 80% 建议清理
- 内存使用率高建议关注
- 包冲突可能导致潜在问题

### Q6: 更新规格后实例无响应

**A**:
1. 规格更新可能需要重启实例
2. 等待 5-10 分钟
3. 检查实例状态
4. 如仍然无响应，尝试重启

### Q7: 无法删除实例

**A**:
1. 确保实例已停止
2. 使用 `--force` 参数
3. 检查是否有快照依赖
4. 检查权限

---

## 附录: 诊断检查清单

当遇到问题时，按以下清单逐项检查：

- [ ] 实例状态是否正常？
- [ ] 磁盘空间是否充足？
- [ ] 内存使用是否过高？
- [ ] GPU 是否可用？
- [ ] 网络连接是否正常？
- [ ] 阿里云凭证是否有效？
- [ ] Python 环境是否有冲突？
- [ ] 是否有异常进程？
- [ ] 安全组配置是否正确？
- [ ] 工作空间 ID 是否正确？

---

## 联系支持

如果以上步骤都无法解决问题：

1. **阿里云工单**: 登录阿里云控制台，提交 PAI 产品工单
2. **文档参考**: [PAI-DSW 官方文档](https://help.aliyun.com/product/163395.html)
3. **收集诊断信息**:
   ```bash
   # 收集完整诊断信息
   ./dsw.py diagnose --json > diagnose.json
   ./dsw.py env --json > env.json
   ./dsw.py get <instance-id> > instance.txt
   ```

---

*最后更新: 2026-03-07*