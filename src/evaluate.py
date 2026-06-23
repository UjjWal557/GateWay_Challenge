import sys
import os
import time
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Ensure root of project is in python path
sys.path.append(str(Path(__file__).parent.parent))

from src.triage import triage_message, SYSTEM_PROMPT

def main():
    # Configure UTF-8 output encoding to handle checkmarks and emojis on Windows
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
        
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Signal Evaluator")
    parser.add_argument(
        "-d", "--dry-run",
        action="store_true",
        help="Perform evaluations using local mock rules (no API calls)"
    )
    args = parser.parse_args()
    
    api_key = os.environ.get("GEMINI_API_KEY")
    
    dry_run = args.dry_run
    if not dry_run and not api_key:
        print("Note: GEMINI_API_KEY not found on disk. Falling back to DRY-RUN mode.")
        dry_run = True

    # Path setup
    gt_path = Path("data/ground_truth.json")
    if not gt_path.exists():
        print(f"Error: Ground truth file '{gt_path}' not found.", file=sys.stderr)
        sys.exit(1)
        
    with open(gt_path, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)
        
    print(f"Running evaluation on {len(ground_truth)} ground truth cases (dry-run: {dry_run})...\n")
    
    # Print Table Header
    print(f"{'#':<3} | {'Message (35 chars)':<35} | {'Expected Cat':<18} | {'Predicted Cat':<18} | {'Cat✓':<4} | {'Expected Pri':<12} | {'Predicted Pri':<12} | {'Pri✓':<4} | {'Conf':<6} | {'ms':<6}")
    print("-" * 130)
    
    per_message_results = []
    cat_correct = 0
    pri_correct = 0
    needs_human_count = 0
    total_confidence = 0.0
    total_latency_ms = 0
    total_input_tokens = 0
    total_output_tokens = 0
    
    start_total_time = time.time()
    
    for idx, gt in enumerate(ground_truth, 1):
        message = gt["message"]
        expected_cat = gt["expected_category"]
        expected_pri = gt["expected_priority"]
        
        # Track latency
        start_msg_time = time.time()
        result = triage_message(message, dry_run=dry_run)
        latency_ms = int((time.time() - start_msg_time) * 1000)
        

        
        total_latency_ms += latency_ms
        
        # Predictions
        predicted_cat = result.get("category", "unclear")
        predicted_pri = result.get("priority", "P2")
        confidence = result.get("confidence", 0.0)
        needs_human = result.get("needs_human", True)
        
        cat_match = (predicted_cat == expected_cat)
        pri_match = (predicted_pri == expected_pri)
        
        if cat_match:
            cat_correct += 1
        if pri_match:
            pri_correct += 1
        if needs_human:
            needs_human_count += 1
            
        total_confidence += confidence
        
        # Token estimation (character-based)
        # 1 token ≈ 4 characters
        input_tokens = (len(SYSTEM_PROMPT) + len(message)) // 4
        output_tokens = len(json.dumps(result)) // 4
        
        total_input_tokens += input_tokens
        total_output_tokens += output_tokens
        
        # Printable indicators
        cat_check = "✓" if cat_match else "✗"
        pri_check = "✓" if pri_match else "✗"
        
        # Format table row
        truncated_msg = message[:35] if len(message) <= 35 else message[:32] + "..."
        print(f"{idx:<3} | {truncated_msg:<35} | {expected_cat:<18} | {predicted_cat:<18} | {cat_check:<4} | {expected_pri:<12} | {predicted_pri:<12} | {pri_check:<4} | {confidence:<6.2f} | {latency_ms:<6}")
        
        # Store for report JSON
        per_message_results.append({
            "message": message,
            "expected_category": expected_cat,
            "predicted_category": predicted_cat,
            "category_match": cat_match,
            "expected_priority": expected_pri,
            "predicted_priority": predicted_pri,
            "priority_match": pri_match,
            "confidence": confidence,
            "needs_human": needs_human,
            "latency_ms": latency_ms
        })
        
    total_time_s = time.time() - start_total_time
    
    # Calculate stats
    total_count = len(ground_truth)
    cat_accuracy_pct = (cat_correct / total_count) * 100 if total_count > 0 else 0.0
    pri_accuracy_pct = (pri_correct / total_count) * 100 if total_count > 0 else 0.0
    avg_confidence = total_confidence / total_count if total_count > 0 else 0.0
    avg_latency_ms = int(total_latency_ms / total_count) if total_count > 0 else 0
    
    # Cost calculation: inputs * 0.000000075 + outputs * 0.0000003
    est_cost = total_input_tokens * 0.000000075 + total_output_tokens * 0.0000003
    
    # Print Metrics Block
    print("-" * 130)
    print("=== Evaluation Report ===")
    print(f"  Category accuracy : {cat_correct}/{total_count} ({cat_accuracy_pct:.0f}%)")
    print(f"  Priority accuracy : {pri_correct}/{total_count} ({pri_accuracy_pct:.0f}%)")
    print(f"  Needs human rate  : {needs_human_count}/{total_count}")
    print(f"  Avg confidence    : {avg_confidence:.2f}")
    print(f"  Avg latency       : {avg_latency_ms}ms")
    print(f"  Total latency     : {total_time_s:.2f}s")
    print(f"  Est. cost (USD)   : ${est_cost:.4f}")
    print("  (cost formula: input_tokens * 0.000000075 + output_tokens * 0.0000003")
    print("   for gemini-1.5-flash free tier approximation)")
    print("=========================")
    
    # Save output/eval_report.json
    report_data = {
        "category_accuracy": round(cat_correct / total_count, 2) if total_count > 0 else 0.0,
        "priority_accuracy": round(pri_correct / total_count, 2) if total_count > 0 else 0.0,
        "needs_human_rate": round(needs_human_count / total_count, 2) if total_count > 0 else 0.0,
        "avg_confidence": round(avg_confidence, 2),
        "avg_latency_ms": avg_latency_ms,
        "total_latency_s": round(total_time_s, 2),
        "estimated_cost_usd": round(est_cost, 6),
        "per_message": per_message_results
    }
    
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / "eval_report.json", "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
