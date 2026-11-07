import asyncio
import asyncpg
import os
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
    
    # Claim external_user '6bcd61f7-b5fb-49a3-8ea9-f1e029b18fb0' ('user')
    await conn.execute("""
        INSERT INTO external_user_claims (external_user_id, user_id, created_at, tenant_id)
        VALUES ('6bcd61f7-b5fb-49a3-8ea9-f1e029b18fb0', '0a5f712a-c889-4ece-97a2-b88bebe30286', NOW(), '00000000-0000-0000-0000-000000000000')
        ON CONFLICT DO NOTHING
    """)
    print("Claim inserted successfully!")
    
    claims = await conn.fetch("SELECT * FROM external_user_claims")
    for c in claims:
        print("CLAIM:", dict(c))

    await conn.close()

asyncio.run(main())
