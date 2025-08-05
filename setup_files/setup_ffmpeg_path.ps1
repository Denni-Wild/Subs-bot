# PowerShell script to add FFmpeg to system PATH permanently
# Run this script as Administrator

Write-Host "Setting up FFmpeg PATH..." -ForegroundColor Green

# Get the current user's PATH
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")

# FFmpeg installation path
$ffmpegPath = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-7.1.1-full_build\bin"

# Check if FFmpeg path is already in PATH
if ($currentPath -notlike "*$ffmpegPath*") {
    # Add FFmpeg to PATH
    $newPath = "$currentPath;$ffmpegPath"
    [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
    Write-Host "FFmpeg path added to user PATH successfully!" -ForegroundColor Green
    Write-Host "Please restart your terminal/PowerShell for changes to take effect." -ForegroundColor Yellow
} else {
    Write-Host "FFmpeg path is already in user PATH." -ForegroundColor Yellow
}

# Test if FFmpeg is accessible
Write-Host "Testing FFmpeg installation..." -ForegroundColor Green
try {
    $ffmpegVersion = & "$ffmpegPath\ffmpeg.exe" -version 2>&1 | Select-Object -First 1
    Write-Host "FFmpeg version: $ffmpegVersion" -ForegroundColor Green
    Write-Host "FFmpeg is working correctly!" -ForegroundColor Green
} catch {
    Write-Host "Error testing FFmpeg: $_" -ForegroundColor Red
}

Write-Host "Setup complete!" -ForegroundColor Green 