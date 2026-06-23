import os
import sys
import json
import pandas as pd
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

# Ensure root of project is in python path
sys.path.append(str(Path(__file__).parent.parent))

from src.triage import triage_message

# Category colors for badge rendering in styled tables (Pandas Styler)
CATEGORY_COLORS = {
    "billing": "background-color: rgba(52, 152, 219, 0.2); color: #2980b9; font-weight: bold; border-radius: 4px; padding: 2px 6px;",
    "technical_support": "background-color: rgba(46, 204, 113, 0.2); color: #27ae60; font-weight: bold; border-radius: 4px; padding: 2px 6px;",
    "complaint": "background-color: rgba(231, 76, 60, 0.2); color: #c0392b; font-weight: bold; border-radius: 4px; padding: 2px 6px;",
    "general_question": "background-color: rgba(241, 196, 15, 0.2); color: #d35400; font-weight: bold; border-radius: 4px; padding: 2px 6px;",
    "feature_request": "background-color: rgba(155, 89, 182, 0.2); color: #8e44ad; font-weight: bold; border-radius: 4px; padding: 2px 6px;",
    "abuse": "background-color: rgba(52, 73, 94, 0.2); color: #2c3e50; font-weight: bold; border-radius: 4px; padding: 2px 6px;",
    "out_of_scope": "background-color: rgba(127, 140, 141, 0.2); color: #7f8c8d; font-weight: bold; border-radius: 4px; padding: 2px 6px;",
    "unclear": "background-color: rgba(149, 165, 166, 0.2); color: #7f8c8d; font-weight: bold; border-radius: 4px; padding: 2px 6px;"
}

def style_category_cell(val):
    return CATEGORY_COLORS.get(val, "")

def color_compare_rows(row):
    cat_match = "✅" in str(row["Match"])
    pri_match = "✅" in str(row["Match "])
    if cat_match and pri_match:
        return ["background-color: rgba(46, 204, 113, 0.15); color: #27ae60;"] * len(row)
    elif not cat_match and not pri_match:
        return ["background-color: rgba(231, 76, 60, 0.15); color: #c0392b;"] * len(row)
    else:
        return ["background-color: rgba(241, 196, 15, 0.15); color: #d35400;"] * len(row)

