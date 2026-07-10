# Changelog

本项目采用人工维护的变更日志。

记录原则：
- 只记录已经进入主开发线的重要变化
- 以版本为单位归档
- `Unreleased` 仅记录已确认会进入下一版的事实性改动

## [Unreleased]

### Added

- Added local-only formal history search for `v0.4.5`: the sidebar search now filters local thread history through `/api/v1/threads?q=...`, matches key local idea fields such as titles, root idea content, and formal summaries, and intentionally excludes follow-up draft cache plus any external search source.
- Added non-root formal leaf deletion for `v0.4.5`: `DELETE /api/v1/sessions/{session_id}` now removes one formal leaf version, cascade-cleans any attached local follow-up draft cache, best-effort deletes linked Feishu archives, and returns the parent fallback node for the UI.

### Changed

- Aligned package metadata with the released `v0.4.0` state by updating both `pyproject.toml` and `ideaos_agent.__version__` from `0.2.0` to `0.4.0`.
- Refined the sidebar history presentation for `v0.4.5`: time-bucket labels now follow the updated mockup scale, summary cards use tighter corners with full-wrap shadow, long thread titles truncate after 10 characters with an ellipsis, the `历史记录 / HISTORY` row is vertically centered with the action buttons, and the workspace `IdeaOS-Agent` title uses a lighter weight.
- Continued the `v0.4.5` frontend polish pass: widened the sidebar without affecting workspace centering, repositioned the thread expand chevron and reserved scrollbar rail space, flipped the collapse icon in collapsed state, kept analysis section indices and titles on one line, converted blue-accent side-strip cards to square corners, simplified expanded version labels to `V01 ROOT / V02`, and softened the success-state status/archive card treatments.
- Continued the `v0.4.5` sidebar micro-polish pass: unified the five history action buttons to a smaller shared size, enlarged and left-shifted the expand chevron for readability, rebalanced analysis indices with their titles, and moved the scrollbar rail farther right so card shadows read cleanly.
- Continued the `v0.4.5` sidebar detail polish: bottom-aligned the top history controls with the `历史记录 / HISTORY` title block, unified the `Latest / Updated` metadata treatment, and aligned version badges plus analysis indices more consistently.
- Locked the `v0.4.5` implementation plan before code work begins: local history search stays local-only and formal-only, node deletion is constrained to non-root leaves, and branch follow-up keeps linear sidebar history with global version increments plus explicit relationship markers.
- Implemented the `v0.4.5` linear branch follow-up semantics: formal history nodes now persist stable global version numbers in SQLite, expanded sidebar versions expose lightweight parent markers such as `from V01`, and `CURRENT THREAD` now shows explicit `root / parent / current / chain` context without switching the sidebar to a tree-aware layout.
- Exposed leaf-delete state directly in formal history responses for `v0.4.5`: history items now declare whether a version is individually deletable plus the block reason, so the sidebar can hide ROOT single-delete, disable non-leaf delete, and safely fall back to the parent version after a successful delete.

### Fixed

- Removed the stray `httpx2` dev dependency residue from `pyproject.toml`.
- Added a metadata regression test so package version drift and `httpx2`-style dependency residue are caught earlier.

## [0.4.0] - 2026-07-09

### Added

- Added thread-level deletion for grouped history in `v0.4.0`: `DELETE /api/v1/threads/{root_session_id}` now removes local SQLite history and best-effort deletes linked Feishu archives.
- Added a real sidebar delete action for history folders in `v0.4.0`, so users can remove one local idea thread from the web UI and simultaneously attempt Feishu cleanup.
- Added one-way remote deletion sync for `v0.4.0`: clicking the sidebar refresh button now triggers `POST /api/v1/threads/sync-remote-archives` so locally archived sessions disappear automatically after their Feishu docs have been manually removed.
- Added recoverable follow-up draft metadata to session detail responses: formal history nodes can now expose `active_follow_up_draft_id / question / updated_at` so the UI can restore an unfinished refinement draft within the retention window.
- 为 `v0.4.0` 前端改版接入新的页面壳层，`/app` 现已具备 `Topbar + Sidebar + Workspace` 三段式结构。
- 新增前端静态资源目录 `src/ideaos_agent/presentation/static/assets/logo/`，将 `IdeaOS_logo / search / close / user` 四张图片纳入应用静态服务路径。
- 新增空状态边界提示条，明确展示 `Single Analysis / One Clarification / Feishu Archive` 三条当前产品边界。
- 新增 workspace 内的 `thread context` 面板壳层与对应前端挂点，使 `CURRENT THREAD / 当前链路` 可在结果区上方作为显式上下文展示。
- 新增针对 `v0.4.0` 前端壳层、样式 token、thread context 挂点与 logo 资源的 smoke test。

### Changed

