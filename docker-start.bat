@echo off
REM DocExtract Docker 시작 스크립트 (Windows)

echo ^> DocExtract Docker 환경 시작 중...

REM 환경 변수 로드
if exist .env (
    echo ^> 환경 변수 파일 로드 중...
    REM Windows에서는 환경변수를 직접 로드할 수 없으므로 docker-compose에서 처리
)

REM 필요한 디렉토리 생성
echo ^> 필요한 디렉토리 생성 중...
if not exist "data" mkdir data
if not exist "uploads" mkdir uploads
if not exist "logs" mkdir logs

REM Docker Compose로 서비스 시작
echo ^> Docker 서비스 시작 중...
docker-compose up -d

if %errorlevel% neq 0 (
    echo ^> Docker 서비스 시작 실패
    pause
    exit /b 1
)

REM 서비스 시작 대기
echo ^> 서비스 시작 대기 중...
timeout /t 10 /nobreak >nul

echo ^> 서비스 상태 확인 중...
docker-compose ps

echo.
echo ^> DocExtract Docker 환경이 시작되었습니다!
echo.
echo ^> 서비스 접속 정보:
echo   - DocExtract API: http://localhost:58000
echo   - API 문서: http://localhost:58000/docs
echo   - Memgraph Bolt: bolt://localhost:7688
echo   - Memgraph 모니터링: http://localhost:7445
echo.
echo ^> 유용한 명령어:
echo   - 로그 보기: docker-compose logs -f
echo   - 서비스 중지: docker-compose down
echo   - 서비스 재시작: docker-compose restart
echo   - 컨테이너 상태: docker-compose ps
echo.

REM 서비스 헬스체크
echo ^> 서비스 헬스체크 중...
timeout /t 5 /nobreak >nul

REM DocExtract API 확인
echo ^> DocExtract API 확인 중...
curl -s http://localhost:58000/docs >nul 2>&1
if %errorlevel% equ 0 (
    echo ^> DocExtract API 정상 작동 중
) else (
    echo ^> DocExtract API 접속 실패 - 서비스가 아직 시작 중일 수 있습니다
)

echo.
echo ^> 모든 서비스가 준비되었습니다!
echo ^> 자세한 사용법은 DOCKER_README.md를 참고하세요.
echo.
pause