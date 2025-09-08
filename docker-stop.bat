@echo off
REM DocExtract Docker 중지 스크립트 (Windows)

echo ^> DocExtract Docker 환경 중지 중...

REM Docker Compose로 서비스 중지
echo ^> Docker 서비스 중지 중...
docker-compose down

if %errorlevel% neq 0 (
    echo ^> Docker 서비스 중지 실패
    pause
    exit /b 1
)

echo.
echo ^> 선택적 정리 옵션:
echo   전체 정리 (이미지, 볼륨 포함): docker-clean.bat
echo   로그만 확인: docker-compose logs
echo.
echo ^> DocExtract Docker 환경이 중지되었습니다!
echo.
pause