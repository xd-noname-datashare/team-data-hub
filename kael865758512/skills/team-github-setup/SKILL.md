---
name: team-github-setup
description: >-
  团队数据分析成果共享的完整工作流：GitHub Organization 协作仓库 + GitHub Actions
  自动同步阿里云 OSS（备份）+ 公司内网 Nginx 服务器自动同步（主要访问方式）。
  当用户提到"建团队仓库"、"GitHub组织"、"Organization"、"团队协作"、"多人共享仓库"、
  "自动同步OSS"、"团队部署"、"共享看板"、"团队网页"、"内网同步"、"部署到内网"、
  "公司服务器"、"内网服务器" 时使用此技能。
---

# 团队协作仓库 + 双端自动同步

## 架构

```
组员A push ─┐
组员B push ─┤→ GitHub Org 仓库 (xd-noname-datashare/team-data-hub)
组员C push ─┘        │
                     ├→ GitHub Actions → 阿里云 OSS（备份存储）
                     └→ 内网服务器 cron git pull（主要访问方式，每5分钟）
```

**分工**：
- **阿里云 OSS**：仅作备份/容灾，不作为日常分享链接
- **内网服务器**：主要的链接分享方式，仅公司网络可访问，数据安全

## 访问地址

| 用途 | 地址 |
|------|------|
| 内网主页（主要） | `http://172.25.135.140/` |
| 内网报告示例 | `http://172.25.135.140/kael865758512/报告名/index.html` |
| OSS 备份 | `http://dashboard.kael99.com/datateam-noname/文件夹名/index.html` |
| GitHub Pages 备用 | `https://xd-noname-datashare.github.io/team-data-hub/` |

## 已有实例

- **Organization**: `xd-noname-datashare`
- **仓库**: `https://github.com/xd-noname-datashare/team-data-hub`（公开仓库）
- **OSS Bucket**: `kael1235`（香港节点），路径前缀 `datateam-noname/`
- **内网服务器**: `172.25.135.140`（Ubuntu 24.04，Nginx 1.24）

---

## Part 1: GitHub Org 仓库搭建

### 创建 Organization

1. https://github.com/organizations/plan → 选 Free
2. 创建仓库（不勾选 Initialize）
3. 修改 Org 默认权限为 Write：

```bash
gh auth refresh -h github.com -s admin:org
gh api -X PATCH "orgs/<ORG>" -f default_repository_permission=write
```

### 仓库目录结构

```
team-data-hub/
├── .github/workflows/sync-to-oss.yml
├── _template/                    # 报告模板（不同步）
├── sync_to_oss.py                # OSS 同步脚本
├── index.html                    # 团队主页
├── requirements.txt
├── 团队成员入门指南.md
├── kael865758512/                # 成员个人目录
│   └── 某报告/index.html
└── 心动小镇周报合集/              # 项目报告目录
    └── ...
```

### 邀请成员

```bash
gh api -X PUT "orgs/<ORG>/memberships/<USERNAME>" -f role=member
```

---

## Part 2: 阿里云 OSS 自动同步（备份）

### GitHub Actions 工作流

```yaml
name: 自动同步到阿里云 OSS
on:
  push:
    branches: [main]
    paths-ignore: ["README.md", ".gitignore", "_template/**", ".github/**"]
  workflow_dispatch:
jobs:
  sync-to-oss:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install oss2
      - run: python sync_to_oss.py --all
        env:
          OSS_ACCESS_KEY_ID: ${{ secrets.OSS_ACCESS_KEY_ID }}
          OSS_ACCESS_KEY_SECRET: ${{ secrets.OSS_ACCESS_KEY_SECRET }}
          OSS_BUCKET_NAME: ${{ secrets.OSS_BUCKET_NAME }}
          OSS_ENDPOINT: ${{ secrets.OSS_ENDPOINT }}
          OSS_BASE_PATH: ${{ secrets.OSS_BASE_PATH }}
```

### sync_to_oss.py 关键设计

```python
SKIP_DIRS = {".git", ".github", "__pycache__", "_template", ".cursor", "node_modules"}
SKIP_FILES = {".gitignore", "sync_to_oss.py", "requirements.txt", "README.md", "LICENSE"}
ALLOWED_EXTENSIONS = {".html", ".js", ".css", ".json", ".csv", ".png", ".jpg", ".svg", ".pdf", ".xlsx"}
```

