from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import os

# Neon PostgreSQL connection URL
DATABASE_URL = "postgresql://smolana_owner:npg_iUcRWt0wzuh8@ep-lingering-frost-a46k2ega-pooler.us-east-1.aws.neon.tech/smolana?sslmode=require"

app = FastAPI()

# Allow CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

@app.get("/tokens")
def get_tokens():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT name, contract_address, market_cap, time_posted, last_seen
        FROM tokens
        ORDER BY last_seen DESC
        LIMIT 100;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    tokens = [
        {
            "name": row[0],
            "contract_address": row[1],
            "market_cap": row[2],
            "time_posted": row[3],
            "last_seen": row[4].isoformat() if row[4] else None,
        }
        for row in rows
    ]
    return {"tokens": tokens}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("token_api:app", host="0.0.0.0", port=8000, reload=True) 