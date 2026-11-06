using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace Central.Desktop.Models;

public abstract class ObservableObject : INotifyPropertyChanged
{
    public event PropertyChangedEventHandler? PropertyChanged;

    protected bool SetProperty<T>(ref T field, T value, [CallerMemberName] string? propertyName = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value))
        {
            return false;
        }

        field = value;
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        return true;
    }

    protected void Raise([CallerMemberName] string? propertyName = null)
        => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
}

public enum ProjectStatus
{
    Open,
    Closing,
    Closed,
    Reopening
}

public enum TaskStatus
{
    Ready,
    Reserved,
    InProgress,
    InReview,
    Blocked,
    Done,
    Cancelled
}

public enum OperationState
{
    Success,
    Error,
    Pending,
    Denied
}

public sealed record OperationResult(bool Success, string Message, OperationState State = OperationState.Success);

public sealed class WorkspaceReference
{
    public WorkspaceReference(string kind, string label, string targetId, bool isResolvable = true, string? hint = null)
    {
        Kind = kind;
        Label = label;
        TargetId = targetId;
        IsResolvable = isResolvable;
        Hint = hint ?? (isResolvable ? "Abrir referência local" : "Indisponível nesta simulação");
    }

    public string Kind { get; }
    public string Label { get; }
    public string TargetId { get; }
    public bool IsResolvable { get; }
    public string Hint { get; }
    public string AccessibleLabel => IsResolvable ? $"{Kind} {Label}; abrir referência local" : $"{Kind} {Label}; referência indisponível nesta simulação";
    public string Tone => IsResolvable ? "resolvable" : "unavailable";
}

public sealed class WorkspaceFile : ObservableObject
{
    private bool _isSelected;
    private readonly string _previewContent;

    public WorkspaceFile(string path, string description, string area, string owner, string revisionLabel, string status, string? previewContent = null)
    {
        Path = path;
        Description = description;
        Area = area;
        Owner = owner;
        RevisionLabel = revisionLabel;
        Status = status;
        _previewContent = previewContent ?? description;
    }

    public string Path { get; }
    public string Description { get; }
    public string Area { get; }
    public string Owner { get; }
    public string RevisionLabel { get; }
    public string Status { get; }
    public string FileName => Path.Split('/', StringSplitOptions.RemoveEmptyEntries).LastOrDefault() ?? Path;
    public string DirectoryLabel => Path.Contains('/') ? Path[..Path.LastIndexOf('/')] : "raiz";
    public string FileTypeLabel => Path.EndsWith(".md", StringComparison.OrdinalIgnoreCase) ? "MD"
        : Path.EndsWith(".pdf", StringComparison.OrdinalIgnoreCase) ? "PDF"
        : Path.EndsWith(".zip", StringComparison.OrdinalIgnoreCase) ? "ZIP"
        : Path.EndsWith(".yaml", StringComparison.OrdinalIgnoreCase) || Path.EndsWith(".yml", StringComparison.OrdinalIgnoreCase) ? "YML"
        : Path.EndsWith(".rs", StringComparison.OrdinalIgnoreCase) ? "RS"
        : Path.EndsWith(".cs", StringComparison.OrdinalIgnoreCase) ? "CS"
        : "FILE";
    public bool IsMarkdown => Path.EndsWith(".md", StringComparison.OrdinalIgnoreCase);
    public string PreviewContent => _previewContent;
    public bool IsSelected
    {
        get => _isSelected;
        set => SetProperty(ref _isSelected, value);
    }
}

public sealed class WorkspaceCommit
{
    public WorkspaceCommit(string id, string title, string actor, string revisionLabel, string time, string summary)
    {
        Id = id;
        Title = title;
        Actor = actor;
        RevisionLabel = revisionLabel;
        Time = time;
        Summary = summary;
    }

    public string Id { get; }
    public string Title { get; }
    public string Actor { get; }
    public string RevisionLabel { get; }
    public string Time { get; }
    public string Summary { get; }
    public string KindLabel => "COMMIT TÉCNICO · LOCAL";
    public string AccessibleLabel => $"Selecionar commit {Title} · {RevisionLabel}";
}

public sealed class WorkspaceTag
{
    public WorkspaceTag(string name, string targetRevision, string description, string createdBy)
    {
        Name = name;
        TargetRevision = targetRevision;
        Description = description;
        CreatedBy = createdBy;
    }

