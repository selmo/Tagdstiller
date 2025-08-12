# 📘 프로젝트 명세서

## 프로젝트 목적
문서를 업로드하고 키워드를 추출하는 백엔드 API를 제공하며, 간단한 프론트엔드로 테스트할 수 있는 전체 스택 프로토타입 구현

## 기술 스택 <!-- SPEC: tech_stack -->
- Backend: Python 3.11+, FastAPI, SQLite, SQLAlchemy
- Frontend: React, Tailwind CSS, Axios
- Testing: Pytest, FastAPI TestClient
- 추출기: KeyBERT, spaCy NER, LLM, KoNLPy (한국어 지원시)

## DB 테이블 설계 <!-- SPEC: db_schema -->
- `Project`: id, name, created_at
- `File`: id, project_id, filename, path, uploaded_at, size
- `Keyword`: id, project_id, text, extractor_type
- `KeywordOccurrence`: id, keyword_id, file_id, position (page, line, etc.)
- `Config`: key, value, value_type, updated_at

## 키워드 추출 방식 <!-- SPEC: keyword_extraction --> ✅ 완성됨
- 사용 가능한 추출기: `keybert`, `spacy_ner`, `llm`, `konlpy`
- 모든 추출기는 `KeywordExtractor` 인터페이스 구현 필수
- 각 추출기는 다른 추출기와 동시 선택 가능
- 각 추출기 결과는 `extractor` 필드를 포함
- **LLM 기반 추출기는 Ollama와 연동 가능**
- `Config` 테이블의 `DEFAULT_EXTRACTORS`, `ENABLE_LLM_EXTRACTION` 설정값으로 제어 가능
- 모델 설정은 목록 중에서 선택 (직접 입력 X)
- **진행률 추적 개선 (완성됨)**:
  - 파일 수 × 추출기 수로 정확한 진행률 계산
  - 각 추출기가 각 파일을 처리할 때마다 진행률 업데이트
  - 실시간 추출 로그 표시 (어떤 파일을 처리 중인지)

## 설정 관리 <!-- SPEC: config_management --> ✅ 완성됨
- 설정 저장 위치: SQLite 내 `Config` 테이블
- 엔드포인트:
  - `GET /configs`: 전체 설정 목록
  - `GET /configs/{key}`: 단일 조회
  - `PUT /configs/{key}`: 값 갱신
  - `GET /configs/keybert/models`: KeyBERT 모델 목록 조회 (신규)
  - `POST /configs/keybert/models/{model_name}/download`: KeyBERT 모델 다운로드 (신규)
  - `GET /configs/keybert/models/download/progress/{progress_key}`: 다운로드 진행률 스트리밍 (신규)
  - `DELETE /configs/keybert/models/{model_name}/cache`: 모델 캐시 삭제 (신규)
  - `GET /configs/keybert/models/{model_name}/status`: 모델 캐시 상태 확인 (신규)
  - `GET /llm/ollama/models`: Ollama 서버 모델 목록 (동적 로딩)
  - `POST /llm/test_connection`: LLM 연결 테스트
- **완성된 설정 키**:
  - **LLM 설정**:
    - `OLLAMA_BASE_URL`: Ollama 서버 주소
    - `OLLAMA_MODEL`: 사용할 모델명 (동적 목록에서 선택)
    - `OLLAMA_TIMEOUT`: Ollama 요청 타임아웃
    - `ENABLE_LLM_EXTRACTION`: LLM 추출기 활성화 여부
  - **KeyBERT 설정**:
    - `KeyBERT_ENABLED`: KeyBERT 추출기 활성화 여부
    - `KeyBERT_MODEL`: KeyBERT 모델 선택 (14개 모델 중 선택)
    - `KeyBERT_MMR`: MMR 알고리즘 사용 여부
    - `extractor.keybert.use_maxsum`: MaxSum 알고리즘 사용 여부  
    - `extractor.keybert.diversity`: MMR 다양성 파라미터 (0.0-1.0)
    - `extractor.keybert.keyphrase_ngram_range`: N-gram 범위 [최소, 최대]
    - `extractor.keybert.stop_words`: 불용어 언어 설정
    - `extractor.keybert.max_keywords`: 최대 키워드 개수
  - **기타 설정**:
    - `DEFAULT_EXTRACTORS`: 기본 추출기 배열 (`["keybert", "spacy_ner"]` 등)
    - `ALLOWED_EXTENSIONS`: 허용 파일 확장자
