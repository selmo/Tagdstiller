"""
파서별 개별 파일 저장 관리자

이 모듈은 각 파서의 결과를 개별 파일로 저장하고 관리하는 기능을 제공합니다.
- 파서별 텍스트 추출 결과
- 문서 구조화 정보 (장, 절, 문단 등)
- 메타데이터 정보 (키워드, 요약, 주제 등)
"""

import json
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DocumentStructure:
    """문서 구조 정보"""
    sections: List[Dict[str, Any]] = None  # 장/절 구조
    headings: List[Dict[str, Any]] = None  # 제목 계층
    paragraphs: List[Dict[str, Any]] = None  # 문단 정보
    tables: List[Dict[str, Any]] = None  # 테이블 정보
    lists: List[Dict[str, Any]] = None  # 리스트 정보
    figures: List[Dict[str, Any]] = None  # 그림/이미지 정보
    
    def __post_init__(self):
        if self.sections is None:
            self.sections = []
        if self.headings is None:
            self.headings = []
        if self.paragraphs is None:
            self.paragraphs = []
        if self.tables is None:
            self.tables = []
        if self.lists is None:
            self.lists = []
        if self.figures is None:
            self.figures = []


@dataclass
class ParserMetadata:
    """파서별 메타데이터"""
    keywords: List[str] = None
    summary: Dict[str, str] = None  # intro, conclusion, core, tone
    topics: List[str] = None
    language: str = None
    document_type: str = None
    formality: str = None
    target_audience: str = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.summary is None:
            self.summary = {}
        if self.topics is None:
            self.topics = []


