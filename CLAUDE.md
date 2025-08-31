# 📄 CLAUDE.md - DocExtract 시스템

## 프로젝트 개요 ✅ 완성됨 (2025.08.29)
이 프로젝트는 문서를 프로젝트 단위로 업로드하고 키워드를 추출하여 관리하는 **완전한 풀스택 시스템**입니다. 

### 핵심 기능 (최종 업데이트 2025.08.30)
- **🚀 완전 파싱 시스템**: 모든 파서를 동시 사용하여 최상의 결과 보장
- **📊 단계적 문서 처리**: 파싱→키워드추출→구조분석→KG생성 자동 연계
- **🔥 Memgraph Knowledge Graph**: 도메인별 지식 그래프 자동 생성 및 그래프 DB 저장 **NEW!**
- **🎯 도메인 특화 KG**: 기술/학술/비즈니스/법률 문서별 최적화된 엔티티/관계 **NEW!**
- **🔗 구체적 관계 추론**: RELATED_TO → IMPLEMENTS/CITES/COMPETES_WITH 등 **NEW!**
- **🏗️ 문서 구조 분석**: 헤더, 테이블, 이미지 등 구조 요소 완전 분석
- **💾 완전한 파일 저장 시스템**: 파서별 개별 결과 + 종합 결과 모두 저장
- **다중 파일 형식 지원**: PDF, DOCX, HTML, Markdown, TXT, ZIP 자동 추출
- **다중 키워드 추출기**: KeyBERT, spaCy NER, LLM(Ollama), KoNLPy
- **🎯 Dublin Core 메타데이터 시스템**: 국제 표준 메타데이터 스키마 완전 준수
- **🔍 Docling 파서**: 고급 PDF 구조 추출 (테이블, 섹션, 이미지)
- **📊 로컬 분석 API**: 프로젝트 없이 직접 파일 분석 가능
- **🐛 고급 디버그 로깅 시스템**: 모든 추출 과정의 중간 결과물을 상세 기록 및 분석
- **실시간 LLM 연동**: Ollama 서버와 완전 통합, 동적 모델 로딩
- **spaCy 모델 자동 관리**: 모델 자동 다운로드, 설치 상태 확인, 테스트 기능
- **고급 키워드 관리**: 키워드 중심/문서 중심 뷰, 추출기별 필터링
- **설정 관리 UI**: 탭 기반 추출기별 설정 관리, 드롭다운 모델 선택
- **프로젝트 관리**: 생성, 수정, 삭제, 파일 업로드/삭제
- **지능형 파싱 관리**: 업로드 시 파싱 비활성화, 키워드 추출 시 자동 파싱
- **추출기별 키워드 관리**: 재분석 시 기존 키워드 자동 삭제 후 재추출
- **실시간 상태 표시**: 파싱 상태, 연결 테스트, 오류 메시지
- **정확한 진행률 추적**: 파일 수 × 추출기 수 기반 상세 진행 표시
- **실제 KeyBERT 모델 로딩**: 14개의 다양한 sentence-transformer 모델 지원
- **KeyBERT 모델 다운로드 관리**: 자동 다운로드, 진행률 표시, 캐시 관리
- **상세한 추출 로깅**: 모든 추출 단계와 결과를 서버 로그에 기록
- **고급 PDF 뷰어**: PDF.js 기반 뷰어로 키워드 하이라이팅 및 페이지 네비게이션
- **리사이징 가능한 UI**: 사이드바 및 키워드 패널 크기 조절 기능
- **전체 키워드 통계**: 모든 프로젝트의 키워드 통합 분석

## 기술 스택
### 백엔드
- Python 3.11+ with Conda Environment
- FastAPI (완전한 RESTful API)
- SQLite with SQLAlchemy ORM (관계형 데이터)
- **Memgraph (그래프 데이터베이스)** - Knowledge Graph 저장 **NEW!**
- PyMuPDF, python-docx, BeautifulSoup4, Docling (문서 파싱)
- KeyBERT, spaCy, sentence-transformers (AI 키워드 추출)
- LangChain, Ollama (LLM 통합)
- KoNLPy (한국어 자연언어처리)

### 프론트엔드  
- React 18 with TypeScript
- Tailwind CSS
- Axios (API 통신)

### 배포 및 실행
- Conda 환경 기반 백엔드 (포트 8000)
- React 개발 서버 (포트 3001)
- **Memgraph 그래프 DB (포트 7687)** - Docker 권장 **NEW!**
- **Memgraph Studio (포트 3000)** - 그래프 시각화 **NEW!**
- Ollama LLM 서버 (포트 11434)
- 자동화된 스크립트 (scripts/ 디렉토리)

## 시스템 아키텍처 (완성됨)

### API 엔드포인트
#### 프로젝트 관리
- `GET /projects/` - 프로젝트 목록 조회
- `POST /projects/` - 프로젝트 생성
- `PUT /projects/{id}` - 프로젝트 이름 수정
- `DELETE /projects/{id}` - 프로젝트 삭제
- `GET /projects/{id}/files` - 프로젝트 파일 목록
- `POST /projects/{id}/upload` - 단일 파일 업로드
- `POST /projects/{id}/upload_bulk` - 다중 파일 업로드
- `POST /projects/{id}/extract_keywords/` - 키워드 추출

