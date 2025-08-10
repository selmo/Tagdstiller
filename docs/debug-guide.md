# 🐛 DocExtract 디버그 로깅 가이드

> **고급 디버그 로깅 시스템 완전 가이드**

## 📚 목차
1. [개요](#개요)
2. [활성화 방법](#활성화-방법)
3. [로깅 단계](#로깅-단계)
4. [생성 파일](#생성-파일)
5. [HTML 리포트](#html-리포트)
6. [실제 사용 예제](#실제-사용-예제)
7. [성능 최적화](#성능-최적화)
8. [문제 해결](#문제-해결)

---

## 개요

DocExtract의 **고급 디버그 로깅 시스템**은 키워드 추출 과정의 모든 단계를 상세히 기록하고 분석할 수 있도록 설계된 포괄적인 디버깅 도구입니다.

### 주요 특징
- 🔄 **8단계 상세 추적**: 추출 시작부터 최종 결과까지 모든 중간 과정 기록
- 📁 **자동 파일 저장**: JSON, 텍스트, HTML 형태로 결과 저장
- 🎯 **4개 추출기 지원**: KeyBERT, spaCy NER, LLM, KoNLPy 완전 지원
- 🚀 **성능 영향 최소화**: 비활성화 시 성능 영향 없음

---

## 활성화 방법

### 환경변수 설정
```bash
# 디버그 모드 활성화
export ENABLE_KEYWORD_DEBUG=true

# 백엔드 서버 시작
cd /Users/selmo/Workspaces/DocExtract
./scripts/start_backend.sh
```

### 확인 방법
서버 시작 시 다음 메시지가 출력되면 디버그 모드가 활성화된 것입니다:
```
🐛 디버그 모드 활성화 - 세션: a1b2c3d4
📁 로그 저장 위치: /Users/selmo/Workspaces/DocExtract/backend/debug_logs/20250807_154520_a1b2c3d4
```

---

## 로깅 단계

### 1. 추출 시작 (`start_extraction`)
키워드 추출 프로세스 시작 시 기록되는 정보:
- **파일 정보**: 이름, 크기, ID, 미리보기
- **텍스트 통계**: 길이, 단어 수, 문장 수, 고유 단어 수, 다양성 지수
- **추출기 설정**: 모든 설정 매개변수

### 2. 전처리 (`log_preprocessing`)
텍스트 정제 과정 기록:
- **원본 vs 정제된 텍스트** 비교
- **전처리 단계**: `clean_text`, `normalize_unicode`, `remove_extra_whitespace` 등
- **변화율**: 텍스트 길이 변화 비율

### 3. 후보 생성 (`log_candidate_generation`)
키워드 후보 추출 과정:
- **생성 방법별 후보 목록**:
  - KeyBERT: `CountVectorizer_ngram_(1, 2)`
  - spaCy NER: `spacy_named_entity_recognition`
  - LLM: `llm_generation`
  - KoNLPy: `konlpy_Okt_nouns`
- **후보 통계**: 총 개수, 고유 개수, 평균 길이, 단일어/복합어 비율

### 4. 임베딩 계산 (`log_embeddings`)
벡터 임베딩 생성 과정:
- **모델 정보**: 사용된 모델명 (예: `all-MiniLM-L6-v2`)
- **임베딩 차원**: 문서 및 후보 임베딩 shape
- **임베딩 통계**: 평균, 표준편차, 노름 값

### 5. 유사도 계산 (`log_similarity_calculation`)
유사도/점수 계산 과정:
- **계산 방법**:
  - KeyBERT: 코사인 유사도
  - spaCy NER: 신뢰도 점수
  - LLM: 생성된 점수
  - KoNLPy: 빈도 기반 점수
- **분포 통계**: 최소/최대/평균/중앙값
- **상위/하위 결과**: Top 10, Bottom 5

### 6. 알고리즘 적용 (`log_algorithm_application`)
최종 키워드 선택 알고리즘:
- **KeyBERT**: MMR (Maximal Marginal Relevance), Max Sum Similarity
- **LLM**: 생성 및 파싱 알고리즘
- **매개변수**: diversity, nr_candidates, temperature 등
- **선택/제외된 키워드** 목록

### 7. 위치 분석 (`log_position_analysis`)
키워드 위치 매핑:
- **텍스트 내 위치**: 시작/끝 문자 위치
- **페이지/줄 번호**: PDF, 문서 구조 기반
- **컨텍스트**: 키워드 주변 50자 텍스트
- **커버리지 통계**: 위치 찾은 키워드 비율

### 8. 최종 결과 (`log_final_results`)
추출 완료 후 최종 정보:
- **최종 키워드 목록**: 점수, 카테고리, 위치 정보
- **성능 통계**: 추출 시간, 초당 키워드 수
- **품질 지표**: 평균 점수, 분포

---

## 생성 파일

### 디렉토리 구조
```
debug_logs/
└── 20250807_154520_a1b2c3d4/          # 타임스탬프_세션ID
    ├── debug_session.json              # 전체 세션 데이터
    ├── input_text.txt                  # 원본 입력 텍스트
    ├── keybert_preprocessed.txt         # KeyBERT 전처리된 텍스트
    ├── keybert_candidates.json         # KeyBERT 후보 키워드
    ├── keybert_similarities.json       # KeyBERT 유사도 계산
    ├── keybert_MMR_results.json        # KeyBERT MMR 알고리즘 결과
    ├── keybert_positions.json          # KeyBERT 위치 분석
    ├── keybert_summary.json            # KeyBERT 요약
    ├── spacy_ner_candidates.json       # spaCy NER 개체명 후보
    ├── spacy_ner_positions.json        # spaCy NER 위치 분석
    ├── llm_ollama_generation_results.json  # LLM 생성 결과
    ├── konlpy_similarities.json        # KoNLPy 빈도 분석
    └── summary_report.html             # 시각적 요약 리포트 ⭐
```

### 주요 파일 설명

#### `debug_session.json`
전체 세션의 모든 단계별 데이터가 포함된 메인 파일:
```json
{
  "session_info": {
    "session_id": "a1b2c3d4",
    "timestamp": "20250807_154520",
    "start_time": "2025-08-07T15:45:20.123456",
    "end_time": "2025-08-07T15:45:25.789012",
    "total_time": 5.665556
  },
  "extraction_steps": [
    {
      "step": "start_extraction",
      "extractor": "keybert",
      "timestamp": "2025-08-07T15:45:20.123456",
      "file_info": { ... },
      "text_stats": { ... }
    },
    ...
  ]
}
```

#### `*_candidates.json`
각 추출기별 후보 키워드 생성 결과:
```json
{
  "method": "CountVectorizer_ngram_(1, 2)",
  "count": 247,
  "candidates": ["인공지능", "머신러닝", "딥러닝", "자연어 처리", ...]
}
```

#### `*_similarities.json`
유사도 또는 점수 계산 결과:
```json
{
  "method": "cosine",
  "results": [
    {"candidate": "인공지능", "similarity": 0.856},
    {"candidate": "머신러닝", "similarity": 0.743},
    ...
  ]
}
```

---

## HTML 리포트

### 자동 생성 리포트
키워드 추출 완료 시 `summary_report.html` 파일이 자동 생성됩니다.

### 리포트 내용
- **세션 정보**: 추출 시간, 사용된 추출기
- **추출기별 결과**: 각 추출기의 최종 키워드 목록
- **키워드 점수**: 상위 키워드와 점수 표시
- **생성된 파일 목록**: 추가 분석을 위한 파일 링크

### 브라우저에서 보기
```bash
# 생성된 HTML 리포트 열기
open debug_logs/20250807_154520_a1b2c3d4/summary_report.html

# 또는 웹 브라우저에서 직접 열기
```

---

## 실제 사용 예제

### 1. 디버그 모드 활성화 및 키워드 추출
```bash
# 환경변수 설정
export ENABLE_KEYWORD_DEBUG=true

# 백엔드 서버 시작
./scripts/start_backend.sh

# 프론트엔드에서 키워드 추출 실행
# 또는 API 직접 호출
curl -X POST "http://localhost:58000/projects/1/extract_keywords/" \
     -H "Content-Type: application/json" \
     -d '{"extractors": ["keybert", "spacy_ner"]}'
```

### 2. 서버 로그 확인
```bash
tail -f backend.log
```

서버 로그에서 다음과 같은 디버그 메시지 확인:
```
🐛 디버그 모드 활성화 - 세션: a1b2c3d4
🐛 [keybert] 추출 시작 - 텍스트 길이: 1247자
🐛 [keybert] 전처리 완료 - 1247 → 1203자
🐛 [keybert] 후보 생성 완료 - CountVectorizer_ngram_(1, 2): 247개
🐛 [keybert] 임베딩 완료 - 모델: all-MiniLM-L6-v2
🐛 [keybert] 유사도 계산 완료 - cosine, 범위: 0.123~0.856
🐛 [keybert] MMR 적용 완료 - 247 → 10개
🐛 [keybert] 위치 분석 완료 - 8/10개 위치 확인
🐛 [keybert] 추출 완료 - 8개 키워드, 2.34초
🐛 디버그 세션 저장 완료: debug_logs/20250807_154520_a1b2c3d4/debug_session.json
📊 요약 리포트: debug_logs/20250807_154520_a1b2c3d4/summary_report.html
```

### 3. 결과 분석
```bash
# 디렉토리 확인
ls -la debug_logs/20250807_154520_a1b2c3d4/

# 주요 결과 파일 확인
cat debug_logs/20250807_154520_a1b2c3d4/keybert_summary.json

# HTML 리포트 열기
open debug_logs/20250807_154520_a1b2c3d4/summary_report.html
```

---

## 성능 최적화

### 디스크 사용량
- 세션당 평균 **1-5MB** (텍스트 크기에 따라)
- 임베딩 저장 시 추가 **10-50MB** (선택사항)

### 메모리 사용량
- 디버그 모드 활성화 시 추가 **10-20MB**
- 세션 데이터는 메모리에 일시 보관 후 파일 저장

### 처리 시간
- 디버그 모드 비활성화: **성능 영향 없음**
- 디버그 모드 활성화: **10-20% 추가 시간** (파일 I/O 포함)

### 최적화 팁
```bash
# 임베딩 저장 비활성화 (용량 절약)
export SAVE_EMBEDDINGS=false

# 디스크 공간 절약을 위한 정기적 정리
find debug_logs -type d -mtime +7 -exec rm -rf {} +
```

---

## 문제 해결

### Q: 디버그 파일이 생성되지 않아요
**A:** 환경변수 확인:
```bash
echo $ENABLE_KEYWORD_DEBUG  # "true" 출력되어야 함
```

### Q: 서버 시작 시 pandas 오류가 발생해요
**A:** 이미 해결됨. debug_logger.py에서 pandas 의존성 제거됨.

### Q: 디스크 공간이 부족해요
**A:** 오래된 디버그 파일 정리:
```bash
# 7일 이상된 디버그 로그 삭제
find debug_logs -type d -mtime +7 -exec rm -rf {} +

# 또는 전체 디버그 로그 삭제
rm -rf debug_logs
```

### Q: 특정 추출기만 디버깅하고 싶어요
**A:** 현재는 모든 추출기를 동시에 디버깅합니다. 필요시 코드 수정으로 선택적 디버깅 가능합니다.

### Q: HTML 리포트가 제대로 열리지 않아요
**A:** 브라우저 보안 설정 확인:
```bash
# 다른 브라우저로 시도
firefox debug_logs/SESSION/summary_report.html
```

---

## 고급 활용

### 연구 목적 활용
- 다양한 알고리즘 매개변수 비교 분석
- 모델별 성능 벤치마킹
- 키워드 추출 품질 평가

### 개발 디버깅
- 새로운 추출기 개발 시 단계별 검증
- 성능 병목 지점 파악
- 알고리즘 튜닝 효과 측정

### 사용자 지원
- 키워드 추출 결과 개선을 위한 상세 분석
- 특정 문서 유형에 최적화된 설정 발견

---

**작성일**: 2025년 8월 7일  
**DocExtract 프로젝트**: 고급 디버그 로깅 시스템 완전 가이드