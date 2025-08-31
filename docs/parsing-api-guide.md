# 🚀 Parsing API 완전 가이드

## 개요

Parsing API는 DocExtract 시스템의 새로운 핵심 기능으로, 모든 적용 가능한 파서를 동시 사용하여 최상의 문서 파싱 결과를 제공합니다. 기존의 단일 파서 접근 방식을 벗어나 다중 파서 전략을 통해 품질과 완성도를 극대화했습니다.

**Base URL**: `http://localhost:58000/local-analysis`

## 🎯 핵심 특징

### 1. 완전 파싱 (Comprehensive Parsing)
- **모든 파서 동시 실행**: 파일 형식에 따라 모든 적용 가능한 파서를 동시 실행
- **품질 점수 기반 선정**: 텍스트 품질을 정량적으로 평가하여 최적 파서 자동 선정
- **구조화된 정보 보존**: 테이블, 이미지, 섹션 등 문서 구조 완전 보존
- **결과 재사용**: 파싱 결과를 파일로 저장하여 후속 작업에서 재사용

### 2. 계층적 파일 저장
```
document.pdf
document/
├── parsing_results.json        # 종합 파싱 결과
├── docling.md                 # Docling 구조화 결과
├── docling/
│   ├── docling_text.txt       # 순수 텍스트
│   ├── docling_metadata.json  # Dublin Core 메타데이터
│   └── docling_structure.json # 구조 정보
└── pdf_parser/
    ├── pdf_parser_text.txt
    ├── pdf_parser_metadata.json
    └── pdf_parser_structure.json
```

### 3. 지원 파서 매트릭스

| 파일 형식 | 지원 파서 |
|----------|-----------|
| **PDF** | Docling (우선), PdfParser (다중 엔진) |
| **DOCX** | DocxParser |
| **TXT** | TxtParser |
| **HTML** | HtmlParser |
| **Markdown** | MarkdownParser |
| **ZIP** | ZipParser (자동 압축 해제) |

## 📋 API 엔드포인트

### 1. 완전 파싱 실행

#### 🔵 POST 방식 (권장)
```http
POST /local-analysis/parse
Content-Type: application/json

{
    "file_path": "document.pdf",
    "force_reparse": false
}
```

**Parameters**:
- `file_path` (required): 파싱할 파일 경로
- `force_reparse` (optional): 기존 결과 무시하고 재파싱 여부

**Response**:
```json
{
    "file_info": {
        "name": "document.pdf",
        "size": 3369,
        "extension": "pdf"
    },
    "parsing_timestamp": "2025-08-30T13:09:16.585585",
    "parsers_used": ["docling", "pdf_parser"],
    "parsing_results": {
        "docling": {
            "success": true,
            "quality_score": 0.615,
            "text_length": 618,
            "word_count": 145,
            "md_file_path": "/path/to/docling.md",
            "structured_info": {
                "document_structure": {
                    "tables": [],
                    "images": [],
                    "sections": [...]
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
    "output_directory": "/path/to/output"
}
```

#### 🟢 GET 방식
```http
GET /local-analysis/parse?file_path=document.pdf&force_reparse=false
```

### 2. 파싱 상태 확인

```http
GET /local-analysis/parse/status?file_path=document.pdf
```

**Response**:
```json
{
    "file_path": "document.pdf",
    "exists": true,
    "supported": true,
    "has_parsing_results": true,
    "parsing_timestamp": "2025-08-30T13:09:16.585585",
    "parsers_used": ["docling", "pdf_parser"],
    "summary": {
        "best_parser": "docling",
        "successful_parsers": 2
    },
    "supported_extensions": ["pdf", "docx", "txt", "html", "md", "zip"]
}
```

### 3. 파싱 결과 조회

```http
GET /local-analysis/parse/results?file_path=document.pdf&parser_name=docling
```

**Parameters**:
- `file_path` (required): 파일 경로
- `parser_name` (optional): 특정 파서 결과만 조회

## 🏗️ 품질 평가 시스템

### 품질 점수 계산 방식
1. **길이 점수 (30%)**: `min(텍스트_길이 / 1000, 1.0) * 0.3`
2. **다양성 점수 (30%)**: `min(고유단어수 / 전체단어수, 1.0) * 0.3`
3. **구조 점수 (20%)**: `min(문장부호수 / 텍스트길이 * 100, 1.0) * 0.2`
4. **의미 점수 (20%)**: `(의미있는문자수 / 전체문자수) * 0.2`

