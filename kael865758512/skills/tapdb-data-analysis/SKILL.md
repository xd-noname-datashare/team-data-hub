---
name: tapdb-data-analysis
description: >
  TapDB 游戏数据分析技能。用于查询和分析 TapDB 中的游戏运营数据，包括活跃(DAU/WAU/MAU)、
  留存(1日留存-180日留存)、付费(收入/ARPU/ARPPU)、来源(新增/转化)、用户价值(LTV)、版本分布、
  玩家行为、广告变现等指标。
  当用户需要查询游戏数据、分析运营指标、对比项目表现、检测数据异常、生成数据报告时使用此技能。
  触发关键词：TapDB、DAU、MAU、留存、付费、收入、ARPU、LTV、活跃、新增、来源、玩家行为、
  版本分布、鲸鱼用户、广告变现、游戏数据分析。
---

# TapDB 数据分析

> Skill 版本：v0.1.31

通过 Python 脚本调用 TapDB 运营数据查询接口，获取游戏指标数据并分析。

## 环境要求

- 查询脚本: `<SKILL_DIR>/scripts/tapdb_query.py`
- Python 3（优先用 `python3`；否则用 `python`）
- npm（用于 Skill 更新检查）
- 认证密钥 `TAPDB_MCP_KEY_CN` / `TAPDB_MCP_KEY_SG`

## 运行前检查（每次讨论一个新话题或新一轮数据查询时使用）

### 1. Skill 更新

```bash
npm view @tapdb/tapdb-data-analysis version --registry https://registry.npmjs.org/
```

与本文件顶部 `Skill 版本` 对比，不同则更新本 Skill

更新后**重新读取** `<SKILL_DIR>/SKILL.md`，以新版本为准。告知用户"TapDB 数据分析 Skill 已更新到 vX.X.X"，并给出更新内容。

### 2. 环境变量

检查 `TAPDB_MCP_KEY_CN` 和 `TAPDB_MCP_KEY_SG` 环境变量是否存在。
缺少则**停止操作**，引导配置：秘钥在 **TapDB 页面右上角 → 账号设置 → 秘钥管理**。国内 CN/海外 SG 各需独立秘钥。用户提供后按步骤 3 写入 shell 配置文件并验证。

### 3. 持久化检查

环境变量必须写入 shell 配置文件（根据 `$SHELL` 判断，zsh → `~/.zshrc`，bash → `~/.bashrc`），确保重启终端 / 新会话后仍可用。检查配置文件中是否已包含 `TAPDB_MCP_KEY_CN` / `TAPDB_MCP_KEY_SG` 的 export 语句，缺失的自动追加并 `source` 生效，然后运行 `list_projects` 验证。

## 工作流程

1. **确认项目**: `list_projects` 获取项目列表（含 `id/name/appid/sticky/remark`，若返回列表过长则先保存到本地再查找，避免截断导致找不到需要的项目）
   - 在 `name` 和 `remark` 中检索匹配，任一命中即为候选
   - 多候选时优先 `sticky: true`；仍有多个则对每个做轻量探测（如 7 天 DAU）：仅一个有数据→直接用；多个有数据→列出让用户选；全零→同样列出让用户选
2. **识别场景**: 按「场景路由」判断分析路径
3. **查看能力**: `describe <接口名>` 确认支持的指标/分组/过滤
4. **调用脚本**: 查询数据
5. **分析**: 读 `references/metrics_glossary.md`（指标定义）、`references/analysis_guide.md`（方法论）
6. **输出报告**: 按 `references/output_rules.md` 生成结论优先、可追溯的结构化报告

## 场景路由

### A: 纯数据查询

**触发**："查询/给我看/导出XX" → 直接查询展示（汇总表→说明→明细折叠）。**不分析、不评价、不建议**。

### B: 趋势/异常分析

**触发**："分析趋势/有没有异常/为什么下降/波动大"

1. 先查 60 天**汇总趋势**（当前30天 + 上一周期30天，优先周粒度）：DAU→`active -g time --quota dau --group-unit week`，收入→`income -g time --group-unit week`，留存→`retention -g activation_time --group-unit week`，新增→`source -g activation_time --group-unit week`
2. 按 `analysis_guide.md` 异常检测方法判断，先检查节假日效应（周粒度无法定位时再按日）
3. 需要定位异常日期/用户要求按日 → 对异常区间切到按日（`--group-unit day`），并缩小时间窗定位异常日期
4. 需要解释原因 → 做维度下钻：`-g <维度> --limit 10`（一次只查一个维度；Top10 仅作为候选池），报告只输出通过噪音过滤阈值的 Top3-5 异常维度（详见 `references/output_rules.md`「维度下钻噪音过滤」）
5. 输出执行摘要式报告

### C: 版本/卡池/活动分析

**触发**："XX版本表现/卡池效果/联动数据"

