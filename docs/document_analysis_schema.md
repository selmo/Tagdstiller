# 문서 분석 결과 JSON 스키마 정의

## 개요
DocExtract 시스템의 문서 분석 결과를 담는 표준 JSON 형식을 정의합니다. 이 스키마는 로컬 파일 분석 API와 키워드 추출 결과 API에서 공통으로 사용됩니다.

## JSON 스키마 구조

### 최상위 구조
```json
{
  "file_info": { ... },
  "content_info": { ... },
  "document_structure": { ... },
  "document_summary": { ... },
  "extraction_info": { ... },
  "keywords": { ... },
  "analysis_status": "completed|failed|in_progress",
  "analysis_timestamp": "2025-08-25T08:28:58.532993",
  "analyzer_version": "1.0.0",
  "result_file": "/path/to/result.analysis.json",
  "error_message": "에러 발생 시 메시지"
}
```

### 1. file_info (파일 정보)
```json
{
  "file_info": {
    "path": "relative/path/to/file.txt",
    "absolute_path": "/full/system/path/to/file.txt",
    "size": 1162,
    "modified": "2025-08-25T08:23:45.880410",
    "extension": ".txt"
  }
}
```

**필드 설명:**
- `path`: 상대 경로 (사용자가 입력한 경로)
- `absolute_path`: 시스템 절대 경로
- `size`: 파일 크기 (바이트)
- `modified`: 파일 수정 시간 (ISO 8601 형식)
- `extension`: 파일 확장자

### 3. document_structure (문서 구조)
```json
{
  "document_structure": {
    "title": "문서의 주제목",
    "sections": [
      {
        "level": 1,
        "title": "1장. 서론",
        "start_position": 0,
        "end_position": 150,
        "page_number": 1,
        "subsections": [
          {
            "level": 2,
            "title": "1.1 연구 배경",
            "start_position": 50,
            "end_position": 120,
            "page_number": 1
          }
        ]
      }
    ],
    "headings": [
      {
        "level": 1,
        "text": "서론",
        "position": 25,
        "page_number": 1
      },
      {
        "level": 2,
        "text": "연구 배경",
        "position": 75,
        "page_number": 1
      }
    ],
    "table_of_contents": [
      {
        "title": "1장. 서론",
        "page_number": 1,
        "level": 1
      },
      {
        "title": "1.1 연구 배경",
        "page_number": 1,
        "level": 2
      }
    ],
    "total_pages": 10,
    "total_sections": 5,
    "max_section_level": 3
  }
}
```

**필드 설명:**
- `title`: 문서의 주제목
- `sections`: 계층적 섹션 구조 (장, 절)
- `headings`: 모든 제목들의 평면적 목록
- `table_of_contents`: 목차 정보
- `total_pages`: 전체 페이지 수
- `total_sections`: 전체 섹션 수
- `max_section_level`: 최대 섹션 레벨 깊이

### 4. document_summary (문서 요약)
```json
{
  "document_summary": {
    "title": "인공지능과 머신러닝의 발전",
    "abstract": "최근 몇 년간 인공지능과 머신러닝 기술이 급속도로 발전하고 있다...",
    "executive_summary": "핵심 내용을 요약한 경영진용 요약",
    "key_findings": [
      "딥러닝 기술이 이미지 인식에서 혁신적 성과를 보임",
      "대형 언어 모델이 텍스트 처리에서 인간 수준에 근접",
      "다양한 산업 분야에서 AI 도입이 가속화됨"
    ],
    "main_topics": [
      "딥러닝",
      "대형 언어 모델", 
      "컴퓨터 비전",
      "자연어 처리",
      "산업 응용"
    ],
    "conclusion": "이러한 기술들은 미래 사회의 패러다임을 바꿀 것으로 예상됩니다.",
    "document_type": "기술 보고서",
    "domain": "인공지능/IT",
    "complexity_level": "중급",
    "target_audience": "기술 전문가",
    "reading_time_minutes": 5
  }
}
```

