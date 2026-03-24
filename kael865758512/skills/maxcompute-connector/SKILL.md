---
name: maxcompute-connector
description: 连接阿里云 MaxCompute（ODPS）数仓，执行 SQL 查询、导出数据。当用户提到"连接数仓"、"查数仓"、"MaxCompute"、"ODPS"、"取数"、"阿里云数仓"、"跑SQL"、"导出数据" 时使用此技能。
---

# 阿里云 MaxCompute 连接

## 凭证

凭证从本机环境变量或 `.env` 文件读取，严禁硬编码：

```
MAXCOMPUTE_ACCESS_KEY_ID=<从 .env 文件读取>
MAXCOMPUTE_ACCESS_KEY_SECRET=<从 .env 文件读取>
```

## 连接参数

| 配置项 | 国服（china） | 海外（overseas） |
|---|---|---|
| Project | tapdb_one_data | （按需确认） |
| Endpoint | http://service.cn-shanghai.maxcompute.aliyun.com/api | （按需确认） |

## 快速连接方式（Python + pyodps）

### 1. 安装依赖

```bash
py -m pip install pyodps python-dotenv pyyaml
```

### 2. 连接代码

```python
from odps import ODPS

import os
o = ODPS(
    access_id=os.environ['MAXCOMPUTE_ACCESS_KEY_ID'],
    secret_access_key=os.environ['MAXCOMPUTE_ACCESS_KEY_SECRET'],
    project='tapdb_one_data',
    endpoint='http://service.cn-shanghai.maxcompute.aliyun.com/api'
)

# 测试连通性
with o.execute_sql('select 1').open_reader() as reader:
    for row in reader:
        print(row)
```

### 3. 执行 SQL 并取结果

```python
sql = "select * from some_table limit 10"
with o.execute_sql(sql).open_reader() as reader:
    for row in reader:
        print(row.values)
```

### 4. 导出为 CSV

```python
import csv

sql = "select * from some_table limit 100"
with o.execute_sql(sql).open_reader() as reader:
    with open('output.csv', 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow([col.name for col in reader._schema.columns])
        for row in reader:
            writer.writerow(row.values)
```

## 已有项目参考

如果用户本机存在数仓项目目录（参考 `C:\Users\XD\Downloads\README.md`），优先使用其中的：
- `maxcompute_client.py`：统一连接模块
- `test_maxcompute.py`：连通性测试脚本
- `maxcompute.yaml` + `.env`：配置文件

## 安全规则

- **严禁**将 AK/SK 写入任何会被 git 提交的文件
- **严禁**在终端输出中打印 AK/SK
- 如需创建 `.env` 文件，必须同时确保 `.gitignore` 中包含 `.env`
- 创建新项目时，AK/SK 只放在 `.env` 中，代码通过环境变量读取