1. **先确定上线日期**：查近3月收入找尖峰日 `income -g time --no-truncate`，或查版本分布找 activeDevices 冲高的版本，或用户提供
2. 对齐天数 N = min(14, 今天 - 上线日 + 1)
3. 问"表现/效果"→**必须查上一同类版本做对比**
4. 分别查两版本上线后前 N 天（第0~N-1天）的 active/source/retention/income，表格并排对比

⚠️ 版本上线日期必须通过数据确认，不能用默认时间窗口替代。

### D: 多项目对比

**触发**："对比XX和YY" → 查多项目相同指标相同时间范围 → 按【相同点/不同点/原因/建议】输出

### E: 赛季/卡池周期对比

**触发**："对比两个赛季/SS10和SS11"

1. 查近3月收入按日 `income -g time --no-truncate`，找尖峰日定位赛季/卡池起点
2. 候选日期展示给用户确认
3. 按确认的周期分别查 active/income/retention/source，对比输出

## 脚本使用

### 基础命令

```bash
python3 <SKILL_DIR>/scripts/tapdb_query.py list_projects          # 列出项目（-r sg 查海外）
python3 <SKILL_DIR>/scripts/tapdb_query.py describe active        # 查看接口能力（不带参数查全部）
```

### 通用参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `-p` | 项目ID（必需） | `-p 2588` |
| `-s` | 开始日期（必需） | `-s 2026-02-01` |
| `-e` | 结束日期（必需） | `-e 2026-02-25` |
| `-g` | 分组字段 | `-g time` |
| `--group-unit` | 时间粒度 | `--group-unit day` |
| `--filters` | 过滤条件JSON | `--filters '[{"col_name":"activation_os","data_type":"string","calculate_symbol":"include","ftv":["Android"]}]'` |
| `--exchange-to-currency` | 金额目标货币(默认CNY) | `--exchange-to-currency USD` |
| `--charge-subject` | 付费主体 user/device | `--charge-subject user` |
| `--language` | 语言(国家分组时) | `--language cn` |
| `--group-dim` | 分组维度 cy/scon | `--group-dim cy` |
| `--de-water` | 去水 | |
| `--limit` | 结果数量上限（默认5000） | `--limit 10` |
| `--no-truncate` | 不截断输出 | |
| `-r` | 区域 cn/sg | `-r sg` |

### 时间范围硬规则（必须遵守）

- ✅ 连续时间范围直接查询
- ✅ TapDB 单次查询最长 **180 天**（包含起止日）
- ❌ 不要把时间范围按周拆分成多次查询（需要周粒度：用 `--group-unit week` **一次性**范围查询）
- ⚠️ 仅当用户明确要求“按日趋势/按天对比/定位异常日期”时才按天拆分；否则保持一次范围查询

### 查询示例

```bash
python3 <SKILL_DIR>/scripts/tapdb_query.py active -p 2588 -s 2026-02-19 -e 2026-02-25 --quota dau -g time
python3 <SKILL_DIR>/scripts/tapdb_query.py retention -p 2588 -s 2026-02-01 -e 2026-02-25 --subject device -g activation_time
python3 <SKILL_DIR>/scripts/tapdb_query.py income -p 2588 -s 2026-02-01 -e 2026-02-25 -g time
python3 <SKILL_DIR>/scripts/tapdb_query.py source -p 2588 -s 2026-02-01 -e 2026-02-25 -g activation_time
python3 <SKILL_DIR>/scripts/tapdb_query.py source -p 2588 -s 2026-02-01 -e 2026-02-25 -g activation_channel
python3 <SKILL_DIR>/scripts/tapdb_query.py user_value -p 2588 -s 2026-02-01 -e 2026-02-25 -g activation_time
python3 <SKILL_DIR>/scripts/tapdb_query.py life_cycle -p 2588 -s 2026-02-01 -e 2026-02-25 -g activation_time
python3 <SKILL_DIR>/scripts/tapdb_query.py whale_user -p 2588 -s 2026-01-01 -e 2026-02-25
python3 <SKILL_DIR>/scripts/tapdb_query.py version_distri -p 2588 -s 2026-02-01 -e 2026-02-25
python3 <SKILL_DIR>/scripts/tapdb_query.py player_behavior -p 2588 -s 2026-02-01 -e 2026-02-25 -g time
python3 <SKILL_DIR>/scripts/tapdb_query.py raw /op/active '{"project_id":2588,"start_time":"2026-02-01 00:00:00.000","end_time":"2026-02-25 23:59:59.999","subject":"device","quota":"dau","group":{"col_name":"time","col_alias":"date","is_time":true,"trunc_unit":"day"},"is_de_water":false,"filters":[]}'
```

## 子命令速查

