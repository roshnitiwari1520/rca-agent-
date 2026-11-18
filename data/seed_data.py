"""
Synthetic Dataset Generator for Multi-Agent Root Cause Analysis (RCA) Project.
Generates:
1. data/synthetic_database.db (SQLite database with 18% sales drop anomaly seeded in EU mobile)
2. data/mock_git_deploys.json (Git commits/PRs including culprit PR #482)
3. data/mock_slack_logs.json (Chat and incident threads around event window)
4. data/mock_funnel_analytics.json (Funnel telemetry showing conversion collapse)
"""

import sqlite3
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

# Fix seed for strict reproducibility (ground-truth defense)
random.seed(42)

DATA_DIR = Path(__file__).parent
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "synthetic_database.db"
GIT_PATH = DATA_DIR / "mock_git_deploys.json"
SLACK_PATH = DATA_DIR / "mock_slack_logs.json"
FUNNEL_PATH = DATA_DIR / "mock_funnel_analytics.json"

# Incident Timeline Anchor
INCIDENT_START = datetime(2026, 10, 22, 14, 15, 0)
START_DATE = datetime(2026, 10, 15, 0, 0, 0)
END_DATE = datetime(2026, 10, 28, 23, 59, 59)

REGIONS = ["US", "EU", "APAC", "LATAM"]
PLATFORMS = ["web", "ios", "android"]
CATEGORIES = ["Electronics", "Apparel", "Home & Kitchen", "Books"]

def seed_sqlite_database():
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE orders (
        order_id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        region TEXT NOT NULL,
        platform TEXT NOT NULL,
        amount REAL NOT NULL,
        status TEXT NOT NULL,
        error_code TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE daily_sales_summary (
        date TEXT NOT NULL,
        region TEXT NOT NULL,
        total_orders INTEGER NOT NULL,
        successful_orders INTEGER NOT NULL,
        total_revenue REAL NOT NULL,
        success_rate REAL NOT NULL,
        PRIMARY KEY (date, region)
    )
    """)

    orders = []
    current_time = START_DATE
    order_num = 10000

    print("Generating synthetic order transactions...")
    while current_time <= END_DATE:
        # Average ~120 orders per hour
        orders_in_hour = int(random.gauss(100, 15))
        for _ in range(max(10, orders_in_hour)):
            order_id = f"ORD-{order_num}"
            order_num += 1
            order_time = current_time + timedelta(seconds=random.randint(0, 3599))
            region = random.choices(REGIONS, weights=[0.35, 0.38, 0.17, 0.10])[0]
            platform = random.choices(PLATFORMS, weights=[0.40, 0.32, 0.28])[0]
            amount = round(random.uniform(25.0, 350.0), 2)

            # Check if this order falls in the anomaly window
            is_post_incident = order_time >= INCIDENT_START
            if is_post_incident and region == "EU":
                # Anomaly condition: EU mobile failure rate tuned to produce ~18% company-wide revenue drop
                fail_threshold = 0.85 if platform in ["ios", "android"] else 0.18
                if random.random() < fail_threshold:
                    status = "failed"
                    error_code = "ERR_502_PAYMENT_WEBHOOK_TIMEOUT"
                else:
                    status = "completed"
                    error_code = None
            else:
                # Normal baseline failure rate (2.5%)
                if random.random() < 0.025:
                    status = "failed"
                    error_code = random.choice(["CARD_DECLINED", "INSUFFICIENT_FUNDS", "EXPIRED_CARD"])
                else:
                    status = "completed"
                    error_code = None

            orders.append((
                order_id,
                order_time.strftime("%Y-%m-%d %H:%M:%S"),
                f"CUST-{random.randint(1000, 9999)}",
                region,
                platform,
                amount,
                status,
                error_code
            ))

        current_time += timedelta(hours=1)

    cursor.executemany("""
    INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, orders)

    # Populate daily aggregation table
    cursor.execute("""
    INSERT INTO daily_sales_summary
    SELECT 
        date(timestamp) as date,
        region,
        count(*) as total_orders,
        sum(case when status = 'completed' then 1 else 0 end) as successful_orders,
        round(sum(case when status = 'completed' then amount else 0.0 end), 2) as total_revenue,
        round(100.0 * sum(case when status = 'completed' then 1 else 0 end) / count(*), 2) as success_rate
    FROM orders
    GROUP BY date(timestamp), region
    ORDER BY date, region
    """)

    conn.commit()
    conn.close()
    print(f"Created SQLite database at {DB_PATH} with {len(orders)} transactions.")