- **모델 선택 방식 (완성됨)**: 
  - Ollama 서버에서 실시간으로 모델 목록을 가져와 드롭다운으로 선택
  - KeyBERT 모델은 14개의 사전 정의된 모델 중 선택 (다국어 5개, 한국어 최적화 4개, 영어 전용 5개)
  - 직접 입력 불가, 안전한 선택 방식만 지원
- **설정 통합**: 기존 `ollama.*` 형식 설정은 `OLLAMA_*` 형식으로 통합 완료
- **KeyBERT 모델 다운로드 관리 (신규 완성됨)**:
  - 자동 모델 다운로드 및 캐시 관리
  - Server-Sent Events를 통한 실시간 진행률 표시 (0% → 100%)
  - 모델 상태 확인 (is_cached, 캐시 크기)
  - 캐시 삭제 및 재로드 기능
  - huggingface_hub 5.0.0 호환성 확보

## 프론트엔드 요구사항 <!-- SPEC: frontend_spec --> **2025.08.07 업데이트**
- 기술 스택: React + TypeScript + Tailwind + Axios
- 화면 구성:
  1. **프로젝트 생성/관리** (`POST /projects`, `PUT /projects/{id}`, `DELETE /projects/{id}`)
  2. **파일 업로드/관리** (`POST /projects/{id}/upload`, `POST /projects/{id}/upload_bulk`, `DELETE /projects/{id}/files/{file_id}`)
  3. **추출기 선택 및 키워드 추출 요청** (`POST /projects/{id}/extract_keywords`)
  4. **키워드 결과 출력** (`GET /projects/{id}/keywords`)
  5. **키워드 관리 UI** (`GET /files/{id}/keywords/`)
  6. **문서 뷰어** - 완성됨
  7. **전체 키워드 통계** - 완성됨
  8. **리사이징 가능한 UI** - 완성됨
- 구성 컴포넌트:
  - `App.tsx` - 메인 애플리케이션 (사이드바 리사이저 포함, 완성됨)
  - `ProjectForm.tsx` - 프로젝트 생성/관리 (완성됨)
  - `FileUploader.tsx` - 파일 업로드 (완성됨)
  - `ExtractorTrigger.tsx` - 추출기 선택/실행 (완성됨)
  - `KeywordResultViewer.tsx` - 추출 결과 표시 (완성됨)
  - `SettingsPanel.tsx` - 시스템 설정 관리 (탭 기반 UI, 완성됨)
  - `KeywordManagement.tsx` - 키워드 관리 UI (리사이징 가능한 패널, 완성됨)
  - `AdvancedPDFViewer.tsx` - PDF 뷰어 (키워드 하이라이팅, 완성됨)
  - `GlobalKeywordManagement.tsx` - 전체 키워드 통계 (완성됨)
  - `DocumentViewerSimple.tsx` - 문서 뷰어 (다중 형식 지원, 완성됨)
- 모든 요청 전에 `/configs` 호출로 동기화 필요
- **완성된 설정 페이지**:
  - `SettingsPanel.tsx` 컴포넌트:
    - **탭 기반 추출기별 설정 관리**: KeyBERT, NER, LLM, KoNLPy 탭으로 구분
    - **색상 코딩**: 탭별 고유 색상 (파란색, 초록색, 보라색, 주황색)
    - **설정 개수 표시**: 각 탭의 설정 항목 개수를 뱃지로 표시
    - **추출기 상태 표시**: 활성화/비활성화 상태 표시
    - Ollama 모델 동적 로딩 (드롭다운 선택)
    - KeyBERT 모델 선택 (14개 모델 중 드롭다운 선택, 카테고리별 optgroup)
    - 연결 테스트 기능 (`POST /llm/test_connection`)
    - 실시간 상태 피드백
    - 모델별 추천 안내 표시
