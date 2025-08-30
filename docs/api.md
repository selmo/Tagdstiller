# DocExtract Backend API Documentation

## 🚀 개요

DocExtract 백엔드는 문서 키워드 추출 시스템을 위한 RESTful API를 제공합니다.  
기본 URL: `http://localhost:58000` (로컬 개발용)

**포트 정보:**
- 백엔드 API: 포트 8001
- 프론트엔드: 포트 3001

## 📋 목차

- [프로젝트 관리 API](#프로젝트-관리-api)
- [파일 관리 API](#파일-관리-api)
- [키워드 추출 API](#키워드-추출-api)
- [설정 관리 API](#설정-관리-api)
- [모델 관리 API](#모델-관리-api)
- [프롬프트 템플릿 API](#프롬프트-템플릿-api)
- [로컬 분석 API](#로컬-분석-api)
- [관리자 API](#관리자-api)

---

## 프로젝트 관리 API

### 프로젝트 CRUD 작업

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/projects/` | 새 프로젝트 생성 |
| `GET` | `/projects/` | 모든 프로젝트 목록 조회 |
| `GET` | `/projects/{project_id}` | 특정 프로젝트 조회 |
| `PUT` | `/projects/{project_id}` | 프로젝트 정보 수정 |
| `DELETE` | `/projects/{project_id}` | 프로젝트 삭제 |

### 프로젝트 통계

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/projects/statistics/global` | 전체 키워드 통계 |
| `GET` | `/projects/{project_id}/statistics` | 특정 프로젝트 키워드 통계 |
| `POST` | `/projects/statistics/refresh` | 통계 캐시 새로고침 |
| `DELETE` | `/projects/statistics/cache` | 통계 캐시 삭제 |

---

## 파일 관리 API

### 파일 업로드 및 관리

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/projects/{project_id}/upload` | 단일 파일 업로드 |
| `POST` | `/projects/{project_id}/upload_bulk` | 다중 파일 업로드 (ZIP 지원) |
| `GET` | `/projects/{project_id}/files` | 프로젝트 파일 목록 |
| `DELETE` | `/projects/{project_id}/files/{file_id}` | 파일 삭제 |

### 파일 처리

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/projects/{project_id}/files/{file_id}/reparse` | 파일 재파싱 |
| `GET` | `/projects/{project_id}/files/{file_id}/analyze` | 파일 분석 정보 |
| `GET` | `/projects/{project_id}/files/{file_id}/content` | 파일 텍스트 내용 |

### 파일 메타데이터 (🎯 스키마 준수)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/files/{file_id}/metadata` | 파일 메타데이터 조회 (직접 접근) |
| `GET` | `/projects/{project_id}/files/{file_id}/metadata` | 프로젝트 내 파일 메타데이터 조회 |

#### 메타데이터 응답 예시 (Dublin Core 표준 준수)

**✨ 2025-08-28 업데이트**: 메타데이터 응답이 [metadata-schema.md](./metadata-schema.md) 규격을 완전히 준수하도록 개선되었습니다.

```json
{
  "@context": "http://purl.org/dc/terms/",
  
  // 필수 필드 (Dublin Core)
  "dc:title": "test_document.txt",
  "dc:identifier": "file-1-adf12f58",
  "dc:creator": "Unknown", 
  "dc:type": "Text",
  "dc:format": "text/plain",
  "dc:language": "ko",
  
  // 선택 필드 (Dublin Core)
  "dc:subject": ["인공지능", "머신러닝", "딥러닝"],
  "dc:description": "인공지능과 머신러닝 기술의 발전에 관한 문서",
  
  // Dublin Core Terms 확장
  "dcterms:created": "2025-08-27T14:03:45+09:00",
  "dcterms:modified": "2025-08-27T14:03:45+09:00",
  "dcterms:accessRights": "public",
  "dcterms:extent": "1162 bytes",
  "dcterms:medium": "digital",
  "dcterms:alternative": "test_document.txt",
  "dcterms:isPartOf": "project_1",
  "dcterms:hasFormat": ".txt",
  
  // 파일 정보
  "file:name": "test_document.txt",
  "file:size": 1162,
  
  // 문서 특정 정보
  "doc:pageCount": 1,
  "doc:wordCount": 112,
  "doc:characterCount": 557,
  "doc:supported": "yes",
  
  // 처리 정보
  "processing:parserName": "txt_parser_basic",
  "processing:parserVersion": "1.0",
  "processing:extractionDate": "2025-08-28T02:01:20.771729",
  "processing:appVersion": "1.0.0",
  "processing:parseStatus": "success"
}
```

#### 🌟 주요 특징

- **Dublin Core 표준 준수**: 국제 표준 메타데이터 스키마 완전 구현
- **스마트 폴백**: 메타데이터 누락 시 자동으로 적절한 기본값 생성
- **자동 타입 변환**: 문자열 → 배열, 타임스탬프 → ISO 8601 자동 변환
- **다중 네임스페이스**: dc:, dcterms:, doc:, processing:, file: 네임스페이스 지원
- **Null 값 제외**: null 또는 빈 문자열 값은 응답에서 자동 제외
- **고유 식별자**: 파일 ID + UUID 조합으로 고유 식별자 자동 생성

#### 지원 파일 형식별 메타데이터
- **PDF**: 페이지 수, 작성자, 생성일, 언어 감지
- **DOCX**: 작성자, 제목, 생성/수정일, 언어 감지  
- **TXT/HTML/MD**: 언어 감지, 문자/단어 수 계산
- **모든 형식**: 파일 크기, MIME 타입, 처리 상태

### 파일 다운로드 및 기타

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/files/{file_id}/download` | 파일 다운로드 |
| `GET` | `/files/{file_id}/content` | 파일 내용 조회 (직접 접근) |
| `GET` | `/files/supported-formats` | 지원 파일 형식 목록 |

---

## 키워드 추출 API

### 키워드 추출 실행

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/projects/{project_id}/extract_keywords` | 프로젝트 키워드 추출 |
| `POST` | `/files/{file_id}/extract_keywords` | 단일 파일 키워드 추출 |

### 키워드 조회

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/projects/{project_id}/keywords` | 프로젝트 키워드 목록 |
| `GET` | `/files/{file_id}/keywords` | 파일 키워드 목록 |
| `GET` | `/keywords/list` | 전체 키워드 목록 |
| `GET` | `/keywords/statistics` | 키워드 통계 |

### 추출기 관리

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/extractors/available` | 사용 가능한 추출기 목록 |
| `GET` | `/llm/test_connection` | LLM 연결 테스트 |
| `GET` | `/llm/ollama/models` | Ollama 모델 목록 |

---

## 설정 관리 API

### 기본 설정

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/configs/` | 전체 설정 목록 |
| `GET` | `/configs/{key}` | 특정 설정 조회 |
| `PUT` | `/configs/{key}` | 설정 값 수정 |
| `POST` | `/configs/` | 새 설정 생성 |
| `DELETE` | `/configs/{key}` | 설정 삭제 |

---

## 모델 관리 API

### KeyBERT 모델 관리

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/configs/keybert/models` | KeyBERT 모델 목록 |
| `POST` | `/configs/keybert/models/{model_name}/download` | 모델 다운로드 |
| `GET` | `/configs/keybert/models/download/progress/{progress_key}` | 다운로드 진행률 (SSE) |
| `GET` | `/configs/keybert/models/{model_name}/status` | 모델 상태 확인 |
| `DELETE` | `/configs/keybert/models/{model_name}/cache` | 모델 캐시 삭제 |

### spaCy 모델 관리

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/configs/spacy/models` | spaCy 모델 목록 |
| `POST` | `/configs/spacy/models/{model_name}/download` | spaCy 모델 다운로드 |
| `GET` | `/configs/spacy/models/download/progress/{progress_key}` | 다운로드 진행률 (SSE) |
| `GET` | `/configs/spacy/models/{model_name}/status` | spaCy 모델 상태 |

### spaCy 모델 전용 API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/spacy_models/available` | 사용 가능한 spaCy 모델 |
| `GET` | `/spacy_models/installed` | 설치된 spaCy 모델 |
| `GET` | `/spacy_models/info/{model_name}` | 모델 상세 정보 |
| `POST` | `/spacy_models/download` | 모델 다운로드 |
| `POST` | `/spacy_models/test` | 모델 테스트 |
| `GET` | `/spacy_models/recommended` | 추천 모델 |

---

## 프롬프트 템플릿 API

### 템플릿 관리

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/prompts/templates` | 모든 템플릿 카테고리 |
| `GET` | `/prompts/templates/{category}` | 카테고리별 템플릿 목록 |
| `GET` | `/prompts/templates/{category}/{template_name}` | 특정 템플릿 조회 |
| `POST` | `/prompts/templates/custom` | 커스텀 템플릿 생성 |
| `POST` | `/prompts/templates/test` | 템플릿 테스트 |

### 템플릿 정보

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/prompts/categories` | 템플릿 카테고리 목록 |
| `GET` | `/prompts/variables/{category}` | 카테고리별 사용 가능한 변수 |

---

## 로컬 분석 API

### ⚠️ 중요: 자주 발생하는 실수와 해결법

#### 1. 현재 디렉토리 확인 시
```bash
# ❌ 잘못된 방법 (POST 사용)
curl -X POST "http://localhost:58000/local-analysis/config/current-directory"
# 오류: {"detail":"Method Not Allowed"}

# ✅ 올바른 방법 (GET 사용)
curl "http://localhost:58000/local-analysis/config/current-directory"
```

#### 2. 디렉토리 변경 시
```bash
# ❌ 잘못된 방법 ("path" 키 사용)
curl -X POST "http://localhost:58000/local-analysis/config/change-directory" \
  -H "Content-Type: application/json" \
  -d '{"path": "/Users/selmo/Documents"}'
# 오류: {"detail":"디렉토리 경로가 필요합니다"}

# ✅ 올바른 방법 ("directory" 키 사용)
curl -X POST "http://localhost:58000/local-analysis/config/change-directory" \
  -H "Content-Type: application/json" \
  -d '{"directory": "/Users/selmo/Documents"}'
```

#### 3. GET 방식 추출기 지정 시
```bash
# ❌ 잘못된 방법 (여러 파라미터 사용)
curl "http://localhost:58000/local-analysis/analyze?file_path=doc.pdf&extractors=KeyBERT&extractors=spaCy%20NER"

# ✅ 올바른 방법 (쉼표로 구분)
curl "http://localhost:58000/local-analysis/analyze?file_path=doc.pdf&extractors=KeyBERT,spaCy%20NER"
```

### 파일 분석

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/local-analysis/analyze` | 로컬 파일 분석 (경로 지정) |
| `GET` | `/local-analysis/analyze` | 파일 분석 (파라미터로 경로) |
| `GET` | `/local-analysis/metadata` | 메타데이터만 추출 (키워드 추출 없이) |
| `POST` | `/local-analysis/metadata` | 메타데이터만 추출 (POST 방식) |
| `GET` | `/local-analysis/status` | 분석 상태 확인 |
| `GET` | `/local-analysis/result` | 분석 결과 조회 |
| `POST` | `/local-analysis/reanalyze` | 재분석 실행 |

#### 🆕 Docling 파서 옵션 (2025.08.29)

PDF 파일 분석 시 고급 Docling 파서를 선택적으로 사용할 수 있습니다:

```bash
# 기본 파서 사용 (빠른 처리)
curl "http://localhost:58000/local-analysis/analyze?file_path=document.pdf"

# Docling 파서 사용 (테이블, 섹션 구조 추출)
curl "http://localhost:58000/local-analysis/analyze?file_path=document.pdf&use_docling=true"
```

**Docling 파서 특징:**
- 테이블 구조 추출 및 Markdown 변환
- 섹션 구조 분석 (헤딩, 계층)
- 이미지 위치 및 캡션 정보
- ⚠️ 큰 PDF 파일의 경우 처리 시간이 길어질 수 있음

**🛠️ 알려진 문제 및 해결방법:**
- **Pydantic 호환성 문제**: `SerializationInfo` 오류가 발생할 수 있습니다
- **자동 폴백**: 오류 발생 시 기본 PDF 파서로 자동 전환됩니다

**실제 오류 로그 예시:**
```
ERROR - PDFDocling 파싱 실패: Error calling function '_serialize': 
AttributeError: 'pydantic_core._pydantic_core.SerializationInfo' object has no attribute 'context'
WARNING - ⚠️ Pydantic 버전 호환성 문제가 감지되었습니다. 기본 PDF 파서를 사용합니다.
```

**해결방법**: 
```bash
# Docling 최신 버전으로 업데이트
pip install --upgrade docling docling-core

# 또는 호환 가능한 Pydantic 버전 사용  
pip install pydantic>=2.5.0,<2.6.0
```

**대안**: 
- `use_docling=false`로 기본 파서 강제 사용 가능
- 시스템이 자동으로 폴백 파서를 사용하므로 분석은 정상적으로 완료됩니다

#### 🔍 지식 그래프 구축 API (신규)

문서에서 추출된 키워드를 기반으로 지식 그래프를 구축할 수 있습니다:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/kg/build-from-metadata` | 메타데이터 파일에서 지식 그래프 구축 |

**요청 예시:**
```bash
curl -X POST "http://localhost:58000/kg/build-from-metadata" \
  -H "Content-Type: application/json" \
  -d '{"metadata_path": "/path/to/document.json", "save_files": true}'
```

### 디렉토리 관리

| Method | Endpoint | Description | 요청 형식 |
|--------|----------|-------------|---------|
| `GET` | `/local-analysis/config/root` | 루트 디렉토리 조회 | - |
| `GET` | `/local-analysis/config/current-directory` | 현재 디렉토리 조회 | - |
| `POST` | `/local-analysis/config/change-directory` | 디렉토리 변경 | `{"directory": "경로"}` |
| `POST` | `/local-analysis/config/change-directory-and-list` | 디렉토리 변경 및 목록 | `{"directory": "경로"}` |

### 추출기 설정

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/local-analysis/config/extractors` | 사용 가능한 추출기 목록 |

---

## 관리자 API

### 설정 캐시 관리

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/admin/config/refresh` | 전체 설정 캐시 새로고침 |
| `POST` | `/admin/config/refresh/{key}` | 특정 설정 캐시 새로고침 |
| `GET` | `/admin/config/cache/stats` | 캐시 통계 |
| `GET` | `/admin/config/cache/all` | 전체 캐시 내용 |

---

## 📊 응답 모델

### 공통 응답 형식

```json
{
  "success": true,
  "message": "작업 완료",
  "data": { ... }
}
```

### 오류 응답 형식

```json
{
  "detail": "오류 메시지",
  "status_code": 400
}
```

---

## 🔧 사용 예시

### 1. 프로젝트 생성 및 파일 업로드

```bash
# 프로젝트 생성
curl -X POST "http://localhost:58000/projects/" \
  -H "Content-Type: application/json" \
  -d '{"name": "테스트 프로젝트"}'

# 파일 업로드 (자동 파싱 활성화)
curl -X POST "http://localhost:58000/projects/1/upload?auto_parse=true" \
  -F "file=@document.pdf"
```

### 2. 키워드 추출 실행

```bash
# 프로젝트 전체 키워드 추출
curl -X POST "http://localhost:58000/projects/1/extract_keywords" \
  -H "Content-Type: application/json" \
  -d '{"extractors": ["KeyBERT", "spaCy NER", "LLM"]}'
```

### 3. 메타데이터 조회

```bash
# 파일 메타데이터 조회
curl "http://localhost:58000/files/1/metadata"

# 프로젝트 내 파일 메타데이터 조회
curl "http://localhost:58000/projects/1/files/1/metadata"
```

### 4. 키워드 결과 조회

```bash
# 프로젝트 키워드 조회
curl "http://localhost:58000/projects/1/keywords"

# 특정 파일 키워드 조회
curl "http://localhost:58000/files/1/keywords"
```

### 5. 로컬 분석 API 사용

```bash
# 현재 디렉토리 확인 (GET 요청)
curl "http://localhost:58000/local-analysis/config/current-directory"

# 디렉토리 변경 (directory 키 사용)
curl -X POST "http://localhost:58000/local-analysis/config/change-directory" \
  -H "Content-Type: application/json" \
  -d '{"directory": "/path/to/your/documents"}'

# 로컬 파일 분석 실행 (POST 방식)
curl -X POST "http://localhost:58000/local-analysis/analyze" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "document.pdf", "extractors": ["KeyBERT", "spaCy NER"]}'

# 로컬 파일 분석 실행 (GET 방식)
curl "http://localhost:58000/local-analysis/analyze?file_path=document.pdf&extractors=KeyBERT&extractors=spaCy%20NER"

# 분석 상태 확인
curl "http://localhost:58000/local-analysis/status"

# 분석 결과 조회
curl "http://localhost:58000/local-analysis/result"

# 재분석 실행
curl -X POST "http://localhost:58000/local-analysis/reanalyze"

# 사용 가능한 추출기 목록 조회
curl "http://localhost:58000/local-analysis/config/extractors"

# 메타데이터만 추출 (키워드 추출 없이)
curl "http://localhost:58000/local-analysis/metadata?file_path=document.pdf"

# 메타데이터 추출 (POST 방식)
curl -X POST "http://localhost:58000/local-analysis/metadata" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "document.pdf"}'
```

---

## 📝 주요 특징

- **완전한 RESTful API**: 표준 HTTP 메서드 사용
- **Dublin Core 메타데이터**: 국제 표준 메타데이터 지원
- **다중 파일 형식**: PDF, DOCX, HTML, Markdown, TXT 지원
- **실시간 진행률**: Server-Sent Events를 통한 실시간 업데이터
- **모델 관리**: KeyBERT, spaCy 모델 자동 다운로드 및 관리
- **캐시 시스템**: 효율적인 성능을 위한 다층 캐시
- **오류 처리**: 상세한 오류 메시지 및 상태 코드
- **로컬 분석**: 프로젝트 없이도 로컬 파일 직접 분석 가능

## 🔍 로컬 분석 API 상세 가이드

### 개요
로컬 분석 API는 프로젝트 생성 없이 로컬 파일 시스템의 문서를 직접 분석할 수 있는 기능을 제공합니다. 개발자나 연구자가 빠른 테스트나 일회성 분석을 수행할 때 유용합니다.

### 주요 기능
- **프로젝트 독립적**: 별도 프로젝트 생성 없이 바로 분석
- **디렉토리 탐색**: 작업 디렉토리 변경 및 파일 탐색
- **실시간 분석**: 즉시 키워드 추출 결과 제공
- **메타데이터 추출**: Dublin Core 표준 메타데이터 함께 제공
- **다중 추출기**: 여러 키워드 추출기 동시 사용 가능

### 작동 원리
1. **현재 디렉토리 기준**: 모든 파일 경로는 현재 작업 디렉토리를 기준으로 해석됩니다
2. **디렉토리 변경**: `/config/change-directory`로 작업 디렉토리를 변경하면 모든 파일 작업이 새 디렉토리 기준으로 수행됩니다
3. **상대 경로 사용**: 파일 분석 시 현재 디렉토리 기준 상대 경로를 사용합니다

### 사용 시나리오

#### 시나리오 1: 단일 문서 빠른 분석
```bash
# 1. 분석할 디렉토리로 이동
curl -X POST "http://localhost:58000/local-analysis/config/change-directory" \
  -H "Content-Type: application/json" \
  -d '{"directory": "/Users/username/Documents"}'

# 2. 문서 분석 실행
curl -X POST "http://localhost:58000/local-analysis/analyze" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "research_paper.pdf", "extractors": ["KeyBERT", "LLM"]}'

# 3. 결과 확인
curl "http://localhost:58000/local-analysis/result"
```

#### 시나리오 2: 여러 추출기로 비교 분석
```bash
# KeyBERT와 spaCy NER, LLM을 모두 사용하여 분석
curl -X POST "http://localhost:58000/local-analysis/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "document.pdf",
    "extractors": ["KeyBERT", "spaCy NER", "LLM", "KoNLPy"]
  }'
```

#### 시나리오 3: GET 방식으로 간단 분석
```bash
# URL 파라미터를 사용한 간단 분석 (쉼표로 구분된 추출기)
curl "http://localhost:58000/local-analysis/analyze?file_path=report.docx&extractors=KeyBERT,spaCy%20NER"
```

#### 시나리오 3-1: 한글 파일명 처리 예제 **NEW!**

**POST 방식 (권장):**
```bash
# 한글 파일명은 POST 방식으로 JSON 내부에 포함하면 안전하게 처리됩니다
curl -X POST "http://localhost:58000/local-analysis/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "연구보고서_2024년도_최종.pdf",
    "extractors": ["KeyBERT", "spaCy NER", "LLM"],
    "use_docling": true
  }'

# 경로에 한글이 포함된 경우
curl -X POST "http://localhost:58000/local-analysis/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "한글폴더/재무제표_분석_리포트.docx",
    "extractors": ["KeyBERT", "spaCy NER"]
  }'
```

**GET 방식 (URL 인코딩 필요):**
```bash
# 한글 파일명을 URL 인코딩하여 처리
curl "http://localhost:58000/local-analysis/analyze?file_path=%EC%97%B0%EA%B5%AC%EB%B3%B4%EA%B3%A0%EC%84%9C_2024%EB%85%84%EB%8F%84_%EC%B5%9C%EC%A2%85.pdf&extractors=KeyBERT,spaCy%20NER"

# 또는 curl의 --data-urlencode 옵션 사용
curl -G "http://localhost:58000/local-analysis/analyze" \
  --data-urlencode "file_path=연구보고서_2024년도_최종.pdf" \
  --data-urlencode "extractors=KeyBERT,spaCy NER"
```

**디렉토리 변경 시 한글 경로 처리:**
```bash
# 한글 디렉토리 경로 설정
curl -X POST "http://localhost:58000/local-analysis/config/change-directory" \
  -H "Content-Type: application/json" \
  -d '{"directory": "/Users/사용자명/문서/프로젝트폴더"}'

# 변경 후 한글 파일명으로 분석
curl -X POST "http://localhost:58000/local-analysis/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "회의록_2024_12월.docx",
    "extractors": ["KeyBERT", "KoNLPy"]
  }'
```

**✅ 권장사항:**
- 한글 파일명은 **POST 방식**을 사용하는 것이 안전합니다
- JSON 내부에서는 한글이 자동으로 UTF-8로 처리됩니다
- GET 방식 사용 시 URL 인코딩이 필수입니다

**🧪 테스트된 파일명 예시:**
- `[별첨] 지방은행의 시중은행 전환시 인가방식 및 절차.pdf` ✅
- `★2019 제1회 증시콘서트 자료집_최종★.pdf` ✅
- `한-호주 퇴직연금 포럼_책자(최종).pdf` ✅
- `2. 통화신용정책 운영.pdf` ✅

**⚠️ 주의사항:**
- 파일명에 특수문자(`★`, `[]`, `()` 등)가 포함되어도 정상 처리됩니다
- 한글과 영문이 혼합된 파일명도 지원됩니다
- 공백과 언더스코어(`_`)도 문제없이 처리됩니다

#### 시나리오 4: 메타데이터만 빠르게 추출
```bash
# 키워드 추출 없이 문서 메타데이터만 빠르게 확인
curl "http://localhost:58000/local-analysis/metadata?file_path=document.pdf"

# 응답 예시:
# {
#   "@context": "http://purl.org/dc/terms/",
#   "dc:title": "Financial Report 2024",
#   "dc:creator": "John Doe",
#   "dc:type": "Text",
#   "dc:format": "application/pdf",
#   "dc:language": "ko",
#   "doc:pageCount": 45,
#   "doc:wordCount": 12340,
#   "file_info": {
#     "absolute_path": "/Users/selmo/Documents/document.pdf",
#     "relative_path": "document.pdf",
#     "size": 2348976,
#     "modified": "2024-03-15T10:30:00",
#     "created": "2024-03-01T09:00:00"
#   },
#   "text_statistics": {
#     "total_characters": 65432,
#     "total_words": 12340,
#     "total_lines": 850,
#     "total_paragraphs": 125
#   }
# }
```

#### 시나리오 5: 실제 사용 예시 (완전한 워크플로우)
```bash
# 1. 현재 작업 디렉토리 확인
curl "http://localhost:58000/local-analysis/config/current-directory"

# 응답 예시:
# {
#   "current_directory": "/Users/selmo/Workspaces/DocExtract/backend",
#   "parent_directory": "/Users/selmo/Workspaces/DocExtract",
#   "contents": {
#     "directories": [...],
#     "files": [...],
#     "total_directories": 5,
#     "total_files": 10
#   }
# }

# 2. 원하는 디렉토리로 변경 (예: RAG 평가 데이터셋 폴더)
curl -X POST "http://localhost:58000/local-analysis/config/change-directory" \
  -H "Content-Type: application/json" \
  -d '{"directory": "/Users/selmo/Workspaces/RAG-Evaluation-Dataset-KO/finance"}'

# 응답:
# {
#   "success": true,
#   "message": "디렉토리가 성공적으로 변경되었습니다",
#   "old_directory": "/Users/selmo/Workspaces/DocExtract/backend",
#   "new_directory": "/Users/selmo/Workspaces/RAG-Evaluation-Dataset-KO/finance"
# }

# 3. 변경된 디렉토리 확인 (파일 목록 포함)
curl "http://localhost:58000/local-analysis/config/current-directory"
# 이제 finance 폴더 내의 PDF 파일들이 보입니다

# 4. 파일 상태 확인 (상대 경로 사용)
curl "http://localhost:58000/local-analysis/status?file_path=KIFVIP2013-10.pdf"

# 5. 파일 분석 실행 (현재 디렉토리의 파일을 상대 경로로 지정)
curl -X POST "http://localhost:58000/local-analysis/analyze" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "KIFVIP2013-10.pdf", "extractors": ["KeyBERT", "spaCy NER"]}'

# 6. 분석 결과 조회
curl "http://localhost:58000/local-analysis/result"

# 7. 분석 결과는 같은 디렉토리에 .analysis.json 파일로도 저장됩니다
# 예: KIFVIP2013-10.pdf.analysis.json
```

### 응답 형식 예시

#### 분석 결과 응답
```json
{
  "success": true,
  "message": "분석 완료",
  "data": {
    "file_info": {
      "filename": "document.pdf",
      "file_size": 1234567,
      "mime_type": "application/pdf"
    },
    "metadata": {
      "@context": "http://purl.org/dc/terms/",
      "dc:title": "Research Paper",
      "dc:creator": "Author Name",
      "dc:type": "Text",
      "dc:format": "application/pdf",
      "dc:language": "ko",
      "doc:pageCount": 15,
      "doc:wordCount": 5234,
      "doc:characterCount": 28456
    },
    "document_structure": {
      "total_pages": 15,
      "sections": [
        {
          "title": "1. 서론",
          "page": 1,
          "level": 1
        },
        {
          "title": "2. 관련 연구",
          "page": 3,
          "level": 1
        },
        {
          "title": "2.1 기존 방법론",
          "page": 4,
          "level": 2
        },
        {
          "title": "3. 제안 방법",
          "page": 6,
          "level": 1
        },
        {
          "title": "4. 실험 결과",
          "page": 10,
          "level": 1
        },
        {
          "title": "5. 결론",
          "page": 14,
          "level": 1
        }
      ],
      "tables_count": 3,
      "figures_count": 8,
      "references_count": 42,
      "footnotes_count": 12
    },
    "text_statistics": {
      "total_sentences": 387,
      "total_paragraphs": 52,
      "avg_words_per_sentence": 13.5,
      "avg_sentences_per_paragraph": 7.4,
      "language_detected": "ko",
      "readability_score": 68.2
    },
    "keywords": [
      {
        "extractor_name": "KeyBERT",
        "keywords": [
          {
            "keyword": "인공지능",
            "score": 0.8756,
            "category": "기술",
            "positions": [
              {
                "page": 1,
                "line": 15,
                "start": 123,
                "end": 127,
                "context": "현대 기술에서 인공지능의 역할은...",
                "section": "1. 서론"
              },
              {
                "page": 6,
                "line": 8,
                "start": 456,
                "end": 460,
                "context": "제안된 인공지능 모델은...",
                "section": "3. 제안 방법"
              }
            ],
            "frequency": 23,
            "distribution": {
              "by_section": {
                "1. 서론": 5,
                "3. 제안 방법": 12,
                "4. 실험 결과": 4,
                "5. 결론": 2
              },
              "by_page": [3, 2, 1, 0, 0, 12, 2, 1, 0, 2, 0, 0, 0, 1, 0]
            }
          }
        ]
      },
      {
        "extractor_name": "spaCy NER",
        "keywords": [
          {
            "keyword": "KAIST",
            "score": 1.0,
            "category": "ORG",
            "entity_type": "ORGANIZATION",
            "positions": [
              {
                "page": 1,
                "start": 234,
                "end": 239,
                "context": "본 연구는 KAIST 연구팀과 협력하여..."
              }
            ]
          }
        ]
      },
      {
        "extractor_name": "LLM",
        "keywords": [
          {
            "keyword": "머신러닝",
            "score": 0.9234,
            "category": "기술",
            "context": "머신러닝 알고리즘의 발전...",
            "reasoning": "문서 전체에서 핵심적으로 다루는 기술 용어"
          }
        ]
      }
    ],
    "analysis_time": 2.34,
    "total_keywords": 15,
    "extraction_summary": {
      "total_extractors_used": 3,
      "successful_extractions": 3,
      "failed_extractions": 0,
      "keywords_by_extractor": {
        "KeyBERT": 6,
        "spaCy NER": 4,
        "LLM": 5
      }
    }
  }
}
```

### 오류 처리
```json
{
  "detail": "파일을 찾을 수 없습니다: document.pdf",
  "status_code": 404
}
```

### 제한사항
- 분석 결과는 메모리에 임시 저장되며 서버 재시작 시 초기화됩니다
- 동시에 하나의 분석만 실행 가능합니다
- 매우 큰 파일(100MB 이상)은 타임아웃될 수 있습니다

### 문제 해결 가이드

| 오류 메시지 | 원인 | 해결 방법 |
|------------|------|----------|
| `{"detail":"Method Not Allowed"}` | GET 엔드포인트에 POST 요청 | `/config/current-directory`는 GET 사용 |
| `{"detail":"디렉토리 경로가 필요합니다"}` | 잘못된 JSON 키 사용 | `{"path": "..."}` → `{"directory": "..."}` |
| `{"detail":"파일을 찾을 수 없습니다"}` | 파일 경로 오류 | 현재 디렉토리 확인 후 올바른 경로 사용 |
| `{"detail":"지원하지 않는 파일 형식"}` | 미지원 파일 형식 | PDF, DOCX, TXT, MD, HTML 파일만 지원 |

---

## 🚀 시작하기

1. **백엔드 서버 시작**:
   ```bash
   ./scripts/start_backend.sh
   ```

2. **API 문서 확인**: 
   - Swagger UI: http://localhost:58000/docs
   - ReDoc: http://localhost:58000/redoc

3. **헬스체크**:
   ```bash
   curl http://localhost:58000/
   ```

---

*마지막 업데이트: 2025-08-29*