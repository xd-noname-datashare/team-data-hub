---
name: feishu-bot-messenger
description: 通过飞书机器人「数据用研集散田」向群聊发送消息，支持文本、富文本、卡片等格式。当用户提到"发飞书"、"发到群里"、"飞书推送"、"群消息"、"飞书通知"、"飞书机器人"、"机器人发消息"、"推送到飞书"、"数据推送"、"告警通知" 时使用此技能。
---

# 飞书机器人消息推送

> 前置要求：已完成飞书 MCP 配置（参考 `feishu-mcp-setup` 技能）。

## 已接入群聊

| 群名 | chat_id | 用途 |
|------|---------|------|
| 策略分析组 | `oc_979246aa52ff46587277f2e4a30ddadc` | 数据监控 / 日报推送 |

> 需要推送到新群？先在飞书客户端将机器人「数据用研集散田」拉入目标群，然后调用 `im_v1_chat_list` 获取 chat_id，更新此表。

## 发送消息

所有发送均使用 MCP 工具 `im_v1_message_create`，固定参数：

```
params:
  receive_id_type: "chat_id"
data:
  receive_id: "<chat_id>"
  msg_type: "<消息类型>"
  content: "<JSON字符串>"
```

### 1. 纯文本消息

```json
{
  "receive_id": "oc_979246aa52ff46587277f2e4a30ddadc",
  "msg_type": "text",
  "content": "{\"text\":\"这是一条纯文本消息\"}"
}
```

文本中 @所有人：`"content": "{\"text\":\"<at user_id=\\\"all\\\">所有人</at> 请注意查收\"}"`

### 2. 卡片消息（数据报告推荐）

content 为卡片 JSON 的字符串化结果。卡片结构：

```json
{
  "config": {"wide_screen_mode": true},
  "header": {
    "title": {"tag": "plain_text", "content": "标题文字"},
    "template": "blue"
  },
  "elements": [
    {
      "tag": "div",
      "fields": [
        {"is_short": true, "text": {"tag": "lark_md", "content": "**指标A**\n12,345"}},
        {"is_short": true, "text": {"tag": "lark_md", "content": "**指标B**\n+5.2%"}}
      ]
    },
    {
      "tag": "hr"
    },
    {
      "tag": "note",
      "elements": [{"tag": "plain_text", "content": "数据来源：XXX | 统计时间：YYYY-MM-DD"}]
    }
  ]
}
```

**header.template 色值选择指南：**

| 场景 | 推荐色值 |
|------|---------|
| 日常数据报告 | `blue` |
| 正向指标/达标 | `green` |
| 异常告警 | `red` |
| 提醒通知 | `orange` |
| 中性信息 | `grey` |

全部可选：`blue` `wathet` `turquoise` `green` `yellow` `orange` `red` `carmine` `violet` `purple` `indigo` `grey`

### 3. 富文本消息（post）

支持混排文字、链接、@人：

```json
{
  "receive_id": "oc_979246aa52ff46587277f2e4a30ddadc",
  "msg_type": "post",
  "content": "{\"zh_cn\":{\"title\":\"标题\",\"content\":[[{\"tag\":\"text\",\"text\":\"普通文本 \"},{\"tag\":\"a\",\"text\":\"点击查看\",\"href\":\"https://example.com\"},{\"tag\":\"at\",\"user_id\":\"all\",\"user_name\":\"所有人\"}]]}}"
}
```

## 常用场景模板

### 数据日报

- header: template=`blue`，标题如 "📊 每日数据日报 - YYYY/MM/DD"
- elements: 用 `fields` 展示核心 KPI（DAU / 收入 / 留存 / 新增等），每行 2 个指标
- 底部 `note` 标注数据截止时间和来源

### 异常告警

- header: template=`red`，标题如 "⚠️ 数据异常告警"
- elements: 说明异常指标名称、当前值、基准值、偏离幅度
- 包含一行简要判断或建议动作

### 周报/专题报告

- header: template=`purple`，标题如 "📋 本周数据周报"
- elements: 用 `div` + `lark_md` 写多段结论，用 `hr` 分隔章节
- 可附加 `note` 写作者和分发范围

## 实用技巧

1. **先查群再发**：不确定 chat_id 时，先调用 `im_v1_chat_list` 查看机器人所在群列表
2. **content 必须是字符串**：卡片/富文本的 JSON 需要先 `JSON.stringify()`，不能直接传对象
3. **卡片字段换行**：在 `lark_md` 中用 `\n` 换行，如 `"**DAU**\n12,345"`
4. **发送后确认**：成功会返回 `message_id`，失败会返回错误码和原因
