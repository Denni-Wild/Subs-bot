# MCP Task Management System Setup Script
# Run as Administrator

Write-Host "Setting up MCP Task Management System..." -ForegroundColor Green

# Create data directories
$directories = @(
    "D:/PY/MCP/calendar-data",
    "D:/PY/MCP/notifications-data", 
    "D:/PY/MCP/time-tracking-data",
    "D:/PY/MCP/backup-data"
)

Write-Host "Creating data directories..." -ForegroundColor Yellow
foreach ($dir in $directories) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  Created: $dir" -ForegroundColor Green
    } else {
        Write-Host "  Exists: $dir" -ForegroundColor Blue
    }
}

# Copy updated config
Write-Host "Updating MCP configuration..." -ForegroundColor Yellow
$sourceConfig = "mcp-config-updated.json"
$targetConfig = "$env:USERPROFILE\.cursor\mcp.json"

if (Test-Path $sourceConfig) {
    try {
        Copy-Item $sourceConfig $targetConfig -Force
        Write-Host "  Config updated: $targetConfig" -ForegroundColor Green
    }
    catch {
        Write-Host "  Config copy failed: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  Config file not found: $sourceConfig" -ForegroundColor Red
}

Write-Host "`nSetup completed!" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Restart Cursor" -ForegroundColor White
Write-Host "  2. Check MCP servers in panel" -ForegroundColor White
Write-Host "  3. Start using shrimp-task-manager" -ForegroundColor White

Write-Host "`nAvailable servers:" -ForegroundColor Cyan
Write-Host "  * deltatask - basic task management" -ForegroundColor White
Write-Host "  * shrimp-task-manager - intelligent orchestration" -ForegroundColor White
Write-Host "  * hpkv-memory-server - semantic memory" -ForegroundColor White
Write-Host "  * memory - knowledge graph" -ForegroundColor White
Write-Host "  * mcp-calendar - time planning" -ForegroundColor White
Write-Host "  * mcp-notifications - alerts" -ForegroundColor White
Write-Host "  * mcp-time-tracker - time tracking" -ForegroundColor White
Write-Host "  * mcp-git - Git integration" -ForegroundColor White
Write-Host "  * mcp-filesystem - file storage" -ForegroundColor White
Write-Host "  * mcp-backup - backup system" -ForegroundColor White 