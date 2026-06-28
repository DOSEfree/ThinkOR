# Changelog

本项目采用人工维护的变更日志。

记录原则：

- 所有对外可感知的重要变化都应记录
- 以版本为单位归档
- 尚未发布的内容统一放在 `Unreleased`

## [Unreleased]

### 新增

- 建立文档治理结构
- 建立 Python 主体技术栈基线
- 建立代码规范与协作规范
- 建立 GitHub 项目管理建议
- 建立最小 FastAPI 服务入口
- 建立 `.env.example` 环境变量示例
- 新增 Phase 1 薄纵切设计方案
- 新增 Phase 1 单次 LLM 调用的端到端薄纵切实现
- 新增分层 LLM 调用链路（api / application / domain / infrastructure / prompts）
- 新增 fake LLM client 与真实 HTTP LLM client
- 新增 `.env` 自动加载与项目级密钥配置支持
- 新增 Phase 1 输入校验、错误映射与最小联调测试
- 新增 Phase 2 交互模型提质设计方案（假设透明化 + 无状态单轮澄清）
- 新增 P0/P1 交互模型实现：假设透明化、外层 response wrapper、无状态单轮澄清

### 变更

- 将开发基线统一到 `conda + Python 3.13 + pip`
- 更新 `README` 的环境安装、运行和质量检查说明
- 将 LLM 接入策略固定为“本地 `.env` 保存真实密钥，`.env.example` 保留模板”
- 将默认 LLM 超时配置调整到更适合真实模型调用的 90 秒
- 补齐外层 `input_echo` 契约，并将澄清模式从默认行为校准为例外行为

### 验证

- 已使用真实阿里兼容接口完成 Phase 1 链路联调，成功返回 `IdeaAnalysis` JSON
- 已确认当前下一阶段重点从“链路打通”转向“结果质量校准”
- 已用新 prompt 复跑三条真实诊断输入，24 字短想法已转为 `needs_clarification=true` 且 `analysis=null`
- 已用校准后 prompt 复跑 5 条真实诊断输入，`24/54/63` 三条目标样例均命中预期档位，`input_echo` 全部忠实复述原始想法

## [0.1.0-init] - 2026-06-15

### 新增

- 初始愿景、产品、路线图文档

### 变更

- 将 `CHANGELOG.md` 提升为项目根目录主版本日志
- 确立 `v0.1` 采用 Python 主体路线

### 移除

- 删除旧的 `github_project_management/` 目录，避免版本日志分散
