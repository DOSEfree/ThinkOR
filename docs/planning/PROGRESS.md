# 项目进度

## 当前版本

- `Version`：`v0.3.0`
- `Status`：`Released`
- `Theme`：`Idea Thread / History Navigation`
- `Stable Base`：`release/v0.2.5` 已完成发布收口，`v0.3.0` 在其基础上增量推进
- `Release Branch`：`release/v0.3.0`

------

## 收口结论

`v0.3.0` 的最小目标已经达成，当前版本已完成以下收口：

- 本地历史记录与 thread 聚合能力已上线
- 可从任意允许继续的历史节点显式发起 follow-up
- 飞书归档正文已补充 thread context
- 产品边界仍保持“显式历史导航”，没有滑向自动长期记忆
- 未完成项主要为后续增强议题，不阻塞 `v0.3.0` 发布

------

## v0.3.0 目标

- 让用户可以在前端看见本地历史记录，而不只围绕“当前结果”继续操作
- 让用户可以明确选择某个**已完成 session** 作为下一轮 follow-up 的父节点
- 让系统能够展示一条想法链路中的父子关系，而不把产品变成长期记忆聊天助手
- 保持飞书文档继续承担“归档与回看”角色，但不把飞书当作唯一系统状态来源

------

## 当前起点

`v0.2.5` 已完成以下基础能力，构成 `v0.3.0` 的直接前提：

- [x] 已支持 `analysis / follow_up_refinement / full_plan_composed` 三类 session
- [x] 已支持 `session_id / parent_session_id / session_kind` 基础会话关系
- [x] 已支持本地 `SQLite` 结构化快照存储
- [x] 已支持基于当前结果继续 follow-up
- [x] 已支持 follow-up 结果再次归档到飞书

### 当前达成

- [x] 已有“历史记录列表”入口
- [x] 已可从任意已完成历史节点继续 follow-up
- [x] 已有“同一条 idea thread”的首版聚合视角
- [x] 已有专门的历史查询 API

------

## 已确认方向

- [x] `v0.3.0` 仍然不是长期记忆助手
- [x] 历史记录首先服务“回看与继续完善”，而不是 silent 注入 prompt
- [x] follow-up 继续保持显式选择父 session 的机制
- [x] 历史能力优先落在本地 `SQLite + API + 前端`，而不是先依赖 Feishu 真树状结构
- [x] 前端历史记录功能进入 `v0.3.0`

------

## v0.3.0 核心设计回顾

### 线程视角

建议在现有 `session_id / parent_session_id` 之上，引入更稳定的线程聚合键：

- 优先方案：`root_session_id`
- 备选方案：`thread_id`

当前倾向优先使用 `root_session_id`，原因是：

- 更贴近“一条想法链路从某次根分析开始”的产品语义
- 可以与现有 `parent_session_id` 自然共存
- 对现有 `v0.2.5` 数据模型改动最小

### 历史导航原则

- 用户必须显式选择“基于哪个历史节点继续”
- 历史列表只展示**已完成**节点作为继续入口
- 可以允许从非最新节点继续 follow-up，但它会产生新的分支 session
- 首版不强求复杂树图，可先以“列表 + 当前链路”方式呈现

------

## 里程碑清单

### M1：线程标识与存储补强

- [x] 冻结线程聚合键方案：`root_session_id`
- [x] 为 `session_records` 增加线程聚合字段
- [x] 为 `session_snapshots` 增加线程聚合字段
- [x] 明确历史链中三类 session 的展示语义：`analysis / follow_up_refinement / full_plan_composed`
- [x] 完成 `SQLite` 读写兼容策略，保证旧数据可平滑读取
- [x] 补线程字段相关类型与测试
 
### M1 当前状态

- [x] 已冻结 `root_session_id` 方案
- [x] 已为 `session_records / session_snapshots` 增加 `root_session_id`
- [x] 已完成根分析、follow-up refinement、full plan composed 的继承规则
- [x] 已完成 `SQLite` 增量兼容与读取回退
- [x] 已补模型、存储与编排测试

#### M1 具体执行步骤

1. 冻结 `root_session_id` 方案
   - 根分析 session：`root_session_id = session_id`
   - 任意 follow-up / composed session：继承直接父 session 的 `root_session_id`
2. 扩展领域模型
   - `SessionRecord` 增加 `root_session_id`
   - `SessionSnapshot` 增加 `root_session_id`
   - 需要时同步 API 响应模型中的只读展示字段，为 `v0.3` 查询接口预留一致语义
3. 扩展 `SQLite`
   - `session_records` 增加 `root_session_id`
   - `session_snapshots` 增加 `root_session_id`
   - 旧库升级时，对缺失列执行增量 `ALTER TABLE`
4. 落地编排继承规则
   - 根分析完成时写入自身 `root_session_id`
   - follow-up refinement 从父快照继承 `root_session_id`
   - full plan composed 从 refinement 快照继承 `root_session_id`
5. 明确旧数据兼容
   - 读取旧记录时，如果数据库中 `root_session_id` 为空：
     - 根 analysis 默认回退为自身 `session_id`
     - 非根 session 首版允许回退为自身 `session_id`，后续通过新写入数据逐步稳定