- **신규 완성된 키워드 관리 UI**:
  - `KeywordManagement.tsx` 컴포넌트:
    - **키워드 중심 뷰**: 키워드별로 해당 키워드가 발견된 문서 및 위치 정보 표시
    - **문서 중심 뷰**: 문서별로 추출된 키워드 목록 표시
    - **추출기별 필터링**: 특정 추출기로 추출된 키워드만 필터링
    - **검색 기능**: 키워드 이름으로 실시간 검색
    - **상세 정보 표시**: 점수, 카테고리, 컨텍스트, 위치 정보
    - **색상 구분**: 추출기별, 카테고리별 색상으로 구분
- **문서 뷰어 UI**:
  - 문서 관리 UI와, 키워드 UI에서 선택한 문서를 표시
  - 원래의 형식 : PDF, Word 등 화면 표시 형식이 있는 문서
  - 추출된 키워드의 경우, 그 키워드가 있는 위치를 보여주어야 한다.
  - 선택한 키워드는 해당 문서에서 컬러링 해서 보여준다.


## 테스트 정책 <!-- SPEC: testing_policy -->
- 디렉토리: `/backend/tests`
- 커버 범위:
  - 프로젝트 생성, 중복 방지
  - 파일 업로드/조회
  - 키워드 추출 API 결과 구조
  - 설정 조회/수정
- 실행: `pytest`
- DB: `sqlite:///:memory:` in test environment

## 지원 파일 포맷 <!-- SPEC: supported_file_formats -->
- `.txt`: 일반 텍스트
- `.pdf`: PDF 문서 (예: PyMuPDF, pdfminer 사용)
- `.docx`: Microsoft Word (python-docx 기반)
- `.html`: HTML 파일 (BeautifulSoup 등 활용)
- `.md`: Markdown 문서 (텍스트로 처리 또는 HTML로 렌더링 후 파싱)

### 처리 방식
- 파일 업로드 후 확장자 또는 MIME 타입 기반으로 파서가 자동 선택됩니다
- 모든 파서는 내부적으로 문서 내용을 **plain text**로 변환한 뒤 키워드 추출기에 전달합니다
- 추출기는 `KeywordExtractor` 인터페이스를 따르며, 추출 시 원본 파일명, 위치 메타데이터와 함께 키워드를 저장합니다
- 설정 파일 또는 `Config` 테이블을 통해 **허용 포맷 목록 설정 및 확장 가능** (`ALLOWED_EXTENSIONS` 등)

## 키워드 관리 UI 명세 <!-- SPEC: keyword_management_ui --> ✅ 완성됨

### KeywordManagement 컴포넌트
#### 기본 구조
- **파일 위치**: `frontend/src/components/KeywordManagement.tsx`
- **용도**: 추출된 키워드를 체계적으로 관리하고 분석하는 고급 UI
- **접근 방법**: 프로젝트 선택 후 헤더의 "📊 키워드 관리" 버튼으로 접근

#### 주요 기능
1. **듀얼 뷰 시스템**:
   - **키워드 중심 뷰**: 키워드별로 해당 키워드를 포함하는 문서들과 위치 정보 표시
   - **문서 중심 뷰**: 문서별로 추출된 키워드 목록 표시

2. **키워드 중심 뷰 상세**:
   - 키워드 목록: 총 발생 횟수, 최대 점수, 추출기 정보 표시
   - 키워드 선택 시: 해당 키워드가 발견된 모든 문서와 상세 위치 정보
   - 컨텍스트 표시: 키워드 주변 텍스트 스니펫
   - 추출기별 색상 구분: keybert(파란색), spacy_ner(보라색), llm(초록색), konlpy(분홍색)

