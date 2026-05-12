[根目录](../CLAUDE.md) > **helm**

# Helm -- Kubernetes 部署配置

## 模块职责

提供 Clawith 应用的 Helm Chart，用于在 Kubernetes 集群中一键部署完整的生产环境。

## 入口与启动

- **Chart 定义**: `clawith/Chart.yaml` -- Chart 名称、版本（appVersion: 1.8.3-beta.2）
- **默认值**: `clawith/values.yaml` -- 全部可配置参数
- **快速指南**: `QUICKSTART.md`（中文）、`QUICKSTART_EN.md`（英文）

### 安装

```bash
helm install clawith ./clawith -n clawith --create-namespace
```

## 对外接口

Helm Chart 不直接对外提供 API，而是编排以下 Kubernetes 资源：

### 模板清单（`clawith/templates/`）

| 模板 | 说明 |
|------|------|
| `backend.yaml` | 后端 Deployment + Service |
| `frontend.yaml` | 前端 Deployment + Service |
| `postgresql.yaml` | PostgreSQL StatefulSet |
| `redis.yaml` | Redis StatefulSet |
| `ingress.yaml` | Ingress 路由规则 |
| `secrets.yaml` | 密钥管理 |
| `namespace.yaml` | 命名空间 |
| `storageclass.yaml` | 存储类 |
| `_helpers.tpl` | 模板辅助函数 |

## 关键依赖与配置

### values.yaml 主要配置项

| 配置 | 说明 | 默认值 |
|------|------|--------|
| `global.namespace` | 命名空间 | `clawith` |
| `global.imageRegistry` | 镜像仓库 | 用户自定义 |
| `backend.secrets.secretKey` | 应用密钥 | 需修改 |
| `backend.secrets.jwtSecretKey` | JWT 密钥 | 需修改 |
| `backend.persistence.size` | Agent 数据持久卷 | `10Gi` |
| `backend.env.agentDataDir` | Agent 数据目录 | `/data/agents` |

### 外部依赖

- Kubernetes 集群（1.20+）
- Helm 3
- StorageClass（用于持久卷）
- Ingress Controller（如 Nginx Ingress）

## 数据模型

不适用（纯部署配置）。

## 测试与质量

- `helm lint ./clawith` -- Chart 语法检查
- `helm template ./clawith` -- 渲染模板验证

## 常见问题 (FAQ)

**Q: 如何配置 HTTPS？**
A: 参考根目录 `HTTPS_GUIDE.md`。

**Q: 如何更新镜像版本？**
A: 修改 `values.yaml` 中的 `backend.image.tag` 和 `frontend.image.tag`，然后 `helm upgrade`。

## 相关文件清单

```
helm/
  clawith/
    Chart.yaml           # Chart 元数据
    values.yaml          # 默认配置值
    README.md            # Chart 说明
    templates/           # Kubernetes 模板
      _helpers.tpl
      backend.yaml
      frontend.yaml
      ingress.yaml
      namespace.yaml
      postgresql.yaml
      redis.yaml
      secrets.yaml
      storageclass.yaml
  QUICKSTART.md          # 中文快速入门
  QUICKSTART_EN.md       # 英文快速入门
```

## 变更记录 (Changelog)

| 时间 | 操作 | 说明 |
|------|------|------|
| 2026-05-07T13:40:31 | 初始化 | 首次生成模块文档 |
