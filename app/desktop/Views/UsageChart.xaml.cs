using System.Windows;
using System.Windows.Controls;
using System.Windows.Media.Animation;

namespace Central.Desktop.Views;

public partial class UsageChart : UserControl
{
    private bool _reduceMotion;

    public UsageChart()
    {
        InitializeComponent();
        Loaded += UsageChart_Loaded;
    }

    public string SelectedRange { get; private set; } = "1 dia";

    public void SetRange(string range)
    {
        SelectedRange = range;
        RangeMessage.Text = $"Nenhum gateway conectado para {range}";

        if (!_reduceMotion && IsLoaded)
        {
            var fade = new DoubleAnimation(0.72, 1, new Duration(TimeSpan.FromMilliseconds(160)))
            {
                EasingFunction = new QuadraticEase()
            };
            EmptyStateBorder.BeginAnimation(OpacityProperty, fade);
        }
    }

    public void SetReducedMotion(bool reducedMotion)
    {
        _reduceMotion = reducedMotion;
        if (reducedMotion)
        {
            EmptyStateBorder.BeginAnimation(OpacityProperty, null);
            EmptyStateBorder.Opacity = 1;
        }
    }

    private void UsageChart_Loaded(object sender, RoutedEventArgs e)
    {
        if (_reduceMotion)
        {
            return;
        }

        EmptyStateBorder.Opacity = 0;
        var fade = new DoubleAnimation(0, 1, new Duration(TimeSpan.FromMilliseconds(180)))
        {
            EasingFunction = new QuadraticEase()
        };
        EmptyStateBorder.BeginAnimation(OpacityProperty, fade);
    }
}
