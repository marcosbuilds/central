using System.Globalization;
using System.Windows.Data;

namespace Central.Desktop;

public sealed class BooleanAndConverter : IMultiValueConverter
{
    public object Convert(object[] values, Type targetType, object? parameter, CultureInfo culture)
        => values.Length > 0 && values.All(value => value is bool enabled && enabled);

    public object[] ConvertBack(object value, Type[] targetTypes, object? parameter, CultureInfo culture)
        => throw new NotSupportedException();
}