#### 로컬 파일 완전 파싱 (신규)
- `POST /local-analysis/parse` - 모든 파서를 사용한 완전 파싱
- `GET /local-analysis/parse` - 완전 파싱 (GET 방식)
- `GET /local-analysis/parse/status` - 파싱 상태 확인
- `GET /local-analysis/parse/results` - 파싱 결과 조회

#### 고급 문서 분석 (신규)
- `POST /local-analysis/structure-analysis` - 문서 구조 분석
- `GET /local-analysis/structure-analysis` - 구조 분석 (GET 방식)
- `POST /local-analysis/knowledge-graph` - Knowledge Graph 생성
- `GET /local-analysis/knowledge-graph` - KG 조회 (GET 방식)

#### 키워드 관리
- `GET /projects/{id}/keywords/` - 프로젝트 키워드 조회
- `GET /files/{id}/keywords/` - 파일별 키워드 조회

#### 추출기 관리
- `GET /extractors/available` - 사용 가능한 추출기 목록
- `GET /llm/ollama/models` - Ollama 모델 목록
- `POST /llm/test_connection` - LLM 연결 테스트

#### 설정 관리
- `GET /configs/` - 전체 설정 목록
- `GET /configs/{key}` - 단일 설정 조회
- `PUT /configs/{key}` - 설정 값 수정
- `GET /configs/keybert/models` - KeyBERT 모델 목록 조회
- `POST /configs/keybert/models/{model_name}/download` - KeyBERT 모델 다운로드
- `GET /configs/keybert/models/download/progress/{progress_key}` - 다운로드 진행률 스트리밍
- `DELETE /configs/keybert/models/{model_name}/cache` - 모델 캐시 삭제
- `GET /configs/keybert/models/{model_name}/status` - 모델 캐시 상태 확인

#### Memgraph Knowledge Graph API (신규)
- `GET /memgraph/health` - Memgraph 연결 상태 확인
- `GET /memgraph/stats` - 데이터베이스 통계 정보
- `POST /memgraph/insert` - KG 데이터 삽입
- `GET /memgraph/document/{file_path:path}` - 특정 문서 KG 조회
- `GET /memgraph/search/entities` - 엔티티 검색 (타입, 이름, 도메인 필터)
- `POST /memgraph/query` - 사용자 정의 Cypher 쿼리 실행
- `GET /memgraph/export` - KG 데이터 내보내기 (JSON/Cypher)
- `GET /memgraph/graph/visualization` - 그래프 시각화 데이터
- `GET /memgraph/entities/types` - 엔티티 타입 목록
- `GET /memgraph/relationships/types` - 관계 타입 목록
- `DELETE /memgraph/clear` - 데이터베이스 전체 삭제 (관리자 권한)

### 프론트엔드 컴포넌트
- `App.tsx` - 메인 애플리케이션 (리사이저 기능 포함, 완성됨)
- `ProjectForm.tsx` - 프로젝트 생성/관리 (완성됨)
- `FileUploader.tsx` - 파일 업로드 (완성됨)
- `ExtractorTrigger.tsx` - 키워드 추출 실행 (완성됨)
- `KeywordResultViewer.tsx` - 추출 결과 표시 (완성됨)
- `SettingsPanel.tsx` - 시스템 설정 관리 (탭 기반 UI, 완성됨)
- `KeywordManagement.tsx` - 키워드 관리 UI (리사이징 가능한 패널, 완성됨)
- `AdvancedPDFViewer.tsx` - PDF 문서 뷰어 (키워드 하이라이팅 기능, 완성됨)
- `GlobalKeywordManagement.tsx` - 전체 키워드 통계 및 관리 (완성됨)
- `DocumentViewerSimple.tsx` - 문서 뷰어 (다중 형식 지원, 완성됨)

## 데이터베이스 스키마 (완성됨)
- **Project**: 프로젝트 관리 (id, name, created_at)
- **File**: 파일 관리 (id, project_id, filename, filepath, size, content, parse_status, parse_error)
- **KeywordOccurrence**: 키워드 추출 결과 (id, file_id, keyword, extractor_name, score, category, position, context)
- **Config**: 시스템 설정 (key, value, description, updated_at)

## 디렉토리 구조
- main.py: 엔트리 포인트
- db/: 데이터베이스 설정 및 모델 정의
- routers/, services/: 라우팅 및 비즈니스 로직 확장 예정

## 테스트 기준 및 도구
- 테스트 프레임워크: `pytest`
- FastAPI 내장 `TestClient` 사용
- DB는 테스트 시 `sqlite:///:memory:` 사용
- 테스트 파일은 `tests/` 디렉토리에 위치
- 테스트는 `pytest`로 실행 가능해야 함

