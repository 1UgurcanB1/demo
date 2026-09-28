@echo off
cd /d "%~dp0"
where docker >nul 2>nul
if errorlevel 1 (
  echo Docker Desktop bulunamadi. README.md dosyasindaki Python ve Node kurulumunu kullanin.
  pause
  exit /b 1
)
docker compose up --build -d
if errorlevel 1 (
  echo Baslatilamadi. Docker Desktop uygulamasinin acik oldugunu kontrol edin.
  pause
  exit /b 1
)
start http://localhost:3000
pause
