# feishu-publisher

中文名：张榜小弟

## 用途

将文本消息真实发送到飞书群或飞书会话，并记录返回状态，确保不是内部假成功。

## 类型

本地脚本能力，不是独立 agent。

## 脚本入口

`/root/.openclaw/kael-hub/jobs/send_feishu_text.sh`

## 参数顺序

1. `chat_id`
2. `text`

## 标准调用

```bash
/root/.openclaw/kael-hub/jobs/send_feishu_text.sh \
  "<chat_id>" \
  "<text>"
```

## 何时调用

- 定时推送
- 固定业务播报
- 主人明确要求在飞书中发送消息

## 返回结果

脚本返回飞书 API 原始 JSON，成功时应至少看到：

- `code = 0`
- 真实 `message_id`
- 对应 `chat_id`

## 边界

- 张榜小弟当前不是 OpenClaw 注册 agent
- 禁止把张榜小弟解释为任意 `agentId`
- 只能按本地脚本方式调用
- 没有真实 `message_id` 不应视为发送成功
