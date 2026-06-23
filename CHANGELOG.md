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

### 变更

- 将开发基线统一到 `conda + Python 3.13 + pip`
- 更新 `README` 的环境安装、运行和质量检查说明

## [0.1.0-init] - 2026-06-15

### 新增

- 初始愿景、产品、路线图文档

### 变更

- 将 `CHANGELOG.md` 提升为项目根目录主版本日志
- 确立 `v0.1` 采用 Python 主体路线

### 移除

- 删除旧的 `github_project_management/` 目录，避免版本日志分散
