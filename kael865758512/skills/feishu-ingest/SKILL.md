# feishu-ingest

中文名：情报官

## 用途

收到飞书消息后，将消息标准化并落盘，作为后续分析和审计输入。

## 类型

本地脚本能力，不是独立 agent。

## 脚本入口

`/root/.openclaw/kael-hub/jobs/ingest_feishu_message.sh`

## 参数顺序

1. `chat_id`
2. `sender_id`
3. `sender_name`
4. `message_id`
5. `message_type`
6. `text`

## 标准调用

```bash
/root/.openclaw/kael-hub/jobs/ingest_feishu_message.sh \
  "<chat_id>" \
  "<sender_id>" \
  "<sender_name>" \
  "<message_id>" \
  "<message_type>" \
  "<text>"
```

## 何时调用

- 飞书私聊消息：默认调用
- 飞书群聊消息：默认调用
- 先落盘，再决定是否回复

## 返回结果

脚本返回 JSON，当前主要有两种状态：

- `written`
- `duplicate_skipped`

## 边界

- 情报官当前不是 OpenClaw 注册 agent
- 禁止把情报官解释为任意 `agentId`
- 只能按本地脚本方式调用