- Refined the `v0.4.0` sidebar history experience so `历史记录 / HISTORY` stays on one line, the refresh icon reads more clearly, and expanded thread versions stop repeating the same root title on every child card.
- Changed follow-up refinement persistence semantics: completed `follow_up_refinement` sessions now stay as local draft cache for 7 days by default instead of immediately becoming formal archived history versions.
- Changed formal history/thread views so the left sidebar only counts and displays formal versions (`analysis` and `full_plan_composed`), while draft recovery is surfaced from the parent formal session detail.
- Changed compose flow parent-link semantics so consuming a cached refinement draft creates a new formal version directly under the previous formal session and deletes the used draft snapshot afterward.
- 调整左侧刷新按钮语义：当前仅在用户主动点击刷新时，页面才会向飞书执行一次远端归档存在性探测并同步清理本地历史，不引入实时监听或飞书恢复反向回填。
- 重构 `/static/swiss.css` 的设计令牌，统一采用 `#002FA7 / #7E8289 / #F9FAFB / #FFFFFF` 作为 `v0.4.0` 首版视觉基准，并将字体优先链切换为 `OPPOSans M / OPPOSans B`。
- 调整 `/app` 页面结构，使既有分析、归档、history、follow-up 逻辑继续可挂载在新前端骨架上，而不改动后端 API 契约。
- 重做工作区输入体验：首页现采用更聚焦的 hero 式输入台，而进入分析、错误或历史详情后会自动切换为更紧凑的 active workspace 模式。
- 将 `recent sessions` 正式收敛到左侧侧栏，并把 `CURRENT THREAD / 当前链路` 从侧栏迁移到 workspace 内的上下文面板。
- 同步调整左侧历史列表、线程节点卡片、前端事件委托与 smoke test，适配新的 `sidebar-only history + workspace thread context` 结构。
- 重做结果区阅读与状态反馈：`result-shell` 现已接入 workspace 级 busy banner、`aria-busy` 状态与按钮级 loading 同步反馈，统一分析 / 澄清 / follow-up / archive 卡片的视觉层级。
- 优化 `/app` 的空状态、错误态、归档反馈与移动端排版，补充结果占位提示卡、状态说明文案与响应式间距收口，同时保留失败时已生成结果继续可见的调试体验。
- 调整 `/app` 桌面端双栏滚动边界：recent sessions 现在固定在左侧栏内独立滚动，workspace 不再被历史列表长度撑高；移动端单列布局仍保留自然页面滚动。
- 进一步收敛 `/app` 首屏信息密度：移除顶栏重复用户名标签与左栏冗余说明，保留侧栏搜索占位和折叠入口，并收紧左侧历史卡片宽度与滚动边界，避免出现横向滚动条。
- 将左侧历史记录升级为按 `idea thread` 展示的“文件夹 + 版本展开”视图，补回 `7天内 / 30天内 / YYYY-MM` 时间分组，并为后续后端删除能力预留前端占位入口。

### Fixed

- Strengthened `v0.4.0` Feishu deletion sync: refresh-time archive probing now uses a lightweight `docs +fetch` presence check instead of URL inspection alone, so documents moved into the Feishu recycle bin are treated as deleted and removed from local history on the next manual refresh.
- Fixed legacy history thread expansion for rows with blank stored `root_session_id`: thread/detail/delete behavior now resolves root relationships from loaded snapshots instead of depending on older SQLite rows having complete root metadata.
- Reduced the sidebar refresh icon size by about 10% to keep it visually aligned with the other toolbar controls.
- Replaced the sidebar refresh glyph with the new `refresh.png` asset and stopped rendering `SUCCEEDED` badges on history cards so completed threads read more cleanly.
- Isolated pytest from the developer's real `data/ideaos_agent.db` by forcing a temporary SQLite path plus fake LLM/archive defaults during tests, preventing local history pollution from integration runs.

## [0.3.0] - 2026-07-08

### Added

- 新增面向 `v0.3.0` 的 idea thread 聚合能力：会话记录、结构化快照、API 响应与本地 `SQLite` 均补充 `root_session_id`，用于将 `analysis / follow_up_refinement / full_plan_composed` 串联为同一条想法链路。
- 新增本地历史查询能力：提供 `GET /api/v1/sessions`、`GET /api/v1/sessions/{session_id}`、`GET /api/v1/threads`、`GET /api/v1/threads/{root_session_id}`，支持查看最近 session、单个详情与 thread 链路。
- 新增 `/app` 历史导航界面，包括 recent sessions、current thread、历史详情加载，以及从任意允许继续的历史节点直接发起 follow-up 的入口。
- 新增 Feishu 归档 thread context，归档 payload 支持 `root_session_id / root_archive_url`，归档正文可展示根会话、父节点与当前节点在链路中的角色。

### Changed

- 历史记录能力继续保持显式导航边界，而不是自动把历史内容 silent 注入下一轮 prompt。
- follow-up 可从当前结果或任意允许继续的历史节点显式发起，但仍保持 bounded refinement 与用户确认后再合成完整方案的交互模型。
- 前端历史按钮、局部完善结果区与归档展示文案进一步统一为中英双语，便于在历史 / 结果混合场景下阅读与操作。

### Fixed

