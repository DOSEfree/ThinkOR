# 技术栈说明

## 选型结论

v0.1 采用 Python 主体路线。

推荐技术组合：

- FastAPI
- Pydantic
- Jinja2
- SQLite（如后续需要存储）
- pytest
- ruff
- mypy

------

## 为什么不在 v0.1 采用双栈

当前阶段的重点是验证产品价值，而不是优化前后端分离体验。

如果一开始同时引入 Next.js 与 FastAPI，会增加以下成本：

- 维护两套语言与工具链
- 增加 Agent 协作复杂度
- 增加初始化与部署复杂度
- 让早期迭代变慢

因此，v0.1 先坚持 Python 单栈更合理。

------

## 运行环境建议

当前确认的开发版本：

- Python `3.13`
- Conda 虚拟环境
- pip 负责项目依赖安装

当前说明：

- 你的系统 Python 仍然可以是 `3.14`
- 但项目开发、测试和 CI 统一以 Conda 中的 Python `3.13` 为准
- 这样可以减少解释器版本差异带来的依赖和类型检查噪音

------

## 依赖管理策略

初始化阶段默认使用：

- `conda` 创建虚拟环境
- `pip` 安装依赖

原因：

- 稳定
- 通用
- 无额外工具门槛

可选增强：

- 后续可引入 `uv` 提升依赖解析与安装速度
- 但不把它作为当前启动前置条件

------

## 核心依赖

### 运行时

- `fastapi`：Web API 框架
- `uvicorn`：本地开发与服务运行
- `pydantic`：输入输出模型
- `jinja2`：轻量页面模板
- `httpx`：HTTP 客户端

### 开发时

- `pytest`：测试
- `pytest-cov`：测试覆盖率
- `ruff`：格式化与静态检查
- `mypy`：类型检查

------

## 官方资料

以下均为官方文档，后续需要时可直接查阅：

- FastAPI: https://fastapi.tiangolo.com/
- uv: https://docs.astral.sh/uv/
- Ruff: https://docs.astral.sh/ruff/
- pytest: https://docs.pytest.org/en/stable/
- mypy: https://mypy.readthedocs.io/en/stable/

------

## 暂缓引入

以下技术先不进入 v0.1：

- Next.js
- Docker 强依赖
- PostgreSQL
- Celery / RQ
- Redis
- 向量数据库
- LangChain / 大型 Agent 框架

除非后续版本目标明确要求。
