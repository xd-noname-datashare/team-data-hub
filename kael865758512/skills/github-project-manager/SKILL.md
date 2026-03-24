---
name: github-project-manager
description: 管理本地项目与 GitHub 仓库的同步。包括：将本地文件夹推送到 GitHub 私有仓库、从 GitHub 克隆项目到本地、推送后删除本地文件夹。当用户提到"上传 GitHub"、"推送到 GitHub"、"传到 GitHub"、"克隆"、"clone"、"拉取项目"、"从 GitHub 下载"、"备份项目"、"同步到 GitHub" 时使用此技能。
---

# GitHub 项目管理

用户的 GitHub 账号：`kael865758512`

## 前置检查

每次操作前先确认环境：

```powershell
git --version
gh auth status
```

如果 `gh` 未安装：`winget install --id GitHub.cli -e`
如果未登录：`gh auth login --web -p https`

确保已配置 safe.directory：
```powershell
git config --global --add safe.directory '*'
```

## 工作流一：推送本地文件夹到 GitHub

### 步骤

1. **在目标文件夹初始化 Git**
2. **添加并提交所有文件**
3. **用 `gh` 创建私有仓库并推送**
4. **按用户要求决定是否删除本地文件夹**

### 中文路径注意事项

Windows PowerShell 对中文路径的处理存在编码问题。如果 `working_directory` 设置为中文路径后命令报错（如 `ParserError`、`MissingEndParenthesisInMethodCall`），**必须改用批处理文件方式**：

```bat
@echo off
chcp 65001 >nul
cd /d "C:\Users\XD\Desktop\中文文件夹"
git init
git add -A
git commit -m "init: project-name"
```

将上述内容写入临时 `.bat` 文件，然后用 `cmd /c "路径\temp.bat"` 执行，执行完毕后删除 `.bat` 文件。

### 单个文件夹推送（英文路径可用）

```powershell
# 1. 初始化并提交
git init
git add -A
git commit -m "init: 项目名"

# 2. 创建私有仓库并推送（需要刷新 PATH 以找到 gh）
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
gh repo create 仓库名 --private --source=. --remote=origin --push
```

### 批量推送（多个文件夹）

写一个 `.bat` 文件统一处理：

```bat
@echo off
chcp 65001 >nul
cd /d "C:\path\to\folder1"
git init && git add -A && git commit -m "init: folder1"
gh repo create repo-name-1 --private --source=. --remote=origin --push

cd /d "C:\path\to\folder2"
git init && git add -A && git commit -m "init: folder2"
gh repo create repo-name-2 --private --source=. --remote=origin --push
```

### 常见问题

- **workflow 权限错误**（`refusing to allow an OAuth App to create or update workflow`）：先 `git rm --cached -r .github`，提交后推送，workflow 文件保留在本地
- **dubious ownership 错误**：执行 `git config --global --add safe.directory '*'`
- **仓库名规范**：使用英文小写+连字符，如 `banana-cat-battle`、`intern-recruitment`

## 工作流二：从 GitHub 克隆项目到本地

### 查看所有仓库

```powershell
gh repo list kael865758512 --limit 100
```

### 克隆单个项目

```powershell
cd C:\Users\XD\Desktop
git clone https://github.com/kael865758512/仓库名.git
```

### 克隆后继续开发

```powershell
# 修改代码后...
git add -A
git commit -m "描述修改内容"
git push
```

## 工作流三：推送后删除本地文件夹

用批处理文件删除（适配中文路径）：

```bat
@echo off
chcp 65001 >nul
rmdir /s /q "C:\Users\XD\Desktop\要删除的文件夹"
echo Deleted
```

**重要**：删除前务必确认已成功推送到 GitHub（`gh repo create` 返回了仓库 URL 且无错误）。

## 已有仓库列表

以下是用户已推送的仓库（供参考）：

| 项目 | 仓库名 |
|---|---|
| 香蕉猫大作战 | banana-cat-battle |
| 我是大老爷 | im-the-boss |
| gacha | gacha |
| dashboard | dashboard |
| 选表推荐 | watch-recommender |
| mylifedb | mylifedb |
| 实习生招聘 | intern-recruitment |
| 八字 | bazi |
