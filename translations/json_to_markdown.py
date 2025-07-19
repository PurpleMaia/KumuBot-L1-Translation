#!/usr/bin/env python3
"""Convert hybrid complex analysis JSON results back to markdown format."""

import json
import os
import sys
import argparse
import re
from pathlib import Path


def load_json_files(output_dir, task_name):
    """Load all JSON files for the given task."""
    passages = {}
    summaries = {}
    model_key = None
    
    # Find all passage files matching the pattern
    passage_pattern = re.compile(f"{task_name}_passage_(\\d+)_(\\d+)\\.json")
    manifest_pattern = re.compile(f"{task_name}_chapter_(\\d+)_manifest\\.json")
    
    # Construct full path to translations directory
    output_path = Path("translations") / output_dir
    
    # Load passage files
    for file_path in output_path.glob(f"{task_name}_passage_*.json"):
        match = passage_pattern.match(file_path.name)
        if match:
            chapter = int(match.group(1))
            passage = int(match.group(2))
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Extract model key from the first file if not already found
                if not model_key:
                    for key in data:
                        if key.endswith('_translation') and not key.startswith('reference_'):
                            model_key = key.replace('_translation', '')
                            break
                
                if chapter not in passages:
                    passages[chapter] = {}
                passages[chapter][passage] = data
    
    # Load manifest files for summaries
    for file_path in output_path.glob(f"{task_name}_chapter_*_manifest.json"):
        match = manifest_pattern.match(file_path.name)
        if match:
            chapter = int(match.group(1))
            
            with open(file_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
                
                # Extract model key if not found yet
                if not model_key:
                    for key in manifest:
                        if key.endswith('_summary'):
                            model_key = key.replace('_summary', '')
                            break
                
                if model_key:
                    summary = manifest.get(f"{model_key}_summary")
                    if summary:
                        summaries[chapter] = summary
    
    return passages, summaries, model_key


def create_markdown(passages, summaries, model_key):
    """Create markdown content from passages and summaries."""
    lines = []
    
    # Create table header
    lines.append("| Source Text | Translation | Commentary |")
    lines.append("| ----- | ----- | ----- |")
    
    # Process all chapters
    for chapter in sorted(passages.keys()):
        chapter_passages = passages[chapter]
        
        # Process passages in order
        for passage_num in sorted(chapter_passages.keys()):
            p = chapter_passages[passage_num]
            
            hawaiian = p.get('hawaiian_text', '').replace('\n', ' ')
            translation = p.get(f'{model_key}_translation', '').replace('\n', ' ')
            
            # Handle special case for grouped commentary
            if p.get('special_case') == 'grouped_commentary' and 'raw_response' in p:
                # Extract commentary from raw_response for special cases
                raw_response = p['raw_response']
                import re
                commentary_match = re.search(r'<commentary>(.*?)</commentary>', raw_response, re.DOTALL)
                if commentary_match:
                    commentary = commentary_match.group(1).strip().replace('\n', ' ')
                else:
                    commentary = p.get(f'{model_key}_commentary', '').replace('\n', ' ')
            else:
                commentary = p.get(f'{model_key}_commentary', '').replace('\n', ' ')
            
            # Add paragraph number to text
            hawaiian = f"**{passage_num}:** {hawaiian}"
            translation = f"**{passage_num}:** {translation}"
            
            lines.append(f"| {hawaiian} | {translation} | {commentary} |")
    
    lines.append("")
    
    # Add summary sections if available
    if summaries:
        for chapter in sorted(summaries.keys()):
            summary = summaries[chapter]
            if len(summaries) > 1:
                lines.append(f"**Chapter {chapter} Summary:** ")
            else:
                lines.append("**Summary:** ")
            lines.append("")
            
            # Split summary into paragraphs
            summary_paragraphs = summary.split('\n\n')
            for para in summary_paragraphs:
                lines.append(para.strip())
                lines.append("")
    
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Convert hybrid complex analysis JSON to markdown')
    parser.add_argument('--output-dir', required=True, help='Output directory containing JSON files')
    parser.add_argument('--task-name', required=True, help='Task name (e.g., hybrid_complex_analysis_enhanced_fewshot)')
    parser.add_argument('--output-file', help='Output markdown file path (default: OUTPUT_DIR_TASK_NAME.md)')
    
    args = parser.parse_args()
    
    # Load JSON files
    passages, summaries, model_key = load_json_files(args.output_dir, args.task_name)
    
    if not passages:
        print(f"Error: No passage files found in {args.output_dir} for task {args.task_name}")
        sys.exit(1)
    
    # Create markdown
    markdown_content = create_markdown(passages, summaries, model_key)
    
    # Determine output file
    if args.output_file:
        output_path = args.output_file
    else:
        output_dir_name = os.path.basename(args.output_dir)
        output_path = f"{output_dir_name}_{args.task_name}.md"
    
    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    # Report statistics
    total_passages = sum(len(chapter_passages) for chapter_passages in passages.values())
    chapters = sorted(passages.keys())
    
    print(f"Successfully created markdown file: {output_path}")
    print(f"Found {total_passages} passages across {len(chapters)} chapter(s): {chapters}")
    print(f"Found summaries for chapters: {sorted(summaries.keys()) if summaries else 'None'}")
    print(f"Model: {model_key}")


if __name__ == '__main__':
    main()