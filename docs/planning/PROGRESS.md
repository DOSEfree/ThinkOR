# 项目进度

## 当前版本

- `Version`：`v0.2.5`
- `Status`：`Release Ready`
- `Theme`：`Archive Follow-up / Plan Refinement`
- `Stable Base`：`release/v0.2.0` 已完成发布收口，后续实现基于该版本增量推进

------

## v0.2.5 目标

- 基于某次**已完成归档**的结果发起 follow-up
- 默认产出“局部完善结果”，而不是直接重跑完整九模块
- 用户可显式选择“确认修改并生成新版完整方案”
- follow-up 结果继续生成新的 `session_id`，并归档为新的飞书文档
- 保持单次有界交互：默认直接回答，必要时最多一次澄清

------

## 当前实现快照

- [x] 已落地 follow-up 契约：`FollowUpInput / FollowUpResponse / ComposeFullPlanInput / ComposedPlanResponse`
- [x] 已引入本地结构化快照：`SessionSnapshot / SessionKind / parent_session_id`
- [x] 已新增 follow-up API：`/api/v1/follow-up/refine` 与 `/api/v1/follow-up/compose-full-plan`
- [x] 已支持程序合成“新版完整方案”：仅覆盖受影响板块，未修改板块继承父方案
- [x] 已支持 follow-up 结果再次归档到飞书，且保留逻辑父子关系
- [x] 已补前端最小交互：从当前结果继续完善、必要时单轮澄清、确认后生成新版完整方案
- [x] 已补测试与类型检查，当前实现通过 `pytest / ruff / mypy`

### 收口判断

- [x] `v0.2.5` 的既定里程碑 `M1 ~ M4` 已全部落地
- [x] 当前实现满足“基于归档结果继续完善 -> 确认后生成新版完整方案 -> 再次归档”的最小闭环
- [x] 历史记录列表与历史导航未进入本版，但这属于已确认延期范围，不构成 `v0.2.5` 阻塞项
- [x] 因此当前开发分支可以视为 `v0.2.5` 的发布候选状态，后续工作主轴可转入 `v0.3`

### 当前实现边界

- follow-up 可以连续进行，但入口仍然只围绕“当前正在查看的结果”
- 前端历史记录列表仍然明确延后到 `v0.3`
- 飞书当前保留的是逻辑父子关系，不强依赖真实树状挂载结构

------

## 已确认决策

- [x] follow-up 必须显式基于某个已完成会话发起，不做“自动读取全部历史”
- [x] 每次 follow-up 都创建新的 `session_id`，不覆盖原 session
- [x] 新 session 至少记录 `parent_session_id`，保留逻辑父子关系
- [x] follow-up 默认输出“局部完善结果”，不默认重跑完整九模块
- [x] 用户可在看到局部修改后，再点击“确认修改并生成新版完整方案”
- [x] `v0.2.5` 首版的“新版完整方案”优先采用程序合成：新修改板块覆盖父方案，未修改板块原样继承
- [x] follow-up 同样最多只允许一次澄清，继续保持单次有界交互
- [x] follow-up 归档先创建**新飞书文档**，并在正文中写明父 session 与来源链接
- [x] 前端历史记录列表不进入 `v0.2.5`，延后到 `v0.3`

------

## follow-up 边界

### 可以连续 follow-up，但不是自由聊天

- 一次 follow-up 请求，仍然只对应一次有边界的分析结果
- 用户在拿到一个 follow-up 结果后，理论上可以继续基于**最新结果**再发起下一次 follow-up
- 因此系统层面允许形成：`原始分析 -> follow-up A -> follow-up B -> follow-up C`
- 但每一步都必须显式选择“基于哪一个父 session 继续”，而不是进入无限上下文闲聊

### 为什么这不等于长期记忆

- 系统只读取用户当前明确指定的父 session
- 不自动注入其它历史记录
- 不把所有历史 silently 拼进 prompt
- 每次 follow-up 仍然是离散、可归档、可回看的单次动作

------

## v0.2.5 非目标

- 不做多轮自由聊天
- 不做自动跨会话长期记忆
- 不做前端历史记录列表
- 不做“从任意历史树节点可视化跳转”的完整项目空间
- 不做飞书文档双向编辑回写
- 不承诺首版就落成真实 Feishu 树状父子结构

------

## 关键工程前提

### 仅靠 v0.2.0 的最小索引还不够

当前 `v0.2.0` 的本地 `SQLite` 只保存最小索引与归档状态，这足以支撑归档与回看，但**不足以支撑 follow-up 推理**。

原因是：

- follow-up 需要读取父 session 的结构化分析内容
- 不能把飞书文档当作唯一系统状态来源
- 也不适合在运行时反向解析飞书正文来恢复结构化数据

因此 `v0.2.5` 的第一步，不是先做 UI，而是先补齐**本地结构化会话快照存储**。

