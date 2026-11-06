using System.Collections.ObjectModel;
using Central.Desktop.Models;
using ProjectTaskStatus = Central.Desktop.Models.TaskStatus;

namespace Central.Desktop.Services;

public sealed class CentralStore : ObservableObject
{
    private ProjectModel? _selectedProject;

    public CentralStore()
    {
        Projects = new ObservableCollection<ProjectModel>();
        Team = new ObservableCollection<TeamMember>();
        SeedTeam();
        SeedProjects();
    }

    public ObservableCollection<ProjectModel> Projects { get; }
    public ObservableCollection<TeamMember> Team { get; }

    public ProjectModel? SelectedProject
    {
        get => _selectedProject;
        set => SetProperty(ref _selectedProject, value);
    }

    public IEnumerable<ActivityEvent> RecentActivity => Projects
        .SelectMany(project => project.Activity.Select(activity => new ActivityEvent(activity.Time, activity.Actor, project.Name, activity.Summary, activity.Tone)))
        .OrderBy(activity => ActivityAgeInMinutes(activity.Time))
        .Take(8);

    public IEnumerable<AgentSession> ActiveSessions => Projects.SelectMany(project => project.ActiveSessions);

    public OperationResult ClaimTask(ProjectModel project, ProjectTask task, string actor)
    {
        if (!project.IsOpen)
        {
            return Fail(project, "claim.blocked", $"A reserva foi bloqueada: {project.Name} está fechado.");
        }

        var semanticConflict = project.Tasks.FirstOrDefault(other =>
            other != task
            && string.Equals(other.Area, task.Area, StringComparison.OrdinalIgnoreCase)
            && other.Status is ProjectTaskStatus.Reserved or ProjectTaskStatus.InProgress);
        if (semanticConflict is not null)
        {
            return Fail(project, "claim.blocked", $"A área lógica {task.Area} já está ocupada por {semanticConflict.ClaimOwner ?? "outra sessão"}.");
        }

        if (task.Status != ProjectTaskStatus.Ready)
        {
            var owner = string.IsNullOrWhiteSpace(task.ClaimOwner) ? "outra sessão" : task.ClaimOwner;
            return Fail(project, "claim.blocked", $"A área {task.Area} já está ocupada por {owner}.");
        }

        task.Status = ProjectTaskStatus.Reserved;
        task.ClaimOwner = actor;
        project.AddActivity(new ActivityEvent(Now(), actor, "task.claimed", $"reservou {task.Id} · {task.Title}", "accent"));
        return Success($"Reserva criada para {task.Id}. A área lógica {task.Area} está protegida nesta simulação.");
    }

    public OperationResult ApplyWorkspaceChange(ProjectModel project, string actor, string summary)
        => ApplyWorkspaceChange(project, actor, summary, null);

    public OperationResult ApplyWorkspaceChange(ProjectModel project, string actor, string summary, int? expectedBaseRevision)
    {
        if (!project.IsOpen)
        {
            return Fail(project, "patch.denied", $"Alteração negada: {project.Name} está {project.StatusLabel.ToLowerInvariant()}.");
        }

        if (expectedBaseRevision.HasValue && expectedBaseRevision.Value != project.WorkspaceRevision)
        {
            return Fail(project, "patch.stale_base", $"Base obsoleta: o workspace está em {project.WorkspaceRevisionLabel}, mas o lote foi criado sobre r{expectedBaseRevision.Value}.");
        }

        project.WorkspaceRevision++;
        var commit = new WorkspaceCommit(
            $"commit-local-{project.WorkspaceRevision}",
            $"Lote local · {summary}",
            actor,
            project.WorkspaceRevisionLabel,
            Now(),
            "Registro técnico da simulação; não é commit Git e não altera repositório externo.");
        project.WorkspaceCommits.Insert(0, commit);
        project.AddActivity(new ActivityEvent(Now(), actor, "patch.applied", $"{summary} · workspace {project.WorkspaceRevisionLabel}", "accent"));
        return Success($"Patch aplicado atomicamente na revisão {project.WorkspaceRevisionLabel}. Nenhum repositório externo foi alterado.");
    }

