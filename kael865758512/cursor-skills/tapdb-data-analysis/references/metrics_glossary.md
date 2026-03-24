# TapDB 核心业务指标详解

> **通用说明**：① 去重=同一用户/设备在统计周期内只计一次 ② 统计维度=账号(user) vs 设备(device) ③ 去水=过滤异常/作弊数据（脚本默认不去水，需加 `--de-water`） ④ 标注 ✨ 的字段由API直接返回，无需手动计算

---

## 基础指标

| 指标 | 字段 | 定义 | 要点 |
|------|------|------|------|
| 新增设备 | newDevice | 首次完成 SDK 初始化的设备数（设备维度） | 卸载重装不算新增 |
| 转化设备 | convertedDevice | 登录过账号的新增设备数 | ⚠️ 按设备新增日记录，非登录日（11-01新增+11-05登录→算11-01转化） |
| 转化率 | converted_rate ✨ | 转化设备÷新增设备（API返回小数，如0.8333=83.33%） | |
| 新增用户 | newUser | 首次登录的用户数（账号维度） | 与新增设备不同，统计的是账号 |

## 活跃指标

| 指标 | 定义 |
|------|------|
| DAU/WAU/MAU | 日/周/月内打开游戏的去重用户数（账号维度） |
| 活跃设备 (active_devices) | 统计期内至少打开一次应用的去重设备数 |
| 打开次数 | 打开应用的总次数（不去重，后台→前台算一次） |

**用户生命周期分类**：新用户（首次打开在统计期内）| 老用户（首次打开在统计期前，期内仍活跃）| 回流用户（曾流失，期内重新活跃）| 流失用户（超N天未打开）| 沉默用户（注册后从未打开）

### 时长指标

- 使用时长：应用内总停留时间（所有用户累计）
- 平均使用时长 ✨：总时长÷打开次数
- 人均使用时长 ✨：总时长÷活跃用户数

## 留存指标

API 直接返回 DRx_rate/WRx_rate/MRx_rate（小数形式，如 0.7656=76.56%），**无需手动计算**。

- DR1=次日留存、DR3=3日留存、DR7=7日留存、DR30=30日留存
- 通用公式：DR_N = D_N回访÷D0新增
- 常见周期：DR1/DR3/DR7/DR14/DR30/DR60/DR90
- 留存曲线应逐步下降；某节点异常下降需重点分析

### 留存指标范围（重要）

查询留存数据时，**必须明确需要哪些留存指标**：

**关键指标（默认，10个左右）**：
- 日留存：DR1、DR3、DR7、DR14、DR30
- 周留存：WR1、WR4
- 月留存：MR1、MR3、MR6
- 用途：日常分析、趋势监控
- 数据量：适中，不会超限

**所有指标（谨慎使用，180+个）**：
- 日留存：DR1-DR180（180个）| 周留存：WR1-WR26（26个）| 月留存：MR1-MR12（12个）
- 用途：特定留存天数分析（如60日留存、90日留存）
- ⚠️ 数据量极大，容易导致超限

**严格规则**：
- 默认不加 `--all-retention`（仅返回关键10个指标）
- 仅当用户明确要求"60日留存""所有留存""完整留存""DR60"等才启用 `--all-retention`
- 不要因为查询多个维度或多个项目就自动启用全量留存

| 参数 | 返回字段数 | 数据量 |
|-----|---------|--------|
| 默认（关键指标） | 约30字段 | 适中 |
| `--all-retention` | 约200+字段 | 极大，慎用 |

### 留存展示规则

- 默认只展示留存率，不展示留存人数
- 留存率 = DR1 ÷ DR1_newDevice × 100%
- 字段名固定为 `_newDevice`，含义取决于 subject（device→设备数，user→用户数）
- 若 API 返回了 `_rate` 字段，直接使用；否则手动计算
- 当前日期前1-2天的留存数据通常不完整，标注"数据未完全回补"

## 付费指标

所有付费指标基于 charge 事件统计（核心字段：charge_amount、user_id）。