class ParserFileManager:
    """파서별 파일 저장 관리자"""
    
    def __init__(self, base_output_dir: str = "tests/outputs"):
        """
        Args:
            base_output_dir: 출력 파일들을 저장할 기본 디렉토리
        """
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(exist_ok=True)
        
    def _generate_session_id(self, file_path: str, parser_name: str) -> str:
        """세션 ID 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
        return f"{timestamp}_{parser_name}_{file_hash}"
    
    def _create_parser_directory(self, file_path: str, parser_name: str) -> Path:
        """파서별 디렉토리 생성"""
        session_id = self._generate_session_id(file_path, parser_name)
        parser_dir = self.base_output_dir / session_id
        parser_dir.mkdir(exist_ok=True)
        return parser_dir
    
    def save_parser_text(self, file_path: str, parser_name: str, extracted_text: str) -> Path:
        """파서별 텍스트 추출 결과 저장"""
        parser_dir = self._create_parser_directory(file_path, parser_name)
        text_file = parser_dir / f"{parser_name}_extracted_text.txt"
        
        try:
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(f"# {parser_name} 파서 텍스트 추출 결과\n")
                f.write(f"# 원본 파일: {file_path}\n")
                f.write(f"# 추출 시각: {datetime.now().isoformat()}\n")
                f.write(f"# 텍스트 길이: {len(extracted_text)} 문자\n\n")
                f.write(extracted_text)
            
            logger.info(f"✅ {parser_name} 텍스트 저장 완료: {text_file}")
            return text_file
            
        except Exception as e:
            logger.error(f"❌ {parser_name} 텍스트 저장 실패: {e}")
            raise
    
    def save_document_structure(self, file_path: str, parser_name: str, 
                              structure: DocumentStructure, raw_structure: Dict = None) -> Path:
        """문서 구조 정보 저장"""
        parser_dir = self._create_parser_directory(file_path, parser_name)
        structure_file = parser_dir / f"{parser_name}_document_structure.json"
        
        try:
            structure_data = {
                "@context": "http://purl.org/dc/terms/",
                "parser_name": parser_name,
                "source_file": file_path,
                "extraction_timestamp": datetime.now().isoformat(),
                "document_structure": {
                    "sections": structure.sections,
                    "headings": structure.headings,
                    "paragraphs": structure.paragraphs,
                    "tables": structure.tables,
                    "lists": structure.lists,
                    "figures": structure.figures,
                    "statistics": {
                        "total_sections": len(structure.sections),
                        "total_headings": len(structure.headings),
                        "total_paragraphs": len(structure.paragraphs),
                        "total_tables": len(structure.tables),
                        "total_lists": len(structure.lists),
                        "total_figures": len(structure.figures)
                    }
                }
            }
            
            # 원본 구조 정보가 있으면 포함
            if raw_structure:
                structure_data["raw_parser_structure"] = raw_structure
            
            with open(structure_file, 'w', encoding='utf-8') as f:
                json.dump(structure_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ {parser_name} 문서 구조 저장 완료: {structure_file}")
            return structure_file
            
        except Exception as e:
            logger.error(f"❌ {parser_name} 문서 구조 저장 실패: {e}")
            raise
    
    def save_parser_metadata(self, file_path: str, parser_name: str, 
                           metadata: ParserMetadata, raw_metadata: Dict = None) -> Path:
        """파서별 메타데이터 저장"""
        parser_dir = self._create_parser_directory(file_path, parser_name)
        metadata_file = parser_dir / f"{parser_name}_metadata.json"
        
        try:
            metadata_data = {
                "@context": "http://purl.org/dc/terms/",
                "parser_name": parser_name,
                "source_file": file_path,
                "extraction_timestamp": datetime.now().isoformat(),
                "extracted_metadata": {
                    "keywords": metadata.keywords,
                    "summary": metadata.summary,
                    "topics": metadata.topics,
                    "language": metadata.language,
                    "document_type": metadata.document_type,
                    "formality": metadata.formality,
                    "target_audience": metadata.target_audience,
                    "statistics": {
                        "keywords_count": len(metadata.keywords),
                        "topics_count": len(metadata.topics),
                        "summary_fields": list(metadata.summary.keys()) if metadata.summary else []
                    }
                }
            }
            
            # 원본 메타데이터가 있으면 포함
            if raw_metadata:
                metadata_data["raw_parser_metadata"] = raw_metadata
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ {parser_name} 메타데이터 저장 완료: {metadata_file}")
            return metadata_file
            
        except Exception as e:
            logger.error(f"❌ {parser_name} 메타데이터 저장 실패: {e}")
            raise
    
    def save_complete_parser_result(self, file_path: str, parser_name: str,
                                  extracted_text: str, structure: DocumentStructure,
                                  metadata: ParserMetadata, raw_data: Dict = None) -> Dict[str, Path]:
        """파서의 전체 결과를 개별 파일로 저장"""
        try:
            saved_files = {}
            
            # 1. 텍스트 저장
            saved_files['text'] = self.save_parser_text(file_path, parser_name, extracted_text)
            
            # 2. 구조 정보 저장
            raw_structure = raw_data.get('structure') if raw_data else None
            saved_files['structure'] = self.save_document_structure(
                file_path, parser_name, structure, raw_structure
            )
            
            # 3. 메타데이터 저장
            raw_metadata = raw_data.get('metadata') if raw_data else None
            saved_files['metadata'] = self.save_parser_metadata(
                file_path, parser_name, metadata, raw_metadata
            )
            
            # 4. 통합 정보 파일 저장
            parser_dir = self._create_parser_directory(file_path, parser_name)
            summary_file = parser_dir / f"{parser_name}_summary.json"
            
            summary_data = {
                "@context": "http://purl.org/dc/terms/",
                "parser_name": parser_name,
                "source_file": file_path,
                "extraction_timestamp": datetime.now().isoformat(),
                "saved_files": {k: str(v) for k, v in saved_files.items()},
                "processing_summary": {
                    "text_length": len(extracted_text),
                    "structure_elements": len(structure.sections) + len(structure.headings),
                    "metadata_keywords": len(metadata.keywords),
                    "parser_success": True
                }
            }
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=2)
            
            saved_files['summary'] = summary_file
            
            logger.info(f"🎉 {parser_name} 전체 결과 저장 완료: {parser_dir}")
            return saved_files
            
        except Exception as e:
            logger.error(f"❌ {parser_name} 전체 결과 저장 실패: {e}")
            raise
    
    def extract_structure_from_docling(self, docling_result: Dict) -> DocumentStructure:
        """Docling 파서 결과에서 문서 구조 추출"""
        structure = DocumentStructure()
        
        try:
            # Docling 구조 정보 추출
            if 'docling_structure' in docling_result:
                docling_struct = docling_result['docling_structure']
                structure.sections = docling_struct.get('sections', [])
                
            if 'document_structure' in docling_result:
                doc_struct = docling_result['document_structure']
                structure.headings = doc_struct.get('sections', [])
                structure.tables = [{'count': doc_struct.get('tables_count', 0)}]
                structure.figures = [{'count': doc_struct.get('figures_count', 0)}]
                
        except Exception as e:
            logger.warning(f"Docling 구조 추출 중 오류: {e}")
            
        return structure
    
    def extract_metadata_from_result(self, result: Dict) -> ParserMetadata:
        """결과에서 메타데이터 추출"""
        metadata = ParserMetadata()
        
        try:
            # 기본 메타데이터 추출
            if 'keywords' in result:
                metadata.keywords = result['keywords'] if isinstance(result['keywords'], list) else []
                
            if 'content_analysis' in result:
                analysis = result['content_analysis']
                metadata.summary = {
                    'core': analysis.get('summary', ''),
                    'topics': analysis.get('main_topics', [])
                }
                metadata.topics = analysis.get('keywords', [])
                
            metadata.language = result.get('dc:language', result.get('language', 'ko'))
            metadata.document_type = result.get('document_type', '문서')
            
        except Exception as e:
            logger.warning(f"메타데이터 추출 중 오류: {e}")
            
        return metadata


# 전역 파일 매니저 인스턴스
file_manager = ParserFileManager()


def save_parser_results(file_path: str, parser_results: Dict[str, Dict]) -> Dict[str, Dict[str, Path]]:
    """모든 파서 결과를 개별 파일로 저장"""
    saved_results = {}
    
    for parser_name, result_data in parser_results.items():
        try:
            if not result_data.get('success', False):
                logger.warning(f"⏭️  {parser_name} 파서 실패로 저장 건너뜀")
                continue
                
            result = result_data.get('metadata', {})
            
            # 텍스트 추출
            extracted_text = result.get('content_analysis', {}).get('text', 
                                      result.get('text', '추출된 텍스트 없음'))
            
            # 구조 정보 추출
            if parser_name == 'docling':
                structure = file_manager.extract_structure_from_docling(result)
            else:
                structure = DocumentStructure()  # 기본 빈 구조
            
            # 메타데이터 추출
            metadata = file_manager.extract_metadata_from_result(result)
            
            # 전체 결과 저장
            saved_files = file_manager.save_complete_parser_result(
                file_path, parser_name, extracted_text, structure, metadata, 
                raw_data={'structure': result, 'metadata': result}
            )
            
            saved_results[parser_name] = saved_files
            
        except Exception as e:
            logger.error(f"❌ {parser_name} 결과 저장 실패: {e}")
            continue
    
    logger.info(f"📁 총 {len(saved_results)}개 파서 결과 저장 완료")
    return saved_results