"""
키워드 통계 및 목록 관련 API 엔드포인트 테스트
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

class TestKeywordEndpoints:
    """키워드 관련 엔드포인트 테스트"""
    
    def test_get_keywords_statistics_empty(self):
        """빈 데이터베이스에서 키워드 통계 조회"""
        response = client.get("/keywords/statistics")
        assert response.status_code == 200
        
        data = response.json()
        assert data["type"] == "all_projects"
        assert data["summary"]["total_projects"] >= 0
        assert data["summary"]["total_keywords"] >= 0
        assert data["summary"]["unique_keywords"] >= 0
        assert isinstance(data["projects"], list)
        assert isinstance(data["global_keywords"], list)
        assert isinstance(data["global_extractors"], list)
        assert isinstance(data["global_categories"], list)
    
    def test_get_keywords_statistics_with_project_id(self):
        """존재하지 않는 프로젝트 ID로 키워드 통계 조회"""
        response = client.get("/keywords/statistics?project_id=999")
        assert response.status_code == 404
    
    def test_get_keywords_list_empty(self):
        """빈 데이터베이스에서 키워드 목록 조회"""
        response = client.get("/keywords/list")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data["keywords"], list)
        assert "pagination" in data
        assert data["pagination"]["total"] >= 0
        assert data["pagination"]["limit"] == 100  # 기본값
        assert data["pagination"]["offset"] == 0   # 기본값
        assert "filters" in data
    
    def test_get_keywords_list_with_pagination(self):
        """페이지네이션 파라미터로 키워드 목록 조회"""
        response = client.get("/keywords/list?limit=10&offset=5")
        assert response.status_code == 200
        
        data = response.json()
        assert data["pagination"]["limit"] == 10
        assert data["pagination"]["offset"] == 5
        assert len(data["keywords"]) <= 10
    
    def test_get_keywords_list_with_project_filter(self):
        """존재하지 않는 프로젝트 ID로 필터링"""
        response = client.get("/keywords/list?project_id=999")
        assert response.status_code == 404
    
    def test_get_keywords_list_with_extractor_filter(self):
        """추출기 필터로 키워드 목록 조회"""
        response = client.get("/keywords/list?extractor=keybert")
        assert response.status_code == 200
        
        data = response.json()
        assert data["filters"]["extractor"] == "keybert"
        # 결과가 있다면 모든 키워드가 keybert 추출기여야 함
        for keyword in data["keywords"]:
            if keyword["extractor_name"]:
                assert keyword["extractor_name"] == "keybert"
    
    def test_get_keywords_list_with_category_filter(self):
        """카테고리 필터로 키워드 목록 조회"""
        response = client.get("/keywords/list?category=ORG")
        assert response.status_code == 200
        
        data = response.json()
        assert data["filters"]["category"] == "ORG"
        # 결과가 있다면 모든 키워드가 ORG 카테고리여야 함
        for keyword in data["keywords"]:
            if keyword["category"]:
                assert keyword["category"] == "ORG"
    
    def test_get_keywords_list_with_multiple_filters(self):
        """여러 필터 조합으로 키워드 목록 조회"""
        response = client.get("/keywords/list?extractor=spacy_ner&category=PERSON&limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert data["filters"]["extractor"] == "spacy_ner"
        assert data["filters"]["category"] == "PERSON"
        assert data["pagination"]["limit"] == 5
        assert len(data["keywords"]) <= 5
    
    def test_keywords_list_response_structure(self):
        """키워드 목록 응답 구조 검증"""
        response = client.get("/keywords/list?limit=1")
        assert response.status_code == 200
        
        data = response.json()
        
        # 필수 필드 확인
        required_fields = ["keywords", "pagination", "filters"]
        for field in required_fields:
            assert field in data
        
        # 페이지네이션 구조 확인
        pagination_fields = ["total", "limit", "offset", "has_next", "has_prev"]
        for field in pagination_fields:
            assert field in data["pagination"]
        
        # 필터 구조 확인
        filter_fields = ["project_id", "extractor", "category"]
        for field in filter_fields:
            assert field in data["filters"]
        
        # 키워드가 있는 경우 구조 확인
        if data["keywords"]:
            keyword = data["keywords"][0]
            keyword_fields = [
                "keyword", "score", "extractor_name", "category",
                "start_position", "end_position", "context_snippet", "file"
            ]
            for field in keyword_fields:
                assert field in keyword
            
            # 파일 정보 구조 확인
            if keyword["file"]:
                file_fields = ["id", "filename", "project"]
                for field in file_fields:
                    assert field in keyword["file"]
                
                # 프로젝트 정보 구조 확인
                if keyword["file"]["project"]:
                    project_fields = ["id", "name"]
                    for field in project_fields:
                        assert field in keyword["file"]["project"]

class TestKeywordStatisticsStructure:
    """키워드 통계 응답 구조 테스트"""
    
    def test_statistics_all_projects_structure(self):
        """전체 프로젝트 통계 응답 구조 검증"""
        response = client.get("/keywords/statistics")
        assert response.status_code == 200
        
        data = response.json()
        
        # 기본 구조 확인
        assert data["type"] == "all_projects"
        
        # 필수 필드 확인
        required_fields = ["projects", "global_keywords", "global_extractors", "global_categories", "summary"]
        for field in required_fields:
            assert field in data
            assert isinstance(data[field], list) or isinstance(data[field], dict)
        
        # summary 구조 확인
        summary_fields = ["total_projects", "total_keywords", "unique_keywords", "extractors_used", "categories_found"]
        for field in summary_fields:
            assert field in data["summary"]
            assert isinstance(data["summary"][field], int)
        
        # 프로젝트가 있는 경우 구조 확인
        if data["projects"]:
            project = data["projects"][0]
            project_fields = [
                "project_id", "project_name", "keywords_count", "unique_keywords_count",
                "extractors_count", "categories_count", "files_count", "avg_score",
                "extractors", "categories", "top_keywords"
            ]
            for field in project_fields:
                assert field in project
    
    def test_statistics_single_project_structure_not_found(self):
        """존재하지 않는 프로젝트의 통계 조회"""
        response = client.get("/keywords/statistics?project_id=999")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data

class TestKeywordIntegration:
    """키워드 관련 통합 테스트"""
    
    def test_complete_keyword_workflow(self):
        """키워드 관련 전체 워크플로우 테스트"""
        # 1. 초기 통계 확인
        response = client.get("/keywords/statistics")
        assert response.status_code == 200
        initial_stats = response.json()
        
        # 2. 키워드 목록 확인
        response = client.get("/keywords/list")
        assert response.status_code == 200
        initial_list = response.json()
        
        # 3. 필터링 테스트
        if initial_list["keywords"]:
            # 첫 번째 키워드의 추출기로 필터링
            first_extractor = initial_list["keywords"][0]["extractor_name"]
            if first_extractor:
                response = client.get(f"/keywords/list?extractor={first_extractor}")
                assert response.status_code == 200
                filtered_data = response.json()
                
                # 필터가 적용되었는지 확인
                for keyword in filtered_data["keywords"]:
                    assert keyword["extractor_name"] == first_extractor
        
        # 4. 페이지네이션 테스트
        if initial_list["pagination"]["total"] > 5:
            response = client.get("/keywords/list?limit=5&offset=0")
            assert response.status_code == 200
            page1 = response.json()
            
            response = client.get("/keywords/list?limit=5&offset=5")
            assert response.status_code == 200
            page2 = response.json()
            
            # 페이지가 다른지 확인 (키워드가 충분히 있는 경우)
            if len(page1["keywords"]) == 5 and len(page2["keywords"]) > 0:
                page1_keywords = {kw["keyword"] for kw in page1["keywords"]}
                page2_keywords = {kw["keyword"] for kw in page2["keywords"]}
                # 완전히 같지 않아야 함 (일부 겹칠 수는 있음)
                assert page1_keywords != page2_keywords

class TestKeywordPagination:
    """키워드 목록 페이지네이션 테스트"""
    
    def test_pagination_limits(self):
        """페이지네이션 한계값 테스트"""
        # 최대 한계 테스트
        response = client.get("/keywords/list?limit=1000")
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["limit"] == 1000
        
        # 0 limit 테스트
        response = client.get("/keywords/list?limit=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["keywords"]) == 0
    
    def test_pagination_navigation_flags(self):
        """페이지네이션 네비게이션 플래그 테스트"""
        # 첫 페이지
        response = client.get("/keywords/list?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        
        # has_prev는 false여야 함
        assert data["pagination"]["has_prev"] == False
        
        # 전체 키워드가 10개보다 많으면 has_next는 true
        if data["pagination"]["total"] > 10:
            assert data["pagination"]["has_next"] == True
        else:
            assert data["pagination"]["has_next"] == False