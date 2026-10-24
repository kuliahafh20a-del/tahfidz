@echo off
setlocal

cd /d "%~dp0"

if /I "%~1"=="--help" goto :help

where pnpm >nul 2>&1
if errorlevel 1 (
  echo [ERROR] pnpm tidak ditemukan. Install pnpm 11 atau lebih baru terlebih dahulu.
  exit /b 1
)

where uv >nul 2>&1
if errorlevel 1 (
  echo [ERROR] uv tidak ditemukan. Install uv 0.12 atau lebih baru terlebih dahulu.
  exit /b 1
)

if not exist "node_modules\.pnpm" (
  echo [SETUP] Menginstal dependency workspace...
  call pnpm install
  if errorlevel 1 exit /b 1
)

if not exist "apps\api\.venv\Scripts\python.exe" (
  echo [SETUP] Menyiapkan environment FastAPI...
  call pnpm --filter @yaqin/api setup
  if errorlevel 1 exit /b 1
)

echo [START] Next.js  : http://localhost:3000
echo [START] FastAPI  : http://localhost:8000
echo [START] API docs : http://localhost:8000/docs
echo.
echo Tekan Ctrl+C untuk menghentikan kedua service.
echo.

call pnpm dev
exit /b %errorlevel%

:help
echo Menjalankan Next.js dan FastAPI untuk development.
echo.
echo Penggunaan:
echo   dev.cmd
echo.
echo Jalankan dari Command Prompt atau double-click file ini.
exit /b 0