- 修复本地 fake LLM 在 follow-up 场景中对 prompt 形态判断不稳定的问题，避免把 follow-up 请求误判回根分析链路。
- 修复归档链路在 Windows 环境下的中文渲染与线程上下文传递细节，保证飞书文档正文可稳定展示中文与 thread metadata。

## [0.2.5] - 2026-07-06

### Added

- 新增 `v0.2.5` follow-up 领域模型与 API 契约，包括 `SessionKind / SessionSnapshot / RefinementResult / FollowUpResponse / ComposedPlanResponse`，用于承接“基于已归档结果继续完善方案”的最小闭环。
- 新增 follow-up 应用层服务与接口：`POST /api/v1/follow-up/refine` 用于生成局部完善结果，`POST /api/v1/follow-up/compose-full-plan` 用于在用户确认后合成新版本完整方案。
- 新增本地 `SQLite` 结构化快照存储 `session_snapshots`，并为会话索引补充 `parent_session_id / session_kind` 字段，支持沿父 session 继续推理。
- 新增 follow-up 归档模板与飞书文档渲染能力，支持归档 `analysis / follow_up_refinement / full_plan_composed` 三类 session，并在正文中保留逻辑父子关系信息。
- 新增 follow-up 单测覆盖，验证局部完善结果生成、父子 session 关系保存、完整方案合成以及归档适配行为。

### Changed

- 根分析链路在完成态时现在会额外保存结构化 analysis snapshot，而不只是最小归档索引，为 `v0.2.5` follow-up 提供可靠的本地状态来源。
- 本地 fake LLM 与响应解析逻辑已扩展到 follow-up 场景，可在不依赖真实模型的情况下稳定演示“继续完善 -> 澄清 -> 合成完整方案”的交互。
- 前端 `/app` 已加入“继续完善方案”和“确认修改并生成新版本完整方案”入口，并支持从当前展示结果继续发起下一轮 follow-up。
- 前端结果区现在会区分完整分析、局部完善结果与归档状态，并按当前操作显示对应的加载状态，避免多按钮场景下交互混乱。

### Fixed

- 修复真实 LLM 在 follow-up 场景下偶发返回单对象或 `null` 数组字段时的解析脆弱性；本地解析器现在会对 `proposed_section_updates / affected_sections / next_actions` 等字段做最小兼容纠偏。
- 修复前端在 follow-up 请求失败时将当前结果区整体隐藏的问题；现在错误信息会单独显示，已生成的分析或局部完善结果会继续保留在页面中便于人工调试。
- 修复重复点击“继续完善方案”会不断插入新的输入面板的问题；当前实现会复用已打开的 follow-up 编辑区，并阻止重复提交。
- 修复 follow-up 输出板块标题与标签显示不一致的问题，统一为可读的中英文标题格式，避免直接暴露底层字段名。

## [0.2.0] - 2026-07-06

### Added

- 引入会话归档领域模型 `ArchiveStatus / SessionRecord` 与会话编排服务，补齐 `session_id / archive_status / archive_url` 契约。
- 接入本地 `SQLite` 归档索引存储，默认落盘到 `data/ideaos_agent.db`，支持最小会话记录的创建、更新与查询。
- 补充 `session_id` 续传、会话状态编排与 `SQLite` 存储层的测试覆盖。
- 新增飞书归档契约 `SessionArchiver / SessionArchivePayload / ArchiveResult`，并接入基于 `lark-cli` 的 Feishu Docx 归档适配。
- 新增飞书归档 XML 渲染器与本地 fake 归档器，支持在不写入真实飞书文档的情况下完成测试与本地联调。
- 新增前端归档状态面板，支持在 `/app` 中展示 `session_id / archive_status / archive_title / archive_url`，并在归档成功时提供飞书文档打开入口。

### Changed

- 拆分 LLM 输出模型与 API 响应模型，避免会话归档元数据进入 prompt 或 fake client。
- 调整前端单轮澄清流程：首次响应保留 `session_id`，二次“补充并重新分析”请求原样带回。
- 新增 `IDEAOS_ARCHIVE_DB_PATH` 配置项，并补充本地归档数据库文件的忽略规则。
- 完成态会话现在会在写入本地 `SQLite` 索引后同步尝试飞书归档，并将结果回写为 `succeeded / failed`，同时保证归档失败不阻塞主分析结果返回。
- 补充 `archive_title` 语义标题字段与 `IDEAOS_USE_FAKE_ARCHIVE`、`IDEAOS_FEISHU_*` 配置项，用于控制飞书标题策略、CLI 调用方式、归档位置与超时行为。

### Fixed

- 修复 Windows 环境下真实飞书归档调用 `lark-cli` 时的命令解析问题，归档器现在会先解析可执行文件真实路径，避免 `.cmd` 包装器无法被 `subprocess.run(["lark-cli", ...])` 正确找到。
- 修复 Windows 环境下飞书归档中文乱码问题，归档器调用 `lark-cli` 时现已显式使用 `UTF-8` 传输 XML 内容，避免运行中 Python 进程回落系统默认编码后将中文写成乱码。

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
