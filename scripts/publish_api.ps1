<#
.SYNOPSIS
    Publish the working tree to GitHub through the REST API.

.DESCRIPTION
    Some networks answer api.github.com but silently drop github.com:443, so
    `git push` fails with "Failed to connect to github.com port 443". This
    script uploads every git-tracked file as a blob, builds one tree that is a
    complete snapshot of the repository, commits it on top of the current head
    and moves main. Nothing is written to disk and no credential is echoed.

    The token is taken from $env:GITHUB_TOKEN when set, otherwise from Git
    Credential Manager, which must already hold a credential for github.com
    (`git push` once from a network where github.com is reachable, or run
    `git credential-manager get` and finish the browser flow).

.EXAMPLE
    pwsh -File scripts/publish_api.ps1
    pwsh -File scripts/publish_api.ps1 -Message "Fix plural forms"
#>
param(
    [string]$Owner = 'zhuo7017',
    [string]$Repo = 'llm-reply-marketing',
    [string]$Branch = 'main',
    [string]$Message = 'Update research index',
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Get-GitHubToken {
    if ($env:GITHUB_TOKEN) { return $env:GITHUB_TOKEN.Trim() }
    $gcm = 'F:\Program Files\Git\mingw64\bin\git-credential-manager.exe'
    if (-not (Test-Path $gcm)) {
        throw 'Git Credential Manager not found. Set $env:GITHUB_TOKEN instead.'
    }
    $raw = "protocol=https`nhost=github.com`n`n" | & $gcm get 2>$null
    $tok = ($raw | Where-Object { $_ -like 'password=*' }) -replace '^password=', ''
    if (-not $tok) { throw 'No GitHub credential available. Run git push once on an unblocked network, or set $env:GITHUB_TOKEN.' }
    return $tok.Trim()
}

$token = Get-GitHubToken
$headers = @{
    Authorization          = "token $token"
    'User-Agent'           = 'llm-reply-marketing-publisher'
    Accept                 = 'application/vnd.github+json'
}
$api = "https://api.github.com/repos/$Owner/$Repo"

$files = @(git ls-files)
if ($files.Count -eq 0) { throw 'No tracked files. Run from inside the repository.' }
Write-Host "publishing $($files.Count) files to $Owner/$Repo@$Branch"

if ($DryRun) { $files | ForEach-Object { "  $_" }; return }

$tree = @()
foreach ($f in $files) {
    $bytes = [IO.File]::ReadAllBytes((Resolve-Path -Path $f).ProviderPath)
    $body = @{ content = [Convert]::ToBase64String($bytes); encoding = 'base64' } |
        ConvertTo-Json -Compress
    $blob = Invoke-RestMethod -Method Post -Uri "$api/git/blobs" -Headers $headers `
        -Body $body -ContentType 'application/json' -TimeoutSec 60
    $tree += @{ path = $f; mode = '100644'; type = 'blob'; sha = $blob.sha }
}

$newTree = Invoke-RestMethod -Method Post -Uri "$api/git/trees" -Headers $headers `
    -Body (@{ tree = $tree } | ConvertTo-Json -Depth 6 -Compress) `
    -ContentType 'application/json' -TimeoutSec 60

# A brand new repository has no ref yet: create the first commit without parents.
$parents = @()
try {
    $head = Invoke-RestMethod -Uri "$api/git/ref/heads/$Branch" -Headers $headers -TimeoutSec 30
    $parents = @($head.object.sha)
} catch {
    Write-Host "no ref yet for $Branch - creating the initial commit"
}

$commitBody = @{ message = $Message; tree = $newTree.sha; parents = $parents } |
    ConvertTo-Json -Depth 5 -Compress
$commit = Invoke-RestMethod -Method Post -Uri "$api/git/commits" -Headers $headers `
    -Body $commitBody -ContentType 'application/json' -TimeoutSec 60

if ($parents.Count -eq 0) {
    Invoke-RestMethod -Method Post -Uri "$api/git/refs" -Headers $headers `
        -Body (@{ ref = "refs/heads/$Branch"; sha = $commit.sha } | ConvertTo-Json -Compress) `
        -ContentType 'application/json' -TimeoutSec 60 | Out-Null
} else {
    Invoke-RestMethod -Method Patch -Uri "$api/git/refs/heads/$Branch" -Headers $headers `
        -Body (@{ sha = $commit.sha; force = $false } | ConvertTo-Json -Compress) `
        -ContentType 'application/json' -TimeoutSec 60 | Out-Null
}

Write-Host "published commit $($commit.sha.Substring(0, 8)) - $Message"
Write-Host "pages workflow will rebuild: https://github.com/$Owner/$Repo/actions"
