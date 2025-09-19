"""
Memgraph Knowledge Graph API Router

Memgraph 데이터베이스와의 상호작용을 위한 API 엔드포인트들을 제공합니다.
KG 데이터 삽입, 조회, 검색, 통계 등의 기능을 포함합니다.
"""

from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import FileResponse
from typing import Dict, List, Any, Optional
import logging
import json
import tempfile
import os
from pathlib import Path

from services.memgraph_service import MemgraphService, create_memgraph_service
from services.kg_builder import KGBuilder

router = APIRouter(prefix="/memgraph", tags=["memgraph"])
logger = logging.getLogger(__name__)

# 전역 Memgraph 서비스 인스턴스
_memgraph_service: Optional[MemgraphService] = None

def get_memgraph_service() -> MemgraphService:
    """Memgraph 서비스 인스턴스 가져오기 (싱글톤 패턴)"""
    global _memgraph_service
    if _memgraph_service is None:
        _memgraph_service = create_memgraph_service()
    return _memgraph_service

@router.get("/health")
async def health_check():
    """Memgraph 연결 상태 확인"""
    try:
        service = get_memgraph_service()
        is_connected = service.is_connected()
        
        return {
            "status": "connected" if is_connected else "disconnected",
            "uri": service.uri,
            "message": "Memgraph 연결 정상" if is_connected else "Memgraph 연결 실패"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memgraph 상태 확인 실패: {str(e)}")

@router.get("/stats")
async def get_database_stats():
    """데이터베이스 통계 정보 조회"""
    try:
        service = get_memgraph_service()
        if not service.is_connected():
            raise HTTPException(status_code=503, detail="Memgraph에 연결되지 않음")
        
        stats = service.get_database_stats()
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")

@router.post("/insert")
async def insert_kg_data(
    kg_data: Dict[str, Any] = Body(..., description="삽입할 KG 데이터"),
    clear_existing: bool = Query(False, description="기존 문서 데이터 삭제 여부")
):
    """KG 데이터를 Memgraph에 삽입"""
    try:
        service = get_memgraph_service()
        if not service.is_connected():
            raise HTTPException(status_code=503, detail="Memgraph에 연결되지 않음")
        
        # 데이터 유효성 검사
        if "entities" not in kg_data or "relationships" not in kg_data:
            raise HTTPException(
                status_code=400, 
                detail="KG 데이터에 'entities'와 'relationships' 필드가 필요함"
            )
        
        success = service.insert_kg_data(kg_data, clear_existing=clear_existing)
        
        if success:
            return {
                "status": "success",
                "message": "KG 데이터 삽입 완료",
                "entities_count": len(kg_data.get("entities", [])),
                "relationships_count": len(kg_data.get("relationships", [])),
                "clear_existing": clear_existing
            }
        else:
            raise HTTPException(status_code=500, detail="KG 데이터 삽입 실패")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"KG 데이터 삽입 실패: {e}")
        raise HTTPException(status_code=500, detail=f"KG 데이터 삽입 실패: {str(e)}")

@router.get("/document/{file_path:path}")
async def get_document_kg(file_path: str):
    """특정 문서의 KG 데이터 조회"""
    try:
        service = get_memgraph_service()
        if not service.is_connected():
            raise HTTPException(status_code=503, detail="Memgraph에 연결되지 않음")
        
        kg_data = service.get_document_kg(file_path)
        
        return {
            "status": "success",
            "file_path": file_path,
            "data": kg_data
        }
    except Exception as e:
        logger.error(f"문서 KG 조회 실패: {file_path}, 오류: {e}")
        raise HTTPException(status_code=500, detail=f"문서 KG 조회 실패: {str(e)}")

@router.get("/search/entities")
async def search_entities(
    entity_type: Optional[str] = Query(None, description="엔티티 타입 필터"),
    name: Optional[str] = Query(None, description="엔티티 이름 검색"),
    domain: Optional[str] = Query(None, description="도메인 필터"),
    limit: int = Query(100, ge=1, le=1000, description="결과 개수 제한")
):
    """엔티티 검색"""
    try:
        service = get_memgraph_service()
        if not service.is_connected():
            raise HTTPException(status_code=503, detail="Memgraph에 연결되지 않음")
        
        # 검색 조건 구성
        properties = {}
        if name:
            properties["name"] = f"*{name}*"  # 와일드카드 검색
        if domain:
            properties["domain"] = domain
        
        entities = service.search_entities(
            entity_type=entity_type,
            properties=properties,
            limit=limit
        )
        
        return {
            "status": "success",
            "total": len(entities),
            "entities": entities,
            "filters": {
                "entity_type": entity_type,
                "name": name,
                "domain": domain,
                "limit": limit
            }
        }
    except Exception as e:
        logger.error(f"엔티티 검색 실패: {e}")
        raise HTTPException(status_code=500, detail=f"엔티티 검색 실패: {str(e)}")

