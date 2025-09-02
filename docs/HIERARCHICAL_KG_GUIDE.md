# 🏗️ 계층적 Knowledge Graph 시스템 가이드

DocExtract의 계층적 KG 시스템은 **문서 구조 정보**를 기반으로 지식 그래프를 구축합니다. 문서의 섹션, 테이블, 이미지 등 구조적 요소와 그 안에서 발견된 엔티티들 간의 관계를 명확히 표현합니다.

## 🎯 주요 특징

### 1. **문서 구조 기반 계층**
```
Document (문서)
├── Section (섹션)
│   ├── Subsection (하위섹션)
│   └── Keywords/Entities (키워드/엔티티)
├── Table (테이블)
│   └── Keywords/Entities (테이블 내 엔티티)
├── Image (이미지)
│   └── Keywords/Entities (캡션/메타데이터 엔티티)
└── List (목록)
    └── Keywords/Entities (목록 항목 엔티티)
```

### 2. **구조별 엔티티 매핑**
- **섹션에서 발견된 엔티티**: `Section → MENTIONS → Technology`
- **테이블에서 발견된 엔티티**: `Table → DESCRIBES → Database`  
- **이미지에서 발견된 엔티티**: `Image → DEPICTS → Concept`

### 3. **계층적 관계 표현**
- `CONTAINS_STRUCTURE`: 문서가 구조 요소를 포함
- `MENTIONS/DESCRIBES/DEPICTS`: 구조 요소가 엔티티를 언급/설명/묘사
- `INTEGRATES_WITH/CONNECTS_TO`: 엔티티 간 도메인별 관계

## 📊 결과 구조

### 기본 엔티티 구조
```json
{
  "id": "technology_hash_section_id_extractor",
  "type": "Technology",
  "properties": {
    "text": "FastAPI",
    "domain": "technical",
    "source_structure": "section_doc_123_1",
    "source_structure_type": "Section",
    "extractor": "llm",
    "hierarchical_entity": true,
    "extraction_context": {
      "context": "FastAPI: 고성능 Python 웹 프레임워크",
      "structure_type": "Section"
    }
  }
}
```

### 계층적 관계 구조
```json
{
  "source": "section_doc_123_1",
  "target": "technology_hash_section_id_llm",
  "type": "RELATED_TO", 
  "properties": {
    "relationship_name": "MENTIONS",
    "extraction_method": "llm",
    "context_snippet": "FastAPI: 고성능 Python 웹 프레임워크",
    "hierarchical_relationship": true,
    "domain": "technical"
  }
}
```

## 🚀 사용 방법

### 1. 계층적 KG 생성
```bash
# 기본 사용법 (자동 Memgraph 저장)
curl -X POST "http://localhost:8000/local-analysis/knowledge-graph" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "docs/api_guide.md"}'

# 강제 재생성
curl -X POST "http://localhost:8000/local-analysis/knowledge-graph" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "docs/api_guide.md", "force_rebuild": true}'
```

### 2. 계층적 관계 조회
```bash
# 특정 문서의 모든 구조 요소 조회
curl -X POST "http://localhost:8000/memgraph/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "MATCH (d:Document {path: \"docs/api_guide.md\"})-[:CONTAINS_STRUCTURE]->(s) RETURN d, s"
  }'

# 섹션별 엔티티 조회
curl -X POST "http://localhost:8000/memgraph/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "MATCH (s:Section)-[:RELATED_TO]->(e) WHERE s.title CONTAINS \"기술 스택\" RETURN s.title, e.type, e.text"
  }'

# 테이블에서 발견된 엔티티 조회
curl -X POST "http://localhost:8000/memgraph/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "MATCH (t:Table)-[:RELATED_TO]->(e) RETURN t.content, e.type, e.text, e.score ORDER BY e.score DESC"
  }'
```

