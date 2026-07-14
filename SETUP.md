# SETUP

这个文件只在以下情况下需要阅读：

- 你想从默认的 fake 模式切到真实 LLM
- 你想启用真实飞书归档
- 你想知道哪些环境变量只是可选调优项

如果你只是想先把项目跑起来，请优先看 [README.md](README.md)。

## 先选一种运行模式

| 目标 | `IDEAOS_USE_FAKE_LLM` | `IDEAOS_USE_FAKE_ARCHIVE` | 额外要求 |
| --- | --- | --- | --- |
| 最快公开 demo | `true` | `true` | 无 |
| 真实 LLM，fake 归档 | `false` | `true` | 需要自己的兼容接口、模型名和 API key |
| 真实 LLM，真实飞书归档 | `false` | `false` | 需要自己的兼容接口、模型名、API key，以及可用的 `lark-cli` |

建议按这个顺序推进：

1. 先跑通 `fake LLM + fake archive`
2. 再切到 `real LLM + fake archive`
3. 最后切到 `real LLM + real archive`

这样最容易定位问题到底出在模型链路还是飞书归档链路。

## 接入你自己的 LLM API

当前代码发送的是 OpenAI-compatible 的 `chat completions` 风格请求。  
`IDEAOS_LLM_PROVIDER` 目前主要作为请求头里的标记值传出，不会改变请求体结构。

把 `.env` 中的核心变量改成类似下面这样：

```env
IDEAOS_USE_FAKE_LLM=false
IDEAOS_USE_FAKE_ARCHIVE=true

IDEAOS_LLM_PROVIDER=alibaba_compatible
IDEAOS_LLM_BASE_URL=https://your-endpoint.example.com/compatible-mode/v1/chat/completions
IDEAOS_LLM_API_KEY=your_api_key_here
IDEAOS_LLM_MODEL=your_model_name_here
```

最小要求：

- `IDEAOS_LLM_BASE_URL`：真实可访问的兼容接口地址
- `IDEAOS_LLM_API_KEY`：你的本地私有 key
- `IDEAOS_LLM_MODEL`：要调用的模型名

可选项：

- `IDEAOS_LLM_TIMEOUT_SECONDS`：请求超时时间，默认 `30`
- `IDEAOS_MAX_INPUT_CHARS`：输入上限，默认 `4000`

验证方式：

1. 保持 `IDEAOS_USE_FAKE_ARCHIVE=true`
2. 启动服务并打开 `/app`
3. 完成一次分析
4. 确认你拿到的是模型真实输出，而不是 fake demo 的固定样例

如果你看到类似“LLM base URL、model 或 API key 未完整配置”，说明 fake 模式已经关闭，但这三个变量还没配完整。

## 接入真实飞书归档

当前仓库通过本地 `lark-cli` 命令完成飞书文档创建、探测和删除。  
这意味着仓库本身不会保存你的登录态或飞书凭据，它只会调用你本机已经可用的 CLI。

### 启用前提

- 你的终端里可以直接运行 `lark-cli`
- `lark-cli` 已完成你自己的本地登录
- 你已经先跑通了 `real LLM + fake archive`

### 需要的环境变量

把 `.env` 中相关项改成类似下面这样：

```env
IDEAOS_USE_FAKE_ARCHIVE=false

IDEAOS_FEISHU_CLI_COMMAND=lark-cli
IDEAOS_FEISHU_ARCHIVE_AS=user
IDEAOS_FEISHU_ARCHIVE_PARENT_TOKEN=
IDEAOS_FEISHU_ARCHIVE_TIMEOUT_SECONDS=30
```

各项含义：

- `IDEAOS_FEISHU_CLI_COMMAND`
  - 默认就是 `lark-cli`
  - 只有当你的可执行名或绝对路径不同，才需要改
- `IDEAOS_FEISHU_ARCHIVE_AS`
  - 当前默认值是 `user`
- `IDEAOS_FEISHU_ARCHIVE_PARENT_TOKEN`
  - 可留空
  - 只有当你想把所有归档都放到固定父节点下时再填写
- `IDEAOS_FEISHU_ARCHIVE_TIMEOUT_SECONDS`
  - 归档、探测、删除时共享的 CLI 超时时间

### 验证方式

1. 启动服务并完成一次正式分析
2. 确认返回结果里 `archive_status` 成功
3. 确认返回了可打开的 `archive_url`
4. 在历史线程或会话详情里再次检查归档状态回显

说明：

- 真实飞书归档失败时，主分析结果仍然会返回
- 这类失败通常会体现为 `archive_status` 失败或没有可用的 `archive_url`

## 可选的本地调优项

这些变量不是首次运行的必需项：

```env
IDEAOS_ARCHIVE_DB_PATH=data/ideaos_agent.db
IDEAOS_FOLLOW_UP_DRAFT_RETENTION_DAYS=7
IDEAOS_LLM_TIMEOUT_SECONDS=30
IDEAOS_MAX_INPUT_CHARS=4000
```

它们分别用于：

- 调整本地 `SQLite` 文件路径
- 调整 follow-up draft 在本地保留的天数
- 调整 LLM 请求超时
- 调整输入长度限制

## 安全边界

- 不要把真实 API key、真实飞书 token 或私有链接写进仓库
- 只在本地 `.env` 保存你的真实配置
- 对外演示时，优先使用 fake 模式或测试用凭据

## 常见问题

### 分析结果能出来，但归档失败

这通常说明主分析链路正常，但飞书 CLI 没有准备好。优先检查：

- `IDEAOS_USE_FAKE_ARCHIVE` 是否已经切到 `false`
- `lark-cli` 是否能在当前终端直接运行
- 你的本地登录态是否有效
- `IDEAOS_FEISHU_ARCHIVE_PARENT_TOKEN` 是否填错

### 一启动就提示 LLM 未配置

这通常说明：

- `IDEAOS_USE_FAKE_LLM=false`
- 但 `IDEAOS_LLM_BASE_URL`、`IDEAOS_LLM_API_KEY`、`IDEAOS_LLM_MODEL` 还不完整

