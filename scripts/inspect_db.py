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
    tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    table_names = [t['table_name'] for t in tables]
    print('Tables:', table_names)
    for t in table_names:
        if any(term in t for term in ['bridge', 'collab', 'mattermost', 'room', 'agent']):
            rows = await conn.fetch(f'SELECT * FROM {t}')
            print(f'=== {t} ({len(rows)} rows) ===')
            for r in rows:
                d = dict(r)
                for k in d:
                    if any(s in k.lower() for s in ['token', 'password', 'secret', 'key']):
                        d[k] = '***'
                print(d)
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