    public string Name { get; }
    public string TargetRevision { get; }
    public string Description { get; }
    public string CreatedBy { get; }
    public string KindLabel => "TAG · LOCAL";
    public string AccessibleLabel => $"Selecionar tag {Name} · {TargetRevision}";
}

public sealed class WorkspaceRelease
{
    public WorkspaceRelease(string name, string tag, string status, string notes, string targetRevision)
    {
        Name = name;
        Tag = tag;
        Status = status;
        Notes = notes;
        TargetRevision = targetRevision;
    }

    public string Name { get; }
    public string Tag { get; }
    public string Status { get; }
    public string Notes { get; }
    public string TargetRevision { get; }
    public string KindLabel => "RELEASE · LOCAL";
    public string AccessibleLabel => $"Selecionar release {Name} · {Status}";
}

public sealed class AgentStreamEvent : ObservableObject
{
    private bool _isSelected;

    public AgentStreamEvent(string eventId, int sequence, string time, string actor, string provider, string taskId, string resource, string operation, string summary, string result, string tone, IEnumerable<WorkspaceReference>? references = null)
    {
        EventId = eventId;
        Sequence = sequence;
        Time = time;
        Actor = actor;
        Provider = provider;
        TaskId = taskId;
        Resource = resource;
        Operation = operation;
        Summary = summary;
        Result = result;
        Tone = tone;
        References = new ObservableCollection<WorkspaceReference>(references ?? Array.Empty<WorkspaceReference>());
    }

    public string EventId { get; }
    public int Sequence { get; }
    public string Time { get; }
    public string Actor { get; }
    public string Provider { get; }
    public string TaskId { get; }
    public string Resource { get; }
    public string Operation { get; }
    public string Summary { get; }
    public string Result { get; }
    public string Tone { get; }
    public ObservableCollection<WorkspaceReference> References { get; }
    public string SequenceLabel => $"{Sequence:000}";
    public string ActorLabel => $"{Actor} · {Provider}";
    public string ScopeLabel => $"{TaskId} · {Resource}";
    public string OperationLabel => $"{Operation} · {Result}";
    public bool IsSelected
    {
        get => _isSelected;
        set => SetProperty(ref _isSelected, value);
    }
}

public sealed class ProjectModel : ObservableObject
{
    private ProjectStatus _status;
    private int _workspaceRevision;
    private int _generation;

    public ProjectModel(string id, string name, string description, string owner, ProjectStatus status, int workspaceRevision, int generation)
    {
        Id = id;
        Name = name;
        Description = description;
        Owner = owner;
        _status = status;
        _workspaceRevision = workspaceRevision;
        _generation = generation;
        Tasks = new ObservableCollection<ProjectTask>();
        ActiveSessions = new ObservableCollection<AgentSession>();
        Activity = new ObservableCollection<ActivityEvent>();
        Discussions = new ObservableCollection<DiscussionMessage>();
        Deliveries = new ObservableCollection<DeliveryCandidate>();
        QualityChecks = new ObservableCollection<QualityCheck>();
        Modules = new ObservableCollection<string>();
        WorkspaceFiles = new ObservableCollection<WorkspaceFile>();
        WorkspaceCommits = new ObservableCollection<WorkspaceCommit>();
        WorkspaceTags = new ObservableCollection<WorkspaceTag>();
        WorkspaceReleases = new ObservableCollection<WorkspaceRelease>();
        StreamEvents = new ObservableCollection<AgentStreamEvent>();
        SimulationQueue = new ObservableCollection<AgentStreamEvent>();
    }

    public string Id { get; }
    public string Name { get; }
    public string Description { get; }
    public string Owner { get; }
    // These are presentation-facing marks for the local catalog. They are deliberately
    // not treated as external brand registrations or source-of-truth project metadata.
    public string LogoPathData { get; set; } = "M4,4 H20 V20 H4 Z";
    public string PriorityTier { get; set; } = "TIER III";
    public string PriorityTierLabel => $"PRIORIDADE · {PriorityTier}";
    public string OpenAccessibleLabel => $"Abrir projeto {Name}";
    public ObservableCollection<string> Modules { get; }
    public ObservableCollection<ProjectTask> Tasks { get; }
    public ObservableCollection<AgentSession> ActiveSessions { get; }
    public ObservableCollection<ActivityEvent> Activity { get; }
    public ObservableCollection<DiscussionMessage> Discussions { get; }
    public ObservableCollection<DeliveryCandidate> Deliveries { get; }
    public ObservableCollection<QualityCheck> QualityChecks { get; }
    public ObservableCollection<WorkspaceFile> WorkspaceFiles { get; }
    public ObservableCollection<WorkspaceCommit> WorkspaceCommits { get; }
    public ObservableCollection<WorkspaceTag> WorkspaceTags { get; }
    public ObservableCollection<WorkspaceRelease> WorkspaceReleases { get; }
    public ObservableCollection<AgentStreamEvent> StreamEvents { get; }
    public ObservableCollection<AgentStreamEvent> SimulationQueue { get; }

