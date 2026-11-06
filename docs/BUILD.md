# Build, publishing, and installer

The repository keeps the build tools and scripts separate from source code.
Use the versions available in the checkout or in CI; do not publish local
machine paths or installer caches in documentation.

## One-command build

From the repository root in PowerShell:

```powershell
& .\ops\scripts\Build-Central.ps1
```

The script restores, builds, tests, publishes self-contained x64 output, and
invokes Inno Setup when the required tools are available. The .NET Desktop
runtime ships with the application, so the user's machine does not need a
global .NET installation.

## Reproducibility

- Keep tool downloads and generated installers outside the committed source
  tree or in ignored folders.
- Use repository-relative paths in scripts and Pull Requests.
- Record the command, commit, platform, and result when reporting a build.
- Do not include credentials, provider identifiers, local paths, or runtime
  data in a build log or public issue.

## Output boundary

Build and publish output is generated evidence, not source. Review the staged
file list before every commit and keep `artifacts/`, caches, and local package
stores out of Git.
