param(
  [Parameter(Mandatory = $true)]
  [string]$BackupFile
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupFile)) {
  throw "Backup file not found: $BackupFile"
}

Get-Content $BackupFile | docker compose -f "docker-compose.prod.yml" exec -T postgres psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB

Write-Host "Restore completed from $BackupFile"
