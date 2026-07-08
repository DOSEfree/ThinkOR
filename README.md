# IdeaOS-Agent

IdeaOS-Agent 是一个面向想法孵化阶段的 Idea Development System。

它的目标不是成为通用聊天助手，而是帮助用户把一个模糊想法拆解为可执行的下一步计划。

## 当前阶段

当前仓库已完成 `v0.3.0` 的收口，当前稳定能力重点包括：

- 保留 `v0.1` 已验证完成的单次分析链路与单轮澄清模型
- 完成 `v0.2.0` 的 `session_id / archive_status / archive_url` 归档闭环与本地 `SQLite + Feishu` 双层状态
- 完成 `v0.2.5` 的 bounded follow-up、局部完善结果与新版完整方案合成
- 完成 `v0.3.0` 的本地历史记录列表、thread 导航、历史详情查看与从任意已完成节点继续 follow-up
- 在飞书归档正文中补充 thread context，明确根会话、父节点与当前会话角色

当前仍然明确延后的能力：

- Feishu 子文档 / Wiki 层级组织：延后到后续版本再评估
- 自动跨会话长期记忆：仍然不是当前产品目标

当前规划状态：

- `v0.3.0` 已作为独立发布分支收口
- 下一阶段候选主题为 `v0.4.0`：`Frontend Interaction / Layout Refresh`

## 当前核心能力

面向单次输入的想法分析，系统仍逐步输出以下九个分析模块：

1. 想法摘要
2. 可行性分析
3. 市场判断
4. 知识缺口分析
5. 资源缺口分析
6. 团队需求分析
7. 相似项目参考
8. MVP 路线图
9. 长期发展路线图

在上述分析完成后，当前版本还会补充以下归档能力：

- 首次请求生成并返回 `session_id`，用于串联“原始输入 + 单轮澄清 + 最终分析”
- 完成态分析自动写入本地 `SQLite` 索引，记录 `archive_status`
- 归档成功时返回 `archive_url`，可直接打开飞书文档
- 归档失败不阻塞主分析结果返回

在 `v0.3.0` 中，当前版本还补充了以下显式历史能力：

- 查询最近完成的本地 sessions
- 查看同一条 idea thread 的父子链路
- 打开任意已完成历史节点的详情结果
- 从任意允许继续的历史节点显式发起 follow-up

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

- `/app`：极简可用前端界面，可直接输入想法、回答澄清问题、查看分析结果与归档状态
- `/api/v1/idea-analysis`：后端 JSON 接口，返回分析内容以及 `session_id / archive_status / archive_url`
- `/api/v1/follow-up/refine`：基于已完成 session 发起一次有界的 follow-up 完善
- `/api/v1/follow-up/compose-full-plan`：在用户确认局部修改后生成新版完整方案
- `/api/v1/sessions`：查询最近完成的本地历史 session
- `/api/v1/sessions/{session_id}`：查看某个历史 session 的完整详情
- `/api/v1/threads`：查询本地 idea thread 摘要列表
- `/api/v1/threads/{root_session_id}`：查看某条 thread 的链路节点

归档相关说明：

- `IDEAOS_USE_FAKE_LLM=true` 可在本地使用 fake LLM 体验完整分析流程
- `IDEAOS_USE_FAKE_ARCHIVE=true` 可在不写入真实飞书的情况下联调归档链路
- 如需启用真实飞书归档，请确保 `lark-cli` 已安装并完成登录

## 质量检查

```powershell
python -m pytest
python -m ruff check .
python -m ruff format .
python -m mypy src
```

## v0.3.0 收口检查

当前阶段建议至少确认以下事项：

- 最小 FastAPI 服务可以在本地启动
- `.env.example` 已覆盖当前环境变量约定
- `pytest`、`ruff`、`mypy` 能在 Python `3.13` 环境中通过
- 完成态分析会返回 `session_id / archive_status / archive_url`
- 开启真实飞书归档后，可为同一会话生成文档并返回链接
- 基于当前结果发起 follow-up 时，可得到局部完善结果并继续归档
- 用户确认修改后，可生成新版完整方案且不覆盖原 session
- `/app` 中可查看最近历史记录、当前 thread，并从历史节点继续 follow-up
- 飞书归档正文可展示根会话、父节点与 thread context

## 下一阶段

`v0.4.0` 将优先评估与推进以下方向：

- 前端交互布局重整
- 历史 / 结果 / follow-up 区的信息层级优化
- 更顺手的状态反馈、按钮动作与阅读体验

这些优化会继续遵守当前产品边界：显式历史导航，不等于自动长期记忆，也不引入长期对话产品形态。

## 版本管理

项目版本变更统一记录在根目录的 [CHANGELOG.md](CHANGELOG.md)。