    public OperationResult AdvanceSimulation(ProjectModel project, string actor)
    {
        if (!project.IsOpen)
        {
            return Fail(project, "stream.blocked", "O Pulso local não avança: o projeto está fechado.");
        }

        if (project.SimulationQueue.Count == 0)
        {
            return new OperationResult(false, "A fila manual já foi exibida por completo. Nenhum evento externo está conectado.", OperationState.Pending);
        }

        var next = project.SimulationQueue[0];
        project.SimulationQueue.RemoveAt(0);
        project.AddStreamEvent(next);
        project.AdvanceSimulationStep();
        project.AddActivity(new ActivityEvent(next.Time, next.Actor, next.Operation, $"{next.Summary} · {next.Result}", next.Tone));

        var session = project.ActiveSessions.FirstOrDefault(item => item.DisplayName.StartsWith(next.Actor.Split(' ', StringSplitOptions.RemoveEmptyEntries)[0], StringComparison.OrdinalIgnoreCase));
        if (session is not null)
        {
            session.Activity = $"{next.Operation}: {next.Result}";
        }

        project.RaiseForSimulation();
        return Success($"Evento {next.SequenceLabel} revelado no Pulso local. Nenhuma fonte externa foi consultada.");
    }

    public OperationResult CreateWorkspaceTag(ProjectModel project, string actor)
    {
        if (!project.IsOpen)
        {
            return Fail(project, "tag.blocked", "A tag local não pode ser criada enquanto o projeto está fechado.");
        }

        var name = $"local-r{project.WorkspaceRevision}";
        if (project.WorkspaceTags.Any(item => item.Name == name))
        {
            return new OperationResult(false, $"{name} já existe no manifesto local.", OperationState.Pending);
        }

        var tag = new WorkspaceTag(name, project.WorkspaceRevisionLabel, "Marco nomeado apenas para navegação e revisão local.", actor);
        project.WorkspaceTags.Insert(0, tag);
        project.AddActivity(new ActivityEvent(Now(), actor, "tag.created", $"criou a tag {tag.Name} em {tag.TargetRevision}; somente local", "blue"));
        project.RaiseForSimulation();
        return Success($"Tag {tag.Name} criada localmente. Ela não foi enviada a um provedor Git.");
    }

    public OperationResult CreateWorkspaceRelease(ProjectModel project, string actor)
    {
        if (!project.IsOpen)
        {
            return Fail(project, "release.blocked", "A release local não pode ser criada enquanto o projeto está fechado.");
        }

        var tag = project.WorkspaceTags.FirstOrDefault();
        if (tag is null)
        {
            return new OperationResult(false, "Crie uma tag local antes de rascunhar uma release.", OperationState.Pending);
        }

        var name = $"release-local-{project.WorkspaceReleases.Count + 1:00}";
        var release = new WorkspaceRelease(
            name,
            tag.Name,
            "RASCUNHO LOCAL · SEM DEPLOY",
            "Release nomeada para inspeção da interface; não é artefato publicado.",
            project.WorkspaceRevisionLabel);
        project.WorkspaceReleases.Insert(0, release);
        project.AddActivity(new ActivityEvent(Now(), actor, "release.created", $"rascunhou {release.Name} a partir de {release.Tag}; sem deploy", "blue"));
        project.RaiseForSimulation();
        return Success($"{release.Name} criada como rascunho local. Publicação continua desconectada.");
    }

    public IReadOnlyList<ProjectModel> ResolveProjects(string query)
    {
        if (string.IsNullOrWhiteSpace(query))
        {
            return Array.Empty<ProjectModel>();
        }

        return Projects
            .Where(project => project.Name.Contains(query, StringComparison.OrdinalIgnoreCase)
                || project.Id.Contains(query, StringComparison.OrdinalIgnoreCase)
                || project.Modules.Any(module => module.Contains(query, StringComparison.OrdinalIgnoreCase)))
            .ToList();
    }

    public OperationResult PostMessage(ProjectModel project, string author, string body)
    {
        if (!project.IsOpen)
        {
            return Fail(project, "message.denied", "O projeto está fechado. A mensagem não foi enviada; leitura continua disponível.");
        }

        project.Discussions.Insert(0, new DiscussionMessage(author, "pessoa", Now(), body, "comment", false, ResolveReferences(project, body)));
        project.AddActivity(new ActivityEvent(Now(), author, "discussion.message", "publicou uma mensagem na thread principal", "neutral"));
        return Success("Mensagem registrada na thread do projeto.");
    }

    public OperationResult CreateDelivery(ProjectModel project, string actor)
    {
        if (!project.IsOpen)
        {
            return Fail(project, "delivery.blocked", "Não é possível criar candidato: o projeto está fechado.");
        }

        var number = project.Deliveries.Count + 1;
        var delivery = new DeliveryCandidate($"DEL-{number:000}", "Workspace vivo + coordenação de reservas", "MÉDIO", $"sha256:sim-{project.WorkspaceRevision:X4}", DeliveryStatus.Draft, 0, "Evidências locais ainda não verificadas");
        project.Deliveries.Insert(0, delivery);
        project.AddActivity(new ActivityEvent(Now(), actor, "delivery.created", $"criou {delivery.Id} como rascunho local; evidências: {delivery.EvidenceCount}", "blue"));
        return Success($"{delivery.Id} criado como rascunho local. Evidências e revisão ainda não foram verificadas.");
    }