    private WorkspaceFile? _selectedWorkspaceFile;
    private WorkspaceCommit? _selectedWorkspaceCommit;
    private WorkspaceTag? _selectedWorkspaceTag;
    private WorkspaceRelease? _selectedWorkspaceRelease;
    private AgentStreamEvent? _selectedStreamEvent;
    private ProjectTask? _selectedTask;
    private DeliveryCandidate? _selectedDelivery;
    private int _simulationStep;

    public ProjectStatus Status
    {
        get => _status;
        set
        {
            if (SetProperty(ref _status, value))
            {
                Raise(nameof(StatusLabel));
                Raise(nameof(StatusTone));
                Raise(nameof(IsOpen));
                Raise(nameof(LifecycleAccessibleLabel));
            }
        }
    }

    public int WorkspaceRevision
    {
        get => _workspaceRevision;
        set
        {
            if (SetProperty(ref _workspaceRevision, value))
            {
                Raise(nameof(WorkspaceRevisionLabel));
            }
        }
    }

    public int Generation
    {
        get => _generation;
        set => SetProperty(ref _generation, value);
    }

    public string StatusLabel => Status switch
    {
        ProjectStatus.Open => "ABERTO",
        ProjectStatus.Closing => "FECHANDO",
        ProjectStatus.Closed => "FECHADO",
        ProjectStatus.Reopening => "REABRINDO",
        _ => "DESCONHECIDO"
    };

    public string StatusTone => Status switch
    {
        ProjectStatus.Open => "open",
        ProjectStatus.Closed => "closed",
        _ => "transition"
    };

    public bool IsOpen => Status == ProjectStatus.Open;
    public string AccessLabel => IsOpen ? "Escrita local permitida" : "Leitura disponível · escrita bloqueada";
    public string LifecycleAccessibleLabel => IsOpen ? $"Fechar projeto {Name}" : $"Reabrir projeto {Name}";
    public string WorkspaceRevisionLabel => $"r{WorkspaceRevision}";
    public string SimulationProgressLabel => SimulationQueue.Count == 0
        ? $"{_simulationStep} eventos exibidos · fila concluída"
        : $"{_simulationStep} eventos exibidos · {SimulationQueue.Count} na fila manual";
    public string SimulationStateLabel => SimulationQueue.Count == 0 ? "SIMULAÇÃO CONCLUÍDA" : "PRÓXIMO EVENTO MANUAL";
    public string WorkspaceFileCountLabel => $"{WorkspaceFiles.Count} arquivos no manifesto local";
    public string WorkspaceVersioningLabel => $"{WorkspaceCommits.Count} commits · {WorkspaceTags.Count} tags · {WorkspaceReleases.Count} releases locais";
    public string WorkspaceSelectionLabel => SelectedWorkspaceFile is null
        ? "Selecione um arquivo para ver a descrição"
        : SelectedWorkspaceFile.Path;
    public string StreamSelectionLabel => SelectedStreamEvent is null
        ? "Selecione um evento para inspecionar a reação"
        : $"{SelectedStreamEvent.SequenceLabel} · {SelectedStreamEvent.Operation}";
    public int SimulationStep
    {
        get => _simulationStep;
        set
        {
            if (SetProperty(ref _simulationStep, value))
            {
                Raise(nameof(SimulationProgressLabel));
                Raise(nameof(SimulationStateLabel));
            }
        }
    }

    public WorkspaceFile? SelectedWorkspaceFile
    {
        get => _selectedWorkspaceFile;
        set
        {
            if (SetProperty(ref _selectedWorkspaceFile, value))
            {
                foreach (var file in WorkspaceFiles)
                {
                    file.IsSelected = ReferenceEquals(file, value);
                }

                Raise(nameof(WorkspaceSelectionLabel));
            }
        }
    }

