# Arquitetura da entrega local

## Escolha

A primeira fase usa um monólito desktop WPF em .NET 8. A decisão é intencional: a documentação recomenda validar primeiro o núcleo de coordenação e não começar por microsserviços ou por um dashboard decorativo. A aplicação mantém separação entre shell, views, view model, modelos de domínio e `CentralStore`.

O incremento operacional adiciona `Central.Core` com reservas, leases e adaptadores de conectividade. A colaboração entre computadores usa três planos separados: Syncthing transporta bytes; Supabase Auth/PostgreSQL/Realtime autoriza, registra estado e entrega notificações; PythonAnywhere fornece apenas saúde/capacidades. O coordenador em memória e os fixtures do catálogo não são autoridade compartilhada.

```text
MainWindow
  ├── DashboardView
  ├── ProjectsView
  ├── ProjectView
  ├── TeamView
  └── SettingsView

CentralViewModel
  └── CentralStore
        ├── Projects / Tasks / Claims simulados
        ├── Activity / Discussions
        ├── Deliveries / Quality checks
        └── Team / Agent sessions

CentralSyncRuntime
  ├── SyncthingRuntime + SyncthingClient (bytes, peers, pause, status)
  ├── SupabaseRestClient (Auth, RPCs, snapshot/replay, heartbeat)
  └── SupabaseRealtimeClient (canal privado, presença, reconnect, replay)
```

## Regras exercitadas

- Projeto selecionado por registro do catálogo, sem usar nome de pasta como chave.
- Reserva de tarefa com conflito semântico por área lógica.
- Patch aceito somente para projeto aberto e, quando informado, para a revisão-base atual.
- Revisão do workspace monotônica e recuperável.
- Fechamento incrementa a geração/fencing local e bloqueia escrita, reserva, entrega e integração.
- Candidato de entrega exige evidências, não é deploy e só integra depois da aprovação.
- Eventos de atividade exibem fatos observáveis e não raciocínio privado ou telemetria invasiva.

## Estado atual e limites

`CentralStore` continua como fonte das telas visuais e não foi convertido silenciosamente em um catálogo remoto. A vertical slice de sincronização é explícita e separada: exige sessão Supabase, organização/projeto válidos e uma pasta dedicada. A migração `202611060002_sync_stream.sql` já foi aplicada ao projeto dedicado e adiciona RPCs, RLS, publicação Realtime e filtro de peers por projeto. Ainda faltam a prova física observada em dois PCs, convites/membros na UI e a integração de Git/CI/deploy.
