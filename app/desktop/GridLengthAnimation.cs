using System.Windows;
using System.Windows.Media.Animation;

namespace Central.Desktop;

/// <summary>
/// WPF has no built-in interpolation for GridLength. This small timeline keeps
/// the rail collapse animation in the compositor-friendly layout surface without
/// adding a third-party motion dependency.
/// </summary>
public sealed class GridLengthAnimation : AnimationTimeline
{
    public static readonly DependencyProperty FromProperty = DependencyProperty.Register(
        nameof(From), typeof(GridLength), typeof(GridLengthAnimation), new PropertyMetadata(new GridLength(0)));

    public static readonly DependencyProperty ToProperty = DependencyProperty.Register(
        nameof(To), typeof(GridLength), typeof(GridLengthAnimation), new PropertyMetadata(new GridLength(0)));

    public GridLength From
    {
        get => (GridLength)GetValue(FromProperty);
        set => SetValue(FromProperty, value);
    }

    public GridLength To
    {
        get => (GridLength)GetValue(ToProperty);
        set => SetValue(ToProperty, value);
    }

    public override Type TargetPropertyType => typeof(GridLength);

    protected override Freezable CreateInstanceCore() => new GridLengthAnimation();

    public override object GetCurrentValue(object defaultOriginValue, object defaultDestinationValue, AnimationClock animationClock)
    {
        var from = From.IsAbsolute ? From.Value : ((GridLength)defaultOriginValue).Value;
        var to = To.IsAbsolute ? To.Value : ((GridLength)defaultDestinationValue).Value;
        var progress = animationClock.CurrentProgress ?? 0;
        return new GridLength(from + ((to - from) * progress), GridUnitType.Pixel);
    }
}
