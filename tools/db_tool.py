"""
Database tool utilities for the Data Agent.
Provides read-only access to SQLite transactional data, schema inspection, and metric aggregation.
"""

import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional

DB_PATH = Path(__file__).parent.parent / "data" / "synthetic_database.db"

class DatabaseTool:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found at {self.db_path}. Run data/seed_data.py first.")
        return sqlite3.connect(self.db_path)

    def get_schema(self) -> Dict[str, List[str]]:
        """Returns the schema of all tables for LLM prompt context."""
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cur.fetchall()]
        
        schema = {}
        for table in tables:
            cur.execute(f"PRAGMA table_info({table});")
            columns = [f"{col[1]} ({col[2]})" for col in cur.fetchall()]
            schema[table] = columns
        conn.close()
        return schema

    def execute_read_only_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Executes a SELECT query safely. Rejects any write/mutation statements.
        """
        clean_query = query.strip()
        upper_query = clean_query.upper()
        
        # Guardrail: Prevent mutations
        forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "REPLACE"]
        first_word = upper_query.split()[0] if upper_query.split() else ""
        if first_word != "SELECT" and first_word != "WITH":
            raise ValueError(f"Security Alert: Only SELECT/WITH read queries are allowed. Received: {first_word}")
        
        for word in forbidden:
            # Check for standalone tokens
            if f" {word} " in f" {upper_query} ":
                raise ValueError(f"Security Alert: Query contains forbidden mutation keyword: {word}")

        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        try:
            cur.execute(clean_query)
            rows = [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()
        return rows

    def get_sales_anomaly_breakdown(self, start_date: str = "2026-10-15", split_date: str = "2026-10-22") -> Dict[str, Any]:
        """
        Direct analytical segmentation tool: compares baseline week against incident week
        broken down across regions, platforms, and error codes.
        """
        conn = self.get_connection()
        cur = conn.cursor()

        # 1. Weekly revenue comparison
        cur.execute("""
        SELECT 
            CASE WHEN date < ? THEN 'baseline' ELSE 'incident' END as period,
            ROUND(SUM(total_revenue), 2) as revenue,
            SUM(total_orders) as total_orders,
            SUM(successful_orders) as successful_orders,
            ROUND(100.0 * SUM(successful_orders) / SUM(total_orders), 2) as success_rate
        FROM daily_sales_summary
        WHERE date >= ?
        GROUP BY period
        """, (split_date, start_date))
        period_rows = {r[0]: dict(zip(["period", "revenue", "orders", "success_orders", "success_rate"], r)) for r in cur.fetchall()}

        baseline_rev = period_rows.get("baseline", {}).get("revenue", 1.0)
        incident_rev = period_rows.get("incident", {}).get("revenue", 1.0)
        overall_revenue_drop_pct = round(((baseline_rev - incident_rev) / baseline_rev) * 100.0, 2)

        # 2. Regional Breakdown
        cur.execute("""
        SELECT 
            region,
            ROUND(SUM(CASE WHEN date < ? THEN total_revenue ELSE 0 END), 2) as baseline_rev,
            ROUND(SUM(CASE WHEN date >= ? THEN total_revenue ELSE 0 END), 2) as incident_rev,
            ROUND(AVG(CASE WHEN date < ? THEN success_rate END), 2) as baseline_success_rate,
            ROUND(AVG(CASE WHEN date >= ? THEN success_rate END), 2) as incident_success_rate
        FROM daily_sales_summary
        WHERE date >= ?
        GROUP BY region
        """, (split_date, split_date, split_date, split_date, start_date))
        regions = []
        for r in cur.fetchall():
            b_rev, i_rev = r[1], r[2]
            drop = round(((b_rev - i_rev) / b_rev) * 100.0, 2) if b_rev else 0.0
            regions.append({
                "region": r[0],
                "baseline_revenue": b_rev,
                "incident_revenue": i_rev,
                "drop_percentage": drop,
                "baseline_success_rate": r[3],
                "incident_success_rate": r[4]
            })

        # 3. EU Platform & Error Code Slicing
        cur.execute("""
        SELECT 
            platform,
            error_code,
            COUNT(*) as count
        FROM orders
        WHERE region = 'EU' AND status = 'failed' AND timestamp >= ?
        GROUP BY platform, error_code
        ORDER BY count DESC
        """, (split_date + " 00:00:00",))
        eu_failures = [{"platform": r[0], "error_code": r[1], "count": r[2]} for r in cur.fetchall()]

        conn.close()

        return {
            "overall_revenue_drop_pct": overall_revenue_drop_pct,
            "period_metrics": period_rows,
            "regional_breakdown": regions,
            "eu_failure_slicing": eu_failures
        }

if __name__ == "__main__":
    tool = DatabaseTool()
    print("Database Schema:", tool.get_schema())
    print("\nAnomaly Breakdown:")
    breakdown = tool.get_sales_anomaly_breakdown()
    print(f"Overall Revenue Drop: {breakdown['overall_revenue_drop_pct']}%")
    for reg in breakdown['regional_breakdown']:
        print(f"  Region {reg['region']}: Revenue Drop = {reg['drop_percentage']}%, Success Rate: {reg['baseline_success_rate']}% -> {reg['incident_success_rate']}%")
