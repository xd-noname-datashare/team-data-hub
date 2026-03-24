#!/usr/bin/env python3
"""TapDB 数据查询工具 - 通过 TapDB MCP 服务查询游戏运营数据。

支持国内(cn)和海外(sg)两套部署，endpoint 已内置，只需配置认证密钥。
所有查询走 /mcp/op/* 代理接口，无需 SQL。

环境变量:
  TAPDB_MCP_KEY_CN    国内认证密钥
  TAPDB_MCP_KEY_SG    海外认证密钥
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error


BUILTIN_ENDPOINTS = {
    "cn": "https://www.tapdb.com/api",
    "sg": "https://console.ap-sg.tapdb.developer.taptap.com/api",
}


REGION_KEY_VARS = {
    "cn": "TAPDB_MCP_KEY_CN",
    "sg": "TAPDB_MCP_KEY_SG",
}


def get_config(region):
    region = (region or "cn").lower()
    base_url = BUILTIN_ENDPOINTS.get(region)
    if not base_url:
        print(f"错误: 不支持的区域 '{region}'，可选: cn, sg", file=sys.stderr)
        sys.exit(1)
    env_var = REGION_KEY_VARS[region]
    key = os.environ.get(env_var)
    if not key:
        print(f"错误: 请设置环境变量 {env_var}", file=sys.stderr)
        sys.exit(1)
    return key, base_url


def http_request(method, url, headers, body=None):
    try:
        headers = dict(headers or {})
        if not any(k.lower() == "user-agent" for k in headers):
            headers["User-Agent"] = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        data = json.dumps(body).encode("utf-8") if body else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        if data:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return {"error": True, "status": e.code, "message": err_body}
    except urllib.error.URLError as e:
        return {"error": True, "message": f"连接失败: {e.reason}"}
    except Exception as e:
        return {"error": True, "message": str(e)}


def output(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


# ── 数据截断 ────────────────────────────────────────────────

_TIME_FIELDS = frozenset(("date", "time", "activation_time", "start_time",
                          "date_", "time_", "activation_time_", "start_time_"))

_MAX_TIME_ROWS = 30
_MAX_GROUP_ROWS = 20
_MAX_WHALE_ROWS = 20
_HEAD = 15
_TAIL = 15


def _slim_rows(rows, cmd_type, group_alias=None):
    """Truncate row count; time-series keeps head+tail, others keep head."""
    if not rows:
        return rows, None
    if not isinstance(rows[0], dict):
        cap = _MAX_WHALE_ROWS if cmd_type == "whale_user" else _MAX_GROUP_ROWS
        if len(rows) <= cap:
            return rows, None
        total = len(rows)
        omit = total - cap
        rows = rows[:cap] + [f"... 省略 {omit} 条 ..."]
        return rows, {"total_rows": total, "omitted": omit}

    total = len(rows)

    # TapDB API often appends a summary row at the end (group field is null).
    # Keep that row (API-provided) when truncating.
    summary_row = None
    group_key = group_alias
    if group_key and isinstance(rows[-1], dict) and group_key in rows[-1] and rows[-1].get(group_key) is None:
        summary_row = rows[-1]
        rows = rows[:-1]
    else:
        # Best-effort fallback when caller didn't provide group_alias.
        for time_key in _TIME_FIELDS:
            if time_key in rows[-1] and rows[-1].get(time_key) is None:
                summary_row = rows[-1]
                rows = rows[:-1]
                break

    has_time = bool(rows and (_TIME_FIELDS & set(rows[0].keys())))
    if cmd_type == "whale_user":
        cap = _MAX_WHALE_ROWS
    elif has_time:
        cap = _MAX_TIME_ROWS
    else:
        cap = _MAX_GROUP_ROWS
    if len(rows) <= cap:
        if summary_row is not None:
            return rows + [summary_row], None
        return rows, None

    if has_time:
        omit = len(rows) - _HEAD - _TAIL
        rows = rows[:_HEAD] + [{"_": f"... 省略 {omit} 行 ..."}] + rows[-_TAIL:]
    else:
        omit = len(rows) - cap
        rows = rows[:cap] + [{"_": f"... 省略 {omit} 行 ..."}]
    if summary_row is not None:
        rows.append(summary_row)
    return rows, {"total_rows": total, "omitted": omit}


def _list_of_lists_to_dicts(lol):
    """Convert [[header...], [row...], ...] to [{header: val, ...}, ...]."""
    headers = [str(h) for h in lol[0]]
    return [dict(zip(headers, row)) for row in lol[1:]]


def _locate_data(obj):
    """Find main data list in API response. Returns (list, path_str) or (None, None)."""
    if isinstance(obj, list):
        if obj and isinstance(obj[0], list):
            return _list_of_lists_to_dicts(obj), "root"
        return obj, "root"
    if not isinstance(obj, dict):
        return None, None
    data = obj.get("data")
    if isinstance(data, list) and data:
        if isinstance(data[0], list):
            return _list_of_lists_to_dicts(data), "data"
        if isinstance(data[0], dict):
            return data, "data"
    if isinstance(data, dict):
        for key in ("items", "list", "rows", "records"):
            sub = data.get(key)
            if isinstance(sub, list) and sub:
                if isinstance(sub[0], list):
                    return _list_of_lists_to_dicts(sub), f"data.{key}"
                if isinstance(sub[0], dict):
                    return sub, f"data.{key}"
    return None, None


def _rebuild(resp, path, rows, info):
    """Reconstruct response with truncated rows and info."""
    if path == "root":
        return {"data": rows, "_truncation": info}
    result = dict(resp)
    result["_truncation"] = info
    if path == "data":
        result["data"] = rows
    elif path.startswith("data."):
        subkey = path[5:]
        result["data"] = dict(resp["data"])
        result["data"][subkey] = rows
    return result


def truncate_response(resp, cmd_type=None, group_alias=None):
    """Truncate API response to save context window tokens."""
    if not resp or (isinstance(resp, dict) and resp.get("error")):
        return resp
    rows, path = _locate_data(resp)
    if not rows:
        return resp

    info = {}
    rows, row_info = _slim_rows(rows, cmd_type, group_alias=group_alias)
    if row_info:
        info.update(row_info)
    if not info:
        return resp
    return _rebuild(resp, path, rows, info)


# ── 通用请求体构造 ──────────────────────────────────────────

COL_ALIAS_MAP = {
    "time": "date",
    "activation_channel": "ch",
    "first_ad_conversion_link_id": "id",
    "utmsrc": "utmsrc",
    "activation_os": "os",
    "activation_os_version": "syver",
    "activation_device_model": "dev",
    "activation_resolution": "res",
    "activation_network": "net",
    "activation_provider": "pvd",
    "activation_province": "rgn",
    "activation_country": "cy",
    "login_type": "login_type",
    "lang_system": "lang_system",
    "payment_source": "payment_source",
    "activation_time": "activation_time",
    "activation_app_version": "activation_app_version",
    "first_server": "first_server",
    "current_server": "current_server",
}

COUNTRY_GROUP_DIMS = {"activation_country", "activation_province"}


# ── 各接口能力描述（基于源码 + 实测验证） ────────────────────
#
# 分组/过滤中的"翻译字段"(trans_dims): activation_channel, activation_device_model,
# activation_network, activation_provider, activation_province, activation_country,
# first_ad_conversion_link_id, lang_system
# 这些字段分组时显示的是翻译后的展示名(来自 tapdb_group_dim 表),
# 但作为过滤条件时需使用视图中的原始值。
# 其中 lang_system 的过滤值会自动翻译(MergeGroupDimTranConstant), 可直接用展示名。

ENDPOINT_CAPS = {
    "active": {
        "description": "活跃数据: DAU/WAU/MAU/HAU",
        "quotas": ["dau", "wau", "mau", "hau"],
        "subjects": ["device", "user"],
        "returned_metrics": {
            "dau": ["dau", "dau_new", "dau_2", "dau_3", "dau_7", "dau_14", "dau_30",
                     "dau_new_rate", "dau_2_rate", "dau_3_rate", "dau_7_rate", "dau_14_rate", "dau_30_rate"],
            "wau": ["wau", "wau_new", "wau_2", "wau_3", "wau_4", "wau_5"],
            "mau": ["mau"],
            "hau": ["hau", "hau_new", "hau_2", "hau_3", "hau_7", "hau_14", "hau_30"],
        },
        "groups": [
            "time", "activation_channel", "activation_os", "activation_os_version",
            "activation_device_model", "activation_resolution", "activation_network",
            "activation_provider", "activation_province", "activation_country",
            "first_ad_conversion_link_id", "lang_system",
        ],
        "filters": [
            "activation_os", "activation_channel", "activation_os_version",
            "activation_device_model", "activation_resolution", "activation_network",
            "activation_provider", "activation_province", "activation_country",
            "first_ad_conversion_link_id", "lang_system",
        ],
        "filter_notes": {
            "activation_device_model": "翻译字段，过滤值需使用原始值（可先 group-by 此字段查看）",
            "activation_province": "翻译字段，过滤值需使用原始值",
            "activation_country": "翻译字段，值如'中国'可直接使用；港澳台会自动映射",
            "first_ad_conversion_link_id": "翻译字段，过滤值需使用原始值（非展示名'自然用户'）",
            "lang_system": "过滤值会自动翻译，可直接用展示名（如'中文'）",
        },
        "group_notes": {
            "activation_province": "需传 --language",
            "activation_country": "需传 --language 和 --group-dim (cy 或 scon)",
        },
        "unsupported_note": "不支持 activation_time/utmsrc/login_type/payment_source/activation_app_version/first_server/current_server",
    },
    "retention": {
        "description": "留存数据: DR1-DR180 / WR / MR",
        "time_field": "activation_time",
        "subjects": ["device", "user"],
        "extra_params": ["interval_unit (day|week|month)", "all_retention (bool)"],
        "groups": [
            "activation_time", "activation_channel", "activation_os", "activation_os_version",
            "activation_device_model", "activation_resolution", "activation_network",
            "activation_provider", "activation_province", "activation_country",
            "first_ad_conversion_link_id", "lang_system", "activation_app_version",
        ],
        "filters": [
            "activation_os", "activation_channel", "activation_os_version",
            "activation_device_model", "activation_resolution", "activation_network",
            "activation_provider", "activation_province", "activation_country",
            "first_ad_conversion_link_id", "lang_system", "activation_app_version",
        ],
        "filter_notes": {
            "activation_device_model": "翻译字段，过滤值需使用原始值",
            "activation_province": "翻译字段，过滤值需使用原始值",
            "activation_country": "翻译字段",
            "first_ad_conversion_link_id": "翻译字段，过滤值需使用原始值",
            "lang_system": "过滤值会自动翻译，可直接用展示名",
        },
        "group_notes": {
            "activation_province": "需传 --language",
            "activation_country": "需传 --language 和 --group-dim (cy 或 scon)",
        },
        "unsupported_note": "不支持 time/utmsrc/login_type/payment_source/first_server/current_server（retention_view 无此列）",
    },
    "income": {
        "description": "收入/付费数据: 收入/付费人数/ARPU/ARPPU",
        "returned_metrics": [
            "incomes", "pay_times", "refunds", "refund_times",
            "payers_num", "refunders_num", "active_users", "vp_incomes", "payment_rate",
        ],
        "extra_params": ["charge_subject (user|device)"],
        "groups": [
            "time", "activation_channel", "activation_os", "activation_os_version",
            "activation_device_model", "activation_resolution", "activation_network",
            "activation_provider", "activation_province", "activation_country",
            "first_ad_conversion_link_id", "lang_system",
            "payment_source", "activation_app_version", "first_server", "current_server",
        ],
        "filters": [
            "activation_os", "activation_channel", "activation_os_version",
            "activation_device_model", "activation_resolution", "activation_network",
            "activation_provider", "activation_province", "activation_country",
            "first_ad_conversion_link_id", "lang_system",
            "payment_source", "activation_app_version", "first_server", "current_server",
        ],
        "filter_notes": {
            "activation_device_model": "翻译字段，过滤值需使用原始值",
            "activation_province": "翻译字段，过滤值需使用原始值",
            "activation_country": "翻译字段",
            "first_ad_conversion_link_id": "翻译字段，过滤值需使用原始值",
            "lang_system": "过滤值会自动翻译，可直接用展示名",
        },
        "group_notes": {
            "activation_province": "需传 --language",
            "activation_country": "需传 --language 和 --group-dim (cy 或 scon)",
        },
        "unsupported_note": "不支持 activation_time/utmsrc/login_type",
    },
    "source": {
        "description": "来源数据: 新增设备/用户/转化率/首充/留存",
        "time_field": "activation_time",
        "returned_metrics": [
            "newDevice", "convertedDevice", "newUser",
            "newChargeUser", "newTotalChargeAmount",
            "firstChargeuser", "firstChargeAmount",
            "DR1", "DR7", "DR1_newDevice", "DR7_newDevice",
            "converted_rate", "DR1_rate", "DR7_rate",
            "new_charge_user_rate", "first_charge_user_rate",
        ],
        "groups": [
            "activation_time", "activation_channel", "activation_os",
            "activation_os_version", "activation_device_model", "activation_resolution",
            "activation_network", "activation_provider", "activation_province",
            "activation_country", "first_ad_conversion_link_id", "lang_system",
            "activation_app_version", "first_server",
        ],
        "filters": [
            "activation_os", "activation_channel", "activation_os_version",
            "activation_device_model", "activation_resolution", "activation_network",
            "activation_provider", "activation_province", "activation_country",
            "first_ad_conversion_link_id", "lang_system", "activation_app_version",
            "first_server",
        ],
        "filter_notes": {
            "activation_device_model": "翻译字段，过滤值需使用原始值（可先 group-by 此字段查看）",
            "activation_province": "翻译字段，过滤值需使用原始值",
            "activation_country": "翻译字段，值如'中国'可直接使用",
            "first_ad_conversion_link_id": "翻译字段，过滤值需使用原始值（非展示名'自然用户'）",
            "lang_system": "过滤值会自动翻译，可直接用展示名（如'中文'）",
        },
        "group_notes": {
            "activation_province": "需传 --language",
            "activation_country": "需传 --language 和 --group-dim (cy 或 scon)",
        },
        "unsupported_note": "不支持 time/utmsrc/login_type/payment_source/current_server 字段（source_view 无此列）",
    },
    "player_behavior": {
        "description": "玩家行为: 游戏时长/启动次数",
        "quotas": ["behavior", "duration"],
        "returned_metrics": {
            "behavior": ["total_duration", "total_times", "total_users"],
            "duration": ["duration", "player_num", "play_times"],
        },
        "groups": [
            "time", "activation_channel", "activation_os", "activation_os_version",
            "activation_device_model", "activation_resolution", "activation_network",
            "activation_provider", "activation_province", "activation_country",
            "first_ad_conversion_link_id", "lang_system", "first_server",
        ],
        "filters": [
            "activation_os", "activation_channel", "activation_os_version",
            "activation_device_model", "activation_resolution", "activation_network",
            "activation_provider", "activation_province", "activation_country",
            "first_ad_conversion_link_id", "lang_system", "first_server",
        ],
        "filter_notes": {
            "activation_device_model": "翻译字段，过滤值需使用原始值",
            "activation_province": "翻译字段，过滤值需使用原始值",
            "activation_country": "翻译字段",
            "first_ad_conversion_link_id": "翻译字段，过滤值需使用原始值",
            "lang_system": "过滤值会自动翻译，可直接用展示名",
        },
        "group_notes": {
            "activation_province": "需传 --language",
            "activation_country": "需传 --language 和 --group-dim (cy 或 scon)",
        },
        "unsupported_note": "不支持 activation_time/utmsrc/login_type/payment_source/activation_app_version/current_server",
    },
    "version_distri": {
        "description": "版本分布: 各版本活跃/新增设备数（专用接口，忽略 group 参数，固定按版本分组）",
        "returned_metrics": ["version", "allDevices", "newDevices", "upgradeDevices", "activeDevices", "NUDevices"],
    },
    "user_value": {
        "description": "用户价值(LTV): N日贡献",
        "returned_metrics": ["activation", "N_LTV (1-60,90,120,150,180,210,240,270,300,330,360)"],
        "groups": [
            "time", "activation_time", "activation_channel", "activation_os",
            "activation_os_version", "activation_device_model", "activation_resolution",
            "activation_network", "activation_provider", "activation_province",
            "activation_country", "first_ad_conversion_link_id", "lang_system",
            "activation_app_version",
        ],
        "filters": [
            "activation_os", "activation_channel", "activation_os_version",
            "activation_device_model", "activation_resolution", "activation_network",
            "activation_provider", "activation_province", "activation_country",
            "first_ad_conversion_link_id", "lang_system", "activation_app_version",
            "first_server",
        ],
        "filter_notes": {
            "activation_device_model": "翻译字段，过滤值需使用原始值",
            "activation_province": "翻译字段，过滤值需使用原始值",
            "activation_country": "翻译字段",
            "first_ad_conversion_link_id": "翻译字段，过滤值需使用原始值",
            "lang_system": "过滤值会自动翻译，可直接用展示名",
            "first_server": "仅支持过滤，不支持分组",
        },
        "group_notes": {
            "activation_province": "需传 --language",
            "activation_country": "需传 --language 和 --group-dim (cy 或 scon)",
        },
        "unsupported_note": "不支持 utmsrc/login_type/payment_source/current_server；first_server 仅可用于过滤",
    },
    "whale_user": {
        "description": "鲸鱼用户: 高付费用户排行（特殊接口，无分组/过滤，直接返回用户列表）",
        "returned_metrics": [
            "user_id", "user_name", "total_charge_amount", "server",
            "LEVEL", "first_charge_time", "last_charge_time", "last_login_time",
        ],
    },
    "life_cycle": {
        "description": "用户生命周期: 付费转化/金额/累计",
        "quotas": ["payment_cvs_rate", "payment_cvs", "payment_amount", "acc_payment"],
        "returned_metrics": {
            "payment_amount": ["newUsers", "PA0", "PA1", "PA2", "PA3", "PA4", "PA5", "PA6"],
        },
        "groups": [
            "time", "activation_time", "activation_os",
        ],
        "filters": [
            "activation_os", "activation_channel", "activation_os_version",
            "activation_device_model", "activation_resolution", "activation_network",
            "activation_provider", "activation_province", "activation_country",
            "first_ad_conversion_link_id", "lang_system",
        ],
        "filter_notes": {
            "activation_device_model": "翻译字段，过滤值需使用原始值",
            "activation_province": "翻译字段，过滤值需使用原始值",
            "activation_country": "翻译字段",
            "first_ad_conversion_link_id": "翻译字段，过滤值需使用原始值",
            "lang_system": "过滤值会自动翻译，可直接用展示名",
        },
        "group_notes": {
            "activation_os": "仅当 quota=payment_cvs_rate 时支持；（建议改用 time/activation_time）",
        },
        "unsupported_note": "分组仅支持 time/activation_time/activation_os；过滤不支持 activation_app_version/first_server/current_server/utmsrc/login_type/payment_source",
    },
    "ad_monet": {
        "description": "广告变现数据（MCP 代理路径 /mcp/op/ad_monet 返回 404，可能未开通或路径不同）",
    },
}


def cmd_describe(args):
    """输出指定接口（或全部接口）的能力描述。"""
    target = args.target

    if target and target not in ENDPOINT_CAPS:
        print(json.dumps({"error": f"未知接口 '{target}'，可选: {list(ENDPOINT_CAPS.keys())}"},
                         ensure_ascii=False))
        return

    caps = {target: ENDPOINT_CAPS[target]} if target else ENDPOINT_CAPS

    result = {}
    for name, cap in caps.items():
        info = {"description": cap["description"]}
        if "quotas" in cap:
            info["quotas"] = cap["quotas"]
        if "subjects" in cap:
            info["subjects"] = cap["subjects"]
        if "groups" in cap:
            info["supported_groups"] = [
                {"col_name": g, "col_alias": COL_ALIAS_MAP.get(g, g),
                 **({"note": cap.get("group_notes", {}).get(g)} if g in cap.get("group_notes", {}) else {})}
                for g in cap["groups"]
            ]
        if "filters" in cap:
            info["supported_filters"] = [
                {"col_name": f,
                 **({"note": cap.get("filter_notes", {}).get(f)} if f in cap.get("filter_notes", {}) else {})}
                for f in cap["filters"]
            ]
        if "extra_params" in cap:
            info["extra_params"] = cap["extra_params"]
        if "time_field" in cap:
            info["time_field"] = cap["time_field"]
        if "returned_metrics" in cap:
            info["returned_metrics"] = cap["returned_metrics"]
        if "unsupported_note" in cap:
            info["unsupported_note"] = cap["unsupported_note"]
        result[name] = info

    output(result)


def build_group(group_by, group_unit):
    if not group_by:
        return None
    is_time = group_by in ("time", "activation_time")
    return {
        "col_name": group_by,
        "col_alias": COL_ALIAS_MAP.get(group_by, group_by),
        "is_time": is_time,
        "trunc_unit": group_unit or "day",
    }


def build_base_body(args):
    body = {"project_id": int(args.project_id)}
    if hasattr(args, "start") and args.start:
        body["start_time"] = f"{args.start} 00:00:00.000"
    if hasattr(args, "end") and args.end:
        body["end_time"] = f"{args.end} 23:59:59.999"
    group_by = getattr(args, "group_by", None) or "time"
    group_unit = getattr(args, "group_unit", None)
    body["group"] = build_group(group_by, group_unit)
    if group_by in COUNTRY_GROUP_DIMS:
        body["language"] = getattr(args, "language", None) or "cn"
        group_dim = getattr(args, "group_dim", None)
        if group_dim:
            body["group_dim"] = group_dim
        elif group_by == "activation_country":
            body["group_dim"] = "cy"
    body["is_de_water"] = getattr(args, "de_water", False)
    if getattr(args, "filters", None):
        body["filters"] = json.loads(args.filters)
    else:
        body["filters"] = []
    if getattr(args, "charge_subject", None):
        body["charge_subject"] = args.charge_subject
    exchange_to = getattr(args, "exchange_to_currency", None)
    if exchange_to and exchange_to.lower() != "none":
        body["real_time_currency"] = True
        body["exchange_to_currency"] = exchange_to.upper()
    body["use_cache"] = not getattr(args, "no_cache", False)
    if getattr(args, "limit", None):
        body["limit_num"] = args.limit
    return body


def do_query(args, endpoint_path, extra=None, cmd_type=None):
    key, base_url = get_config(args.region)
    body = build_base_body(args)
    if extra:
        body.update(extra)
    url = f"{base_url}/mcp/op/{endpoint_path}"
    result = http_request("POST", url, {"MCP-KEY": key}, body)
    if not getattr(args, "no_truncate", False):
        group_alias = None
        if isinstance(body.get("group"), dict):
            group_alias = body["group"].get("col_alias")
        result = truncate_response(result, cmd_type or endpoint_path, group_alias=group_alias)
    output(result)


# ── 子命令 ──────────────────────────────────────────────────

def cmd_list_projects(args):
    key, endpoint = get_config(args.region)
    result = http_request("GET", f"{endpoint}/mcp/list_projects", {"MCP-KEY": key})
    output(result)


def cmd_active(args):
    do_query(args, "active", {
        "subject": args.subject,
        "quota": args.quota,
    })


def cmd_retention(args):
    if not args.group_by or args.group_by == "time":
        args.group_by = "activation_time"
    extra = {
        "subject": args.subject,
        "interval_unit": args.interval_unit,
        "percent": args.percent,
    }
    if args.all_retention:
        extra["extend_day"] = True
    do_query(args, "retention", extra)


def cmd_income(args):
    do_query(args, "income_data", cmd_type="income")


def cmd_source(args):
    if not args.group_by or args.group_by == "time":
        args.group_by = "activation_time"
    do_query(args, "source")


def cmd_player_behavior(args):
    do_query(args, "player_behavior", {
        "quota": args.quota,
        "duration_unit": args.duration_unit,
    })


def cmd_version_distri(args):
    do_query(args, "version_distri")

def cmd_user_value(args):
    do_query(args, "user_value")


def cmd_whale_user(args):
    do_query(args, "whale_user")


def cmd_life_cycle(args):
    if getattr(args, "group_by", None) == "activation_os" and getattr(args, "quota", None) != "payment_cvs_rate":
        output({
            "error": True,
            "message": "life_cycle 接口在 -g activation_os 时仅支持 --quota payment_cvs_rate（其他 quota 会 500）",
            "hint": "请改用 --quota payment_cvs_rate 或改用 -g time / -g activation_time",
        })
        return
    do_query(args, "life_cycle", {"quota": args.quota})


def cmd_ad_monet(args):
    do_query(args, "ad_monet")


def cmd_raw(args):
    key, base_url = get_config(args.region)
    body = json.loads(args.body) if args.body else None
    method = "POST" if body else "GET"
    url = f"{base_url}/mcp{args.path}"
    result = http_request(method, url, {"MCP-KEY": key}, body)
    output(result)


# ── CLI 定义 ────────────────────────────────────────────────

def add_common_args(p):
    p.add_argument("-p", "--project-id", required=True, help="项目ID")
    p.add_argument("-s", "--start", required=True, help="开始日期 YYYY-MM-DD")
    p.add_argument("-e", "--end", required=True, help="结束日期 YYYY-MM-DD")
    p.add_argument("-g", "--group-by", help="分组字段: time, activation_channel, activation_country, activation_os, activation_os_version, activation_device_model, activation_resolution, activation_network, activation_provider, activation_province, login_type, lang_system, payment_source, first_ad_conversion_link_id, utmsrc, activation_time, activation_app_version, first_server, current_server")
    p.add_argument("--group-unit", default="day", help="时间分组粒度: hour|day|week|month (默认 day)")
    p.add_argument("--group-dim", help="分组维度名(国家/地区用cy, 次大陆用scon)")
    p.add_argument("--language", default="cn", choices=["cn", "en", "tw", "jp"],
                    help="语言(分组为国家/地区/中国大陆时必填, 默认 cn)")
    p.add_argument("--filters", help='过滤条件JSON, 例: \'[{"col_name":"activation_os","data_type":"string","calculate_symbol":"include","ftv":["Android"]}]\'')
    p.add_argument("--charge-subject", default="user", help="付费主体: user|device (默认 user)")
    p.add_argument("--exchange-to-currency", default="CNY",
                    help="金额转换目标货币代码 (默认 CNY; 常用: CNY/USD/JPY/EUR; 传 none 禁用转换)")
    p.add_argument("--de-water", action="store_true", help="去水(默认不去水)")
    p.add_argument("--no-cache", action="store_true", help="不使用缓存")
    p.add_argument("--limit", type=int, help="结果数量上限 (默认 5000)")


def main():
    parser = argparse.ArgumentParser(
        description="TapDB 数据查询工具 - 查询游戏运营数据(活跃/留存/付费/来源等)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-r", "--region", default="cn", choices=["cn", "sg"],
                        help="部署区域: cn(国内) / sg(海外) (默认 cn)")
    parser.add_argument("--no-truncate", action="store_true",
                        help="输出完整数据，不截断（默认自动截断长数据以节省上下文）")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list_projects", help="列出当前可访问的项目")

    # active
    p = sub.add_parser("active", help="活跃数据: DAU/WAU/MAU/HAU")
    add_common_args(p)
    p.add_argument("--subject", default="device", choices=["device", "user"],
                    help="统计维度 (默认 device; 用户问'用户''人数'时用 user)")
    p.add_argument("--quota", default="dau", choices=["dau", "wau", "mau", "hau"],
                    help="活跃指标 (默认 dau)")

    # retention
    p = sub.add_parser("retention", help="留存数据: DR1-DR180 / WR / MR")
    add_common_args(p)
    p.add_argument("--subject", default="device", choices=["device", "user"],
                    help="统计维度 (默认 device)")
    p.add_argument("--interval-unit", default="day", choices=["day", "week", "month"],
                    help="留存间隔: day|week|month (默认 day)")
    p.add_argument("--percent", default=True, type=lambda x: x.lower() != "false",
                    help="返回百分比数据 (默认 true)")
    p.add_argument("--all-retention", action="store_true",
                    help="返回所有留存指标(DR1-DR180); 默认只返回关键指标")

    # income
    p = sub.add_parser("income", help="收入数据: 收入/付费人数/ARPU/ARPPU")
    add_common_args(p)

    # source
    p = sub.add_parser("source", help="来源数据: 新增设备/用户/转化率")
    add_common_args(p)

    # player_behavior
    p = sub.add_parser("player_behavior", help="玩家行为: 游戏时长/启动次数")
    add_common_args(p)
    p.add_argument("--quota", default="behavior", choices=["behavior", "duration"],
                    help="指标类型 (默认 behavior)")
    p.add_argument("--duration-unit", default="minute", choices=["minute", "10_minute", "hour"],
                    help="时长单位 (默认 minute)")

    # version_distri
    p = sub.add_parser("version_distri", help="版本分布: 各版本活跃设备数")
    add_common_args(p)

    # user_value (LTV)
    p = sub.add_parser("user_value", help="用户价值(LTV): N日贡献")
    add_common_args(p)

    # whale_user
    p = sub.add_parser("whale_user", help="鲸鱼用户: 高付费用户排行")
    add_common_args(p)

    # life_cycle
    p = sub.add_parser("life_cycle", help="用户生命周期: 付费转化/金额/累计")
    add_common_args(p)
    p.add_argument("--quota", default="payment_amount",
                    choices=["payment_cvs_rate", "payment_cvs", "payment_amount", "acc_payment"],
                    help="生命周期指标 (默认 payment_amount)")

    # ad_monet
    p = sub.add_parser("ad_monet", help="广告变现数据")
    add_common_args(p)

    # describe
    p = sub.add_parser("describe", help="查看各接口支持的指标、分组和过滤条件")
    p.add_argument("target", nargs="?", help="接口名 (留空查看全部)")

    # raw (灵活模式)
    p = sub.add_parser("raw", help="原始请求(灵活模式)")
    p.add_argument("path", help="API路径 (例: /op/active)")
    p.add_argument("body", nargs="?", help="JSON请求体")

    args = parser.parse_args()

    cmd_map = {
        "list_projects": cmd_list_projects,
        "describe": cmd_describe,
        "active": cmd_active,
        "retention": cmd_retention,
        "income": cmd_income,
        "source": cmd_source,
        "player_behavior": cmd_player_behavior,
        "version_distri": cmd_version_distri,
        "user_value": cmd_user_value,
        "whale_user": cmd_whale_user,
        "life_cycle": cmd_life_cycle,
        "ad_monet": cmd_ad_monet,
        "raw": cmd_raw,
    }
    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