    public OperationResult ApproveDelivery(ProjectModel project, DeliveryCandidate delivery, string reviewer)
    {
        if (!project.IsOpen)
        {
            return Fail(project, "review.blocked", "A revisão não pode avançar enquanto o projeto está fechado.");
        }

        if (delivery.Status != DeliveryStatus.InReview)
        {
            return Fail(project, "review.blocked", "Este candidato não está aguardando revisão.");
        }

        if (delivery.EvidenceCount == 0)
        {
            return Fail(project, "review.blocked", "Aprovação negada: não há evidências reproduzíveis anexadas.");
        }

        delivery.Status = DeliveryStatus.Approved;
        project.AddActivity(new ActivityEvent(Now(), reviewer, "review.decided", $"aprovou {delivery.Id} com evidências vinculadas ao hash {delivery.Hash}", "accent"));
        return Success($"{delivery.Id} aprovada apenas nesta simulação local. Integração Git e publicação continuam separadas.");
    }

    public OperationResult IntegrateDelivery(ProjectModel project, DeliveryCandidate delivery, string actor)
    {
        if (!project.IsOpen)
        {
            return Fail(project, "merge.blocked", "Integração bloqueada: projeto fechado.");
        }

        if (delivery.Status != DeliveryStatus.Approved)
        {
            return Fail(project, "merge.blocked", "Integração bloqueada: a entrega precisa estar aprovada no hash atual.");
        }

        delivery.Status = DeliveryStatus.Integrated;
        project.AddActivity(new ActivityEvent(Now(), actor, "delivery.integrated", $"marcou {delivery.Id} como integração local; publicação permanece separada", "blue"));
        return Success($"{delivery.Id} marcado como integração local. Git não está conectado e nenhum deploy foi disparado.");
    }

    public OperationResult RunQuality(ProjectModel project, string actor)
    {
        var result = project.IsOpen ? "PASS" : "PENDENTE";
        var tone = project.IsOpen ? "accent" : "amber";
        var detail = project.IsOpen
            ? "12 cenários locais: reservas, revisão-base e fechamento durante patch."
            : "Projeto fechado: execução adiada até reabertura autorizada.";

        project.QualityChecks.Insert(0, new QualityCheck("Smoke suite da Central", result, detail, Now(), tone));
        project.AddActivity(new ActivityEvent(Now(), actor, "test.finished", $"smoke suite local: {result}; evidência vinculada", tone));
        return result == "PASS"
            ? Success("12 cenários executados na simulação local.")
            : new OperationResult(false, "A execução ficou pendente por causa do fechamento do projeto.", OperationState.Pending);
    }

    public OperationResult ToggleProjectLifecycle(ProjectModel project, string actor)
    {
        if (project.Status == ProjectStatus.Open)
        {
            project.Status = ProjectStatus.Closing;
            project.Generation++;
            project.AddActivity(new ActivityEvent(Now(), actor, "project.closing", "fechamento iniciado; novas escritas foram bloqueadas", "amber"));
            project.Status = ProjectStatus.Closed;
            project.AddActivity(new ActivityEvent(Now(), actor, "project.closed", $"projeto congelado em {project.WorkspaceRevisionLabel}", "amber"));
            return Success($"{project.Name} fechado em {project.WorkspaceRevisionLabel}. Leitura continua disponível; escrita e deploy estão bloqueados.");
        }

        if (project.Status == ProjectStatus.Closed)
        {
            project.Status = ProjectStatus.Reopening;
            project.Generation++;
            project.AddActivity(new ActivityEvent(Now(), actor, "project.reopening", "reabertura autorizada; sincronização sendo verificada", "blue"));
            project.Status = ProjectStatus.Open;
            project.AddActivity(new ActivityEvent(Now(), actor, "project.reopened", "projeto reaberto; reservas antigas não foram reaproveitadas", "accent"));
            return Success($"{project.Name} reaberto. Sessões precisam sincronizar antes de escrever.");
        }

        return Fail(project, "project.transition", "A transição já está em andamento.");
    }

    private static OperationResult Success(string message) => new(true, message);

    private static OperationResult Fail(ProjectModel project, string type, string message)
    {
        project.AddActivity(new ActivityEvent(Now(), "Central", type, message, "blocked"));
        var state = type.Contains("pending", StringComparison.OrdinalIgnoreCase)
            ? OperationState.Pending
            : type.Contains("error", StringComparison.OrdinalIgnoreCase)
                ? OperationState.Error
                : OperationState.Denied;
        return new OperationResult(false, message, state);
    }