| 子命令 | 说明 | 关键参数 | 默认时间字段 |
|--------|------|----------|-------------|
| `active` | 活跃 DAU/WAU/MAU/HAU | `--subject device\|user`, `--quota dau\|wau\|mau\|hau` | `time` |
| `retention` | 留存 | `--subject`, `--interval-unit day\|week\|month`, `--all-retention` | `activation_time` |
| `income` | 收入/付费 | 通用参数 | `time` |
| `source` | 来源/新增 | 通用参数 | `activation_time` |
| `player_behavior` | 玩家行为 | `--quota behavior\|duration` | `time` |
| `version_distri` | 版本分布 | 通用参数 | 按版本分组 |
| `user_value` | LTV | 通用参数 | `activation_time` |
| `whale_user` | 鲸鱼用户 | 通用参数 | 无分组 |
| `life_cycle` | 生命周期 | `--quota payment_amount\|payment_cvs_rate\|payment_cvs\|acc_payment` | `activation_time` |
| `ad_monet` | 广告变现 | 通用参数 | 可能返回 404（未开通或路径不同） |

## 数据量控制策略（先小后大，必须遵守）

目标：用**最省 token** 的查询顺序先定位问题，再逐步下钻；避免一上来拉按日/全量/多维明细。

- 第一次查询：只返回**汇总 + Top10**（Top10 仅作为候选池）
  - 汇总：优先用更粗时间粒度（`--group-unit week/month`）或更窄时间窗，而不是直接按日拉满大范围
  - Top10：需要维度分布时，加 `--limit 10`（如 `-g activation_channel --limit 10`）
- 维度分组：一次只下钻一个维度，查询最多 Top10（`--limit 10`）；报告只写通过阈值过滤的 Top3-5 异常维度（其余维度一句话概括“已检查，差异不大/已过滤”）
- 下钻噪音过滤阈值：按 `references/output_rules.md`「维度下钻噪音过滤（硬规则）」执行（只报异常维度、Top3-5、阈值过滤；禁止全量罗列）
- 按日明细：只在需要定位**异常日期**/用户明确要求**按日趋势**时使用；先用周/月趋势锁定区间，再切到 `day` 并缩小时间窗
- 需要完整明细：只在必须时才用 `--no-truncate`，并同时缩小时间范围/limit，避免上下文爆炸

## 数据截断规则

脚本**默认自动截断**，`_truncation` 字段包含总行数与省略行数。TapDB API 会在结果末尾附带**汇总行**（分组字段为 `null`），脚本截断时会保留该汇总行。

| 场景 | 阈值 | 方式 |
|------|------|------|
| 时间序列 | > 30 行 | 首15 + 尾15 |
| 分组维度 | > 20 行 | 前20 |
| 鲸鱼用户 | > 20 条 | 前20 |

- 不加 `--all-retention` 通常仅返回 `DR1-DR30 + DR60/90/120/150/180`；加上后会额外补齐 `DR31-DR59`（及对应 `_newDevice/_rate` 列）。

- 汇总数据以 API 返回的汇总行为准（分组字段为 `null`），不要在本地再计算汇总
- 多次查询：每次先提取关键数值再下一个查询，不累积原始数据
- 版本分布：一次性查询，不按天拆分（除非用户要求"按日趋势"）
- 需完整数据加 `--no-truncate`

## 技术注意

- **货币转换**：默认将金额转为人民币（CNY）。通过 `--exchange-to-currency` 可切换目标货币（如 USD/JPY/EUR），传 `none` 禁用转换返回原始金额。影响 income/source/user_value/life_cycle/ad_monet 等含金额字段的接口
- `filters` 即使无条件也必须传 `[]`，否则 500
- `group` 必传。retention/source 不传 `-g` 时自动用 `activation_time`，其他默认 `time`
- `life_cycle` 在 `-g activation_os` 时仅支持 `--quota payment_cvs_rate`（其他 quota 会 500）
- filters 格式: `{"col_name":"...", "data_type":"string|number|bool|date", "calculate_symbol":"include|un_include", "ftv":[...]}`
- 各接口维度不同，不支持的维度返回 500。**先 `describe` 确认**

## 分析与报告

分析时**必须阅读**：
- `references/metrics_glossary.md` — 指标定义、计算规则、维度速查、留存范围、ARPU 口径
- `references/analysis_guide.md` — 异常检测、版本对比、下钻诊断、趋势分析、业务规则
- `references/output_rules.md` — 报告结构、术语与表达规范、对比展示规则、表格与数值格式

### 分析前检查

- 明确指标、时间范围、是否需维度分组
- 涉及版本/卡池/活动 → 先通过数据确认上线日期
- "表现/效果"关键词 → 需对比基线
- "用户/人数/账号"关键词 → `--subject user`
- 金额数据默认以人民币（CNY）展示；用户提及"美元/USD"等其他货币时用 `--exchange-to-currency` 切换
- 不确定维度是否支持 → 先 `describe`
