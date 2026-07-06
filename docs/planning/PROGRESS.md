# 项目进度

## 当前版本

- `Version`：`v0.2.0`
- `Status`：`Release Ready`
- `Theme`：`Session Archive / Feishu Archive`
- `Stable Base`：`main` 仍代表 `v0.1` 稳定主线；本次收口以 `release/v0.2.0` 发布分支为准

------

## 已确认决策

- [x] 仅在**最终完成态分析**后触发归档，不为澄清中间态自动创建飞书文档
- [x] 本地索引使用 `SQLite`
- [x] 一条完整会话对应一份飞书文档
- [x] 历史记录用于归档与回看，不默认自动注入下一轮分析
- [x] `PROGRESS.md` 继续保留，作为当前版本实时进展文档
- [x] `session_id` 属于系统会话元数据，不进入 prompt，不作为 LLM 输出字段
- [x] `session_id` 由服务端在首次请求时生成，并在首次响应中返回；后续同一会话请求必须原样带回
- [x] `archive_status` 采用四态：`not_triggered / pending / succeeded / failed`
- [x] `archive_url` 仅表示归档成功后的飞书文档链接，不参与 LLM 推理
- [x] 分析内容契约与 API 响应契约分层：LLM 只生成分析内容，应用层补充会话与归档元数据

------

## v0.2 目标

- [x] 定义会话记录与归档契约结构
- [x] 建立本地 `SQLite` 索引与归档状态跟踪
- [x] 接入飞书归档链路，生成面向人的会话文档
- [x] 将归档状态与文档链接回传给前端
- [x] 保持主分析链路与归档链路解耦

------

## v0.2 非目标

- 不实现自动跨会话长期记忆
- 不实现多轮自由聊天
- 不实现飞书双向编辑回写
- 不引入多 Agent、向量数据库或工作流引擎
- 不在首版构建完整项目空间

------

## 里程碑清单

### M1：归档契约与数据模型

- [x] 在 `PROGRESS.md` 固化 v0.2 分步实施计划，作为当前版本执行基线
- [x] 在当前 `PROGRESS.md` 内冻结 M1 设计，不额外拆出独立方案文档
- [x] 定义 `session_id`、`archive_status`、`archive_url` 等核心字段
- [x] 明确“完成态归档”与错误处理策略
- [x] 拆分“LLM 输出模型”与“API 响应模型”，避免系统元数据污染模型契约

#### M1 已冻结设计

- `session_id`
  - 服务端生成，首次请求若未携带则创建
  - 首次响应无论返回澄清态还是分析态，都必须返回 `session_id`
  - 前端在单轮澄清的第二次请求中必须带回相同 `session_id`
  - `session_id` 不进入 prompt，不传给 LLM，不由 fake client 生成
- `archive_status`
  - `not_triggered`：当前仍是澄清态，未触发归档
  - `pending`：已进入完成态，归档动作已开始或已被安排
  - `succeeded`：飞书归档成功，`archive_url` 可用
  - `failed`：飞书归档失败，但主分析结果仍然正常返回
- `archive_url`
  - 仅在归档成功后返回飞书文档链接
  - 澄清态与归档失败时返回 `null`
- 完成态判定
  - 仅当 `needs_clarification=false` 且 `analysis` 完整存在时，触发正式归档
  - `open_questions` 在分析态下可以继续存在，不影响“完成态”判定

#### M1 计划产出

- 请求契约演进：`IdeaInput` 新增可选 `session_id`
- 响应契约演进：在当前分析结果外层补充 `session_id / archive_status / archive_url`
- 领域模型：定义 `ArchiveStatus`、`SessionRecord` 等最小核心模型
- 应用层编排：在分析完成后判断是否触发归档，但不把飞书写入逻辑塞进 `IdeaAnalysisService`
- 最小测试：覆盖首次请求生成 `session_id`、澄清续传 `session_id`、完成态归档状态判定

### M2：本地 SQLite 索引

- [x] 设计最小表结构
- [x] 接入 `SQLite` 存储层
- [x] 为记录创建、状态更新、查询补最小测试

#### M2 最小字段集合

- `session_id`
- `original_content`
- `input_echo`
- `clarification_count`
- `archive_status`
- `archive_url`
- `archive_error`
- `created_at`
- `completed_at`
- `archived_at`
- `updated_at`

说明：

- 首版 `SQLite` 目标是“最小索引 + 归档状态追踪”，不是完整长期记忆仓库
- 首版建议数据库文件路径固定为 `data/ideaos_agent.db`