def seed_git_deploys():
    deploys = [
        {
            "id": "PR-478",
            "title": "perf: improve redis caching on product catalog query",
            "author": "sarah.chen",
            "merged_at": "2026-10-21T09:30:00Z",
            "deployed_at": "2026-10-21T09:45:00Z",
            "service": "catalog-service",
            "files_changed": ["src/cache/redis.py", "src/services/catalog.py"],
            "impact": "low"
        },
        {
            "id": "PR-479",
            "title": "docs: update API documentation for order query endpoints",
            "author": "mike.ross",
            "merged_at": "2026-10-21T16:15:00Z",
            "deployed_at": "2026-10-21T16:20:00Z",
            "service": "docs",
            "files_changed": ["docs/api_v2.md"],
            "impact": "none"
        },
        {
            "id": "PR-480",
            "title": "feat(analytics): add impression tracking to product carousel",
            "author": "rachel.zane",
            "merged_at": "2026-10-22T10:00:00Z",
            "deployed_at": "2026-10-22T10:15:00Z",
            "service": "frontend-web",
            "files_changed": ["src/components/Carousel.tsx", "src/telemetry/events.ts"],
            "impact": "low"
        },
        {
            "id": "PR-481",
            "title": "fix(ui): adjust navbar padding on tablet viewport",
            "author": "harvey.specter",
            "merged_at": "2026-10-22T12:45:00Z",
            "deployed_at": "2026-10-22T13:00:00Z",
            "service": "frontend-web",
            "files_changed": ["src/styles/navbar.css"],
            "impact": "none"
        },
        {
            "id": "PR-482",
            "title": "refactor(checkout): update Stripe webhook endpoint and timeout configs for EU region",
            "author": "alex.dev",
            "merged_at": "2026-10-22T14:10:00Z",
            "deployed_at": "2026-10-22T14:15:00Z",
            "service": "payment-gateway-service",
            "files_changed": [
                "services/payment/stripe_client.py",
                "config/eu_gateway.yaml",
                "helm/values-eu.yaml"
            ],
            "diff_summary": "Reduced webhook timeout from 2000ms to 300ms; updated EU callback URL to deprecated endpoint format",
            "impact": "CRITICAL",
            "root_cause_flag": True
        },
        {
            "id": "PR-483",
            "title": "chore(deps): bump requests from 2.31.0 to 2.32.3",
            "author": "dependabot[bot]",
            "merged_at": "2026-10-23T04:00:00Z",
            "deployed_at": "2026-10-23T04:15:00Z",
            "service": "auth-service",
            "files_changed": ["requirements.txt"],
            "impact": "none"
        },
        {
            "id": "PR-484",
            "title": "perf(database): add composite index on customer order history",
            "author": "donna.paulsen",
            "merged_at": "2026-10-24T11:20:00Z",
            "deployed_at": "2026-10-24T11:35:00Z",
            "service": "order-service",
            "files_changed": ["migrations/20261024_add_index.sql"],
            "impact": "low"
        }
    ]

    with open(GIT_PATH, "w") as f:
        json.dump({"deployments": deploys}, f, indent=2)
    print(f"Created Git deploys JSON at {GIT_PATH}.")

