# 🔍 Local Analysis API 완전 가이드

## 개요

Local Analysis API는 서버의 로컬 파일 시스템에 있는 문서를 직접 분석하는 기능을 제공합니다. 프로젝트 업로드 없이 파일을 직접 키워드 추출 및 메타데이터 분석할 수 있습니다.

**Base URL**: `http://localhost:58000/local-analysis`

## 🎯 주요 기능

- **파일 분석**: 로컬 파일에서 키워드 추출 및 메타데이터 추출
- **디렉토리 관리**: 작업 디렉토리 변경 및 파일 목록 조회
- **분석 상태 관리**: 기존 분석 결과 조회 및 재분석
- **파서 선택**: Docling/기본 파서 선택 지원

## 📋 API 엔드포인트 목록

### 1. 파일 분석

#### 🔵 파일 분석 실행 (POST)
```http
POST /local-analysis/analyze
Content-Type: application/json

{
    "file_path": "test_document.pdf",
    "extractors": ["KeyBERT", "spaCy NER", "LLM"],
    "force_reanalyze": false,
    "use_docling": true
}
```

**Request Body**:
- `file_path` (string, required): 분석할 파일 경로
- `extractors` (array, optional): 사용할 추출기 목록
- `force_reanalyze` (boolean, optional): 재분석 강제 여부 (기본값: false)
- `use_docling` (boolean, optional): Docling 파서 사용 여부 (기본값: false)

**Response**:
```json
{
    "file_info": {
        "name": "test_document.pdf",
        "size": 1234567,
        "modified": 1693456789.0,
        "extension": ".pdf"
    },
    "content_info": {
        "text_length": 5000,
        "word_count": 800,
        "page_count": 10
    },
    "extraction_info": {
        "extractors_used": ["KeyBERT", "spaCy NER"],
        "total_keywords": 25,
        "extraction_time": 3.45
    },
    "keywords": {
        "KeyBERT": [
            {
                "keyword": "인공지능",
                "score": 0.85,
                "category": "technology",
                "positions": [{"start": 120, "end": 124}]
            }
        ]
    },
    "analysis_status": "completed",
    "analysis_timestamp": "2025-08-30T12:30:00",
    "result_file": "/path/to/result.json"
}
```

#### 🔵 파일 분석 실행 (GET)
```http
GET /local-analysis/analyze?file_path=test.pdf&extractors=KeyBERT,spaCy%20NER&use_docling=true
```

**Query Parameters**:
- `file_path` (string, required): 파일 경로
- `extractors` (string, optional): 추출기 목록 (쉼표로 구분)
- `force_reanalyze` (boolean, optional): 재분석 여부
- `use_docling` (boolean, optional): Docling 파서 사용 여부

#### 🔵 파일 재분석
```http
POST /local-analysis/reanalyze
Content-Type: application/json

{
    "file_path": "test_document.pdf",
    "extractors": ["KeyBERT", "LLM"]
}
```

### 2. 분석 결과 조회

#### 🟢 분석 결과 조회
```http
GET /local-analysis/result?file_path=test_document.pdf
```

#### 🟢 파일 상태 확인
```http
GET /local-analysis/status?file_path=test_document.pdf
```

**Response**:
```json
{
    "file_path": "test_document.pdf",
    "exists": true,
    "supported": true,
    "has_analysis": true,
    "analysis_timestamp": "2025-08-30T12:30:00",
    "result_file": "/path/to/result.json"
}
```

### 3. 메타데이터 추출

#### 🟢 메타데이터 추출 (GET)
```http
GET /local-analysis/metadata?file_path=test.pdf&use_docling=true
```

**Query Parameters**:
- `file_path` (string, required): 파일 경로
- `use_docling` (boolean, optional): Docling 파서 사용 여부
- `use_all_parsers` (boolean, optional): 모든 파서 시도 여부

#### 🔵 메타데이터 추출 (POST)
```http
POST /local-analysis/metadata
Content-Type: application/json

{
    "file_path": "test_document.pdf",
    "use_docling": true,
    "use_all_parsers": false
}
```

**Dublin Core 메타데이터 Response**:
```json
{
    "@context": "http://purl.org/dc/terms/",
    "dc:title": "Test Document",
    "dc:creator": "Unknown",
    "dc:type": "Text",
    "dc:format": "application/pdf",
    "dc:language": "ko",
    "dcterms:created": "2025-08-30T12:30:00+09:00",
    "file:name": "test_document.pdf",
    "file:size": 1234567,
    "doc:pageCount": 10,
    "processing:parserName": "pdf_parser_docling"
}
```

### 4. 디렉토리 관리

#### 🟢 현재 디렉토리 조회
```http
GET /local-analysis/config/current-directory
```

**Response**:
```json
{
    "current_directory": "/Users/selmo/Workspaces/DocExtract/backend",
    "parent_directory": "/Users/selmo/Workspaces/DocExtract",
    "contents": {
        "directories": [
            {
                "name": "data",
                "path": "/Users/selmo/Workspaces/DocExtract/backend/data",
                "item_count": 15,
                "modified": 1693456789.0
            }
        ],
        "files": [
            {
                "name": "main.py",
                "path": "/Users/selmo/Workspaces/DocExtract/backend/main.py",
                "size": 1234,
                "extension": ".py",
                "modified": 1693456789.0
            }
        ],
        "total_directories": 5,
        "total_files": 10
    }
}
```

