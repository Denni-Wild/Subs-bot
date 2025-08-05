#!/usr/bin/env powershell
<#
.SYNOPSIS
    PowerShell profile setup to prevent PSReadLine errors
    
.DESCRIPTION
    This script configures PowerShell profile to fix PSReadLine errors
    and improve console experience
#>

# Check if profile exists
$profilePath = $PROFILE.CurrentUserAllHosts
$profileDir = Split-Path $profilePath -Parent

# Create profile directory if it doesn't exist
if (!(Test-Path $profileDir)) {
    New-Item -ItemType Directory -Path $profileDir -Force
    Write-Host "Profile directory created: $profileDir"
}

# Profile content
$profileContent = @'
# PSReadLine settings to prevent errors
if (Get-Module PSReadLine) {
    # Disable problematic features
    Set-PSReadLineOption -PredictionSource None
    Set-PSReadLineOption -PredictionViewStyle ListView
    Set-PSReadLineOption -BellStyle None
    
    # Stability settings
    Set-PSReadLineOption -EditMode Windows
    Set-PSReadLineOption -HistoryNoDuplicates
    Set-PSReadLineOption -MaximumHistoryCount 1000
    
    # Disable auto-completion that can cause errors
    Set-PSReadLineOption -CompletionQueryItems 100
}

# Python project settings
function Set-PythonEnv {
    param([string]$Path = ".")
    if (Test-Path "$Path\.venv\Scripts\Activate.ps1") {
        & "$Path\.venv\Scripts\Activate.ps1"
        Write-Host "Python virtual environment activated" -ForegroundColor Green
    } else {
        Write-Host "Virtual environment not found in $Path" -ForegroundColor Red
    }
}

# Quick file search function
function Find-File {
    param([string]$Pattern, [string]$Path = ".")
    Get-ChildItem -Path $Path -Recurse -Include $Pattern | Select-Object Name, FullName, LastWriteTime
}

# Error search in logs function
function Find-Errors {
    param([string]$Path = ".", [int]$Minutes = 60)
    $files = Get-ChildItem -Path $Path -Recurse -Include "*.log" | Where-Object { $_.LastWriteTime -gt (Get-Date).AddMinutes(-$Minutes) }
    foreach ($file in $files) {
        Write-Host "=== $($file.Name) ===" -ForegroundColor Yellow
        Get-Content $file.FullName | Select-String -Pattern "ERROR|Exception|Traceback|Failed|Error" | Select-Object -Last 10
    }
}

# Aliases for convenience
Set-Alias -Name pyenv -Value Set-PythonEnv
Set-Alias -Name ff -Value Find-File
Set-Alias -Name fe -Value Find-Errors

Write-Host "PowerShell profile configured successfully!" -ForegroundColor Green
Write-Host "Available commands:" -ForegroundColor Cyan
Write-Host "   pyenv - activate Python virtual environment" -ForegroundColor White
Write-Host "   ff - quick file search" -ForegroundColor White
Write-Host "   fe - search errors in logs" -ForegroundColor White
'@

# Write profile
$profileContent | Out-File -FilePath $profilePath -Encoding UTF8 -Force

Write-Host "PowerShell profile created: $profilePath" -ForegroundColor Green
Write-Host "Restart PowerShell to apply settings" -ForegroundColor Yellow

# Show current PSReadLine settings
Write-Host "Current PSReadLine settings:" -ForegroundColor Cyan
Get-PSReadLineOption | Format-List 