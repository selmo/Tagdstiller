# 🔍 Local Analysis API 완전 가이드

## 개요

Local Analysis API는 서버의 로컬 파일 시스템에 있는 문서를 직접 분석하는 완전한 문서 처리 시스템입니다. 파싱부터 키워드 추출, 구조 분석, Knowledge Graph 생성까지 단계적 처리를 지원합니다.

**Base URL**: `http://localhost:58000/local-analysis`

## 🎯 주요 기능

- **완전 파싱**: 모든 적용 가능한 파서를 사용하여 최상의 파싱 결과 제공
- **키워드 분석**: 파싱 결과 기반 다중 추출기 키워드 분석
- **구조 분석**: 문서의 구조적 요소 분석 (헤더, 테이블, 이미지 등)
- **Knowledge Graph**: 엔티티와 관계를 추출한 지식 그래프 생성
- **메타데이터 추출**: Dublin Core 표준 메타데이터 완전 지원
- **디렉토리 관리**: 작업 디렉토리 변경 및 파일 목록 조회
- **결과 재사용**: 각 단계별 결과 캐싱으로 성능 최적화
- **🆕 디렉토리 파라미터**: 모든 결과 파일을 사용자 지정 디렉토리에 저장 (2025.08.31)
- **🆕 saved_files 응답**: 생성된 모든 파일의 경로와 유형 정보 포함
- **🆕 마크다운 파일 관리**: docling.md, pymupdf4llm.md 파일을 지정된 위치에 정확히 생성

## 🆕 최신 업데이트 (2025.08.31)

### 새로운 기능
1. **directory 파라미터**: 모든 API 엔드포인트에서 결과 파일 저장 위치 지정 가능
2. **saved_files 응답**: API 응답에 생성된 모든 파일의 상세 정보 포함
3. **마크다운 파일 위치 수정**: 파서가 생성하는 마크다운 파일이 지정된 디렉토리에 정확히 생성
4. **use_llm 파라미터**: metadata 엔드포인트에서 LLM 기반 분석 옵션 추가

### 개선사항
- 파일 생성 위치의 완전한 제어 가능
- 결과 파일 추적 및 관리 개선
- API 응답의 일관성과 투명성 향상

## 📋 API 엔드포인트 목록

### 1. 완전 파싱 (Comprehensive Parsing)

#### 🔵 문서 완전 파싱 (POST)
```http
POST /local-analysis/parse
Content-Type: application/json

{
    "file_path": "test_document.pdf",
    "force_reparse": false,
    "directory": "/custom/output/path"
}
```

**Request Body**:
- `file_path` (string, required): 파싱할 문서 경로
- `force_reparse` (boolean, optional): 기존 결과 무시하고 재파싱 여부 (기본값: false)
- `directory` (string, optional): **🆕** 결과 파일을 저장할 디렉토리 경로 (기본값: 파일과 같은 디렉토리)

**Response**:
```json
{
    "file_info": {
        "name": "test_document.pdf",
        "path": "/path/to/test_document.pdf",
        "size": 3369,
        "extension": "pdf",
        "modified": 1756425874.536066
    },
    "parsing_timestamp": "2025-08-30T13:09:16.585585",
    "parsers_used": ["docling", "pdf_parser"],
    "parsing_results": {
        "docling": {
            "success": true,
            "parser_name": "pdf_parser_docling",
            "text_length": 618,
            "word_count": 145,
            "quality_score": 0.615,
            "md_file_path": "/path/to/output/docling.md",
            "structured_info": {
                "document_structure": {
                    "tables": [],
                    "images": [],
                    "sections": ["..."]
                }
            }
        }
    },
    "summary": {
        "total_parsers": 2,
        "successful_parsers": 2,
        "best_parser": "docling",
        "best_quality_score": 0.615
    },
    "output_directory": "/path/to/output",
    "saved_files": [
        {
            "path": "/path/to/output/parsing_results.json",
            "type": "parsing_results",
            "parser": "comprehensive"
        },
        {
            "path": "/path/to/output/docling.md",
            "type": "markdown",
            "parser": "docling"
        },
        {
            "path": "/path/to/output/docling/docling_text.txt",
            "type": "text",
            "parser": "docling"
        }
    ]
}
```

#### 🔵 문서 완전 파싱 (GET)
```http
GET /local-analysis/parse?file_path=test.pdf&force_reparse=false&directory=/custom/output/path
```

**Query Parameters**:
- `file_path` (string, required): 파싱할 문서 경로
- `force_reparse` (boolean, optional): 기존 결과 무시하고 재파싱 여부 (기본값: false)
- `directory` (string, optional): **🆕** 결과 파일을 저장할 디렉토리 경로

#### 🟢 파싱 상태 확인
```http
GET /local-analysis/parse/status?file_path=test_document.pdf
```

**Response**:
```json
{
    "file_path": "test_document.pdf",
    "exists": true,
    "supported": true,
    "has_parsing_results": true,
    "parsing_timestamp": "2025-08-30T13:09:16.585585",
    "parsers_used": ["docling", "pdf_parser"],
    "summary": {
        "total_parsers": 2,
        "successful_parsers": 2,
        "best_parser": "docling"
    },
    "output_directory": "/path/to/output",
    "supported_extensions": ["pdf", "docx", "txt", "html", "md", "zip"]
}
```

