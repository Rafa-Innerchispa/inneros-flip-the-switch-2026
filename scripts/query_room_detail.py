import asyncio
import asyncpg
import os
from pathlib import Path

env_file = Path(os.getenv('APPDATA')) / 'switchdash' / 'local-switch-server' / 'native' / 'run' / 'switch-core.env'
env = dict(line.strip().split('=', 1) for line in env_file.read_text(encoding='utf-8-sig').splitlines() if '=' in line)

async def main():
    conn = await asyncpg.connect(
        host=env['DB_HOST'], port=int(env['DB_PORT']),
        user=env['DB_OWNER_USER'], password=env['DB_OWNER_PASSWORD'],
        database=env['DB_NAME']
    )
    rows = await conn.fetch("SELECT * FROM rooms")
    if rows:
        print("ROOM COLUMNS:", list(rows[0].keys()))
        for r in rows:
            d = dict(r)
            print({k: d[k] for k in ['id', 'name', 'bridge_id', 'external_channel_id', 'bridged'] if k in d})
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