| 指标 | 字段 | 定义 |
|------|------|------|
| 收入 | incomes | charge_amount 求和 |
| 付费人数 | payers_num | countdistinct(user_id) |
| 付费次数 | pay_times | count() |
| ARPU ✨ | — | 收入÷活跃用户数(user_login) |
| ARPPU ✨ | — | 收入÷付费用户数 |
| 首日ARPU ✨ | — | 首日付费÷新增设备 |
| 首日ARPPU ✨ | — | 首日付费÷首日付费人数 |
| 付费率 ✨ | _rate字段 | 付费人数÷活跃用户数（小数） |
| 首日付费用户 | firstChargeuser | 新增当天付费的新增用户数 |
| 首日付费金额 | firstChargeAmount | 新增用户首日付费金额 |
| 新增付费人数 | newChargeUser | 首次付费的用户数（不限新增时间） |
| 新增总付费 | newTotalChargeAmount | 首次付费用户的总付费金额 |
| 退款金额/次数/人数 | refunds/refund_times/refunders_num | 退款数据 |

### ARPU/ARPPU 计算口径（重要！防止计算错误）

- **ARPU 永远用日均口径**：ARPU = 日均收入 ÷ 日均DAU
  - 周/月ARPU = 各日ARPU的均值，或 总收入÷天数÷日均DAU
- **ARPPU 永远用日均口径**：ARPPU = 日均收入 ÷ 日均付费人数
- ❌ **禁止用周/月去重活跃用户数做分母**：工具返回的汇总行 active_users 是去重后的累计值（如7天去重195,663），不等于日均DAU（如155,768），用它做分母会得到错误的ARPU
- ❌ 错误：周总收入(12,230,904) ÷ 周去重活跃(195,663) = 62.46 → 这不是ARPU
- ✅ 正确：日均收入(1,747,272) ÷ 日均DAU(155,768) = 11.22 → 这才是日均ARPU

### LTV (Life Time Value)

N日内人均累计付费金额（LTV1/3/7/14/30/60/90）。通过 `user_value` 子命令查询。

### 玩家行为指标

- 游戏时长：游戏内总停留时间
- 平均游戏时长：总时长÷活跃用户数
- 启动次数：打开应用总次数

## 维度与环境字段速查

| 类别 | 字段 | 说明 |
|------|------|------|
| 设备型号 | activation_device_model | 设备兼容性分析 |
| 操作系统 | activation_os | Android/iOS/Windows/macOS |
| 系统版本 | activation_os_version | — |
| 应用版本 | activation_app_version | ⚠️ 版本分布≠版本发布记录（发布记录需另行获取） |
| 分包渠道 | activation_channel | TapTap/App Store等 |
| 广告渠道 | first_ad_conversion_link_id | 广告投放下载链接 |
| UTM来源 | utmsrc | ⚠️ 所有接口均不支持此维度的分组/过滤 |
| 国家/地区 | activation_country | — |
| 省份 | activation_province | 仅国内 |
| 次大陆 | activation_country + `--group-dim scon` | 东亚/东南亚等（非独立字段，通过 activation_country 分组 + scon 模式实现） |
| 网络方式 | activation_network | WiFi/4G/5G/3G |
| 运营商 | activation_provider | — |
| 屏幕分辨率 | activation_resolution | — |
| 首次/当前服务器 | first_server / current_server | — |
| 支付来源 | payment_source | 支付订单来源渠道（income 接口支持分组/过滤） |
| 去水 | is_de_water | 脚本默认**不去水**（需加 `--de-water` 开启） |

### 维度平台兼容性（必须遵守）

- `activation_app_version`、`activation_device_model` **仅适用于移动平台**（iOS/Android），不可用于桌面渠道（TapPC/Steam等）
- TapPC/Steam/Epic/GOG 等渠道**仅存在于桌面平台**（Windows/Mac）
- 跨平台安全维度：activation_os、activation_channel、activation_country、activation_province、activation_network

### 各接口维度支持差异

不同查询子命令支持的分组/过滤维度不同，使用不支持的维度会返回 500 错误。**查询前运行 `describe <接口名>` 确认**。
