# 문서 메타데이터 스키마 정의 v1.0

## 목차
1. [개요](#개요)
2. [기본 메타데이터](#기본-메타데이터)
   - [필수 필드](#필수-필드)
   - [선택 필드](#선택-필드)
3. [문서 구조 메타데이터](#문서-구조-메타데이터)
4. [값 도메인 정의](#값-도메인-정의)
5. [검증 규칙](#검증-규칙)
6. [구현 예시](#구현-예시)

---

## 개요

이 문서는 문서 관리 시스템을 위한 표준화된 메타데이터 스키마를 정의합니다. Dublin Core 표준을 기반으로 하며, 문서 구조 분석을 위한 확장 필드를 포함합니다.

### 버전 정보
- **버전**: 1.0
- **작성일**: 2025-08-28
- **표준 준거**: Dublin Core (DC), Dublin Core Terms (DCTerms)
- **인코딩**: UTF-8

---

## 기본 메타데이터

### 필수 필드

| 필드명 | 설명 | 타입 | 예시 |
|--------|------|------|------|
| **dc:title** | 문서 제목 | String(500) | "온톨로지 설계 가이드라인" |
| **dc:identifier** | 고유 식별자 | String | "DOI:10.1234/example.2025" |
| **dc:creator** | 주 저작자 | String(200) | "홍길동" |
| **dc:type** | 자원 유형 | Enum | "Text" |
| **dc:format** | MIME 타입 | String | "application/pdf" |
| **dc:language** | 언어 코드 | String | "ko" |
| **dcterms:created** | 생성일 | DateTime | "2025-01-15T09:30:00+09:00" |

### 선택 필드

#### 설명 정보
| 필드명 | 설명 | 타입 | 예시 |
|--------|------|------|------|
| **dc:description** | 문서 요약 | String(2000) | "온톨로지 설계 가이드" |
| **dc:subject** | 주제어/키워드 | Array[String] | ["온톨로지", "메타데이터"] |
| **dc:publisher** | 발행 기관 | String(200) | "한국정보과학회" |
| **dc:contributor** | 기여자 | Array[String] | ["김철수", "이영희"] |

#### 권한 정보
| 필드명 | 설명 | 타입 | 예시 |
|--------|------|------|------|
| **dc:rights** | 저작권 | String | "CC BY 4.0" |
| **dcterms:accessRights** | 접근 권한 | Enum | "public" |

#### 시간 정보
| 필드명 | 설명 | 타입 | 예시 |
|--------|------|------|------|
| **dcterms:modified** | 수정일 | DateTime | "2025-08-28T14:45:30+09:00" |
| **dcterms:available** | 공개일 | Date | "2025-09-01" |

#### 관계 정보
| 필드명 | 설명 | 타입 | 예시 |
|--------|------|------|------|
| **dc:source** | 원본 출처 | Array[String] | ["원본보고서.pdf"] |
| **dc:relation** | 관련 자원 | Array[String] | ["DOI:10.1234/related"] |

#### 파일 정보
| 필드명 | 설명 | 타입 | 예시 |
|--------|------|------|------|
| **file:name** | 파일명 | String(255) | "guide_2025.pdf" |
| **file:size** | 파일 크기(bytes) | Integer | 2048576 |
| **doc:pageCount** | 페이지 수 | Integer | 150 |

---

## 문서 구조 메타데이터

### 구조 단위 정의

```yaml
doc:structureUnit:
  id: "string"                    # 고유 식별자
  type: "string"                  # 구조 타입 (chapter, section, note 등)
  title: "string"                  # 제목
  
  # 관계 정의
  relations:
    parent: "string"              # 상위 구조 ID
    children: ["string"]          # 하위 구조 IDs
    previous: "string"            # 이전 구조 ID
    next: "string"                # 다음 구조 ID
    
  # 내용 정보
  content:
    keywords: ["string"]          # 키워드
    abstract: "string"            # 요약
    pageRange:                    # 페이지 범위
      start: "integer"
      end: "integer"
```

### 관계 타입

#### 구조적 관계
- `contains`: 포함 관계
- `precedes`: 선행 관계
- `follows`: 후행 관계

#### 의미적 관계
- `references`: 참조
- `extends`: 확장/상세화
- `requires`: 선행 필수

### 관계 정의

```yaml
doc:relationship:
  source: "string"          # 시작 단위 ID
  target: "string"          # 대상 단위 ID
  type: "string"            # 관계 타입
```

---

## 값 도메인 정의

### dc:type (자원 유형)
- `Text`: 텍스트 문서
- `Dataset`: 데이터셋
- `Image`: 이미지
- `Software`: 소프트웨어
- `Sound`: 음향
- `Collection`: 컬렉션

### dc:format (MIME 타입)
- `application/pdf`
- `text/html`
- `text/plain`
- `application/json`
- `application/xml`

### dc:language (언어 코드)
- `ko`: 한국어
- `en`: 영어
- `ja`: 일본어
- `zh`: 중국어

### dcterms:accessRights (접근 권한)
- `public`: 공개
- `restricted`: 제한
- `internal`: 내부용

### dc:rights (라이선스)
- `CC BY 4.0`: 크리에이티브 커먼즈
- `Copyright`: 저작권 보유
- `Public Domain`: 공개 도메인

---

## 검증 규칙

### 필수 필드
- dc:title
- dc:identifier
- dc:creator
- dc:type
- dc:format
- dc:language
- dcterms:created

### 데이터 타입
- **String**: UTF-8 인코딩
- **DateTime**: ISO 8601 형식 (예: 2025-08-28T10:30:00+09:00)
- **Date**: YYYY-MM-DD 형식
- **Integer**: 64-bit signed
- **Array**: JSON 배열 형식

### 제약 조건
- `dc:identifier`: 유일값
- `dcterms:modified`: `dcterms:created`보다 이후
- 문자열 필드: 최대 길이 준수

---

---

## 🚀 구현 상태

### ✅ 완전 구현됨 (2025-08-28)

이 메타데이터 스키마는 DocExtract 시스템에서 **완전히 구현**되어 실제 사용 중입니다.

#### 구현된 기능
- **자동 메타데이터 추출**: 파일 업로드 시 자동으로 Dublin Core 메타데이터 생성
- **스키마 준수 API**: `/files/{file_id}/metadata` 및 `/projects/{project_id}/files/{file_id}/metadata` 엔드포인트
- **스마트 폴백 시스템**: 메타데이터 누락 시 적절한 기본값 자동 생성
- **다중 네임스페이스**: dc:, dcterms:, doc:, processing:, file: 네임스페이스 완전 지원
- **타입 변환**: 문자열→배열, 타임스탬프→ISO 8601 등 자동 변환

#### 지원 파일 형식
- PDF, DOCX, TXT, HTML, Markdown
- 자동 MIME 타입 감지 및 Dublin Core 타입 매핑

#### 실제 API 응답 예시
```bash
curl "http://localhost:58000/files/1/metadata"
```

```json
{
  "@context": "http://purl.org/dc/terms/",
  "dc:title": "test_document.txt",
  "dc:identifier": "file-1-adf12f58",
  "dc:creator": "Unknown",
  "dc:type": "Text", 
  "dc:format": "text/plain",
  "dc:language": "ko",
  "dcterms:accessRights": "public",
  "file:name": "test_document.txt",
  "file:size": 1162,
  "dcterms:extent": "1162 bytes",
  "dcterms:medium": "digital",
  "dcterms:alternative": "test_document.txt",
  "dcterms:isPartOf": "project_1",
  "dcterms:hasFormat": ".txt",
  "doc:supported": "yes",
  "processing:extractionDate": "2025-08-28T02:01:20.771729",
  "processing:appVersion": "1.0.0",
  "processing:parseStatus": "success"
}
```

#### 구현 특징
- **Null 값 자동 제외**: null 또는 빈 문자열 값은 응답에서 자동 제외
- **고유 식별자 생성**: 파일 ID와 UUID 조합으로 고유 식별자 자동 생성
- **언어 자동 감지**: 문서 내용 분석으로 언어 코드 자동 설정
- **동적 프로젝트 연결**: `dcterms:isPartOf`에 프로젝트 ID 자동 매핑

---

## 구현 예시

### 기본 문서 메타데이터
```json
{
  "@context": "http://purl.org/dc/terms/",
  "dc:title": "온톨로지 설계 가이드라인",
  "dc:identifier": "DOI:10.1234/ontology.2025",
  "dc:creator": "홍길동",
  "dc:type": "Text",
  "dc:format": "application/pdf",
  "dc:language": "ko",
  "dc:subject": ["온톨로지", "메타데이터", "시맨틱웹"],
  "dc:publisher": "한국정보과학회",
  "dc:rights": "CC BY 4.0",
  "dcterms:created": "2025-01-15T09:30:00+09:00",
  "dcterms:modified": "2025-08-28T14:45:30+09:00",
  "dcterms:accessRights": "public",
  "file:name": "ontology_guide_2025.pdf",
  "file:size": 2048576,
  "doc:pageCount": 150
}
```

### 구조화된 문서 예시
```json
{
  "dc:title": "온톨로지 설계 가이드",
  "dc:identifier": "DOI:10.1234/ontology.2025",
  
  "doc:structures": [
    {
      "id": "ch01",
      "type": "chapter",
      "title": "서론",
      "relations": {
        "parent": null,
        "children": ["sec01-1", "sec01-2"],
        "previous": null,
        "next": "ch02"
      },
      "content": {
        "keywords": ["온톨로지", "개요"],
        "abstract": "온톨로지 기본 개념 소개",
        "pageRange": {"start": 1, "end": 30}
      }
    },
    {
      "id": "sec01-1",
      "type": "section",
      "title": "온톨로지 정의",
      "relations": {
        "parent": "ch01",
        "children": [],
        "previous": null,
        "next": "sec01-2"
      },
      "content": {
        "keywords": ["정의", "개념"],
        "pageRange": {"start": 3, "end": 10}
      }
    }
  ],
  
  "doc:relationships": [
    {
      "source": "sec01-1",
      "target": "ch03",
      "type": "references"
    }
  ]
}
```

### RDF/Turtle 표현
```turtle
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix dcterms: <http://purl.org/dc/terms/> .

<http://example.org/doc/001>
  dc:title "온톨로지 설계 가이드라인" ;
  dc:identifier "DOI:10.1234/ontology.2025" ;
  dc:creator "홍길동" ;
  dc:type "Text" ;
  dc:format "application/pdf" ;
  dc:language "ko" ;
  dcterms:created "2025-01-15T09:30:00+09:00" .
```