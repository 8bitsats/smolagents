import os
import time
import psycopg2
from apscheduler.schedulers.background import BackgroundScheduler
from web_browser_agent import extract_token_data_from_letsbonk

# Neon PostgreSQL connection URL
DATABASE_URL = "postgresql://smolana_owner:npg_iUcRWt0wzuh8@ep-lingering-frost-a46k2ega-pooler.us-east-1.aws.neon.tech/smolana?sslmode=require"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def create_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tokens (
            id SERIAL PRIMARY KEY,
            name TEXT,
            contract_address TEXT,
            market_cap TEXT,
            time_posted TEXT,
            last_seen TIMESTAMP DEFAULT NOW(),
            UNIQUE(name, contract_address)
        );
    ''')
    conn.commit()
    cur.close()
    conn.close()

def upsert_tokens(tokens):
    conn = get_db_connection()
    cur = conn.cursor()
    for token in tokens:
        cur.execute('''
            INSERT INTO tokens (name, contract_address, market_cap, time_posted, last_seen)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (name, contract_address) DO UPDATE SET
                market_cap = EXCLUDED.market_cap,
                time_posted = EXCLUDED.time_posted,
                last_seen = NOW();
        ''', (
            token.get('name'),
            token.get('contract_address'),
            token.get('market_cap'),
            token.get('time_posted'),
        ))
    conn.commit()
    cur.close()
    conn.close()

def job():
    print("Creating tokens table only (no extraction)...")
    create_table()
    print("Table created.")

def main():
    create_table()
    scheduler = BackgroundScheduler()
    scheduler.add_job(job, 'interval', minutes=15)
    scheduler.start()
    print("Scheduler started. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

if __name__ == "__main__":
    main() 