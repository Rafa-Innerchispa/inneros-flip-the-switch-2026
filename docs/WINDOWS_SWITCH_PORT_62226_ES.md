# Switch Console 0.40.1 | registro local de InnerOS sin API Keys en la interfaz

**Comprobado:** En las capturas de la version instalada no existe el menu `Settings > API keys`. El Core responde en `http://127.0.0.1:62226/health`, pero la raiz del servidor y Gateway no muestran el dashboard. No continuar buscando esos menus.

**Verificado en el codigo oficial de la etiqueta `switch-console-v0.40.1`:** el Core expone `POST /gateway/auth/login`, `POST /gateway/api-keys`, `DELETE /gateway/api-keys/{id}` y `POST /agents`. Switch Console escribe las credenciales de *su propio servidor* en `%APPDATA%\switchdash\local-switch-server\native\run\switch-core.env` para arrancarlo. No compartir ni editar ese archivo: incluye varios secretos.

## Un unico comando (PowerShell)

Con Switch Console abierto, descomprime el paquete en una carpeta. En PowerShell, ubicado en la carpeta que contiene `README.md` y `scripts`, ejecuta:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_switch_windows.ps1 -SwitchUrl http://127.0.0.1:62226
```

El instalador comprueba la API, crea un entorno Python, instala la dependencia `websockets`, obtiene la sesion **admin local** usando credenciales del archivo privado de Switch **sin imprimirlas**, crea una clave de registro **personal temporal**, registra `inneros-incident-triage` bajo `admin`, y revoca la clave temporal. La credencial de agente emitida se guarda bajo `%USERPROFILE%\.config\inneros-switch\agent-credentials.json`, nunca dentro del repositorio. Si ya existe, no registra de nuevo ni sobrescribe las claves. La conexion de login se limita a localhost y omite proxies.

Esta tecnica es una via de integracion con las rutas API publicas de Switch, no una funcionalidad de interfaz. Si el proceso devuelve `BLOCKED` o un error HTTP, **no intentar extraer o pegar contrasenas**: no se ha probado en el servidor real y necesita diagnostico del error concreto.

## Despues

En Switch Console, agregar el agente `inneros-incident-triage` a la sala existente `#inneros-live-operations`. Luego, en la misma carpeta:

```powershell
.\.venv\Scripts\python.exe scripts\discover_rooms.py
```

Nada de esto prueba todavia el mensaje real desde Mattermost o Home Assistant. No activar `HA_ENABLE_REAL_ACTIONS` antes de comprobar primero las lecturas y autorizaciones de la sala.

**Codigo fuente oficial versionado:**
- https://github.com/sandbox-quantum/switch/blob/switch-console-v0.40.1/core/switch_core/gateway/auth_routes.py
- https://github.com/sandbox-quantum/switch/blob/switch-console-v0.40.1/core/switch_core/gateway/api_keys.py
- https://github.com/sandbox-quantum/switch/blob/switch-console-v0.40.1/core/switch_core/bridges/agent/api/handlers.py
- https://github.com/sandbox-quantum/switch/blob/switch-console-v0.40.1/console/apps/switch-console-desktop/src/main/core/managed-switch-server/native/core-process.ts
