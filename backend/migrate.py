"""
Database migration runner for Supabase PostgreSQL.
Usage:
    python migrate.py "postgresql://postgres.erggjpdfkfaxpnxpieho:YOUR_PASSWORD@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres"
or simply:
    python migrate.py
(it will prompt you for your database password securely)
"""
import sys
import os
import getpass
from pathlib import Path

def run_migration():
    try:
        import psycopg2
    except ImportError:
        print("[*] Installing psycopg2-binary to connect to PostgreSQL...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
        import psycopg2

    migration_file = Path(__file__).parent / "supabase_migration.sql"
    if not migration_file.exists():
        print(f"Error: Migration file not found at {migration_file}")
        return

    sql_content = migration_file.read_text(encoding="utf-8")

    if len(sys.argv) > 1 and sys.argv[1].startswith("postgres"):
        db_url = sys.argv[1]
    else:
        print("\n--- Supabase Migration Runner ---")
        print("Project: erggjpdfkfaxpnxpieho")
        print("Host: aws-0-ap-northeast-1.pooler.supabase.com")
        print("User: postgres.erggjpdfkfaxpnxpieho\n")
        pwd = getpass.getpass("Enter your Supabase database password: ").strip()
        if not pwd:
            print("Password cannot be empty.")
            return
        # percent-encode special characters if necessary
        from urllib.parse import quote_plus
        encoded_pwd = quote_plus(pwd)
        db_url = f"postgresql://postgres.erggjpdfkfaxpnxpieho:{encoded_pwd}@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres"

    print("[*] Connecting to Supabase PostgreSQL database...")
    try:
        conn = psycopg2.connect(db_url, connect_timeout=15)
        conn.autocommit = True
        with conn.cursor() as cur:
            print("[*] Executing supabase_migration.sql...")
            cur.execute(sql_content)
        conn.close()
        print("\n[SUCCESS] Migration applied successfully! Tables and RLS policies created.")
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        print("\nTip: You can also copy backend/supabase_migration.sql directly into:")
        print("https://supabase.com/dashboard/project/erggjpdfkfaxpnxpieho/sql/new and click 'Run'.")

if __name__ == "__main__":
    run_migration()
