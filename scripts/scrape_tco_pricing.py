#!/usr/bin/env python3
"""
InferenceX TCO Pricing Scraper
================================
自动从 InferenceX 页面的 JS bundle 中提取 GPU TCO 定价数据。

数据结构（硬编码在 _next/static/chunks/xxx.js 中）:
    {
        h100: { vendor: "NVIDIA", arch: "Hopper", label: "H100", sort: 7,
                tdp: 700, power: 1.73, costh: 1.3, costn: 1.69, costr: 1.3 },
        ...
    }

功能：
    1. 抓取最新 TCO 定价
    2. 与上次抓取的历史数据对比，检测变化
    3. 保存历史记录（JSON 每日快照 + 追加 CSV + 变更日志）
    4. 完整日志写入本地文件
    5. 支持定时运行（cron 友好）

用法：
    # 单次运行
    python scripts/scrape_tco_pricing.py

    # 强制写入（即使无变化也保存当天快照）
    python scripts/scrape_tco_pricing.py --force

    # 自动安装 cron 定时任务（每天 08:00 运行）
    python scripts/scrape_tco_pricing.py --install-cron
"""

import csv
import json
import logging
import re
import os
import sys
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ============================================================
# 路径配置
# ============================================================
BASE_URL = "https://inferencex.semianalysis.com"
PAGE_URL = f"{BASE_URL}/inference"
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_DIR = SCRIPT_DIR.parent

# 数据目录
DATA_DIR = PROJECT_DIR / "json_data" / "tco_history"
DAILY_DIR = DATA_DIR / "daily"           # 每日快照目录

# 日志目录
LOG_DIR = PROJECT_DIR / "logs" / "tco_scraper"

# 核心文件
LATEST_FILE = DATA_DIR / "tco_latest.json"
HISTORY_FILE = DATA_DIR / "tco_history.csv"
CHANGELOG_FILE = DATA_DIR / "tco_changelog.md"

# 已知 GPU keys（用于验证提取结果的完整性）
EXPECTED_GPUS = {"h100", "h200", "b200", "b300", "gb200", "gb300", "mi300x", "mi325x", "mi355x"}


