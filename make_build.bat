@echo off
echo.
echo =========================================
echo AMS Docker Build and Push Script
echo =========================================
echo.

set REGISTRY=192.168.0.22:5000
set IMAGE_FRONTEND=%REGISTRY%/ams-frontend
set IMAGE_BACKEND=%REGISTRY%/ams-backend

rem 릴리즈 버전 (루트 VERSION 파일이 단일 소스) — 릴리즈마다 VERSION 파일을 올릴 것
set /p TAG=<VERSION

echo Version: %TAG%

echo [1] Building Frontend...
docker build --build-arg APP_VERSION=%TAG% -t %IMAGE_FRONTEND%:%TAG% -t %IMAGE_FRONTEND%:latest ./frontend
if errorlevel 1 goto error

echo.
echo [2] Building Backend...
docker build --build-arg APP_VERSION=%TAG% -t %IMAGE_BACKEND%:%TAG% -t %IMAGE_BACKEND%:latest ./backend
if errorlevel 1 goto error

echo.
echo [3] Pushing Frontend to %REGISTRY%...
docker push %IMAGE_FRONTEND%:%TAG%
docker push %IMAGE_FRONTEND%:latest
if errorlevel 1 goto error

echo.
echo [4] Pushing Backend to %REGISTRY%...
docker push %IMAGE_BACKEND%:%TAG%
docker push %IMAGE_BACKEND%:latest
if errorlevel 1 goto error

echo.
echo [SUCCESS] All builds and pushes completed!
goto end

:error
echo.
echo [ERROR] An error occurred during the process.
pause
exit /b 1

:end
pause