## 키워드 추출 방식 <!-- SPEC: keyword_extraction --> ✅ 완성됨
- 기본 지원 추출기: `KeyBERT`, `spaCy NER`, `KoNLPy`, `LLM`
- 모든 추출기는 `KeywordExtractor` 인터페이스를 구현해야 하며, 결과에 사용된 추출기의 이름을 명시해야 함
- **LLM 추출기의 경우**, OpenAI 또는 Ollama 등 다양한 LLM 서버와의 연동을 지원
- **프론트엔드에서 추출기 선택 가능**: 사용자는 한 가지 이상을 선택하여 키워드 추출 요청 가능
- 추출 방식의 기본값은 `Config` 테이블의 `DEFAULT_EXTRACTORS`에서 설정
- 선택하는 부분은 가용 목록 중에서 선택하는 방식으로 설정
- **KeyBERT 모델 지원 (완성됨)**:
  - 14개의 sentence-transformer 모델 지원
  - 다국어 모델 5개: all-MiniLM-L6-v2 (추천), paraphrase-multilingual-MiniLM-L12-v2, paraphrase-multilingual-mpnet-base-v2, distiluse-base-multilingual-cased, LaBSE
  - 한국어 최적화 모델 4개: jhgan/ko-sroberta-multitask (추천), jhgan/ko-sbert-nli, BM-K/KoSimCSE-roberta-multitask, snunlp/KR-SBERT-V40K-klueNLI-augSTS
  - 영어 전용 모델 5개: all-mpnet-base-v2, all-distilroberta-v1, all-roberta-large-v1, paraphrase-albert-small-v2, msmarco-distilbert-base-v4
  - 설정에서 드롭다운으로 선택 가능
- **진행률 추적 개선 (완성됨)**:
  - 파일 수 × 추출기 수로 정확한 진행률 계산
  - 실시간 추출 로그 표시
- **KeyBERT 모델 다운로드 관리 (신규 완성됨)**:
  - 자동 모델 다운로드 및 캐시 관리
  - 실시간 다운로드 진행률 표시 (Server-Sent Events)
  - 모델 상태 확인, 캐시 삭제, 재로드 기능
  - 14개 모델별 상세 정보 및 크기 표시
- **상세한 추출 로깅 (신규 완성됨)**:
  - 모든 KeyBERT 추출 단계 로깅 (모델 로드, 설정, 원시 결과, 위치 분석)
  - 추출기별 키워드 결과와 점수 로깅
  - 서버 로그와 프론트엔드 진행률 동기화

## 설정 관리 개발 기준 <!-- SPEC: config_management --> ✅ 완성됨
- 설정 저장: SQLite 내 `Config` 테이블
- 프론트엔드에서 읽고 수정 가능한 API 제공:
  - `GET /configs`: 전체 설정 목록 조회
  - `GET /configs/{key}`: 설정 키 단건 조회
  - `PUT /configs/{key}`: 설정 키의 값 갱신
- **주요 설정 키 (완성됨)**:
  - **LLM 설정**:
    - `OLLAMA_BASE_URL`: Ollama 서버의 base URL
    - `OLLAMA_MODEL`: 사용 모델명 (동적 로딩으로 드롭다운 선택)
    - `OLLAMA_TIMEOUT`: Ollama 요청 타임아웃
    - `ENABLE_LLM_EXTRACTION`: LLM 추출 기능 활성화 여부
  - **KeyBERT 설정**:
    - `KeyBERT_MODEL`: KeyBERT 모델 선택 (14개 모델 중 드롭다운 선택)
    - `KeyBERT_MMR`: MMR (Maximal Marginal Relevance) 사용 여부
    - `extractor.keybert.use_maxsum`: Max Sum Similarity 사용 여부
    - `extractor.keybert.diversity`: MMR 다양성 파라미터 (0.0-1.0)
    - `extractor.keybert.keyphrase_ngram_range`: N-gram 범위 [최소, 최대]
    - `extractor.keybert.stop_words`: 불용어 언어 설정
    - `extractor.keybert.max_keywords`: 최대 키워드 개수
  - **기타 설정**:
    - `DEFAULT_EXTRACTORS`: 기본 추출기 배열
    - `ALLOWED_EXTENSIONS`: 허용 파일 확장자
- **설정 관리 UI (완성됨)**:
  - 탭 기반 추출기별 설정 관리 (KeyBERT, NER, LLM, KoNLPy)
  - 모든 설정을 웹에서 관리 가능
  - Ollama 모델은 서버에서 동적으로 목록을 가져와 드롭다운으로 선택
  - 연결 테스트 기능 포함
  - 실시간 상태 피드백
  - 저장 버튼 방식의 설정 관리 (자동 저장 대신 명시적 저장)
  - 변경사항 표시 및 취소 기능
  - 색상 코딩된 탭과 설정 개수 표시
- **KeyBERT 모델 관리 UI (신규 완성됨)**:
  - 실시간 다운로드 진행률 바 표시
  - 모델 상태 확인 (다운로드됨/필요함)
  - 캐시 삭제 및 재로드 버튼
  - 모델 크기 정보 표시
  - EventSource를 통한 실시간 진행률 업데이트