**필드 설명:**
- `title`: 문서 제목
- `abstract`: 초록/요약
- `executive_summary`: 경영진용 요약
- `key_findings`: 주요 발견사항/결과
- `main_topics`: 주요 주제 목록
- `conclusion`: 결론
- `document_type`: 문서 유형 (보고서, 논문, 매뉴얼 등)
- `domain`: 전문 분야
- `complexity_level`: 복잡도 (초급/중급/고급)
- `target_audience`: 대상 독자
- `reading_time_minutes`: 예상 읽기 시간

### 5. content_info (콘텐츠 정보)
```json
{
  "content_info": {
    "length": 557,
    "word_count": 112,
    "line_count": 1
  }
}
```

**필드 설명:**
- `length`: 파싱된 텍스트의 문자 수
- `word_count`: 단어 개수 (공백 기준 분리)
- `line_count`: 줄 개수

### 3. extraction_info (추출 정보)
```json
{
  "extraction_info": {
    "extractors_used": ["keybert", "ner", "konlpy", "metadata"],
    "total_keywords": 35
  }
}
```

**필드 설명:**
- `extractors_used`: 사용된 키워드 추출기 목록
- `total_keywords`: 추출된 총 키워드 개수

### 4. keywords (키워드 결과)
추출기별로 그룹화된 키워드 배열:

```json
{
  "keywords": {
    "keybert": [
      {
        "keyword": "deep learning",
        "extractor_name": "keybert",
        "score": 0.7432,
        "category": "keybert_keyword",
        "start_position": null,
        "end_position": null,
        "context_snippet": "인공지능과 머신러닝의 발전 최근 몇 년간...",
        "page_number": null,
        "line_number": null,
        "column_number": null
      }
    ],
    "ner": [
      {
        "keyword": "GPT",
        "extractor_name": "ner",
        "score": 0.9,
        "category": "TECH",
        "start_position": 185,
        "end_position": 188,
        "context_snippet": "특히 GPT(Generative Pre-trained...",
        "page_number": 1,
        "line_number": 1,
        "column_number": 186
      }
    ],
    "konlpy": [
      {
        "keyword": "러닝",
        "extractor_name": "konlpy",
        "score": 1.0,
        "category": "noun",
        "start_position": 8,
        "end_position": 10,
        "context_snippet": "인공지능과 머신러닝의 발전 최근...",
        "page_number": 1,
        "line_number": 1,
        "column_number": 9
      }
    ],
    "metadata": [
      {
        "keyword": "핵심내용_딥러닝과 대형 언어 모델...",
        "extractor_name": "metadata",
        "score": 1.0,
        "category": "summary_core",
        "start_position": null,
        "end_position": null,
        "context_snippet": "딥러닝과 대형 언어 모델...",
        "page_number": null,
        "line_number": null,
        "column_number": null
      }
    ]
  }
}
```

### 키워드 객체 필드 설명

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `keyword` | string | ✓ | 추출된 키워드 텍스트 |
| `extractor_name` | string | ✓ | 추출기 이름 (keybert, ner, konlpy, metadata, llm) |
| `score` | float | ✓ | 키워드 점수 (0.0-1.0) |
| `category` | string | ✓ | 키워드 카테고리 |
| `start_position` | integer | - | 텍스트 내 시작 위치 (문자 인덱스) |
| `end_position` | integer | - | 텍스트 내 종료 위치 (문자 인덱스) |
| `context_snippet` | string | - | 키워드 주변 컨텍스트 텍스트 |
| `page_number` | integer | - | PDF 등에서 페이지 번호 |
| `line_number` | integer | - | 줄 번호 |
| `column_number` | integer | - | 컬럼 번호 |

### 5. analysis_status (분석 상태)
```json
{
  "analysis_status": "completed"
}
```

**가능한 값:**
- `completed`: 분석 완료
- `failed`: 분석 실패
- `in_progress`: 분석 진행 중

### 6. 메타데이터 필드
```json
{
  "analysis_timestamp": "2025-08-25T08:28:58.532993",
  "analyzer_version": "1.0.0",
  "result_file": "/path/to/result.analysis.json"
}
```

**필드 설명:**
- `analysis_timestamp`: 분석 수행 시간 (ISO 8601)
- `analyzer_version`: 분석기 버전
- `result_file`: 결과 파일이 저장된 경로 (로컬 분석 시)

