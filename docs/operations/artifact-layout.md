# Local artifact layout

Status: implemented local organization; this document does not represent a
production deployment or a release approval.

Generated delivery material is ignored by Git and is organized by the system
that consumes it:

```text
artifacts/
├── acl/
│   ├── deploy/YYYY-MM-DD/deploys/<commit>/
│   └── archive/YYYY-MM-DD/legacy-layout/<legacy-package>/
├── netlify/deploy/YYYY-MM-DD/deploys/<commit>/
├── netlify/archive/YYYY-MM-DD/legacy-layout/<legacy-package>/
├── desktop/{delivery,installers,preview,publish}/YYYY-MM-DD/
├── qa/{screenshots,test-results}/YYYY-MM-DD/
└── (bytecode quarantine lives under data/runtime/quarantine/)
```

Browser profiles, cookies, tokens, local logs, and other diagnostic state do
not belong under `artifacts/`. If they must be retained temporarily for a
local investigation, keep them under an ignored `data/runtime/quarantine/`
directory and never package or publish them.

`artifacts/acl/deploy/YYYY-MM-DD/deploys/<commit>/` is reserved for sanitized
backend packages. The
runtime contract keeps `main.py` at the package root and excludes the Netlify
frontend, local state, databases, secrets, logs, and Python bytecode.

`artifacts/netlify/deploy/YYYY-MM-DD/deploys/<commit>/` contains static
Netlify packages only. A historical archive may retain a mixed package for
auditability, but its name and location must make clear that it is not a valid
ACL deployment.

The same date-and-purpose convention is used for desktop installers, preview
builds, published binaries, screenshots, and test results. These directories
are local evidence and are never added with a broad `git add`.

Legacy generated folders are not kept under a generic `legacy/generated`
bucket. Historical ACL and Netlify material is placed in the matching
consumer's dated `archive/YYYY-MM-DD/legacy-layout/` directory; Python
bytecode and browser state stay in `data/runtime/quarantine/`.

Create a new sanitized ACL package with:

```powershell
powershell -ExecutionPolicy Bypass -File ops/scripts/Build-PeaceAclPackage.ps1
```

The script runs on Windows PowerShell 5.1 and PowerShell 7, requires a clean
working tree and the checked-out `HEAD`, copies only tracked backend files and
runtime artwork, refuses to overwrite an existing commit/date directory, and
excludes `bot/site`, secrets, databases, and bytecode. It writes a SHA-256
manifest inside the package. It does not upload or restart a provider;
production publication remains a separate authorized operation.
