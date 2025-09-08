@echo off
REM DocExtract Docker 정리 스크립트 (Windows)

echo ^> DocExtract Docker 환경 정리 중...

REM 확인 메시지
set /p CONFIRM="^> 모든 컨테이너, 이미지, 볼륨을 삭제하시겠습니까? (y/N): "
if /i not "%CONFIRM%"=="y" (
    echo ^> 정리 작업이 취소되었습니다.
    pause
    exit /b 1
)

REM 서비스 중지 및 삭제
echo ^> Docker 서비스 중지 및 컨테이너 삭제 중...
docker-compose down -v --remove-orphans

if %errorlevel% neq 0 (
    echo ^> Docker 서비스 중지 실패
    pause
    exit /b 1
)

REM 이미지 삭제
echo ^> DocExtract 관련 이미지 삭제 중...
for /f "tokens=3" %%i in ('docker images ^| findstr /i "docextract memgraph"') do (
    docker rmi -f %%i 2>nul
)

REM 볼륨 삭제
echo ^> DocExtract 관련 볼륨 삭제 중...
for /f "tokens=2" %%i in ('docker volume ls ^| findstr /i "docextract memgraph"') do (
    docker volume rm %%i 2>nul
)

REM 네트워크 삭제
echo ^> DocExtract 네트워크 삭제 중...
for /f "tokens=1" %%i in ('docker network ls ^| findstr docextract') do (
    docker network rm %%i 2>nul
)

REM 사용하지 않는 리소스 정리
echo ^> 사용하지 않는 Docker 리소스 정리 중...
docker system prune -f

echo.
echo ^> DocExtract Docker 환경이 완전히 정리되었습니다!
echo ^> 다시 시작하려면: docker-start.bat
echo.
pause