def seed_slack_logs():
    slack_data = {
        "channels": {
            "general": [
                {"timestamp": "2026-10-22T11:30:00Z", "user": "sarah.chen", "text": "Anyone want to grab pizza for lunch today?"},
                {"timestamp": "2026-10-22T11:32:00Z", "user": "alex.dev", "text": "I'm in! Let me just finish this payment PR first."},
                {"timestamp": "2026-10-23T09:00:00Z", "user": "hr_team", "text": "Reminder: All hands meeting tomorrow at 3 PM UTC."}
            ],
            "dev-deployments": [
                {"timestamp": "2026-10-21T09:45:00Z", "user": "github-bot", "text": "PR #478 deployed to production (catalog-service)"},
                {"timestamp": "2026-10-22T10:15:00Z", "user": "github-bot", "text": "PR #480 deployed to production (frontend-web)"},
                {"timestamp": "2026-10-22T14:15:00Z", "user": "github-bot", "text": "PR #482 deployed to production (payment-gateway-service) by alex.dev"},
                {"timestamp": "2026-10-23T04:15:00Z", "user": "github-bot", "text": "PR #483 deployed to production (auth-service)"}
            ],
            "alerts-monitoring": [
                {"timestamp": "2026-10-22T08:00:00Z", "user": "datadog-bot", "text": "INFO: Daily backup completed successfully."},
                {"timestamp": "2026-10-22T14:48:00Z", "user": "datadog-bot", "text": "TRIGGERED: High 502 Rate on service [payment-gateway-service] region: [eu-central-1] threshold > 5% (current: 14.8%)"},
                {"timestamp": "2026-10-22T15:20:00Z", "user": "datadog-bot", "text": "TRIGGERED: Elevated checkout drop-off rate detected in region [EU] on mobile endpoints."},
                {"timestamp": "2026-10-23T02:00:00Z", "user": "datadog-bot", "text": "WARN: Memory usage on worker-pool-2 at 78%"}
            ],
            "incident-payments": [
                {"timestamp": "2026-10-22T14:55:00Z", "user": "support-lead", "text": "@channel We are getting angry customer tickets from Germany and France saying order placement is timing out on their phone."},
                {"timestamp": "2026-10-22T15:02:00Z", "user": "sarah.chen", "text": "Looking at EU payment service now. Webhook timeouts are spiking. Did anyone touch payments recently?"},
                {"timestamp": "2026-10-22T15:05:00Z", "user": "alex.dev", "text": "I merged PR #482 around 14:10 UTC to adjust EU gateway timeouts. Let me check the config."},
                {"timestamp": "2026-10-22T15:15:00Z", "user": "alex.dev", "text": "Wait, the timeout was set to 300ms instead of 3000ms in values-eu.yaml! Stripe EU webhooks usually take 800ms+ under load."}
            ]
        }
    }

    with open(SLACK_PATH, "w") as f:
        json.dump(slack_data, f, indent=2)
    print(f"Created Slack logs JSON at {SLACK_PATH}.")

def seed_funnel_analytics():
    funnel_data = {
        "metric_name": "checkout_conversion_funnel",
        "description": "Funnel drop-off analysis by region and platform comparing week before vs incident week",
        "baseline_period": "2026-10-15 to 2026-10-21",
        "incident_period": "2026-10-22 to 2026-10-28",
        "steps": [
            "1_session_start",
            "2_view_product",
            "3_add_to_cart",
            "4_checkout_start",
            "5_payment_completed"
        ],
        "funnel_by_region": {
            "US": {
                "baseline_checkout_to_payment_conversion_rate": 88.5,
                "incident_checkout_to_payment_conversion_rate": 88.2,
                "delta_percentage": -0.34
            },
            "APAC": {
                "baseline_checkout_to_payment_conversion_rate": 86.8,
                "incident_checkout_to_payment_conversion_rate": 86.5,
                "delta_percentage": -0.35
            },
            "LATAM": {
                "baseline_checkout_to_payment_conversion_rate": 84.1,
                "incident_checkout_to_payment_conversion_rate": 83.9,
                "delta_percentage": -0.24
            },
            "EU": {
                "baseline_checkout_to_payment_conversion_rate": 89.2,
                "incident_checkout_to_payment_conversion_rate": 21.4,
                "delta_percentage": -76.01,
                "platform_breakdown": {
                    "web": {"baseline": 90.1, "incident": 88.9, "delta": -1.33},
                    "ios": {"baseline": 88.7, "incident": 16.2, "delta": -81.74},
                    "android": {"baseline": 88.9, "incident": 14.8, "delta": -83.35}
                },
                "primary_dropoff_stage": "4_checkout_start -> 5_payment_completed",
                "dominant_error": "ERR_502_PAYMENT_WEBHOOK_TIMEOUT"
            }
        }
    }

    with open(FUNNEL_PATH, "w") as f:
        json.dump(funnel_data, f, indent=2)
    print(f"Created Funnel analytics JSON at {FUNNEL_PATH}.")

if __name__ == "__main__":
    print("=== Generating Synthetic RCA Ground Truth Datasets ===")
    seed_sqlite_database()
    seed_git_deploys()
    seed_slack_logs()
    seed_funnel_analytics()
    print("=== All Synthetic Datasets Generated Successfully ===")
