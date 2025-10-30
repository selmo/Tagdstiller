# Docling + OCR 통합 파서 테스트 가이드

## 📋 개요

Docling + OCR 통합 파서는 PDF 문서에서 다음을 수행합니다:

1. **Docling**: 문서 구조 및 텍스트 추출 (테이블, 헤더, 레이아웃 보존)
2. **OCR**: 이미지 영역에서 Tesseract OCR로 텍스트 추출
3. **태그 대체**: Markdown의 `<!-- image -->` 태그를 OCR 결과로 교체
4. **중복 제거**: 이미지 해시 기반으로 동일 이미지 스킵

## 🔧 사전 요구사항

### 1. OCR 라이브러리 설치 확인

```bash
python -c "import pytesseract; import cv2; print('✅ OCR 라이브러리 설치됨')"
```

### 2. Tesseract 엔진 및 언어 팩 확인

```bash
tesseract --version
tesseract --list-langs | grep -E "kor|eng"
```

### 3. 백엔드 서버 실행

```bash
cd /Users/selmo/Projects/Tagdstiller/backend-local
./start_local_backend.sh
```

서버가 http://localhost:58000 에서 실행 중이어야 합니다.

## 🧪 테스트 명령

### 기본 테스트 (Docling + OCR 파싱만)

```bash
FILE_PATH="/Users/selmo/TEMP/0007.pdf"
DIRECTORY="$(dirname "$FILE_PATH")"

curl -X POST 'http://localhost:58000/local-analysis/knowledge-graph' \
  -H 'Content-Type: application/json' \
  -d '{
        "file_path": "'"$FILE_PATH"'",
        "directory": "'"$DIRECTORY"'",
        "use_llm": false,
        "force_reparse": true
      }'
```

### 강제 재파싱 테스트

기존 결과를 무시하고 새로 파싱합니다:

```bash
curl -X POST 'http://localhost:58000/local-analysis/knowledge-graph' \
  -H 'Content-Type: application/json' \
  -d '{
        "file_path": "/Users/selmo/TEMP/0007.pdf",
        "directory": "/Users/selmo/TEMP",
        "use_llm": false,
        "force_reparse": true,
        "force_reanalyze": true
      }'
```

### LLM 분석 포함 테스트

Docling + OCR 파싱 후 LLM 구조 분석까지 수행:

```bash
curl -X POST 'http://localhost:58000/local-analysis/knowledge-graph' \
  -H 'Content-Type: application/json' \
  -d '{
        "file_path": "/Users/selmo/TEMP/0007.pdf",
        "directory": "/Users/selmo/TEMP",
        "use_llm": true,
        "force_reparse": true,
        "llm": {
          "enabled": true,
          "provider": "gemini",
          "model": "models/gemini-2.0-flash",
          "api_key": "YOUR_API_KEY",
          "base_url": "https://generativelanguage.googleapis.com",
          "max_tokens": 30000,
          "temperature": 0.1,
          "timeout": 600
        }
      }'
```

## 📂 출력 파일 구조

테스트 실행 후 다음 디렉토리 구조가 생성됩니다:

```
/Users/selmo/TEMP/0007/
├── docling_ocr/                    # Docling + OCR 파서 결과
│   ├── docling_ocr_text.txt        # 추출된 전체 텍스트
│   ├── docling_ocr_metadata.json   # 메타데이터 (OCR 통계 포함)
│   └── docling_ocr_structure.json  # 문서 구조 정보
├── docling/                         # 기존 Docling 파서 결과 (비교용)
│   ├── docling_text.txt
│   ├── docling_metadata.json
│   └── docling_structure.json
├── pdf_parser/                      # PDF 파서 결과 (비교용)
│   ├── pdf_parser_text.txt
│   ├── pdf_parser_metadata.json
│   └── pdf_parser_structure.json
├── docling_ocr.md                   # OCR 텍스트가 포함된 Markdown
├── docling.md                       # 기존 Docling Markdown (<!-- image --> 태그)
├── pymupdf4llm.md                   # PyMuPDF4LLM Markdown
└── parsing_results.json             # 모든 파서 종합 결과
```

## ✅ 결과 확인 방법

### 1. OCR 텍스트 추출 확인

```bash
# Docling + OCR 결과 확인
cat /Users/selmo/TEMP/0007/docling_ocr/docling_ocr_text.txt | head -50

# 기존 Docling 결과와 비교
diff <(cat /Users/selmo/TEMP/0007/docling/docling_text.txt) \
     <(cat /Users/selmo/TEMP/0007/docling_ocr/docling_ocr_text.txt)
```

### 2. Markdown 이미지 태그 대체 확인

```bash
# 기존: <!-- image --> 태그만 있음
grep "<!-- image -->" /Users/selmo/TEMP/0007/docling.md | wc -l

# 신규: OCR 텍스트로 대체됨
grep -A 3 "\[이미지 OCR" /Users/selmo/TEMP/0007/docling_ocr.md | head -20
```

### 3. 중복 이미지 처리 확인

백엔드 로그에서 "중복 이미지 스킵" 메시지 확인:

```bash
tail -f logs/backend.log | grep "중복 이미지"
```

