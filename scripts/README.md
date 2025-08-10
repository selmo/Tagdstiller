# 🚀 DocExtract 실행 스크립트 가이드

이 디렉토리에는 DocExtract 시스템을 쉽게 실행하고 관리할 수 있는 스크립트들이 포함되어 있습니다.

## 📋 사전 요구사항

### 백엔드
- **Anaconda 또는 Miniconda** (Python 환경 관리)
- **Python 3.11** (conda 환경으로 자동 설치)

### 프론트엔드  
- **Node.js 18+** (JavaScript 런타임)
- **npm 또는 yarn** (패키지 관리)

### 설치 가이드
```bash
# Miniconda 설치 (macOS)
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh
bash Miniconda3-latest-MacOSX-x86_64.sh

# Node.js 설치 (Homebrew 사용)
brew install node

# 또는 공식 웹사이트에서 다운로드
# https://nodejs.org/
```

## 📁 스크립트 목록

### 🔧 개별 실행 스크립트
- **`start_backend.sh`** - 백엔드 서버만 실행
- **`start_frontend.sh`** - 프론트엔드 서버만 실행

### 🚀 통합 관리 스크립트  
- **`start_all.sh`** - 백엔드 + 프론트엔드 동시 실행
- **`stop_all.sh`** - 모든 서버 중지
- **`status.sh`** - 시스템 상태 확인

## 🎯 기본 사용법

### 전체 시스템 시작
```bash
./scripts/start_all.sh
```

### 개발 모드로 시작
```bash
./scripts/start_all.sh dev
```

### 시스템 상태 확인
```bash
./scripts/status.sh
```

### 시스템 중지
```bash
./scripts/stop_all.sh
```

## 🔧 개별 서버 실행

### 백엔드만 실행
```bash
./scripts/start_backend.sh
```

### 프론트엔드만 실행
```bash
./scripts/start_frontend.sh
```

## ⚙️ 고급 사용법

### 다른 포트로 실행
```bash
# 백엔드 포트 변경
PORT=58001 ./scripts/start_backend.sh

# 프론트엔드 포트 변경  
PORT=8081 ./scripts/start_frontend.sh

# 전체 시스템 포트 변경
BACKEND_PORT=58001 FRONTEND_PORT=8081 ./scripts/start_all.sh
```

### Conda 환경 설정
```bash
# 기본 conda 환경 사용 (DocExtract)
./scripts/start_backend.sh

# 다른 conda 환경 사용
CONDA_ENV=myenv ./scripts/start_backend.sh

# 전체 시스템에서 conda 환경 지정
CONDA_ENV=myenv ./scripts/start_all.sh

# conda 환경 수동 생성 (선택사항)
conda create -n DocExtract python=3.11 -y
conda activate DocExtract
```

### 프로덕션 모드 실행
```bash
./scripts/start_backend.sh prod
./scripts/start_frontend.sh build
./scripts/start_all.sh prod
```

## 📊 시스템 모니터링

### 실시간 로그 확인
```bash
# 백엔드 로그
tail -f backend.log

# 프론트엔드 로그  
tail -f frontend.log

# 모든 로그
tail -f backend.log frontend.log
```

### 프로세스 상태 확인
```bash
# 간단한 상태 확인
./scripts/status.sh

# 상세한 프로세스 정보
ps aux | grep -E "(uvicorn|npm|node)"

# 포트 사용 상황
lsof -i :58000 -i :8080
```

## 🚨 문제 해결

### 포트 충돌 해결
```bash
# 사용 중인 프로세스 찾기
lsof -i :58000
lsof -i :8080

# 프로세스 강제 종료
kill -9 <PID>

# 또는 스크립트로 일괄 정리
./scripts/stop_all.sh
```

### 권한 문제 해결
```bash
# 스크립트 실행 권한 부여
chmod +x scripts/*.sh

# 또는 개별적으로
chmod +x scripts/start_all.sh
chmod +x scripts/stop_all.sh
chmod +x scripts/status.sh
```

### 의존성 문제 해결
```bash
# 백엔드 conda 환경 재생성
conda remove -n DocExtract --all -y
conda create -n DocExtract python=3.11 -y
conda activate DocExtract
cd backend && pip install -r requirements.txt

# 프론트엔드 의존성 재설치  
cd frontend && rm -rf node_modules && npm install
```

### Conda 환경 문제 해결
```bash
# Conda 초기화 (처음 설치 후)
conda init bash  # 또는 conda init zsh

# 새 터미널 열거나 shell 재로드
source ~/.bashrc  # 또는 source ~/.zshrc

# Conda 환경 목록 확인
conda info --envs

# 환경 활성화 확인
which python
which pip
```

### 데이터베이스 초기화
```bash
# 데이터베이스 파일 삭제 (새로 생성됨)
rm backend/data/db.sqlite3

# 업로드 파일 정리
rm -rf backend/data/uploads/*
```

## 🔄 개발 워크플로우

### 1. 개발 시작
```bash
# 전체 시스템 개발 모드로 시작
./scripts/start_all.sh dev

# 또는 개별 실행
./scripts/start_backend.sh dev &
./scripts/start_frontend.sh dev &
```

### 2. 개발 중
```bash
# 상태 확인
./scripts/status.sh

# 로그 모니터링
tail -f backend.log frontend.log
```

### 3. 개발 완료
```bash
# 시스템 중지
./scripts/stop_all.sh

# 선택적으로 로그 파일 정리
rm backend.log frontend.log
```

## 📱 접속 정보

시스템이 정상적으로 시작되면 다음 주소로 접속할 수 있습니다:

- **🌐 웹 애플리케이션**: http://localhost:8080
- **🔧 API 서버**: http://localhost:58000  
- **📚 API 문서**: http://localhost:58000/docs
- **🛠️ 대체 API 문서**: http://localhost:58000/redoc

## 💡 팁

### 백그라운드 실행
```bash
# 백그라운드에서 실행
nohup ./scripts/start_all.sh > system.log 2>&1 &

# 실행 확인
./scripts/status.sh
```

### 자동 재시작 설정
```bash
# systemd 서비스 생성 (Linux)
sudo cp scripts/docextract.service /etc/systemd/system/
sudo systemctl enable docextract
sudo systemctl start docextract
```

### 성능 모니터링
```bash
# 리소스 사용량 확인
htop
iostat 1
```

## 🔒 보안 고려사항

- 프로덕션 환경에서는 방화벽 설정 확인
- API 키 및 민감한 설정은 환경 변수로 관리
- HTTPS 설정 권장 (프로덕션)
- 정기적인 로그 파일 관리

## 📞 지원

문제가 발생하면 다음을 확인해보세요:

1. `./scripts/status.sh`로 시스템 상태 확인
2. 로그 파일 확인 (`backend.log`, `frontend.log`)
3. 포트 충돌 여부 확인
4. 의존성 설치 상태 확인

---

*이 스크립트들은 개발과 운영을 편리하게 하기 위해 제작되었습니다. 추가 기능이 필요하면 스크립트를 수정하여 사용하세요.*