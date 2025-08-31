"""
문서 파싱 전용 서비스
모든 파서를 사용하여 완전한 파싱을 수행하고 결과를 파일로 저장
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from services.parser.pdf_parser import PdfParser
from services.parser.docling_parser import DoclingParser
from services.parser.docx_parser import DocxParser
from services.parser.txt_parser import TxtParser
from services.parser.html_parser import HtmlParser
from services.parser.md_parser import MarkdownParser
from services.parser.zip_parser import ZipParser
from services.parser.base import ParseResult, DocumentMetadata

logger = logging.getLogger(__name__)


class DocumentParserService:
    """문서 파싱 전용 서비스 - 모든 파서를 사용하여 완전한 파싱 수행"""
    
    def __init__(self):
        self.parsers = {
            'pdf': [
                ('docling', DoclingParser()),
                ('pdf_parser', PdfParser())
            ],
            'docx': [('docx_parser', DocxParser())],
            'txt': [('txt_parser', TxtParser())],
            'html': [('html_parser', HtmlParser())],
            'htm': [('html_parser', HtmlParser())], 
            'md': [('md_parser', MarkdownParser())],
            'zip': [('zip_parser', ZipParser())]
        }
        
    def get_output_directory(self, file_path: Path, directory: Optional[Path] = None) -> Path:
        """파일별 출력 디렉토리 경로 반환"""
        if directory:
            return directory / file_path.stem
        return file_path.parent / file_path.stem
        
    def get_parsing_result_path(self, file_path: Path, directory: Optional[Path] = None) -> Path:
        """파싱 결과 JSON 파일 경로"""
        output_dir = self.get_output_directory(file_path, directory)
        return output_dir / "parsing_results.json"
        
    def has_parsing_results(self, file_path: Path, directory: Optional[Path] = None) -> bool:
        """파싱 결과가 이미 존재하는지 확인"""
        result_path = self.get_parsing_result_path(file_path, directory)
        return result_path.exists()
        
    def load_existing_parsing_results(self, file_path: Path, directory: Optional[Path] = None) -> Optional[Dict[str, Any]]:
        """기존 파싱 결과 로드"""
        if not self.has_parsing_results(file_path, directory):
            return None
            
        try:
            result_path = self.get_parsing_result_path(file_path, directory)
            with open(result_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"파싱 결과 로드 실패: {e}")
            return None
            
    def parse_document_comprehensive(
        self, 
        file_path: Path, 
        force_reparse: bool = False,
        directory: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        문서를 모든 적용 가능한 파서로 완전 파싱
        
        Args:
            file_path: 파싱할 문서 경로
            force_reparse: 기존 결과 무시하고 재파싱 여부
            
        Returns:
            파싱 결과 딕셔너리
        """
        logger.info(f"📄 문서 완전 파싱 시작: {file_path.name}")
        
        # 기존 결과 확인
        if not force_reparse and self.has_parsing_results(file_path, directory):
            logger.info("기존 파싱 결과 재사용")
            return self.load_existing_parsing_results(file_path, directory)
            
        # 출력 디렉토리 생성
        output_dir = self.get_output_directory(file_path, directory)
        output_dir.mkdir(exist_ok=True)
        
        # 파일 확장자 확인
        extension = file_path.suffix.lower().lstrip('.')
        if extension not in self.parsers:
            raise ValueError(f"지원하지 않는 파일 형식: {extension}")
            
        parsing_results = {
            "file_info": {
                "name": file_path.name,
                "path": str(file_path),
                "size": file_path.stat().st_size,
                "extension": extension,
                "modified": file_path.stat().st_mtime
            },
            "parsing_timestamp": datetime.now().isoformat(),
            "parsers_used": [],
            "parsing_results": {},
            "summary": {
                "total_parsers": 0,
                "successful_parsers": 0,
                "failed_parsers": 0,
                "best_parser": None,
                "best_quality_score": 0
            }
        }
        
        # 모든 적용 가능한 파서로 파싱 시도
        applicable_parsers = self.parsers[extension]
        parsing_results["summary"]["total_parsers"] = len(applicable_parsers)
        
        for parser_name, parser in applicable_parsers:
            try:
                logger.info(f"🔄 {parser_name} 파서로 파싱 시도")
                result = parser.parse(file_path)
                
                if result.success:
                    parsing_results["summary"]["successful_parsers"] += 1
                    parsing_results["parsers_used"].append(parser_name)
                    
                    # 개별 파서 결과를 파일로 저장 (Markdown 파일 이동 포함)
                    self._save_individual_parser_result(output_dir, parser_name, result)
                    
                    # 파싱 결과 저장 (파일 저장 후 업데이트된 경로 사용)
                    parser_result = {
                        "success": True,
                        "parser_name": result.parser_name,
                        "text_length": len(result.text),
                        "word_count": len(result.text.split()) if result.text else 0,
                        "metadata": self._serialize_metadata(result.metadata) if result.metadata else None,
                        "md_file_path": result.md_file_path,  # 이동 후 업데이트된 경로 사용
                        "parsing_time": getattr(result, 'parsing_time', None)
                    }
                    
                    # 텍스트 품질 점수 계산
                    quality_score = self._calculate_text_quality(result.text)
                    parser_result["quality_score"] = quality_score
                    
                    # 최고 품질 파서 추적
                    if quality_score > parsing_results["summary"]["best_quality_score"]:
                        parsing_results["summary"]["best_quality_score"] = quality_score
                        parsing_results["summary"]["best_parser"] = parser_name
                    
                    # 구조화된 정보 추출 (해당 파서인 경우)
                    structured_info = self._extract_structured_info(result, parser_name)
                    if structured_info:
                        parser_result["structured_info"] = structured_info
                    
                    parsing_results["parsing_results"][parser_name] = parser_result
                    
                    logger.info(f"✅ {parser_name} 파싱 성공 (품질: {quality_score:.2f})")
                    
                else:
                    parsing_results["summary"]["failed_parsers"] += 1
                    parsing_results["parsing_results"][parser_name] = {
                        "success": False,
                        "error_message": result.error_message,
                        "parser_name": result.parser_name
                    }
                    logger.warning(f"❌ {parser_name} 파싱 실패: {result.error_message}")
                    
            except Exception as e:
                parsing_results["summary"]["failed_parsers"] += 1
                parsing_results["parsing_results"][parser_name] = {
                    "success": False,
                    "error_message": str(e),
                    "parser_name": parser_name
                }
                logger.error(f"💥 {parser_name} 파서 오류: {e}")
        
        # 전체 결과 저장
        self._save_comprehensive_results(file_path, parsing_results, directory)
        
        logger.info(f"📋 완전 파싱 완료: 성공 {parsing_results['summary']['successful_parsers']}/{parsing_results['summary']['total_parsers']}")
        return parsing_results
        
    def _serialize_metadata(self, metadata: DocumentMetadata) -> Dict[str, Any]:
        """DocumentMetadata를 직렬화 가능한 딕셔너리로 변환"""
        if not metadata:
            return None
            
        result = {}
        for field in metadata.__dataclass_fields__:
            value = getattr(metadata, field)
            if value is not None:
                # 복잡한 객체들은 문자열로 변환
                if isinstance(value, (list, dict)):
                    result[field] = value
                else:
                    result[field] = str(value) if not isinstance(value, (str, int, float, bool)) else value
        
        return result
        
    def _calculate_text_quality(self, text: str) -> float:
        """텍스트 품질 점수 계산"""
        if not text:
            return 0.0
            
        # 기본 품질 지표들
        length_score = min(len(text) / 1000, 1.0) * 0.3  # 길이 점수 (최대 30%)
        
        # 단어 다양성 점수
        words = text.split()
        if words:
            unique_words = set(words)
            diversity_score = min(len(unique_words) / len(words), 1.0) * 0.3  # 다양성 점수 (최대 30%)
        else:
            diversity_score = 0
        
        # 문장 구조 점수 (마침표, 쉼표 등의 존재)
        punctuation_count = sum(1 for c in text if c in '.!?,:;')
        structure_score = min(punctuation_count / len(text) * 100, 1.0) * 0.2  # 구조 점수 (최대 20%)
        
        # 한글/영어 문자 비율 (의미 있는 텍스트 여부)
        meaningful_chars = sum(1 for c in text if c.isalnum() or c.isspace())
        if len(text) > 0:
            meaning_score = (meaningful_chars / len(text)) * 0.2  # 의미 점수 (최대 20%)
        else:
            meaning_score = 0
            
        total_score = length_score + diversity_score + structure_score + meaning_score
        return min(total_score, 1.0)
        
    def _extract_structured_info(self, result: ParseResult, parser_name: str) -> Optional[Dict[str, Any]]:
        """파서별 구조화된 정보 추출"""
        structured_info = {}
        
        if parser_name == 'docling' and result.metadata:
            # Docling 파서의 경우 테이블, 이미지 등 구조 정보 추출
            if hasattr(result.metadata, 'document_structure'):
                structured_info['document_structure'] = result.metadata.document_structure
            if hasattr(result.metadata, 'tables_count'):
                structured_info['tables_count'] = result.metadata.tables_count
            if hasattr(result.metadata, 'images_count'):
                structured_info['images_count'] = result.metadata.images_count
                
        elif parser_name == 'pdf_parser':
            # PDF 파서의 경우 페이지 정보 등
            if result.metadata and result.metadata.page_count:
                structured_info['pages'] = result.metadata.page_count
                
        # 공통 구조 정보
        if result.text:
            lines = result.text.split('\n')
            structured_info.update({
                'total_lines': len(lines),
                'non_empty_lines': len([l for l in lines if l.strip()]),
                'paragraphs': len([l for l in lines if l.strip() and not l.startswith('#')]),
                'headers': len([l for l in lines if l.strip().startswith('#')])
            })
        
        return structured_info if structured_info else None
        
    def _save_individual_parser_result(self, output_dir: Path, parser_name: str, result: ParseResult):
        """개별 파서 결과를 파일로 저장"""
        try:
            # 파서별 디렉토리 생성
            parser_dir = output_dir / parser_name
            parser_dir.mkdir(exist_ok=True)
            
            # 텍스트 파일 저장
            text_file = parser_dir / f"{parser_name}_text.txt"
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(result.text or "")
            
            # 메타데이터 JSON 저장
            if result.metadata:
                metadata_file = parser_dir / f"{parser_name}_metadata.json"
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(self._serialize_metadata(result.metadata), f, ensure_ascii=False, indent=2)
            
            # 구조화된 정보 저장 (해당하는 경우)
            structured_info = self._extract_structured_info(result, parser_name)
            if structured_info:
                structure_file = parser_dir / f"{parser_name}_structure.json"
                with open(structure_file, 'w', encoding='utf-8') as f:
                    json.dump(structured_info, f, ensure_ascii=False, indent=2)
            
            # Markdown 파일을 올바른 위치로 이동 (docling 및 pymupdf4llm 파서의 경우)
            if result.md_file_path and Path(result.md_file_path).exists():
                import shutil
                source_md_file = Path(result.md_file_path)
                
                # 원본 출력 디렉토리로 이동
                target_md_file = output_dir / source_md_file.name
                try:
                    shutil.move(str(source_md_file), str(target_md_file))
                    logger.info(f"📝 Markdown 파일 이동: {source_md_file} → {target_md_file}")
                    
                    # ParseResult의 md_file_path 업데이트
                    result.md_file_path = str(target_md_file)
                except Exception as move_error:
                    logger.warning(f"⚠️ Markdown 파일 이동 실패: {move_error}")
            
            logger.info(f"📁 {parser_name} 개별 결과 저장 완료: {parser_dir}")
            
        except Exception as e:
            logger.error(f"❌ {parser_name} 개별 결과 저장 실패: {e}")
            
    def _save_comprehensive_results(self, file_path: Path, results: Dict[str, Any], directory: Optional[Path] = None):
        """전체 파싱 결과를 종합 파일로 저장"""
        try:
            result_path = self.get_parsing_result_path(file_path, directory)
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 종합 파싱 결과 저장: {result_path}")
            
        except Exception as e:
            logger.error(f"❌ 종합 결과 저장 실패: {e}")
            
    def get_supported_extensions(self) -> List[str]:
        """지원되는 파일 확장자 목록 반환"""
        return list(self.parsers.keys())
        
    def is_supported_file(self, file_path: Path) -> bool:
        """파일이 지원되는 형식인지 확인"""
        extension = file_path.suffix.lower().lstrip('.')
        return extension in self.parsers