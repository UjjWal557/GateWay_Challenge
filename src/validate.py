import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Ensure the root of the project is in python path
project_root = Path(__file__).parent.parent.resolve()
sys.path.append(str(project_root))

from src.triage import triage_message, preprocess_message, pii_check

def run_validation():
    # Configure UTF-8 output encoding to handle box-drawing and emoji characters on Windows
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

    print("Starting Signal System Validation...")
    
    checks_passed = 0

    # ━━━ CHECK 1: Environment ━━━
    print("\n━━━ CHECK 1: Environment ━━━")
    env_pass = True
    
    # .env exists
    env_file = project_root / ".env"
    if env_file.exists():
        print(".env file exists: PASS")
    else:
        print(".env file exists: FAIL")
        env_pass = False
        
    # GEMINI_API_KEY loaded and starts with AIza
    load_dotenv(dotenv_path=env_file)
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if api_key.startswith("AIza"):
        print("GEMINI_API_KEY loaded and starts with 'AIza': PASS")
    else:
        print("GEMINI_API_KEY loaded and starts with 'AIza': FAIL")
        env_pass = False
        
    # All required files exist
    required_files = [
        "src/triage.py", "src/run.py", "src/app.py", 
        "src/test_guardrails.py", "src/evaluate.py",
        "data/messages.txt", "data/ground_truth.json",
        "output/results.json", "output/eval_report.json",
        "AI_DECISIONS.md", "README.md", "requirements.txt"
    ]
    
    files_pass = True
    for rel_path in required_files:
        filepath = project_root / rel_path
        if filepath.exists():
            print(f"  File exists '{rel_path}': PASS")
        else:
            print(f"  File exists '{rel_path}': FAIL")
            files_pass = False
            
    if not files_pass:
        env_pass = False
        
    if env_pass:
        checks_passed += 1
        print("Check 1 Status: PASS")
    else:
        print("Check 1 Status: FAIL")

    # ━━━ CHECK 2: Messages file ━━━
    print("\n━━━ CHECK 2: Messages file ━━━")
    messages_pass = True
    messages_path = project_root / "data/messages.txt"
    num_messages = 0
    
    if messages_path.exists():
        with open(messages_path, "r", encoding="utf-8") as f:
            raw_lines = f.read().splitlines()
            
        # Strip trailing empty lines to determine last line
        while raw_lines and raw_lines[-1].strip() == "":
            raw_lines.pop()
            
        num_messages = len([l for l in raw_lines if l.strip()])
        print(f"Messages loaded: {num_messages}")
        
        if len(raw_lines) < 20:
            print("Messages file has at least 20 lines: FAIL")
            messages_pass = False
        else:
            print("Messages file has at least 20 lines: PASS")
            
        # Check blank lines in the middle
        blank_in_middle = any(line.strip() == "" for line in raw_lines)
        if blank_in_middle:
            print("No completely blank lines in the middle: FAIL")
            messages_pass = False
        else:
            print("No completely blank lines in the middle: PASS")
    else:
        print("Messages file exists: FAIL")
        messages_pass = False
        
    if messages_pass:
        checks_passed += 1
        print("Check 2 Status: PASS")
    else:
        print("Check 2 Status: FAIL")

    # ━━━ CHECK 3: Single message live API test ━━━
    print("\n━━━ CHECK 3: Single message live API test ━━━")
    api_pass = True
    test_msg = "I was charged twice this month"
    
    try:
        print(f"Calling triage_message('{test_msg}')...")
        result = triage_message(test_msg, dry_run=False)
        print("API Response:")
        print(json.dumps(result, indent=2))
        
        # Assert result is a dict
        if isinstance(result, dict):
            print("Result is a dictionary: PASS")
        else:
            print("Result is a dictionary: FAIL")
            api_pass = False
            
        # Assert all 6 required fields present
        required_fields = ["category", "priority", "summary", "suggested_action", "needs_human", "confidence"]
        fields_ok = True
        for field in required_fields:
            if field in result:
                print(f"  Field '{field}' present: PASS")
            else:
                print(f"  Field '{field}' present: FAIL")
                fields_ok = False
        if not fields_ok:
            api_pass = False
            
        # Assert category is one of the 8 valid values
        valid_categories = {
            "billing", "technical_support", "complaint", 
            "general_question", "feature_request", "abuse", 
            "out_of_scope", "unclear"
        }
        cat = result.get("category")
        if cat in valid_categories:
            print(f"Category '{cat}' is valid: PASS")
        else:
            print(f"Category '{cat}' is valid: FAIL")
            api_pass = False
            
        # Assert priority is one of P0/P1/P2/P3
        prio = result.get("priority")
        if prio in {"P0", "P1", "P2", "P3"}:
            print(f"Priority '{prio}' is valid: PASS")
        else:
            print(f"Priority '{prio}' is valid: FAIL")
            api_pass = False
            
        # Assert confidence between 0.0 and 1.0
        conf = result.get("confidence")
        if isinstance(conf, (int, float)) and 0.0 <= conf <= 1.0:
            print(f"Confidence {conf} is in 0.0-1.0: PASS")
        else:
            print(f"Confidence {conf} is in 0.0-1.0: FAIL")
            api_pass = False
            
        # Assert needs_human is boolean
        needs_human = result.get("needs_human")
        if isinstance(needs_human, bool):
            print(f"needs_human '{needs_human}' is boolean: PASS")
        else:
            print(f"needs_human '{needs_human}' is boolean: FAIL")
            api_pass = False
            
    except Exception as e:
        print(f"API call or assertions failed with error: {e}")
        api_pass = False
        
    if api_pass:
        checks_passed += 1
        print("Check 3 Status: PASS")
    else:
        print("Check 3 Status: FAIL")

    # ━━━ CHECK 4: Edge case spot checks (no API call) ━━━
    print("\n━━━ CHECK 4: Edge case spot checks (no API call) ━━━")
    preprocess_passed = 0
    
    # a) HTML input
    res_a = preprocess_message("<div>hello &amp; world</div>")
    if "hello & world" in res_a and "<div" not in res_a and ">" not in res_a:
        print("a) HTML input check: PASS")
        preprocess_passed += 1
    else:
        print("a) HTML input check: FAIL")
        
    # b) Empty string
    res_b = preprocess_message("")
    if res_b == "__EMPTY_MESSAGE__":
        print("b) Empty string check: PASS")
        preprocess_passed += 1
    else:
        print("b) Empty string check: FAIL")
        
    # c) Very long string
    res_c = preprocess_message("a" * 900)
    if len(res_c) <= 810:
        print("c) Very long string check: PASS")
        preprocess_passed += 1
    else:
        print("c) Very long string check: FAIL")
        
    # d) JSON string
    res_d = preprocess_message('{"message": "help me"}')
    if "help me" in res_d:
        print("d) JSON string check: PASS")
        preprocess_passed += 1
    else:
        print("d) JSON string check: FAIL")
        
    # e) Control chars
    res_e = preprocess_message("hello\x00world")
    if "\x00" not in res_e:
        print("e) Control chars check: PASS")
        preprocess_passed += 1
    else:
        print("e) Control chars check: FAIL")
        
    print(f"Preprocessing checks passed: {preprocess_passed}/5")
    if preprocess_passed == 5:
        checks_passed += 1

    # ━━━ CHECK 5: PII detection spot checks ━━━
    print("\n━━━ CHECK 5: PII detection spot checks ━━━")
    pii_passed = 0
    
    # a) Email
    res_a = pii_check("email me at test@example.com")
    if res_a.get("has_pii") is True and "email" in res_a.get("pii_types", []):
        print("a) Email detection: PASS")
        pii_passed += 1
    else:
        print("a) Email detection: FAIL")
        
    # b) Card
    res_b = pii_check("card 4111111111111111")
    if res_b.get("has_pii") is True and "credit_card" in res_b.get("pii_types", []):
        print("b) Card detection: PASS")
        pii_passed += 1
    else:
        print("b) Card detection: FAIL")
        
    # c) Phone
    res_c = pii_check("call me at 555-123-4567")
    if res_c.get("has_pii") is True and "phone" in res_c.get("pii_types", []):
        print("c) Phone detection: PASS")
        pii_passed += 1
    else:
        print("c) Phone detection: FAIL")
        
    # d) No PII
    res_d = pii_check("I want a refund")
    if res_d.get("has_pii") is False:
        print("d) No PII detection: PASS")
        pii_passed += 1
    else:
        print("d) No PII detection: FAIL")
        
    print(f"PII detection checks passed: {pii_passed}/4")
    if pii_passed == 4:
        checks_passed += 1

    # ━━━ CHECK 6: Output files validation ━━━
    print("\n━━━ CHECK 6: Output files validation ━━━")
    outputs_pass = True
    
    # Results.json validation
    results_file = project_root / "output/results.json"
    if results_file.exists():
        try:
            with open(results_file, "r", encoding="utf-8") as f:
                results = json.load(f)
                
            if isinstance(results, list):
                print("results.json is valid JSON array: PASS")
                
                # Check items
                items_ok = True
                valid_categories = {
                    "billing", "technical_support", "complaint", 
                    "general_question", "feature_request", "abuse", 
                    "out_of_scope", "unclear"
                }
                for idx, item in enumerate(results, 1):
                    # fields
                    required = ["category", "priority", "summary", "suggested_action", "needs_human", "confidence"]
                    if not all(field in item for field in required):
                        print(f"  Item {idx} missing required fields: FAIL")
                        items_ok = False
                    # conf
                    conf = item.get("confidence", -1)
                    if not (0.0 <= conf <= 1.0):
                        print(f"  Item {idx} invalid confidence '{conf}': FAIL")
                        items_ok = False
                    # category/priority
                    cat = item.get("category")
                    prio = item.get("priority")
                    if cat not in valid_categories or prio not in {"P0", "P1", "P2", "P3"}:
                        print(f"  Item {idx} invalid category '{cat}' or priority '{prio}': FAIL")
                        items_ok = False
                        
                if items_ok:
                    print("All items in results.json are valid: PASS")
                else:
                    print("All items in results.json are valid: FAIL")
                    outputs_pass = False
                    
                # Summary stats
                used_fallback = sum(1 for item in results if item.get("flags", {}).get("used_fallback") is True)
                needs_human = sum(1 for item in results if item.get("needs_human") is True)
                print(f"  Stats - Fallback used: {used_fallback}, Needs human: {needs_human}")
            else:
                print("results.json is valid JSON array: FAIL")
                outputs_pass = False
        except Exception as e:
            print(f"results.json loaded: FAIL ({e})")
            outputs_pass = False
    else:
        print("results.json exists: FAIL")
        outputs_pass = False
        
    # Eval_report.json validation
    eval_file = project_root / "output/eval_report.json"
    if eval_file.exists():
        try:
            with open(eval_file, "r", encoding="utf-8") as f:
                eval_data = json.load(f)
                
            if "category_accuracy" in eval_data and "priority_accuracy" in eval_data:
                print("eval_report.json contains expected accuracy fields: PASS")
                cat_acc = eval_data["category_accuracy"]
                prio_acc = eval_data["priority_accuracy"]
                print(f"Category accuracy: {int(cat_acc * 100)}%, Priority accuracy: {int(prio_acc * 100)}%")
            else:
                print("eval_report.json contains expected accuracy fields: FAIL")
                outputs_pass = False
        except Exception as e:
            print(f"eval_report.json loaded: FAIL ({e})")
            outputs_pass = False
    else:
        print("eval_report.json exists: FAIL")
        outputs_pass = False
        
    if outputs_pass:
        checks_passed += 1
        print("Check 6 Status: PASS")
    else:
        print("Check 6 Status: FAIL")

    # ━━━ FINAL REPORT ━━━
    print("\n==========================================")
    print("SIGNAL — VALIDATION REPORT")
    print("==========================================")
    print(f"Environment        : {'PASS' if env_pass else 'FAIL'}")
    print(f"Messages file      : {'PASS' if messages_pass else 'FAIL'} ({num_messages} messages)")
    print(f"Live API test      : {'PASS' if api_pass else 'FAIL'}")
    print(f"Preprocessing      : {preprocess_passed}/5 checks passed")
    print(f"PII detection      : {pii_passed}/4 checks passed")
    print(f"Output files       : {'PASS' if outputs_pass else 'FAIL'}")
    print("------------------------------------------")
    print(f"OVERALL            : {checks_passed}/6 checks passed")
    print(f"Ready to submit    : {'YES' if checks_passed == 6 else 'NO'}")
    print("==========================================\n")

if __name__ == "__main__":
    run_validation()