#### 🟢 파싱 결과 조회
```http
GET /local-analysis/parse/results?file_path=test.pdf&parser_name=docling
```

**Query Parameters**:
- `file_path` (string, required): 파일 경로
- `parser_name` (string, optional): 특정 파서 결과만 조회

### 2. 키워드 분석

#### 🔵 키워드 분석 실행 (POST)
```http
POST /local-analysis/analyze
Content-Type: application/json

{
    "file_path": "test_document.pdf",
    "extractors": ["KeyBERT", "spaCy NER", "LLM"],
    "force_reanalyze": false,
    "force_reparse": false
}
```

**Request Body**:
- `file_path` (string, required): 분석할 파일 경로
- `extractors` (array, optional): 사용할 추출기 목록
- `force_reanalyze` (boolean, optional): 키워드 재분석 여부 (기본값: false)
- `force_reparse` (boolean, optional): 파싱부터 다시 수행할지 여부 (기본값: false)
- `directory` (string, optional): **🆕** 결과 파일을 저장할 디렉토리 경로

**동작 방식**:
1. 파싱 결과가 없으면 먼저 완전 파싱을 자동 수행
2. 파싱 결과를 기반으로 키워드 추출 분석 수행
3. 모든 결과를 파일로 저장하여 재사용

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
    "result_file": "/path/to/result.json",
    "saved_files": [
        {
            "path": "/path/to/result.json",
            "type": "analysis_results",
            "parser": "comprehensive"
        },
        {
            "path": "/path/to/document.pdf.analysis.json",
            "type": "keyword_analysis",
            "parser": "comprehensive"
        }
    ]
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
- `directory` (string, optional): **🆕** 결과 파일을 저장할 디렉토리 경로

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
GET /local-analysis/metadata?file_path=test.pdf&force_reparse=false&parser_name=docling&directory=/custom/output&use_llm=true
```

**Query Parameters**:
- `file_path` (string, required): 파일 경로
- `force_reparse` (boolean, optional): 재파싱 여부 (기본값: false)
- `parser_name` (string, optional): 특정 파서의 메타데이터만 조회
- `directory` (string, optional): **🆕** 결과 파일을 저장할 디렉토리 경로
- `use_llm` (boolean, optional): **🆕** LLM 기반 분석 사용 여부 (기본값: false)

**동작 방식**:
1. 파싱 결과가 없으면 먼저 완전 파싱을 자동 수행
2. 모든 파서의 메타데이터를 통합하여 반환
3. parser_name 지정시 해당 파서의 메타데이터만 반환

#### 🔵 메타데이터 추출 (POST)
```http
POST /local-analysis/metadata
Content-Type: application/json

