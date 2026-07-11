# 技术栈说明

## 选型结论

当前稳定版本继续采用 Python 主体路线。

推荐技术组合：

- FastAPI
- Pydantic
- Jinja2
- SQLite（当前已用于本地会话索引与结构化快照存储）
- python-dotenv
- pytest
- ruff
- mypy

------

## 为什么当前仍不采用双栈

当前阶段的重点是验证产品价值，而不是优化前后端分离体验。

如果一开始同时引入 Next.js 与 FastAPI，会增加以下成本：

- 维护两套语言与工具链
- 增加 Agent 协作复杂度
- 增加初始化与部署复杂度
- 让早期迭代变慢

因此，当前阶段继续坚持 Python 单栈更合理。

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
- 项目默认开发环境名为 `ideaos-agent`；新终端即使先进入 `base`，在执行项目命令前也应切换到该环境

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
- `python-dotenv`：本地 `.env` 环境变量加载
- `sqlite3`：Python 标准库内建，本地会话索引与快照存储的底层支撑

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

以下技术当前仍不进入最小稳定版本：

- Next.js
- Docker 强依赖
- PostgreSQL
- Celery / RQ
- Redis
- 向量数据库
- LangChain / 大型 Agent 框架

除非后续版本目标明确要求。
