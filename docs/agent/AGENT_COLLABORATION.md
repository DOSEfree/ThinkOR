# Agent 协作说明

## 默认协作方式

在本项目中，Agent 的首要职责是协助推进项目，而不是擅自重定义项目。

默认行为要求：

- 修改前先说明计划
- 由你拍板后再执行关键改动
- 每次变更保持最小化
- 优先遵守项目文档

------

## 文档优先级

从高到低建议如下：

1. `docs/strategy/VISION.md`
2. `docs/product/PRODUCT.md`
3. `docs/planning/ROADMAP.md`
4. `docs/engineering/ARCHITECTURE.md`
5. `docs/engineering/TECH_STACK.md`
6. `docs/engineering/CODE_STYLE.md`
7. 代码实现

------

## 输出风格

Agent 在完成一次任务后，应尽量明确输出：

- 修改了哪些文件
- 为什么要这样改
- 潜在风险
- 测试结果

------

## 沟通风格

- 默认使用中文
- 尽量避免空泛建议
- 优先给出可执行的下一步
- 发现歧义时先暂停并确认

------

## 环境约定

- 项目默认开发环境为 Conda 环境 `ideaos-agent`
- Agent 在执行任何 Python 相关命令前，应先确认当前终端不在 `base`，且已切换到 `ideaos-agent`
- 适用命令包括：依赖安装、`pytest`、`ruff`、`mypy`、`uvicorn`、诊断脚本与其他项目级 Python 命令
- 如需核验，优先检查 `CONDA_DEFAULT_ENV`、`python --version` 与 `python` 可执行文件路径
- 项目文档、测试与 CI 的 Python 基线统一为 `3.13`

------

## 变更边界

未经明确批准，不应主动做以下事情：

- 引入新框架
- 重构大量无关代码
- 擅自改变文档定义的产品边界
- 引入多 Agent、长期记忆或复杂编排能力