### 7. 오류 처리
분석 실패 시 구조:
```json
{
  "file_info": {
    "path": "file.txt",
    "error": "파일을 찾을 수 없습니다"
  },
  "analysis_status": "failed",
  "error_message": "상세 오류 메시지",
  "analysis_timestamp": "2025-08-25T08:28:58.532993"
}
```

## 키워드 분류 체계

### 1. 의미적 카테고리 (Semantic Categories)

#### 개념적 키워드
- `concept_technical`: 기술 개념 (알고리즘, 방법론)
- `concept_theoretical`: 이론적 개념
- `concept_domain`: 도메인 전문 개념

#### 개체명 (Named Entities)
- `entity_person`: 인명
- `entity_organization`: 조직/기관명  
- `entity_location`: 지명
- `entity_product`: 제품/서비스명
- `entity_technology`: 기술명/도구명

#### 주제어 (Topics)
- `topic_main`: 주제어
- `topic_subtopic`: 부주제어
- `topic_domain`: 전문분야 용어

### 2. 구조적 카테고리 (Structural Categories)

#### 문서 구조 요소
- `structure_title`: 제목
- `structure_section`: 장/절 제목
- `structure_heading`: 소제목
- `structure_caption`: 캡션
- `structure_footnote`: 각주 내용

#### 메타데이터
- `meta_summary_core`: 핵심 내용 요약
- `meta_summary_intro`: 도입부 요약  
- `meta_summary_conclusion`: 결론부 요약
- `meta_key_finding`: 주요 발견사항
- `meta_document_type`: 문서 유형
- `meta_domain`: 전문 분야
- `meta_complexity`: 복잡도 지표

### 3. 추출기별 카테고리

#### KeyBERT
- `keybert_primary`: 주요 키워드 (상위 점수)
- `keybert_secondary`: 보조 키워드 (중간 점수)
- `keybert_related`: 관련 키워드 (낮은 점수)

#### spaCy NER
- `ner_person`: 인명 (PERSON)
- `ner_organization`: 조직 (ORG)
- `ner_location`: 지명 (GPE, LOC)
- `ner_misc`: 기타 개체명 (MISC)
- `ner_date`: 날짜/시간 (DATE, TIME)
- `ner_money`: 금액 (MONEY)
- `ner_quantity`: 수량 (QUANTITY)

#### KoNLPy (품사별)
- `konlpy_noun`: 명사
- `konlpy_verb`: 동사
- `konlpy_adjective`: 형용사
- `konlpy_adverb`: 부사
- `konlpy_proper_noun`: 고유명사

#### LLM 추출기
- `llm_keyword`: LLM 키워드
- `llm_concept`: LLM 개념어
- `llm_entity`: LLM 개체명
- `llm_topic`: LLM 주제어
- `llm_summary`: LLM 요약

#### 사용자 정의
- `custom_tag`: 사용자 지정 태그
- `custom_annotation`: 사용자 주석
- `custom_category`: 사용자 정의 분류

### 4. 중요도 레벨 (Priority Levels)
키워드에 추가적으로 중요도를 표시:
- `priority_critical`: 핵심 키워드
- `priority_high`: 중요 키워드  
- `priority_medium`: 보통 키워드
- `priority_low`: 참고 키워드

### 5. 신뢰도 레벨 (Confidence Levels)
추출 신뢰도를 표시:
- `confidence_high`: 높은 신뢰도 (0.8-1.0)
- `confidence_medium`: 보통 신뢰도 (0.5-0.8)
- `confidence_low`: 낮은 신뢰도 (0.0-0.5)

