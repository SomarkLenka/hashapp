@echo off
echo =========================================
echo HashGen Container Verification Script
echo =========================================
echo.

REM Check if container is running
echo 1. Checking running containers...
echo ---------------------------------
docker ps | findstr "hashgen myapp"
if errorlevel 1 echo No hashgen container found running
echo.

REM Get container name or ID
for /f "tokens=*" %%i in ('docker ps --format "{{.Names}}" ^| findstr "hashgen myapp"') do set CONTAINER=%%i
if "%CONTAINER%"=="" for /f "tokens=*" %%i in ('docker ps --format "{{.ID}}"') do set CONTAINER=%%i

if "%CONTAINER%"=="" (
    echo ERROR: No running container found
    echo Start the container with: docker run -d --name hashgen somark28/hashgen:latest
    exit /b 1
)

echo Using container: %CONTAINER%
echo.

REM Check container status
echo 2. Container Status...
echo ----------------------
for /f "tokens=*" %%i in ('docker inspect %CONTAINER% --format="{{.State.Status}}"') do echo Status: %%i
for /f "tokens=*" %%i in ('docker inspect %CONTAINER% --format="{{.State.StartedAt}}"') do echo Started: %%i
echo.

REM Check CPU/Memory usage
echo 3. Resource Usage...
echo --------------------
docker stats %CONTAINER% --no-stream --format "table {{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
echo.

REM Check recent logs
echo 4. Recent Logs (last 20 lines)...
echo ----------------------------------
docker logs %CONTAINER% --tail 20 2>&1 | findstr "INFO ERROR WARNING"
echo.

REM Check for errors
echo 5. Error Check...
echo -----------------
for /f %%i in ('docker logs %CONTAINER% 2^>^&1 ^| find /c "ERROR"') do set ERROR_COUNT=%%i
echo Total errors in logs: %ERROR_COUNT%

if %ERROR_COUNT% GTR 0 (
    echo Last 5 errors:
    docker logs %CONTAINER% 2>&1 | findstr "ERROR"
)
echo.

REM Check BigTable operations
echo 6. BigTable Upload Status...
echo -----------------------------
for /f %%i in ('docker logs %CONTAINER% 2^>^&1 ^| find /c "Uploaded"') do set UPLOAD_COUNT=%%i
echo Successful uploads: %UPLOAD_COUNT%

if %UPLOAD_COUNT% GTR 0 (
    echo Last upload:
    docker logs %CONTAINER% 2>&1 | findstr "Uploaded"
) else (
    echo No uploads yet (uploads occur every 10 minutes or after 10M hashes)
)
echo.

REM Check hashrate
echo 7. Hashrate Performance...
echo ---------------------------
docker logs %CONTAINER% 2>&1 | findstr "Hashrate:"
if errorlevel 1 echo No hashrate data yet (reported with uploads)
echo.

REM Check monitoring server connection
echo 8. Monitoring Server Status...
echo -------------------------------
for /f %%i in ('docker logs %CONTAINER% 2^>^&1 ^| find /c "Failed to report"') do set MONITOR_ERRORS=%%i
echo Monitoring failures: %MONITOR_ERRORS%

if %MONITOR_ERRORS% GTR 0 (
    echo Last monitoring error:
    docker logs %CONTAINER% 2>&1 | findstr "Failed to report"
)
echo.

REM Process check
echo 9. Python Process Check...
echo ---------------------------
docker exec %CONTAINER% ps aux | findstr python
echo.

echo =========================================
echo SUMMARY
echo =========================================
echo.
echo For real-time logs: docker logs -f %CONTAINER%
echo For shell access: docker exec -it %CONTAINER% bash
echo.
pause