    private static IReadOnlyList<WorkspaceReference> ResolveReferences(ProjectModel project, string body)
    {
        var references = new List<WorkspaceReference>();
        foreach (var task in project.Tasks.Where(item => body.Contains(item.Id, StringComparison.OrdinalIgnoreCase)))
        {
            references.Add(new WorkspaceReference("tarefa", task.Id, task.Id));
        }

        foreach (var file in project.WorkspaceFiles.Where(item => body.Contains(item.Path, StringComparison.OrdinalIgnoreCase)))
        {
            references.Add(new WorkspaceReference("arquivo", file.FileName, file.Path));
        }

        foreach (var tag in project.WorkspaceTags.Where(item => body.Contains(item.Name, StringComparison.OrdinalIgnoreCase)))
        {
            references.Add(new WorkspaceReference("tag", tag.Name, tag.Name));
        }

        if (body.Contains(project.WorkspaceRevisionLabel, StringComparison.OrdinalIgnoreCase))
        {
            references.Add(new WorkspaceReference("revisão", project.WorkspaceRevisionLabel, project.WorkspaceRevisionLabel));
        }

        if (body.Contains("linha", StringComparison.OrdinalIgnoreCase))
        {
            references.Add(new WorkspaceReference("linha", "linha citada", "line:unknown", false, "Código fonte não está aberto nesta instalação"));
        }

        return references;
    }

    private static string Now() => DateTime.Now.ToString("HH:mm");

    private static int ActivityAgeInMinutes(string label)
    {
        if (string.Equals(label, "agora", StringComparison.OrdinalIgnoreCase))
        {
            return 0;
        }

        if (label.StartsWith("há ", StringComparison.OrdinalIgnoreCase) && label.EndsWith(" min", StringComparison.OrdinalIgnoreCase))
        {
            var numericPart = label[3..^4].Trim();
            if (int.TryParse(numericPart, out var minutes))
            {
                return minutes;
            }
        }

        if (string.Equals(label, "ontem", StringComparison.OrdinalIgnoreCase))
        {
            return 24 * 60;
        }

        if (DateTime.TryParse(label, out var clockTime))
        {
            var now = DateTime.Now;
            var timestamp = now.Date.Add(clockTime.TimeOfDay);
            if (timestamp > now)
            {
                timestamp = timestamp.AddDays(-1);
            }

            return Math.Max(0, (int)(now - timestamp).TotalMinutes);
        }

        return int.MaxValue;
    }

    private void SeedTeam()
    {
        Team.Add(new TeamMember("Ana Martins", "Backend e sistemas", "Líder técnica", "Em foco", "Parser e contratos", true));
        Team.Add(new TeamMember("Bruno Costa", "Backend e sistemas", "Desenvolvedor", "Em foco", "API de cadastro", true));
        Team.Add(new TeamMember("Caio Nunes", "Backend e sistemas", "Desenvolvedor", "Disponível", "Revisão cruzada", false));
        Team.Add(new TeamMember("Davi Rocha", "Backend e sistemas", "Infraestrutura", "Em foco", "Backups e runners", true));
        Team.Add(new TeamMember("Elisa Prado", "Frontend e aplicações", "Desenvolvedora", "Em foco", "UI de registro", true));
        Team.Add(new TeamMember("Fábio Lima", "Frontend e aplicações", "Desenvolvedor", "Disponível", "Acessibilidade", false));
        Team.Add(new TeamMember("Gabi Alves", "Testes e qualidade", "QA", "Em foco", "Testes de concorrência", true));
        Team.Add(new TeamMember("Helena Luz", "Experiência e interface", "Design de produto", "Disponível", "Fluxos e consistência", false));
        Team.Add(new TeamMember("Ícaro Melo", "Produto e documentação", "Produto / arquitetura", "Em foco", "Entrevistas e escopo", true));
    }

