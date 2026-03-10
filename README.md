# PAI-DSW Skill

一个完整的阿里云 PAI-DSW 实例管理技能，支持在 DSW 实例和本地环境中使用。

## 功能特性

### 实例管理
- 创建/启动/停止/删除实例
- 批量操作支持
- 实例详情查询

### 资源监控
- CPU/内存/GPU 使用率监控
- 资源趋势分析
- GPU 使用率告警

### 成本优化
- 成本估算
- 空闲自动关机
- 定时关机

### 运维诊断
- 实例诊断
- 故障排查指南
- 系统日志查询

### 智能推荐
- 实例规格推荐
- 多区域支持
- 标签管理

## 快速开始

### 在 DSW 实例中使用（推荐）

```bash
cd scripts
./dsw.py list
```

### 在本地环境使用

```bash
# 配置凭证
./dsw.py config init

# 按提示输入 AccessKey 和区域信息
```

## 主要命令

```bash
dsw list                    # 列出实例
dsw create                  # 创建实例
dsw start/stop/delete       # 实例操作
dsw gpu-usage               # GPU 使用率检查
dsw recommend               # 规格推荐
dsw diagnose                # 实例诊断
```

## 文档

- [SKILL.md](SKILL.md) - 完整使用文档
- [references/use-cases.md](references/use-cases.md) - 使用案例
- [references/troubleshooting.md](references/troubleshooting.md) - 故障排查

## 依赖

```bash
pip install alibabacloud-pai-dsw20220101 requests
```

## License

MIT
