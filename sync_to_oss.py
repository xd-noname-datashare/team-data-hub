# -*- coding: utf-8 -*-
"""
阿里云 OSS 自动同步脚本
将仓库中的分析成果（HTML/JS/CSS/图片等）镜像同步到阿里云 OSS。

用法:
  python sync_to_oss.py --all                          # 全量同步仓库内所有可发布文件
  python sync_to_oss.py 用户留存分析/index.html data.js  # 只同步指定文件
"""

import json
import os
import sys
import argparse

try:
    import oss2
except ImportError:
    print("[ERROR] 请先安装 oss2: pip install oss2")
    sys.exit(1)

# ── 不需要同步到 OSS 的目录/文件 ──
SKIP_DIRS = {".git", ".github", "__pycache__", "_template", ".cursor", "node_modules"}
SKIP_FILES = {
    ".gitignore", ".gitattributes", "sync_to_oss.py",
    "requirements.txt", "README.md", "LICENSE",
}

# ── 允许同步的文件扩展名 ──
ALLOWED_EXTENSIONS = {
    ".html", ".htm", ".js", ".css", ".json", ".csv", ".txt", ".md",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
    ".woff", ".woff2", ".ttf", ".eot",
    ".xml", ".yaml", ".yml",
    ".pdf", ".xlsx", ".xls",
}

CONTENT_TYPE_MAP = {
    ".html": "text/html; charset=utf-8",
    ".htm":  "text/html; charset=utf-8",
    ".js":   "application/javascript; charset=utf-8",
    ".css":  "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".csv":  "text/csv; charset=utf-8",
    ".txt":  "text/plain; charset=utf-8",
    ".md":   "text/markdown; charset=utf-8",
    ".xml":  "application/xml; charset=utf-8",
    ".yaml": "text/yaml; charset=utf-8",
    ".yml":  "text/yaml; charset=utf-8",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif":  "image/gif",
    ".svg":  "image/svg+xml",
    ".ico":  "image/x-icon",
    ".webp": "image/webp",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf":  "font/ttf",
    ".pdf":  "application/pdf",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls":  "application/vnd.ms-excel",
}


def get_content_type(filename):
    ext = os.path.splitext(filename)[1].lower()
    return CONTENT_TYPE_MAP.get(ext, "application/octet-stream")


def is_syncable(filepath):
    """判断文件是否应该同步到 OSS"""
    parts = filepath.replace("\\", "/").split("/")
    if any(p in SKIP_DIRS for p in parts):
        return False
    basename = os.path.basename(filepath)
    if basename in SKIP_FILES or basename.startswith("."):
        return False
    ext = os.path.splitext(basename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def load_oss_config():
    """从环境变量（CI）或本地 oss_config.json 加载配置"""
    access_key_id = os.environ.get("OSS_ACCESS_KEY_ID")
    if access_key_id:
        return {
            "access_key_id": access_key_id,
            "access_key_secret": os.environ.get("OSS_ACCESS_KEY_SECRET"),
            "bucket_name": os.environ.get("OSS_BUCKET_NAME"),
            "endpoint": os.environ.get("OSS_ENDPOINT"),
            "base_path": os.environ.get("OSS_BASE_PATH", ""),
        }

    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oss_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def collect_all_files(root="."):
    """遍历仓库，收集所有可同步文件"""
    result = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            rel = os.path.relpath(os.path.join(dirpath, fname), root).replace("\\", "/")
            if is_syncable(rel):
                result.append(rel)
    return sorted(result)


def upload_file(bucket, local_path, oss_key, content_type):
    """上传单个文件"""
    try:
        with open(local_path, "rb") as f:
            result = bucket.put_object(oss_key, f, headers={"Content-Type": content_type})
        if result.status == 200:
            size = os.path.getsize(local_path)
            return True, f"{local_path} -> {oss_key} ({size:,} bytes)"
        return False, f"HTTP {result.status}"
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description="同步分析成果到阿里云 OSS")
    parser.add_argument("files", nargs="*", default=[], help="指定要同步的文件")
    parser.add_argument("--all", action="store_true", help="全量同步仓库内所有可发布文件")
    args = parser.parse_args()

    print("=" * 60)
    print("  数据分析团队 → 阿里云 OSS 同步")
    print("=" * 60)

    config = load_oss_config()
    if not config:
        print("[ERROR] 找不到 OSS 配置")
        print("  CI 环境: 请在 GitHub Secrets 中配置 OSS_ACCESS_KEY_ID 等")
        print("  本地运行: 请创建 oss_config.json")
        sys.exit(1)

    required = ["access_key_id", "access_key_secret", "bucket_name", "endpoint"]
    missing = [k for k in required if not config.get(k)]
    if missing:
        print(f"[ERROR] OSS 配置缺少: {missing}")
        sys.exit(1)

    base_path = config.get("base_path", "").strip("/")
    print(f"  Bucket  : {config['bucket_name']}")
    print(f"  Endpoint: {config['endpoint']}")
    print(f"  BasePath: {base_path or '(根目录)'}")
    print()

    # 确定要同步的文件
    if args.all or not args.files:
        targets = collect_all_files(".")
        print(f"  全量扫描，找到 {len(targets)} 个可同步文件")
    else:
        targets = [f.replace("\\", "/") for f in args.files if is_syncable(f) and os.path.exists(f)]
        skipped = [f for f in args.files if f.replace("\\", "/") not in targets]
        if skipped:
            print(f"  跳过（不在同步范围或不存在）: {', '.join(skipped)}")
        print(f"  待同步 {len(targets)} 个文件")

    if not targets:
        print("  没有需要同步的文件。")
        return

    print()

    auth = oss2.Auth(config["access_key_id"], config["access_key_secret"])
    bucket = oss2.Bucket(auth, config["endpoint"], config["bucket_name"])

    ok_count, fail_count = 0, 0
    for fpath in targets:
        oss_key = f"{base_path}/{fpath}" if base_path else fpath
        ct = get_content_type(fpath)
        ok, msg = upload_file(bucket, fpath, oss_key, ct)
        print(f"  [{'OK' if ok else 'FAIL'}] {msg}")
        if ok:
            ok_count += 1
        else:
            fail_count += 1

    print()
    print(f"  完成: {ok_count} 成功, {fail_count} 失败")
    print("=" * 60)

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    main()