### M3：飞书归档适配

- [x] 封装飞书 CLI / 接口调用边界
- [x] 固定文档模板与标题策略
- [x] 明确失败重试与回退行为

#### M3 当前实现说明

- 已新增 `SessionArchiver` 归档适配契约，并在 `infrastructure/archive/` 下分别实现真实飞书归档器与本地 `fake` 归档器。
- 真实飞书归档当前通过 `lark-cli docs +create --as user --json --content -` 创建文档，并解析返回结果中的 `data.document.url` 作为 `archive_url`。
- 当前默认创建位置为飞书根目录；后续如需切换归档位置，可通过 `IDEAOS_FEISHU_ARCHIVE_PARENT_TOKEN` 指向目标父目录或知识库节点。
- 当前标题规则已冻结为 `IdeaOS Archive | {archive_title}`：
  - `archive_title` 优先使用 LLM 产出的语义标题
  - 若语义标题不可用，则依次回退到 `summary`、`input_echo`
- 当前飞书正文模板已固定为“单次完整会话归档”，包含：
  - Session 信息
  - Original Idea
  - Input Echo
  - Clarification Record
  - System Assumptions
  - Analysis 九字段
  - Open Questions
- 当前失败策略已冻结为：
  - 首版不做后台自动重试
  - 飞书归档失败时写回 `failed / archive_error / archived_at`
  - 主分析结果照常返回，不回滚本次分析输出

#### M3 飞书模板最小输入

- `session_id`
- `created_at`
- `original_content`
- `input_echo`
- `clarifications`
- `assumptions`
- `analysis` 九个字段
- `open_questions`
- `archive_generated_at`

说明：

- 飞书文档承载“面向人阅读的完整会话归档”
- `archive_status` 不是飞书正文必需字段，而是本地系统状态
- `archive_url` 是飞书归档成功后返回给系统的结果，不是飞书输入

### M4：前端与接口反馈

- [x] API 返回归档状态与文档链接
- [x] 页面展示归档成功 / 失败结果
- [ ] 评估是否需要最小“查看最近归档”入口（保留为后续版本 open question）

#### M4 当前实现说明

- 前端结果区已新增 `SESSION ARCHIVE / 归档状态` 面板，最小展示：
  - `session_id`
  - `archive_status`
  - `archive_title`
  - `archive_url`（仅成功时展示飞书跳转链接）
- 当前四态展示规则已接入页面：
  - `not_triggered`：提示当前仍处于澄清态，尚未触发归档
  - `pending`：提示分析已完成，归档任务已开始
  - `succeeded`：提示已成功归档，并提供飞书文档打开入口
  - `failed`：提示飞书归档失败，但不影响本次分析结果阅读
- 当前首版仍不提供历史记录列表，只展示当前会话的归档状态与链接

#### M4 前端联动约定

- 第一次请求返回澄清态时，前端必须保存 `session_id`
- 第二次“补充并重新分析”请求必须携带相同 `session_id`
- 用户点击 `RESET` 后，前端应清空本地保存的 `session_id`
- 首版优先展示 `archive_status` 与 `archive_url`，暂不强推完整历史列表

------

## 当前执行顺序

为避免 v0.2 过早发散，后续实现统一按以下顺序推进：

1. `M1`：先冻结契约与分层边界，再开始代码改动
2. `M2`：先落本地 `SQLite` 最小索引，确保会话状态可追踪
3. `M3`：在不阻塞主分析链路的前提下接入飞书归档
4. `M4`：最后补前端展示与接口回传体验

每一步都必须满足以下约束：

- 不把 `session_id / archive_status / archive_url` 注入 LLM prompt
- 不把飞书调用逻辑直接塞进 `IdeaAnalysisService`
- 不把历史记录自动注入下一轮分析
- 新增契约必须补类型、测试与文档
- 尽量最小改动，不顺手重构无关文件

------

## 打开问题

- [x] `SQLite` 文件位置首版建议固定为 `data/ideaos_agent.db`
- [x] 飞书文档标题格式最终采用哪种规则
- [x] 首版不做后台自动重试，先记录失败状态与错误信息
- [ ] 是否在 v0.2 首版就展示历史记录列表

------

## 退出标准

满足以下条件时，可认为 v0.2 的最小目标达成：

- [x] 同一会话可成功生成飞书文档并返回链接
- [x] 完成一次正式分析后，系统创建本地会话索引
- [x] 飞书归档失败时，主分析结果仍正常返回
- [x] 相关环境变量、文档与测试全部补齐
