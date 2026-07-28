# SETUP

本文件说明如何从默认的本地 Fake 体验切换到真实 LLM 或真实飞书归档。第一次运行项目时不需要任何 Secret：没有 `.env` 时，ThinkOR 默认启用 Fake LLM 和 Fake Archive。

## 首次运行

安装依赖并启动服务：

```powershell
python -m pip install --upgrade pip
python -m pip install .
python -m uvicorn ideaos_agent.main:app --reload
```

打开 `http://127.0.0.1:8000/app`。默认模式不会调用真实 LLM，也不会创建飞书文档；本地历史会保存到 `data/ideaos_agent.db`。

只有准备使用真实能力时，才创建本地配置文件：

```powershell
copy .env.example .env
```

macOS 或 Linux 使用 `cp .env.example .env`。`.env` 属于本机私有配置，不应提交到 Git。

## 运行设置面板

打开右上角“菜单 / Menu”进入“运行设置”。该面板仅可在以下条件下修改本机模式：

- `IDEAOS_ENV=development`；
- 浏览器与服务运行在本机 loopback 地址；
- 请求来自同源页面，且带有页面生成的 CSRF Token。

面板可以独立选择 LLM 与飞书归档的 Fake / Real 状态。保存时，它只会创建 `.env` 或更新以下两个键：

```env
IDEAOS_USE_FAKE_LLM=true
IDEAOS_USE_FAKE_ARCHIVE=true
```

它不会接受、读取、显示、返回或写入 API Key、模型名、飞书 Token、App Secret、代理凭据或完整 `.env` 内容。若系统环境变量中显式设置了这两个模式键，它们会优先于 `.env`；面板会显示覆盖提示。

`Fake LLM + Real Archive` 会将模拟生成内容写入真实飞书。选择此组合时，必须勾选页面上的明确确认项才能保存。

## 真实 LLM

先保持飞书归档为 Fake，再配置并验证真实 LLM。ThinkOR 使用 OpenAI-compatible Chat Completions 请求，真实模式至少需要以下三项：

```env
IDEAOS_USE_FAKE_LLM=false
IDEAOS_USE_FAKE_ARCHIVE=true

IDEAOS_LLM_PROVIDER=alibaba_compatible
IDEAOS_LLM_BASE_URL=https://your-endpoint.example.com/compatible-mode/v1/chat/completions
IDEAOS_LLM_API_KEY=your_api_key_here
IDEAOS_LLM_MODEL=your_model_name_here
```

可选调优项：

```env
IDEAOS_LLM_TIMEOUT_SECONDS=30
IDEAOS_MAX_INPUT_CHARS=4000
```

运行设置只会提示 `api_key`、`model` 等缺失项，绝不显示它们的值。系统不会为了检查配置自动发送真实 LLM 请求或消耗额度；配置后请自行完成一次分析验证结果。

## 真实飞书归档

真实归档由本机 `lark-cli` 执行。ThinkOR 不保存飞书登录态或 Token，只调用已配置的 CLI。推荐先确认 `Real LLM + Fake Archive` 已可用，再启用真实归档。

### 1. 安装并配置 CLI

在终端确认 CLI 可用；若未安装，可执行：

```powershell
npm install -g @larksuite/cli
lark-cli --version
```

首次使用 CLI 还需要完成飞书应用配置。请使用 `lark-cli config init` 的交互流程，或绑定你已有的 CLI profile；当前 ThinkOR 页面不会创建或修改飞书应用配置。

### 2. 选择身份

在 `.env` 中设置真实归档：

```env
IDEAOS_USE_FAKE_ARCHIVE=false
IDEAOS_FEISHU_CLI_COMMAND=lark-cli
IDEAOS_FEISHU_ARCHIVE_AS=user
IDEAOS_FEISHU_ARCHIVE_PARENT_TOKEN=
IDEAOS_FEISHU_ARCHIVE_TIMEOUT_SECONDS=30
```

`IDEAOS_FEISHU_ARCHIVE_AS` 的两种身份不能混用：

- `user`：需要飞书应用已具备相应权限，用户再通过 CLI 授权。页面可检测状态，并在“未授权”时发起短时二维码授权；二维码和 device code 不会持久化。
- `bot`：使用飞书应用身份。页面不会发起 user 授权；应在飞书开发者后台配置 App ID、App Secret 与所需 scopes。

运行设置会检查目标身份，而不是仅检查 CLI 是否安装。`已授权，待首次归档验证` 说明目标 CLI 身份有效，但不代表创建文档、父目录权限或网络一定成功。

### 3. 验证归档

首次真实归档建议使用独立的测试父目录及其 `IDEAOS_FEISHU_ARCHIVE_PARENT_TOKEN`。完成一次真实 LLM 分析后，检查页面归档状态和可打开的 `archive_url`。归档失败不会丢失主分析结果；对失败会话可使用“查看错误并重试”，该操作只重试归档，不会再次调用 LLM 或创建新版本。

## 常见状态与处理

| 页面状态 | 含义 | 下一步 |
| --- | --- | --- |
| 模拟 LLM / 模拟归档 | 默认安全体验 | 可直接完成分析 |
| 真实 LLM 缺少 `api_key` 或 `model` | `.env` 尚未完整配置 | 手动填写对应本机字段 |
| 未安装 CLI | 找不到 `lark-cli` | 安装 CLI 后点击“重新检测飞书” |
| CLI 不可用 | CLI 无响应或命令配置错误 | 检查 `IDEAOS_FEISHU_CLI_COMMAND` 与 CLI 本身 |
| 未授权 | 目标身份尚未可用 | user 可从页面发起二维码授权；bot 到开发者后台处理权限 |
| 身份不匹配 | 可用身份与 `IDEAOS_FEISHU_ARCHIVE_AS` 不一致 | 修改本机配置或完成目标身份配置 |
| 已授权，待首次归档验证 | CLI 授权状态正常 | 使用测试目录完成一次真实归档 |

## 安全边界

- 不要把 `.env`、API Key、飞书 Token、App Secret、代理凭据或私有文档链接提交到仓库、日志、截图或测试快照。
- 对外演示优先使用 Fake LLM 与 Fake Archive；测试真实飞书时使用专用测试目录。
- 不要为了模拟未授权状态，在日常机器上执行 `lark-cli auth logout` 或重置现有 profile；这会影响当前机器已配置的飞书能力。
- 完整模拟“未安装 CLI -> 配置应用 -> 授权 -> 归档”的首次飞书流程，请使用 Windows Sandbox、虚拟机或另一个 Windows 用户，并使用独立测试飞书应用与测试目录。
