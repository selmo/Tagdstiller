# 🔥 Memgraph Knowledge Graph 설정 가이드

DocExtract 시스템에서 Memgraph를 사용한 지식 그래프 기능을 설정하는 방법입니다.

## 🚀 Memgraph 설치

### 1. Docker를 사용한 설치 (권장)

```bash
# Memgraph 컨테이너 실행
docker run -it -p 7687:7687 -p 7444:7444 -p 3000:3000 \
  --name memgraph memgraph/memgraph-platform

# 또는 백그라운드로 실행
docker run -d -p 7687:7687 -p 7444:7444 -p 3000:3000 \
  --name memgraph \
  -v mg_lib:/var/lib/memgraph \
  -v mg_log:/var/log/memgraph \
  -v mg_etc:/etc/memgraph \
  memgraph/memgraph-platform
```

### 2. 로컬 설치 (macOS)

```bash
# Homebrew로 설치
brew install memgraph

# 실행
memgraph
```

### 3. 연결 확인

```bash
# Bolt 프로토콜 연결 확인 (포트 7687)
telnet localhost 7687

# 웹 인터페이스 접속 (포트 3000)
# http://localhost:3000
```

## 🔧 DocExtract 연동 설정

### 1. Python 의존성 설치

```bash
# DocExtract 백엔드 디렉토리에서
pip install neo4j
```

### 2. 환경 변수 설정 (선택사항)

```bash
# .env 파일 생성 또는 환경변수 설정
export MEMGRAPH_URI="bolt://localhost:7687"
export MEMGRAPH_USERNAME=""  # 기본값: 빈 문자열
export MEMGRAPH_PASSWORD=""  # 기본값: 빈 문자열
export MEMGRAPH_ADMIN_PASSWORD="admin123"  # DB 삭제용 관리자 비밀번호
```

### 3. DocExtract 백엔드 실행

```bash
# 백엔드 실행
./scripts/start_backend.sh
```

## 📊 API 엔드포인트

### 기본 상태 확인
```bash
# Memgraph 연결 상태 확인
curl http://localhost:8000/memgraph/health

# 데이터베이스 통계
curl http://localhost:8000/memgraph/stats
```

### KG 데이터 삽입
```bash
# 로컬 분석에서 자동 삽입
curl -X POST "http://localhost:8000/local-analysis/knowledge-graph" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "test/test_document.txt"}'

# 수동으로 KG 데이터 삽입
curl -X POST "http://localhost:8000/memgraph/insert" \
  -H "Content-Type: application/json" \
  -d '{
    "entities": [
      {"id": "doc_1", "type": "Document", "properties": {"title": "테스트 문서"}}
    ],
    "relationships": [
      {"source": "doc_1", "target": "keyword_1", "type": "RELATED_TO"}
    ]
  }'
```

### 데이터 조회
```bash
# 특정 문서의 KG 조회
curl "http://localhost:8000/memgraph/document/test%2Ftest_document.txt"

# 엔티티 검색
curl "http://localhost:8000/memgraph/search/entities?entity_type=Document&limit=10"

# 그래프 시각화 데이터
curl "http://localhost:8000/memgraph/graph/visualization?limit=20"
```

### 사용자 정의 쿼리
```bash
# Cypher 쿼리 실행
curl -X POST "http://localhost:8000/memgraph/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "MATCH (n:Document) RETURN n.title, n.domain LIMIT 5"
  }'
```

### 데이터 내보내기
```bash
# JSON 형식으로 내보내기
curl "http://localhost:8000/memgraph/export?format=json" -o kg_export.json

# Cypher 스크립트로 내보내기
curl "http://localhost:8000/memgraph/export?format=cypher" -o kg_export.cypher
```

## 🎯 도메인별 KG 생성 예시

### 1. 기술 문서

```bash
curl -X POST "http://localhost:8000/local-analysis/knowledge-graph" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "docs/api.md",
    "force_rebuild": true
  }'
```

**결과 예시**:
- 엔티티: `API`, `Function`, `Technology`, `Framework`
- 관계: `IMPLEMENTS`, `USES`, `DEPENDS_ON`, `CALLS`

### 2. 학술 논문

```bash
curl -X POST "http://localhost:8000/local-analysis/knowledge-graph" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "papers/research_paper.pdf",
    "force_rebuild": true
  }'
```

**결과 예시**:
- 엔티티: `Author`, `Research_Method`, `Finding`, `Citation`
- 관계: `AUTHORED_BY`, `USES_METHOD`, `CITES`, `PROVES`

### 3. 비즈니스 문서

```bash
curl -X POST "http://localhost:8000/local-analysis/knowledge-graph" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "reports/business_report.docx",
    "force_rebuild": true
  }'
```

