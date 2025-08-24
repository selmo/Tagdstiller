"""
로컬 파일 분석 서비스
"""
import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from services.config_service import ConfigService
from routers.extraction import ExtractorManager
from services.parser.auto_parser import AutoParser


class LocalFileAnalyzer:
    """로컬 파일 분석을 위한 서비스 클래스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.extractor_manager = ExtractorManager(db)
        
    def get_file_root(self) -> str:
        """설정에서 파일 루트 디렉토리를 가져옴"""
        return ConfigService.get_config_value(self.db, "LOCAL_FILE_ROOT", ".")
    
    def get_absolute_path(self, file_path: str) -> Path:
        """상대 경로를 절대 경로로 변환"""
        root = Path(self.get_file_root()).resolve()
        target_path = Path(file_path)
        
        if target_path.is_absolute():
            # 절대 경로인 경우, 루트 디렉토리 하위인지 확인
            try:
                target_path.resolve().relative_to(root)
                return target_path.resolve()
            except ValueError:
                raise ValueError(f"파일이 허용된 루트 디렉토리 외부에 있습니다: {file_path}")
        else:
            # 상대 경로인 경우
            return (root / target_path).resolve()
    
    def get_result_file_path(self, file_path: str) -> Path:
        """분석 결과 JSON 파일 경로를 생성"""
        absolute_path = self.get_absolute_path(file_path)
        result_path = absolute_path.with_suffix(absolute_path.suffix + '.analysis.json')
        return result_path
    
    def file_exists(self, file_path: str) -> bool:
        """파일 존재 여부 확인"""
        try:
            absolute_path = self.get_absolute_path(file_path)
            return absolute_path.exists() and absolute_path.is_file()
        except (ValueError, OSError):
            return False
    
    def is_supported_file(self, file_path: str) -> bool:
        """지원되는 파일 형식인지 확인"""
        allowed_extensions = ConfigService.get_json_config(
            self.db, "ALLOWED_EXTENSIONS", [".txt", ".pdf", ".docx", ".html", ".md"]
        )
        
        file_extension = Path(file_path).suffix.lower()
        return file_extension in allowed_extensions
    
    def load_existing_result(self, file_path: str) -> Optional[Dict[str, Any]]:
        """기존 분석 결과 로드"""
        try:
            result_file = self.get_result_file_path(file_path)
            if result_file.exists():
                with open(result_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"기존 결과 로드 실패: {e}")
        return None
    
    def save_result(self, file_path: str, result: Dict[str, Any]) -> str:
        """분석 결과를 JSON 파일로 저장"""
        result_file = self.get_result_file_path(file_path)
        
        # 디렉토리 생성
        result_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 메타데이터 추가
        enhanced_result = {
            "file_path": file_path,
            "analysis_timestamp": datetime.now().isoformat(),
            "analyzer_version": "1.0.0",
            **result
        }
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(enhanced_result, f, ensure_ascii=False, indent=2)
        
        return str(result_file)
    
    def backup_existing_result(self, file_path: str) -> Optional[str]:
        """기존 결과 파일을 백업"""
        result_file = self.get_result_file_path(file_path)
        if not result_file.exists():
            return None
        
        # 백업 파일명 생성 (타임스탬프 포함)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = result_file.with_suffix(f'.backup_{timestamp}.json')
        
        try:
            shutil.copy2(result_file, backup_file)
            return str(backup_file)
        except Exception as e:
            print(f"백업 생성 실패: {e}")
            return None
    
    def parse_file_content(self, file_path: str) -> str:
        """파일 내용을 파싱하여 텍스트로 변환"""
        absolute_path = self.get_absolute_path(file_path)
        
        # AutoParser를 사용하여 파일 파싱
        parser = AutoParser()
        parse_result = parser.parse(absolute_path)
        
        if not parse_result.success:
            raise ValueError(f"파일 파싱 실패: {parse_result.error_message}")
        
        return parse_result.text
    
    def extract_keywords(self, content: str, extractors: Optional[List[str]] = None, filename: str = "local_analysis.txt") -> List[Dict[str, Any]]:
        """키워드 추출 수행"""
        if extractors is None:
            extractors = ConfigService.get_json_config(
                self.db, "DEFAULT_EXTRACTORS", ["keybert", "ner", "konlpy", "metadata"]
            )
        
        # ExtractorManager를 사용하여 키워드 추출
        keywords = self.extractor_manager.extract_keywords(content, extractors, filename)
        
        # 결과를 딕셔너리 형태로 변환
        result = []
        for keyword in keywords:
            result.append({
                "keyword": keyword.keyword,
                "extractor_name": keyword.extractor_name,
                "score": keyword.score,
                "category": keyword.category,
                "start_position": keyword.start_position,
                "end_position": keyword.end_position,
                "context_snippet": keyword.context_snippet,
                "page_number": keyword.page_number,
                "line_number": keyword.line_number,
                "column_number": keyword.column_number
            })
        
        return result
    
    def analyze_file(self, file_path: str, extractors: Optional[List[str]] = None, force_reanalyze: bool = False) -> Dict[str, Any]:
        """파일 분석 수행"""
        # 파일 존재 여부 및 형식 확인
        if not self.file_exists(file_path):
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
        
        if not self.is_supported_file(file_path):
            raise ValueError(f"지원하지 않는 파일 형식입니다: {file_path}")
        
        # 기존 결과 확인
        if not force_reanalyze:
            existing_result = self.load_existing_result(file_path)
            if existing_result:
                return existing_result
        
        # 재분석의 경우 기존 결과 백업
        if force_reanalyze:
            backup_path = self.backup_existing_result(file_path)
            if backup_path:
                print(f"기존 결과를 백업했습니다: {backup_path}")
        
        try:
            # 파일 정보 수집
            absolute_path = self.get_absolute_path(file_path)
            
            # 파일 내용 파싱
            content = self.parse_file_content(file_path)
            
            # 키워드 추출
            keywords = self.extract_keywords(content, extractors, filename=absolute_path.name)
            
            # 파일 통계
            file_stats = absolute_path.stat()
            
            # 키워드를 추출기별로 그룹화
            grouped_keywords = {}
            for keyword in keywords:
                extractor_name = keyword["extractor_name"]
                if extractor_name not in grouped_keywords:
                    grouped_keywords[extractor_name] = []
                grouped_keywords[extractor_name].append(keyword)
            
            # 결과 구성
            result = {
                "file_info": {
                    "path": file_path,
                    "absolute_path": str(absolute_path),
                    "size": file_stats.st_size,
                    "modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                    "extension": absolute_path.suffix.lower()
                },
                "content_info": {
                    "length": len(content),
                    "word_count": len(content.split()),
                    "line_count": len(content.splitlines())
                },
                "extraction_info": {
                    "extractors_used": extractors or [],
                    "total_keywords": len(keywords)
                },
                "keywords": grouped_keywords,
                "analysis_status": "completed"
            }
            
            # 결과 저장
            result_file_path = self.save_result(file_path, result)
            result["result_file"] = result_file_path
            
            return result
            
        except Exception as e:
            error_result = {
                "file_info": {
                    "path": file_path,
                    "error": str(e)
                },
                "analysis_status": "failed",
                "error_message": str(e)
            }
            
            # 오류도 저장
            try:
                self.save_result(file_path, error_result)
            except:
                pass
            
            raise e