### 3. 구조적 계층 분석
```bash
# 문서의 전체 구조 계층 조회
curl -X POST "http://localhost:8000/memgraph/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "MATCH path = (d:Document)-[:CONTAINS_STRUCTURE*]->(leaf) WHERE NOT (leaf)-[:CONTAINS_STRUCTURE]->() RETURN path"
  }'

# 특정 구조 요소의 모든 하위 엔티티 조회
curl -X POST "http://localhost:8000/memgraph/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "MATCH (s:Section {title: \"2.1 백엔드 프레임워크\"})-[:RELATED_TO]->(e) RETURN e.type, e.text, e.extraction_context"
  }'
```

## 📈 실제 예시

### 입력 문서 (Markdown)
```markdown
# API 개발 가이드

## 2. 기술 스택

### 2.1 백엔드 프레임워크
- **FastAPI**: 고성능 Python 웹 프레임워크
- **SQLAlchemy**: 데이터베이스 ORM

### 2.2 데이터베이스

| 데이터베이스 | 용도 | 장점 |
|-------------|------|------|
| PostgreSQL  | 메인 DB | ACID 준수, 확장성 |
| Redis       | 캐싱 | 고속 인메모리 저장 |
```

### 생성되는 계층적 KG 구조

#### **1. 문서 구조 엔티티**
```json
[
  {
    "id": "doc_123abc",
    "type": "Document",
    "properties": {"title": "API 개발 가이드", "hierarchical_root": true}
  },
  {
    "id": "section_doc_123abc_1", 
    "type": "Section",
    "properties": {"title": "2. 기술 스택", "level": 2}
  },
  {
    "id": "section_doc_123abc_2",
    "type": "Section", 
    "properties": {"title": "2.1 백엔드 프레임워크", "level": 3}
  },
  {
    "id": "table_doc_123abc_0",
    "type": "Table",
    "properties": {"row_count": 3, "column_count": 3}
  }
]
```

#### **2. 구조 기반 엔티티**
```json
[
  {
    "id": "technology_fastapi_section2_llm",
    "type": "Technology",
    "properties": {
      "text": "FastAPI",
      "source_structure": "section_doc_123abc_2",
      "source_structure_type": "Section",
      "hierarchical_entity": true
    }
  },
  {
    "id": "database_postgresql_table0_llm",
    "type": "Database", 
    "properties": {
      "text": "PostgreSQL",
      "source_structure": "table_doc_123abc_0",
      "source_structure_type": "Table",
      "hierarchical_entity": true
    }
  }
]
```

#### **3. 계층적 관계**
```json
[
  {
    "source": "doc_123abc",
    "target": "section_doc_123abc_1",
    "type": "CONTAINS_STRUCTURE",
    "properties": {"relationship_name": "CONTAINS_SECTION"}
  },
  {
    "source": "section_doc_123abc_2", 
    "target": "technology_fastapi_section2_llm",
    "type": "RELATED_TO",
    "properties": {
      "relationship_name": "MENTIONS",
      "hierarchical_relationship": true
    }
  },
  {
    "source": "table_doc_123abc_0",
    "target": "database_postgresql_table0_llm", 
    "type": "RELATED_TO",
    "properties": {
      "relationship_name": "DESCRIBES",
      "hierarchical_relationship": true
    }
  }
]
```

## 🔍 고급 쿼리 예시

### 1. 섹션별 엔티티 밀도 분석
```cypher
MATCH (s:Section)-[:RELATED_TO]->(e)
WITH s, count(e) as entity_count
RETURN s.title, entity_count
ORDER BY entity_count DESC
```

### 2. 테이블 데이터 기반 엔티티 관계 분석
```cypher
MATCH (t:Table)-[:RELATED_TO]->(e1), (t)-[:RELATED_TO]->(e2)
WHERE e1 <> e2
RETURN t.content, e1.text, e2.text, 
       "FOUND_IN_SAME_TABLE" as relationship_type
```

### 3. 문서 구조의 깊이별 엔티티 분포
```cypher
MATCH (d:Document)-[:CONTAINS_STRUCTURE*]->(s)-[:RELATED_TO]->(e)
WITH s.type as structure_type, 
     length((d)-[:CONTAINS_STRUCTURE*]->(s)) as depth,
     count(e) as entity_count
RETURN structure_type, depth, entity_count
ORDER BY depth, entity_count DESC
```

