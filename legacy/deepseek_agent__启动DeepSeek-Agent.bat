@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist deepseek_key.txt (
  echo 首次启动，请粘贴你的 DeepSeek API Key。
  set /p DEEPSEEK_KEY=Key: 
  if "%DEEPSEEK_KEY%"=="" (
    echo Key 不能为空。
    pause
    exit /b 1
  )
  >deepseek_key.txt echo %DEEPSEEK_KEY%
)
python deepseek_app.py
pause
