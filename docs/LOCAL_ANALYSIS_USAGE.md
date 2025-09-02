# 🔍 로컬 분석 API 사용법

## 🆕 최신 업데이트 (2025.08.31)
- **directory 파라미터** 추가: 모든 결과 파일을 지정된 디렉토리에 저장 가능
- **saved_files 응답** 추가: 생성된 모든 파일의 경로 정보 제공
- **마크다운 파일 위치 수정**: docling.md, pymupdf4llm.md가 정확한 위치에 생성됨

## ⚠️ 중요: 올바른 사용법

### ❌ 잘못된 사용 예시
```bash
# 잘못됨 1: POST 요청 (GET이어야 함)
curl -X POST "http://localhost:58000/local-analysis/config/current-directory"

# 잘못됨 2: "path" 키 사용 ("directory"여야 함)
curl -X POST "http://localhost:58000/local-analysis/config/change-directory" \
  -H "Content-Type: application/json" \
  -d '{"path": "/Users/selmo/Documents"}'
```

### ✅ 올바른 사용 예시

#### 1. 현재 디렉토리 확인 (GET 요청)
```bash
curl "http://localhost:58000/local-analysis/config/current-directory"
```

#### 2. 디렉토리 변경 (directory 키 사용)
```bash
curl -X POST "http://localhost:58000/local-analysis/config/change-directory" \
  -H "Content-Type: application/json" \
  -d '{"directory": "/Users/selmo/Documents"}'
```

## 📋 전체 워크플로우 예시

### 1단계: 현재 위치 확인
```bash
# GET 요청으로 현재 디렉토리 확인
curl "http://localhost:58000/local-analysis/config/current-directory"
```

응답:
```json
{
  "current_directory": "/Users/selmo/Workspaces/DocExtract/backend",
  "parent_directory": "/Users/selmo/Workspaces/DocExtract",
  "contents": {
    "directories": [...],
    "files": [...],
    "total_directories": 5,
    "total_files": 10
  }
}
```

### 2단계: 작업 디렉토리 변경
```bash
# "directory" 키를 사용하여 POST 요청
curl -X POST "http://localhost:58000/local-analysis/config/change-directory" \
  -H "Content-Type: application/json" \
  -d '{"directory": "/Users/selmo/Documents"}'
```

응답:
```json
{
  "message": "디렉토리를 변경했습니다",
  "new_directory": "/Users/selmo/Documents"
}
```

### 3단계: 파일 분석
```bash
# POST 방식 (기본)
curl -X POST "http://localhost:58000/local-analysis/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "test_document.txt",
    "extractors": ["KeyBERT", "spaCy NER"]
  }'

# 🆕 directory 파라미터 사용 (결과 파일을 특정 디렉토리에 저장)
curl -X POST "http://localhost:58000/local-analysis/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "test_document.txt",
    "extractors": ["KeyBERT", "spaCy NER"],
    "directory": "/Users/selmo/analysis_results"
  }'

# 한글 파일명 처리 (POST 방식 권장)
curl -X POST "http://localhost:58000/local-analysis/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "연구보고서_최종본.pdf",
    "extractors": ["KeyBERT", "spaCy NER", "LLM"],
    "use_docling": true,
    "directory": "/Users/selmo/analysis_results"
  }'

# GET 방식 (영문 파일명)
curl "http://localhost:58000/local-analysis/analyze?file_path=test_document.txt&extractors=KeyBERT,spaCy%20NER"

# 🆕 GET 방식 + directory 파라미터 (한글 파일명 - URL 인코딩 필요)
curl -G "http://localhost:58000/local-analysis/analyze" \
  --data-urlencode "file_path=연구보고서_최종본.pdf" \
  --data-urlencode "extractors=KeyBERT,spaCy NER" \
  --data-urlencode "directory=/Users/selmo/analysis_results"
```

### 4단계: 결과 확인
```bash
curl "http://localhost:58000/local-analysis/result"
```

## 🛠️ 디버깅 팁

### API 엔드포인트 요약

| 엔드포인트 | 메서드 | 설명 | 주의사항 |
|---------|-------|------|---------|
| `/local-analysis/config/current-directory` | **GET** | 현재 디렉토리 조회 | POST 아님! |
| `/local-analysis/config/change-directory` | **POST** | 디렉토리 변경 | `{"directory": "..."}` 사용 |
| `/local-analysis/config/root` | **GET** | 루트 디렉토리 조회 | |
| `/local-analysis/config/extractors` | **GET** | 추출기 목록 조회 | |
| `/local-analysis/analyze` | **POST/GET** | 파일 분석 실행 | |
| `/local-analysis/status` | **GET** | 분석 상태 확인 | |
| `/local-analysis/result` | **GET** | 분석 결과 조회 | |
| `/local-analysis/reanalyze` | **POST** | 재분석 실행 | |

