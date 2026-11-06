# Central no PythonAnywhere

Este diretório contém o gateway WSGI mínimo para o smoke test da infraestrutura
da Central. Ele é compatível com o plano gratuito do PythonAnywhere porque não
depende de Flask, FastAPI ou de um processo residente separado.

## Configuração do web app

1. Crie um web app manual com Python 3.12 para `MarcosBuilds.pythonanywhere.com`.
2. Faça upload de `central_gateway.py` para `/home/MarcosBuilds/central_gateway.py`.
3. No arquivo WSGI do web app, use:

   ```python
   import sys

   project_home = "/home/MarcosBuilds"
   if project_home not in sys.path:
       sys.path.insert(0, project_home)

   from central_gateway import application
   ```

4. Recarregue o web app e valide `/healthz` e `/v1/capabilities`.

As variáveis opcionais `CENTRAL_SUPABASE_URL` e
`CENTRAL_SUPABASE_PUBLISHABLE_KEY` só devem ser definidas no painel de variáveis
do PythonAnywhere. O gateway informa apenas se elas existem; nunca devolve os
valores e nunca aceita uma service-role key.

## Limites deliberados

O gateway publicado é um ponto de saúde e capacidades. Ele não mantém SSE
contínuo nem transporta bytes da pasta. O desktop usa Supabase Realtime/WebSocket
para avisos retomáveis e Syncthing para a sincronização P2P; o Supabase é a
fonte de dados de coordenação e o PythonAnywhere não é armazenamento de código
nem disco de sincronização.
