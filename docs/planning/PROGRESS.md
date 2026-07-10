# 项目进度

## 当前版本

- `Version`：`v0.4.5`
- `Status`：`Closeout Complete / Ready To Push`
- `Theme`：`Frontend Polish / Engineering Debt Cleanup / Local History Search / Leaf Delete / Branch Semantics`
- `Stable Base`：`release/v0.4.0` 已完成发布收口，`v0.4.5` 在其基础上继续增量推进
- `Working Branch Baseline`：当前开发已整理到 `release/v0.4.5`，稳定基线仍为 `release/v0.4.0`，不直接回到 `main`

------

## 当前阶段判断

`v0.4.0` 已经完成前端壳层重构、历史侧栏收敛、thread context 面板、线程级删除与 follow-up draft 恢复的首版闭环。

当前 `v0.4.5` 原本不再启动新主能力，而是收敛到两类工作：

- 继续修前端交互细节，优先打磨现有 `/app` 的状态反馈、阅读节奏、按钮行为、响应式与可访问性细节
- 收掉已经确认的工程债，优先处理版本元数据、依赖配置、文档状态与发布信息不一致的问题

在以上两类工作基础上，本轮新增 3 个明确需求。它们都涉及 history / delete / follow-up 语义，目前都已完成首轮实现与验证：

1. 本地历史搜索功能
2. 非 ROOT 叶子节点删除能力
3. 旧版本分支 follow-up 的线性展示语义

当前已明确优先处理的工程债：

1. 文档、分支状态与包元数据版本不一致：`v0.4.0` 已发布，但 `pyproject.toml` 与 `src/ideaos_agent/__init__.py` 仍停留在 `0.2.0`
2. `pyproject.toml` 的 dev 依赖中存在可疑残留项 `httpx2>=2.5,<3.0`，需要先核实并最小修正

------

## v0.4.5 目标

- 在不改变产品边界的前提下，继续优化前端交互细节
- 修正发布元数据、依赖配置与规划文档之间的不一致
- 在不引入外部检索的前提下，补最小可用的本地历史显式搜索，帮助用户找回以前的想法
- 在明确 ROOT / non-root 边界后，补最小可控的 non-root leaf delete
- 落地旧版本 follow-up 的线性分支语义，保证 history / delete / archive / draft 协同一致
- 所有修复尽量增量实现，不借机扩需求或重做结构

------

## 产品边界冻结

`v0.4.5` 继续严格遵守以下边界：

- 不把产品扩成通用聊天助手
- 不引入自动跨会话长期记忆
- 不引入多 Agent 编排
- 不引入真实外部搜索、真实登录或新的后端平台能力；如做搜索，仅限本地 history 显式搜索
- 不把 follow-up draft 从“本地可恢复缓存”改成正式历史版本
- 不把左侧历史从 formal versions 视图改成自动注入记忆入口
- 不把删除能力无约束地扩成任意单版本删除；如支持节点删除，必须先确认 non-root formal node 的删除语义

如某个前端改动会影响以下任一语义，必须先暂停确认：

- 历史逻辑
- 归档逻辑
- 删除逻辑
- draft 逻辑
- follow-up 交互语义

本轮已确认的语义基线：

1. 搜索范围
   - 仅做本地 history 搜索，不接外部搜索、联网检索或飞书远端全文搜索
   - 首版默认只覆盖 formal history，不把 follow-up draft 恢复缓存注入搜索结果
   - 搜索目标以“找回以前的想法”为主，优先覆盖 thread 标题、root idea、formal summary / archive title 等本地可索引字段
2. 节点删除范围
   - `ROOT` 节点仍禁止单删，只允许 thread-level delete
   - non-root 节点仅允许删除叶子节点；是否“全局最新”不重要，关键判断是否为 leaf
   - 删除节点时需要同步重算 `Latest`、可见版本数与历史视图，并对附着的本地 draft 与对应飞书归档做联动清理
3. 旧版本分支 follow-up 范围
   - 当用户已从 `V01 -> V02 -> V03` 演进后，再从 `V01` 发起 follow-up，新结果继续创建新的 formal node，不覆盖既有分支
   - expanded history 首版不做 tree-aware 展示，仍保持线性列表
   - 版本号采用全局递增且不重编号，并在左侧补轻量 parent / from 标记，在右侧 `CURRENT THREAD` 中明确展示 root / parent / current / chain 关系
   - folder card 的 `Latest` 继续按 thread 内最新 formal node 的更新时间计算，而不是按当前选中分支计算