    private void SeedProjects()
    {
        var seloryn = new ProjectModel("proj-seloryn-exemplo", "Seloryn", "Compilador, runtime e CLI para a linguagem Seloryn.", "Ícaro Melo", ProjectStatus.Open, 127, 1);
        seloryn.PriorityTier = "TIER I";
        seloryn.LogoPathData = "M120,37 H69 C46,37 35,49 35,66 C35,83 47,91 69,91 H97 M40,125 H91 C115,125 126,113 126,95 C126,78 114,69 92,69 H63";
        seloryn.Modules.Add("compiler");
        seloryn.Modules.Add("runtime");
        seloryn.Modules.Add("cli");
        seloryn.Tasks.Add(new ProjectTask("TASK-29", "Concluir suíte de testes da CLI", "Cobrir erros de entrada, reconexão e saída legível.", "module:cli/tests", "Alta", ProjectTaskStatus.Ready, "9 sessões e retries reproduzíveis", "—", "TASK-18"));
        seloryn.Tasks.Add(new ProjectTask("TASK-31", "Implementar contrato api.registration.v1", "Fechar campos, erros e versão consumida pela UI.", "contract:api.registration", "Alta", ProjectTaskStatus.InProgress, "Contrato validado e consumidores notificados", "Bruno + Claude", "REQ-012"));
        seloryn.Tasks.Add(new ProjectTask("TASK-32", "Revisar parser do compilador", "Validar a regra de tokens reservados sem alterar o runtime.", "compiler.parser", "Média", ProjectTaskStatus.Reserved, "Diff com testes de regressão", "Ana + Codex", "TASK-21"));
        seloryn.Tasks.Add(new ProjectTask("TASK-33", "Documentar recuperação após desconexão", "Registrar last_seq, snapshot e reconciliação.", "docs:sync-recovery", "Média", ProjectTaskStatus.Blocked, "Decisão ADR-0004 aprovada", "—", "ADR-0004"));
        seloryn.Tasks.Add(new ProjectTask("TASK-34", "Smoke test do runtime", "Executar cenários de execução em ambiente isolado.", "runtime:smoke", "Baixa", ProjectTaskStatus.InReview, "Logs filtrados anexados", "Caio Nunes", "TASK-26"));
        seloryn.ActiveSessions.Add(new AgentSession("Ana · Codex", "Codex", "TASK-32 · Revisar parser", "compiler.parser", true, "Validando dependências do AST"));
        seloryn.ActiveSessions.Add(new AgentSession("Bruno · Claude", "Claude", "TASK-31 · Contrato", "contract:api.registration", true, "Aguardando confirmação do frontend"));
        seloryn.ActiveSessions.Add(new AgentSession("Gabi · QA", "Manual + runner", "TASK-34 · Smoke test", "runtime:smoke", true, "Último check: 12/12"));
        seloryn.ActiveSessions.Add(new AgentSession("Elisa · Codex", "Codex", "TASK-18 · UI", "ui.registration", false, "Sessão desconectada; pedido pendente"));
        seloryn.Activity.Add(new ActivityEvent("agora", "Central", "workspace.revision_updated", "revisão do workspace local confirmada em r127", "accent"));
        seloryn.Activity.Add(new ActivityEvent("há 4 min", "Bruno · Claude", "integration.requested", "frontend precisa do contrato api.registration.v1", "blue"));
        seloryn.Activity.Add(new ActivityEvent("há 8 min", "Gabi · QA", "test.finished", "smoke test do runtime: 12/12 cenários locais", "accent"));
        seloryn.Activity.Add(new ActivityEvent("há 12 min", "Ana · Codex", "claim.created", "reserva lógica compiler.parser renovada", "neutral"));
        seloryn.Activity.Add(new ActivityEvent("há 19 min", "Ícaro", "decision.recorded", "ADR-0003: revisão humana para mudanças de autenticação", "amber"));
        seloryn.Discussions.Add(new DiscussionMessage(
            "Bruno · Claude",
            "IA",
            "há 4 min",
            "Pedido de contrato: qual é a resposta 409 esperada para e-mail já registrado?",
            "integration_request",
            false,
            new[]
            {
                new WorkspaceReference("tarefa", "TASK-31", "TASK-31"),
                new WorkspaceReference("arquivo", "api.registration.v1.yaml", "contracts/api.registration.v1.yaml"),
                new WorkspaceReference("linha", "linha citada", "line:unknown", false, "Código fonte não está aberto nesta instalação")
            }));
        seloryn.Discussions.Add(new DiscussionMessage(
            "Elisa",
            "pessoa",
            "há 2 min",
            "Vou consumir a proposta assim que o contrato estiver em estado acordado. @Bruno, deixei a UI pronta para a revisão local.",
            "comment",
            false,
            new[]
            {
                new WorkspaceReference("pessoa", "@Bruno", "Bruno Costa"),
                new WorkspaceReference("IA", "Claude", "Claude"),
                new WorkspaceReference("arquivo", "registration.xaml", "src/ui/registration.xaml", false, "Arquivo de UI ainda não foi incluído no manifesto")
            }));
        seloryn.Discussions.Add(new DiscussionMessage("Central", "sistema", "há 1 min", "Sessão backend offline: pedido mantido como pendente, sem resposta inventada.", "notification", true));
        seloryn.Deliveries.Add(new DeliveryCandidate("DEL-007", "Parser + testes de regressão", "MÉDIO", "sha256:8f12a0", DeliveryStatus.InReview, 5, "Gabi aguarda revisão independente"));
        seloryn.Deliveries.Add(new DeliveryCandidate("DEL-006", "Ajuste de copy da CLI", "BAIXO", "sha256:4ca11d", DeliveryStatus.Approved, 3, "Caio Nunes"));
        seloryn.QualityChecks.Add(new QualityCheck("Contrato api.registration.v1", "PASS", "Compatibilidade verificada com o exemplo de payload.", "há 4 min", "accent"));
        seloryn.QualityChecks.Add(new QualityCheck("Concorrência de reservas", "PASS", "5 sobreposições negadas; 4 áreas independentes liberadas.", "há 8 min", "accent"));
        seloryn.QualityChecks.Add(new QualityCheck("Recuperação após queda", "PENDENTE", "A sessão de Elisa precisa reconectar para concluir o cenário.", "há 12 min", "amber"));
        SeedSelorynWorkspace(seloryn);
        SeedSelorynStream(seloryn);
        Projects.Add(seloryn);

        var sales = new ProjectModel("proj-vendas-exemplo", "Sistema de Vendas", "Painel de estoque e pedidos com integração de pagamentos isolada.", "Ícaro Melo", ProjectStatus.Open, 24, 2);
        sales.PriorityTier = "TIER II";
        sales.LogoPathData = "M3,5 H21 L19,16 H6 Z M8,20 A2,2 0 1 0 8,20.1 M17,20 A2,2 0 1 0 17,20.1 M5,9 H19";
        sales.Modules.Add("frontend");
        sales.Modules.Add("api");
        sales.Modules.Add("payments");
        sales.Tasks.Add(new ProjectTask("TASK-44", "Validar estoque concorrente", "Evitar venda acima do estoque em duas operações simultâneas.", "api.inventory", "Alta", ProjectTaskStatus.Ready, "Um sucesso e um conflito compreensível", "—", "REQ-044"));
        sales.Tasks.Add(new ProjectTask("TASK-45", "Mapa de checkout", "Documentar fluxo de pagamento sem capturar dados reais.", "docs:checkout", "Média", ProjectTaskStatus.Ready, "Fluxo revisado por produto", "—", "Entrevista"));
        sales.ActiveSessions.Add(new AgentSession("Davi · Runner", "Runner local", "TASK-43 · Backup", "infra:backup", true, "Snapshot diário concluído"));
        sales.Activity.Add(new ActivityEvent("há 22 min", "Davi", "snapshot.created", "backup de staging criado e verificável", "accent"));
        sales.Activity.Add(new ActivityEvent("há 31 min", "Helena", "decision.recorded", "fluxo de checkout aguarda entrevista", "amber"));
        sales.Discussions.Add(new DiscussionMessage("Helena", "pessoa", "há 31 min", "Antes de desenhar o checkout, preciso confirmar regras de cancelamento com a loja.", "question"));
        sales.QualityChecks.Add(new QualityCheck("Validação de payload", "PASS", "Erros de entrada cobertos no pacote local.", "há 42 min", "accent"));
        sales.WorkspaceFiles.Add(new WorkspaceFile("src/inventory/stock.service.cs", "Regra de reserva concorrente do estoque.", "api.inventory", "Davi · Runner", "r24", "leitura compartilhada"));
        sales.WorkspaceFiles.Add(new WorkspaceFile("docs/checkout-flow.md", "Fluxo de checkout sem dados reais de pagamento.", "docs:checkout", "Helena", "r23", "aguarda entrevista"));
        sales.StreamEvents.Add(new AgentStreamEvent("evt-sales-024", 24, "há 22 min", "Davi", "Runner local", "TASK-43", "infra:backup", "snapshot.created", "Snapshot de staging criado e verificável.", "PASS · local", "accent", new[] { new WorkspaceReference("arquivo", "stock.service.cs", "src/inventory/stock.service.cs") }));
        sales.SimulationStep = 1;
        Projects.Add(sales);

        var central = new ProjectModel("proj-interno-exemplo", "Projeto Interno", "Espaço reservado para decisões administrativas da plataforma.", "Ana Martins", ProjectStatus.Closed, 5, 4);
        central.PriorityTier = "TIER V";
        central.LogoPathData = "M19,5 H9 A4,4 0 0 0 9,19 H19 M15,9 H8";
        central.Modules.Add("dashboard");
        central.Modules.Add("auth");
        central.Tasks.Add(new ProjectTask("TASK-02", "Revisar política de retenção", "Documento congelado até decisão de governança.", "governance:retention", "Alta", ProjectTaskStatus.Blocked, "Aprovação humana registrada", "—", "ADR-0002"));
        central.ActiveSessions.Add(new AgentSession("Central · leitura", "Somente leitura", "Nenhuma tarefa de escrita", "—", false, "Projeto congelado em r5"));
        central.Activity.Add(new ActivityEvent("ontem", "Ana", "project.closed", "projeto congelado em r5 por decisão de governança", "amber"));
        central.Discussions.Add(new DiscussionMessage("Central", "sistema", "ontem", "Leitura permitida para membros autorizados; escrita, merge e deploy bloqueados.", "notification"));
        central.QualityChecks.Add(new QualityCheck("Snapshot congelado", "PASS", "Manifesto de hashes disponível para consulta.", "ontem", "accent"));
        Projects.Add(central);
    }

