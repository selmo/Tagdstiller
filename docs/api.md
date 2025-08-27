# DocExtract Backend API Documentation

## 🚀 개요

DocExtract 백엔드는 문서 키워드 추출 시스템을 위한 RESTful API를 제공합니다.  
기본 URL: `http://localhost:8000`

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

### 파일 메타데이터 (✨ 새로운 기능)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/files/{file_id}/metadata` | 파일 메타데이터 조회 |
| `GET` | `/projects/{project_id}/files/{file_id}/metadata` | 프로젝트 내 파일 메타데이터 조회 |

#### 메타데이터 응답 예시 (Dublin Core 표준 형식)
```json
{
  "file_id": 1,
  "filename": "document.pdf",
  
  // Dublin Core 표준 메타데이터 (null 값은 자동 제외됨)
  "dc:title": "문서 제목",
  "dc:creator": "작성자", 
  "dc:subject": "주제",
  "dc:description": "문서 설명",
  "dc:date": "2024-01-15T09:30:00",
  "dc:type": "document",
  "dc:format": "application/pdf",
  "dc:identifier": "document.pdf",
  "dc:source": "/uploads/1/document.pdf",
  "dc:language": "ko",
  
  // Dublin Core Terms 확장
  "dcterms:created": "2024-01-15T09:30:00",
  "dcterms:modified": "2024-01-15T09:35:00", 
  "dcterms:extent": "1048576 bytes",
  "dcterms:medium": "digital",
  "dcterms:alternative": "document.pdf",
  "dcterms:isPartOf": "project_1",
  "dcterms:hasFormat": ".pdf",
  
  // 문서 특정 정보
  "doc:pageCount": 10,
  "doc:wordCount": 2500,
  "doc:characterCount": 15000,
  "doc:typeCode": "pdf",
  "doc:supported": "yes",
  
  // 처리 정보
  "processing:parserName": "pdf_parser_pymupdf_basic",
  "processing:parserVersion": "1.0",
  "processing:extractionDate": "2024-01-15T10:00:00",
  "processing:appVersion": "1.0.0",
  "processing:parseStatus": "success",
  "processing:uploadDate": "2024-01-15T09:00:00"
}
```

> **📝 참고**: null 또는 빈 문자열 값을 가진 메타데이터 필드는 응답에서 자동으로 제외됩니다.

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

### 파일 분석

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/local-analysis/analyze` | 로컬 파일 분석 (경로 지정) |
| `GET` | `/local-analysis/analyze` | 파일 분석 (파라미터로 경로) |
| `GET` | `/local-analysis/status` | 분석 상태 확인 |
| `GET` | `/local-analysis/result` | 분석 결과 조회 |
| `POST` | `/local-analysis/reanalyze` | 재분석 실행 |

### 디렉토리 관리

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/local-analysis/config/root` | 루트 디렉토리 조회 |
| `GET` | `/local-analysis/config/current-directory` | 현재 디렉토리 조회 |
| `POST` | `/local-analysis/config/change-directory` | 디렉토리 변경 |
| `POST` | `/local-analysis/config/change-directory-and-list` | 디렉토리 변경 및 목록 |

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
curl -X POST "http://localhost:8000/projects/" \
  -H "Content-Type: application/json" \
  -d '{"name": "테스트 프로젝트"}'

# 파일 업로드 (자동 파싱 활성화)
curl -X POST "http://localhost:8000/projects/1/upload?auto_parse=true" \
  -F "file=@document.pdf"
```

### 2. 키워드 추출 실행

```bash
# 프로젝트 전체 키워드 추출
curl -X POST "http://localhost:8000/projects/1/extract_keywords" \
  -H "Content-Type: application/json" \
  -d '{"extractors": ["KeyBERT", "spaCy NER", "LLM"]}'
```

### 3. 메타데이터 조회
ch
```bash
# 파일 메타데이터 조회
curl "http://localhost:8000/files/1/metadata"

# 프로젝트 내 파일 메타데이터 조회
curl "http://localhost:8000/projects/1/files/1/metadata"
```

### 4. 키워드 결과 조회

```bash
# 프로젝트 키워드 조회
curl "http://localhost:8000/projects/1/keywords"

# 특정 파일 키워드 조회
curl "http://localhost:8000/files/1/keywords"
```

---

## 📝 주요 특징

- **완전한 RESTful API**: 표준 HTTP 메서드 사용
- **Dublin Core 메타데이터**: 국제 표준 메타데이터 지원
- **다중 파일 형식**: PDF, DOCX, HTML, Markdown, TXT 지원
- **실시간 진행률**: Server-Sent Events를 통한 실시간 업데이트
- **모델 관리**: KeyBERT, spaCy 모델 자동 다운로드 및 관리
- **캐시 시스템**: 효율적인 성능을 위한 다층 캐시
- **오류 처리**: 상세한 오류 메시지 및 상태 코드

---

## 🚀 시작하기

1. **백엔드 서버 시작**:
   ```bash
   ./scripts/start_backend.sh
   ```

2. **API 문서 확인**: 
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

3. **헬스체크**:
   ```bash
   curl http://localhost:8000/
   ```

---

*마지막 업데이트: 2024-08-27*