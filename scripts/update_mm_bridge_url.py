import asyncio
import asyncpg
import json
import os
import sys
from pathlib import Path

env_file = Path(os.getenv('APPDATA')) / 'switchdash' / 'local-switch-server' / 'native' / 'run' / 'switch-core.env'
env = dict(line.strip().split('=', 1) for line in env_file.read_text(encoding='utf-8-sig').splitlines() if '=' in line)

core_dir = Path(r'C:\Users\hrlg\AppData\Roaming\switchdash\local-switch-server\native\switch-core\0.31.0\src\core')
sys.path.insert(0, str(core_dir))

from switch_core.keys import Keyring
kr = Keyring.parse(env['SECRET_KEYS'], legacy_secret=env.get('JWT_SECRET_KEY'))

async def main():
    conn = await asyncpg.connect(
        host=env['DB_HOST'], port=int(env['DB_PORT']),
        user=env['DB_OWNER_USER'], password=env['DB_OWNER_PASSWORD'],
        database=env['DB_NAME']
    )
    rows = await conn.fetch("SELECT * FROM collaboration_bridges WHERE type='mattermost'")
    for r in rows:
        bridge_id = r['id']
        cfg = json.loads(r['connection_config'])
        if '_enc' in cfg:
            plain = kr.decrypt(cfg['_enc'])
            parsed = json.loads(plain)
            print('Current URL:', parsed.get('url'))
            if parsed.get('url') == 'http://localhost:62227':
                parsed['url'] = 'http://127.0.0.1:62227'
                new_plain = json.dumps(parsed)
                new_enc = kr.encrypt(new_plain)
                new_cfg = json.dumps({'_enc': new_enc})
                await conn.execute(
                    'UPDATE collaboration_bridges SET connection_config = $1 WHERE id = $2',
                    new_cfg, bridge_id
                )
                print('Updated bridge', bridge_id, 'url to http://127.0.0.1:62227')
                
                # Notify switch-core processes via pg_notify
                notify_payload = json.dumps({
                    'kind': 'bridge.changed',
                    'from': 'patch-script',
                    'bridge_id': str(bridge_id)
                })
                await conn.execute("SELECT pg_notify('switch_signal', $1)", notify_payload)
                print('Sent pg_notify for bridge.changed!')
            else:
                print('URL is already:', parsed.get('url'))

    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())

