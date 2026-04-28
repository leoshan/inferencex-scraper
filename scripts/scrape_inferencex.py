#!/usr/bin/env python3
"""
InferenceX 数据采集脚本 v3 - 使用新的 /api/v1 端点采集 LLM 推理性能基准数据

新 API 结构:
  1. /api/v1/availability  → 返回所有可用的 model/hardware/framework/date 组合列表
  2. /api/v1/benchmarks?model={display_name}&date={date} → 返回具体模型在指定日期的全部性能数据
  3. /api/v1/workflow-info?date={date} → 返回工作流元数据

数据流程:
  1. 从 /api/v1/availability 获取所有可用组合
  2. 从中提取唯一的 model+date 对
  3. 调用 /api/v1/benchmarks 获取每个 model+date 的完整性能数据
  4. 按模型保存为 JSON 文件
"""

import subprocess
import json
import time
import os
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Set
import logging

logger = logging.getLogger(__name__)

# ─── API 配置 ──────────────────────────────────────────────────────────────────

API_BASE_URL = "https://inferencex.semianalysis.com/api/v1"

# ─── availability 中的 model ID → 网站上使用的 display name 映射 ────────────────
# availability 返回的 model 字段是短 ID (如 "llama70b")
# benchmarks API 需要的是 display name (如 "Llama-3.3-70B-Instruct-FP8")
# 这个映射可以从网站的模型选择器中获取
MODEL_DISPLAY_NAMES = {
    "llama70b": "Llama-3.3-70B-Instruct-FP8",
    "dsr1": "DeepSeek-R1-0528",
    "gptoss120b": "gpt-oss-120B",
    "kimik2.5": "Kimi-K2.5",
    "minimaxm2.5": "MiniMax-M2.5",
    "qwen3.5": "Qwen-3.5-397B-A17B",
    "glm5": "GLM-5",
}

# 反向映射: display name → model ID
DISPLAY_NAME_TO_ID = {v: k for k, v in MODEL_DISPLAY_NAMES.items()}

# 用户友好名称 → model ID 映射
USER_FRIENDLY_NAMES = {
    "Llama 3.3 70B Instruct": "llama70b",
    "gpt-oss 120B": "gptoss120b",
    "DeepSeek R1 0528": "dsr1",
    "Kimi K2.5": "kimik2.5",
    "MiniMax M2.5": "minimaxm2.5",
    "Qwen 3.5 397B-A17B": "qwen3.5",
    "GLM 5": "glm5",
}

DEFAULT_MODELS = list(MODEL_DISPLAY_NAMES.keys())  # 默认采集所有已知模型

DEFAULT_SEQUENCES = ["1K / 1K", "1K / 8K", "8K / 1K"]


# ─── 工具函数 ─────────────────────────────────────────────────────────────────

def curl_fetch(url: str, timeout: int = 120) -> Tuple[Optional[str], int]:
    """
    使用 curl 获取 URL 内容（避免 Python requests SSL 挂起问题）

    Returns:
        (response_body, http_status_code)
    """
    try:
        result = subprocess.run(
            ['curl', '-sL', '--compressed', '--max-time', str(timeout),
             '-w', '\n__HTTP_CODE__%{http_code}',
             '-H', 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
             '-H', 'Accept: application/json',
             url],
            capture_output=True, text=True, timeout=timeout + 10
        )

        if result.returncode != 0:
            logger.error(f"curl failed with exit code {result.returncode}: {result.stderr}")
            return None, 0

        output = result.stdout
        if '__HTTP_CODE__' in output:
            parts = output.rsplit('\n__HTTP_CODE__', 1)
            body = parts[0]
            http_code = int(parts[1].strip()) if len(parts) > 1 else 0
        else:
            body = output
            http_code = 200

        return body, http_code

    except subprocess.TimeoutExpired:
        logger.error(f"curl timeout after {timeout}s for {url}")
        return None, 0
    except Exception as e:
        logger.error(f"curl error for {url}: {e}")
        return None, 0


def seq_to_isl_osl(sequence: str) -> Tuple[int, int]:
    """将序列格式转换为 isl/osl 数值: '1K / 8K' -> (1024, 8192)"""
    seq = sequence.lower().replace(' ', '')
    parts = seq.split('/')
    if len(parts) != 2:
        return 0, 0

    def parse_k(s):
        s = s.strip().lower()
        if s.endswith('k'):
            return int(s[:-1]) * 1024
        return int(s)

    return parse_k(parts[0]), parse_k(parts[1])


# ─── 数据采集器 ───────────────────────────────────────────────────────────────