### 최적 파서 선정 기준
- 가장 높은 품질 점수를 받은 파서를 최적 파서로 선정
- 동점인 경우 파서 우선순위에 따라 결정
- PDF의 경우 Docling이 일반적으로 우선됨 (구조 보존 능력)

## 📊 구조화된 정보 추출

### Docling 파서 구조 정보
```json
{
    "document_structure": {
        "tables": [
            {
                "content": "테이블 내용",
                "page": 1
            }
        ],
        "images": [
            {
                "caption": "이미지 캡션",
                "page": 2
            }
        ],
        "sections": [
            {
                "level": 2,
                "title": "섹션 제목",
                "line": 15
            }
        ]
    },
    "total_lines": 25,
    "paragraphs": 8,
    "headers": 3
}
```

### 모든 파서 공통 구조 정보
- **total_lines**: 총 라인 수
- **non_empty_lines**: 비어있지 않은 라인 수
- **paragraphs**: 단락 수 (# 시작하지 않는 라인)
- **headers**: 헤더 수 (# 시작 라인)

## 🔄 사용 워크플로우

### 기본 워크플로우
```bash
# 1. 파일 파싱 상태 확인
curl "http://localhost:58000/local-analysis/parse/status?file_path=document.pdf"

# 2. 완전 파싱 실행 (필요한 경우)
curl -X POST "http://localhost:58000/local-analysis/parse" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "document.pdf"}'

# 3. 특정 파서 결과 조회
curl "http://localhost:58000/local-analysis/parse/results?file_path=document.pdf&parser_name=docling"

# 4. 전체 결과 조회
curl "http://localhost:58000/local-analysis/parse/results?file_path=document.pdf"
```

### 재파싱 워크플로우
```bash
# 기존 결과 무시하고 재파싱
curl -X POST "http://localhost:58000/local-analysis/parse" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "document.pdf", "force_reparse": true}'
```

## 🛠️ 고급 활용

### 1. 후속 분석 API와 연계
파싱 완료 후 다음 API들이 파싱 결과를 자동 활용:
- `/local-analysis/analyze` - 키워드 추출 분석
- `/local-analysis/metadata` - 메타데이터 추출
- `/local-analysis/structure-analysis` - 구조 분석
- `/local-analysis/knowledge-graph` - Knowledge Graph 생성

### 2. 배치 처리 예시
```python
import requests
import json
from pathlib import Path

files = ["doc1.pdf", "doc2.docx", "doc3.txt"]
results = {}

for file_path in files:
    response = requests.post(
        "http://localhost:58000/local-analysis/parse",
        json={"file_path": file_path}
    )
    results[file_path] = response.json()
    print(f"✅ {file_path}: {results[file_path]['summary']['best_parser']}")
```

## ⚠️ 주의사항

### 1. 파일 경로 처리
- 절대 경로 권장
- 상대 경로는 서버 작업 디렉토리 기준으로 해석
- 한글 파일명은 POST 방식 권장

### 2. 성능 고려사항
- 첫 파싱 시간이 소요될 수 있음 (모든 파서 동시 실행)
- 결과 재사용으로 후속 작업은 빠름
- 대용량 파일의 경우 timeout 설정 필요할 수 있음

### 3. 저장 공간
- 파서별 개별 결과 + 종합 결과로 저장 공간 사용량 증가
- 구조화된 파서(Docling)는 추가로 MD 파일 생성
- 필요시 `force_reparse=true`로 기존 결과 갱신

## 🔧 오류 처리

### 일반적인 오류 코드
- **404**: 파일을 찾을 수 없음
- **400**: 지원하지 않는 파일 형식
- **500**: 서버 내부 오류 (파싱 실패 등)

### 문제 해결
```bash
# 파싱 상태 확인
curl "http://localhost:58000/local-analysis/parse/status?file_path=problem.pdf"

# 강제 재파싱
curl -X POST "http://localhost:58000/local-analysis/parse" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "problem.pdf", "force_reparse": true}'
```

이 Parsing API는 DocExtract 시스템의 모든 고급 기능의 기반이 되며, 최상의 문서 처리 품질을 보장합니다.