import re
import secrets
from pathlib import Path

src = Path('/home/rlopez/inneros/modules/switch-repo/.env.example').read_text()
dst_dir = Path('/home/rlopez/inneros/modules/switch-liveops/compose')
dst_dir.mkdir(parents=True, exist_ok=True)

replacements = {
    'SWITCH_VERSION': '0.31.0',
    'SWITCH_BIND_ADDR': '127.0.0.1',
    'GATEWAY_HOST_PORT': '62325',
    'API_HOST_PORT': '62326',
    'MATTERMOST_HOST_PORT': '62327',
    'POSTGRES_HOST_PORT': '62328',
    'GATEWAY_ADMIN_EMAIL': 'admin@inneros.local',
    'DB_PASSWORD': secrets.token_hex(24),
    'DB_OWNER_PASSWORD': secrets.token_hex(24),
    'AGENT_REGISTRATION_TOKEN': secrets.token_hex(24),
    'GATEWAY_ADMIN_PASSWORD': secrets.token_hex(24),
    'MATTERMOST_ADMIN_PASSWORD': secrets.token_hex(24),
    'MATTERMOST_USER_PASSWORD': secrets.token_hex(24),
    'SECRET_KEYS': 'local:' + secrets.token_hex(32)
}

out_lines = []
for line in src.splitlines():
    m = re.match(r'^([A-Z0-9_]+)=', line)
    if m and m.group(1) in replacements:
        out_lines.append(f'{m.group(1)}={replacements[m.group(1)]}')
    else:
        out_lines.append(line)

out_lines.append('COMPOSE_PROJECT_NAME=inneros-switch-amd')
(dst_dir / '.env').write_text('\n'.join(out_lines) + '\n')
print('Generated .env successfully!')