## JSON Schema (Draft 7)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "문서 분석 결과",
  "type": "object",
  "required": ["analysis_status", "analysis_timestamp"],
  "properties": {
    "file_info": {
      "type": "object",
      "properties": {
        "path": {"type": "string"},
        "absolute_path": {"type": "string"},
        "size": {"type": "integer"},
        "modified": {"type": "string", "format": "date-time"},
        "extension": {"type": "string"}
      }
    },
    "content_info": {
      "type": "object",
      "properties": {
        "length": {"type": "integer"},
        "word_count": {"type": "integer"},
        "line_count": {"type": "integer"}
      }
    },
    "document_structure": {
      "type": "object",
      "properties": {
        "title": {"type": "string"},
        "sections": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "level": {"type": "integer"},
              "title": {"type": "string"},
              "start_position": {"type": "integer"},
              "end_position": {"type": "integer"},
              "page_number": {"type": "integer"},
              "subsections": {
                "type": "array",
                "items": {"$ref": "#/properties/document_structure/properties/sections/items"}
              }
            }
          }
        },
        "headings": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "level": {"type": "integer"},
              "text": {"type": "string"},
              "position": {"type": "integer"},
              "page_number": {"type": "integer"}
            }
          }
        },
        "table_of_contents": {
          "type": "array", 
          "items": {
            "type": "object",
            "properties": {
              "title": {"type": "string"},
              "page_number": {"type": "integer"},
              "level": {"type": "integer"}
            }
          }
        },
        "total_pages": {"type": "integer"},
        "total_sections": {"type": "integer"},
        "max_section_level": {"type": "integer"}
      }
    },
    "document_summary": {
      "type": "object",
      "properties": {
        "title": {"type": "string"},
        "abstract": {"type": "string"},
        "executive_summary": {"type": "string"},
        "key_findings": {
          "type": "array",
          "items": {"type": "string"}
        },
        "main_topics": {
          "type": "array",
          "items": {"type": "string"}
        },
        "conclusion": {"type": "string"},
        "document_type": {"type": "string"},
        "domain": {"type": "string"},
        "complexity_level": {
          "type": "string",
          "enum": ["초급", "중급", "고급"]
        },
        "target_audience": {"type": "string"},
        "reading_time_minutes": {"type": "integer"}
      }
    },
    "extraction_info": {
      "type": "object",
      "properties": {
        "extractors_used": {
          "type": "array",
          "items": {"type": "string"}
        },
        "total_keywords": {"type": "integer"}
      }
    },
    "keywords": {
      "type": "object",
      "patternProperties": {
        "^(keybert|ner|konlpy|metadata|llm|structure|summary)$": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["keyword", "extractor_name", "score", "category"],
            "properties": {
              "keyword": {"type": "string"},
              "extractor_name": {"type": "string"},
              "score": {"type": "number", "minimum": 0, "maximum": 1},
              "category": {"type": "string"},
              "priority": {
                "type": "string", 
                "enum": ["critical", "high", "medium", "low"]
              },
              "confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"]
              },
              "start_position": {"type": ["integer", "null"]},
              "end_position": {"type": ["integer", "null"]},
              "context_snippet": {"type": ["string", "null"]},
              "page_number": {"type": ["integer", "null"]},
              "line_number": {"type": ["integer", "null"]},
              "column_number": {"type": ["integer", "null"]}
            }
          }
        }
      }
    },
    "analysis_status": {
      "type": "string",
      "enum": ["completed", "failed", "in_progress"]
    },
    "analysis_timestamp": {
      "type": "string",
      "format": "date-time"
    },
    "analyzer_version": {"type": "string"},
    "result_file": {"type": ["string", "null"]},
    "error_message": {"type": ["string", "null"]}
  }
}
```

## 사용 예시

### API 응답 예시
```http
POST /local_analysis/analyze_file
Content-Type: application/json

{
  "file_path": "documents/sample.pdf",
  "extractors": ["keybert", "ner"],
  "force_reanalyze": false
}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "file_info": {
    "path": "documents/sample.pdf",
    "absolute_path": "/full/path/documents/sample.pdf",
    "size": 2048,
    "modified": "2025-08-25T08:23:45.880410",
    "extension": ".pdf"
  },
  "content_info": {
    "length": 1200,
    "word_count": 200,
    "line_count": 50
  },
  "extraction_info": {
    "extractors_used": ["keybert", "ner"],
    "total_keywords": 15
  },
  "keywords": {
    "keybert": [...],
    "ner": [...]
  },
  "analysis_status": "completed",
  "analysis_timestamp": "2025-08-25T08:28:58.532993",
  "analyzer_version": "1.0.0"
}
```

## 버전 관리
- 현재 버전: 1.0.0
- 스키마 변경 시 analyzer_version 필드로 호환성 관리
- 하위 호환성을 위해 필수 필드 추가 시 기본값 제공