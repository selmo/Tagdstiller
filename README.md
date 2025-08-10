# 📄 DocExtract (Tagdstiller) - AI 문서 키워드 추출 시스템

> **완전한 풀스택 문서 키워드 추출 및 관리 시스템**  
> 다중 파일 형식 지원, AI 기반 키워드 추출, 실시간 관리 UI 제공

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-blue.svg)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5+-blue.svg)](https://typescriptlang.org)

---

## 🌟 주요 기능

### 📁 **다중 파일 형식 지원**
- **PDF, DOCX, HTML, Markdown, TXT** 파일 자동 파싱
- **Drag & Drop** 파일 업로드 (단일/다중)
- **실시간 파싱 상태** 확인 및 오류 처리

### 🤖 **AI 기반 키워드 추출**
- **KeyBERT**: 14개 다국어/한국어 최적화 모델 지원
- **spaCy NER**: 개체명 인식 기반 키워드 추출
- **LLM (Ollama)**: 대화형 AI 모델 연동
- **KoNLPy**: 한국어 자연어 처리

### 🎯 **고급 키워드 관리**
- **키워드 중심 뷰**: 키워드별 문서 분포 분석
- **문서 중심 뷰**: 문서별 키워드 목록
- **추출기별 필터링** 및 색상 구분
- **실시간 검색** 및 상세 정보 표시

### ⚙️ **탭 기반 설정 관리**
- **추출기별 독립 설정**: KeyBERT, NER, LLM, KoNLPy 탭
- **색상 코딩** 및 설정 개수 표시
- **동적 모델 선택** (드롭다운)
- **실시간 연결 테스트** 및 상태 피드백

### 📄 **고급 문서 뷰어**
- **PDF 뷰어**: react-pdf 기반 키워드 하이라이팅
- **다중 형식 지원**: PDF, TXT, HTML, Markdown
- **키워드 위치 표시**: 페이지/라인 정보
- **줌/회전/페이지 네비게이션**

### 🎨 **리사이징 가능한 UI**
- **사이드바 크기 조절**: 마우스 드래그로 너비 조절
- **키워드 패널 높이 조절**: 각 패널 독립적 리사이징
- **반응형 레이아웃**: 화면 크기에 따라 자동 조정

### 📊 **실시간 모니터링**
- **진행률 추적**: 파일 수 × 추출기 수 기반 정확한 진행률
- **모델 다운로드**: Server-Sent Events 기반 실시간 진행률
- **상세 로깅**: 모든 추출 단계 기록

### 🐛 **고급 디버그 로깅 시스템** ⭐ **NEW!**
- **단계별 중간 결과 추적**: 전처리 → 후보생성 → 임베딩 → 유사도계산 → 최종결과
- **자동 파일 저장**: JSON/텍스트 형태로 모든 디버그 정보 저장
- **시각적 HTML 리포트**: 추출 과정을 한눈에 볼 수 있는 요약 리포트
- **환경변수 제어**: `ENABLE_KEYWORD_DEBUG=true`로 간편 활성화
- **성능 영향 최소화**: 비활성화 시 성능 영향 없음

---

## 🚀 빠른 시작

### 📋 사전 요구사항
- **Python 3.11+** (Conda 환경 권장)
- **Node.js 16+** (React 개발용)
- **Git**

### 1️⃣ 프로젝트 클론
```bash
git clone <repository-url>
cd DocExtract
```

### 2️⃣ 백엔드 환경 설정
```bash
# Conda 환경 생성 (환경명: DocExtract)
conda create -n DocExtract python=3.11
conda activate DocExtract

# 의존성 설치
cd backend
pip install -r requirements.txt
```

### 3️⃣ 프론트엔드 환경 설정
```bash
cd frontend
npm install
```

### 4️⃣ 시스템 실행
```bash
# 전체 시스템 실행 (백엔드 + 프론트엔드)
./scripts/start_all.sh

# 또는 개별 실행
./scripts/start_backend.sh    # 백엔드만 (포트 58000)
./scripts/start_frontend.sh   # 프론트엔드만 (포트 3001)
```

### 5️⃣ 접속
- **웹 애플리케이션**: http://localhost:3001
- **API 문서**: http://localhost:58000/docs

---

## 📖 사용법

### 1. **프로젝트 생성**
- 좌측 상단 "새 프로젝트" 버튼 클릭
- 프로젝트 이름 입력 후 생성

### 2. **파일 업로드**
- 파일 업로드 영역에 파일을 **드래그 앤 드롭**
- 또는 "파일 선택" 버튼으로 파일 선택
- 지원 형식: `.pdf`, `.docx`, `.html`, `.md`, `.txt`

### 3. **키워드 추출**
- 추출하려는 방법을 선택 (KeyBERT, NER, LLM, KoNLPy)
- "키워드 추출" 버튼 클릭
- 실시간 진행률 확인

### 4. **결과 확인**
- **키워드 결과**: 추출된 키워드 목록 및 점수
- **키워드 관리**: 상세 분석 및 관리 UI
- **키워드 통계**: 전체 통계 및 분포

### 5. **설정 관리**
- 우측 상단 ⚙️ 설정 버튼 클릭
- **탭별 설정**: KeyBERT, NER, LLM, KoNLPy 개별 설정
- 모델 선택, 매개변수 조정, 연결 테스트

### 6. **디버그 로깅** 🐛 **NEW!**
- 추출 과정 상세 분석이 필요한 경우
- 환경변수로 디버그 모드 활성화: `ENABLE_KEYWORD_DEBUG=true`
- 키워드 추출 후 `debug_logs/` 디렉토리에서 결과 확인
- HTML 리포트로 시각적 분석 가능

---

## 🔧 고급 설정

### 디버그 로깅 시스템 ⭐ **NEW!**
키워드 추출 과정을 상세히 분석하고 디버깅할 수 있는 고급 기능입니다.

#### 활성화 방법
```bash
# 디버그 모드 활성화
export ENABLE_KEYWORD_DEBUG=true

# 백엔드 서버 실행
./scripts/start_backend.sh
```

#### 생성되는 파일
- `debug_logs/YYYYMMDD_HHMMSS_SESSION/` 디렉토리
- 전체 세션 데이터 (`debug_session.json`)
- 추출기별 상세 결과 (`keybert_*.json`, `spacy_*.json` 등)
- **시각적 HTML 리포트** (`summary_report.html`)

#### 활용 사례
- 키워드 추출 품질 분석
- 알고리즘 매개변수 튜닝
- 성능 병목 지점 파악
- 연구 및 개발 목적의 상세 분석

### Ollama LLM 연동 (선택사항)
```bash
# Ollama 설치
curl -fsSL https://ollama.com/install.sh | sh

# 모델 다운로드
ollama pull llama2
ollama pull gemma

# Ollama 서버 실행
ollama serve
```

### KeyBERT 모델 선택
설정 패널에서 14개 모델 중 선택:
- **다국어 모델**: all-MiniLM-L6-v2 (추천)
- **한국어 최적화**: jhgan/ko-sroberta-multitask (추천)
- **영어 전용**: all-mpnet-base-v2

### spaCy 모델 설치
```bash
# 영어 모델
python -m spacy download en_core_web_sm

# 한국어 모델 
python -m spacy download ko_core_news_sm
```

---

## 🏗️ 시스템 아키텍처

### **백엔드** (FastAPI + SQLite)
```
backend/
├── main.py                 # FastAPI 애플리케이션 엔트리포인트
├── db/                     # 데이터베이스 설정 및 모델
│   ├── db.py              # SQLAlchemy 설정
│   └── models.py          # 데이터 모델 정의
├── routers/               # API 라우터
│   ├── projects.py        # 프로젝트 관리
│   ├── files.py           # 파일 업로드/관리
│   ├── configs.py         # 설정 관리
│   └── extraction.py      # 키워드 추출
├── extractors/            # 키워드 추출기
│   ├── keybert_extractor.py
│   ├── spacy_ner_extractor.py
│   ├── llm_extractor.py
│   └── konlpy_extractor.py
├── services/              # 비즈니스 로직
│   ├── parser/           # 문서 파서
│   └── config_service.py # 설정 관리
└── utils/                 # 유틸리티
    └── text_cleaner.py    # 텍스트 정제
```

### **프론트엔드** (React + TypeScript)
```
frontend/src/
├── App.tsx                # 메인 애플리케이션
├── components/            # React 컴포넌트
│   ├── ProjectForm.tsx           # 프로젝트 관리
│   ├── FileUploader.tsx          # 파일 업로드
│   ├── ExtractorTrigger.tsx      # 키워드 추출 실행
│   ├── KeywordResultViewer.tsx   # 결과 표시
│   ├── KeywordManagement.tsx     # 키워드 관리 UI (리사이징 가능)
│   ├── SettingsPanel.tsx         # 설정 관리 (탭 기반)
│   ├── AdvancedPDFViewer.tsx     # PDF 뷰어 (키워드 하이라이팅)
│   └── GlobalKeywordManagement.tsx # 전체 키워드 통계
├── services/              # API 통신
│   └── api.ts
└── types/                 # TypeScript 타입 정의
    └── api.ts
```

### **데이터베이스 스키마**
- **Project**: 프로젝트 정보 (id, name, created_at)
- **File**: 파일 정보 (id, project_id, filename, content, parse_status)
- **KeywordOccurrence**: 키워드 추출 결과 (keyword, extractor_name, score, position)
- **Config**: 시스템 설정 (key, value, description)

---

## 🔧 주요 API 엔드포인트

### **프로젝트 관리**
- `GET /projects/` - 프로젝트 목록
- `POST /projects/` - 프로젝트 생성
- `PUT /projects/{id}` - 프로젝트 수정
- `DELETE /projects/{id}` - 프로젝트 삭제

### **파일 관리**
- `POST /projects/{id}/upload` - 단일 파일 업로드
- `POST /projects/{id}/upload_bulk` - 다중 파일 업로드
- `GET /projects/{id}/files` - 프로젝트 파일 목록
- `DELETE /projects/{id}/files/{file_id}` - 파일 삭제

### **키워드 추출**
- `POST /projects/{id}/extract_keywords/` - 키워드 추출
- `GET /projects/{id}/keywords/` - 프로젝트 키워드 조회
- `GET /files/{id}/keywords/` - 파일별 키워드 조회
- `GET /keywords/statistics` - 키워드 통계

### **설정 관리**
- `GET /configs/` - 전체 설정 목록
- `PUT /configs/{key}` - 설정 값 수정
- `GET /configs/keybert/models` - KeyBERT 모델 목록
- `POST /configs/keybert/models/{model}/download` - 모델 다운로드

### **추출기 관리**
- `GET /extractors/available` - 사용 가능한 추출기 목록
- `GET /llm/ollama/models` - Ollama 모델 목록
- `POST /llm/test_connection` - LLM 연결 테스트

---

## 🤖 지원 키워드 추출기

### **1. KeyBERT** 🎯
**총 14개 모델 지원**

#### 다국어 모델 (5개)
- `all-MiniLM-L6-v2` 🌟 **추천** - 빠르고 효율적
- `paraphrase-multilingual-MiniLM-L12-v2` - 고품질 다국어
- `paraphrase-multilingual-mpnet-base-v2` - 최고 품질
- `distiluse-base-multilingual-cased` - 균형잡힌 성능
- `LaBSE` - 109개 언어 지원

#### 한국어 최적화 (4개)
- `jhgan/ko-sroberta-multitask` 🌟 **한국어 추천**
- `jhgan/ko-sbert-nli` - 의미 유사도 특화
- `BM-K/KoSimCSE-roberta-multitask` - SimCSE 기반
- `snunlp/KR-SBERT-V40K-klueNLI-augSTS` - KLUE 데이터 학습

#### 영어 전용 (5개)  
- `all-mpnet-base-v2` - 고성능 영어 모델
- `all-distilroberta-v1` - 빠른 처리
- `all-roberta-large-v1` - 최고 정확도
- `paraphrase-albert-small-v2` - 경량화
- `msmarco-distilbert-base-v4` - 검색 최적화

### **2. spaCy NER** 🏷️
- **다국어 개체명 인식**: 인명, 기관명, 지명 등
- **지원 모델**: `ko_core_news_*`, `en_core_web_*`
- **카테고리별 색상 구분**: PERSON, ORG, LOC, MISC

### **3. LLM (Ollama)** 🧠
- **지원 제공자**: Ollama, OpenAI, Anthropic
- **동적 모델 로딩**: 서버에서 실시간 모델 목록 조회
- **연결 테스트**: 실시간 연결 상태 확인
- **프롬프트 기반**: 컨텍스트 인식 키워드 추출

### **4. KoNLPy** 🇰🇷
- **한국어 전용**: Okt, Komoran, Hannanum, Kkma
- **품사 태깅**: 명사, 동사, 형용사 기반 키워드
- **한국어 특화**: 조사, 어미 처리

---

## ⚙️ 설정 가이드

### **KeyBERT 설정**
```json
{
  "extractor.keybert.model": "all-MiniLM-L6-v2",
  "KeyBERT_MMR": "true",
  "extractor.keybert.diversity": "0.5",
  "extractor.keybert.max_keywords": "10",
  "extractor.keybert.keyphrase_ngram_range": "[1, 2]"
}
```

### **LLM 설정**  
```json
{
  "LLM_PROVIDER": "ollama",
  "OLLAMA_BASE_URL": "http://localhost:11434",
  "OLLAMA_MODEL": "mistral",
  "OLLAMA_TIMEOUT": "30",
  "extractor.llm.temperature": "0.3"
}
```

### **추출기 활성화**
```json
{
  "DEFAULT_EXTRACTORS": "[\"keybert\", \"spacy_ner\"]",
  "ENABLE_LLM_EXTRACTION": "true"
}
```

---

## 🧪 테스트

### **백엔드 테스트**
```bash
cd backend
pytest tests/ -v
```

### **테스트 커버리지**
- ✅ 프로젝트 생성/관리
- ✅ 파일 업로드/파싱
- ✅ 키워드 추출 API
- ✅ 설정 관리
- ✅ 데이터베이스 연동

---

## 🔍 문제 해결

### **일반적인 문제들**

#### 1. **KeyBERT 모델 로딩 실패**
```bash
# 캐시 삭제 후 재다운로드
rm -rf ~/.cache/huggingface/hub/
# 설정에서 모델 재로드 버튼 클릭
```

#### 2. **Ollama 연결 실패**
```bash
# Ollama 서버 실행 확인
ollama serve
# 설정에서 연결 테스트 실행
```

#### 3. **파일 파싱 오류**
- 지원 형식 확인: `.pdf`, `.docx`, `.html`, `.md`, `.txt`
- 파일 크기 제한 확인
- 파일 권한 확인

#### 4. **프론트엔드 빌드 오류**
```bash
cd frontend
npm install
npm run build
```

### **로그 확인**
- **백엔드 로그**: `backend/backend.log`
- **프론트엔드 로그**: `frontend/frontend.log`
- **실시간 로그**: 개발자 도구 콘솔

---

## 📈 성능 최적화

### **KeyBERT 모델 선택 가이드**
- **한국어 문서**: `jhgan/ko-sroberta-multitask` (400MB)
- **다국어 문서**: `all-MiniLM-L6-v2` (90MB, 빠름)
- **고품질 필요**: `paraphrase-multilingual-mpnet-base-v2` (1.1GB)
- **영어 문서**: `all-mpnet-base-v2` (420MB)

### **시스템 요구사항**
- **최소 메모리**: 4GB RAM
- **권장 메모리**: 8GB+ RAM (대용량 모델 사용 시)
- **저장공간**: 5GB+ (모델 캐시 포함)

---

## 🤝 기여하기

### **개발 환경 설정**
```bash
# 개발용 브랜치 생성
git checkout -b feature/new-feature

# 백엔드 개발
cd backend
pip install -r requirements.txt
python main.py

# 프론트엔드 개발  
cd frontend
npm install
npm start
```

### **코드 스타일**
- **백엔드**: Black, isort, flake8
- **프론트엔드**: Prettier, ESLint
- **커밋**: Conventional Commits

---

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

---

## 🙋‍♂️ 지원

### **문서**
- [CLAUDE.md](./CLAUDE.md) - 상세 시스템 문서
- [spec.md](./spec.md) - 기술 명세서
- [API 문서](http://localhost:8000/docs) - FastAPI 자동 생성 문서

### **연락처**
- 이슈 제기: GitHub Issues
- 기능 요청: GitHub Discussions

---

## 📊 최근 업데이트 (2025.08.07)

### ✨ 새로운 기능
- **🐛 고급 디버그 로깅 시스템**: 키워드 추출 과정의 모든 중간 결과물 상세 기록 및 분석 **NEW!**
- **고급 PDF 뷰어**: PDF.js 기반 키워드 하이라이팅
- **리사이징 가능한 UI**: 사이드바 및 패널 크기 조절 기능
- **전체 키워드 통계**: 모든 프로젝트의 통합 키워드 분석
- **향상된 키워드 관리**: 키워드/문서 중심 다중 뷰 모드

### 🐛 버그 수정
- pandas 의존성 오류 해결 (debug_logger에서 제거)
- 백엔드 서버 시작 오류 수정
- PDF 로딩 안정성 개선
- 키워드 위치 계산 정확도 향상
- 메모리 사용량 최적화

### 🔧 개선사항
- **디버그 로깅**: 모든 추출기(KeyBERT, spaCy NER, LLM, KoNLPy)에 단계별 로깅 통합
- **HTML 리포트**: 자동 생성되는 시각적 디버그 요약 리포트
- **성능 최적화**: 디버그 모드 비활성화 시 성능 영향 없음
- UI/UX 전면 개선
- 반응형 레이아웃 강화

---

**Made with ❤️ using FastAPI, React, and AI**

**최종 업데이트**: 2025년 8월 7일