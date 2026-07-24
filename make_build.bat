@echo off
echo.
echo =========================================
echo AMS Docker Build and Push Script
echo =========================================
echo.

set REGISTRY=192.168.0.22:5000
set IMAGE_FRONTEND=%REGISTRY%/ams-frontend
set IMAGE_BACKEND=%REGISTRY%/ams-backend
set TAG=latest

echo [1] Building Frontend...
docker build -t %IMAGE_FRONTEND%:%TAG% ./frontend
if errorlevel 1 goto error

echo.
echo [2] Building Backend...
docker build -t %IMAGE_BACKEND%:%TAG% ./backend
if errorlevel 1 goto error

echo.
echo [3] Pushing Frontend to %REGISTRY%...
docker push %IMAGE_FRONTEND%:%TAG%
if errorlevel 1 goto error

echo.
echo [4] Pushing Backend to %REGISTRY%...
docker push %IMAGE_BACKEND%:%TAG%
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
