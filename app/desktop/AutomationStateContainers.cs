using System.Collections.Generic;
using System.Windows;
using System.Windows.Automation;
using System.Windows.Automation.Peers;
using System.Windows.Controls;

namespace Central.Desktop;

/// <summary>
/// Container used for mutually exclusive visual states. WPF can keep peers for
/// collapsed descendants in the UI Automation tree; the peer below removes the
/// inactive branch instead of making assistive technology read two states at once.
/// </summary>
public class AutomationStateGrid : Grid
{
    protected override AutomationPeer OnCreateAutomationPeer() => new StateContainerAutomationPeer(this);
}

/// <summary>Border variant for an empty/success state that is swapped by code.</summary>
public class AutomationStateBorder : Border
{
    protected override AutomationPeer OnCreateAutomationPeer() => new StateContainerAutomationPeer(this);
}

internal sealed class StateContainerAutomationPeer : FrameworkElementAutomationPeer
{
    private readonly FrameworkElement _owner;

    public StateContainerAutomationPeer(FrameworkElement owner)
        : base(owner)
    {
        _owner = owner;
    }

    protected override List<AutomationPeer>? GetChildrenCore()
        => _owner.Visibility == Visibility.Visible ? base.GetChildrenCore() : new List<AutomationPeer>();

    protected override bool IsControlElementCore() => _owner.Visibility == Visibility.Visible;

    protected override bool IsContentElementCore() => _owner.Visibility == Visibility.Visible;

    protected override AutomationControlType GetAutomationControlTypeCore()
        => AutomationControlType.Pane;
}

/// <summary>
/// A WPF Border does not expose a dialog control type by itself. This small
/// project-owned peer keeps the centered settings surface discoverable as one
/// dialog in UI Automation, instead of relying only on an attached XAML flag.
/// </summary>
public sealed class AutomationDialogBorder : Border
{
    protected override AutomationPeer OnCreateAutomationPeer() => new DialogAutomationPeer(this);
}

internal sealed class DialogAutomationPeer : FrameworkElementAutomationPeer
{
    public DialogAutomationPeer(FrameworkElement owner)
        : base(owner)
    {
    }

    protected override AutomationControlType GetAutomationControlTypeCore()
        => AutomationControlType.Window;

    protected override string GetClassNameCore() => "Dialog";

    protected override bool IsControlElementCore() => true;

    protected override bool IsContentElementCore() => true;
}