**결과 예시**:
- 엔티티: `Company`, `Product`, `Market`, `Strategy`
- 관계: `COMPETES_WITH`, `PRODUCES`, `TARGETS`, `IMPLEMENTS`

## 🔍 Memgraph Studio 사용법

### 1. 웹 인터페이스 접속

```
http://localhost:3000
```

### 2. 유용한 Cypher 쿼리들

```cypher
// 모든 문서 조회
MATCH (d:Document) RETURN d LIMIT 10;

// 도메인별 엔티티 개수
MATCH (n) 
WHERE EXISTS(n.domain)
RETURN n.domain as domain, count(n) as count
ORDER BY count DESC;

// 특정 키워드와 연결된 문서들
MATCH (d:Document)-[:RELATED_TO]->(k)
WHERE k.text CONTAINS "API"
RETURN d.title, k.text, k.score;

// 가장 많이 연결된 엔티티 (허브 엔티티)
MATCH (n)-[r]-()
RETURN n.id, n.type, count(r) as connections
ORDER BY connections DESC
LIMIT 10;

// 도메인별 관계 타입 분포
MATCH ()-[r]->()
WHERE EXISTS(r.domain)
RETURN r.domain, type(r), count(r) as count
ORDER BY count DESC;
```

### 3. 그래프 시각화

1. **노드 색상 설정**: 엔티티 타입별로 다른 색상
2. **관계 두께**: 점수나 중요도에 따라 설정
3. **노드 크기**: 연결 개수에 따라 설정

## ⚠️ 주의사항

### 1. 성능 최적화

```cypher
-- 인덱스 생성 (자동으로 생성되지만 수동으로도 가능)
CREATE INDEX ON :Document(id);
CREATE INDEX ON :Document(title);
CREATE INDEX ON :Keyword(text);
```

### 2. 메모리 관리

- 대용량 문서 처리 시 메모리 사용량 모니터링
- 필요시 배치 크기 조정 (`memgraph_service.py`에서 설정)

### 3. 보안

```bash
# 운영 환경에서는 인증 설정
docker run -d -p 7687:7687 -p 7444:7444 -p 3000:3000 \
  --name memgraph \
  -e MEMGRAPH_USER=admin \
  -e MEMGRAPH_PASSWORD=your_secure_password \
  memgraph/memgraph-platform
```

### 4. 백업

```bash
# 데이터 백업
docker exec memgraph mgconsole --username="" --password="" \
  --execute "DUMP DATABASE;"

# JSON으로 백업
curl "http://localhost:8000/memgraph/export?format=json" -o backup.json
```

## 🛠️ 트러블슈팅

### 1. 연결 실패

```bash
# 컨테이너 상태 확인
docker ps -a | grep memgraph

# 로그 확인
docker logs memgraph

# 포트 확인
netstat -an | grep 7687
```

### 2. 메모리 부족

```bash
# 메모리 사용량 확인
docker stats memgraph

# 메모리 한계 설정
docker run -d --memory=4g --memory-swap=4g \
  -p 7687:7687 -p 3000:3000 \
  --name memgraph memgraph/memgraph-platform
```

### 3. 성능 이슈

```cypher
-- 쿼리 실행 계획 확인
EXPLAIN MATCH (n:Document) RETURN n;

-- 통계 확인
SHOW STORAGE INFO;
```

## 📈 모니터링

### 1. 시스템 상태

```bash
# 데이터베이스 통계
curl http://localhost:8000/memgraph/stats

# 헬스체크
curl http://localhost:8000/memgraph/health
```

### 2. 성능 메트릭

```cypher
-- 처리 시간 모니터링
PROFILE MATCH (n) RETURN count(n);

-- 메모리 사용량
SHOW STORAGE INFO;
```

## 🎉 완료!

이제 DocExtract에서 Memgraph를 사용한 지식 그래프 기능을 완전히 활용할 수 있습니다!

- ✅ **자동 도메인 감지**: 문서 타입별 최적화된 엔티티/관계 생성
- ✅ **풍부한 관계**: `RELATED_TO`에서 `IMPLEMENTS`, `CITES` 등으로 확장
- ✅ **실시간 저장**: KG 생성과 동시에 Memgraph에 자동 저장
- ✅ **RESTful API**: 완전한 CRUD 및 검색 기능
- ✅ **시각화 지원**: Memgraph Studio 및 웹 API 연동
- ✅ **확장 가능**: 새로운 도메인과 엔티티 타입 쉽게 추가

**다음 단계**: 프론트엔드에서 KG 시각화 컴포넌트를 추가하여 완전한 지식 그래프 관리 시스템을 구축할 수 있습니다! 🚀