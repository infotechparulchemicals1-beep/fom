"""
Database migration runner for Supabase PostgreSQL.
Supports:
1. Direct PostgreSQL connection via pooler (port 5432 or 6543)
2. Supabase Management API (with Personal Access Token sbp_...)

Usage:
    python migrate.py
    python migrate.py "postgresql://postgres.erggjpdfkfaxpnxpieho:YOUR_PASSWORD@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres"
    python migrate.py --password "YOUR_PASSWORD"
    python migrate.py --pat "sbp_..."
"""
import sys
import os
import getpass
import json
import urllib.request
from pathlib import Path
from urllib.parse import quote_plus

DEFAULT_MIGRATION_FILE = "CLEAN_FRESH_MIGRATION.sql"
PROJECT_REF = "erggjpdfkfaxpnxpieho"
POOLER_HOST = "aws-0-ap-northeast-1.pooler.supabase.com"
POOLER_USER = f"postgres.{PROJECT_REF}"

def run_migration_management_api(pat_token: str, sql_content: str):
    print(f"[*] Executing migration via Supabase Management API (Project: {PROJECT_REF})...")
    url = f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query"
    headers = {
        "Authorization": f"Bearer {pat_token.strip()}",
        "Content-Type": "application/json",
    }
    payload = json.dumps({"query": sql_content}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"\n[SUCCESS] Migration applied successfully via Management API! (Status: {resp.status})")
            return True
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        print(f"\n[ERROR] Management API error {e.code}: {err_msg}")
        return False
    except Exception as e:
        print(f"\n[ERROR] Failed to execute via Management API: {e}")
        return False

def run_migration_postgres(db_url: str, sql_content: str):
    try:
        import psycopg2
    except ImportError:
        print("[*] Installing psycopg2-binary to connect to PostgreSQL...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
        import psycopg2

    print(f"[*] Connecting to Supabase PostgreSQL database at {POOLER_HOST}:5432...")
    try:
        conn = psycopg2.connect(db_url, connect_timeout=15)
        conn.autocommit = True
        with conn.cursor() as cur:
            print(f"[*] Executing {DEFAULT_MIGRATION_FILE}...")
            cur.execute(sql_content)
        conn.close()
        print("\n[SUCCESS] Migration applied successfully! All 17 tables, indexes, and RLS policies created.")
        return True
    except Exception as e:
        print(f"\n[ERROR] PostgreSQL execution failed: {e}")
        print("\nTip: You can also copy backend/CLEAN_FRESH_MIGRATION.sql directly into:")
        print(f"https://supabase.com/dashboard/project/{PROJECT_REF}/sql/new and click 'Run'.")
        return False

def run():
    backend_dir = Path(__file__).parent
    migration_file = backend_dir / DEFAULT_MIGRATION_FILE
    if not migration_file.exists():
        print(f"Error: Migration file not found at {migration_file}")
        return

    sql_content = migration_file.read_text(encoding="utf-8")

    # Check for PAT argument
    if "--pat" in sys.argv:
        idx = sys.argv.index("--pat")
        if idx + 1 < len(sys.argv):
            pat = sys.argv[idx + 1]
            if run_migration_management_api(pat, sql_content):
                return

    # Check for DB password argument
    pwd = None
    if "--password" in sys.argv:
        idx = sys.argv.index("--password")
        if idx + 1 < len(sys.argv):
            pwd = sys.argv[idx + 1]

    # Check for direct connection string
    db_url = None
    for arg in sys.argv[1:]:
        if arg.startswith("postgres://") or arg.startswith("postgresql://"):
            db_url = arg
            break

    if not db_url:
        env_pwd = os.environ.get("SUPABASE_DB_PASSWORD") or pwd
        if not env_pwd:
            print("\n--- Supabase Migration Runner ---")
            print(f"Project: {PROJECT_REF}")
            print(f"Host:    {POOLER_HOST}")
            print(f"User:    {POOLER_USER}")
            print("---------------------------------")
            print("Options:")
            print("1. Enter Supabase DB password below to apply automatically.")
            print("2. Or copy backend/CLEAN_FRESH_MIGRATION.sql into Supabase SQL Editor:")
            print(f"   https://supabase.com/dashboard/project/{PROJECT_REF}/sql/new\n")
            env_pwd = getpass.getpass("Enter your Supabase database password (or press Enter to cancel): ").strip()

        if not env_pwd:
            print("\nCanceled. You can run the SQL query directly in Supabase SQL Editor:")
            print(f"https://supabase.com/dashboard/project/{PROJECT_REF}/sql/new")
            return

        encoded_pwd = quote_plus(env_pwd)
        db_url = f"postgresql://{POOLER_USER}:{encoded_pwd}@{POOLER_HOST}:5432/postgres"

    run_migration_postgres(db_url, sql_content)

if __name__ == "__main__":
    run()
