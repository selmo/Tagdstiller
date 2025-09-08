# 🐳 DocExtract Docker 배포 가이드

DocExtract와 Memgraph를 함께 실행하는 Docker 환경을 제공합니다.

## 📋 구성 요소

### 서비스
- **DocExtract Backend**: FastAPI 기반 문서 분석 API 서버
- **Memgraph**: 그래프 데이터베이스
- **Memgraph Studio**: 그래프 시각화 웹 인터페이스

### 포트
- `58000`: DocExtract API 서버
- `7687`: Memgraph Bolt 프로토콜
- `3000`: Memgraph Studio 웹 UI

## 🚀 빠른 시작

### 1. 환경 설정 (선택적)
`.env` 파일을 수정하여 설정을 변경할 수 있습니다:

```bash
# Ollama URL 설정 (호스트에서 실행 중인 경우)
OLLAMA_BASE_URL=http://host.docker.internal:11434

# 기타 설정들...
```

### 2. Docker 환경 시작

#### Windows:
```batch
docker-start.bat
```

#### Linux/Mac:
```bash
./docker-start.sh
```

또는 수동으로:
```bash
docker-compose up -d
```

### 3. 서비스 접속
- **API 문서**: http://localhost:58000/docs
- **Memgraph Studio**: http://localhost:3000

## 📁 파일 구조

```
DocExtract/
├── docker-compose.yml          # Docker Compose 설정
├── Dockerfile.backend          # DocExtract 백엔드 Dockerfile
├── .env                        # 환경변수 설정
├── .dockerignore              # Docker 무시 파일
├── docker-start.sh            # 시작 스크립트 (Linux/Mac)
├── docker-stop.sh             # 중지 스크립트 (Linux/Mac)
├── docker-clean.sh            # 정리 스크립트 (Linux/Mac)
├── docker-start.bat           # 시작 스크립트 (Windows)
├── docker-stop.bat            # 중지 스크립트 (Windows)
├── docker-clean.bat           # 정리 스크립트 (Windows)
├── data/                      # 데이터 볼륨
├── uploads/                   # 업로드 볼륨
└── logs/                      # 로그 볼륨
```

## 🎛️ 주요 명령어

### 서비스 관리

#### Windows:
```batch
# 서비스 시작
docker-start.bat

# 서비스 중지
docker-stop.bat

# 완전 정리 (이미지, 볼륨 삭제)
docker-clean.bat
```

#### Linux/Mac:
```bash
# 서비스 시작
./docker-start.sh

# 서비스 중지
./docker-stop.sh

# 완전 정리 (이미지, 볼륨 삭제)
./docker-clean.sh
```

### Docker Compose 직접 사용
```bash
# 백그라운드 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f docextract-backend

# 서비스 재시작
docker-compose restart

# 서비스 상태 확인
docker-compose ps

# 서비스 중지
docker-compose down
```

## 🔧 고급 설정

### 1. 메모리 및 CPU 제한
`docker-compose.yml`에서 리소스 제한을 설정할 수 있습니다:

```yaml
services:
  docextract-backend:
    # ... 기타 설정
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          memory: 1G
```

### 2. 볼륨 마운트
호스트 디렉토리를 컨테이너에 마운트:

```yaml
volumes:
  - ./my-documents:/app/uploads
  - ./my-results:/app/data
```

### 3. 환경변수 오버라이드
`.env` 파일 또는 `docker-compose.override.yml` 사용

## 🐛 문제 해결

### 서비스가 시작되지 않는 경우
```bash
# 로그 확인
docker-compose logs

# 서비스별 로그
docker-compose logs docextract-backend
docker-compose logs memgraph
```

### 포트 충돌
포트가 이미 사용 중인 경우 `.env`에서 포트를 변경:
```env
DOCEXTRACT_PORT=58001
MEMGRAPH_PORT=7688
```

### Memgraph 연결 실패
1. Memgraph 컨테이너 상태 확인:
   ```bash
   docker-compose ps memgraph
   ```

2. 네트워크 연결 확인:
   ```bash
   docker-compose exec docextract-backend ping memgraph
   ```

### Ollama 연결
호스트에서 Ollama가 실행 중인지 확인:
```bash
curl http://localhost:11434/api/tags
```

## 📊 모니터링

### 리소스 사용량 확인
```bash
docker stats
```

### 로그 모니터링
```bash
# 실시간 로그
docker-compose logs -f

# 최근 100줄
docker-compose logs --tail=100
```

## 🔒 보안 고려사항

1. **환경변수**: 민감한 정보는 `.env` 파일에 저장하고 Git에 추가하지 마세요
2. **네트워크**: 프로덕션에서는 포트를 제한하고 방화벽 설정
3. **볼륨 권한**: 적절한 파일 권한 설정

## 🚢 배포

### 프로덕션 배포
1. `.env` 파일 수정 (프로덕션 설정)
2. `DEBUG=false` 설정
3. 적절한 시크릿 키 설정
4. 리소스 제한 설정

### 스케일링
```bash
# 백엔드 인스턴스 증가
docker-compose up -d --scale docextract-backend=3
```

## 📝 로그 및 디버깅

### 주요 로그 위치
- DocExtract: `./logs/`
- Memgraph: 컨테이너 내부 `/var/log/memgraph`

### 디버그 모드
```env
DEBUG=true
ENABLE_KEYWORD_DEBUG=true
LOG_LEVEL=DEBUG
```

## 🎯 성능 최적화

1. **메모리 할당**: Memgraph와 DocExtract에 충분한 메모리 할당
2. **볼륨 최적화**: SSD 사용 권장
3. **네트워크**: 로컬 네트워크 사용으로 지연시간 최소화

---

문제가 발생하면 로그를 확인하고 GitHub Issues에 보고해주세요!