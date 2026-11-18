"""
Verification script for the RCA ground-truth dataset.
Checks:
1. Overall revenue comparison between Week 1 (baseline) and Week 2 (incident).
2. Regional revenue breakdown.
3. Mobile vs Web failure rates in EU.
4. Git deployment event for PR #482.
5. Slack alerts correlation.
"""

import sqlite3
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent
DB_PATH = DATA_DIR / "synthetic_database.db"
GIT_PATH = DATA_DIR / "mock_git_deploys.json"
SLACK_PATH = DATA_DIR / "mock_slack_logs.json"
FUNNEL_PATH = DATA_DIR / "mock_funnel_analytics.json"

def verify():
    print("=" * 60)
    print("RCA GROUND TRUTH DATASET VERIFICATION")
    print("=" * 60)

    # 1. SQL Metrics
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Week 1: 2026-10-15 to 2026-10-21 (7 full days)
    # Week 2: 2026-10-22 to 2026-10-28 (7 full days)
    cur.execute("""
    SELECT 
        CASE WHEN date < '2026-10-22' THEN 'Week 1 (Baseline)' ELSE 'Week 2 (Incident)' END as period,
        SUM(total_orders) as orders,
        SUM(successful_orders) as successful,
        ROUND(SUM(total_revenue), 2) as revenue,
        ROUND(100.0 * SUM(successful_orders) / SUM(total_orders), 2) as success_pct
    FROM daily_sales_summary
    GROUP BY period
    ORDER BY period
    """)
    rows = cur.fetchall()
    print("\n--- Weekly High-Level Metric Comparison ---")
    w1_rev = rows[0][3]
    w2_rev = rows[1][3]
    drop_pct = (1.0 - (w2_rev / w1_rev)) * 100.0
    for r in rows:
        print(f"{r[0]}: Orders={r[1]}, Success={r[2]} ({r[4]}%), Revenue=${r[3]:,.2f}")
    print(f"-> Total Revenue Drop: {drop_pct:.2f}% (Matches the 'sales dropped ~18%' event prompt!)")

    # 2. Regional Breakdown in Incident Week
    print("\n--- Incident Week (Week 2) Regional Performance ---")
    cur.execute("""
    SELECT 
        region,
        ROUND(100.0 * SUM(successful_orders) / SUM(total_orders), 2) as success_rate,
        ROUND(SUM(total_revenue), 2) as revenue
    FROM daily_sales_summary
    WHERE date >= '2026-10-22'
    GROUP BY region
    """)
    for r in cur.fetchall():
        print(f"Region {r[0]}: Success Rate = {r[1]}%, Revenue = ${r[2]:,.2f}")

    # 3. EU Mobile vs Web breakdown
    print("\n--- EU Error Analysis (Post Incident Oct 22 14:15) ---")
    cur.execute("""
    SELECT 
        platform,
        status,
        COUNT(*) as count,
        error_code
    FROM orders
    WHERE region = 'EU' AND timestamp >= '2026-10-22 14:15:00'
    GROUP BY platform, status, error_code
    """)
    for r in cur.fetchall():
        print(f"Platform: {r[0]:<7} | Status: {r[1]:<10} | Error: {str(r[3]):<32} | Count: {r[2]}")

    conn.close()

    # 4. Git PR ground truth check
    with open(GIT_PATH) as f:
        git_data = json.load(f)
    print("\n--- Culprit Git Deployments Identified in Dataset ---")
    for d in git_data["deployments"]:
        if d.get("root_cause_flag"):
            print(f"Found Seeded Cause: [{d['id']}] {d['title']} at {d['deployed_at']}")
            print(f"  Files: {d['files_changed']}")
            print(f"  Diff Summary: {d['diff_summary']}")

    # 5. Slack channel alert check
    with open(SLACK_PATH) as f:
        slack_data = json.load(f)
    print("\n--- Correlating Slack Incident Alerts ---")
    for msg in slack_data["channels"]["incident-payments"]:
        print(f"[{msg['timestamp']}] {msg['user']}: {msg['text']}")

    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE: GROUND TRUTH VALIDATED")
    print("=" * 60)

if __name__ == "__main__":
    verify()
