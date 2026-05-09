import json
import os
import glob

def process_data():
    raw_dir = 'json_data/raw_json_files'
    json_files = glob.glob(os.path.join(raw_dir, '*.json'))
    
    table_data = []
    
    for file_path in json_files:
        if 'api_scraping_summary.json' in file_path:
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                content = json.load(f)
            except:
                continue
                
        metadata = content.get('metadata', {})
        model_name = metadata.get('model_display_name', '')
        
        # Filter out llama and gpt
        if 'llama' in model_name.lower() or 'gpt' in model_name.lower():
            continue
            
        data_records = content.get('data', [])
        
        # We'll take a subset of records to keep the table manageable
        # Strategy: For each (Model, Hardware, Sequence), pick the best throughput record
        grouped = {}
        for rec in data_records:
            hw = rec.get('hardware', 'unknown')
            isl = rec.get('isl', 0)
            osl = rec.get('osl', 0)
            seq = f"{isl}/{osl}"
            key = (model_name, hw, seq)
            
            metrics = rec.get('metrics', {})
            tput = metrics.get('output_tput_per_gpu', 0)
            
            if key not in grouped or tput > grouped[key].get('metrics', {}).get('output_tput_per_gpu', 0):
                grouped[key] = rec
        
        for key, rec in grouped.items():
            metrics = rec.get('metrics', {})
            table_data.append({
                'Model': key[0],
                'Hardware': key[1].upper(),
                'Sequence': key[2],
                'Conc': rec.get('conc', 1),
                'TTFT_med': round(metrics.get('median_ttft', 0) * 1000, 2), # s to ms
                'TPOT_mean': round(metrics.get('mean_tpot', 0) * 1000, 2), # s to ms
                'Tput/GPU': round(metrics.get('output_tput_per_gpu', 0), 2)
            })

    # Sort by Model then Hardware
    table_data.sort(key=lambda x: (x['Model'], x['Hardware']))
    
    # Generate Markdown
    md_output = "# AI 模型性能对比表 (非 Llama/GPT)\n\n"
    md_output += "本表格展示了各模型在不同硬件和序列长度下的最佳输出吞吐量表现数据。\n\n"
    md_output += "| 模型 | 硬件 | 序列 (ISL/OSL) | 并发 | TTFT (ms) | TPOT (ms) | 吞吐量/GPU |\n"
    md_output += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    
    for row in table_data:
        md_output += f"| {row['Model']} | {row['Hardware']} | {row['Sequence']} | {row['Conc']} | {row['TTFT_med']} | {row['TPOT_mean']} | {row['Tput/GPU']} |\n"
    
    with open('model_performance_comparison.md', 'w', encoding='utf-8') as f:
        f.write(md_output)
    
    print("Successfully generated model_performance_comparison.md")

if __name__ == "__main__":
    process_data()