## 프론트엔드 요구사항 <!-- SPEC: frontend_spec --> ** 수정됨 2025.08.05 **
- 목적: 완전한 문서 키워드 추출 관리 시스템
- 기술 스택: React + TypeScript + Tailwind + Axios
- **완성된 사용 흐름**:
  1. ✅ 프로젝트 생성, 수정, 삭제
  2. ✅ 다중 파일 업로드 (drag & drop 지원)
  3. ✅ 파일별 파싱 상태 확인 및 관리
  4. ✅ 다중 추출기 선택 및 키워드 추출
  5. ✅ 실시간 추출 결과 표시
  6. ✅ 고급 키워드 관리 (키워드 중심/문서 중심 뷰)
  7. ✅ 시스템 설정 관리 (동적 모델 선택 포함)
  8. 문서에 대한 뷰어 기능

- **완성된 컴포넌트**:
  - `App.tsx`: 메인 애플리케이션 라우팅 및 상태 관리
  - `ProjectForm.tsx`: 프로젝트 생성 및 관리
  - `FileUploader.tsx`: 파일 업로드 (단일/다중 지원)
  - `ExtractorTrigger.tsx`: 추출기 선택 및 실행
  - `KeywordResultViewer.tsx`: 추출 결과 표시
  - `SettingsPanel.tsx`: 시스템 설정 관리 (탭 기반 UI, 드롭다운 모델 선택)
  - `KeywordManagement.tsx`: 키워드 관리 UI (키워드/문서 중심 뷰)

- **고급 기능 (완성됨)**:
  - 키워드 중심 뷰: 키워드별로 발견된 문서와 위치 정보 표시
  - 문서 중심 뷰: 문서별로 추출된 키워드 목록 표시
  - 추출기별 필터링 및 색상 구분
  - 실시간 검색 및 필터링
  - 추출기 정보 및 점수 표시

## 배포 가이드 (완성됨)

### 실행 스크립트
- `scripts/start_backend.sh`: 백엔드 실행 (Conda 환경, 포트 8000)
- `scripts/start_frontend.sh`: 프론트엔드 실행 (포트 3001)
- `scripts/start_all.sh`: 백엔드와 프론트엔드 동시 실행

### 실행 방법
```bash
# 백엔드만 실행
./scripts/start_backend.sh

# 프론트엔드만 실행  
./scripts/start_frontend.sh

# 전체 시스템 실행
./scripts/start_all.sh
```

### 환경 요구사항
- Conda (기본 환경명: DocExtract)
- Node.js (React 개발 서버용)
- Python 3.11+ (Conda 환경 내)
- Ollama 서버 (LLM 기능 사용 시)

## KeyBERT 모델 다운로드 및 진행률 관리 <!-- SPEC: keybert_model_management --> ✅ 신규 완성됨

### 기능 개요
- **자동 모델 다운로드**: 설정에서 모델 변경 시 필요한 경우 자동 다운로드
- **실시간 진행률 표시**: Server-Sent Events (SSE)를 통한 실시간 다운로드 진행률
- **캐시 관리**: 모델 상태 확인, 캐시 삭제, 재로드 기능
- **호환성 확보**: huggingface_hub 5.0.0과 sentence-transformers 5.0.0 호환

### 백엔드 구현
- **Progress Tracking**: 전역 `download_progress` 딕셔너리로 실시간 상태 관리
- **SSE 스트리밍**: `/configs/keybert/models/download/progress/{progress_key}` 엔드포인트
- **캐시 감지**: 새로운 huggingface hub 캐시 위치 (`~/.cache/huggingface/hub/`) 지원
- **상세 로깅**: 모든 다운로드 단계별 서버 로그 기록

### 프론트엔드 구현
- **Progress Bar**: Tailwind CSS 기반 애니메이션 진행률 바
- **EventSource**: 실시간 진행률 수신 및 상태 업데이트
- **모델 관리 UI**: 상태 확인, 캐시 삭제, 재로드 버튼
- **사용자 피드백**: 다운로드 완료 시 크기 정보 및 소요 시간 표시

### 진행률 단계
1. **0% - 시작**: "다운로드 준비 중..."
2. **10% - 캐시 확인**: "캐시 상태 확인 중..."
3. **20% - 다운로드**: "모델 다운로드 중... (시간이 걸릴 수 있습니다)"
4. **50% - 초기화**: "모델 초기화 중..."
5. **80% - 검증**: "모델 검증 중..."
6. **90% - 크기 계산**: "캐시 크기 계산 중..."
7. **100% - 완료**: "완료! (소요시간: X초, 크기: XMB)"

## KeyBERT 추출 로깅 시스템 <!-- SPEC: keybert_extraction_logging --> ✅ 신규 완성됨

