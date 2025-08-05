# PowerShell скрипт для установки MCP серверов системы управления задачами
# Запускать от имени администратора

Write-Host "🚀 Настройка MCP серверов для системы управления задачами" -ForegroundColor Green

# Создание директорий для данных
$directories = @(
    "D:/PY/MCP/calendar-data",
    "D:/PY/MCP/notifications-data", 
    "D:/PY/MCP/time-tracking-data",
    "D:/PY/MCP/backup-data"
)

Write-Host "📁 Создание директорий для данных..." -ForegroundColor Yellow
foreach ($dir in $directories) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force
        Write-Host "  ✓ Создана директория: $dir" -ForegroundColor Green
    } else {
        Write-Host "  ✓ Директория уже существует: $dir" -ForegroundColor Blue
    }
}

# Установка MCP серверов
Write-Host "📦 Установка MCP серверов..." -ForegroundColor Yellow

$servers = @(
    "@modelcontextprotocol/server-calendar",
    "@modelcontextprotocol/server-notifications", 
    "@modelcontextprotocol/server-time-tracking",
    "@modelcontextprotocol/server-git",
    "@modelcontextprotocol/server-filesystem",
    "@modelcontextprotocol/server-backup"
)

foreach ($server in $servers) {
    Write-Host "  📥 Установка $server..." -ForegroundColor Cyan
    try {
        $null = npx -y $server --version 2>$null
        Write-Host "    ✓ $server установлен" -ForegroundColor Green
    }
    catch {
        Write-Host "    ⚠️ Ошибка установки $server" -ForegroundColor Red
    }
}

# Копирование обновленного конфига
Write-Host "⚙️ Обновление конфигурации MCP..." -ForegroundColor Yellow
$sourceConfig = "mcp-config-updated.json"
$targetConfig = "$env:USERPROFILE\.cursor\mcp.json"

if (Test-Path $sourceConfig) {
    Copy-Item $sourceConfig $targetConfig -Force
    Write-Host "  ✓ Конфигурация обновлена: $targetConfig" -ForegroundColor Green
} else {
    Write-Host "  ❌ Файл конфигурации не найден: $sourceConfig" -ForegroundColor Red
}

Write-Host "`n🎉 Настройка завершена!" -ForegroundColor Green
Write-Host "📋 Следующие шаги:" -ForegroundColor Yellow
Write-Host "  1. Перезапустите Cursor" -ForegroundColor White
Write-Host "  2. Проверьте подключение серверов в MCP панели" -ForegroundColor White
Write-Host "  3. Начните создавать задачи через shrimp-task-manager" -ForegroundColor White

Write-Host "`n🔧 Доступные серверы:" -ForegroundColor Cyan
Write-Host "  * deltatask - базовое управление задачами" -ForegroundColor White
Write-Host "  * shrimp-task-manager - интеллектуальная оркестрация" -ForegroundColor White
Write-Host "  * hpkv-memory-server - семантическая память" -ForegroundColor White
Write-Host "  * memory - граф знаний" -ForegroundColor White
Write-Host "  * mcp-calendar - планирование времени" -ForegroundColor White
Write-Host "  * mcp-notifications - уведомления" -ForegroundColor White
Write-Host "  * mcp-time-tracker - отслеживание времени" -ForegroundColor White
Write-Host "  * mcp-git - интеграция с Git" -ForegroundColor White
Write-Host "  * mcp-filesystem - файловое хранилище" -ForegroundColor White
Write-Host "  * mcp-backup - резервное копирование" -ForegroundColor White 