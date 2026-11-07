import asyncio
import asyncpg
import os
import json
import sys
from pathlib import Path

env_file = Path(os.getenv('APPDATA')) / 'switchdash' / 'local-switch-server' / 'native' / 'run' / 'switch-core.env'
env = dict(line.strip().split('=', 1) for line in env_file.read_text(encoding='utf-8-sig').splitlines() if '=' in line)

async def main():
    conn = await asyncpg.connect(
        host=env['DB_HOST'],
        port=int(env['DB_PORT']),
        user=env['DB_OWNER_USER'],
        password=env['DB_OWNER_PASSWORD'],
        database=env['DB_NAME']
    )
    
    print("--- USERS COLUMNS ---")
    rows = await conn.fetch("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'users'")
    for r in rows:
        print(dict(r))

    print("\n--- USERS ---")
    rows = await conn.fetch("SELECT * FROM users")
    for r in rows:
        print(dict(r))

    print("\n--- EXTERNAL USERS ---")
    rows = await conn.fetch("SELECT * FROM external_users")
    for r in rows:
        print(dict(r))

    print("\n--- EXTERNAL USER CLAIMS ---")
    rows = await conn.fetch("SELECT * FROM external_user_claims")
    for r in rows:
        print(dict(r))

    print("\n--- CLIENTS (sample 5) ---")
    rows = await conn.fetch("SELECT * FROM clients LIMIT 10")
    for r in rows:
        print(dict(r))

    await conn.close()

asyncio.run(main())
