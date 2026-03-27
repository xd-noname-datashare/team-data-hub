---
name: feishu-mcp-setup
description: 配置飞书（Lark）MCP 服务，让 Cursor 能直接调用飞书 API（发消息、读文档、操作多维表格等）。当用户提到"配置飞书MCP"、"连接飞书"、"飞书MCP设置"、"安装飞书MCP" 时使用此技能。
---

# 飞书 MCP 连接配置

## 前置条件

1. 已安装 **Node.js**（v16+），终端中 `npx` 命令可用
2. 已安装 **Cursor** 编辑器

验证 Node.js：

```bash
node -v
npx -v
```

如未安装，前往 https://nodejs.org 下载 LTS 版本。

## 配置步骤

### 1. 创建 MCP 配置文件

在用户目录下创建 `~/.cursor/mcp.json`：

- **Windows 路径**: `C:\Users\<你的用户名>\.cursor\mcp.json`
- **Mac 路径**: `~/.cursor/mcp.json`

写入以下内容：

```json
{
  "mcpServers": {
    "feishu-mcp": {
      "command": "npx",
      "args": [
        "-y",
        "@larksuiteoapi/lark-mcp",
        "mcp",
        "-a",
        "cli_a9f2307120f81cd0",
        "-s",
        "<从飞书开放平台获取>"
      ]
    }
  }
}
```

> 如果 `mcp.json` 已存在且有其他 MCP 服务，将 `feishu-mcp` 段合并到 `mcpServers` 对象中，不要覆盖原有配置。

### 2. 重启 Cursor

配置文件保存后，**完全退出并重新打开 Cursor**，MCP 服务才会加载。

### 3. 验证连接

重启后，在 Cursor 对话中输入以下任意指令测试：

- "帮我查一下飞书群列表" → 应调用 `im_v1_chat_list`
- "搜索飞书文档 xxx" → 应调用 `docx_builtin_search`

如果 Cursor 能识别并调用飞书相关工具，说明配置成功。

## 配置说明

| 参数 | 值 | 说明 |
|------|-----|------|
| `-a` | `cli_a9f2307120f81cd0` | 飞书应用 App ID |
| `-s` | `<从飞书开放平台获取>` | 飞书应用 App Secret |

此应用名为「数据用研集散田」，为团队共用的飞书机器人应用。

## 可用能力一览

配置成功后，Cursor 中可直接使用以下飞书能力：

| 能力 | 工具名 | 说明 |
|------|--------|------|
| 发送消息 | `im_v1_message_create` | 向群聊/个人发送消息 |
| 群聊列表 | `im_v1_chat_list` | 查看机器人加入的群 |
| 群成员 | `im_v1_chatMembers_get` | 获取群成员列表 |
| 创建群 | `im_v1_chat_create` | 创建新群聊 |
| 搜索文档 | `docx_builtin_search` | 搜索飞书云文档 |
| 读取文档 | `docx_v1_document_rawContent` | 获取文档纯文本内容 |
| 多维表格 | `bitable_v1_appTableRecord_*` | 读写多维表格记录 |
| 知识库 | `wiki_v1_node_search` | 搜索知识库 |
| 导入文档 | `docx_builtin_import` | 将 Markdown 导入为飞书文档 |

## 常见问题

### Q: npx 命令报错 / 下载超时

设置 npm 镜像：

```bash
npm config set registry https://registry.npmmirror.com
```

### Q: Cursor 没有识别飞书工具

1. 确认 `mcp.json` 路径正确（必须在 `~/.cursor/` 目录下）
2. 确认 JSON 格式无语法错误
3. 完全退出 Cursor 后重新打开（不是重新加载窗口）

### Q: 调用时报权限错误

联系管理员在飞书开放平台为应用开通对应权限并重新发布版本。