    public WorkspaceCommit? SelectedWorkspaceCommit
    {
        get => _selectedWorkspaceCommit;
        set => SetProperty(ref _selectedWorkspaceCommit, value);
    }

    public WorkspaceTag? SelectedWorkspaceTag
    {
        get => _selectedWorkspaceTag;
        set => SetProperty(ref _selectedWorkspaceTag, value);
    }

    public WorkspaceRelease? SelectedWorkspaceRelease
    {
        get => _selectedWorkspaceRelease;
        set => SetProperty(ref _selectedWorkspaceRelease, value);
    }

    public AgentStreamEvent? SelectedStreamEvent
    {
        get => _selectedStreamEvent;
        set
        {
            if (SetProperty(ref _selectedStreamEvent, value))
            {
                foreach (var item in StreamEvents)
                {
                    item.IsSelected = ReferenceEquals(item, value);
                }

                Raise(nameof(StreamSelectionLabel));
            }
        }
    }

    public ProjectTask? SelectedTask
    {
        get => _selectedTask;
        set => SetProperty(ref _selectedTask, value);
    }

    public DeliveryCandidate? SelectedDelivery
    {
        get => _selectedDelivery;
        set
        {
            if (SetProperty(ref _selectedDelivery, value))
            {
                foreach (var delivery in Deliveries)
                {
                    delivery.IsSelected = ReferenceEquals(delivery, value);
                }

                Raise(nameof(SelectedDeliveryLabel));
            }
        }
    }

    public string SelectedDeliveryLabel => SelectedDelivery is null
        ? "Nenhuma entrega selecionada"
        : $"{SelectedDelivery.Id} · {SelectedDelivery.Summary} · {SelectedDelivery.StatusLabel}";
    public int OpenTaskCount => Tasks.Count(task => task.Status is not TaskStatus.Done and not TaskStatus.Cancelled);
    public int BlockedTaskCount => Tasks.Count(task => task.Status == TaskStatus.Blocked);
    public ProjectTask? NextActionableTask => Tasks.FirstOrDefault(task => task.Status == TaskStatus.Ready);
    public int ActiveAgentCount => ActiveSessions.Count(session => session.IsOnline);
    public int PendingDeliveryCount => Deliveries.Count(delivery => delivery.Status is not DeliveryStatus.Integrated and not DeliveryStatus.Rejected);
    public IEnumerable<ActivityEvent> RecentActivities => Activity.Take(4);
    public ActivityEvent? LatestActivity => Activity.FirstOrDefault();

    public void AddActivity(ActivityEvent activity)
    {
        Activity.Insert(0, activity);
        Raise(nameof(OpenTaskCount));
        Raise(nameof(BlockedTaskCount));
        Raise(nameof(NextActionableTask));
        Raise(nameof(ActiveAgentCount));
        Raise(nameof(PendingDeliveryCount));
    }

    public void AddStreamEvent(AgentStreamEvent streamEvent)
    {
        StreamEvents.Insert(0, streamEvent);
        SelectedStreamEvent = streamEvent;
        Raise(nameof(SimulationProgressLabel));
        Raise(nameof(SimulationStateLabel));
    }

    public void EnqueueSimulationEvent(AgentStreamEvent streamEvent) => SimulationQueue.Add(streamEvent);

    public void AdvanceSimulationStep()
    {
        SimulationStep++;
        Raise(nameof(SimulationProgressLabel));
        Raise(nameof(SimulationStateLabel));
    }

    public void RaiseForSimulation()
    {
        Raise(nameof(SimulationProgressLabel));
        Raise(nameof(SimulationStateLabel));
        Raise(nameof(WorkspaceVersioningLabel));
        Raise(nameof(WorkspaceFileCountLabel));
    }

    public void RefreshDerivedState()
    {
        Raise(nameof(OpenTaskCount));
        Raise(nameof(BlockedTaskCount));
        Raise(nameof(ActiveAgentCount));
        Raise(nameof(PendingDeliveryCount));
    }
}

public sealed class ProjectTask : ObservableObject
{
    private TaskStatus _status;
    private string? _claimOwner;

