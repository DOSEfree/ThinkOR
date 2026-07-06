# Changelog

本项目采用人工维护的变更日志。

记录原则：

- 只记录已经进入主线的重要变化
- 以版本为单位归档
- `Unreleased` 只存放尚未发布、但已确认会进入下一版的事实性改动

## [Unreleased]

- 暂无

## [0.2.0] - 2026-07-06

### Added

- 引入会话归档领域模型 `ArchiveStatus / SessionRecord` 与会话编排服务，补齐 `session_id / archive_status / archive_url` 契约。
- 接入本地 `SQLite` 归档索引存储，默认落盘到 `data/ideaos_agent.db`，支持最小会话记录的创建、更新与查询。
- 补充 `session_id` 续传、会话状态编排与 `SQLite` 存储层的测试覆盖。
- 新增飞书归档契约 `SessionArchiver / SessionArchivePayload / ArchiveResult`，并接入基于 `lark-cli` 的 Feishu Docx 归档适配。
- 新增飞书归档 XML 渲染器与本地 `fake` 归档器，支持在不写入真实飞书文档的情况下完成测试与本地联调。
- 新增前端归档状态面板，支持在 `/app` 中展示 `session_id / archive_status / archive_title / archive_url`，并在归档成功时提供飞书文档打开入口。

### Changed

- 拆分 LLM 输出模型与 API 响应模型，避免会话归档元数据进入 prompt 或 fake client。
- 调整前端单轮澄清流程：首次响应保存 `session_id`，二次“补充并重新分析”请求原样带回。
- 新增 `IDEAOS_ARCHIVE_DB_PATH` 配置项，并补充本地归档数据库文件的忽略规则。
- 完成态会话现在会在写入本地 `SQLite` 索引后同步尝试飞书归档，并将结果回写为 `succeeded / failed`，同时保证归档失败不阻塞主分析结果返回。
- 补充 `archive_title` 语义标题字段与 `IDEAOS_USE_FAKE_ARCHIVE`、`IDEAOS_FEISHU_*` 配置项，用于控制飞书标题策略、CLI 调用方式、归档位置与超时行为。
- 结果区占位文案与前端脚本已更新为归档感知版本，并补充静态资源 smoke test，确保归档状态展示逻辑随页面一同交付。

### Fixed

- 修复 Windows 环境下真实飞书归档调用 `lark-cli` 时的命令解析问题：归档器现在会先解析可执行文件真实路径，避免 `subprocess.run(["lark-cli", ...])` 找不到 `.cmd` 包装器而直接失败。
- 修复 Windows 环境下飞书归档中文乱码问题：归档器调用 `lark-cli` 时现在显式使用 `UTF-8` 传输 XML 内容，避免运行中 Python 进程落回系统默认编码后将中文写成乱码。

## [0.1.0] - 2026-07-05

### Added

- 建立项目愿景、产品定义、路线图与 Python 主体工程基线。
- 建立单次想法分析主链路，完成从输入校验、提示词构建、LLM 调用到结构化输出的端到端闭环。
- 引入分层后端结构：`api / application / domain / infrastructure / prompts`。
- 实现假设透明化与单轮澄清交互模型，支持“澄清态 / 正式分析态”两档输出。
- 提供最小可运行 Web 界面 `/app`，承接想法输入、澄清补充与分析结果展示。
- 支持真实 LLM 接口与本地 fake client 两种运行方式。

### Changed

- 将开发基线统一为 `conda + Python 3.13 + pip`。
- 将项目状态文档调整为以 `v0.x` 为主的版本化表达。
- 将默认交互校准为“信息不足时才澄清”，并补齐 `input_echo` 契约。
- 优化 `/app` 页面结构与九个分析模块的展示布局。
- 明确项目默认开发环境为 `ideaos-agent`。

### Fixed

- 修复 `TestClient/httpx` 兼容性 warning。
- 统一文本文件换行策略为 `LF`，补齐 `.gitattributes` 与 `.editorconfig`。
- 补充 `.gitignore` 对本地工程产物的忽略规则。

### Removed

- 删除未使用的本地 `issue/` 目录。
