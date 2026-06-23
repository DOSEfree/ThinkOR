# IdeaOS-Agent

IdeaOS-Agent 是一个面向想法孵化阶段的 Idea Development System。

它的目标不是成为通用聊天助手，而是帮助用户把一个模糊想法拆解为可执行的下一步计划。

## 当前阶段

当前仓库处于 `v0.1` 初始化阶段，重点工作包括：

- 明确产品边界
- 固化 Python 主体技术栈
- 建立文档与协作规则
- 建立 GitHub 项目管理与版本管理基线
- 建立最小可运行服务入口与环境变量约定

## v0.1 核心能力

面向单次输入的想法分析，逐步输出以下模块：

1. 想法摘要
2. 可行性分析
3. 市场判断
4. 知识缺口分析
5. 资源缺口分析
6. 团队需求分析
7. 相似项目参考
8. MVP 路线图
9. 长期发展路线图

## 项目原则

- Agent 服务于 Idea，不反客为主
- 优先简单架构，避免过度设计
- 优先可解释性、可维护性与可验证性
- 先验证价值，再追求复杂功能

## 文档导航

- [项目愿景](docs/strategy/VISION.md)
- [产品定义](docs/product/PRODUCT.md)
- [开发路线图](docs/planning/ROADMAP.md)
- [系统架构](docs/engineering/ARCHITECTURE.md)
- [技术栈说明](docs/engineering/TECH_STACK.md)
- [代码风格](docs/engineering/CODE_STYLE.md)
- [协作规范](docs/management/GITHUB_WORKFLOW.md)
- [Agent 协作说明](docs/agent/AGENT_COLLABORATION.md)

## 环境准备

当前推荐环境：

- Conda 虚拟环境
- Python `3.13`
- Windows PowerShell、macOS Terminal 或 Linux Shell
- `pip` 作为默认依赖安装方式

说明：

- 项目当前以 Python `3.13` 作为主开发与 CI 基线。
- 后续如果需要，也可以评估 `uv`，但初始化阶段先保持 `conda + pip` 的低门槛方案。

## 初始化命令

```powershell
conda create -n ideaos-agent python=3.13
conda activate ideaos-agent
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## 本地运行

复制环境变量示例文件后，可以启动最小服务：

```powershell
copy .env.example .env
python -m uvicorn ideaos_agent.main:app --reload
```

默认健康检查地址：

- `http://127.0.0.1:8000/health`

## 质量检查

```powershell
python -m pytest
python -m ruff check .
python -m ruff format .
python -m mypy src
```

## 初始化收尾清单

除了关联 GitHub 仓库之外，当前初始化阶段还应确认以下事项：

- 最小 FastAPI 服务可以在本地启动
- `.env.example` 已覆盖当前环境变量约定
- `pytest`、`ruff`、`mypy` 能在 Python `3.13` 环境中通过
- 清理本地生成物后再初始化 Git，保证首次提交足够干净

## 版本管理

项目版本变更统一记录在根目录的 [CHANGELOG.md](CHANGELOG.md)。