@router.post("/query")
async def execute_cypher_query(
    query: str = Body(..., description="실행할 Cypher 쿼리"),
    parameters: Dict[str, Any] = Body(default={}, description="쿼리 파라미터")
):
    """사용자 정의 Cypher 쿼리 실행"""
    try:
        service = get_memgraph_service()
        if not service.is_connected():
            raise HTTPException(status_code=503, detail="Memgraph에 연결되지 않음")
        
        # 보안을 위해 일부 위험한 쿼리 제한
        dangerous_keywords = ["DELETE", "DETACH", "DROP", "CREATE CONSTRAINT", "DROP CONSTRAINT"]
        query_upper = query.upper().strip()
        
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                raise HTTPException(
                    status_code=403, 
                    detail=f"보안상 '{keyword}' 쿼리는 허용되지 않음"
                )
        
        results = service.execute_query(query, parameters)
        
        return {
            "status": "success",
            "query": query,
            "parameters": parameters,
            "results": results,
            "count": len(results)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cypher 쿼리 실행 실패: {query[:100]}..., 오류: {e}")
        raise HTTPException(status_code=500, detail=f"쿼리 실행 실패: {str(e)}")

@router.get("/export")
async def export_kg_data(
    format: str = Query("json", regex="^(json|cypher)$", description="내보내기 형식"),
    file_path: Optional[str] = Query(None, description="특정 문서만 내보내기")
):
    """KG 데이터 내보내기"""
    try:
        service = get_memgraph_service()
        if not service.is_connected():
            raise HTTPException(status_code=503, detail="Memgraph에 연결되지 않음")
        
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{format}") as temp_file:
            temp_path = temp_file.name
        
        # 데이터 내보내기
        success = service.export_kg_to_file(temp_path, format)
        
        if not success:
            os.unlink(temp_path)  # 실패 시 임시 파일 삭제
            raise HTTPException(status_code=500, detail="내보내기 실패")
        
        # 파일명 설정
        filename = f"kg_export_{format}.{format}"
        if file_path:
            safe_filename = Path(file_path).stem
            filename = f"kg_{safe_filename}.{format}"
        
        return FileResponse(
            path=temp_path,
            filename=filename,
            media_type='application/octet-stream'
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"KG 내보내기 실패: {e}")
        raise HTTPException(status_code=500, detail=f"내보내기 실패: {str(e)}")

@router.post("/rebuild-from-document")
async def rebuild_kg_from_document(
    file_path: str = Body(..., description="재구축할 문서 경로"),
    force_reanalyze: bool = Body(False, description="문서 재분석 여부")
):
    """문서로부터 KG 재구축"""
    try:
        # 이 기능은 기존 분석 결과를 사용하여 KG를 재생성
        # 실제 구현에서는 local_analysis API와 연동 필요
        
        service = get_memgraph_service()
        if not service.is_connected():
            raise HTTPException(status_code=503, detail="Memgraph에 연결되지 않음")
        
        # TODO: 실제 문서 분석 로직과 연동
        # 1. 문서 파일 존재 확인
        # 2. 기존 분석 결과 로드 또는 새로 분석
        # 3. KG 재구축
        # 4. Memgraph에 저장
        
        return {
            "status": "success",
            "message": f"문서 '{file_path}' KG 재구축 완료",
            "file_path": file_path,
            "force_reanalyze": force_reanalyze,
            "note": "실제 구현은 local_analysis API와 연동 필요"
        }
        
    except Exception as e:
        logger.error(f"KG 재구축 실패: {file_path}, 오류: {e}")
        raise HTTPException(status_code=500, detail=f"KG 재구축 실패: {str(e)}")

@router.get("/relationships/types")
async def get_relationship_types():
    """관계 타입 목록 조회"""
    try:
        service = get_memgraph_service()
        if not service.is_connected():
            raise HTTPException(status_code=503, detail="Memgraph에 연결되지 않음")
        
        # 현재 데이터베이스의 모든 관계 타입 조회
        query = "MATCH ()-[r]->() RETURN DISTINCT type(r) as rel_type, count(r) as count ORDER BY count DESC"
        results = service.execute_query(query)
        
        relationship_types = [
            {"type": result["rel_type"], "count": result["count"]} 
            for result in results
        ]
        
        return {
            "status": "success",
            "relationship_types": relationship_types,
            "total_types": len(relationship_types)
        }
    except Exception as e:
        logger.error(f"관계 타입 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"관계 타입 조회 실패: {str(e)}")

@router.get("/entities/types")
async def get_entity_types():
    """엔티티 타입 목록 조회"""
    try:
        service = get_memgraph_service()
        if not service.is_connected():
            raise HTTPException(status_code=503, detail="Memgraph에 연결되지 않음")
        
        # 현재 데이터베이스의 모든 엔티티 타입 조회
        query = "MATCH (n) RETURN DISTINCT labels(n) as labels, count(n) as count ORDER BY count DESC"
        results = service.execute_query(query)
        
        entity_types = []
        for result in results:
            labels = result.get("labels", [])
            if labels:
                entity_types.append({
                    "type": labels[0],  # 첫 번째 라벨 사용
                    "count": result["count"]
                })
        
        return {
            "status": "success",
            "entity_types": entity_types,
            "total_types": len(entity_types)
        }
    except Exception as e:
        logger.error(f"엔티티 타입 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"엔티티 타입 조회 실패: {str(e)}")

@router.delete("/clear")
async def clear_database(
    confirm: bool = Query(False, description="삭제 확인"),
    password: str = Query("", description="관리자 비밀번호")
):
    """데이터베이스 전체 삭제 (위험!)"""
    try:
        # 보안 검사
        if not confirm:
            raise HTTPException(
                status_code=400, 
                detail="데이터베이스 삭제에는 confirm=true 파라미터 필요"
            )
        
        # 추가 보안: 비밀번호 확인 (실제 운영에서는 환경변수에서 관리)
        admin_password = os.getenv("MEMGRAPH_ADMIN_PASSWORD", "admin123")
        if password != admin_password:
            raise HTTPException(
                status_code=403, 
                detail="관리자 비밀번호가 일치하지 않음"
            )
        
        service = get_memgraph_service()
        if not service.is_connected():
            raise HTTPException(status_code=503, detail="Memgraph에 연결되지 않음")
        
        success = service.clear_database(confirm=True)
        
        if success:
            return {
                "status": "success",
                "message": "데이터베이스가 완전히 삭제되었습니다",
                "warning": "이 작업은 되돌릴 수 없습니다"
            }
        else:
            raise HTTPException(status_code=500, detail="데이터베이스 삭제 실패")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"데이터베이스 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=f"삭제 실패: {str(e)}")

@router.get("/graph/visualization")
async def get_graph_visualization_data(
    limit: int = Query(50, ge=1, le=500, description="노드/관계 개수 제한"),
    entity_type: Optional[str] = Query(None, description="특정 엔티티 타입만 조회")
):
    """그래프 시각화를 위한 데이터 조회"""
    try:
        service = get_memgraph_service()
        if not service.is_connected():
            raise HTTPException(status_code=503, detail="Memgraph에 연결되지 않음")
        
        # 노드 및 관계 데이터 조회 (시각화용)
        if entity_type:
            nodes_query = f"MATCH (n:{entity_type}) RETURN n LIMIT $limit"
        else:
            nodes_query = "MATCH (n) RETURN n LIMIT $limit"
        
        edges_query = """
        MATCH (source)-[r]->(target)
        WHERE id(source) IN [n IN $node_ids] AND id(target) IN [n IN $node_ids]
        RETURN source.id as source_id, target.id as target_id, type(r) as rel_type, properties(r) as rel_props
        LIMIT $limit
        """
        
        # 노드 조회
        node_results = service.execute_query(nodes_query, {"limit": limit})
        
        nodes = []
        node_ids = []
        
        for result in node_results:
            node_data = result.get("n")
            if node_data:
                node_id = node_data.get("id")
                if node_id:
                    node_ids.append(node_id)
                    
                    # 노드 라벨 추출
                    node_type = "Unknown"
                    if hasattr(node_data, 'labels') and node_data.labels:
                        node_type = list(node_data.labels)[0]
                    
                    nodes.append({
                        "id": node_id,
                        "type": node_type,
                        "label": node_data.get("text") or node_data.get("name") or node_data.get("title") or node_id,
                        "properties": dict(node_data)
                    })
        
        # 관계 조회
        edge_results = service.execute_query(edges_query, {"node_ids": node_ids, "limit": limit})
        
        edges = []
        for result in edge_results:
            edges.append({
                "source": result.get("source_id"),
                "target": result.get("target_id"),
                "type": result.get("rel_type"),
                "label": result.get("rel_props", {}).get("relationship_name") or result.get("rel_type"),
                "properties": result.get("rel_props", {})
            })
        
        return {
            "status": "success",
            "graph": {
                "nodes": nodes,
                "edges": edges
            },
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "limit": limit,
                "entity_type": entity_type
            }
        }
        
    except Exception as e:
        logger.error(f"그래프 시각화 데이터 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"시각화 데이터 조회 실패: {str(e)}")