    private static void SeedSelorynWorkspace(ProjectModel project)
    {
        project.WorkspaceFiles.Add(new WorkspaceFile(
            "README.md",
            "Entrada principal do projeto e contrato de leitura da fixture local.",
            "docs:readme",
            "Central · fixture",
            "r127",
            "leitura local",
            "# Seloryn\n\nCompilador, runtime e CLI para a linguagem Seloryn.\n\n## Nesta fixture\n\nParser, runtime, CLI e contratos são exibidos como contexto local. Nenhum arquivo é alterado por esta visualização."));
        project.WorkspaceFiles.Add(new WorkspaceFile(
            "src/compiler/parser.rs",
            "Parser de tokens reservados e regras de entrada do compilador.",
            "compiler.parser",
            "Ana + Codex",
            "r127",
            "reservado · leitura compartilhada"));
        project.WorkspaceFiles.Add(new WorkspaceFile(
            "src/runtime/executor.rs",
            "Execução do runtime e superfície usada pelo smoke test.",
            "runtime:smoke",
            "Gabi · QA",
            "r126",
            "em verificação local"));
        project.WorkspaceFiles.Add(new WorkspaceFile(
            "src/cli/tests/connection.spec.cs",
            "Casos de retry e recuperação da CLI para a tarefa TASK-29.",
            "module:cli/tests",
            "livre",
            "r124",
            "disponível para reserva"));
        project.WorkspaceFiles.Add(new WorkspaceFile(
            "contracts/api.registration.v1.yaml",
            "Contrato proposto do cadastro; ainda não é uma API conectada.",
            "contract:api.registration",
            "Bruno + Claude",
            "r127",
            "proposto · aguardando consumidor"));
        project.WorkspaceFiles.Add(new WorkspaceFile(
            "docs/ADR-0004.md",
            "Decisão sobre last_seq, snapshot e recuperação após desconexão.",
            "docs:sync-recovery",
            "—",
            "r121",
            "bloqueado por decisão"));

        project.WorkspaceCommits.Add(new WorkspaceCommit(
            "commit-local-127",
            "Parser: preservar token reservado",
            "Ana + Codex",
            "r127",
            "há 12 min",
            "Checkpoint técnico local com teste de regressão."));
        project.WorkspaceCommits.Add(new WorkspaceCommit(
            "commit-local-126",
            "CLI: cobrir reconexão",
            "Gabi · QA",
            "r126",
            "há 18 min",
            "Registro local do cenário de retries."));
        project.WorkspaceTags.Add(new WorkspaceTag(
            "v0.8.0-local",
            "r127",
            "Marco nomeado para revisar parser e contrato.",
            "Ícaro"));
        project.WorkspaceTags.Add(new WorkspaceTag(
            "parser-review",
            "r126",
            "Tag de inspeção antes da entrega.",
            "Ana"));
        project.WorkspaceReleases.Add(new WorkspaceRelease(
            "Seloryn 0.8.0-local",
            "v0.8.0-local",
            "RASCUNHO LOCAL · SEM DEPLOY",
            "Nome para inspeção do dossiê; não é artefato publicado.",
            "r127"));
        project.SelectedWorkspaceFile = project.WorkspaceFiles[0];
    }