### 4. 도메인별 구조-엔티티 매핑 패턴
```cypher
MATCH (s)-[:RELATED_TO]->(e)
WHERE EXISTS(s.domain) AND EXISTS(e.domain)
WITH s.type as structure_type, 
     e.type as entity_type,
     s.domain as domain,
     count(*) as frequency
RETURN domain, structure_type, entity_type, frequency
ORDER BY domain, frequency DESC
```

## 🎨 Memgraph Studio에서 시각화

### 1. 계층적 구조 시각화 설정

**노드 색상 설정**:
- `Document`: 파란색 (#3498db)
- `Section`: 초록색 (#2ecc71) 
- `Table`: 주황색 (#f39c12)
- `Technology`: 보라색 (#9b59b6)
- `Database`: 빨간색 (#e74c3c)

**관계 스타일**:
- `CONTAINS_STRUCTURE`: 굵은 실선
- `RELATED_TO` (hierarchical): 점선
- `INTEGRATES_WITH`: 화살표

### 2. 유용한 시각화 쿼리
```cypher
// 전체 문서 구조와 엔티티 관계 시각화
MATCH path = (d:Document)-[:CONTAINS_STRUCTURE*]->(s)-[:RELATED_TO]->(e)
WHERE d.title CONTAINS "API"
RETURN path
LIMIT 50

// 특정 구조 타입의 엔티티 관계만 시각화
MATCH (s:Section)-[:RELATED_TO]->(e)
RETURN s, e
LIMIT 30
```

## 🚀 성능 최적화

### 1. 인덱스 생성
```cypher
CREATE INDEX ON :Document(title);
CREATE INDEX ON :Section(title);
CREATE INDEX ON :Table(content);
CREATE INDEX ON :Technology(text);
CREATE INDEX ON :Database(text);
```

### 2. 쿼리 최적화 팁
- **구조 필터링**: 먼저 구조 요소로 필터링한 후 엔티티 조회
- **도메인 기반 분할**: 도메인별로 쿼리를 분리하여 성능 향상
- **배치 처리**: 대량 데이터 처리 시 배치 크기 조정

## 🔧 커스터마이징

### 1. 새로운 구조 요소 추가
`hierarchical_kg_builder.py`에서 `_extract_structural_elements_from_parser` 메서드 확장:

```python
# 새로운 구조 요소 (예: Code Block)
if "code_blocks" in structured_info:
    code_blocks = structured_info["code_blocks"]
    for i, code in enumerate(code_blocks):
        code_id = f"code_{doc_id}_{i}"
        element = StructuralElement(
            id=code_id,
            type="CodeBlock",
            properties={
                "language": code.get("language"),
                "lines": len(code.get("content", "").split("\n")),
                "parser": parser_name,
                "index": i
            },
            parent_id=doc_id,
            content=code.get("content", "")
        )
        elements.append(element)
```

### 2. 도메인별 관계 확장
`kg_schema_manager.py`에서 새로운 도메인과 관계 추가:

```python
"code_documentation": {
    "entities": {
        "CodeBlock": ["language", "complexity", "purpose"],
        "Function": ["name", "parameters", "return_type"],
        "Class": ["name", "methods", "inheritance"]
    },
    "relationships": {
        "코드_관계": ["DEFINES", "CALLS", "INHERITS", "IMPLEMENTS"]
    }
}
```

## ✅ 완료!

계층적 KG 시스템으로 이제 문서의 **구조적 정보**와 **의미적 엔티티**를 모두 포함하는 풍부한 지식 그래프를 구축할 수 있습니다!

### 🎯 **주요 장점**
- **정확한 컨텍스트**: 엔티티가 어떤 구조에서 발견되었는지 명확히 표시
- **계층적 탐색**: 문서 → 섹션 → 엔티티 순으로 체계적 탐색 가능
- **구조 기반 분석**: 테이블 vs 텍스트에서 발견된 정보 구분 가능
- **확장 가능성**: 새로운 문서 구조와 엔티티 타입 쉽게 추가

이제 단순한 키워드 나열이 아닌, **문서의 구조적 맥락을 보존한 의미있는 지식 그래프**를 활용할 수 있습니다! 🚀