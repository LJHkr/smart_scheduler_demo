$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$keyPath = Join-Path $PSScriptRoot "deepseek_key.txt"

if (-not (Test-Path -LiteralPath $keyPath)) {
    $apiKey = Read-Host "Paste your DeepSeek API Key"
    if ([string]::IsNullOrWhiteSpace($apiKey)) {
        Write-Host "API Key cannot be empty." -ForegroundColor Red
        exit 1
    }
    [System.IO.File]::WriteAllText(
        $keyPath,
        $apiKey.Trim(),
        [System.Text.UTF8Encoding]::new($false)
    )
    Write-Host "API Key saved locally." -ForegroundColor Green
}

Write-Host "Starting DeepSeek scheduling agent..." -ForegroundColor Cyan
python deepseek_app.py