    public ProjectTask(string id, string title, string description, string area, string priority, TaskStatus status, string acceptance, string owner, string dependency)
    {
        Id = id;
        Title = title;
        Description = description;
        Area = area;
        Priority = priority;
        _status = status;
        Acceptance = acceptance;
        Owner = owner;
        Dependency = dependency;
    }

    public string Id { get; }
    public string Title { get; }
    public string Description { get; }
    public string Area { get; }
    public string Priority { get; }
    public string Acceptance { get; }
    public string Owner { get; }
    public string Dependency { get; }
    public string AccessibleLabel => $"Abrir tarefa {Id} · {Title} · {StatusLabel}";

    public TaskStatus Status
    {
        get => _status;
        set
        {
            if (SetProperty(ref _status, value))
            {
                Raise(nameof(StatusLabel));
                Raise(nameof(StatusTone));
                Raise(nameof(IsClaimable));
            }
        }
    }

    public string? ClaimOwner
    {
        get => _claimOwner;
        set
        {
            if (SetProperty(ref _claimOwner, value))
            {
                Raise(nameof(ClaimLabel));
            }
        }
    }

    public bool IsClaimable => Status == TaskStatus.Ready;
    public string ClaimLabel => !string.IsNullOrWhiteSpace(ClaimOwner)
        ? $"Reservada por {ClaimOwner}"
        : Status switch
        {
            TaskStatus.InProgress => "Em andamento",
            TaskStatus.InReview => "Aguardando revisão",
            TaskStatus.Blocked => "Bloqueada por dependência",
            TaskStatus.Done => "Concluída",
            TaskStatus.Cancelled => "Cancelada",
            _ => "Livre"
        };

    public string StatusLabel => Status switch
    {
        TaskStatus.Ready => "PRONTA",
        TaskStatus.Reserved => "RESERVADA",
        TaskStatus.InProgress => "EM ANDAMENTO",
        TaskStatus.InReview => "EM REVISÃO",
        TaskStatus.Blocked => "BLOQUEADA",
        TaskStatus.Done => "CONCLUÍDA",
        TaskStatus.Cancelled => "CANCELADA",
        _ => "—"
    };

    public string StatusTone => Status switch
    {
        TaskStatus.Ready => "ready",
        TaskStatus.Blocked => "blocked",
        TaskStatus.Done => "done",
        TaskStatus.InReview => "review",
        _ => "active"
    };

    public string DependencyLabel => string.IsNullOrWhiteSpace(Dependency) ? "Sem dependência declarada" : $"Depende de {Dependency}";
}

public sealed class AgentSession : ObservableObject
{
    private bool _isOnline;
    private string _activity;

    public AgentSession(string displayName, string provider, string task, string area, bool isOnline, string activity)
    {
        DisplayName = displayName;
        Provider = provider;
        Task = task;
        Area = area;
        _isOnline = isOnline;
        _activity = activity;
    }

    public string DisplayName { get; }
    public string Provider { get; }
    public string Task { get; }
    public string Area { get; }
    public string Activity
    {
        get => _activity;
        set => SetProperty(ref _activity, value);
    }

    public bool IsOnline
    {
        get => _isOnline;
        set
        {
            if (SetProperty(ref _isOnline, value))
            {
                Raise(nameof(ConnectionLabel));
            }
        }
    }

    public string ConnectionLabel => IsOnline ? "Ativa · simulação local" : "Pendente · offline local";
    public string ConnectionDetail => IsOnline ? "fixture local · sem conexão externa" : "sem resposta externa; pendência preservada";
    public string ConnectionTone => IsOnline ? "active" : "offline";
    public string Initials
    {
        get
        {
            var identity = DisplayName.Split('·')[0].Trim();
            return string.Concat(identity.Split(' ', StringSplitOptions.RemoveEmptyEntries).Take(2).Select(part => part[0])).ToUpperInvariant();
        }
    }
}

public sealed class ActivityEvent
{
    public ActivityEvent(string time, string actor, string type, string summary, string tone = "neutral")
    {
        Time = time;
        Actor = actor;
        Type = type;
        Summary = summary;
        Tone = tone;
    }

    public string Time { get; }
    public string Actor { get; }
    public string Type { get; }
    public string Summary { get; }
    public string Tone { get; }
    public string MetaLabel => $"{Actor} · {Time}";
}

