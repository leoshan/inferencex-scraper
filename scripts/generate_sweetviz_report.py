import pandas as pd
import sweetviz as sv
import os

def generate_report():
    input_file = 'json_data/inference_max_merged.csv'
    output_file = 'inference_data_report.html'
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return
    
    print(f"Loading data from {input_file}...")
    df = pd.read_csv(input_file)
    
    print("Generating Sweetviz report...")
    # Analyze the dataframe
    report = sv.analyze(df)
    
    # Save the report
    report.show_html(output_file, open_browser=False)
    print(f"Report generated: {output_file}")

if __name__ == "__main__":
    generate_report()
