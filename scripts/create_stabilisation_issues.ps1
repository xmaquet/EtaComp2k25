# Crée le milestone et les issues de stabilisation v1.0.1 sur GitHub.
# Prérequis : GitHub CLI installé et authentifié (gh auth login)
#   https://cli.github.com/
#
# Usage :
#   .\scripts\create_stabilisation_issues.ps1
#   .\scripts\create_stabilisation_issues.ps1 -Repo "xmaquet/EtaComp2k25" -DryRun

param(
    [string]$Repo = "xmaquet/EtaComp2k25",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$IssuesDir = Join-Path $Root "docs\issues"
$ManifestPath = Join-Path $IssuesDir "manifest.json"

function Find-Gh {
    $cmd = Get-Command gh -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $paths = @(
        "${env:ProgramFiles}\GitHub CLI\gh.exe",
        "${env:LocalAppData}\Programs\GitHub CLI\gh.exe"
    )
    foreach ($p in $paths) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

$Gh = Find-Gh
if (-not $Gh -and -not $DryRun) {
    Write-Error @"
GitHub CLI (gh) introuvable.

Installez-le puis authentifiez-vous :
  https://cli.github.com/
  gh auth login

Puis exécutez :
  .\scripts\create_stabilisation_issues.ps1

Les corps d'issues sont prêts dans docs/issues/*.md
"@
}

if (-not (Test-Path $ManifestPath)) {
    Write-Error "Manifest introuvable : $ManifestPath"
}

$manifest = Get-Content $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$milestoneTitle = $manifest.milestone
$milestoneDesc = $manifest.milestone_description

Write-Host "Dépôt cible : $Repo"
Write-Host "Milestone   : $milestoneTitle"
if ($DryRun) { Write-Host "[DRY RUN] Aucune création réelle." -ForegroundColor Yellow }

# Labels
foreach ($label in $manifest.labels) {
    if ($DryRun) { Write-Host "  [label] $label"; continue }
    $null = & $Gh label create $label --repo $Repo 2>&1
}

# Milestone
$milestoneNumber = $null
if ($DryRun) {
    Write-Host "  [milestone] $milestoneTitle"
} else {
    $existing = & $Gh api "repos/$Repo/milestones" --jq ".[] | select(.title==`"$milestoneTitle`") | .number" 2>$null
    if ($existing) {
        $milestoneNumber = [int]$existing
        Write-Host "Milestone existant #$milestoneNumber : $milestoneTitle"
    } else {
        $created = & $Gh api -X POST "repos/$Repo/milestones" -f title=$milestoneTitle -f description=$milestoneDesc -f state=open | ConvertFrom-Json
        $milestoneNumber = $created.number
        Write-Host "Milestone créé #$milestoneNumber : $milestoneTitle"
    }
}

$createdIssues = @()
foreach ($issue in $manifest.issues) {
    $bodyPath = Join-Path $IssuesDir $issue.body_file
    if (-not (Test-Path $bodyPath)) {
        Write-Warning "Corps manquant : $($issue.body_file)"
        continue
    }
    $body = Get-Content $bodyPath -Raw -Encoding UTF8
    $labels = ($issue.labels -join ",")

    if ($DryRun) {
        Write-Host "  [issue $($issue.id)] $($issue.title)"
        continue
    }

    $args = @(
        "issue", "create",
        "--repo", $Repo,
        "--title", $issue.title,
        "--body-file", $bodyPath,
        "--label", $labels
    )
    if ($milestoneNumber) {
        $args += @("--milestone", $milestoneTitle)
    }

    $url = & $Gh @args
    $num = if ($url -match '/issues/(\d+)') { $Matches[1] } else { "?" }
    Write-Host "  #$num ISSUE-$($issue.id) : $($issue.title)"
    $createdIssues += [pscustomobject]@{ DocId = $issue.id; Number = $num; Url = $url; Title = $issue.title }
}

if (-not $DryRun -and $createdIssues.Count -gt 0) {
    Write-Host ""
    Write-Host "=== Issues créées ===" -ForegroundColor Green
    $createdIssues | Format-Table -AutoSize
    Write-Host "Mettez à jour docs/ROADMAP_v1.0.1.md avec les numéros GitHub si besoin."
}