public sealed class DiscussionMessage
{
    public DiscussionMessage(string author, string senderType, string time, string body, string messageType, bool isPending = false, IEnumerable<WorkspaceReference>? references = null)
    {
        Author = author;
        SenderType = senderType;
        Time = time;
        Body = body;
        MessageType = messageType;
        IsPending = isPending;
        References = new ObservableCollection<WorkspaceReference>(references ?? Array.Empty<WorkspaceReference>());
    }

    public string Author { get; }
    public string SenderType { get; }
    public string Time { get; }
    public string Body { get; }
    public string MessageType { get; }
    public bool IsPending { get; }
    public ObservableCollection<WorkspaceReference> References { get; }
    public string Initials
    {
        get
        {
            var identity = Author.Split('·')[0].Trim();
            return string.Concat(identity.Split(' ', StringSplitOptions.RemoveEmptyEntries).Take(2).Select(part => part[0])).ToUpperInvariant();
        }
    }
}

public enum DeliveryStatus
{
    Draft,
    Testing,
    InReview,
    Approved,
    Rejected,
    Integrated
}

public sealed class DeliveryCandidate : ObservableObject
{
    private DeliveryStatus _status;
    private bool _isSelected;

    public DeliveryCandidate(string id, string summary, string risk, string hash, DeliveryStatus status, int evidenceCount, string reviewer)
    {
        Id = id;
        Summary = summary;
        Risk = risk;
        Hash = hash;
        _status = status;
        EvidenceCount = evidenceCount;
        Reviewer = reviewer;
    }

    public string Id { get; }
    public string Summary { get; }
    public string Risk { get; }
    public string Hash { get; }
    public int EvidenceCount { get; }
    public string Reviewer { get; }

    public bool IsSelected
    {
        get => _isSelected;
        set => SetProperty(ref _isSelected, value);
    }

    public DeliveryStatus Status
    {
        get => _status;
        set
        {
            if (SetProperty(ref _status, value))
            {
                Raise(nameof(StatusLabel));
                Raise(nameof(StatusTone));
                Raise(nameof(CanApprove));
                Raise(nameof(CanIntegrate));
                Raise(nameof(GateLabel));
            }
        }
    }

    public string StatusLabel => Status switch
    {
        DeliveryStatus.Draft => "RASCUNHO",
        DeliveryStatus.Testing => "TESTANDO",
        DeliveryStatus.InReview => "EM REVISÃO",
        DeliveryStatus.Approved => "APROVADA · LOCAL",
        DeliveryStatus.Rejected => "REPROVADA",
        DeliveryStatus.Integrated => "INTEGRAÇÃO LOCAL · NÃO CONFIRMADA",
        _ => "—"
    };

    public string StatusTone => Status switch
    {
        DeliveryStatus.Approved or DeliveryStatus.Integrated => "done",
        DeliveryStatus.Rejected => "blocked",
        _ => "review"
    };

    public bool CanApprove => Status == DeliveryStatus.InReview;
    public bool CanIntegrate => Status == DeliveryStatus.Approved;
    public string GateLabel => Status switch
    {
        DeliveryStatus.InReview => "Aguardando revisor independente",
        DeliveryStatus.Approved => "Aprovada localmente · Git não conectado",
        DeliveryStatus.Integrated => "Marcada localmente · publicação continua separada",
        DeliveryStatus.Draft => "Rascunho local · evidências ainda não verificadas",
        _ => "Gate não disponível"
    };
}

public sealed class QualityCheck
{
    public QualityCheck(string name, string status, string detail, string time, string tone)
    {
        Name = name;
        Status = status;
        Detail = detail;
        Time = time;
        Tone = tone;
    }

    public string Name { get; }
    public string Status { get; }
    public string Detail { get; }
    public string Time { get; }
    public string Tone { get; }
}

public sealed class TeamMember
{
    public TeamMember(string name, string area, string role, string status, string focus, bool isActive)
    {
        Name = name;
        Area = area;
        Role = role;
        Status = status;
        Focus = focus;
        IsActive = isActive;
    }

    public string Name { get; }
    public string Area { get; }
    public string Role { get; }
    public string Status { get; }
    public string Focus { get; }
    public bool IsActive { get; }
    public string StatusTone => IsActive ? "active" : "offline";
    public string Initials => string.Concat(Name.Split(' ', StringSplitOptions.RemoveEmptyEntries).Take(2).Select(part => part[0])).ToUpperInvariant();
}