------

## 当前起点

`v0.4.0` 已作为稳定底座提供以下能力：

- [x] `Topbar + Sidebar + Workspace` 三段式前端壳层
- [x] `analysis / follow_up_refinement / full_plan_composed` 三类 session 流转
- [x] formal history 仅展示 `analysis` 与 `full_plan_composed`
- [x] follow-up refinement 仅作为 7 天本地可恢复 draft
- [x] thread-level delete 与远端 Feishu best-effort cleanup
- [x] 手动 refresh 触发的 remote archive 缺失同步
- [x] SQLite 作为系统状态来源之一，飞书作为归档阅读载体

当前已识别但尚未收口的问题：

- [x] 包版本元数据仍停留在 `0.2.0`
- [x] 打包配置中的 dev 依赖存在可疑残留 `httpx2`
- [x] 规划文档尚未正式切换到 `v0.4.5`
- [ ] 前端细节优化项仍待按风险逐步推进
- [x] 本地历史搜索（local-only / formal-only）已接线并完成首轮验证
- [x] 叶子节点删除已接线完成，旧版本分支 follow-up 线性语义与删除联动已完成首轮验证

------

## 执行顺序

为避免 `v0.4.5` 滑向“顺手重做产品”，执行顺序固定如下：

1. `M1`：先修规划文档与工程元数据一致性
2. `M2`：再修低风险工程债与依赖配置问题
3. `M3`：然后逐步推进不改变语义的前端细节优化
4. `M3.5`：按“本地历史搜索 -> 线性分支语义 -> 叶子节点删除”的顺序进入受控实现
5. `M4`：最后做验证、文档同步与收口

每一步都必须满足以下约束：

- 不新增后端主能力
- 不改既有 API 契约语义
- 不重做分层结构
- 不引入与当前目标无关的大规模重构
- 每轮修改都同步补文档、类型与测试覆盖

------

## 里程碑清单

### M1：规划文档与版本状态对齐

- [x] 将 `docs/planning/PROGRESS.md` 更新为 `v0.4.5` 步骤化执行计划
- [x] 最小同步 `docs/planning/ROADMAP.md`，明确 `v0.4.5` 已启动
- [x] 明确 `release/v0.4.0` 为稳定基线，`main` 仍不是当前开发主线
- [x] 记录 `v0.4.5` 的非目标与暂停确认条件

### M2：工程债优先收口

- [x] 将 `pyproject.toml` 中的版本号从 `0.2.0` 对齐到已发布的 `0.4.0`
- [x] 将 `src/ideaos_agent/__init__.py` 中的 `__version__` 从 `0.2.0` 对齐到已发布的 `0.4.0`
- [x] 核实并移除或修正 `pyproject.toml` 中可疑的 `httpx2` dev 依赖残留
- [x] 如有必要，补充最小测试或检查，避免后续版本再次漂移

### M3：前端细节优化

- [x] 仅在不改变语义的前提下继续优化 `/app` 交互细节
- [x] 优先检查 loading / disabled / focus / error / empty state / responsive / aria 细节
- [x] 保持历史、归档、删除、draft、follow-up 语义完全不变
- [x] 一旦改动触及语义边界，立即暂停并确认

### M3.5：本地历史搜索、线性分支语义与叶子节点删除（方案已确认，并按步骤落地）

