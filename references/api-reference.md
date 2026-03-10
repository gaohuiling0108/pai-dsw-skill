# PAI-DSW API Reference

## 实例快照（自定义镜像）API

### CreateInstanceSnapshot - 创建实例快照
**用途**: 将现有DSW实例保存为自定义镜像，用于后续创建相同环境的实例。

**必需参数**:
- `InstanceId`: 源实例ID
- `SnapshotName`: 快照名称（仅支持小写字母、数字和中横线）
- `ImageUrl`: 目标镜像地址

**可选参数**:
- `SnapshotDescription`: 快照描述
- `Overwrite`: 是否覆盖已存在的镜像tag
- `ExcludePaths`: 排除的文件路径列表
- `Labels`: 用户自定义标签

**ImageUrl格式**:
```
dsw-registry-vpc.{region}.cr.aliyuncs.com/{namespace}/{repository}:{tag}
```

**示例**:
- Registry: `dsw-registry-vpc.cn-beijing.cr.aliyuncs.com`
- Namespace: `pai` 
- Repository: `openclawtestsave`
- Tag: `openclawtestsave`
- 完整URL: `dsw-registry-vpc.cn-beijing.cr.aliyuncs.com/pai/openclawtestsave:openclawtestsave`

### 其他快照相关API
- `ListInstanceSnapshot`: 列出快照
- `GetInstanceSnapshot`: 获取快照详情  
- `DeleteInstanceSnapshot`: 删除快照

## 实例管理API

### CreateInstance - 创建实例
**关键参数**:
- `instance_name`: 实例名称
- `ecs_spec`: 实例规格 (如: ecs.g6.large)
- `image_url`: 镜像URL
- `workspace_id`: 工作空间ID

**镜像URL格式**:
1. **官方镜像**: `dsw-registry-vpc.cn-beijing.cr.aliyuncs.com/pai/modelscope:1.34.0-pytorch2.9.1-gpu-py311-cu124-ubuntu22.04`
2. **自定义镜像**: `dsw-registry-vpc.cn-beijing.cr.aliyuncs.com/pai/{snapshot_name}:{snapshot_name}`

### DeleteInstance - 删除实例
### StartInstance - 启动实例  
### StopInstance - 停止实例
### GetInstance - 获取实例详情

## 工作空间信息
- **当前工作空间ID**: 349330
- **区域**: cn-beijing

## 鉴权方式
- **推荐**: 使用RAM角色临时凭证
- **凭证URI**: `ALIBABA_CLOUD_CREDENTIALS_URI`
- **包含字段**: AccessKeyId, AccessKeySecret, SecurityToken