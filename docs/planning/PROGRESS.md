# 项目进度

## Phase 0：项目初始化

- [x] 建立 Python 主体项目结构
- [x] 配置最小 FastAPI 服务入口
- [x] 配置环境变量示例
- [x] 配置测试、格式化、类型检查工具
- [x] 建立文档、版本日志与协作规范
- [x] 初始化 Git 并关联 GitHub 仓库

## Phase 1：端到端薄纵切

- [x] 明确输出契约 `IdeaAnalysis`
- [x] 完成 Phase 1 设计方案评审
- [x] 实现单次 LLM 调用的端到端链路
- [x] 补齐 Phase 1 最小测试
- [x] 完成一次真实模型联调并返回完整 `IdeaAnalysis`
- [x] 建立输入链路诊断脚本与 `debug_runs/` 结果输出机制
- [x] 校准 prompt，提升模型对用户输入的理解准确率

## Phase 2：逐段提质

- [x] 确认交互模型提质为当前主线
- [x] 设计增量 A：假设透明化（assumptions / open_questions）
- [x] 设计增量 B：无状态单轮澄清（needs_clarification + clarifications）
- [x] 实现 P0：假设透明化 + 单轮澄清
- [x] 实现 P1：想法 = 结构化状态（content + clarifications）
- [x] 用真实模型复跑诊断输入并完成新旧输出对照
- [x] 补齐 `input_echo` 契约并抬高澄清门槛，完成 5 条真实输入校准
- [ ] 清理 `TestClient/httpx` 兼容性 warning（低优先级技术债）

## Phase 3：打磨与发布准备

- [ ] 待开始

当前下一步：复审分析模式下的 assumptions 与 open_questions 是否仍有过度扩写倾向，并决定是否继续细化 prompt 边界。
