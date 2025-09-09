# Windows 환경 설정 가이드

## Windows에서 DocExtract 실행 문제 해결

### 주요 문제점

1. **데이터베이스 초기화 중 멈춤**: Ollama, spaCy, Memgraph 등 외부 서비스 연결 시도
2. **경로 구분자**: Windows (`\`) vs Unix (`/`) 경로 문제  
3. **권한 문제**: SQLite 파일 생성 권한
4. **네트워크 타임아웃**: Ollama 서버 연결 시도

### 해결 방법

#### 1. Windows 전용 실행 스크립트 사용

```batch
# scripts/start_backend_windows.bat 사용
start_backend_windows.bat

# 또는 환경변수와 함께
set OFFLINE_MODE=true
set SKIP_EXTERNAL_CHECKS=true
start_backend_windows.bat
```

#### 2. 수동 초기화 (문제 발생 시)

```cmd
# 1. Conda 환경 활성화
conda activate DocExtract

# 2. 백엔드 디렉토리로 이동
cd backend

# 3. 환경변수 설정
set OFFLINE_MODE=true
set SKIP_EXTERNAL_CHECKS=true

# 4. 수동 데이터베이스 생성
python -c "from db.db import Base, engine; Base.metadata.create_all(bind=engine); print('Database created')"

# 5. 서버 실행
uvicorn main:app --reload --host 0.0.0.0 --port 58000
```

#### 3. 의존성 문제 해결

```cmd
# spaCy 한국어 모델 설치 (선택사항)
python -m spacy download ko_core_news_sm

# PyTorch 다시 설치 (GPU 문제 시)
pip uninstall torch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# sentence-transformers 재설치
pip install --upgrade sentence-transformers
```

### 환경변수 설정

Windows에서 다음 환경변수를 설정하면 빠른 시작이 가능합니다:

```cmd
set OFFLINE_MODE=true              # 오프라인 모드
set SKIP_EXTERNAL_CHECKS=true     # 외부 연결 건너뛰기
set OLLAMA_BASE_URL=http://localhost:11434  # Ollama 서버 주소
set PORT=58000                     # 서버 포트
set HOST=0.0.0.0                   # 서버 호스트
```

### 문제별 해결책

#### 데이터베이스 초기화 멈춤
- **원인**: Ollama 서버 연결 시도 (기본 11434 포트)
- **해결**: `OFFLINE_MODE=true` 설정

#### spaCy 모델 오류
- **원인**: 한국어 모델 `ko_core_news_sm` 미설치
- **해결**: 모델 설치 또는 NER 추출기 비활성화

#### 포트 충돌
- **확인**: `netstat -an | findstr :58000`
- **해결**: 다른 포트 사용 `set PORT=8001`

#### 권한 문제
- **원인**: SQLite 파일 생성 권한 부족
- **해결**: 관리자 권한으로 실행 또는 사용자 디렉토리 사용

### 성능 최적화

```cmd
# CPU 전용 모드 (GPU 문제 시)
set CUDA_VISIBLE_DEVICES=""

# 메모리 사용량 줄이기
set TRANSFORMERS_CACHE=./cache
set HF_HOME=./cache

# 병렬 처리 제한
set OMP_NUM_THREADS=2
```

### 로그 확인

```cmd
# 백엔드 로그 확인
type backend.log

# 상세 로그 활성화
set LOG_LEVEL=DEBUG
```

### 주의사항

1. **Conda 환경**: 반드시 DocExtract 환경에서 실행
2. **Python 버전**: 3.11 권장
3. **관리자 권한**: 필요시 관리자로 실행
4. **방화벽**: 포트 58000 허용 설정
5. **바이러스 백신**: Python/Conda 실행 허용

### 트러블슈팅

```cmd
# 환경 정보 확인
conda info --envs
python --version
pip list | findstr -i "fastapi uvicorn sqlalchemy"

# 네트워크 연결 테스트
curl http://localhost:11434/api/tags
curl http://localhost:58000/

# 프로세스 확인
tasklist | findstr python
```

### 도움말

문제가 지속되면 다음 정보와 함께 이슈를 보고해주세요:

- Windows 버전 및 아키텍처
- Python/Conda 버전
- 오류 메시지 전문
- backend.log 파일 내용