- 全量同步（`--all`），因为 `git diff` 对中文文件名做八进制转义会导致路径不匹配
- OSS 默认域名会强制下载 HTML → 必须用自定义域名访问

### 配置 Secrets

```bash
gh secret set OSS_ACCESS_KEY_ID -b "值" -R org/repo
gh secret set OSS_ACCESS_KEY_SECRET -b "值" -R org/repo
gh secret set OSS_BUCKET_NAME -b "值" -R org/repo
gh secret set OSS_ENDPOINT -b "值" -R org/repo
gh secret set OSS_BASE_PATH -b "值" -R org/repo
```

---

## Part 3: 内网服务器自动同步（主要访问）

### 原理

GitHub Actions 无法访问内网服务器（172.25.x.x 是私网 IP），因此采用**服务器主动拉取**：
- 服务器上 clone 仓库
- cron 每 5 分钟执行 `git pull`
- Nginx 直接从 clone 目录提供服务

### 首次配置服务器

使用 paramiko 通过 SSH 完成（避免交互式密码输入）：

```python
import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=pwd, timeout=10)
```

**步骤**：

1. 安装 Nginx + Git：
```bash
apt-get update -qq && apt-get install -y -qq nginx git
systemctl enable nginx && systemctl start nginx
```

2. Clone 仓库：
```bash
git clone https://github.com/xd-noname-datashare/team-data-hub.git /var/www/team-data-hub
```

3. 创建自动拉取脚本 `/usr/local/bin/sync-team-data.sh`：
```bash
#!/bin/bash
cd /var/www/team-data-hub && git pull --ff-only origin main >> /var/log/team-data-hub-sync.log 2>&1
```

4. 配置 cron（每 5 分钟）：
```bash
(crontab -l 2>/dev/null | grep -v "sync-team-data"; echo "*/5 * * * * /usr/local/bin/sync-team-data.sh") | crontab -
```

5. Nginx 配置 `/etc/nginx/sites-available/reports`：

```nginx
server {
    listen 80;
    server_name _;
    charset utf-8;
    root /var/www/team-data-hub;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
        autoindex on;
        autoindex_exact_size off;
        autoindex_localtime on;
    }

    # 独立部署的报告用 alias 映射（不在 git 仓库内的内容）
    # location /some_report/ {
    #     alias /var/www/reports/some_report/;
    # }

    location ~* \.(js|css|png|jpg|gif|ico|svg)$ {
        expires 1h;
    }

    location ~ /\. {
        deny all;
    }
}
```

6. 启用配置：
```bash
ln -sf /etc/nginx/sites-available/reports /etc/nginx/sites-enabled/reports
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

### 服务器信息

- **IP**: 172.25.135.140（内网）
- **OS**: Ubuntu 24.04 LTS
- **Nginx 根目录**: `/var/www/team-data-hub/`（即 git clone 目录）
- **同步日志**: `/var/log/team-data-hub-sync.log`
- **凭据**: 服务器密码存放在各项目的 `server_config.json`（已 gitignore）
- **依赖**: `pip install paramiko`

### 新增仓库同步

如需同步其他 GitHub 仓库到同一台服务器：

```bash
git clone https://github.com/ORG/NEW_REPO.git /var/www/new-repo
# 创建拉取脚本
echo '#!/bin/bash\ncd /var/www/new-repo && git pull --ff-only >> /var/log/new-repo-sync.log 2>&1' > /usr/local/bin/sync-new-repo.sh
chmod +x /usr/local/bin/sync-new-repo.sh
# 添加 cron
(crontab -l; echo "*/5 * * * * /usr/local/bin/sync-new-repo.sh") | crontab -
```

然后在 Nginx 配置中添加对应的 `location` 块。

---

## 踩坑记录

1. **中文文件名**：`git diff --name-only` 对中文做八进制转义 → 改用全量同步
2. **OSS 强制下载**：默认域名访问 HTML 弹下载 → 必须用自定义域名
3. **Org 默认权限**：新成员默认 Read → 需 PATCH 改为 write
4. **GitHub Actions 无法访问内网**：Actions 跑在 GitHub 云端 → 服务器端用 cron pull 代替
5. **push rejected**：多人协作远端有新提交 → `git pull --rebase` 后再 push
6. **公开仓库 vs 私有仓库**：公开仓库服务器可直接 clone；私有仓库需在服务器配置 GitHub PAT