### 로깅 범위
- **모델 로드**: 모델 변경 감지, 로드 시작/완료, 실패 처리
- **추출 설정**: 알고리즘(MMR/MaxSum/CosineSim), 매개변수, 다양성 설정
- **원시 결과**: KeyBERT가 반환한 키워드와 점수 목록
- **위치 분석**: 텍스트에서 찾은 키워드 위치와 컨텍스트
- **통계 정보**: 총 키워드 수, 위치 있는 키워드와 추상 키워드 분류

### 로깅 예시
```
🔍 KeyBERT 키워드 추출 시작 - 텍스트 길이: 1234 문자
📥 KeyBERT 모델 'all-MiniLM-L6-v2' 로드 시작...
✅ KeyBERT 모델 'all-MiniLM-L6-v2' 로드 성공
⚙️ KeyBERT 설정 - 알고리즘: MMR, 최대키워드: 10, n-gram: (1, 2), 다양성: 0.5
🧠 MMR 알고리즘으로 키워드 추출 중 (다양성: 0.5)...
🔍 KeyBERT 원시 결과 (8개): 인공지능(0.856), 머신러닝(0.743), 딥러닝(0.621)
📍 '인공지능' (점수: 0.856) - 위치: 15-19, 컨텍스트: '현대 기술에서 인공지능과...'
📋 KeyBERT 키워드 처리 완료 - 총 8개 (위치있음: 6, 추상: 2)
✅ KeyBERT 추출 완료 - 8개 키워드, 상위: 인공지능(0.856), 머신러닝(0.743)
```

## 고급 디버그 로깅 시스템 <!-- SPEC: advanced_debug_logging --> 🐛 신규 완성됨 (2025.08.07)

### 시스템 개요
키워드 추출 과정의 모든 중간 결과물을 상세히 기록하고 분석할 수 있는 포괄적인 디버깅 시스템입니다.

### 주요 기능
- **🔄 단계별 추적**: 추출 시작 → 전처리 → 후보생성 → 임베딩 → 유사도계산 → 알고리즘적용 → 위치분석 → 최종결과
- **📁 자동 파일 저장**: 모든 중간 결과물을 JSON/텍스트 파일로 자동 저장
- **📊 HTML 리포트**: 시각적 요약 리포트 자동 생성
- **🎯 추출기별 지원**: KeyBERT, spaCy NER, LLM(Ollama), KoNLPy 모든 추출기 완전 지원
- **⚙️ 환경변수 제어**: `ENABLE_KEYWORD_DEBUG=true`로 간편 활성화

### 수집되는 디버그 정보

#### 1. 추출 시작 (`start_extraction`)
- 파일 정보 (이름, 크기, ID)
- 텍스트 통계 (길이, 단어수, 문장수, 다양성)
- 추출기 설정 및 매개변수

#### 2. 전처리 (`log_preprocessing`)
- 원본 텍스트 vs 정제된 텍스트 비교
- 전처리 단계 기록 (`clean_text`, `normalize_unicode` 등)
- 텍스트 변화율 및 통계

#### 3. 후보 생성 (`log_candidate_generation`)
- 키워드 후보 목록 (상위 50개)
- 생성 방법 (`CountVectorizer_ngram`, `spacy_NER`, `konlpy_nouns` 등)
- 후보 통계 (총 개수, 고유 개수, 평균 길이, 단일어/복합어 비율)

#### 4. 임베딩 계산 (`log_embeddings`)
- 사용된 모델 정보
- 문서 임베딩 및 후보 임베딩 차원
- 임베딩 통계 (평균, 표준편차, 노름)

#### 5. 유사도 계산 (`log_similarity_calculation`)
- 코사인 유사도 또는 빈도 기반 점수 배열
- 유사도 분포 통계 (최소/최대/평균/중앙값)
- 상위/하위 결과 (Top 10, Bottom 5)

#### 6. 알고리즘 적용 (`log_algorithm_application`)
- 사용된 알고리즘 (MMR, Max Sum, Frequency-based)
- 알고리즘 매개변수 (diversity, nr_candidates 등)
- 입력 후보 vs 최종 선택된 키워드
- 제외된 키워드 목록 및 사유

#### 7. 위치 분석 (`log_position_analysis`)
- 각 키워드의 텍스트 내 위치 정보
- 페이지/줄/컬럼 번호 매핑
- 키워드 주변 컨텍스트
- 위치 커버리지 통계

#### 8. 최종 결과 (`log_final_results`)
- 추출된 최종 키워드 목록 (점수, 카테고리, 위치)
- 처리 성능 통계 (추출 시간, 초당 키워드 수)
- 평균 점수 및 분포

### 저장되는 파일 구조
```
debug_logs/
└── 20250807_154520_a1b2c3d4/          # 세션 디렉토리
    ├── debug_session.json              # 전체 세션 데이터
    ├── input_text.txt                  # 입력 텍스트
    ├── keybert_preprocessed.txt         # 전처리된 텍스트
    ├── keybert_candidates.json         # 키워드 후보
    ├── keybert_similarities.json       # 유사도 계산 결과
    ├── keybert_MMR_results.json        # 알고리즘 적용 결과
    ├── keybert_positions.json          # 위치 분석 결과
    ├── keybert_summary.json            # 추출기별 요약
    ├── spacy_ner_candidates.json       # spaCy NER 후보
    ├── llm_summary.json                # LLM 요약
    ├── konlpy_similarities.json        # KoNLPy 유사도
    └── summary_report.html             # 시각적 요약 리포트
```

