# 数据分析团队 - 分析成果共享仓库

团队成员将分析报告（HTML 看板、数据文件等）推送到本仓库后，GitHub Actions 会自动将文件同步到阿里云 OSS。

## 快速上手

### 1. 克隆仓库

```bash
git clone https://github.com/xd-noname-datashare/team-data-hub.git
cd team-data-hub
```

### 2. 创建你的分析项目

```bash
# 复制模板
cp -r _template 用户留存分析

# 编辑文件
# - index.html  → 报告页面
# - data.js     → 数据
# 也可以放 CSV、图片等任何需要的文件
```

### 3. 推送

```bash
git add 用户留存分析/
git commit -m "新增: 用户留存分析报告 - 张三"
git push
```

推送后 GitHub Actions 自动运行，文件会在 1-2 分钟内同步到阿里云 OSS。

## 目录结构

```
team-data-hub/
├── _template/            ← 报告模板（不会同步到 OSS）
│   ├── index.html
│   └── data.js
├── 用户留存分析/          ← 示例：按分析主题建文件夹
│   ├── index.html
│   └── data.js
├── Q1收入分析/
│   ├── index.html
│   ├── data.js
│   └── revenue.csv
├── sync_to_oss.py        ← 同步脚本（不需要改动）
├── requirements.txt
└── .github/workflows/    ← 自动化配置
```

## 规范

- **文件夹命名**：用中文或英文均可，简洁描述分析主题
- **每个分析一个文件夹**：保持仓库整洁
- **提交信息**：写清楚做了什么，例如 `新增: XXX分析 - 姓名` 或 `更新: XXX数据修正`
- **不要提交敏感数据**：API Key、密码、内部用户明细等不要放进来

## 查看同步状态

推送后，打开仓库的 **Actions** 页签即可查看同步是否成功：

`https://github.com/xd-noname-datashare/team-data-hub/actions`

## 支持的文件类型

HTML, JS, CSS, JSON, CSV, TXT, PNG, JPG, SVG, PDF, Excel 等常见格式均可自动同步。
