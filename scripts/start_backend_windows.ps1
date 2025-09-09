# DocExtract Backend 실행 스크립트 (PowerShell용)
# 사용법: .\scripts\start_backend_windows.ps1 [dev|prod]

param(
    [string]$Mode = "dev"
)

# 색상 정의
$Green = [System.ConsoleColor]::Green
$Yellow = [System.ConsoleColor]::Yellow
$Red = [System.ConsoleColor]::Red
$Blue = [System.ConsoleColor]::Blue

# 기본값 설정
if (-not $env:HOST) { $env:HOST = "0.0.0.0" }
if (-not $env:PORT) { $env:PORT = "58000" }
if (-not $env:CONDA_ENV) { $env:CONDA_ENV = "DocExtract" }

Write-Host "🚀 DocExtract Backend 시작 (Windows PowerShell)" -ForegroundColor $Blue
Write-Host "모드: $Mode" -ForegroundColor $Yellow
Write-Host "호스트: $($env:HOST)" -ForegroundColor $Yellow
Write-Host "포트: $($env:PORT)" -ForegroundColor $Yellow
Write-Host "Conda 환경: $($env:CONDA_ENV)" -ForegroundColor $Yellow
Write-Host ""

# 프로젝트 루트 디렉토리로 이동
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $ProjectRoot "backend"

Write-Host "📁 프로젝트 루트: $ProjectRoot" -ForegroundColor $Blue
Write-Host "📁 백엔드 디렉토리: $BackendDir" -ForegroundColor $Blue

# 백엔드 디렉토리 확인
if (-not (Test-Path $BackendDir)) {
    Write-Host "❌ 오류: backend 디렉토리를 찾을 수 없습니다" -ForegroundColor $Red
    Write-Host "예상 위치: $BackendDir"
    Read-Host "Press Enter to exit"
    exit 1
}

Set-Location $BackendDir

# main.py 파일 확인
if (-not (Test-Path "main.py")) {
    Write-Host "❌ 오류: main.py 파일을 찾을 수 없습니다" -ForegroundColor $Red
    Write-Host "현재 위치: $(Get-Location)"
    Read-Host "Press Enter to exit"
    exit 1
}

# Conda 확인
try {
    $null = Get-Command conda -ErrorAction Stop
    Write-Host "✅ Conda 확인됨" -ForegroundColor $Green
} catch {
    Write-Host "❌ 오류: conda가 설치되어 있지 않습니다" -ForegroundColor $Red
    Write-Host "Anaconda 또는 Miniconda를 설치해주세요"
    Read-Host "Press Enter to exit"
    exit 1
}

# Conda 환경 확인 및 생성
$envExists = & conda info --envs | Select-String "^$($env:CONDA_ENV)\s"
if (-not $envExists) {
    Write-Host "📦 Conda 환경 생성 중: $($env:CONDA_ENV)" -ForegroundColor $Yellow
    & conda create -n $env:CONDA_ENV python=3.11 -y
    Write-Host "✅ Conda 환경 생성 완료" -ForegroundColor $Green
} else {
    Write-Host "✅ Conda 환경 확인: $($env:CONDA_ENV)" -ForegroundColor $Green
}

# Conda 환경 활성화
Write-Host "🔄 Conda 환경 활성화 중: $($env:CONDA_ENV)" -ForegroundColor $Yellow
& conda activate $env:CONDA_ENV

# 의존성 설치 확인
Write-Host "📋 의존성 확인 중..." -ForegroundColor $Yellow
if (-not (Test-Path "requirements.txt")) {
    Write-Host "❌ requirements.txt 파일이 없습니다" -ForegroundColor $Red
    Read-Host "Press Enter to exit"
    exit 1
}

# pip 업그레이드
Write-Host "🔄 pip 업그레이드 중..." -ForegroundColor $Yellow
& pip install --upgrade pip | Out-Null

# 의존성 설치
Write-Host "📦 의존성 설치 중..." -ForegroundColor $Yellow
& pip install -r requirements.txt
Write-Host "✅ 의존성 설치 완료" -ForegroundColor $Green

# 데이터 디렉토리 생성
if (-not (Test-Path "data")) {
    Write-Host "📁 데이터 디렉토리 생성 중..." -ForegroundColor $Yellow
    New-Item -ItemType Directory -Path "data\uploads" -Force | Out-Null
    Write-Host "✅ 데이터 디렉토리 생성 완료" -ForegroundColor $Green
}

# 오프라인 모드로 데이터베이스 초기화 (Windows 문제 해결)
if (-not (Test-Path "data\db.sqlite3")) {
    Write-Host "🗄️ 데이터베이스 초기화 중 (오프라인 모드)..." -ForegroundColor $Yellow
    $env:OFFLINE_MODE = "true"
    $env:SKIP_EXTERNAL_CHECKS = "true"
    
    try {
        & python -c "import os; os.environ['OFFLINE_MODE']='true'; os.environ['SKIP_EXTERNAL_CHECKS']='true'; from main import app; print('Database initialized')" | Out-Null
        Write-Host "✅ 데이터베이스 초기화 완료" -ForegroundColor $Green
    } catch {
        Write-Host "❌ 데이터베이스 초기화 실패" -ForegroundColor $Red
        Write-Host "수동으로 초기화를 시도합니다..." -ForegroundColor $Yellow
        & python -c "from db.db import Base, engine; Base.metadata.create_all(bind=engine); print('Manual DB init complete')"
        Write-Host "✅ 수동 데이터베이스 초기화 완료" -ForegroundColor $Green
    }
}

# 포트 사용 중인지 확인 (PowerShell용)
$portInUse = Get-NetTCPConnection -LocalPort $env:PORT -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "⚠️ 포트 $($env:PORT)이 이미 사용 중입니다" -ForegroundColor $Yellow
    Write-Host "다른 포트를 사용하려면: `$env:PORT=8001; .\scripts\start_backend_windows.ps1" -ForegroundColor $Yellow
    $reply = Read-Host "계속하시겠습니까? (y/N)"
    if ($reply -ne "y" -and $reply -ne "Y") {
        exit 1
    }
}

Write-Host ""
Write-Host "🎯 서버 시작 중..." -ForegroundColor $Green
Write-Host "📍 서버 주소: http://localhost:$($env:PORT)" -ForegroundColor $Blue
Write-Host "📚 API 문서: http://localhost:$($env:PORT)/docs" -ForegroundColor $Blue
Write-Host "🛠️ 대체 문서: http://localhost:$($env:PORT)/redoc" -ForegroundColor $Blue
Write-Host ""
Write-Host "서버를 중지하려면 Ctrl+C를 누르세요" -ForegroundColor $Yellow
Write-Host ""

# 오프라인 모드 환경변수 설정
$env:OFFLINE_MODE = "true"
$env:SKIP_EXTERNAL_CHECKS = "true"

# 서버 실행
if ($Mode -eq "prod") {
    Write-Host "🏭 프로덕션 모드로 시작" -ForegroundColor $Green
    & uvicorn main:app --host $env:HOST --port $env:PORT
} else {
    Write-Host "🔧 개발 모드로 시작 (자동 리로드)" -ForegroundColor $Green
    & uvicorn main:app --reload --host $env:HOST --port $env:PORT
}