### 활용 방법

#### 디버그 모드 활성화
```bash
# 환경변수 설정
export ENABLE_KEYWORD_DEBUG=true

# 키워드 추출 실행 시 자동으로 debug_logs/ 에 저장됨
```

#### HTML 리포트 확인
```bash
# 생성된 HTML 리포트 열기
open debug_logs/YYYYMMDD_HHMMSS_SESSION/summary_report.html
```

#### 개별 파일 분석
- `debug_session.json`: 전체 세션의 모든 단계별 데이터
- `*_candidates.json`: 각 추출기별 키워드 후보 분석
- `*_similarities.json`: 유사도/점수 계산 상세 결과
- `*_positions.json`: 키워드 위치 및 컨텍스트 정보

### 성능 영향
- 디버그 모드 비활성화 시: **성능 영향 없음** (모든 로깅 건너뜀)
- 디버그 모드 활성화 시: **약 10-20% 추가 처리 시간** (파일 I/O 포함)

### 보안 및 개인정보
- 디버그 파일은 **로컬에만 저장**됨 (외부 전송 없음)
- 텍스트 내용이 포함되므로 **민감한 문서 처리 시 주의**
- 필요 시 디버그 파일 자동 삭제 기능 구현 가능

## Dublin Core 메타데이터 시스템 <!-- SPEC: dublin_core_metadata --> 🎯 신규 완성됨 (2025.08.28)

### 기능 개요
- **국제 표준 준수**: Dublin Core 메타데이터 표준을 완전히 구현한 문서 메타데이터 시스템
- **스키마 기반 구조**: [metadata-schema.md](docs/metadata-schema.md)에 정의된 엄격한 스키마 준수
- **자동 메타데이터 추출**: 파일 업로드 시 Dublin Core 표준에 따른 메타데이터 자동 생성
- **다중 네임스페이스 지원**: dc:, dcterms:, doc:, processing:, file: 네임스페이스 완전 지원

### 주요 특징
1. **필수 필드 보장**: Dublin Core 필수 7개 필드 자동 생성 (dc:title, dc:identifier, dc:creator, dc:type, dc:format, dc:language, dcterms:created)
2. **스마트 폴백 시스템**: 메타데이터 누락 시 적절한 기본값 자동 제공
3. **타입 정규화**: 문자열→배열, 타임스탬프→ISO 8601 등 자동 변환
4. **언어 감지**: 문서 내용 분석을 통한 자동 언어 코드 설정
5. **고유 식별자 생성**: 파일 ID + UUID 조합으로 전역 고유 식별자 생성

### API 엔드포인트
- `GET /files/{file_id}/metadata` - 직접 파일 메타데이터 접근
- `GET /projects/{project_id}/files/{file_id}/metadata` - 프로젝트 스코프 메타데이터 접근

### 응답 예시
```json
{
  "@context": "http://purl.org/dc/terms/",
  "dc:title": "test_document.txt",
  "dc:identifier": "file-1-adf12f58",
  "dc:creator": "Unknown",
  "dc:type": "Text",
  "dc:format": "text/plain", 
  "dc:language": "ko",
  "dcterms:accessRights": "public",
  "file:name": "test_document.txt",
  "file:size": 1162,
  "dcterms:extent": "1162 bytes",
  "dcterms:medium": "digital",
  "dcterms:isPartOf": "project_1",
  "doc:supported": "yes",
  "processing:parseStatus": "success"
}
```

### 기술 구현
- **DocumentMetadata.to_schema_compliant_dict()**: 스키마 준수 변환 메서드
- **자동 MIME 타입 감지**: 파일 확장자 기반 MIME 타입 자동 매핑
- **Dublin Core 타입 매핑**: 파일 형식을 표준 Dublin Core 타입으로 변환
- **Null 값 필터링**: 응답에서 null 값 자동 제외로 깨끗한 JSON 출력

## 탭 기반 설정 관리 시스템 <!-- SPEC: tab_based_settings --> ✅ 신규 완성됨 (2025.08.04)

### 기능 개요
- **추출기별 설정 분리**: 각 추출기(KeyBERT, NER, LLM, KoNLPy)별로 독립적인 탭 제공
- **색상 코딩**: 탭별 고유 색상으로 시각적 구분 (KeyBERT: 파란색, NER: 초록색, LLM: 보라색, KoNLPy: 주황색)
- **설정 개수 표시**: 각 탭에 해당하는 설정 항목 개수를 뱃지로 표시
- **활성화 상태 표시**: 각 추출기의 활성화/비활성화 상태를 탭 내용에서 확인 가능

