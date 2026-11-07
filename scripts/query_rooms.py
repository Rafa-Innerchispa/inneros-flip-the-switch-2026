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
    rooms = await conn.fetch('SELECT * FROM rooms')
    print('ROOMS:')
    for r in rooms:
        d = dict(r)
        print(d.get('id'), d.get('name'), d.get('owner_id'))
    
    links = await conn.fetch('SELECT * FROM client_rooms')
    print('\nCLIENT ROOMS:')
    for l in links:
        print(dict(l))
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
