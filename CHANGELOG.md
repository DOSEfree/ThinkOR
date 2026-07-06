# Changelog

本项目采用人工维护的变更日志。

记录原则：

- 只记录已经进入主线的重要变化
- 以版本为单位归档
- `Unreleased` 只存放尚未发布、但已确认会进入下一版的事实性改动

## [Unreleased]

暂无已确认条目。

## [0.2.5] - 2026-07-06

### Added

- 新增 `v0.2.5` follow-up 领域模型与 API 契约，包括 `SessionKind / SessionSnapshot / RefinementResult / FollowUpResponse / ComposedPlanResponse`，用于承接“基于已归档结果继续完善方案”的最小闭环。
- 新增 follow-up 应用层服务与接口：`POST /api/v1/follow-up/refine` 用于生成局部完善结果，`POST /api/v1/follow-up/compose-full-plan` 用于在用户确认后合成新版完整方案。
- 新增本地 `SQLite` 结构化快照存储 `session_snapshots`，并为会话索引补充 `parent_session_id / session_kind` 字段，支持沿父 session 继续推理。
- 新增 follow-up 归档模板与飞书文档渲染能力，支持归档 `analysis / follow_up_refinement / full_plan_composed` 三类 session，并在正文中保留逻辑父子关系信息。
- 新增 follow-up 单测覆盖，验证局部完善结果生成、父子 session 关系保存、完整方案合成以及归档适配行为。

### Changed

- 根分析链路在完成态时现在会额外保存结构化 analysis snapshot，而不只是最小归档索引，为 `v0.2.5` follow-up 提供可靠的本地状态来源。
- 本地 fake LLM 与响应解析逻辑已扩展到 follow-up 场景，可在不依赖真实模型的情况下稳定演示“继续完善 -> 澄清 -> 合成完整方案”的交互。
- 前端 `/app` 已加入“继续完善方案”和“确认修改并生成新版完整方案”入口，并支持从当前展示结果继续发起下一轮 follow-up。
- 前端结果区现在会区分完整分析、局部完善结果与归档状态，并按当前操作显示对应的加载状态，避免多按钮场景下交互含混。

### Fixed

- 修复真实 LLM 在 follow-up 场景下偶发返回单对象或 `null` 数组字段时的解析脆弱性；本地解析器现在会对 `proposed_section_updates / affected_sections / next_actions` 等字段做最小兼容纠偏。
- 修复前端在 follow-up 请求失败时将当前结果区整体隐藏的问题；现在错误信息会单独显示，已生成的分析或局部完善结果会继续保留在页面中便于人工调试。
- 修复重复点击“继续完善方案”会不断插入新的输入面板的问题；当前实现会复用已打开的 follow-up 编辑区，并阻止重复提交。
- 修复 follow-up 输出板块标题与标签展示不一致的问题，统一为可读的中英文标题格式，避免直接暴露底层字段名。

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