### UI 구성 요소
1. **탭 헤더**: 
   - 클릭 가능한 탭 버튼 (KeyBERT, NER, LLM, KoNLPy)
   - 활성 탭은 색상 강조 및 하단 테두리 표시
   - 설정 개수 뱃지 (예: "KeyBERT 5", "LLM 8")

2. **탭 내용**:
   - 선택된 탭에 해당하는 설정만 표시
   - 추출기 활성화 상태 표시 (활성화됨/비활성화됨)
   - 색상 인디케이터로 추출기 구분

3. **기존 기능 유지**:
   - 기본 추출기 설정, Ollama 설정, 파일 설정, 앱 설정은 별도 섹션으로 유지
   - 모든 기존 기능(드롭다운, 연결 테스트, 진행률 표시 등) 완전 호환

### 기술 구현
- **동적 CSS 클래스**: 함수 기반 스타일 헬퍼로 Tailwind CSS 호환성 확보
- **상태 관리**: `activeExtractorTab` 상태로 현재 선택된 탭 추적
- **조건부 렌더링**: 선택된 탭에 따라 해당 설정만 표시

## 지원 파일 포맷 <!-- SPEC: supported_file_formats -->
- `.txt`, `.pdf`, `.docx`, `.html`, `.md` 포맷 지원
- 업로드 시 포맷에 따라 자동 파서 선택
- 내부적으로 모든 문서를 plain text로 변환 후 키워드 추출기(`KeywordExtractor`)에 전달
- 파서는 `services/parser/` 모듈 내 정의
- 허용 확장자 설정은 `Config` 테이블의 `ALLOWED_EXTENSIONS` 항목으로 관리

## Docling 고급 파서 시스템 <!-- SPEC: docling_parser --> 🔍 신규 완성됨 (2025.08.29)

### 개요
Docling은 IBM에서 개발한 고급 문서 파싱 라이브러리로, PDF 파일의 복잡한 구조를 정확하게 추출할 수 있습니다.

### 주요 기능
- **테이블 구조 추출**: PDF 내 테이블을 Markdown 형식으로 정확하게 변환
- **섹션 계층 분석**: 헤딩 레벨과 문서 구조 자동 인식
- **이미지 캡션 추출**: 이미지와 관련된 캡션 텍스트 추출
- **레이아웃 보존**: 원본 문서의 레이아웃 정보 유지

### 사용법
```bash
# 로컬 분석에서 Docling 파서 활성화
curl -X POST "http://localhost:58000/local-analysis/analyze" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "document.pdf", "use_docling": true}'
```

### 구현 특징
- **선택적 활성화**: `use_docling=true` 파라미터로 선택적 사용
- **폴백 시스템**: Docling 실패 시 기본 PDF 파서로 자동 전환
- **성능 고려**: 큰 파일의 경우 처리 시간이 길어질 수 있음
- **호환성 문제**: Pydantic 버전 충돌 시 자동으로 기본 파서 사용

### 알려진 문제
- **Pydantic SerializationInfo 오류**: 라이브러리 버전 간 호환성 문제
- **해결 방법**: 자동 폴백 메커니즘으로 기본 PDF 파서 사용
- **권장 사항**: 중요한 문서 분석 시 `use_docling=false` 명시적 설정

## 지식 그래프 구축 시스템 <!-- SPEC: knowledge_graph --> 🧠 신규 완성됨 (2025.08.29)

### 개요
추출된 키워드 간의 관계를 분석하여 지식 그래프를 구축하고 시각화하는 기능입니다.

### 주요 기능
- **키워드 관계 분석**: 동시 출현 빈도 기반 관계 추출
- **그래프 구축**: 노드(키워드)와 엣지(관계) 생성
- **다양한 내보내기 형식**: JSON, GraphML, DOT 형식 지원
- **통계 정보**: 그래프 메트릭 및 중심성 분석

### API 엔드포인트
- `POST /kg/build` - 지식 그래프 구축
- `GET /kg/export` - 그래프 데이터 내보내기
- `GET /kg/stats` - 그래프 통계 정보

### 구현 위치
- 라우터: `backend/routers/kg.py`
- 서비스: `backend/services/kg_builder.py`

## 로컬 분석 API 시스템 <!-- SPEC: local_analysis_api --> 📊 신규 완성됨 (2025.08.29)

### 개요
프로젝트 생성 없이 로컬 파일 시스템의 문서를 직접 분석할 수 있는 독립적인 API 시스템입니다.

### 주요 기능
- **프로젝트 독립적**: 별도 프로젝트 생성 없이 바로 분석
- **디렉토리 탐색**: 작업 디렉토리 변경 및 파일 탐색
- **실시간 분석**: 즉시 키워드 추출 결과 제공
- **메타데이터 전용 추출**: 키워드 추출 없이 메타데이터만 빠르게 확인
- **다중 추출기 지원**: 여러 키워드 추출기 동시 사용