또는 메타데이터에서 OCR 통계 확인:

```bash
cat /Users/selmo/TEMP/0007/docling_ocr/docling_ocr_metadata.json | jq '.ocr_images_count, .ocr_text_length'
```

### 4. 파서별 품질 점수 비교

```bash
cat /Users/selmo/TEMP/0007/parsing_results.json | jq '.parsing_results | to_entries[] | {parser: .key, quality: .value.quality_score, text_length: .value.text_length}'
```

## 🐛 문제 해결

### OCR 라이브러리 오류

```
ImportError: No module named 'pytesseract'
```

**해결:**

```bash
pip install pytesseract opencv-python pillow pymupdf
brew install tesseract tesseract-lang  # macOS
```

### Docling 임포트 오류

```
ImportError: cannot import name 'DocumentConverter' from 'docling'
```

**해결:**

```bash
pip install docling
```

### 중복 이미지가 스킵되지 않음

로그에서 이미지 해시를 확인하세요:

```bash
grep "이미지 OCR" logs/backend.log | grep -E "성공|스킵"
```

### Markdown 태그가 대체되지 않음

`docling_ocr.md` 파일에서 OCR 블록이 있는지 확인:

```bash
grep -c "\[이미지 OCR" /Users/selmo/TEMP/0007/docling_ocr.md
```

0이면 OCR이 실패한 것이므로 로그 확인:

```bash
grep "OCR 실행 실패" logs/backend.log
```

## 📊 성능 벤치마크

### 예상 처리 시간 (0007.pdf - 20MB, 18페이지 기준)

| 단계 | 소요 시간 | 설명 |
|------|----------|------|
| Docling 파싱 | ~30-60초 | 문서 구조 및 텍스트 추출 |
| 이미지 추출 | ~5-10초 | PDF에서 이미지 객체 추출 |
| OCR 처리 | ~2-5초/이미지 | Tesseract OCR 실행 |
| Markdown 생성 | ~1-2초 | 태그 대체 및 파일 저장 |
| **총 예상 시간** | ~2-5분 | 이미지 개수에 따라 변동 |

## 🎯 성공 기준

다음 조건이 모두 충족되어야 테스트 성공:

1. ✅ `docling_ocr.md` 파일이 생성됨
2. ✅ Markdown에 `<!-- image -->` 태그 대신 `[이미지 OCR]` 블록이 있음
3. ✅ OCR 텍스트 블록에 실제 텍스트가 포함됨 (비어있지 않음)
4. ✅ 메타데이터에 `ocr_images_count` 및 `ocr_text_length` 필드가 있음
5. ✅ 로그에 "중복 이미지 스킵" 메시지가 있음 (중복 이미지가 있는 경우)
6. ✅ `parsing_results.json`에서 `docling_ocr` 파서의 `quality_score`가 다른 파서보다 높음

## 📝 추가 테스트 케이스

### 1. 순수 이미지 PDF (스캔본)

텍스트가 전혀 없는 스캔 PDF:

```bash
curl -X POST 'http://localhost:58000/local-analysis/knowledge-graph' \
  -H 'Content-Type: application/json' \
  -d '{
        "file_path": "/path/to/scanned_document.pdf",
        "directory": "/path/to/output",
        "use_llm": false,
        "force_reparse": true
      }'
```

**예상 결과:** `docling_ocr` 파서가 OCR 전용 모드로 전환되어 모든 페이지를 OCR 처리

### 2. 하이브리드 PDF (텍스트 + 이미지)

텍스트와 이미지가 혼합된 일반 PDF:

```bash
curl -X POST 'http://localhost:58000/local-analysis/knowledge-graph' \
  -H 'Content-Type: application/json' \
  -d '{
        "file_path": "/path/to/hybrid_document.pdf",
        "directory": "/path/to/output",
        "use_llm": false,
        "force_reparse": true
      }'
```

**예상 결과:** Docling이 텍스트 추출, 이미지 영역만 OCR 처리

### 3. 대용량 PDF (100+ 페이지)

```bash
curl -X POST 'http://localhost:58000/local-analysis/knowledge-graph' \
  -H 'Content-Type: application/json' \
  -d '{
        "file_path": "/path/to/large_document.pdf",
        "directory": "/path/to/output",
        "use_llm": false,
        "force_reparse": true
      }' \
  --max-time 1800  # 30분 타임아웃
```

**주의:** 대용량 PDF는 처리 시간이 길어질 수 있습니다 (이미지 개수에 비례)

## 🚀 다음 단계

테스트 성공 후:

1. **다른 PDF 문서로 추가 테스트** (다양한 형식, 언어, 이미지 타입)
2. **성능 최적화** (병렬 OCR 처리, 캐싱, 이미지 크기 필터링)
3. **품질 향상** (OCR 전처리 알고리즘 튜닝, 언어 감지)
4. **UI 통합** (프론트엔드에서 OCR 진행률 표시)

## 📞 문의

문제 발생 시:
- 로그 파일: `logs/backend.log`
- 디버그 모드: `export DEBUG=1 && ./start_local_backend.sh`
- 이슈 보고: GitHub Issues