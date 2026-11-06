# Build, publishing, and installer

## Tools installed on the D: drive

- .NET SDK 8.0.427: `D:\projetos\Central\tools\dotnet`
- Inno Setup 6.7.4: `D:\projetos\Central\tools\inno-setup`
- Downloaded installers: `D:\projetos\Central\tools\installers`

## One-command build

```powershell
& 'D:\projetos\Central\ops\scripts\Build-Central.ps1'
```

The script restores, builds, tests, publishes self-contained x64 output, and
calls `ISCC.exe`. The .NET Desktop runtime ships with `Central.exe`, so the
user's machine does not need a global .NET installation.