- [x] 确认本轮仅做本地 history 搜索，不接外部搜索、联网检索或自动记忆
- [x] 确认搜索结果默认仅覆盖 formal history，不包含 follow-up draft 恢复缓存
- [x] 确认搜索目标聚焦“找回以前的想法”，首版优先覆盖 thread 标题、root idea、formal summary / archive title 等本地字段
- [x] 确认 `ROOT` 仍只能 thread-level delete，non-root 仅允许叶子节点删除
- [x] 确认叶子节点删除与“是否全局最新”无直接绑定，只以是否为 leaf 作为判定标准
- [x] 确认旧版本 follow-up 不做左侧 tree-aware，采用“全局版本号递增 + 左侧轻关系标记 + 右侧当前链路明确展示”的方案
- [x] `P1`：搜索实现
- [x] 复用现有 history/session 查询链路，补最小本地搜索能力，不重做 history 数据模型
- [x] 明确搜索返回结果如何映射回 thread / version，并保持 formal history 视图边界不变
- [x] 设计前端交互：显式搜索入口、清空搜索、空结果提示、命中结果回到对应 thread / version 的导航方式
- [x] 为本地 history 搜索补最小测试，覆盖命中、空结果与 formal-only 边界
- [x] `P2`：线性分支语义实现
- [x] 固化 global version ordering：新分支只追加新版本号，不对历史节点重编号
- [x] 为 expanded history 节点补轻量关系标记，例如 `from V01` 或 `parent V01`
- [x] 在 `CURRENT THREAD` 中补明确的 root / parent / current / chain 关系展示
- [x] 明确 follow-up / compose / draft recovery 在分支场景下的 parent 绑定规则，不自动迁移、不静默改链
- [x] 为分支 follow-up 的线性展示与 `Latest` 计算补最小测试
- [x] `P3`：叶子节点删除实现
- [x] 在应用层明确 leaf 判定规则，并暴露 non-root leaf delete 所需的最小状态
- [x] 设计删除联动：同步清理本地 session snapshot、active follow-up draft、对应飞书归档，并重算 `Latest` 与版本计数
- [x] 明确 UI 约束：ROOT 节点不出现单删入口；非叶子节点必须禁用删除或显式提示原因
- [x] 若用户当前正查看被删节点，界面需安全回退到 parent 或 thread 的可用节点
- [x] 为叶子节点删除补最小测试，覆盖 leaf / non-leaf / root / branch leaf 等边界
- [x] `P4`：统一验证与文档收口
- [x] 按 `application -> infrastructure -> api/presentation -> tests -> docs` 顺序增量实现并回归验证
- [x] 同步更新 `CHANGELOG.md`、必要的规划文档与实现说明，确保代码与文档状态一致

### M4：验证与收口

- [x] 运行前先确认 Conda 环境已切换到 `ideaos-agent`
- [x] 根据改动范围执行 `pytest`、`ruff`、`mypy` 或更小粒度检查
- [x] 同步更新 `CHANGELOG.md` 的 `Unreleased`
- [x] 汇总每轮修改的文件、原因、风险与测试结果

------

## 发布前检查项

- [x] 规划文档已经正式切换到 `v0.4.5`
- [x] 包元数据与已发布版本状态一致
- [x] `pyproject.toml` 不再包含明显错误或残留的依赖声明
- [x] 前端细节优化没有改变产品边界与交互语义
- [x] 搜索、叶子节点删除与线性分支 follow-up 的语义基线已在文档中锁定
- [x] 本地 history 搜索仍保持“显式导航”边界，不演化成外部搜索或自动记忆入口
- [x] 叶子节点删除实现后，仍与 archive / draft / delete 行为保持一致；旧版本分支 follow-up 已完成当前轮验证
- [x] `CHANGELOG.md`、`ROADMAP.md`、`PROGRESS.md` 与代码状态一致
- [x] 所有验证在 `ideaos-agent` 环境下完成

------

## 非目标

- 不启动新的大版本设计
- 不改产品定义
- 不引入真实外部搜索
- 不引入真实登录
- 不引入自动记忆
- 不引入超出“non-root leaf delete”边界的任意单版本删除
- 不把 `v0.4.5` 变成复杂工作台版本

------

## 退出标准

满足以下条件时，可认为 `v0.4.5` 当前阶段的最小目标达成：

- [x] `v0.4.5` 计划文档已落地并可持续执行
- [x] 已确认的版本元数据与依赖工程债已收口
- [x] 至少完成一轮不改变语义的前端细节优化
- [x] 搜索、叶子节点删除与旧版本分支 follow-up 的方案已确认
- [x] 本地 history 搜索已进入受控实现并完成验证
- [x] 旧版本分支 follow-up 已进入受控实现并完成验证
- [x] 叶子节点删除已进入受控实现
- [x] ROOT / non-root delete、Latest 计算、draft 绑定与 branch 展示语义已验证
- [x] 文档、配置、代码与验证结果保持一致