{F
    "file_path": "test_document.pdf",
    "force_reparse": false,
    "parser_name": "docling"
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

### 4. 구조 분석

#### 🔵 문서 구조 분석 (POST)
```http
POST /local-analysis/structure-analysis
Content-Type: application/json

{
    "file_path": "test_document.pdf",
    "force_reparse": false,
    "force_reanalyze": false
}
```

**Request Body**:
- `file_path` (string, required): 분석할 파일 경로
- `force_reparse` (boolean, optional): 재파싱 여부 (기본값: false)
- `force_reanalyze` (boolean, optional): 구조 재분석 여부 (기본값: false)

**동작 방식**:
1. 파싱 결과가 없으면 먼저 완전 파싱을 자동 수행
2. 각 파서별 구조 정보를 수집하여 통합 분석
3. 복잡도 점수를 계산하여 최적 파서 선정

**Response**:
```json
{
    "file_info": {
        "name": "test_document.pdf",
        "size": 3369,
        "extension": "pdf"
    },
    "analysis_timestamp": "2025-08-30T13:15:00.123456",
    "structure_elements": {
        "docling": {
            "total_lines": 25,
            "paragraphs": 8,
            "headers": 3,
            "table_count": 2,
            "image_count": 1,
            "section_count": 3,
            "complexity_score": 0.85
        }
    },
    "summary": {
        "best_parser": "docling",
        "total_elements": 6,
        "element_types": {
            "paragraphs": 8,
            "headers": 3,
            "table_count": 2
        },
        "complexity_score": 0.85,
        "has_tables": true,
        "has_images": true,
        "has_sections": true
    }
}
```

#### 🟢 문서 구조 분석 (GET)
```http
GET /local-analysis/structure-analysis?file_path=test.pdf&force_reanalyze=false
```

### 5. Knowledge Graph 생성

#### 🔵 Knowledge Graph 생성 (POST)
```http
POST /local-analysis/knowledge-graph
Content-Type: application/json

{
    "file_path": "test_document.pdf",
    "force_reparse": false,
    "force_reanalyze": false,
    "force_rebuild": false
}
```

**Request Body**:
- `file_path` (string, required): 분석할 파일 경로
- `force_reparse` (boolean, optional): 재파싱 여부 (기본값: false)
- `force_reanalyze` (boolean, optional): 키워드 재분석 여부 (기본값: false)
- `force_rebuild` (boolean, optional): KG 재생성 여부 (기본값: false)

**동작 방식**:
1. 파싱 결과가 없으면 먼저 완전 파싱을 자동 수행
2. 키워드 추출 결과가 없으면 키워드 분석을 자동 수행
3. 최고 품질 파서의 텍스트와 키워드를 활용하여 KG 생성

**Response**:
```json
{
    "file_info": {
        "name": "test_document.pdf",
        "size": 3369
    },
    "generation_timestamp": "2025-08-30T13:20:00.123456",
    "source_parser": "docling",
    "keywords_used": 25,
    "knowledge_graph": {
        "entities": [
            {
                "id": "entity_1",
                "name": "인공지능",
                "type": "concept",
                "properties": {
                    "score": 0.85,
                    "frequency": 5
                }
            }
        ],
        "relationships": [
            {
                "id": "rel_1",
                "source": "entity_1",
                "target": "entity_2",
                "type": "relates_to",
                "properties": {
                    "strength": 0.7
                }
            }
        ]
    },
    "statistics": {
        "total_entities": 15,
        "total_relationships": 8,
        "entity_types": {
            "concept": 10,
            "person": 3,
            "organization": 2
        }
    }
}
```

#### 🟢 Knowledge Graph 조회 (GET)
```http
GET /local-analysis/knowledge-graph?file_path=test.pdf&force_rebuild=false
```

### 6. 디렉토리 관리

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

### 완전 문서 처리 워크플로우
```bash
# 1. 현재 디렉토리 확인
curl "http://localhost:58000/local-analysis/config/current-directory"

# 2. 작업 디렉토리 변경 (필요시)
curl -X POST "http://localhost:58000/local-analysis/config/change-directory" \
  -H "Content-Type: application/json" \
  -d '{"directory": "/Users/selmo/Documents"}'

# 3. 문서 완전 파싱 (모든 파서 사용)
curl -X POST "http://localhost:58000/local-analysis/parse" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "document.pdf",
    "force_reparse": false
  }'

# 4. 키워드 분석 (파싱 결과 활용)
curl -X POST "http://localhost:58000/local-analysis/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "document.pdf",
    "extractors": ["KeyBERT", "spaCy NER", "LLM"],
    "force_reanalyze": false
  }'

# 5. 문서 구조 분석
curl -X POST "http://localhost:58000/local-analysis/structure-analysis" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "document.pdf",
    "force_reanalyze": false
  }'

# 6. Knowledge Graph 생성
curl -X POST "http://localhost:58000/local-analysis/knowledge-graph" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "document.pdf",
    "force_rebuild": false
  }'

# 7. 통합 메타데이터 조회
curl "http://localhost:58000/local-analysis/metadata?file_path=document.pdf"
```

### 단계적 처리 시스템
각 API는 이전 단계의 결과를 자동으로 활용합니다:

1. **Parse** → 모든 파서로 완전 파싱
2. **Analyze** → 파싱 결과 기반 키워드 추출
3. **Structure-Analysis** → 파싱 결과 기반 구조 분석  
4. **Knowledge-Graph** → 파싱 + 키워드 결과 기반 KG 생성

필요한 이전 단계 결과가 없으면 자동으로 수행됩니다.

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

## 📁 생성되는 파일 구조

완전한 문서 처리 후 다음과 같은 구조화된 파일들이 생성됩니다:

```
document.pdf
document/
├── parsing_results.json        # 종합 파싱 결과
├── structure_analysis.json     # 구조 분석 결과
├── knowledge_graph.json        # Knowledge Graph
├── docling.md                  # Docling 파서 Markdown 결과
├── docling/
│   ├── docling_text.txt        # 추출된 텍스트
│   ├── docling_metadata.json   # 메타데이터 (Dublin Core)
│   └── docling_structure.json  # 구조 정보 (테이블, 이미지 등)
├── pdf_parser/
│   ├── pdf_parser_text.txt     # 추출된 텍스트
│   ├── pdf_parser_metadata.json # 메타데이터
│   └── pdf_parser_structure.json # 구조 정보
└── document.pdf.analysis.json  # 키워드 분석 결과 (기존 위치)
```

### 파일별 상세 설명

#### 파싱 관련 파일
- **parsing_results.json**: 모든 파서의 종합 결과, 품질 점수, 최적 파서 정보
- **[parser]/[parser]_text.txt**: 각 파서별 추출된 순수 텍스트
- **[parser]/[parser]_metadata.json**: 각 파서별 메타데이터 (Dublin Core 표준)
- **[parser]/[parser]_structure.json**: 각 파서별 구조 정보
- **docling.md, pymupdf4llm.md**: 구조화된 파서의 Markdown 결과

#### 분석 관련 파일
- **structure_analysis.json**: 문서 구조 분석 결과 (복잡도, 요소 통계)
- **knowledge_graph.json**: 생성된 지식 그래프 (엔티티, 관계)
- **document.pdf.analysis.json**: 키워드 추출 분석 결과

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