# ============================================================
# 日志设置 — 同时输出到终端和本地日志文件
# ============================================================
def setup_logging() -> logging.Logger:
    """配置 logging，同时写入文件和终端"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # 日志文件名按日期轮转
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"tco_scraper_{today}.log"

    logger = logging.getLogger("tco_scraper")
    logger.setLevel(logging.DEBUG)

    # 文件 handler — 详细日志
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    # 终端 handler — 简洁输出
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info(f"📝 Log file: {log_file}")
    return logger


log = setup_logging()


# ============================================================
# 网络请求
# ============================================================
def fetch_url(url: str) -> str:
    """用 curl 获取 URL 内容（避免 Python requests 在某些环境下的超时/缓冲问题）"""
    log.debug(f"Fetching: {url}")
    result = subprocess.run(
        ["curl", "-s", "-L", "--max-time", "30", url],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        raise RuntimeError(f"curl failed (exit {result.returncode}): {result.stderr}")
    log.debug(f"  → {len(result.stdout)} bytes")
    return result.stdout


# ============================================================
# JS Bundle 查找和数据提取
# ============================================================
def find_tco_bundle(html: str) -> tuple[str, str]:
    """
    从页面 HTML 中定位包含 TCO 数据的 JS bundle。
    返回 (bundle_url, js_content)。
    """
    chunks = list(set(re.findall(r'/_next/static/chunks/[\w\.\-~]+\.js', html)))

    if not chunks:
        raise RuntimeError("No JS chunks found in page HTML")

    log.info(f"   Found {len(chunks)} unique JS chunks, scanning for TCO data...")

    for chunk_path in chunks:
        url = f"{BASE_URL}{chunk_path}"
        try:
            js = fetch_url(url)
            if 'costn:' in js and 'costh:' in js and 'h100:' in js:
                log.info(f"   ✅ Found TCO bundle: {chunk_path}")
                return url, js
        except Exception as e:
            log.warning(f"   ⚠️  Failed to fetch {chunk_path}: {e}")
            continue

    raise RuntimeError("Could not find JS bundle containing TCO pricing data")


def extract_gpu_specs(js_content: str) -> dict:
    """从 minified JS 中提取 GPU spec 数据"""
    lines = js_content.split('}')
    gpu_data = {}

    for line in lines:
        if 'costh:' not in line or 'vendor:' not in line:
            continue

        gpu_match = re.search(r'[,{](\w+):\{.*?vendor:', line)
        if not gpu_match:
            continue
        gpu_key = gpu_match.group(1)

        def extract_str(field):
            m = re.search(rf'{field}:"([^"]*)"', line)
            return m.group(1) if m else None

        def extract_num(field):
            m = re.search(rf'{field}:([\d.e]+)', line)
            return float(m.group(1)) if m else None

        spec = {
            "vendor": extract_str("vendor"),
            "arch": extract_str("arch"),
            "label": extract_str("label"),
            "sort": extract_num("sort"),
            "tdp": extract_num("tdp"),
            "power": extract_num("power"),
            "costh": extract_num("costh"),
            "costn": extract_num("costn"),
            "costr": extract_num("costr"),
        }

        # 处理 tdp 科学计数法 (1e3 → 1000)
        if spec["tdp"] and spec["tdp"] < 10:
            spec["tdp"] = spec["tdp"] * 1000

        gpu_data[gpu_key] = spec

    return gpu_data


def extract_cost_formula(js_content: str) -> dict:
    """提取成本计算公式中的权重参数"""
    formulas = {}
    for label, pattern_key in [("input_weight", "inputTputPerGpu"), ("output_weight", "outputTputPerGpu")]:
        m = re.search(rf'{pattern_key}.*?(\.\d+)\*.*?tpPerGpu.*?costn/o', js_content, re.DOTALL)
        if m:
            formulas[label] = float(m.group(1))
    return formulas


# ============================================================
# 数据对比
# ============================================================
def load_previous_data() -> dict | None:
    if LATEST_FILE.exists():
        with open(LATEST_FILE, 'r') as f:
            return json.load(f)
    return None


def compare_data(old_data: dict, new_data: dict) -> list:
    """对比新旧数据，返回变化列表"""
    changes = []
    cost_fields = ['costh', 'costn', 'costr', 'power', 'tdp']

    old_gpus = old_data.get('gpu_specs', {})
    new_gpus = new_data.get('gpu_specs', {})

    all_keys = set(list(old_gpus.keys()) + list(new_gpus.keys()))
    for gpu_key in sorted(all_keys):
        if gpu_key not in old_gpus:
            changes.append({'type': 'NEW_GPU', 'gpu': gpu_key,
                            'detail': f"New GPU added: {gpu_key}", 'new_data': new_gpus[gpu_key]})
            continue
        if gpu_key not in new_gpus:
            changes.append({'type': 'REMOVED_GPU', 'gpu': gpu_key,
                            'detail': f"GPU removed: {gpu_key}", 'old_data': old_gpus[gpu_key]})
            continue

        for field in cost_fields:
            old_val = old_gpus[gpu_key].get(field)
            new_val = new_gpus[gpu_key].get(field)
            if old_val != new_val:
                pct = ((new_val - old_val) / old_val * 100) if old_val else 0
                changes.append({
                    'type': 'PRICE_CHANGE', 'gpu': gpu_key, 'field': field,
                    'old_value': old_val, 'new_value': new_val,
                    'change_pct': round(pct, 2),
                    'detail': f"{gpu_key}.{field}: {old_val} → {new_val} ({pct:+.1f}%)"
                })

    return changes


# ============================================================
# 数据保存 — 核心：每次都保存每日快照 + 追加历史
# ============================================================
def save_data(data: dict, changes: list):
    """保存抓取结果到多个位置"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DAILY_DIR.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")

    # ---- 1. 最新快照（覆盖写入） ----
    with open(LATEST_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log.debug(f"Saved latest snapshot: {LATEST_FILE}")

    # ---- 2. 每日快照（每天一个独立 JSON 文件） ----
    daily_json = DAILY_DIR / f"tco_{today}.json"
    with open(daily_json, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log.info(f"   📅 Daily snapshot: {daily_json}")

    # ---- 3. 每日价格汇总 CSV（一天一行，便于追踪趋势） ----
    daily_summary_csv = DATA_DIR / "tco_daily_summary.csv"
    csv_new = not daily_summary_csv.exists()
    gpu_keys_sorted = sorted(data['gpu_specs'].keys())

    # 构建表头和数据行
    header = ['date', 'bundle_hash']
    for gpu in gpu_keys_sorted:
        for tier in ['costh', 'costn', 'costr']:
            header.append(f"{gpu}_{tier}")

    row = [today, data.get('bundle_url', '').split('/')[-1].replace('.js', '')]
    for gpu in gpu_keys_sorted:
        spec = data['gpu_specs'][gpu]
        for tier in ['costh', 'costn', 'costr']:
            row.append(spec.get(tier, ''))

    with open(daily_summary_csv, 'a', newline='') as f:
        writer = csv.writer(f)
        if csv_new:
            writer.writerow(header)
        writer.writerow(row)
    log.info(f"   📊 Daily summary CSV: {daily_summary_csv}")

    # ---- 4. 完整历史 CSV（每行一个 GPU，追加模式） ----
    history_new = not HISTORY_FILE.exists()
    with open(HISTORY_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        if history_new:
            writer.writerow([
                'timestamp', 'date', 'gpu', 'label', 'vendor', 'arch',
                'tdp_w', 'power_factor', 'costh', 'costn', 'costr',
                'bundle_url'
            ])
        for gpu_key, spec in sorted(data['gpu_specs'].items()):
            writer.writerow([
                data['timestamp'], today, gpu_key, spec.get('label', ''),
                spec.get('vendor', ''), spec.get('arch', ''),
                spec.get('tdp', ''), spec.get('power', ''),
                spec.get('costh', ''), spec.get('costn', ''), spec.get('costr', ''),
                data.get('bundle_url', '')
            ])
    log.debug(f"Appended to history CSV: {HISTORY_FILE}")

    # ---- 5. 变更日志（Markdown） ----
    if changes:
        with open(CHANGELOG_FILE, 'a') as f:
            f.write(f"\n## {data['timestamp']} ({today})\n\n")
            f.write(f"Bundle: `{data.get('bundle_url', 'unknown')}`\n\n")
            for c in changes:
                if c['type'] == 'PRICE_CHANGE':
                    emoji = "📈" if c['change_pct'] > 0 else "📉"
                    f.write(f"- {emoji} **{c['detail']}**\n")
                elif c['type'] == 'NEW_GPU':
                    f.write(f"- 🆕 **{c['detail']}**\n")
                elif c['type'] == 'REMOVED_GPU':
                    f.write(f"- ❌ **{c['detail']}**\n")
            f.write("\n")
        log.info(f"   📋 Changelog updated: {CHANGELOG_FILE}")


# ============================================================
# 输出摘要
# ============================================================
def print_summary(data: dict, changes: list):
    log.info("")
    log.info("=" * 90)
    log.info("💰 InferenceX TCO Pricing Snapshot")
    log.info("=" * 90)
    log.info(f"   Timestamp:  {data['timestamp']}")
    log.info(f"   Bundle URL: {data.get('bundle_url', 'N/A')}")

    header = (f"{'GPU':>10s}  {'Label':>12s}  {'Vendor':>8s}  {'Arch':>12s}  "
              f"{'TDP(W)':>7s}  {'Hyperscaler':>12s}  {'Neocloud':>10s}  {'3Y Rental':>10s}")
    log.info(f"\n{header}")
    log.info("-" * 100)

    for gpu_key in sorted(data['gpu_specs'].keys(),
                          key=lambda k: data['gpu_specs'][k].get('sort', 99)):
        s = data['gpu_specs'][gpu_key]
        tdp_str = f"{int(s['tdp'])}" if s.get('tdp') else "?"
        log.info(f"{gpu_key:>10s}  {s.get('label',''):>12s}  {s.get('vendor',''):>8s}  "
                 f"{s.get('arch',''):>12s}  {tdp_str:>7s}  "
                 f"${s.get('costh',0):>10.3f}  ${s.get('costn',0):>8.3f}  ${s.get('costr',0):>8.3f}")

    if changes:
        log.info(f"\n⚠️  {len(changes)} CHANGE(S) detected since last scrape:")
        for c in changes:
            log.info(f"   • {c['detail']}")
    else:
        log.info("\n✅ No changes since last scrape")

    log.info(f"\n📁 Data saved to:")
    log.info(f"   Latest JSON:   {LATEST_FILE}")
    log.info(f"   Daily snapshot: {DAILY_DIR}/")
    log.info(f"   History CSV:    {HISTORY_FILE}")
    log.info(f"   Daily CSV:      {DATA_DIR / 'tco_daily_summary.csv'}")
    log.info(f"   Cron log:       {LOG_DIR}/")
    log.info("=" * 90)


# ============================================================
# Cron 安装
# ============================================================
def install_cron():
    """自动安装 cron 定时任务"""
    script_path = Path(__file__).resolve()
    project_dir = script_path.parent.parent
    cron_line = f"0 8 * * * cd {project_dir} && /usr/bin/python3 {script_path} --force 2>&1\n"

    # 读取当前 crontab
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    current_crontab = result.stdout if result.returncode == 0 else ""

    # 检查是否已安装
    if "scrape_tco_pricing" in current_crontab:
        log.info("⚠️  Cron job already exists:")
        for line in current_crontab.splitlines():
            if "scrape_tco_pricing" in line:
                log.info(f"   {line}")
        log.info("   To remove: crontab -e")
        return

    # 追加新任务
    new_crontab = current_crontab.rstrip('\n') + '\n' + cron_line
    proc = subprocess.run(["crontab", "-"], input=new_crontab, text=True, capture_output=True)
    if proc.returncode == 0:
        log.info("✅ Cron job installed successfully!")
        log.info(f"   Schedule: Every day at 08:00")
        log.info(f"   Command:  {cron_line.strip()}")
    else:
        log.error(f"❌ Failed to install cron: {proc.stderr}")


# ============================================================
# 主流程
# ============================================================
def main():
    # 处理 --install-cron
    if '--install-cron' in sys.argv:
        install_cron()
        return 0

    force = '--force' in sys.argv

    log.info("🔍 InferenceX TCO Pricing Scraper")
    log.info(f"   Target: {PAGE_URL}")
    log.info(f"   Time:   {datetime.now(timezone.utc).isoformat()}")
    log.info(f"   Mode:   {'force' if force else 'normal'}")

    # Step 1: 获取页面
    log.info("\n📡 Step 1: Fetching page HTML...")
    html = fetch_url(PAGE_URL)
    log.info(f"   HTML size: {len(html)} bytes")

    # Step 2: 定位 TCO bundle
    log.info("\n📦 Step 2: Scanning JS bundles for TCO data...")
    bundle_url, js_content = find_tco_bundle(html)

    # Step 3: 提取数据
    log.info("\n🔧 Step 3: Extracting GPU specs...")
    gpu_specs = extract_gpu_specs(js_content)
    log.info(f"   Extracted {len(gpu_specs)} GPUs: {', '.join(sorted(gpu_specs.keys()))}")

    missing = EXPECTED_GPUS - set(gpu_specs.keys())
    if missing:
        log.warning(f"   ⚠️  Missing expected GPUs: {missing}")

    extra = set(gpu_specs.keys()) - EXPECTED_GPUS
    if extra:
        log.info(f"   🆕 New GPUs detected: {extra}")

    formulas = extract_cost_formula(js_content)
    if formulas:
        log.info(f"   📐 Cost formula weights: {formulas}")

    # 构建数据包
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = {
        "timestamp": now_utc,
        "bundle_url": bundle_url,
        "gpu_specs": gpu_specs,
        "formulas": formulas,
        "source": "inferencex.semianalysis.com",
    }

    # Step 4: 对比 & 保存
    log.info("\n📊 Step 4: Comparing with previous data...")
    prev_data = load_previous_data()
    changes = []

    if prev_data:
        changes = compare_data(prev_data, data)
        if changes:
            log.info(f"   🔔 {len(changes)} change(s) detected!")
            save_data(data, changes)
        elif force:
            log.info("   No changes, but --force enabled. Saving anyway.")
            save_data(data, [])
        else:
            log.info("   No changes. Saving daily snapshot only.")
            # 即使无变化也保存每日快照（用于完整历史记录）
            save_data(data, [])
    else:
        log.info("   No previous data. Saving initial snapshot.")
        save_data(data, [])

    # Step 5: 输出摘要
    print_summary(data, changes)

    log.info(f"\n✅ Done. Exit code: {'1 (changed)' if changes else '0 (unchanged)'}")
    return 1 if changes else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log.error(f"\n❌ Error: {e}")
        log.debug("Traceback:", exc_info=True)
        sys.exit(2)