------

## 里程碑清单

### M1：follow-up 契约与本地快照模型

- [x] 定义 `FollowUpInput / FollowUpResponse / RefinementResult` 等新契约
- [x] 明确 follow-up 与“确认修改并生成新版完整方案”是两个动作，而不是一次请求内混做
- [x] 定义 `parent_session_id`、`session_kind` 等最小会话关系字段
- [x] 定义“局部修改 patch”结构：仅返回被修改板块与变更说明
- [x] 明确连续 follow-up 的规则：允许多次链式继续，但每步必须产生新 session

#### M1 冻结设计草案

- 原始分析链路继续使用现有 `IdeaAnalysisResponse`
- follow-up 新增独立契约，避免污染 `v0.2.0` 的主分析响应模型
- 建议引入两个动作：
  1. `follow_up_refine`：生成局部完善结果
  2. `follow_up_compose_full_plan`：基于上一轮局部修改，合成新版完整方案
- 新版完整方案首版优先采用程序合成，而不是再次要求 LLM 重写九个板块

### M2：本地会话快照与父子关系存储

- [x] 扩展本地存储，不只保存最小索引，还保存可继续推理的结构化快照
- [x] 为 completed analysis 保存结构化分析内容、澄清记录、假设与开放问题
- [x] 为 follow-up 保存问题、局部完善结果、受影响板块与 patch 数据
- [x] 增加 `parent_session_id`、`session_kind` 等可查询字段
- [x] 为链式 follow-up 的读取与保存补测试

#### M2 最小快照信息

- `session_id`
- `parent_session_id`
- `session_kind`：建议至少区分 `analysis / follow_up_refinement / full_plan_composed`
- `original_content`
- `input_echo`
- `clarifications`
- `assumptions`
- `analysis_snapshot` 或 `refinement_snapshot`
- `archive_status`
- `archive_url`
- `created_at / completed_at / archived_at / updated_at`

### M3：follow-up 应用层编排

- [x] 新增 follow-up service，读取父 session 快照并组织 follow-up prompt
- [x] 保持最多一次澄清的交互限制
- [x] 完成“局部完善结果”生成与校验
- [x] 完成“确认修改并生成新版完整方案”的程序合成逻辑
- [x] 保证原 session 只读，新结果写入新 session

#### M3 合成逻辑约束

- 仅覆盖 `proposed_section_updates` 中声明的板块
- 未声明修改的板块，原样继承父方案
- 若用户修改的是明显跨板块的核心前提，首版先允许继续 follow-up 打磨，不在 `v0.2.5` 强行做全量重生

### M4：follow-up 归档与前端最小体验

- [x] 新增 follow-up 归档模板
- [x] 在归档正文中写入 `parent_session_id`、父文档链接、本次追问与修改摘要
- [x] 前端在当前结果页提供“继续完善方案”入口
- [x] 前端支持“确认修改并生成新版完整方案”
- [x] 前端支持基于**当前结果**继续下一次 follow-up

#### M4 首版体验边界

- 首版可以连续 follow-up，但入口只围绕“当前正在查看的结果”
- 用户离开当前结果页后，不强求在 `v0.2.5` 中提供完整历史选择器
- 历史记录列表、筛选与树状导航统一放到 `v0.3`

------

## 当前执行顺序

为避免 `v0.2.5` 直接滑向“自由聊天产品”，实现顺序固定如下：

1. `M1`：先冻结 follow-up 契约与动作边界
2. `M2`：先补本地结构化快照，再谈连续 follow-up
3. `M3`：在父 session 只读前提下实现局部完善与完整方案合成
4. `M4`：最后补前端入口与 follow-up 归档展示

每一步都必须满足以下约束：

- 不自动注入无关历史记录
- 不把 follow-up 做成开放式聊天
- 不覆盖原 session 或原飞书归档
- 不把飞书文档当作唯一系统状态来源
- 新增契约、存储与交互必须补类型、测试与文档

------

## 打开问题

- [ ] `v0.3` 是否引入 `root_session_id` 或 `thread_id` 作为历史线程聚合键
- [ ] 哪些跨板块修改应在 UI 层显式提示“建议继续 follow-up 打磨，而不是立即合成完整方案”
- [ ] 历史记录列表、筛选与从任意历史节点继续 follow-up 的交互细节，统一转入 `v0.3`

------

## 退出标准

满足以下条件时，可认为 `v0.2.5` 的最小目标达成：

- [x] 用户可基于某个已归档 session 发起 follow-up
- [x] 系统可返回局部完善结果，并保留逻辑父子关系
- [x] 用户可显式确认修改并得到新版完整方案
- [x] follow-up 可继续归档为新文档，且不覆盖原归档
- [x] 用户可从当前结果继续发起下一次 follow-up
- [x] 历史记录列表仍然保持在 `v0.3` 范围内