def main():
    load_dotenv()
    
    # Configure UTF-8 for outputs
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

    st.set_page_config(page_title="Signal", layout="wide", page_icon="📡")
    
    # Premium CSS Injections
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .gradient-text {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    
    /* Sleek card design for metrics */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.03);
    }
    
    /* Sidebar custom branding */
    .sidebar-title {
        font-size: 1.8rem;
        font-weight: 800;
        color: #3b82f6;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.title("📡 Signal")
    st.sidebar.caption("AI triage — turn messy messages into clear decisions")
    
    uploaded_file = st.sidebar.file_uploader("Upload messages file (.txt)", type=["txt"])
    pasted_text = st.sidebar.text_area("Or paste messages directly (one per line)", value="", height=150)
    
    run_triage = st.sidebar.button("Run Triage ▶")
    st.sidebar.markdown("---")
    st.sidebar.caption("Model: gemini-3.1-flash-lite")
    
    # Tab config
    tab_live, tab_eval = st.tabs(["Live Triage", "Evaluation"])
    
    # Session state init
    if "results" not in st.session_state:
        st.session_state.results = []
        
    with tab_live:
        st.title("📡 Signal")
        st.write("AI triage — turn messy messages into clear decisions")
        st.markdown("---")
        
        if run_triage:
            messages = []
            if uploaded_file is not None:
                file_contents = uploaded_file.read().decode("utf-8")
                messages.extend([line.strip() for line in file_contents.splitlines() if line.strip()])
            if pasted_text.strip():
                messages.extend([line.strip() for line in pasted_text.splitlines() if line.strip()])
                
            if not messages:
                st.warning("Please upload a messages file or paste some text first.")
            else:
                with st.spinner("Triaging messages..."):
                    results = []
                    # Detect if API key is present, otherwise fallback to dry-run
                    api_key = os.environ.get("GEMINI_API_KEY")
                    dry_run = not api_key
                    
                    for message in messages:
                        meta = {}
                        res = triage_message(message, dry_run=dry_run, meta=meta)
                        retry_count = meta.get("retry_count", 0)
                        
                        used_fallback = (res.get("confidence", 0.0) == 0.0 and res.get("category") == "unclear")
                        res["original_message"] = message
                        res["flags"] = {
                            "retried": (retry_count > 0),
                            "used_fallback": used_fallback
                        }
                        results.append(res)
                        
                    st.session_state.results = results
                    st.success(f"Successfully processed {len(results)} messages!")
 
        if st.session_state.results:
            results = st.session_state.results
            total = len(results)
            needs_human_count = sum(1 for r in results if r.get("needs_human", True))
            p0_p1_count = sum(1 for r in results if r.get("priority") in ["P0", "P1"])
            avg_confidence = sum(r.get("confidence", 0.0) for r in results) / total if total > 0 else 0.0
            
            # Show Metrics in 4 columns
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            
            with m_col1:
                st.markdown(f"""
                <div style="
                    background: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 12px;
                    padding: 11px 15px;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
                ">
                    <div style="font-size: 0.9rem; color: #64748b; font-weight: 500;">Total Messages</div>
                    <div style="font-size: 1.8rem; font-weight: 700; color: #f8fafc; margin-top: 4px;">
                        {total}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            human_pct = (needs_human_count / total) if total > 0 else 0.0
            human_color = "#e74c3c" if human_pct > 0.2 else "#f8fafc"
            with m_col2:
                st.markdown(f"""
                <div style="
                    background: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 12px;
                    padding: 11px 15px;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
                ">
                    <div style="font-size: 0.9rem; color: #64748b; font-weight: 500;">Needs Human</div>
                    <div style="font-size: 1.8rem; font-weight: 700; color: {human_color}; margin-top: 4px;">
                        {needs_human_count} ({human_pct:.0%})
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            critical_color = "#e74c3c" if p0_p1_count > 0 else "#2ecc71"
            with m_col3:
                st.markdown(f"""
                <div style="
                    background: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 12px;
                    padding: 11px 15px;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
                ">
                    <div style="font-size: 0.9rem; color: #64748b; font-weight: 500;">P0/P1 Critical</div>
                    <div style="font-size: 1.8rem; font-weight: 700; color: {critical_color}; margin-top: 4px;">
                        {p0_p1_count}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            if avg_confidence > 0.8:
                conf_color = "#2ecc71"
            elif avg_confidence > 0.6:
                conf_color = "#f39c12"
            else:
                conf_color = "#e74c3c"
            with m_col4:
                st.markdown(f"""
                <div style="
                    background: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 12px;
                    padding: 11px 15px;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
                ">
                    <div style="font-size: 0.9rem; color: #64748b; font-weight: 500;">Avg Confidence</div>
                    <div style="font-size: 1.8rem; font-weight: 700; color: {conf_color}; margin-top: 4px;">
                        {avg_confidence:.0%}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # Summary Stats Row
            p0_cnt = sum(1 for r in results if r.get("priority") == "P0")
            p1_cnt = sum(1 for r in results if r.get("priority") == "P1")
            p2_cnt = sum(1 for r in results if r.get("priority") == "P2")
            p3_cnt = sum(1 for r in results if r.get("priority") == "P3")
            
            billing_cnt = sum(1 for r in results if r.get("category") == "billing")
            complaints_cnt = sum(1 for r in results if r.get("category") == "complaint")
            abuse_cnt = sum(1 for r in results if r.get("category") == "abuse")
            pii_cnt = sum(1 for r in results if r.get("pii_detected", {}).get("has_pii") is True)
            
            st.markdown(f"**P0:** {p0_cnt} &nbsp;|&nbsp; **P1:** {p1_cnt} &nbsp;|&nbsp; **P2:** {p2_cnt} &nbsp;|&nbsp; **P3:** {p3_cnt} &nbsp;|&nbsp; **Billing:** {billing_cnt} &nbsp;|&nbsp; **Complaints:** {complaints_cnt} &nbsp;|&nbsp; **Abuse/Injection:** {abuse_cnt} &nbsp;|&nbsp; **PII Flagged:** {pii_cnt}")
            st.markdown("---")

            # Classified Results Overview Dataframe Table
            st.markdown("### Classified Results Overview")
            table_rows = []
            for idx, r in enumerate(results, 1):
                category = r.get("category", "unclear")
                priority = r.get("priority", "P2")
                summary = r.get("summary", "")
                needs_human = r.get("needs_human", True)
                confidence = r.get("confidence", 0.0)
                
                pri_formatted = {"P0": "🔴 P0", "P1": "🟠 P1", "P2": "🟡 P2", "P3": "🟢 P3"}.get(priority, priority)
                human_formatted = "🔴 Needs Human" if needs_human else "🟢 Auto"
                truncated_summary = summary[:50] if len(summary) <= 50 else summary[:47] + "..."
                
                table_rows.append({
                    "#": idx,
                    "Category": category,
                    "Priority": pri_formatted,
                    "Needs Human": human_formatted,
                    "Confidence": f"{confidence:.0%}",
                    "Summary (50 chars)": truncated_summary
                })
                
            df = pd.DataFrame(table_rows)
            styled_df = df.style.map(style_category_cell, subset=["Category"])
            st.dataframe(styled_df, width="stretch", hide_index=True)

            # Details cards
            st.markdown("### 🏷️ Classified Cards Details")
            for i, r in enumerate(results):
                category = r.get("category", "unclear")
                priority = r.get("priority", "P2")
                summary = r.get("summary", "")
                needs_human = r.get("needs_human", True)
                confidence = r.get("confidence", 0.0)
                suggested_action = r.get("suggested_action", "")
                original_message = r.get("original_message", "")
                pii_detected = r.get("pii_detected", {})
                
                color = {
                    "billing": "blue",
                    "technical_support": "green",
                    "complaint": "red",
                    "general_question": "orange",
                    "feature_request": "violet",
                    "abuse": "red",
                    "out_of_scope": "gray",
                    "unclear": "gray"
                }.get(category, "gray")
                
                priority_with_emoji = {"P0": "🔴 P0", "P1": "🟠 P1", "P2": "🟡 P2", "P3": "🟢 P3"}.get(priority, priority)
                needs_human_badge = ":red[🔴 Needs Human]" if needs_human else ":green[🟢 Auto]"
                confidence_pct = int(confidence * 100)
                
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([0.5, 2, 1.5, 2, 1])
                    with col1: st.markdown(f"**#{i+1}**")
                    with col2: st.markdown(f":{color}-background[{category}]")
                    with col3: st.markdown(priority_with_emoji)
                    with col4: st.markdown(needs_human_badge)
                    with col5: st.markdown(f"**{confidence_pct}%**")
                    
                    st.markdown(f"**Summary:** {summary}")
                    st.markdown(f"**Suggested action:** {suggested_action}")
                    st.markdown(f"> {original_message}")
                    
                    if pii_detected and pii_detected.get("has_pii"):
                        types = ", ".join(pii_detected.get("pii_types", []))
                        st.error(f"🛡 PII detected: {types}")
                    
                    st.divider()
            
            st.download_button(
                label="Download Results JSON 📥",
                data=json.dumps(results, indent=2, ensure_ascii=False),
                file_name="results.json",
                mime="application/json"
            )
            
    with tab_eval:
        st.markdown("<div class='gradient-text'>System Evaluation</div>", unsafe_allow_html=True)
        st.write("Compare triage model predictions against curated ground truth data.")
        st.markdown("---")
        
        eval_path = Path("output/eval_report.json")
        
        if eval_path.exists():
            with open(eval_path, "r", encoding="utf-8") as f:
                report = json.load(f)
                
            per_messages = report.get("per_message", [])
            total_cases = len(per_messages)
            
            # Calculate actual match counts
            cat_correct = sum(1 for pm in per_messages if pm.get("category_match", False))
            pri_correct = sum(1 for pm in per_messages if pm.get("priority_match", False))
            
            e_col1, e_col2, e_col3, e_col4 = st.columns(4)
            e_col1.metric("Category Accuracy", f"{cat_correct}/{total_cases} — {report.get('category_accuracy', 0.0):.0%}")
            e_col2.metric("Priority Accuracy", f"{pri_correct}/{total_cases} — {report.get('priority_accuracy', 0.0):.0%}")
            e_col3.metric("Avg Confidence", f"{report.get('avg_confidence', 0.0):.0%}")
            e_col4.metric("Avg Latency", f"{report.get('avg_latency_ms', 0)} ms")
            
            # Section A: Ground Truth Evaluation
            st.markdown("---")
            st.subheader("📋 Ground Truth Evaluation")
            st.caption("10 hand-labeled messages — expected vs predicted")

            per_message = per_messages[::-1]  # reverse list to show latest at top

            rows_html = ""
            for i, item in enumerate(per_message):
                cat_match = item["category_match"]
                pri_match = item["priority_match"]
                
                if cat_match and pri_match:
                    row_style = "background-color: transparent"
                    cat_icon = "✅"
                    pri_icon = "✅"
                elif cat_match or pri_match:
                    row_style = "background-color: rgba(250,200,50,0.15)"
                    cat_icon = "✅" if cat_match else "❌"
                    pri_icon = "✅" if pri_match else "❌"
                else:
                    row_style = "background-color: rgba(255,80,80,0.15)"
                    cat_icon = "❌"
                    pri_icon = "❌"
                
                msg = item["message"][:40] + "..." if len(item["message"]) > 40 else item["message"]
                
                rows_html += f"""
                <tr style="{row_style}">
                    <td style="padding:8px;font-size:13px">{msg}</td>
                    <td style="padding:8px;font-size:13px">{item["expected_category"]}</td>
                    <td style="padding:8px;font-size:13px">{item["predicted_category"]}</td>
                    <td style="padding:8px;font-size:13px;text-align:center">{cat_icon}</td>
                    <td style="padding:8px;font-size:13px">{item["expected_priority"]}</td>
                    <td style="padding:8px;font-size:13px">{item["predicted_priority"]}</td>
                    <td style="padding:8px;font-size:13px;text-align:center">{pri_icon}</td>
                    <td style="padding:8px;font-size:13px">{item.get("confidence", 0)*100:.0f}%</td>
                </tr>
                """

            table_html = f"""
            <table style="width:100%;border-collapse:collapse;font-family:sans-serif">
                <thead>
                    <tr style="border-bottom:1px solid #444">
                        <th style="padding:8px;text-align:left;font-size:12px;
                            color:#888">Message</th>
                        <th style="padding:8px;text-align:left;font-size:12px;
                            color:#888">Expected Cat</th>
                        <th style="padding:8px;text-align:left;font-size:12px;
                            color:#888">Predicted Cat</th>
                        <th style="padding:8px;text-align:center;font-size:12px;
                            color:#888">✓</th>
                        <th style="padding:8px;text-align:left;font-size:12px;
                            color:#888">Expected Pri</th>
                        <th style="padding:8px;text-align:left;font-size:12px;
                            color:#888">Predicted Pri</th>
                        <th style="padding:8px;text-align:center;font-size:12px;
                            color:#888">✓</th>
                        <th style="padding:8px;text-align:left;font-size:12px;
                            color:#888">Conf</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
            """

            st.markdown(table_html, unsafe_allow_html=True)

            mismatched_cats = [
                item["expected_category"] 
                for item in per_message 
                if not item["category_match"]
            ]

            if not mismatched_cats:
                st.success("✅ All predictions matched ground truth perfectly.")
            else:
                unique_fails = list(set(mismatched_cats))
                st.warning(f"⚠ System struggled with: {', '.join(unique_fails)}")

            # Section B: All Processed Messages
            st.markdown("---")
            st.subheader("📨 All Processed Messages")
            st.caption("Complete results from last pipeline run — latest first")

            results_path = os.path.join("output", "results.json")
            if os.path.exists(results_path):
                with open(results_path, "r", encoding="utf-8") as f:
                    all_results = json.load(f)
                all_results = all_results[::-1]  # latest first
            else:
                all_results = []

            if all_results:
                processed_rows_html = ""
                for idx, item in enumerate(all_results, 1):
                    orig_msg = item.get("original_message", "")
                    truncated_msg = orig_msg[:40] + "..." if len(orig_msg) > 40 else orig_msg
                    
                    category = item.get("category", "unclear")
                    cat_color = {
                        "billing": "#2980b9",
                        "technical_support": "#27ae60",
                        "complaint": "#c0392b",
                        "general_question": "#d35400",
                        "feature_request": "#8e44ad",
                        "abuse": "#c0392b",
                        "out_of_scope": "#7f8c8d",
                        "unclear": "#7f8c8d"
                    }.get(category, "#7f8c8d")
                    
                    cat_badge_html = f'<span style="background-color: {cat_color}33; color: {cat_color}; border: 1px solid {cat_color}66; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: bold;">{category}</span>'
                    
                    priority = item.get("priority", "P3")
                    prio_formatted = {"P0": "🔴 P0", "P1": "🟠 P1", "P2": "🟡 P2", "P3": "🟢 P3"}.get(priority, priority)
                    
                    needs_human = item.get("needs_human", True)
                    needs_human_str = '<span style="color:#ff4b4b;font-weight:bold">🔴 Needs Human</span>' if needs_human else '<span style="color:#2ecc71;font-weight:bold">🟢 Auto</span>'
                    
                    conf_pct = f"{item.get('confidence', 0)*100:.0f}%"
                    
                    pii_detected = item.get("pii_detected", {})
                    pii_icon = "🛡️" if pii_detected.get("has_pii") else ""
                    
                    flags_data = item.get("flags", {})
                    flag_list = []
                    if flags_data.get("retried"):
                        flag_list.append("retried")
                    if flags_data.get("used_fallback"):
                        flag_list.append("fallback")
                    flags_str = ", ".join(flag_list)
                    
                    processed_rows_html += f"""
                    <tr style="border-bottom:1px solid #333">
                        <td style="padding:8px;font-size:13px;font-weight:bold">#{idx}</td>
                        <td style="padding:8px;font-size:13px">{truncated_msg}</td>
                        <td style="padding:8px;font-size:13px">{cat_badge_html}</td>
                        <td style="padding:8px;font-size:13px">{prio_formatted}</td>
                        <td style="padding:8px;font-size:13px">{needs_human_str}</td>
                        <td style="padding:8px;font-size:13px">{conf_pct}</td>
                        <td style="padding:8px;font-size:13px;text-align:center">{pii_icon}</td>
                        <td style="padding:8px;font-size:13px;color:#888;font-style:italic">{flags_str}</td>
                    </tr>
                    """
                
                processed_table_html = f"""
                <table style="width:100%;border-collapse:collapse;font-family:sans-serif">
                    <thead>
                        <tr style="border-bottom:1px solid #444">
                            <th style="padding:8px;text-align:left;font-size:12px;color:#888;width:5%">#</th>
                            <th style="padding:8px;text-align:left;font-size:12px;color:#888;width:35%">Message</th>
                            <th style="padding:8px;text-align:left;font-size:12px;color:#888;width:15%">Category</th>
                            <th style="padding:8px;text-align:left;font-size:12px;color:#888;width:10%">Priority</th>
                            <th style="padding:8px;text-align:left;font-size:12px;color:#888;width:15%">Needs Human</th>
                            <th style="padding:8px;text-align:left;font-size:12px;color:#888;width:8%">Conf</th>
                            <th style="padding:8px;text-align:center;font-size:12px;color:#888;width:5%">PII</th>
                            <th style="padding:8px;text-align:left;font-size:12px;color:#888;width:12%">Flags</th>
                        </tr>
                    </thead>
                    <tbody>
                        {processed_rows_html}
                    </tbody>
                </table>
                """
                st.markdown(processed_table_html, unsafe_allow_html=True)
            else:
                st.info("No processed messages found in output/results.json")
        else:
            st.warning("Run src/evaluate.py first to generate evaluation data")
            st.code("python src/evaluate.py")

if __name__ == "__main__":
    main()
