namespace Central.Core.Coordination;

public static class ResourcePath
{
    private const char Separator = '\\';

    public static string Normalize(string? value)
    {
        if (value is null)
        {
            throw new ArgumentNullException(nameof(value));
        }

        var candidate = value.Trim().Replace('/', Separator);
        if (candidate.Length == 0)
        {
            return string.Empty;
        }

        if (candidate.StartsWith(Separator) ||
            candidate.StartsWith("\\\\", StringComparison.Ordinal) ||
            (candidate.Length >= 2 && candidate[1] == ':'))
        {
            throw new ArgumentException("O recurso deve ser um caminho lógico relativo ao projeto.", nameof(value));
        }

        var segments = new List<string>();
        foreach (var segment in candidate.Split(Separator, StringSplitOptions.RemoveEmptyEntries))
        {
            if (segment == ".")
            {
                continue;
            }

            if (segment == "..")
            {
                throw new ArgumentException("O caminho do recurso não pode sair da raiz do projeto.", nameof(value));
            }

            segments.Add(segment);
        }

        return string.Join(Separator, segments).ToLowerInvariant();
    }

    public static bool Overlaps(string left, string right)
    {
        var normalizedLeft = Normalize(left);
        var normalizedRight = Normalize(right);

        if (normalizedLeft.Length == 0 || normalizedRight.Length == 0)
        {
            return true;
        }

        return string.Equals(normalizedLeft, normalizedRight, StringComparison.OrdinalIgnoreCase)
            || normalizedLeft.StartsWith(normalizedRight + Separator, StringComparison.OrdinalIgnoreCase)
            || normalizedRight.StartsWith(normalizedLeft + Separator, StringComparison.OrdinalIgnoreCase);
    }
}
