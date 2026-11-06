# Build, publicação e instalador

## Ferramentas instaladas no disco D:

- .NET SDK 8.0.427: `D:\projetos\Central\tools\dotnet`
- Inno Setup 6.7.4: `D:\projetos\Central\tools\inno-setup`
- Instaladores baixados: `D:\projetos\Central\tools\installers`

## Comando único

```powershell
& 'D:\projetos\Central\ops\scripts\Build-Central.ps1'
```

O script restaura, compila, testa, publica self-contained x64 e chama `ISCC.exe`. O runtime .NET Desktop acompanha `Central.exe`; a máquina do usuário não precisa ter o .NET instalado globalmente.
