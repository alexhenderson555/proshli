param(
  [string]$OutputDir = ".\\backups"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $OutputDir)) {
  New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$file = Join-Path $OutputDir "otklik-$timestamp.sql"

docker compose -f "docker-compose.prod.yml" exec -T postgres pg_dump -U $env:POSTGRES_USER $env:POSTGRES_DB > $file

Write-Host "Backup saved to $file"
