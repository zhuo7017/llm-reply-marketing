<#
.SYNOPSIS
  Build, verify and publish the research index to GitHub.

.DESCRIPTION
  Runs the build, the integrity gate, then commits and pushes to GitHub.
  If -SiteUrl is supplied it is written to data/site.json first, so canonical
  links, the sitemap and llms.txt all point at the real domain.

  This script never stores a credential. Authentication is delegated to git:
  Git Credential Manager prompts once, GitHub CLI (`gh auth login`) or a
  personal access token in the remote URL also work.

.EXAMPLE
  .\publish.ps1 -GitHubUser zhuo7017 -SiteUrl https://zhuo7017.github.io/llm-reply-marketing

.EXAMPLE
  .\publish.ps1 -Message "Add 2026 publications"
#>
[CmdletBinding()]
param(
    [string]$GitHubUser = '',
    [string]$RepoName = 'llm-reply-marketing',
    [string]$SiteUrl = '',
    [string]$Message = 'Rebuild research index',
    [switch]$SkipPush
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $root
try {
    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $python) { throw 'python not found on PATH' }

    # 1. point the site at its real address
    if ($SiteUrl) {
        $cfgPath = Join-Path $root 'data/site.json'
        $cfg = Get-Content $cfgPath -Raw -Encoding utf8 | ConvertFrom-Json
        $cfg.site_url = $SiteUrl.TrimEnd('/')
        if ($GitHubUser) {
            $cfg | Add-Member -NotePropertyName github_user -NotePropertyValue $GitHubUser -Force
            $cfg.author | Add-Member -NotePropertyName github_url -NotePropertyValue "https://github.com/$GitHubUser" -Force
        }
        $cfg | ConvertTo-Json -Depth 8 | Set-Content $cfgPath -Encoding utf8
        Write-Host "site_url = $($cfg.site_url)"
    }

    # 2. build + verify
    & $python scripts/build.py
    if ($LASTEXITCODE -ne 0) { throw 'build failed' }
    & $python scripts/check.py
    if ($LASTEXITCODE -ne 0) { throw 'integrity check failed — fix the errors above before publishing' }

    # 3. git
    if (-not (Test-Path (Join-Path $root '.git'))) {
        git init -b main | Out-Null
    }
    if (-not (git config user.name)) {
        if (-not $GitHubUser) { throw 'set -GitHubUser or run: git config --global user.name "Your Name"' }
        git config user.name $GitHubUser
        git config user.email "$GitHubUser@users.noreply.github.com"
    }
    git add -A
    if (git status --porcelain) {
        git commit -m $Message | Out-Null
    } else {
        Write-Host 'nothing to commit'
    }

    if ($SkipPush) { Write-Host 'built and committed locally (-SkipPush)'; return }

    $remote = "https://github.com/$GitHubUser/$RepoName.git"
    if ($GitHubUser -and -not (git remote get-url origin 2>$null)) {
        git remote add origin $remote
    }
    Write-Host "pushing to $remote"
    git push -u origin main
    if ($LASTEXITCODE -ne 0) { throw 'push failed (auth or repository missing)' }

    if ($SiteUrl) { Write-Host "Live (after Pages finishes): $SiteUrl" }
}
finally {
    Pop-Location
}
