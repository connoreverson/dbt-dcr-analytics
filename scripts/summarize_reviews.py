import warnings
warnings.warn(
    "scripts/summarize_reviews.py is deprecated. Use: python -m scripts.reviewer summarize --input <dir>",
    DeprecationWarning,
    stacklevel=2,
)

import os
import yaml
import glob
from collections import defaultdict

def summarize_reviews(input_dir, output_file):
    # Dictionaries to hold our summaries
    # Key: rule_id, Value: {'title': str, 'description': str, 'failures': list of dicts}
    rule_summary = defaultdict(lambda: {'title': '', 'description': '', 'failures': []})
    
    total_files_reviewed = 0
    files_with_failures = set()
    total_failures = 0

    # Iterate over all yaml files in the input directory
    for filepath in glob.glob(os.path.join(input_dir, '*.yml')):
        total_files_reviewed += 1
        model_name = os.path.basename(filepath).replace('.yml', '')
        
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = yaml.safe_load(f)
            except Exception as e:
                print(f"Error parsing {filepath}: {e}")
                continue
                
        if not data or 'rules' not in data:
            continue
            
        for rule in data.get('rules', []):
            if not isinstance(rule, dict):
                continue
            
            eval_data = rule.get('evaluation', {})
            status = None
            
            if isinstance(eval_data, list):
                for eval_item in eval_data:
                    if isinstance(eval_item, dict) and 'status' in eval_item:
                        status = eval_item.get('status')
                        eval_data = eval_item
                        break
            elif isinstance(eval_data, dict):
                status = eval_data.get('status')
            
            if status == 'FAIL':
                rule_id = rule.get('id', 'Unknown')
                rule_summary[rule_id]['title'] = rule.get('title', '')
                rule_summary[rule_id]['description'] = rule.get('description', '')
                
                # Consolidate evidence
                evidence = eval_data.get('evidence', [])
                impacted_files = set()
                for ev in evidence:
                    if 'file' in ev:
                        impacted_files.add(ev['file'])
                
                failure_record = {
                    'model': model_name,
                    'rationale': eval_data.get('rationale', ''),
                    'impacted_files': list(impacted_files)
                }
                
                rule_summary[rule_id]['failures'].append(failure_record)
                files_with_failures.add(model_name)
                total_failures += 1

    # Now generate the summary report
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Review Failures Summary\n\n")
        f.write(f"**Total Files Reviewed:** {total_files_reviewed}\n")
        f.write(f"**Files with Failures:** {len(files_with_failures)}\n")
        f.write(f"**Total Failures:** {total_failures}\n\n")
        
        f.write("## Trends: Most Common Failures\n")
        # Sort rules by number of failures (descending)
        sorted_rules = sorted(rule_summary.items(), key=lambda x: len(x[1]['failures']), reverse=True)
        
        for rule_id, data in sorted_rules:
            num_failures = len(data['failures'])
            f.write(f"* **{rule_id}**: {data['title']} ({num_failures} failures)\n")
            
        f.write("\n## Detailed Breakdown by Rule\n\n")
        
        for rule_id, data in sorted_rules:
            f.write(f"### {rule_id}: {data['title']}\n")
            # Include a truncated description for context
            desc = data['description']
            if desc:
                desc = desc.replace('\n', ' ')
                if len(desc) > 300:
                    desc = desc[:297] + "..."
                f.write(f"> {desc}\n\n")
            
            for fail in data['failures']:
                f.write(f"- **{fail['model']}**: {fail['rationale']}\n")
                if fail['impacted_files']:
                    files_str = ', '.join([f"`{os.path.basename(pf)}`" for pf in fail['impacted_files']])
                    f.write(f"  - *Impacted Files*: {files_str}\n")
            f.write("\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Summarize review yaml files to help an agent plan resolutions.")
    parser.add_argument("--input_dir", default="tmp/reviews", help="Directory containing review yaml files")
    parser.add_argument("--output_file", default="tmp/failed_reviews_summary.md", help="Output markdown file for the summary")
    
    args = parser.parse_args()
    
    os.makedirs(os.path.dirname(os.path.abspath(args.output_file)), exist_ok=True)
    summarize_reviews(args.input_dir, args.output_file)
    print(f"Summary generated successfully at: {args.output_file}")
