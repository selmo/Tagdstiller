# Tests 디렉토리 구조

이 디렉토리는 DocExtract 백엔드의 모든 테스트 관련 파일들을 포함합니다.

## 디렉토리 구조

```
tests/
├── README.md                 # 이 파일
├── __init__.py              # 테스트 패키지 초기화
├── conftest.py              # pytest 설정 및 공통 fixture
│
├── 테스트 파일들
├── test_configs.py          # 설정 관련 테스트
├── test_files.py            # 파일 관련 테스트
├── test_keywords.py         # 키워드 추출 테스트
├── test_parser.py           # 파서 테스트
├── test_projects.py         # 프로젝트 관련 테스트
├── test_prompts.py          # 프롬프트 템플릿 테스트
│
├── 출력 파일들
├── outputs/                 # 파서별 개별 결과 저장
│   ├── 20250829_173503_docling_148160b8/
│   │   ├── docling_document_structure.json
│   │   ├── docling_extracted_text.txt
│   │   ├── docling_metadata.json
│   │   └── docling_summary.json
│   └── ... (다른 파서 결과들)
│
└── debug_outputs/           # 디버그 및 로그 출력
    ├── 20250828_122231_8f5c880d/
    │   ├── debug_session.json
    │   ├── input_text.txt
    │   └── ... (디버그 파일들)
    └── llm/                 # LLM 프롬프트/응답 로그
        └── 20250829/
            └── 180254_local_metadata_langchain_038d9cbf/
                ├── meta.json
                ├── prompt.txt
                └── response.txt
```

## 파일 설명

### 테스트 파일
- `test_*.py`: 각 모듈별 단위 테스트 및 통합 테스트
- `conftest.py`: pytest 공통 설정, fixture 정의
- `test_prompts.py`: 프롬프트 템플릿 시스템 테스트

### 출력 디렉토리
- `outputs/`: 파서별 개별 결과 저장
  - 각 파서별로 독립적인 디렉토리 생성
  - 텍스트, 구조, 메타데이터, 요약 파일 포함
  
- `debug_outputs/`: 디버그 정보 저장
  - 키워드 추출 과정의 중간 결과물
  - LLM 프롬프트/응답 로그
  - 성능 및 분석 데이터

## 테스트 실행

```bash
# 모든 테스트 실행
pytest tests/

# 특정 테스트 파일 실행
pytest tests/test_parser.py

# 커버리지 리포트와 함께 실행
pytest tests/ --cov=services --cov=extractors

# 특정 테스트 함수 실행
pytest tests/test_prompts.py::test_template_loading
```

## 파일 정리 규칙

1. **테스트 파일**: `test_*.py` 형식으로 명명
2. **출력 파일**: `outputs/` 디렉토리에 자동 저장
3. **디버그 파일**: `debug_outputs/` 디렉토리에 자동 저장
4. **임시 파일**: 테스트 완료 후 필요시 정리

## 주의사항

- 출력 디렉토리의 파일들은 테스트 실행 시 자동으로 생성됩니다
- 대용량 출력 파일들은 `.gitignore`에 추가되어 있습니다
- 디버그 모드는 환경변수 `ENABLE_KEYWORD_DEBUG=true`로 활성화됩니다