3. **문서 중심 뷰 상세**:
   - 문서 목록: 각 문서에서 추출된 키워드 개수와 사용된 추출기 표시
   - 문서 선택 시: 해당 문서에서 추출된 모든 키워드 상세 정보
   - 키워드별 점수, 카테고리, 위치 정보 표시

4. **검색 및 필터링**:
   - 실시간 키워드 검색
   - 추출기별 필터링 (전체/keybert/spacy_ner/llm/konlpy)
   - 카테고리별 색상 구분 (PERSON, ORG, LOC 등)

#### API 연동
- `GET /projects/{id}/files`: 프로젝트 파일 목록 조회
- `GET /files/{id}/keywords/`: 파일별 키워드 조회
- 데이터 구조: `KeywordOccurrence[]` 배열로 키워드 정보 수신

#### 데이터 구조
```typescript
interface KeywordWithFiles {
  keyword: string;
  totalOccurrences: number;
  extractors: string[];
  files: {
    file: UploadedFile;
    occurrences: KeywordOccurrence[];
  }[];
  categories: string[];
  maxScore: number;
}
```

#### UI/UX 특징
- 모달 형태로 전체 화면 커버
- 반응형 그리드 레이아웃 (모바일/데스크톱 대응)
- 스크롤 가능한 목록과 상세 뷰
- 색상 코딩으로 추출기와 카테고리 구분
- 로딩 상태 및 빈 상태 처리

## KeyBERT 모델 지원 <!-- SPEC: keybert_models --> ✅ 완성됨

### 지원 모델 목록 (총 14개)

#### 다국어 모델 (5개)
1. **all-MiniLM-L6-v2** 🌟 추천
   - 설명: 빠르고 효율적인 다국어 모델 (384 차원)
   - 크기: Small (~90MB)
   - 지원 언어: 영어, 한국어, 중국어, 일본어 등 100개 이상
   - 속도: 빠름
   - 품질: 좋음

2. **paraphrase-multilingual-MiniLM-L12-v2**
   - 설명: 다국어 패러프레이즈 모델 (384 차원)
   - 크기: Medium (~420MB)
   - 지원 언어: 한국어 포함 50개 이상
   - 속도: 보통
   - 품질: 매우 좋음

3. **paraphrase-multilingual-mpnet-base-v2**
   - 설명: 고품질 다국어 모델 (768 차원)
   - 크기: Large (~1.1GB)
   - 지원 언어: 한국어 포함 50개 이상
   - 속도: 느림
   - 품질: 우수

4. **distiluse-base-multilingual-cased**
   - 설명: 다국어 DistilUSE 모델 (512 차원)
   - 크기: Medium (~500MB)
   - 지원 언어: 한국어 포함 15개 언어
   - 속도: 빠름
   - 품질: 좋음

5. **sentence-transformers/LaBSE**
   - 설명: 언어 중립적 BERT 문장 임베딩
   - 크기: Large (~1.9GB)
   - 지원 언어: 한국어 포함 109개 이상
   - 속도: 느림
   - 품질: 우수

#### 한국어 최적화 모델 (4개)
1. **jhgan/ko-sroberta-multitask** 🌟 추천
   - 설명: 한국어 최적화 SBERT 모델
   - 크기: Medium (~400MB)
   - 지원 언어: 한국어, 영어
   - 속도: 보통
   - 품질: 한국어 우수

2. **jhgan/ko-sbert-nli**
   - 설명: 한국어 SBERT 의미 유사도 모델
   - 크기: Medium (~400MB)
   - 지원 언어: 한국어
   - 속도: 보통
   - 품질: 한국어 매우 좋음

3. **BM-K/KoSimCSE-roberta-multitask**
   - 설명: 한국어 SimCSE 의미 유사도 모델
   - 크기: Medium (~420MB)
   - 지원 언어: 한국어
   - 속도: 보통
   - 품질: 한국어 우수

