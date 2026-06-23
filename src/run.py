import os
import sys
import time
import argparse
import json
from pathlib import Path
from dotenv import load_dotenv

# Ensure the root of the project is in python path
sys.path.append(str(Path(__file__).parent.parent))

from src.triage import triage_message

def parse_args():
    parser = argparse.ArgumentParser(description="Signal CLI Runner (Gemini)")
    parser.add_argument(
        "-i", "--input",
        type=str,
        default="data/messages.txt",
        help="Path to the input text file (one message per line)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="output/results.json",
        help="Path to save the JSON results"
    )
    parser.add_argument(
        "-d", "--dry-run",
        action="store_true",
        help="Perform a dry-run using mock classification rules (does not call Gemini API)"
    )
    return parser.parse_args()

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
    load_dotenv()
    args = parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    if not input_path.exists():
        print(f"Error: Input file '{input_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
        
    with open(input_path, "r", encoding="utf-8") as f:
        messages = [line.strip() for line in f if line.strip()]
        
    if not messages:
        print("No messages found to process.", file=sys.stderr)
        sys.exit(0)
        
    print(f"Processing {len(messages)} messages...")
    
    # Check Gemini API Key
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not args.dry_run and not api_key:
        print("Warning: GEMINI_API_KEY is not set. Falling back to DRY-RUN mode.", file=sys.stderr)
        args.dry_run = True
        
    # Table Header
    print("\n" + "=" * 110)
    print(f"{'#':<3} | {'Category':<18} | {'Priority':<8} | {'Needs Human':<11} | {'Confidence':<10} | {'Summary (truncated 50 chars)'}")
    print("-" * 110)
    
    results = []
    total_processed = len(messages)
    needs_human_count = 0
    total_confidence = 0.0
    total_retries = 0
    fallback_used_count = 0
    priority_counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
    
    for idx, message in enumerate(messages, 1):
        meta = {}
        result = triage_message(message, dry_run=args.dry_run, meta=meta)
        retry_count = meta.get("retry_count", 0)
        

        
        # Extract variables for table and stats
        category = result.get("category", "unclear")
        priority = result.get("priority", "P2")
        needs_human = result.get("needs_human", True)
        confidence = result.get("confidence", 0.0)
        summary = result.get("summary", "")
        
        # Reliability calculations
        used_fallback = (confidence == 0.0 and category == "unclear")
        retried = (retry_count > 0)
        
        if used_fallback:
            fallback_used_count += 1
        total_retries += retry_count
        
        # Add original_message field (first 80 chars) and flags to the result dict
        result["original_message"] = message[:80]
        result["flags"] = {
            "retried": retried,
            "used_fallback": used_fallback
        }
        results.append(result)
        
        # Stats tracking
        if needs_human:
            needs_human_count += 1
        total_confidence += confidence
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        # Print table row
        truncated_summary = summary[:50]
        needs_human_str = "True" if needs_human else "False"
        print(f"{idx:<3} | {category:<18} | {priority:<8} | {needs_human_str:<11} | {confidence:<10.2f} | {truncated_summary}")
        
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save as JSON array
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    # Print final summary
    avg_confidence = total_confidence / total_processed if total_processed > 0 else 0.0
    print("-" * 110)
    print("=== Final Summary ===")
    print(f"  Total Processed  : {total_processed}")
    print(f"  Needs Human      : {needs_human_count}")
    print(f"  Avg Confidence   : {avg_confidence:.2f}")
    print(f"  Total Retries    : {total_retries}")
    print(f"  Fallback Used    : {fallback_used_count}")
    print(f"  P0 Critical      : {priority_counts.get('P0', 0)}")
    print(f"  P1 High          : {priority_counts.get('P1', 0)}")
    print(f"  P2 Medium        : {priority_counts.get('P2', 0)}")
    print(f"  P3 Low           : {priority_counts.get('P3', 0)}")
    print("=====================")

if __name__ == "__main__":
    main()