### 핵심 API
```bash
# 현재 디렉토리 확인
curl "http://localhost:58000/local-analysis/config/current-directory"

# 디렉토리 변경
curl -X POST "http://localhost:58000/local-analysis/config/change-directory" \
  -H "Content-Type: application/json" \
  -d '{"directory": "/path/to/documents"}'

# 파일 분석
curl -X POST "http://localhost:58000/local-analysis/analyze" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "document.pdf", "extractors": ["KeyBERT", "spaCy NER"]}'

# 메타데이터만 추출
curl "http://localhost:58000/local-analysis/metadata?file_path=document.pdf"
```

### 구현 위치
- 라우터: `backend/routers/local_analysis.py`
- 서비스: `backend/services/local_file_analyzer.py`
- 사용법 가이드: `LOCAL_ANALYSIS_USAGE.md`

### 특징
- **상대 경로 기반**: 현재 작업 디렉토리 기준으로 모든 파일 경로 해석
- **결과 파일 저장**: 분석 결과를 `.analysis.json` 파일로 자동 저장
- **Dublin Core 메타데이터**: 국제 표준 메타데이터 함께 제공

## 🔥 Memgraph Knowledge Graph 시스템 <!-- SPEC: memgraph_kg_system --> ✅ 완성됨 (2025.08.30)

### 시스템 개요
DocExtract는 이제 전문 그래프 데이터베이스인 Memgraph를 사용하여 문서에서 추출한 지식을 의미있는 그래프 구조로 저장하고 관리합니다.

### 주요 특징
- **🎯 도메인 자동 감지**: 기술, 학술, 비즈니스, 법률, 일반 문서 자동 분류
- **📊 도메인별 특화 엔티티**: 각 문서 타입에 최적화된 엔티티 타입 생성
- **🔗 구체적 관계 추론**: `RELATED_TO` → `IMPLEMENTS`, `CITES`, `COMPETES_WITH` 등 의미있는 관계
- **🚀 자동 저장**: KG 생성과 동시에 Memgraph DB에 자동 저장
- **🔍 강력한 검색**: Cypher 쿼리를 통한 복잡한 그래프 검색
- **📈 시각화 지원**: Memgraph Studio 및 웹 API를 통한 그래프 시각화

### 도메인별 엔티티 및 관계

#### 기술 문서
**엔티티**: `Technology`, `API`, `Function`, `Class`, `Database`, `Server`, `Framework`, `Tool`
**관계**: `DEPENDS_ON`, `IMPLEMENTS`, `EXTENDS`, `USES`, `CALLS`, `CONNECTS_TO`, `CONFIGURED_BY`

#### 학술 논문
**엔티티**: `Author`, `Institution`, `Research_Method`, `Theory`, `Dataset`, `Experiment`, `Finding`
**관계**: `AUTHORED_BY`, `CITES`, `BUILDS_ON`, `PROVES`, `SUPPORTS`, `USES_METHOD`, `BASED_ON`

#### 비즈니스 문서
**엔티티**: `Company`, `Product`, `Market`, `Stakeholder`, `Process`, `KPI`, `Strategy`
**관계**: `COMPETES_WITH`, `SUPPLIES_TO`, `PARTNERS_WITH`, `MANAGES`, `MEASURES`, `IMPLEMENTS`

### 사용 예시

#### KG 생성 및 자동 저장
```bash
# 문서 분석과 동시에 KG 생성 및 Memgraph 저장
curl -X POST "http://localhost:8000/local-analysis/knowledge-graph" \
  -d '{"file_path": "docs/api_manual.pdf"}'
```

#### 그래프 데이터 조회
```bash
# 특정 문서의 KG 조회
curl "http://localhost:8000/memgraph/document/docs%2Fapi_manual.pdf"

# 엔티티 검색
curl "http://localhost:8000/memgraph/search/entities?entity_type=API&limit=10"

# 시각화 데이터
curl "http://localhost:8000/memgraph/graph/visualization?limit=50"
```

#### Cypher 쿼리 실행
```bash
curl -X POST "http://localhost:8000/memgraph/query" \
  -d '{
    "query": "MATCH (d:Document)-[:RELATED_TO]->(a:API) WHERE a.name CONTAINS \"REST\" RETURN d.title, a.name"
  }'
```

### Memgraph Studio 시각화
- **웹 인터페이스**: http://localhost:3000
- **그래프 시각화**: 노드/관계 색상, 크기, 라벨 커스터마이징
- **대화형 탐색**: 클릭 확장, 필터링, 줌인/줌아웃

### 설치 및 설정
자세한 설치 가이드는 `MEMGRAPH_SETUP.md` 파일을 참고하세요.

```bash
# Docker로 Memgraph 실행
docker run -d -p 7687:7687 -p 3000:3000 --name memgraph memgraph/memgraph-platform

# Python 의존성 설치
pip install neo4j

# DocExtract 백엔드 실행 (자동 연동)
./scripts/start_backend.sh
```

### 통합 워크플로우
1. **문서 업로드** → 파싱
2. **키워드 추출** → 도메인 감지
3. **구조 분석** → 엔티티/관계 추출
4. **KG 생성** → Memgraph 자동 저장
5. **시각화/분석** → Studio 또는 API 조회
