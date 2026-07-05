# IdeaOS-Agent

IdeaOS-Agent 是一个面向想法孵化阶段的 Idea Development System。

它的目标不是成为通用聊天助手，而是帮助用户把一个模糊想法拆解为可执行的下一步计划。

## 当前阶段

当前仓库已经具备代表 `v0.1` 当前稳定状态的最小闭环，重点成果包括：

- 明确产品边界与交互模型主线
- 固化 Python 主体技术栈与工程基线
- 建立文档、版本日志与 GitHub 协作规则
- 跑通单次分析链路与无状态单轮澄清链路
- 提供最小可运行 Web 界面与项目级环境约定

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
- 后续如果需要，也可以评估 `uv`，但当前阶段先保持 `conda + pip` 的低门槛方案。

## 初始化命令

```powershell
conda create -n ideaos-agent python=3.13
conda activate ideaos-agent
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## 环境约定

本项目默认开发环境为 Conda 环境 `ideaos-agent`。

说明：

- 新开 PowerShell 终端时，系统仍可能先落在 `base`，这不代表项目环境配置有误
- 进入本项目后，如需运行 `pytest`、`ruff`、`mypy`、`uvicorn`、诊断脚本或依赖安装命令，应先切换到 `ideaos-agent`
- 推荐在执行命令前快速确认当前环境，例如检查 `CONDA_DEFAULT_ENV` 是否为 `ideaos-agent`
- 项目开发、测试与 CI 的 Python 基线统一为 `3.13`

## 本地运行

复制环境变量示例文件后，可以启动最小服务：

```powershell
copy .env.example .env
python -m uvicorn ideaos_agent.main:app --reload
```

默认健康检查地址：

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/app`
- 项目会自动读取根目录 `.env`，因此真实 `API key` 只需保存在本地 `.env` 中，不会进入 GitHub 版本管理

当前入口说明：

- `/app`：极简可用前端界面，可直接输入想法、回答澄清问题并查看分析结果
- `/api/v1/idea-analysis`：后端 JSON 接口，供前端或后续外部调用使用

## 质量检查

```powershell
python -m pytest
python -m ruff check .
python -m ruff format .
python -m mypy src
```

## v0.1 收口检查

当前阶段建议至少确认以下事项：

- 最小 FastAPI 服务可以在本地启动
- `.env.example` 已覆盖当前环境变量约定
- `pytest`、`ruff`、`mypy` 能在 Python `3.13` 环境中通过
- `main` 分支能够代表当前稳定主线，并承接后续 `v0.2` 规划

## 版本管理

项目版本变更统一记录在根目录的 [CHANGELOG.md](CHANGELOG.md)。
