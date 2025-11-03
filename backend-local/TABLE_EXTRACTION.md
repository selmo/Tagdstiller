# 테이블 구조화 추출 (Table Structure Extraction)

## 개요
Knowledge Graph 추출 시 마크다운 테이블을 구조화된 형태로 추출하여 행-열 관계를 보존합니다.

## 새로운 엔티티 타입

### Table
테이블 전체를 나타내는 엔티티
```json
{
  "id": "t1",
  "type": "Table",
  "properties": {
    "name": "도로터널 결로 영향 분석을 위한 실외 환경조건",
    "row_count": 10,
    "column_count": 6
  }
}
```

### TableColumn
테이블의 각 열 (컬럼)
```json
{
  "id": "tc1",
  "type": "TableColumn",
  "properties": {
    "column_name": "인천",
    "column_index": 2
  }
}
```

### TableRow
테이블의 각 행 (데이터 행만, 헤더 제외)
```json
{
  "id": "tr1",
  "type": "TableRow",
  "properties": {
    "row_index": 0,
    "values": ["온도", "60%", "16.0", "15.3", "16.0", "16.0", "17.5", "17.6"]
  }
}
```

### TableCell (선택적)
개별 셀 데이터
```json
{
  "id": "cell1",
  "type": "TableCell",
  "properties": {
    "row_index": 0,
    "column_index": 2,
    "value": "16.0"
  }
}
```

## 새로운 관계 타입

### HAS_ROW
`Table → TableRow` 관계
```json
{
  "id": "e1",
  "source": "t1",
  "target": "tr1",
  "type": "HAS_ROW"
}
```

### HAS_COLUMN
`Table → TableColumn` 관계
```json
{
  "id": "e2",
  "source": "t1",
  "target": "tc1",
  "type": "HAS_COLUMN"
}
```

### CONTAINS_VALUE
`TableRow → Data/Location` 관계 (행에 포함된 실제 데이터)
```json
{
  "id": "e3",
  "source": "tr1",
  "target": "n5",
  "type": "CONTAINS_VALUE"
}
```

### IN_TABLE / IN_ROW / IN_COLUMN
역방향 관계
```json
{
  "id": "e4",
  "source": "n10",
  "target": "tr2",
  "type": "IN_ROW"
}
```

## 추출 예시

### 입력: 마크다운 테이블
```markdown
## 도로터널 결로 영향 분석을 위한 실외 환경조건

| 구분 | 누적빈도 | 인천 | 서산 | 군산 | 해남 | 여수 | 부산 |
|------|---------|------|------|------|------|------|------|
| 온도 | 60%     | 16.0 | 15.3 | 16.0 | 16.0 | 17.5 | 17.6 |
| 온도 | 70%     | 18.7 | 18.2 | 18.7 | 18.8 | 19.8 | 20.0 |
| 습도 | 60%     | 89.0 | 87.7 | 89.0 | 90.2 | 82.2 | 79.7 |
```

### 출력: 구조화된 Knowledge Graph

**엔티티 (13개):**
- 1개 Table: "도로터널 결로 영향 분석을 위한 실외 환경조건"
- 6개 TableColumn: "인천", "서산", "군산", "해남", "여수", "부산"
- 3개 TableRow: 각 데이터 행
- 3개 추가 엔티티: "온도" (Concept), "습도" (Concept), "60%" (Data)

**관계 (15개):**
- 3개 HAS_ROW: Table → 각 TableRow
- 6개 HAS_COLUMN: Table → 각 TableColumn
- 6개 CONTAINS_VALUE: TableRow → 해당 행의 데이터 엔티티

## 프롬프트 업데이트

### Phase 1 (엔티티 추출)
```
**CRITICAL TABLE EXTRACTION RULES:**
1. **WHEN YOU SEE A MARKDOWN TABLE** (lines with |...|...|):
   - Create ONE Table entity with table title/description
   - Create TableColumn entities for EACH column header
   - Create TableRow entities for EACH data row (NOT header row)
   - Store actual data values in row's "values" property as array
   - Example: Table "온습도 조건" has 6 columns × 10 data rows = 1 Table + 6 TableColumn + 10 TableRow entities
```

### Phase 2 (관계 추출)
```
**RULES:**
2. **For Table entities**: Create HAS_ROW relationships to all TableRow entities, HAS_COLUMN to all TableColumn entities
3. **For TableRow entities**: Create CONTAINS_VALUE to relevant Data/Location entities found in that row
```

## 사용 방법

### API 호출
```bash
curl -X POST http://localhost:58000/local-analysis/full-knowledge-graph-chunked \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/document.pdf",
    "extraction_level": "deep",
    "use_llm": true
  }'
```

### 추출 레벨별 동작
- **brief**: 테이블 인식하지만 간략하게만 추출
- **standard**: 테이블 구조 + 주요 행/열 추출
- **deep**: 완전한 테이블 구조 추출 (모든 행, 열, 데이터)

## 기대 효과

### Before (구조화 없음)
```
✗ 테이블 정보가 개별 엔티티로만 존재
✗ 지역명 6개 (인천, 서산, ...) - 서로 연결 안됨
✗ 수치 3개 (16.0, 15.3, ...) - 어느 지역인지 모름
✗ 행-열 관계 파악 불가
```

### After (구조화 완료)
```
✓ Table 엔티티가 전체 테이블 표현
✓ TableColumn이 각 지역 컬럼 표현
✓ TableRow가 각 데이터 행 표현
✓ HAS_ROW/HAS_COLUMN 관계로 구조 명확
✓ CONTAINS_VALUE로 데이터 위치 파악 가능
✓ "인천의 60% 누적빈도 온도는 16.0" 같은 쿼리 가능
```

## Cypher 쿼리 예시

### 특정 지역의 모든 데이터 조회
```cypher
MATCH (t:Table)-[:HAS_COLUMN]->(col:TableColumn {column_name: "인천"})
MATCH (t)-[:HAS_ROW]->(row:TableRow)
WHERE row.values[2] IS NOT NULL
RETURN row.values[0] AS 구분, row.values[1] AS 누적빈도, row.values[2] AS 인천값
```

### 온도 60% 행의 모든 지역 데이터
```cypher
MATCH (t:Table)-[:HAS_ROW]->(row:TableRow)
WHERE row.values[0] = "온도" AND row.values[1] = "60%"
MATCH (t)-[:HAS_COLUMN]->(col:TableColumn)
RETURN col.column_name, row.values[col.column_index]
```

### 테이블 메타정보 조회
```cypher
MATCH (t:Table {name: "도로터널 결로 영향 분석을 위한 실외 환경조건"})
RETURN t.row_count, t.column_count
```

## 구현 파일
- `backend/prompts/templates.py`: 프롬프트 업데이트
  - `PHASE1_ENTITY_BRIEF`: 간략 추출에 Table 엔티티 추가
  - `PHASE1_ENTITY_STANDARD`: 기본 추출에 TableRow/TableColumn 추가
  - `PHASE1_ENTITY_DEEP`: 심층 추출에 완전한 테이블 구조 명시
  - `PHASE2_RELATION_ONLY`: HAS_ROW/HAS_COLUMN/CONTAINS_VALUE 관계 추가

## 제한사항
- 현재는 마크다운 테이블 형식(`|...|...|`)만 인식
- 복잡한 병합 셀(merged cells)은 지원 안 됨
- 중첩 테이블은 개별 테이블로 추출

## 향후 개선
- [ ] HTML 테이블 지원
- [ ] 병합 셀 처리
- [ ] 테이블 캡션/각주 추출
- [ ] 테이블 간 관계 추론 (참조, 비교 등)