class APIDataCollector:
    """API数据采集器 - 适配新的 /api/v1 端点"""

    def __init__(self, base_url: str = API_BASE_URL, timeout: int = 120):
        self.base_url = base_url
        self.timeout = timeout
        self.availability = None  # 缓存 availability 数据

    def fetch_availability(self) -> List[Dict]:
        """获取 /api/v1/availability，返回所有可用的配置组合列表"""
        if self.availability is not None:
            return self.availability

        url = f"{self.base_url}/availability"
        logger.info(f"Fetching availability: {url}")

        body, status = curl_fetch(url, timeout=60)
        if status == 200 and body:
            try:
                self.availability = json.loads(body)
                logger.info(f"Availability loaded: {len(self.availability)} entries")
                return self.availability
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse availability JSON: {e}")
                return []
        else:
            logger.error(f"Failed to fetch availability: HTTP {status}")
            return []

    def get_available_models(self) -> Set[str]:
        """获取所有可用的 model ID"""
        avail = self.fetch_availability()
        return set(item.get('model', '') for item in avail if item.get('model'))

    def get_available_dates(self, model_id: str = None) -> List[str]:
        """获取所有可用日期（可选按模型过滤）"""
        avail = self.fetch_availability()
        dates = set()
        for item in avail:
            if model_id and item.get('model') != model_id:
                continue
            date = item.get('date', '')
            if date:
                dates.add(date)
        return sorted(dates)

    def get_latest_date(self, model_id: str = None) -> Optional[str]:
        """获取最新的可用日期"""
        dates = self.get_available_dates(model_id)
        return dates[-1] if dates else None

    def get_model_display_name(self, model_id: str) -> str:
        """获取模型的 display name（用于 benchmarks API）"""
        return MODEL_DISPLAY_NAMES.get(model_id, model_id)

    def resolve_model_id(self, model_name: str) -> str:
        """将用户输入的模型名称解析为 model ID"""
        # 先检查是否已经是 model ID
        if model_name in MODEL_DISPLAY_NAMES:
            return model_name
        # 检查用户友好名称
        if model_name in USER_FRIENDLY_NAMES:
            return USER_FRIENDLY_NAMES[model_name]
        # 检查 display name
        if model_name in DISPLAY_NAME_TO_ID:
            return DISPLAY_NAME_TO_ID[model_name]
        # 尝试模糊匹配
        model_lower = model_name.lower()
        for uid, mid in USER_FRIENDLY_NAMES.items():
            if model_lower in uid.lower() or uid.lower() in model_lower:
                return mid
        # 原样返回
        return model_name

    def fetch_benchmarks(self, model_id: str, date: str) -> Tuple[Optional[List], str]:
        """
        获取指定模型在指定日期的全部 benchmark 数据

        Args:
            model_id: 模型 ID (如 'llama70b')
            date: 日期 (如 '2025-10-29')

        Returns:
            (data_list, url) - data 是包含所有指标的记录列表
        """
        display_name = self.get_model_display_name(model_id)
        url = f"{self.base_url}/benchmarks?model={display_name}&date={date}"

        logger.info(f"Fetching benchmarks: {url}")
        body, status = curl_fetch(url, timeout=self.timeout)

        if status == 200 and body:
            try:
                data = json.loads(body)
                if isinstance(data, dict) and 'error' in data:
                    logger.error(f"API error for {model_id}: {data['error']}")
                    return None, url
                if isinstance(data, list):
                    return data, url
                else:
                    logger.warning(f"Unexpected response type for {url}: {type(data)}")
                    return None, url
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error for {url}: {e}")
                return None, url
        else:
            logger.error(f"HTTP {status} for {url}")
            return None, url

    def filter_by_sequence(self, data: List[Dict], sequences: List[str] = None) -> Dict[str, List[Dict]]:
        """
        按序列长度过滤数据

        Returns:
            字典: {sequence_key: [records]}
        """
        if sequences is None:
            sequences = DEFAULT_SEQUENCES

        result = {}
        for seq in sequences:
            isl, osl = seq_to_isl_osl(seq)
            seq_key = f"{isl}_{osl}"
            seq_data = [
                record for record in data
                if record.get('isl') == isl and record.get('osl') == osl
            ]
            if seq_data:
                result[seq_key] = seq_data

        return result

    def analyze_data(self, data: List[Dict]) -> Dict:
        """分析数据统计信息"""
        if not data:
            return {
                'record_count': 0,
                'hardware': set(),
                'frameworks': set(),
                'precisions': set(),
                'conc_levels': set(),
                'sequences': set(),
            }

        hardware = set()
        frameworks = set()
        precisions = set()
        conc_levels = set()
        sequences = set()

        for item in data:
            hw = str(item.get('hardware', ''))
            if hw:
                hardware.add(hw)
            fw = str(item.get('framework', ''))
            if fw:
                frameworks.add(fw)
            prec = str(item.get('precision', ''))
            if prec:
                precisions.add(prec)
            conc = item.get('conc')
            if conc is not None:
                conc_levels.add(conc)
            isl = item.get('isl')
            osl = item.get('osl')
            if isl is not None and osl is not None:
                sequences.add(f"{isl}_{osl}")

        return {
            'record_count': len(data),
            'hardware': hardware,
            'frameworks': frameworks,
            'precisions': precisions,
            'conc_levels': conc_levels,
            'sequences': sequences,
        }

    def save_json_file(self, data: List[Dict], model_id: str,
                       output_dir: str, date: str = '', url: str = '',
                       response_index: int = 1) -> str:
        """保存JSON文件"""
        os.makedirs(output_dir, exist_ok=True)

        display_name = self.get_model_display_name(model_id)
        filename = f"{response_index:02d}_{model_id}_benchmarks.json"
        filepath = os.path.join(output_dir, filename)

        analysis = self.analyze_data(data)

        file_data = {
            'metadata': {
                'combination_index': response_index,
                'model_id': model_id,
                'model_display_name': display_name,
                'timestamp': datetime.now().isoformat(),
                'url': url,
                'data_date': date,
                'api_version': 'v3-api-v1',
                'record_count': analysis['record_count'],
                'hardware': sorted(list(analysis['hardware'])),
                'frameworks': sorted(list(analysis['frameworks'])),
                'precisions': sorted(list(analysis['precisions'])),
                'conc_levels': sorted(list(analysis['conc_levels'])),
                'sequences': sorted(list(analysis['sequences'])),
            },
            'data': data
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(file_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved: {filename} ({analysis['record_count']} records, date={date})")
        return filepath

    def collect_all_data(self, model_ids: List[str], sequences: List[str],
                         output_dir: str, date: str = None) -> Dict:
        """采集所有数据"""
        print("📥 Fetching availability index...")
        availability = self.fetch_availability()
        if not availability:
            print("❌ Failed to fetch availability index!")
            return {
                'successful_collections': [],
                'failed_collections': [],
                'total_files': 0,
                'total_records': 0,
                'model_stats': {},
                'error': 'Failed to fetch availability index'
            }

        available_models = self.get_available_models()
        print(f"✅ Availability loaded: {len(availability)} entries, "
              f"{len(available_models)} unique models: {sorted(available_models)}")

        results = {
            'successful_collections': [],
            'failed_collections': [],
            'total_files': 0,
            'total_records': 0,
            'model_stats': {},
            'availability_entries': len(availability),
            'available_models': sorted(available_models),
        }

        response_index = 1

        for model_id in model_ids:
            # 确认模型在 availability 中存在
            if model_id not in available_models:
                print(f"\n❌ Model '{model_id}' not found in availability. "
                      f"Available: {sorted(available_models)}")
                results['failed_collections'].append({
                    'model_id': model_id,
                    'error': 'Model not in availability',
                })
                continue

            # 确定日期
            target_date = date or self.get_latest_date(model_id)
            if not target_date:
                print(f"\n❌ No dates available for {model_id}")
                results['failed_collections'].append({
                    'model_id': model_id,
                    'error': 'No dates available',
                })
                continue

            display_name = self.get_model_display_name(model_id)
            print(f"\n📊 Collecting {display_name} (id={model_id}) [date: {target_date}]...")

            # 获取 benchmarks 数据
            data, url = self.fetch_benchmarks(model_id, target_date)

            if data:
                # 过滤序列（可选）
                seq_data = self.filter_by_sequence(data, sequences)
                filtered_data = []
                for seq_key, records in seq_data.items():
                    filtered_data.extend(records)

                # 如果有序列过滤，用过滤后的数据；否则用全部数据
                save_data = filtered_data if filtered_data else data

                # 保存
                filepath = self.save_json_file(
                    save_data, model_id, output_dir,
                    date=target_date, url=url,
                    response_index=response_index
                )

                analysis = self.analyze_data(save_data)
                model_stats = {
                    'files': 1,
                    'records': analysis['record_count'],
                    'hardware': sorted(list(analysis['hardware'])),
                    'frameworks': sorted(list(analysis['frameworks'])),
                    'precisions': sorted(list(analysis['precisions'])),
                    'conc_levels': sorted(list(analysis['conc_levels'])),
                    'sequences': sorted(list(analysis['sequences'])),
                    'date': target_date,
                }
                results['model_stats'][model_id] = model_stats
                results['total_files'] += 1
                results['total_records'] += analysis['record_count']
                results['successful_collections'].append({
                    'model_id': model_id,
                    'display_name': display_name,
                    'date': target_date,
                    'record_count': analysis['record_count'],
                    'filepath': filepath,
                    'url': url,
                })

                print(f"✅ Success: {analysis['record_count']} records, "
                      f"HW: {sorted(list(analysis['hardware']))}, "
                      f"Seq: {sorted(list(analysis['sequences']))}")
            else:
                print(f"❌ Failed to fetch benchmarks for {display_name}")
                results['failed_collections'].append({
                    'model_id': model_id,
                    'display_name': display_name,
                    'date': target_date,
                    'error': f'Failed to fetch from {url}',
                })

            response_index += 1
            time.sleep(0.5)

        return results


# ─── 入口函数 ─────────────────────────────────────────────────────────────────

def scrape_api_data(models: List[str] = None, sequences: List[str] = None,
                    output_dir: str = "json_data/raw_json_files",
                    timeout: int = 120, date: str = None) -> Dict:
    """
    采集 InferenceX 性能数据的入口函数

    Args:
        models: 模型列表（可以是 model ID、display name 或用户友好名称）
        sequences: 序列长度列表 (如 ["1K / 1K", "1K / 8K", "8K / 1K"])
        output_dir: 输出目录
        timeout: 请求超时时间（秒）
        date: 指定日期采集（None=最新日期）

    Returns:
        采集结果字典
    """
    # 默认值
    if models is None:
        models = DEFAULT_MODELS
    if sequences is None:
        sequences = DEFAULT_SEQUENCES

    # 创建采集器
    collector = APIDataCollector(timeout=timeout)

    # 解析模型名称
    model_ids = [collector.resolve_model_id(m) for m in models]

    print("🚀 Starting InferenceX data collection (API v1)...")
    print(f"📋 Target models: {model_ids}")
    print(f"📋 Target sequences: {sequences}")
    print(f"📁 Output directory: {output_dir}")
    if date:
        print(f"📅 Target date: {date}")

    os.makedirs(output_dir, exist_ok=True)

    # 开始采集
    start_time = time.time()
    results = collector.collect_all_data(model_ids, sequences, output_dir, date)
    elapsed_time = time.time() - start_time

    # 更新统计
    results['elapsed_time'] = elapsed_time
    results['timestamp'] = datetime.now().isoformat()
    results['api_version'] = 'v3-api-v1'
    results['base_url'] = collector.base_url

    # 打印结果
    print(f"\n{'='*80}")
    print(f"📈 Collection Statistics:")
    print(f"{'='*80}")
    print(f"Elapsed time: {elapsed_time:.1f} seconds")
    print(f"Total files: {results['total_files']}")
    print(f"Total records: {results['total_records']}")
    print(f"Successful models: {len(results['successful_collections'])}")
    print(f"Failed models: {len(results['failed_collections'])}")

    print(f"\n📊 Model Details:")
    for model_id, stats in results['model_stats'].items():
        display_name = MODEL_DISPLAY_NAMES.get(model_id, model_id)
        print(f"\n🔸 {display_name} ({model_id}):")
        print(f"  Records: {stats['records']}")
        print(f"  Hardware: {stats['hardware']}")
        print(f"  Frameworks: {stats['frameworks']}")
        print(f"  Precisions: {stats['precisions']}")
        print(f"  Concurrency levels: {stats['conc_levels']}")
        print(f"  Sequences: {stats['sequences']}")
        print(f"  Date: {stats['date']}")

    # 保存总结报告
    summary_file = os.path.join(output_dir, 'api_scraping_summary.json')
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n📋 Summary saved: {summary_file}")

    return results


# ─── CLI 入口 ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="InferenceX 推理性能数据采集 (API v1)"
    )
    parser.add_argument(
        '--output-dir', '-o',
        default='json_data/raw_json_files',
        help='输出目录 (默认: json_data/raw_json_files)'
    )
    parser.add_argument(
        '--models', '-m',
        default=None,
        help='逗号分隔的模型列表 (默认: 所有已知模型)'
    )
    parser.add_argument(
        '--sequences', '-s',
        default=None,
        help='逗号分隔的序列列表 (默认: "1K / 1K,1K / 8K,8K / 1K")'
    )
    parser.add_argument(
        '--date', '-d',
        default=None,
        help='指定采集日期 (如 2025-10-29)，不指定则采集最新数据'
    )
    parser.add_argument(
        '--timeout', '-t',
        type=int, default=120,
        help='请求超时时间（秒）(默认: 120)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='启用详细日志输出'
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')

    models = [m.strip() for m in args.models.split(',')] if args.models else None
    sequences = [s.strip() for s in args.sequences.split(',')] if args.sequences else None

    results = scrape_api_data(models, sequences, args.output_dir, args.timeout, args.date)

    if results.get('total_files', 0) > 0:
        exit(0)
    else:
        print("❌ No data was collected!")
        exit(1)


if __name__ == "__main__":
    main()