6. 补测试
   - 模型校验测试
   - SQLite 存取与旧列兼容测试
   - 根分析 / refinement / composed 三类编排继承测试

#### M1 设计约束

- 不推翻现有 `session_id / parent_session_id` 关系模型
- 不为了历史功能重做归档主链路
- 旧版 `v0.2.x` 数据至少要能被读取并映射到首版线程视图

### M2：历史查询 API

- [x] 新增 session 历史列表接口
- [x] 新增单个 session 详情接口
- [x] 新增 thread 列表接口
- [x] 新增 thread 详情接口
- [x] 明确“可继续 follow-up”的节点判定规则
- [x] 补 API、服务层与存储层测试

### M2 当前状态

- [x] 已完成历史查询 API 后端实现
- [x] 已完成 `SessionHistoryService`、`/api/v1/sessions`、`/api/v1/threads` 及详情接口接线
- [x] 已完成 `pytest / ruff / mypy` 校验

#### M2 建议接口草案

1. `GET /api/v1/sessions`
2. `GET /api/v1/sessions/{session_id}`
3. `GET /api/v1/threads`
4. `GET /api/v1/threads/{root_session_id}`

#### M2 设计约束

- 现有 `POST /api/v1/follow-up/refine` 与 `POST /api/v1/follow-up/compose-full-plan` 语义尽量不变
- 历史查询与分析执行接口分离，避免主链路继续膨胀

### M3：前端历史导航

- [x] 在 `/app` 中新增最小历史记录列表
- [x] 支持查看某个历史节点的核心信息：标题、类型、更新时间、归档状态
- [x] 支持点击历史节点后在结果区加载对应内容
- [x] 支持从任意已完成历史节点继续 follow-up
- [x] 支持查看当前节点的父节点/线程上下文
- [x] 补前端状态管理与交互测试

### M3 当前状态

- [x] 已完成 `/app` 首版历史导航界面接入
- [x] 已完成最近会话列表、当前线程视图与历史详情加载
- [x] 已完成从历史节点直接继续 follow-up 的前端接线
- [x] 已完成 `pytest / ruff / mypy / node --check` 校验

#### M3 首版体验边界

- 首版优先“列表 + 详情 + 继续完善”三段式体验
- 不强求一开始就做复杂树图或项目空间工作台
- 如果节点存在分支，先真实展示事实，不急着做复杂分支管理 UI

### M4：归档与线程协同增强

- [x] 在飞书正文中补更清晰的线程来源信息
- [x] 已记录父文档链接与根链路信息
- [ ] Feishu 子文档 / Wiki 结构后续再评估，不阻塞 `v0.3.0` 发布
- [x] 已明确本地线程状态与飞书展示之间的边界
- [x] 已补归档渲染与兼容性测试

#### M4 当前状态

- [x] 已为归档 payload 增加 `root_session_id / root_archive_url`
- [x] 已在 Feishu 归档正文中新增 `Thread Context` 区块
- [x] 已支持在 follow-up / composed 归档中展示根链路与直接父节点来源
- [x] 已补 session service 与 renderer 级测试，验证线程上下文随归档正确流转

#### M4 设计约束

- 飞书仍然不是唯一系统状态来源
- 不为迁就 Feishu 结构去反向绑架本地数据模型

------

## 当前执行顺序

为避免 `v0.3.0` 直接滑向“复杂项目空间”或“长期记忆产品”，实现顺序固定如下：

1. `M1`：先补线程聚合键与本地存储基础
2. `M2`：先提供历史查询 API，再谈前端导航
3. `M3`：在查询能力稳定后补前端历史交互
4. `M4`：最后增强飞书线程协同表达

每一步都必须满足以下约束：

- 不自动读取全部历史再拼进 prompt
- 不把历史导航做成开放式聊天入口
- 不覆盖原 session 或原飞书归档
- 不把 Feishu 文档当作唯一系统状态来源
- 新增模型、API、存储与交互必须补类型、测试与文档

------

## 发布后打开问题

- [ ] 历史列表首版按“最近 session”展示更合适，还是按“线程摘要”展示更合适
- [ ] 非最新历史节点继续 follow-up 时，前端是否需要显式提示“你将创建新的分支结果”
- [ ] Feishu 子文档 / Wiki 层级关系是否进入 `v0.4.0+`，还是继续保持为后续增强项

------

## 非目标

- 不做自动跨会话长期记忆
- 不做多轮自由聊天
- 不做复杂项目工作台
- 不做飞书双向编辑回写
- 不做多人协作空间
- 不把 Similar Project Finder 等外部信息接入放入 `v0.3.0` 首版主线

------

## 退出标准

满足以下条件时，可认为 `v0.3.0` 的最小目标达成：

- [x] 用户可以在前端看到本地历史记录列表
- [x] 用户可以打开某个历史节点并查看其结果与归档状态
- [x] 用户可以明确选择任意已完成节点作为下一轮 follow-up 的父节点
- [x] 系统可以展示一条想法链路中的父子关系
- [x] 产品边界仍然保持“显式历史导航”，而不是自动长期记忆
