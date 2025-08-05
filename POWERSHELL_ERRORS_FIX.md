# Исправление ошибок PowerShell PSReadLine

## Проблема
В PowerShell возникали ошибки типа:
```
System.ArgumentOutOfRangeException: Значение должно быть больше или равно нулю и меньше, чем размер буфера в данной размерности.
Имя параметра: top
```

## Причина
Проблема связана с модулем PSReadLine версии 2.0.0, который имеет известные баги с обработкой буфера консоли.

## Решение

### 1. Обновление PSReadLine
```powershell
Install-Module PSReadLine -Force -SkipPublisherCheck -Scope CurrentUser
```

### 2. Настройка профиля PowerShell
Запустите скрипт `setup_powershell_profile.ps1` для автоматической настройки.

### 3. Ручная настройка PSReadLine
```powershell
# Отключить проблемные функции
Set-PSReadLineOption -PredictionSource None
Set-PSReadLineOption -PredictionViewStyle ListView
Set-PSReadLineOption -BellStyle None

# Настройки для стабильности
Set-PSReadLineOption -EditMode Windows
Set-PSReadLineOption -HistoryNoDuplicates
Set-PSReadLineOption -MaximumHistoryCount 1000
Set-PSReadLineOption -CompletionQueryItems 100
```

## Проверка исправления
```powershell
Get-PSReadLineOption | Select-Object PredictionSource, PredictionViewStyle, BellStyle, EditMode
```

## Результат
- ✅ Ошибки PSReadLine устранены
- ✅ Команды PowerShell работают стабильно
- ✅ Добавлены полезные функции для работы с проектом

## Дополнительные функции
После настройки профиля доступны команды:
- `pyenv` - активация виртуального окружения Python
- `ff` - быстрый поиск файлов
- `fe` - поиск ошибок в логах

## Дата исправления
05.08.2025 