4. **snunlp/KR-SBERT-V40K-klueNLI-augSTS**
   - 설명: KLUE NLI와 증강 STS로 학습된 한국어 SBERT
   - 크기: Medium (~400MB)
   - 지원 언어: 한국어
   - 속도: 보통
   - 품질: 한국어 매우 좋음

#### 영어 전용 모델 (5개)
1. **all-mpnet-base-v2**
   - 설명: 고성능 영어 모델 (768 차원)
   - 크기: Large (~420MB)
   - 지원 언어: 영어
   - 속도: 보통
   - 품질: 우수

2. **all-distilroberta-v1**
   - 설명: DistilRoBERTa 기반 빠른 영어 모델
   - 크기: Medium (~290MB)
   - 지원 언어: 영어
   - 속도: 빠름
   - 품질: 좋음

3. **all-roberta-large-v1**
   - 설명: 고정확도를 위한 대형 RoBERTa 모델
   - 크기: Large (~1.4GB)
   - 지원 언어: 영어
   - 속도: 느림
   - 품질: 우수

4. **paraphrase-albert-small-v2**
   - 설명: 패러프레이즈 감지용 소형 ALBERT 모델
   - 크기: Small (~40MB)
   - 지원 언어: 영어
   - 속도: 매우 빠름
   - 품질: 좋음

5. **msmarco-distilbert-base-v4**
   - 설명: MS MARCO 데이터셋으로 학습된 DistilBERT
   - 크기: Medium (~260MB)
   - 지원 언어: 영어
   - 속도: 빠름
   - 품질: 매우 좋음

### 선택 가이드
- **한국어 문서**: `jhgan/ko-sroberta-multitask` 사용 권장
- **다국어 문서**: 속도 우선시 `all-MiniLM-L6-v2`, 품질 우선시 `paraphrase-multilingual-mpnet-base-v2`
- **영어 문서**: `all-mpnet-base-v2` 사용 권장

## 탭 기반 설정 UI 명세 <!-- SPEC: tab_based_settings_ui --> ✅ 완성됨 (2025.08.04)

### 개요
추출기별 설정을 효율적으로 관리하기 위해 탭 기반 인터페이스를 도입했습니다. 기존 수직 스택 방식에서 탭 방식으로 변경하여 사용자 경험을 개선했습니다.

### 탭 구성
1. **KeyBERT 탭** (파란색)
   - KeyBERT 관련 모든 설정 (`extractor.keybert.*`)
   - 모델 선택, 알고리즘 설정, 매개변수 조정
   - 모델 다운로드 및 캐시 관리 기능

2. **NER 탭** (초록색)
   - spaCy NER 관련 설정 (`extractor.ner.*`)
   - 모델 선택, 엔티티 타입 설정

3. **LLM 탭** (보라색)
   - LLM 관련 설정 (`extractor.llm.*`, `LLM_PROVIDER` 등)
   - 프롬프트, 온도, 최대 토큰 수 등

4. **KoNLPy 탭** (주황색)
   - 한국어 NLP 관련 설정 (`extractor.konlpy.*`)
   - 분석기 선택, 품사 태깅 옵션

### UI 특징
- **색상 코딩**: 각 탭은 고유 색상으로 구분
- **설정 개수 표시**: 각 탭에 포함된 설정 항목 수를 뱃지로 표시
- **활성화 상태**: 각 추출기의 활성화/비활성화 상태를 명시적으로 표시
- **빈 상태 처리**: 설정이 없는 탭의 경우 안내 메시지 표시

### 기술 구현
- **상태 관리**: `activeExtractorTab` 상태로 현재 선택된 탭 추적
- **동적 스타일링**: 함수 기반 CSS 클래스 생성으로 Tailwind 호환성 확보
- **조건부 렌더링**: 선택된 탭에 따른 설정 필터링 및 표시
- **기존 호환성**: 모든 기존 설정 관리 기능과 완전 호환

