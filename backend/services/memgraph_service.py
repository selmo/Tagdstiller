"""
Memgraph Database Service - KG 데이터 관리

Memgraph 데이터베이스와의 연결, 데이터 삽입, 조회 등의 기능을 제공합니다.
도메인별 KG 엔티티와 관계를 Memgraph에 저장하고 Cypher 쿼리를 실행합니다.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
import json
import time
from pathlib import Path

try:
    from neo4j import GraphDatabase, Driver
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    print("Warning: neo4j driver not available. Install with: pip install neo4j")


class MemgraphService:
    """Memgraph 데이터베이스 서비스"""
    
    def __init__(self, uri: str = "bolt://localhost:7687", username: str = "", password: str = ""):
        """
        Memgraph 서비스 초기화
        
        Args:
            uri: Memgraph 연결 URI (기본: bolt://localhost:7687)
            username: 사용자명 (기본값: 빈 문자열)
            password: 비밀번호 (기본값: 빈 문자열)
        """
        self.uri = uri
        self.username = username
        self.password = password
        self.driver: Optional[Driver] = None
        self.logger = logging.getLogger(__name__)
        
        if not NEO4J_AVAILABLE:
            self.logger.error("neo4j driver가 설치되지 않음. 'pip install neo4j' 실행 필요")
            return
        
        self.connect()
    
    def connect(self) -> bool:
        """Memgraph에 연결"""
        if not NEO4J_AVAILABLE:
            return False
            
        try:
            self.logger.info(f"Memgraph 연결 시도: {self.uri}")
            self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            
            # 연결 테스트
            with self.driver.session() as session:
                result = session.run("RETURN 'Memgraph 연결 성공' as message")
                message = result.single()["message"]
                self.logger.info(f"✅ {message}")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Memgraph 연결 실패: {e}")
            if self.driver:
                self.driver.close()
                self.driver = None
            return False
    
    def close(self):
        """연결 종료"""
        if self.driver:
            self.driver.close()
            self.driver = None
            self.logger.info("Memgraph 연결 종료")
    
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        if not self.driver:
            return False
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
            return True
        except Exception:
            return False
    
    def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Cypher 쿼리 실행"""
        if not self.is_connected():
            self.logger.error("Memgraph에 연결되지 않음")
            return []
        
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except Exception as e:
            self.logger.error(f"쿼리 실행 실패: {query[:100]}... 오류: {e}")
            return []
    
    def clear_database(self, confirm: bool = False) -> bool:
        """데이터베이스 전체 삭제 (주의!)"""
        if not confirm:
            self.logger.warning("데이터베이스 삭제에는 confirm=True 필요")
            return False
        
        try:
            self.logger.warning("🗑️ Memgraph 데이터베이스 전체 삭제 중...")
            result = self.execute_query("MATCH (n) DETACH DELETE n")
            self.logger.info("✅ 데이터베이스 삭제 완료")
            return True
        except Exception as e:
            self.logger.error(f"❌ 데이터베이스 삭제 실패: {e}")
            return False
    
    def insert_kg_data(self, kg_data: Dict[str, Any], clear_existing: bool = False) -> bool:
        """KG 데이터를 Memgraph에 삽입"""
        if not self.is_connected():
            self.logger.error("Memgraph에 연결되지 않음")
            return False
        
        try:
            start_time = time.time()
            
            # 기존 데이터 삭제 (옵션)
            if clear_existing:
                file_path = kg_data.get("metadata", {}).get("file_path")
                if file_path:
                    self._clear_document_data(file_path)
            
            # 엔티티 삽입
            entities_inserted = self._insert_entities(kg_data.get("entities", []))
            
            # 관계 삽입
            relationships_inserted = self._insert_relationships(kg_data.get("relationships", []))
            
            # 인덱스 생성 (성능 최적화)
            self._create_indexes()
            
            elapsed_time = time.time() - start_time
            self.logger.info(
                f"✅ KG 데이터 삽입 완료 - "
                f"엔티티: {entities_inserted}개, 관계: {relationships_inserted}개, "
                f"소요시간: {elapsed_time:.2f}초"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ KG 데이터 삽입 실패: {e}")
            return False
    
    def _clear_document_data(self, file_path: str):
        """특정 문서의 기존 데이터 삭제"""
        import hashlib
        doc_id = hashlib.sha1(str(file_path).encode("utf-8")).hexdigest()[:16]
        
        query = """
        MATCH (doc:Document {id: $doc_id})
        OPTIONAL MATCH (doc)-[r]-()
        DETACH DELETE doc, r
        """
        
        self.execute_query(query, {"doc_id": doc_id})
        self.logger.info(f"🗑️ 문서 '{file_path}' 기존 데이터 삭제")
    
    def _insert_entities(self, entities: List[Dict[str, Any]]) -> int:
        """엔티티 배치 삽입"""
        if not entities:
            return 0
        
        # 엔티티 타입별로 그룹화
        entities_by_type = {}
        for entity in entities:
            entity_type = entity.get("type", "Unknown")
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(entity)
        
        total_inserted = 0
        
        # 각 타입별로 배치 삽입
        for entity_type, type_entities in entities_by_type.items():
            query = f"""
            UNWIND $entities AS entity
            MERGE (n:{entity_type} {{id: entity.id}})
            SET n += entity.properties
            """
            
            # properties에서 복잡한 객체는 JSON 문자열로 변환
            processed_entities = []
            for entity in type_entities:
                processed_entity = {
                    "id": entity["id"],
                    "properties": self._serialize_properties(entity.get("properties", {}))
                }
                processed_entities.append(processed_entity)
            
            self.execute_query(query, {"entities": processed_entities})
            total_inserted += len(type_entities)
            
            self.logger.debug(f"  📝 {entity_type}: {len(type_entities)}개 엔티티 삽입")
        
        return total_inserted
    
    def _insert_relationships(self, relationships: List[Dict[str, Any]]) -> int:
        """관계 배치 삽입"""
        if not relationships:
            return 0
        
        # 관계 타입별로 그룹화
        relationships_by_type = {}
        for rel in relationships:
            rel_type = rel.get("type", "RELATED_TO")
            if rel_type not in relationships_by_type:
                relationships_by_type[rel_type] = []
            relationships_by_type[rel_type].append(rel)
        
        total_inserted = 0
        
        # 각 타입별로 배치 삽입
        for rel_type, type_relationships in relationships_by_type.items():
            # Cypher에서 안전한 관계 타입명으로 변환
            safe_rel_type = rel_type.replace("-", "_").replace(" ", "_")
            
            query = f"""
            UNWIND $relationships AS rel
            MATCH (source {{id: rel.source}})
            MATCH (target {{id: rel.target}})
            MERGE (source)-[r:{safe_rel_type}]->(target)
            SET r += rel.properties
            """
            
            # properties 직렬화
            processed_relationships = []
            for rel in type_relationships:
                processed_rel = {
                    "source": rel["source"],
                    "target": rel["target"],
                    "properties": self._serialize_properties(rel.get("properties", {}))
                }
                processed_relationships.append(processed_rel)
            
            self.execute_query(query, {"relationships": processed_relationships})
            total_inserted += len(type_relationships)
            
            self.logger.debug(f"  🔗 {rel_type}: {len(type_relationships)}개 관계 삽입")
        
        return total_inserted
    
    def _serialize_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """복잡한 속성을 직렬화"""
        serialized = {}
        for key, value in properties.items():
            if isinstance(value, (list, dict, set)):
                # 복잡한 객체는 JSON 문자열로 변환
                serialized[key] = json.dumps(value, ensure_ascii=False, default=str)
            elif value is None:
                # None 값은 생략
                continue
            else:
                serialized[key] = value
        return serialized
    
    def _create_indexes(self):
        """성능 최적화를 위한 인덱스 생성"""
        indexes = [
            "CREATE INDEX ON :Document(id)",
            "CREATE INDEX ON :Document(path)",
            "CREATE INDEX ON :Keyword(text)",
            "CREATE INDEX ON :Technology(name)",
            "CREATE INDEX ON :Author(name)",
            "CREATE INDEX ON :Company(name)"
        ]
        
        for index_query in indexes:
            try:
                self.execute_query(index_query)
            except Exception:
                # 인덱스가 이미 존재하는 경우 무시
                pass
    
    def get_document_kg(self, file_path: str) -> Dict[str, Any]:
        """특정 문서의 KG 데이터 조회"""
        import hashlib
        doc_id = hashlib.sha1(str(file_path).encode("utf-8")).hexdigest()[:16]
        
        # 문서와 연결된 모든 엔티티 및 관계 조회
        query = """
        MATCH (doc:Document {id: $doc_id})
        OPTIONAL MATCH (doc)-[r]->(related)
        RETURN doc, r, related
        """
        
        results = self.execute_query(query, {"doc_id": doc_id})
        
        if not results:
            return {"entities": [], "relationships": [], "message": "문서를 찾을 수 없음"}
        
        # 결과를 KG 형태로 변환
        entities = []
        relationships = []
        entity_ids = set()
        
        for record in results:
            doc_data = record.get("doc")
            rel_data = record.get("r") 
            related_data = record.get("related")
            
            # 문서 엔티티 추가
            if doc_data and doc_data["id"] not in entity_ids:
                entities.append({
                    "id": doc_data["id"],
                    "type": "Document",
                    "properties": doc_data
                })
                entity_ids.add(doc_data["id"])
            
            # 연결된 엔티티 추가
            if related_data and related_data["id"] not in entity_ids:
                # 엔티티 타입은 라벨에서 추출
                entity_type = "Unknown"
                if hasattr(related_data, 'labels') and related_data.labels:
                    entity_type = list(related_data.labels)[0]
                
                entities.append({
                    "id": related_data["id"],
                    "type": entity_type,
                    "properties": related_data
                })
                entity_ids.add(related_data["id"])
            
            # 관계 추가
            if rel_data and doc_data and related_data:
                relationships.append({
                    "source": doc_data["id"],
                    "target": related_data["id"],
                    "type": type(rel_data).__name__,
                    "properties": dict(rel_data)
                })
        
        return {
            "entities": entities,
            "relationships": relationships,
            "total_entities": len(entities),
            "total_relationships": len(relationships)
        }
    
    def search_entities(self, entity_type: str = None, properties: Dict[str, Any] = None, 
                       limit: int = 100) -> List[Dict[str, Any]]:
        """엔티티 검색"""
        where_clauses = []
        params = {"limit": limit}
        
        # 엔티티 타입 필터
        if entity_type:
            node_pattern = f"n:{entity_type}"
        else:
            node_pattern = "n"
        
        # 속성 필터
        if properties:
            for i, (key, value) in enumerate(properties.items()):
                param_name = f"prop_{i}"
                if isinstance(value, str) and "*" in value:
                    # 와일드카드 검색
                    where_clauses.append(f"n.{key} CONTAINS ${param_name}")
                    params[param_name] = value.replace("*", "")
                else:
                    where_clauses.append(f"n.{key} = ${param_name}")
                    params[param_name] = value
        
        where_clause = " AND ".join(where_clauses)
        if where_clause:
            where_clause = f"WHERE {where_clause}"
        
        query = f"""
        MATCH ({node_pattern})
        {where_clause}
        RETURN n
        LIMIT $limit
        """
        
        results = self.execute_query(query, params)
        
        entities = []
        for record in results:
            node_data = record.get("n")
            if node_data:
                entity_type = "Unknown"
                if hasattr(node_data, 'labels') and node_data.labels:
                    entity_type = list(node_data.labels)[0]
                
                entities.append({
                    "id": node_data.get("id"),
                    "type": entity_type,
                    "properties": dict(node_data)
                })
        
        return entities
    
    def get_database_stats(self) -> Dict[str, Any]:
        """데이터베이스 통계 정보"""
        stats = {}
        
        try:
            # 전체 노드 수
            result = self.execute_query("MATCH (n) RETURN count(n) as node_count")
            stats["total_nodes"] = result[0]["node_count"] if result else 0
            
            # 전체 관계 수
            result = self.execute_query("MATCH ()-[r]->() RETURN count(r) as rel_count")
            stats["total_relationships"] = result[0]["rel_count"] if result else 0
            
            # 노드 타입별 개수
            result = self.execute_query("MATCH (n) RETURN labels(n) as labels, count(n) as count")
            node_types = {}
            for record in result:
                labels = record.get("labels", [])
                if labels:
                    label = labels[0]
                    node_types[label] = record.get("count", 0)
            stats["node_types"] = node_types
            
            # 관계 타입별 개수  
            result = self.execute_query("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count")
            relationship_types = {}
            for record in result:
                rel_type = record.get("type")
                if rel_type:
                    relationship_types[rel_type] = record.get("count", 0)
            stats["relationship_types"] = relationship_types
            
        except Exception as e:
            self.logger.error(f"통계 조회 실패: {e}")
            stats["error"] = str(e)
        
        return stats
    
    def export_kg_to_file(self, output_path: str, format: str = "json") -> bool:
        """KG 데이터를 파일로 내보내기"""
        try:
            if format.lower() == "json":
                return self._export_to_json(output_path)
            elif format.lower() == "cypher":
                return self._export_to_cypher(output_path)
            else:
                self.logger.error(f"지원하지 않는 형식: {format}")
                return False
        except Exception as e:
            self.logger.error(f"내보내기 실패: {e}")
            return False
    
    def _export_to_json(self, output_path: str) -> bool:
        """JSON 형식으로 내보내기"""
        # 모든 노드 조회
        nodes_result = self.execute_query("MATCH (n) RETURN n")
        nodes = []
        for record in nodes_result:
            node_data = record.get("n")
            if node_data:
                entity_type = "Unknown"
                if hasattr(node_data, 'labels') and node_data.labels:
                    entity_type = list(node_data.labels)[0]
                
                nodes.append({
                    "id": node_data.get("id"),
                    "type": entity_type,
                    "properties": dict(node_data)
                })
        
        # 모든 관계 조회
        rels_result = self.execute_query("""
            MATCH (source)-[r]->(target)
            RETURN source.id as source_id, target.id as target_id, 
                   type(r) as rel_type, properties(r) as rel_props
        """)
        
        relationships = []
        for record in rels_result:
            relationships.append({
                "source": record.get("source_id"),
                "target": record.get("target_id"),
                "type": record.get("rel_type"),
                "properties": record.get("rel_props", {})
            })
        
        # JSON 파일로 저장
        export_data = {
            "entities": nodes,
            "relationships": relationships,
            "exported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_entities": len(nodes),
            "total_relationships": len(relationships)
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"✅ JSON 내보내기 완료: {output_path}")
        return True
    
    def _export_to_cypher(self, output_path: str) -> bool:
        """Cypher 스크립트로 내보내기"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("// DocExtract KG Export - Cypher Script\n")
            f.write(f"// Exported at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 기존 데이터 삭제
            f.write("// Clear existing data\n")
            f.write("MATCH (n) DETACH DELETE n;\n\n")
            
            # 노드 생성 쿼리
            f.write("// Create nodes\n")
            nodes_result = self.execute_query("MATCH (n) RETURN n")
            for record in nodes_result:
                node_data = record.get("n")
                if node_data:
                    entity_type = "Unknown"
                    if hasattr(node_data, 'labels') and node_data.labels:
                        entity_type = list(node_data.labels)[0]
                    
                    props_str = ", ".join([f"{k}: {json.dumps(v)}" for k, v in node_data.items()])
                    f.write(f"CREATE (:{entity_type} {{{props_str}}});\n")
            
            f.write("\n// Create relationships\n")
            rels_result = self.execute_query("""
                MATCH (source)-[r]->(target)
                RETURN source.id as source_id, target.id as target_id, 
                       type(r) as rel_type, properties(r) as rel_props
            """)
            
            for record in rels_result:
                source_id = record.get("source_id")
                target_id = record.get("target_id") 
                rel_type = record.get("rel_type")
                rel_props = record.get("rel_props", {})
                
                props_str = ""
                if rel_props:
                    props_str = " {" + ", ".join([f"{k}: {json.dumps(v)}" for k, v in rel_props.items()]) + "}"
                
                f.write(f"MATCH (s {{id: {json.dumps(source_id)}}}) ")
                f.write(f"MATCH (t {{id: {json.dumps(target_id)}}}) ")
                f.write(f"CREATE (s)-[:{rel_type}{props_str}]->(t);\n")
        
        self.logger.info(f"✅ Cypher 내보내기 완료: {output_path}")
        return True


def create_memgraph_service(config: Dict[str, Any] = None) -> MemgraphService:
    """Memgraph 서비스 인스턴스 생성"""
    if config is None:
        config = {}
    
    return MemgraphService(
        uri=config.get("uri", "bolt://localhost:7687"),
        username=config.get("username", ""),
        password=config.get("password", "")
    )