    private static void SeedSelorynStream(ProjectModel project)
    {
        project.StreamEvents.Add(new AgentStreamEvent(
            "evt-local-200",
            200,
            "agora",
            "Bruno",
            "Claude",
            "TASK-31",
            "contract:api.registration",
            "integration.requested",
            "Frontend pediu confirmação do erro 409 antes de consumir o contrato.",
            "PENDENTE · resposta externa não conectada",
            "amber",
            new[]
            {
                new WorkspaceReference("tarefa", "TASK-31", "TASK-31"),
                new WorkspaceReference("arquivo", "api.registration.v1.yaml", "contracts/api.registration.v1.yaml"),
                new WorkspaceReference("revisão", "r127", "r127")
            }));
        project.StreamEvents.Add(new AgentStreamEvent(
            "evt-local-199",
            199,
            "há 4 min",
            "Gabi",
            "Manual + runner",
            "TASK-34",
            "runtime:smoke",
            "test.finished",
            "Smoke test do runtime terminou com 12 de 12 cenários locais.",
            "PASS · evidência local",
            "accent",
            new[]
            {
                new WorkspaceReference("arquivo", "executor.rs", "src/runtime/executor.rs"),
                new WorkspaceReference("entrega", "DEL-007", "DEL-007")
            }));
        project.StreamEvents.Add(new AgentStreamEvent(
            "evt-local-198",
            198,
            "há 8 min",
            "Ana",
            "Codex",
            "TASK-32",
            "compiler.parser",
            "claim.heartbeat",
            "Renovou a reserva lógica e está validando dependências do AST.",
            "OBSERVADO · fixture local",
            "blue",
            new[]
            {
                new WorkspaceReference("arquivo", "parser.rs", "src/compiler/parser.rs"),
                new WorkspaceReference("tag", "parser-review", "parser-review")
            }));
        project.StreamEvents.Add(new AgentStreamEvent(
            "evt-local-197",
            197,
            "há 12 min",
            "Elisa",
            "Codex",
            "TASK-18",
            "ui.registration",
            "agent.waiting",
            "Sessão desconectada; o pedido permanece pendente sem resposta inventada.",
            "PENDENTE · offline local",
            "amber",
            new[]
            {
                new WorkspaceReference("pessoa", "Elisa", "Elisa Prado"),
                new WorkspaceReference("tarefa", "TASK-18", "TASK-18"),
                new WorkspaceReference("arquivo", "registration.xaml", "src/ui/registration.xaml", false, "Arquivo de UI ainda não está no manifesto")
            }));
        project.SimulationStep = project.StreamEvents.Count;
        project.SelectedStreamEvent = project.StreamEvents[0];

        project.EnqueueSimulationEvent(new AgentStreamEvent(
            "evt-local-201",
            201,
            "próximo",
            "Local developer",
            "sessão local",
            "TASK-29",
            "module:cli/tests",
            "task.claimed",
            "A tarefa de testes da CLI ficou pronta para uma reserva manual.",
            "PRÓXIMO · ação local disponível",
            "accent",
            new[]
            {
                new WorkspaceReference("tarefa", "TASK-29", "TASK-29"),
                new WorkspaceReference("arquivo", "connection.spec.cs", "src/cli/tests/connection.spec.cs")
            }));
        project.EnqueueSimulationEvent(new AgentStreamEvent(
            "evt-local-202",
            202,
            "próximo",
            "Bruno",
            "Claude",
            "TASK-31",
            "contract:api.registration",
            "contract.proposed",
            "Uma proposta de contrato foi preparada para a discussão; ainda não está implementada.",
            "PROPOSTO · requer confirmação do consumidor",
            "blue",
            new[]
            {
                new WorkspaceReference("arquivo", "api.registration.v1.yaml", "contracts/api.registration.v1.yaml"),
                new WorkspaceReference("tarefa", "TASK-31", "TASK-31")
            }));
        project.EnqueueSimulationEvent(new AgentStreamEvent(
            "evt-local-203",
            203,
            "próximo",
            "Gabi",
            "Manual + runner",
            "TASK-29",
            "module:cli/tests",
            "test.started",
            "A suíte local foi preparada para os cenários de nove sessões e retries.",
            "PENDENTE · execução ainda não iniciada",
            "amber",
            new[]
            {
                new WorkspaceReference("arquivo", "connection.spec.cs", "src/cli/tests/connection.spec.cs"),
                new WorkspaceReference("linha", "linha citada", "line:unknown", false, "Código fonte não está aberto nesta instalação")
            }));
        project.EnqueueSimulationEvent(new AgentStreamEvent(
            "evt-local-204",
            204,
            "próximo",
            "Central",
            "gateway local",
            "TASK-33",
            "docs:sync-recovery",
            "claim.blocked",
            "A documentação de recuperação continua bloqueada pela decisão ADR-0004.",
            "BLOQUEADO · depende de decisão",
            "blocked",
            new[]
            {
                new WorkspaceReference("arquivo", "ADR-0004.md", "docs/ADR-0004.md"),
                new WorkspaceReference("tarefa", "TASK-33", "TASK-33")
            }));
    }
}