### 자주 발생하는 오류

1. **"Method Not Allowed"**: GET 요청을 해야 하는데 POST를 사용한 경우
2. **"디렉토리 경로가 필요합니다"**: `{"path": "..."}` 대신 `{"directory": "..."}` 사용
3. **"파일을 찾을 수 없습니다"**: 작업 디렉토리가 올바른지 확인
4. **한글 파일명 오류**: GET 방식에서 URL 인코딩 누락
5. **Docling 파서 오류**: Pydantic 호환성 문제 (자동 폴백됨)

### 🌏 한글 파일명 처리 가이드

**권장 방법 (POST 방식):**
```bash
# ✅ 안전한 방법 - JSON 내부에서 자동 UTF-8 처리
curl -X POST "http://localhost:58000/local-analysis/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "한글_파일명.pdf",
    "extractors": ["KeyBERT"]
  }'
```

**GET 방식 사용 시:**
```bash
# ❌ 잘못된 방법 - 한글 문자 깨짐
curl "http://localhost:58000/local-analysis/analyze?file_path=한글_파일명.pdf&extractors=KeyBERT"

# ✅ 올바른 방법 - URL 인코딩 사용
curl -G "http://localhost:58000/local-analysis/analyze" \
  --data-urlencode "file_path=한글_파일명.pdf" \
  --data-urlencode "extractors=KeyBERT"
```

### 🛠️ Docling 파서 문제 해결

**문제 증상**: 
```
ERROR - PDFDocling 파싱 실패: Error calling function `_serialize`: AttributeError: 'pydantic_core._pydantic_core.SerializationInfo' object has no attribute 'context'
WARNING - ⚠️ Pydantic 버전 호환성 문제가 감지되었습니다. 기본 PDF 파서를 사용합니다.
```

**해결 상태**: ✅ **자동 해결됨**
- 시스템이 자동으로 기본 PDF 파서로 폴백
- 분석은 정상적으로 완료됩니다
- 사용자 개입이 필요하지 않습니다

**수동 해결 (선택사항)**:
```bash
# 라이브러리 업데이트
pip install --upgrade docling docling-core

# 또는 Docling 사용 안함
curl -X POST "http://localhost:58000/local-analysis/analyze" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "document.pdf", "use_docling": false}'
```

## 🔧 테스트 스크립트

`test_local_analysis.sh` 파일을 실행하여 모든 엔드포인트를 테스트할 수 있습니다:

```bash
./test_local_analysis.sh
```

이 스크립트는 올바른 형식으로 모든 API를 호출합니다.
## 🆕 메타데이터 추출 (2025.08.31 업데이트)

### directory 파라미터를 사용한 메타데이터 추출

```bash
# GET 방식으로 메타데이터 추출 (디렉토리 지정)
curl -G "http://localhost:58000/local-analysis/metadata" \n  --data-urlencode "file_path=문서파일.pdf" \n  --data-urlencode "directory=/Users/selmo/metadata_results" \n  --data-urlencode "use_llm=true"

# POST 방식으로 메타데이터 추출 (디렉토리 지정)
curl -X POST "http://localhost:58000/local-analysis/metadata" \n  -H "Content-Type: application/json" \n  -d '{
    "file_path": "문서파일.pdf",
    "directory": "/Users/selmo/metadata_results",
    "use_llm": true,
    "force_reparse": false
  }'
```

### saved_files 응답 예시
API 응답에는 이제 `saved_files` 필드가 포함되어 생성된 모든 파일의 정보를 제공합니다:

```json
{
  "file_info": { ... },
  "metadata_by_parser": { ... },
  "output_directory": "/Users/selmo/metadata_results/문서파일",
  "saved_files": [
    {
      "type": "parsing_summary",
      "path": "/Users/selmo/metadata_results/문서파일/parsing_results.json",
      "description": "파싱 결과 종합 파일"
    },
    {
      "type": "markdown",
      "parser": "docling",
      "path": "/Users/selmo/metadata_results/문서파일/docling.md",
      "description": "Docling 파서로 생성된 Markdown 파일"
    },
    {
      "type": "markdown",
      "parser": "pdf_parser",
      "path": "/Users/selmo/metadata_results/문서파일/pymupdf4llm.md",
      "description": "PyMuPDF4LLM으로 생성된 Markdown 파일"
    }
  ]
}
```