#### 🔵 디렉토리 변경
```http
POST /local-analysis/config/change-directory
Content-Type: application/json

{
    "directory": "/Users/selmo/Documents"
}
```

**Response**:
```json
{
    "success": true,
    "message": "디렉토리가 성공적으로 변경되었습니다",
    "old_directory": "/Users/selmo/Workspaces/DocExtract/backend",
    "new_directory": "/Users/selmo/Documents"
}
```

#### 🔵 디렉토리 변경 + 파일 목록 조회
```http
POST /local-analysis/config/change-directory-and-list
Content-Type: application/json

{
    "directory": "/Users/selmo/Documents"
}
```

#### 🟢 파일 루트 조회
```http
GET /local-analysis/config/root
```

### 5. 추출기 관리

#### 🟢 사용 가능한 추출기 조회
```http
GET /local-analysis/config/extractors
```

**Response**:
```json
{
    "default_extractors": ["keybert", "ner", "konlpy", "metadata"],
    "available_extractors": ["keybert", "ner", "konlpy", "llm", "metadata"],
    "extractor_status": {
        "keybert": true,
        "ner": true,
        "konlpy": true,
        "llm": true,
        "metadata": true,
        "langextract": false
    }
}
```

## 📋 사용 워크플로우

### 기본 워크플로우
```bash
# 1. 현재 디렉토리 확인
curl "http://localhost:58000/local-analysis/config/current-directory"

# 2. 작업 디렉토리 변경 (필요시)
curl -X POST "http://localhost:58000/local-analysis/config/change-directory" \
  -H "Content-Type: application/json" \
  -d '{"directory": "/Users/selmo/Documents"}'

# 3. 사용 가능한 추출기 확인
curl "http://localhost:58000/local-analysis/config/extractors"

# 4. 파일 분석 실행
curl -X POST "http://localhost:58000/local-analysis/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "document.pdf",
    "extractors": ["KeyBERT", "spaCy NER", "LLM"],
    "use_docling": true
  }'

# 5. 분석 결과 조회 (필요시)
curl "http://localhost:58000/local-analysis/result?file_path=document.pdf"
```

### 한글 파일명 처리
```bash
# POST 방식 (권장)
curl -X POST "http://localhost:58000/local-analysis/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "연구보고서_최종본.pdf",
    "extractors": ["KeyBERT", "spaCy NER"]
  }'

# GET 방식 (URL 인코딩 필요)
curl -G "http://localhost:58000/local-analysis/analyze" \
  --data-urlencode "file_path=연구보고서_최종본.pdf" \
  --data-urlencode "extractors=KeyBERT,spaCy NER"
```

## ⚠️ 주의사항

### 1. HTTP 메서드
- **GET**: `current-directory`, `status`, `result`, `metadata`, `root`, `extractors`
- **POST**: `analyze`, `reanalyze`, `change-directory`, `metadata`

### 2. Request Body 키
- 디렉토리 변경: `{"directory": "..."}` (❌ `{"path": "..."}` 아님)
- 파일 경로: `{"file_path": "..."}` 

### 3. 파서 선택
- `use_docling=true`: Docling 파서 우선 사용
- `use_docling=false`: 기본 파서 사용
- `use_docling=null` + `use_all_parsers=true`: 모든 파서 시도

### 4. 오류 처리
- **404**: 파일을 찾을 수 없음
- **400**: 잘못된 요청 (지원하지 않는 파일 형식 등)
- **403**: 권한 없음
- **500**: 서버 내부 오류

## 🎯 지원 파일 형식

- **PDF**: `.pdf` (Docling/기본 파서 지원)
- **Word**: `.docx`
- **텍스트**: `.txt`, `.md`
- **HTML**: `.html`, `.htm`
- **압축**: `.zip` (자동 압축 해제 및 분석)

## 🛠️ 추출기 종류

1. **KeyBERT**: BERT 기반 키워드 추출
2. **spaCy NER**: Named Entity Recognition
3. **KoNLPy**: 한국어 형태소 분석
4. **LLM**: Large Language Model (Ollama)
5. **metadata**: 파일 메타데이터 추출
6. **langextract**: 언어 감지 (선택적)

## 📁 생성되는 파일

분석 완료 후 다음과 같은 구조로 파일이 생성됩니다:

```
원본파일.pdf
원본파일/
├── docling.md          (Docling 파서 결과)
├── pymupdf4llm.md      (PyMuPDF4LLM 파서 결과)
└── 원본파일.pdf.analysis.json  (분석 결과)
```

## 🔧 테스트 스크립트

시스템에서 제공하는 테스트 스크립트들:
- `test_local_analysis.sh`: 전체 API 테스트
- `test_metadata.sh`: 메타데이터 추출 테스트
- `test_all_parsers.sh`: 모든 파서 테스트

```bash
# 전체 기능 테스트
./test_local_analysis.sh

# 메타데이터만 테스트
./test_metadata.sh
```