# IdeaOS-Agent 开发路线图

## Phase 0

项目初始化

预计时长：

1 到 2 天

任务：

- 初始化 Git 与 GitHub 仓库关联
- 建立 Python 主体项目结构
- 配置 FastAPI
- 配置基础 Web 展示层
- 配置环境变量管理方式
- 配置测试、格式化、类型检查工具
- 建立文档、版本日志与协作规范

当前收尾重点：

- 确认 Python `3.13` 环境为默认开发基线
- 确认最小 FastAPI 服务可启动
- 补齐 `.env.example`
- 初始化本地 Git 并关联 GitHub 远程仓库

目标：

项目可以在本地稳定运行，并具备后续迭代基础。

------

## Phase 1

Idea Analyzer

预计时长：

3 天

输入：

用户原始想法

输出：

结构化想法对象

字段建议：

- title
- problem
- target_users
- solution
- innovation_points
- assumptions

目标：

将自然语言想法转化为结构化数据。

------

## Phase 2

Feasibility Engine

预计时长：

3 天

输出：

- 技术可行性
- 市场可行性
- 资源可行性

评分范围：

1 到 10

目标：

给出可解释、可讨论的初步判断。

------

## Phase 3

Knowledge Gap Engine

预计时长：

3 天

输出：

所需知识领域

示例：

- Computer Vision
- LLM
- Mobile Development
- Hardware Design

目标：

告诉用户为了推进这个想法，需要补哪些能力。

------

## Phase 4

Resource Gap Engine

预计时长：

2 天

输出：

缺失资源清单

示例：

- Dataset
- Funding
- Hardware
- Domain Experts

目标：

揭示容易被忽略的资源约束。

------

## Phase 5

Team Builder Engine

预计时长：

2 天

输出：

推荐团队角色

示例：

- Product Manager
- Backend Engineer
- AI Engineer
- Hardware Engineer

目标：

帮助用户判断需要怎样的团队配置。

------

## Phase 6

Roadmap Generator

预计时长：

5 天

输出：

- Stage 1 MVP
- Stage 2 Beta
- Stage 3 Product
- Stage 4 Commercialization

目标：

生成一条从想法到落地的执行路径。

------

## Phase 7

Similar Project Finder

预计时长：

5 天

数据来源：

- GitHub
- Product Hunt
- Papers
- Startup Database

目标：

帮助用户避免重复造轮子，也帮助校准差异化定位。

------

## Phase 8

打磨与发布准备

预计时长：

1 周

任务：

- 优化 UI
- 支持导出 PDF
- 支持结果历史记录
- 支持分享
- 完善文档
- 准备演示视频
- 完成 GitHub README

目标：

完成 v0.1 对外发布。
