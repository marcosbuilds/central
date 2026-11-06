# Central on PythonAnywhere

This directory contains the minimal WSGI gateway used for Central's
infrastructure smoke test. It is compatible with PythonAnywhere's free plan
because it does not depend on Flask, FastAPI, or a separate resident process.

## Web app configuration

1. Create a manual web app with Python 3.12 on the operator's account.
2. Upload `central_gateway.py` to a private project directory chosen by the
   operator. Do not publish the account name or absolute host path.
3. In the web app's WSGI file, use:

   ```python
   import sys

   project_home = "/home/<pythonanywhere-user>/central"
   if project_home not in sys.path:
       sys.path.insert(0, project_home)

   from central_gateway import application
   ```

4. Reload the web app and validate `/healthz` and `/v1/capabilities`.

The optional `CENTRAL_SUPABASE_URL` and
`CENTRAL_SUPABASE_PUBLISHABLE_KEY` variables should only be defined in
PythonAnywhere's environment-variable panel. The gateway reports only whether
they exist; it never returns their values and never accepts a service-role key.

## Deliberate limits

The published gateway is a health and capabilities endpoint. It does not keep a
continuous SSE connection or transport folder bytes. The desktop uses Supabase
Realtime/WebSocket for resumable notifications and Syncthing for P2P
synchronization; Supabase is the coordination data source, and PythonAnywhere
is neither code storage nor a synchronization disk.
