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
from services.parser.auto_parser import AutoParser
from utils.llm_logger import log_prompt_and_response
from services.parser_file_manager import save_parser_results, file_manager

from langchain_ollama import OllamaLLM
LANGCHAIN_AVAILABLE = True

class LocalFileAnalyzer:
    """로컬 파일 분석을 위한 서비스 클래스"""
    
    def __init__(self, db: Session, initialize_extractors: bool = True):
        self.db = db
        self.extractor_manager = None
        if initialize_extractors:
            self._ensure_extractor_manager()

    def _ensure_extractor_manager(self):
        """필요 시 추출기 매니저를 지연 로딩한다."""
        if self.extractor_manager is None:
            from routers.extraction import ExtractorManager  # 지연 로딩으로 초기화 피하기
            self.extractor_manager = ExtractorManager(self.db)
        return self.extractor_manager
        
    def get_file_root(self) -> str:
        """설정에서 파일 루트 디렉토리를 가져오고 없으면 생성"""
        root_path = ConfigService.get_config_value(self.db, "LOCAL_FILE_ROOT", "./data/uploads")
        root_dir = Path(root_path)
        
        # 디렉토리가 존재하지 않으면 생성
        if not root_dir.exists():
            try:
                root_dir.mkdir(parents=True, exist_ok=True)
                print(f"업로드 디렉토리를 생성했습니다: {root_dir.resolve()}")
            except Exception as e:
                print(f"업로드 디렉토리 생성 실패: {e}")
                # 생성 실패 시 현재 디렉토리 사용
                return "."
        
        return root_path
    
    def get_absolute_path(self, file_path: str) -> Path:
        """상대 경로를 절대 경로로 변환"""
        # 현재 작업 디렉토리를 기준으로 사용
        # (change-directory 엔드포인트가 os.chdir()로 변경한 디렉토리)
        current_dir = Path.cwd()
        target_path = Path(file_path)
        
        if target_path.is_absolute():
            # 절대 경로인 경우 그대로 사용
            return target_path.resolve()
        else:
            # 상대 경로인 경우 현재 작업 디렉토리 기준으로 해석
            return (current_dir / target_path).resolve()
    
    def get_result_file_path(self, file_path: str) -> Path:
        """분석 결과 JSON 파일 경로를 생성 - parsing 결과와 같은 디렉토리에 저장"""
        from services.document_parser_service import DocumentParserService
        
        absolute_path = self.get_absolute_path(file_path)
        parser_service = DocumentParserService()
        output_dir = parser_service.get_output_directory(absolute_path)
        result_path = output_dir / "keyword_analysis.json"
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
    
    def parse_file_content(self, file_path: str, use_docling: bool = False) -> str:
        """파일 내용을 파싱하여 텍스트로 변환
        
        Args:
            file_path: 파싱할 파일 경로
            use_docling: Docling 파서 사용 여부 (PDF 파일에만 적용)
        """
        absolute_path = self.get_absolute_path(file_path)
        
        # PDF 파일이고 use_docling이 True인 경우 Docling 파서 사용
        if use_docling and absolute_path.suffix.lower() == '.pdf':
            from services.parser.docling_parser import DoclingParser
            parser = DoclingParser()
            parse_result = parser.parse(absolute_path)
        else:
            # 기본 AutoParser 사용
            parser = AutoParser()
            parse_result = parser.parse(absolute_path)
        
        if not parse_result.success:
            raise ValueError(f"파일 파싱 실패: {parse_result.error_message}")
        
        return parse_result.text
    
    def extract_metadata_with_all_parsers(self, file_path: str, use_llm: bool = True, save_to_file: bool = True) -> Dict[str, Any]:
        """모든 사용 가능한 파서로 메타데이터 추출 시도
        
        Args:
            file_path: 파일 경로
            use_llm: LLM 사용 여부
            save_to_file: 파일로 저장 여부
        
        Returns:
            각 파서의 결과를 포함한 통합 메타데이터
        """
        import hashlib
        from datetime import datetime
        
        absolute_path = self.get_absolute_path(file_path)
        file_stats = absolute_path.stat()
        file_size = file_stats.st_size
        
        # 결과를 저장할 딕셔너리
        all_results = {
            "file_path": file_path,
            "absolute_path": str(absolute_path),
            "extraction_timestamp": datetime.now().isoformat(),
            "parsers_attempted": [],
            "parsers_results": {},
            "best_result": None,
            "file_info": {
                "size": file_size,
                "modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                "extension": absolute_path.suffix.lower()
            }
        }
        
        # PDF 파일인 경우 모든 개별 파서 시도
        if absolute_path.suffix.lower() == '.pdf':
            parsers_to_try = []
            
            # 각 PDF 엔진 추가
            parsers_to_try.extend([
                ("pymupdf4llm", None),
                ("pdfplumber", None),
                ("pymupdf_advanced", None),
                ("pymupdf_basic", None),
                ("pypdf2", None),
                ("docling", "docling")  # Docling은 특별 처리
            ])
        else:
            parsers_to_try = [("default", None)]  # 기본 파서만
        
        best_score = 0
        best_parser = None
        
        for parser_name, parser_type in parsers_to_try:
            try:
                print(f"🔍 {parser_name} 파서로 추출 시도...")
                all_results["parsers_attempted"].append(parser_name)
                
                # Docling 파서인 경우
                if parser_type == "docling":
                    result = self.extract_file_metadata(
                        file_path=file_path,
                        use_llm=False,
                        save_to_file=False,
                        use_docling=True
                    )
                # 개별 PDF 엔진인 경우
                elif parser_name in ["pymupdf4llm", "pdfplumber", "pymupdf_advanced", "pymupdf_basic", "pypdf2"]:
                    result = self.extract_file_metadata_with_specific_engine(
                        file_path=file_path,
                        engine_name=parser_name,
                        use_llm=use_llm and (parser_name == "pymupdf4llm"),  # LLM은 pymupdf4llm에서만 사용
                        save_to_file=False
                    )
                else:
                    # 기본 파서
                    result = self.extract_file_metadata(
                        file_path=file_path,
                        use_llm=use_llm,
                        save_to_file=False,
                        use_docling=False
                    )
                
                # 결과 평가 (점수 계산)
                score = self._evaluate_parser_result(result)
                
                # 결과 저장
                all_results["parsers_results"][parser_name] = {
                    "success": True,
                    "score": score,
                    "metadata": result,
                    "parser_used": result.get("parser_used", parser_name)
                }
                
                # 최고 점수 업데이트
                if score > best_score:
                    best_score = score
                    best_parser = parser_name
                    all_results["best_result"] = parser_name
                    
            except Exception as e:
                print(f"❌ {parser_name} 파서 실패: {e}")
                all_results["parsers_results"][parser_name] = {
                    "success": False,
                    "error": str(e),
                    "score": 0
                }
        
        # 최상의 결과를 기본 메타데이터로 사용
        if best_parser and all_results["parsers_results"][best_parser]["success"]:
            best_metadata = all_results["parsers_results"][best_parser]["metadata"]
            # 최상의 결과를 루트 레벨에 병합
            for key, value in best_metadata.items():
                if key not in ["metadata_file", "markdown_file"]:  # 파일 경로는 제외
                    all_results[key] = value
        
        # 결과를 파일로 저장
        if save_to_file:
            # 통합 결과 저장
            metadata_file = absolute_path.with_suffix(absolute_path.suffix + '.all_parsers.json')
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, ensure_ascii=False, indent=2)
            all_results["metadata_file"] = str(metadata_file)
            
            # 새로운 파서별 개별 파일 저장 시스템 사용
            try:
                saved_parser_files = save_parser_results(file_path, all_results["parsers_results"])
                all_results["individual_parser_files"] = saved_parser_files
                print(f"📁 {len(saved_parser_files)}개 파서의 개별 결과 저장 완료")
            except Exception as e:
                print(f"⚠️ 개별 파서 파일 저장 중 오류: {e}")
            
            # 각 파서별 결과도 기존 방식으로 개별 저장 (호환성 유지)
            for parser_name, result_data in all_results["parsers_results"].items():
                if result_data["success"]:
                    parser_file = absolute_path.with_suffix(f'{absolute_path.suffix}.{parser_name}.json')
                    with open(parser_file, 'w', encoding='utf-8') as f:
                        json.dump(result_data["metadata"], f, ensure_ascii=False, indent=2)

            # PDF의 경우 Markdown 파일도 함께 저장 (.md, .docling.md)
            if absolute_path.suffix.lower() == '.pdf':
                markdown_files = {}
                # 기본 파서 기반 Markdown (.md)
                try:
                    default_text = self.parse_file_content(file_path, use_docling=False)
                    if default_text:
                        md_path = absolute_path.with_suffix('.md')
                        md_content = self.convert_to_markdown(default_text)
                        with open(md_path, 'w', encoding='utf-8') as f:
                            f.write(md_content)
                        markdown_files["default"] = str(md_path)
                except Exception as e:
                    print(f"기본 Markdown 저장 실패: {e}")

                # Docling 기반 Markdown (.docling.md)
                try:
                    docling_text = self.parse_file_content(file_path, use_docling=True)
                    if docling_text:
                        doc_md_path = absolute_path.with_suffix('.docling.md')
                        with open(doc_md_path, 'w', encoding='utf-8') as f:
                            f.write(docling_text)
                        markdown_files["docling"] = str(doc_md_path)
                except Exception as e:
                    print(f"Docling Markdown 저장 실패: {e}")

                if markdown_files:
                    all_results["markdown_files"] = markdown_files

        return all_results
    
    def _evaluate_parser_result(self, result: Dict[str, Any]) -> int:
        """파서 결과의 품질을 평가하여 점수 반환
        
        점수가 높을수록 더 좋은 결과
        """
        score = 0
        
        # 기본 점수 (성공한 경우)
        score += 10
        
        # 메타데이터 필드 수
        score += len(result.keys())
        
        # 구조 정보가 있는 경우 가산점
        if "docling_structure" in result:
            score += 20
            structure = result["docling_structure"]
            if isinstance(structure, dict):
                # 테이블이 있으면 가산점
                if "tables" in structure and len(structure.get("tables", [])) > 0:
                    score += 10 * len(structure["tables"])
                # 섹션이 있으면 가산점
                if "sections" in structure and len(structure.get("sections", [])) > 0:
                    score += 5 * len(structure["sections"])
                # 이미지가 있으면 가산점
                if "images" in structure and len(structure.get("images", [])) > 0:
                    score += 5 * len(structure["images"])
        
        # 문서 구조 정보가 있는 경우
        if "document_structure" in result:
            score += 10
            
        # 텍스트 통계가 있는 경우
        if "text_statistics" in result:
            score += 5
            
        # LLM 분석 결과가 있는 경우
        if "content_analysis" in result:
            score += 15
        
        return score
    
    def extract_file_metadata_with_specific_engine(self, file_path: str, engine_name: str, use_llm: bool = False, save_to_file: bool = True) -> Dict[str, Any]:
        """특정 PDF 엔진을 사용하여 메타데이터 추출
        
        Args:
            file_path: 파일 경로
            engine_name: 사용할 엔진 이름 (pymupdf4llm, pdfplumber, pymupdf_advanced, pymupdf_basic, pypdf2)
            use_llm: LLM 사용 여부
            save_to_file: 파일로 저장 여부
        """
        import hashlib
        from services.parser.pdf_parser import PdfParser
        from services.parser.base import DocumentMetadata
        
        absolute_path = self.get_absolute_path(file_path)
        file_stats = absolute_path.stat()
        file_size = file_stats.st_size
        
        # PDF 파서 생성
        pdf_parser = PdfParser()
        
        # 특정 엔진 선택
        engine_methods = {
            "pymupdf4llm": pdf_parser._parse_with_pymupdf4llm,
            "pdfplumber": pdf_parser._parse_with_pdfplumber,
            "pymupdf_advanced": pdf_parser._parse_with_pymupdf_advanced,
            "pymupdf_basic": pdf_parser._parse_with_pymupdf_basic,
            "pypdf2": pdf_parser._parse_with_pypdf2
        }
        
        if engine_name not in engine_methods:
            raise ValueError(f"지원하지 않는 엔진: {engine_name}")
        
        parse_method = engine_methods[engine_name]
        
        try:
            # 특정 엔진으로 파싱
            text, metadata_dict = parse_method(absolute_path)
            
            if not text:
                raise ValueError(f"{engine_name} 엔진으로 텍스트 추출 실패")
            
            # DocumentMetadata 생성
            metadata = DocumentMetadata(
                title=metadata_dict.get('title', absolute_path.name),
                page_count=metadata_dict.get('page_count', 1),
                word_count=len(text.split()),
                file_size=file_size,
                mime_type='application/pdf',
                parser_name=f"pdf_parser_{engine_name}",
                parser_version="1.0"
            )
            
            # 추가 메타데이터 설정
            for key, value in metadata_dict.items():
                if hasattr(metadata, key) and value is not None:
                    setattr(metadata, key, value)
            
            # DocumentMetadata를 스키마 준수 형식으로 변환
            metadata_result = metadata.to_schema_compliant_dict(
                file_id=None,
                project_id=None
            )
            
            metadata_result["parser_used"] = f"pdf_{engine_name}"
            
            # 파일 정보 추가
            metadata_result["file_info"] = {
                "absolute_path": str(absolute_path),
                "relative_path": file_path,
                "exists": absolute_path.exists(),
                "size": file_size,
                "modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                "created": datetime.fromtimestamp(file_stats.st_ctime).isoformat() if hasattr(file_stats, 'st_ctime') else None,
            }
            
            # 텍스트 통계
            lines = text.split('\n')
            words = text.split()
            
            metadata_result["text_statistics"] = {
                "total_characters": len(text),
                "total_words": len(words),
                "total_lines": len(lines)
            }
            
            # LLM 분석 (요청된 경우)
            if use_llm and text:
                try:
                    llm_metadata = self.extract_metadata_with_llm(text[:10000])
                    if llm_metadata:
                        metadata_result["content_analysis"] = llm_metadata
                except Exception as e:
                    print(f"LLM 메타데이터 추출 실패: {e}")
            
            # 파일 저장
            if save_to_file:
                metadata_file = absolute_path.with_suffix(f'{absolute_path.suffix}.{engine_name}.metadata.json')
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata_result, f, ensure_ascii=False, indent=2)
                metadata_result["metadata_file"] = str(metadata_file)
            
            return metadata_result
            
        except Exception as e:
            raise ValueError(f"{engine_name} 엔진 실행 실패: {e}")
    
    def extract_file_metadata(self, file_path: str, use_llm: bool = True, save_to_file: bool = True, use_docling: bool = False) -> Dict[str, Any]:
        """파일의 메타데이터만 추출 (Dublin Core 표준 준수)
        
        Args:
            file_path: 파일 경로
            use_llm: LLM 사용 여부
            save_to_file: 파일로 저장 여부
            use_docling: Docling 파서 사용 여부 (PDF 파일에만 적용)
        """
        import hashlib
        
        absolute_path = self.get_absolute_path(file_path)
        
        # PDF 파일이고 use_docling이 True인 경우 Docling 파서 사용
        if use_docling and absolute_path.suffix.lower() == '.pdf':
            from services.parser.docling_parser import DoclingParser
            parser = DoclingParser()
            parse_result = parser.parse(absolute_path)
        else:
            # 기본 AutoParser 사용
            parser = AutoParser()
            parse_result = parser.parse(absolute_path)
        
        if not parse_result.success:
            raise ValueError(f"파일 파싱 실패: {parse_result.error_message}")
        
        # 파일 정보 수집
        file_stats = absolute_path.stat()
        file_size = file_stats.st_size
        
        # 메타데이터가 없는 경우 기본값 생성
        if not parse_result.metadata:
            from services.parser.base import DocumentMetadata
            metadata = DocumentMetadata(
                title=absolute_path.name,
                file_size=file_size,
                mime_type=None
            )
        else:
            metadata = parse_result.metadata
        
        # DocumentMetadata를 스키마 준수 형식으로 변환
        metadata_dict = metadata.to_schema_compliant_dict(
            file_id=None,
            project_id=None
        )
        
        # Docling 파서를 사용한 경우 추가 구조 정보 포함
        if use_docling and hasattr(metadata, 'document_structure'):
            metadata_dict["docling_structure"] = metadata.document_structure
            metadata_dict["parser_used"] = "docling"
        else:
            metadata_dict["parser_used"] = parse_result.parser_name if hasattr(parse_result, 'parser_name') else "unknown"
        
        # dc:identifier를 파일 내용의 해시값으로 설정
        if parse_result.text:
            file_hash = hashlib.sha256(parse_result.text.encode('utf-8')).hexdigest()
        else:
            # 텍스트가 없으면 파일 경로와 크기로 해시 생성
            file_hash = hashlib.sha256(f"{absolute_path}:{file_size}".encode('utf-8')).hexdigest()
        metadata_dict["dc:identifier"] = file_hash
        
        # 추가 파일 정보
        metadata_dict["file_info"] = {
            "absolute_path": str(absolute_path),
            "relative_path": file_path,
            "exists": absolute_path.exists(),
            "size": file_size,
            "modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
            "created": datetime.fromtimestamp(file_stats.st_ctime).isoformat() if hasattr(file_stats, 'st_ctime') else None,
        }
        
        # 텍스트 통계 및 문서 구조 분석
        if parse_result.text:
            text = parse_result.text
            
            # PDF의 경우 종종 모든 텍스트가 한 줄로 파싱됨
            # 이 경우 문장 단위로 분리하여 재구성
            if len(text.split('\n')) <= 2 and len(text) > 1000:
                # 문장 단위로 분리
                import re
                sentence_pattern = re.compile(r'([.!?。！？]\s+|\n\n)')
                sentences_list = sentence_pattern.split(text)
                # 재구성된 텍스트 (문장마다 줄바꿈)
                reconstructed_lines = []
                for sent in sentences_list:
                    if sent.strip() and not sentence_pattern.match(sent):
                        reconstructed_lines.append(sent.strip())
                text_for_analysis = '\n'.join(reconstructed_lines)
            else:
                text_for_analysis = text
            
            # 문서 구조 분석
            document_structure = self.analyze_document_structure(text_for_analysis, absolute_path.suffix.lower())
            metadata_dict["document_structure"] = document_structure
            
            # 텍스트 통계
            lines = text_for_analysis.split('\n')
            words = text.split()
            paragraphs = [p for p in text_for_analysis.split('\n\n') if p.strip()]
            sentences = self.count_sentences(text)
            
            metadata_dict["text_statistics"] = {
                "total_characters": len(text),
                "total_words": len(words),
                "total_lines": len(lines),
                "total_paragraphs": len(paragraphs) if paragraphs else 1,
                "total_sentences": sentences,
                "avg_words_per_sentence": len(words) / sentences if sentences > 0 else 0,
                "avg_sentences_per_paragraph": sentences / len(paragraphs) if paragraphs else sentences,
            }
            
            # LLM을 사용한 고급 메타데이터 추출
            if use_llm and parse_result.text:
                try:
                    llm_metadata = self.extract_metadata_with_llm(parse_result.text[:10000])  # 처음 10000자 사용
                    if llm_metadata:
                        metadata_dict["content_analysis"] = llm_metadata
                except Exception as e:
                    print(f"LLM 메타데이터 추출 실패: {e}")
        
        # Unknown, Null, 빈 값 제거
        metadata_dict = self.filter_empty_values(metadata_dict)
        
        # 메타데이터를 JSON 파일로 저장
        if save_to_file:
            # Docling 사용 시 별도 파일명 생성
            if use_docling and metadata_dict.get("parser_used") == "docling":
                metadata_file = absolute_path.with_suffix(absolute_path.suffix + '.docling.metadata.json')
            else:
                metadata_file = absolute_path.with_suffix(absolute_path.suffix + '.metadata.json')
                
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata_dict, f, ensure_ascii=False, indent=2)
            metadata_dict["metadata_file"] = str(metadata_file)
            
            # Markdown 형식으로도 저장 (파싱된 텍스트가 있는 경우)
            if parse_result.text:
                # Docling 사용 시 별도 Markdown 파일 생성
                if use_docling and metadata_dict.get("parser_used") == "docling":
                    markdown_file = absolute_path.with_suffix('.docling.md')
                    with open(markdown_file, 'w', encoding='utf-8') as f:
                        f.write(parse_result.text)
                    metadata_dict["markdown_file"] = str(markdown_file)
                else:
                    self.save_as_markdown(absolute_path, parse_result)
        
        return metadata_dict
    
    def filter_empty_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Unknown, Null, 빈 값을 재귀적으로 제거"""
        if not isinstance(data, dict):
            return data
        
        filtered = {}
        for key, value in data.items():
            # 값이 None이거나 "Unknown"이거나 빈 문자열/리스트인 경우 제외
            if value is None:
                continue
            if isinstance(value, str):
                if value.lower() in ['unknown', 'null', ''] or value.strip() == '':
                    continue
            if isinstance(value, list) and len(value) == 0:
                continue
            if isinstance(value, dict):
                # 딕셔너리는 재귀적으로 처리
                filtered_value = self.filter_empty_values(value)
                if filtered_value:  # 빈 딕셔너리가 아닌 경우만 포함
                    filtered[key] = filtered_value
            else:
                filtered[key] = value
        
        return filtered
    
    def save_as_markdown(self, file_path: Path, parse_result) -> str:
        """파싱 결과를 Markdown 형식으로 저장"""
        markdown_file = file_path.with_suffix('.md')
        
        # 파서가 반환한 원본 텍스트 사용
        content = parse_result.text
        
        # pymupdf4llm이 반환한 markdown이면 그대로 사용
        if hasattr(parse_result, 'parser_name') and 'pymupdf4llm' in parse_result.parser_name:
            # pymupdf4llm은 이미 Markdown 형식으로 반환
            markdown_content = content
        else:
            # 다른 파서의 경우 기본 변환
            markdown_content = self.convert_to_markdown(content)
        
        # 메타데이터 헤더 추가
        if parse_result.metadata:
            header = f"---\ntitle: {parse_result.metadata.title or file_path.name}\n"
            if parse_result.metadata.dc_creator:
                header += f"author: {parse_result.metadata.dc_creator}\n"
            if parse_result.metadata.dc_date:
                header += f"date: {parse_result.metadata.dc_date}\n"
            header += "---\n\n"
            markdown_content = header + markdown_content
        
        # 파일 저장
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return str(markdown_file)
    
    def convert_to_markdown(self, text: str) -> str:
        """일반 텍스트를 Markdown으로 변환"""
        import re
        
        lines = text.split('\n')
        markdown_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # 빈 줄
            if not stripped:
                markdown_lines.append('')
                continue
            
            # 숫자로 시작하는 제목 패턴
            section_match = re.match(r'^(\d+(?:\.\d+)*)\s*[\.)]?\s+(.+)', stripped)
            if section_match:
                level = len(section_match.group(1).split('.'))
                title = section_match.group(2)
                markdown_lines.append('#' * min(level, 6) + ' ' + title)
                continue
            
            # 테이블 감지 (간단한 패턴)
            if '|' in line and line.count('|') >= 2:
                markdown_lines.append(line)
                continue
            
            # 리스트 항목
            if re.match(r'^\s*[-*•]\s+', line):
                markdown_lines.append(line)
                continue
            
            if re.match(r'^\s*\d+[.)]\s+', line):
                markdown_lines.append(line)
                continue
            
            # 일반 단락
            markdown_lines.append(stripped)
        
        return '\n'.join(markdown_lines)
    
    def extract_metadata_with_llm(self, text: str, file_path: str = None) -> Optional[Dict[str, Any]]:
        """LangChain을 사용하여 문서 메타데이터 추출"""
        from services.config_service import ConfigService
        import json
        import logging
        
        # 로거 설정
        logger = logging.getLogger(__name__)
        
        # LangChain 사용 가능 여부 확인
        if not LANGCHAIN_AVAILABLE:
            logger.error("❌ LangChain이 사용 불가능합니다")
            return self._extract_metadata_fallback(text, "LangChain 사용 불가")
        
        # LLM 설정 확인
        llm_enabled = ConfigService.get_bool_config(self.db, "ENABLE_LLM_EXTRACTION", False)
        logger.info(f"🔍 LLM extraction enabled: {llm_enabled}")
        if not llm_enabled:
            logger.warning("⚠️ LLM extraction is disabled in configuration")
            return None
        
        ollama_url = ConfigService.get_config_value(self.db, "OLLAMA_BASE_URL", "http://localhost:11434")
        model_name = ConfigService.get_config_value(self.db, "OLLAMA_MODEL", "llama3.2")
        
        logger.info(f"📋 LLM 설정: URL={ollama_url}, Model={model_name}")
        
        # 메타데이터 추출 프롬프트
        # 텍스트 크기 제한 (더 많은 내용 포함을 위해 증가)
        max_text_length = 10000  # 800 -> 10000으로 증가
        truncated_text = text[:max_text_length]
        
        # 문서 언어 감지 (한글 문자가 많으면 한국어 문서)
        import re
        korean_chars = len(re.findall(r'[가-힣]', truncated_text))
        total_chars = len(truncated_text)
        is_korean_doc = (korean_chars / total_chars) > 0.3 if total_chars > 0 else False
        
        # 더 간단한 프롬프트로 변경 (타임아웃 방지)
        prompt = f"""Extract the document title, main language, and a brief summary from the following text.

Requirements:
- Return only valid JSON. No explanations, no markdown, no extra text.
- JSON must contain exactly these keys:
  {{
    "title": string,        // extracted or inferred document title
    "language": "ko" | "en" | "other",  // detected main language
    "summary": string       // concise summary (1–2 sentences max)
  }}
- Ensure the JSON is valid and can be parsed without errors.

Text:
{truncated_text}
"""
        
        logger.info(f"🤖 LangChain Ollama 호출 시작: {ollama_url}")
        logger.debug(f"📝 Prompt 길이: {len(prompt)} 문자")
        
        try:
            # LangChain Ollama 클라이언트 생성 - 매우 긴 타임아웃으로 테스트
            ollama_client = OllamaLLM(
                base_url=ollama_url,
                model=model_name,
                timeout=360,  # 6분으로 증가
                temperature=0.3,  # 클라이언트 생성시 설정
            )
            
            logger.info(f"📤 LangChain 요청 (model={model_name}, timeout=360초(6분), temperature=0.3)")
            
            # 먼저 간단한 테스트로 타임아웃 확인
            logger.info("🧪 모델 응답성 테스트 중...")
            import time
            test_start = time.time()
            try:
                test_response = ollama_client.invoke("Say hello in JSON: {\"greeting\": \"hello\"}")
                test_duration = time.time() - test_start
                logger.info(f"✅ 간단한 테스트 성공 - 소요시간: {test_duration:.2f}초, 응답: {test_response[:100]}")
            except Exception as test_error:
                test_duration = time.time() - test_start
                logger.error(f"❌ 간단한 테스트 실패 - 소요시간: {test_duration:.2f}초, 오류: {test_error}")
            
            logger.info(f"⏱️ 실제 메타데이터 추출 시작 (긴 텍스트로 인한 지연이 예상됩니다...)") 
            
            # 시작 시간 기록
            start_time = time.time()
            
            # LangChain을 통해 호출
            response_text = ollama_client.invoke(prompt)
            
            # 종료 시간 기록
            end_time = time.time()
            duration = end_time - start_time
            
            logger.info(f"🔧 LangChain 호출 완료 - 소요시간: {duration:.2f}초")
            
            logger.info(f"📥 LangChain 응답 길이: {len(response_text)} 문자")
            if response_text:
                logger.debug(f"📄 응답 미리보기: {response_text[:200]}...")
            else:
                logger.warning("⚠️ LangChain에서 빈 응답 반환")
            
            # 프롬프트/응답 파일 저장 (결과 파일들과 같은 디렉토리에)
            base_dir = "tests/debug_outputs/llm"  # 기본값
            if file_path:
                try:
                    from services.document_parser_service import DocumentParserService
                    absolute_path = self.get_absolute_path(file_path)
                    parser_service = DocumentParserService()
                    output_dir = parser_service.get_output_directory(absolute_path)
                    base_dir = str(output_dir)
                except Exception:
                    pass  # 기본값 사용
            
            log_prompt_and_response(
                label="local_metadata_langchain",
                provider="ollama",
                model=model_name,
                prompt=prompt,
                response=response_text,
                logger=logger,
                base_dir=base_dir,
                meta={
                    "base_url": ollama_url,
                    "temperature": 0.3,
                    "format": "json",
                    "langchain_version": True,
                },
            )
            
            # 빈 응답 처리
            if not response_text or response_text.strip() == "":
                logger.error("❌ LangChain에서 빈 응답을 반환했습니다")
                return self._extract_metadata_fallback(text, "LangChain 빈 응답")
            
            # JSON 파싱 시도
            try:
                original_response = response_text
                
                # JSON 부분만 추출 (```json ... ``` 처리)
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                    logger.debug("🔧 Extracted JSON from ```json``` blocks")
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                    logger.debug("🔧 Extracted JSON from ``` blocks")
                
                # 첫 번째 { 와 마지막 } 사이의 내용만 추출
                if "{" in response_text and "}" in response_text:
                    json_start = response_text.find("{")
                    json_end = response_text.rfind("}") + 1
                    response_text = response_text[json_start:json_end]
                    logger.debug("🔧 Extracted JSON between { and }")
                
                def repair_json_like(s: str) -> str:
                    """간단한 JSON 복구: 잘못된 인용부호/쉼표/코드펜스 정리"""
                    import re
                    # 스마트 인용부호를 ASCII로 변환
                    s = s.replace(""", '"').replace(""", '"').replace("'", "'")
                    # 키에 사용된 단일 인용부호를 이스케이프된 쌍따옴표로 변경
                    s = re.sub(r"'([A-Za-z0-9_\- ]+)'\s*:", r'"\1":', s)
                    # 값에 사용된 단일 인용부호 문자열을 쌍따옴표로 변경
                    s = re.sub(r":\s*'([^']*)'", r': "\1"', s)
                    # 끝에 붙은 쉼표 제거
                    s = re.sub(r",\s*([}\]])", r"\1", s)
                    # BOM/제어문자 제거
                    s = s.replace("\ufeff", "").strip()
                    return s
                
                try:
                    metadata = json.loads(response_text)
                except json.JSONDecodeError:
                    repaired = repair_json_like(response_text)
                    metadata = json.loads(repaired)
                    logger.info("🛠️ Non‑strict JSON repaired successfully")
                
                logger.info(f"✅ LangChain 메타데이터 추출 성공: {list(metadata.keys())}")
                # 원본 응답도 포함
                metadata["_llm_metadata"] = {
                    "raw_response": original_response,
                    "extraction_status": "langchain_success",
                    "model": model_name,
                    "response_length": len(original_response)
                }
                return metadata
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON 파싱 실패: {e}")
                logger.error(f"📄 문제가 된 응답 (처음 500자): {response_text[:500]}")
                logger.warning("⚠️ 폴백 메타데이터 추출로 전환")
                
                return self._extract_metadata_fallback(text, f"JSON 파싱 실패: {str(e)}")
                
        except Exception as e:
            logger.error(f"❌ LangChain 메타데이터 추출 실패: {e}")
            logger.exception("상세 오류 정보:")
            
            # 오류 시에도 로깅
            try:
                # 출력 디렉토리 설정
                base_dir = "tests/debug_outputs/llm"  # 기본값
                if file_path:
                    try:
                        from services.document_parser_service import DocumentParserService
                        absolute_path = self.get_absolute_path(file_path)
                        parser_service = DocumentParserService()
                        output_dir = parser_service.get_output_directory(absolute_path)
                        base_dir = str(output_dir)
                    except Exception:
                        pass  # 기본값 사용
                        
                log_prompt_and_response(
                    label="local_metadata_langchain_error",
                    provider="ollama",
                    model=model_name,
                    prompt=prompt,
                    response="",
                    logger=logger,
                    base_dir=base_dir,
                    meta={"base_url": ollama_url, "error": f"exception: {e}", "langchain_version": True},
                )
            except Exception:
                pass
            
            return self._extract_metadata_fallback(text, f"LangChain 오류: {str(e)}")
    
    def _test_ollama_model(self, ollama_url: str, model_name: str) -> bool:
        """LangChain으로 Ollama 모델 상태를 간단히 테스트"""
        import logging
        logger = logging.getLogger(__name__)
        
        if not LANGCHAIN_AVAILABLE:
            logger.warning("⚠️ LangChain을 사용할 수 없어 모델 테스트를 건너뜀")
            return False
        
        try:
            logger.debug(f"🧪 LangChain으로 모델 테스트 중: {model_name}")
            
            # LangChain Ollama 클라이언트로 간단한 테스트
            ollama_client = OllamaLLM(
                base_url=ollama_url,
                model=model_name,
                timeout=15
            )
            
            test_response = ollama_client.invoke("Hello")
            
            if test_response and test_response.strip():
                logger.info(f"✅ LangChain 모델 테스트 성공: '{test_response.strip()[:50]}'")
                return True
            else:
                logger.warning("⚠️ LangChain 모델 테스트 - 빈 응답 반환")
                return False
                
        except Exception as e:
            logger.warning(f"⚠️ LangChain 모델 테스트 중 오류: {e}")
            return False
    
    def _extract_metadata_fallback(self, text: str, error_reason: str) -> Dict[str, Any]:
        """LLM 실패 시 기본 메타데이터 추출"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"📋 폴백 메타데이터 추출 시작 - 사유: {error_reason}")
        
        # 텍스트에서 기본 정보 추출
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # 제목 추출 시도 (첫 번째 의미있는 줄)
        title = "제목 추출 실패"
        for line in lines[:10]:
            if (len(line) > 5 and len(line) < 200 and
                not line.replace('.', '').replace('-', '').replace('#', '').replace('=', '').isdigit() and
                not line.startswith('http') and
                not '@' in line):
                title = line[:100]  # 제목은 100자로 제한
                break
        
        # 기본 키워드 추출 (빈도 기반)
        import re
        words = re.findall(r'\b[가-힣a-zA-Z]{3,}\b', text)
        word_freq = {}
        for word in words:
            if len(word) >= 3:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # 상위 5개 단어를 키워드로 사용
        keywords = [word for word, freq in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]]
        
        # 언어 감지
        korean_chars = len(re.findall(r'[가-힣]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        language = "ko" if korean_chars > english_chars else "en"
        
        # 문서 타입 추정
        doc_type = "문서"
        if "보고서" in text or "report" in text.lower():
            doc_type = "보고서"
        elif "논문" in text or "paper" in text.lower() or "abstract" in text.lower():
            doc_type = "논문"
        elif "매뉴얼" in text or "manual" in text.lower() or "guide" in text.lower():
            doc_type = "매뉴얼"
        
        fallback_metadata = {
            "title": title,
            "document_type": doc_type,
            "language": language,
            "keywords": keywords,
            "summary": f"폴백 모드로 추출된 메타데이터 - 원인: {error_reason}",
            "main_topics": keywords[:3],  # 상위 3개를 주요 토픽으로
            "date": None,
            "extraction_status": "fallback",
            "fallback_reason": error_reason,
            "_llm_metadata": {
                "raw_response": "",
                "extraction_status": "fallback",
                "model": "none",
                "response_length": 0,
                "fallback_reason": error_reason
            }
        }
        
        logger.info(f"✅ 폴백 메타데이터 생성 완료 - 제목: '{title[:50]}', 키워드: {len(keywords)}개")
        return fallback_metadata
    
    def _extract_metadata_with_langchain(self, text: str, ollama_url: str, model_name: str) -> Optional[Dict[str, Any]]:
        """LangChain을 사용하여 메타데이터 추출 시도"""
        if not LANGCHAIN_AVAILABLE:
            return None
            
        import logging
        import json
        logger = logging.getLogger(__name__)
        
        try:
            # LangChain Ollama 클라이언트 생성
            ollama_client = OllamaLLM(
                base_url=ollama_url,
                model=model_name,
                timeout=60
            )
            
            # 간소화된 프롬프트 (더 안정적인 응답을 위해)
            prompt = f"""Analyze this document and extract metadata in JSON format:

{text[:15000]}

Return only a JSON object with these fields:
{{
    "title": "document title or first meaningful line",
    "summary": "1-2 sentence summary",
    "keywords": ["key1", "key2", "key3"],
    "language": "ko or en"
}}

JSON only, no explanations:"""
            
            logger.debug(f"🔗 LangChain 호출 시작 - 모델: {model_name}")
            
            # LangChain을 통해 호출
            response = ollama_client.invoke(prompt)
            
            logger.debug(f"📄 LangChain 응답 길이: {len(response)} 문자")
            
            if not response or response.strip() == "":
                logger.warning("⚠️ LangChain에서도 빈 응답 반환")
                return None
            
            # 프롬프트/응답 로깅 (결과 파일들과 같은 디렉토리에)
            base_dir = "tests/debug_outputs/llm"  # 기본값
            if hasattr(self, '_current_file_path') and self._current_file_path:
                try:
                    from services.document_parser_service import DocumentParserService
                    absolute_path = self.get_absolute_path(self._current_file_path)
                    parser_service = DocumentParserService()
                    output_dir = parser_service.get_output_directory(absolute_path)
                    base_dir = str(output_dir)
                except Exception:
                    pass  # 기본값 사용
            
            log_prompt_and_response(
                label="local_metadata_langchain",
                provider="ollama",
                model=model_name,
                prompt=prompt,
                response=response,
                logger=logger,
                base_dir=base_dir,
                meta={
                    "base_url": ollama_url,
                    "langchain_version": True,
                },
            )
            
            # JSON 파싱 시도
            try:
                # JSON 부분 추출
                json_text = response.strip()
                if "```json" in json_text:
                    start_idx = json_text.find("```json") + 7
                    end_idx = json_text.find("```", start_idx)
                    if end_idx != -1:
                        json_text = json_text[start_idx:end_idx]
                
                # 첫 번째 { 부터 마지막 } 까지 추출
                start = json_text.find('{')
                end = json_text.rfind('}')
                if start != -1 and end != -1 and end > start:
                    json_text = json_text[start:end+1]
                
                metadata = json.loads(json_text)
                
                # 기본 필드 보장
                result = {
                    "title": metadata.get("title", "제목 추출 실패"),
                    "document_type": "문서",
                    "language": metadata.get("language", "ko"),
                    "keywords": metadata.get("keywords", []),
                    "summary": metadata.get("summary", "LangChain으로 추출된 메타데이터"),
                    "main_topics": metadata.get("keywords", [])[:3],
                    "date": metadata.get("date"),
                    "extraction_status": "langchain_success",
                    "_llm_metadata": {
                        "raw_response": response,
                        "extraction_status": "langchain_success",
                        "model": model_name,
                        "response_length": len(response)
                    }
                }
                
                logger.info(f"✅ LangChain으로 메타데이터 추출 성공 - 제목: '{result['title'][:50]}'")
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ LangChain 응답 JSON 파싱 실패: {e}")
                logger.debug(f"📄 LangChain 응답: {response[:500]}")
                return None
                
        except Exception as e:
            logger.error(f"❌ LangChain 메타데이터 추출 실패: {e}")
            return None

    def analyze_document_structure(self, text: str, file_extension: str) -> Dict[str, Any]:
        """문서 구조 분석 (섹션, 테이블, 그림 등)"""
        import re
        
        structure = {
            "sections": [],
            "tables_count": 0,
            "figures_count": 0,
            "references_count": 0,
            "footnotes_count": 0,
            "lists_count": 0,
            "headings_hierarchy": []
        }
        
        lines = text.split('\n')
        
        # 섹션/제목 패턴 감지 (더 포괄적인 패턴)
        # 숫자로 시작하는 제목 패턴 (1. , 1.1, 2.3.4 등)
        section_pattern = re.compile(r'^(\d+(?:\.\d+)*)\s*[\.)]?\s+(.+)')
        # 로마 숫자 패턴 (I., II., III. 등)
        roman_pattern = re.compile(r'^([IVXLCDM]+)\s*[\.)]?\s+(.+)')
        # Markdown 스타일 헤더 (###)
        markdown_pattern = re.compile(r'^(#{1,6})\s+(.+)')
        
        # 한국어 섹션 패턴 (제1장, 제2절, 1장, 2절 등)
        korean_section_pattern = re.compile(r'^제?\s*(\d+)\s*[장절항]\s*[\.:]?\s*(.+)')
        
        # 대문자로 시작하는 제목 패턴 (주로 영문 문서)
        # PDF에서 자주 나타나는 패턴
        uppercase_title_pattern = re.compile(r'^([A-Z][A-Z\s]{2,})\s*$')
        
        # 콜론이나 대시로 끝나는 제목 패턴
        title_with_separator = re.compile(r'^([가-힣A-Za-z0-9\s]+)\s*[:：-]\s*$')
        
        # 들여쓰기가 없고 짧은 독립 라인 (제목일 가능성)
        potential_title_pattern = re.compile(r'^[^\s](.{5,50})$')
        
        # 테이블 감지 패턴 (확장)
        table_patterns = [
            re.compile(r'\|.*\|'),  # Markdown 테이블
            re.compile(r'[<\[]?\s*표\s*\d+', re.IGNORECASE),  # "표 1", "<표 1>", "[표 1]"
            re.compile(r'Table\s*\d+', re.IGNORECASE),
            re.compile(r'<table', re.IGNORECASE),  # HTML 테이블
            re.compile(r'┌|├|└|─|│'),  # Box drawing 문자
            re.compile(r'[표表]\s*[\d一二三四五六七八九十]+'),  # 한자 숫자 포함
        ]
        
        # 그림/차트 감지 패턴 (확장)
        figure_patterns = [
            re.compile(r'[<\[]?\s*그림\s*\d+', re.IGNORECASE),  # "그림 1", "<그림 1>"
            re.compile(r'Figure\s*\d+', re.IGNORECASE),
            re.compile(r'Fig\.\s*\d+', re.IGNORECASE),
            re.compile(r'[<\[]?\s*차트\s*\d+', re.IGNORECASE),
            re.compile(r'Chart\s*\d+', re.IGNORECASE),
            re.compile(r'[<\[]?\s*도표\s*\d+', re.IGNORECASE),  # 도표
            re.compile(r'[<\[]?\s*사진\s*\d+', re.IGNORECASE),  # 사진
            re.compile(r'[<\[]?\s*이미지\s*\d+', re.IGNORECASE),  # 이미지
            re.compile(r'!\[.*\]\(.*\)'),  # Markdown 이미지
        ]
        
        # 참고문헌 감지
        reference_patterns = [
            re.compile(r'^\[\d+\]'),  # [1] 스타일
            re.compile(r'참고문헌', re.IGNORECASE),
            re.compile(r'References', re.IGNORECASE),
            re.compile(r'Bibliography', re.IGNORECASE),
        ]
        
        # 각주 감지
        footnote_patterns = [
            re.compile(r'\[\^\d+\]'),  # Markdown 각주
            re.compile(r'주\s*\d+[:\)]'),  # "주1:", "주 1)"
        ]
        
        # 리스트 감지
        list_patterns = [
            re.compile(r'^\s*[-*•]\s+'),  # 불릿 리스트
            re.compile(r'^\s*\d+[.)]\s+'),  # 번호 리스트
            re.compile(r'^\s*[a-z][.)]\s+', re.IGNORECASE),  # 알파벳 리스트
        ]
        
        # 라인별 분석
        prev_line = ""
        next_line = ""
        
        for i, line in enumerate(lines):
            # 이전 라인과 다음 라인 참조 (컨텍스트 분석용)
            prev_line = lines[i-1] if i > 0 else ""
            next_line = lines[i+1] if i < len(lines)-1 else ""
            
            stripped_line = line.strip()
            
            # 빈 줄 건너뛰기
            if not stripped_line:
                continue
            
            # 섹션/제목 감지
            section_match = section_pattern.match(stripped_line)
            if section_match:
                section_num = section_match.group(1)
                section_title = section_match.group(2)
                level = len(section_num.split('.'))
                structure["sections"].append({
                    "number": section_num,
                    "title": section_title,
                    "level": level,
                    "line": i + 1
                })
                structure["headings_hierarchy"].append(level)
                continue
            
            # 한국어 섹션 패턴
            korean_match = korean_section_pattern.match(stripped_line)
            if korean_match:
                structure["sections"].append({
                    "number": korean_match.group(1),
                    "title": korean_match.group(2) if korean_match.group(2) else stripped_line,
                    "level": 1,
                    "line": i + 1,
                    "style": "korean"
                })
                structure["headings_hierarchy"].append(1)
                continue
            
            # 로마 숫자 섹션
            roman_match = roman_pattern.match(stripped_line)
            if roman_match and len(roman_match.group(1)) <= 4:  # 너무 긴 로마 숫자는 제외
                structure["sections"].append({
                    "number": roman_match.group(1),
                    "title": roman_match.group(2),
                    "level": 1,
                    "line": i + 1
                })
                structure["headings_hierarchy"].append(1)
                continue
            
            # Markdown 헤더
            markdown_match = markdown_pattern.match(stripped_line)
            if markdown_match:
                level = len(markdown_match.group(1))
                structure["sections"].append({
                    "title": markdown_match.group(2),
                    "level": level,
                    "line": i + 1,
                    "style": "markdown"
                })
                structure["headings_hierarchy"].append(level)
                continue
            
            # 대문자 제목 (영문 문서)
            if uppercase_title_pattern.match(stripped_line) and len(stripped_line) < 50:
                # 앞뒤가 빈 줄인 경우 제목일 가능성 높음
                if (not prev_line.strip() or not next_line.strip()):
                    structure["sections"].append({
                        "title": stripped_line,
                        "level": 1,
                        "line": i + 1,
                        "style": "uppercase"
                    })
                    structure["headings_hierarchy"].append(1)
                    continue
            
            # 콜론이나 대시로 끝나는 제목
            if title_with_separator.match(stripped_line):
                structure["sections"].append({
                    "title": title_with_separator.match(stripped_line).group(1),
                    "level": 2,
                    "line": i + 1,
                    "style": "separator"
                })
                structure["headings_hierarchy"].append(2)
                continue
            
            # 짧은 독립 라인 (전후 빈 줄이 있고 길이가 적절한 경우)
            if (len(stripped_line) > 5 and len(stripped_line) < 50 and 
                not prev_line.strip() and not next_line.strip() and 
                not stripped_line.endswith(('.', '。', '!', '?', '！', '？'))):
                # 숫자나 특수문자로 시작하지 않는 경우
                if re.match(r'^[가-힣A-Za-z]', stripped_line):
                    structure["sections"].append({
                        "title": stripped_line,
                        "level": 3,
                        "line": i + 1,
                        "style": "isolated"
                    })
                    structure["headings_hierarchy"].append(3)
            
            # 테이블 감지
            for pattern in table_patterns:
                if pattern.search(line):
                    structure["tables_count"] += 1
                    break
            
            # 그림/차트 감지
            for pattern in figure_patterns:
                if pattern.search(line):
                    structure["figures_count"] += 1
                    break
            
            # 참고문헌 감지
            for pattern in reference_patterns:
                if pattern.search(line):
                    structure["references_count"] += 1
                    break
            
            # 각주 감지
            for pattern in footnote_patterns:
                if pattern.search(line):
                    structure["footnotes_count"] += 1
                    break
            
            # 리스트 감지
            for pattern in list_patterns:
                if pattern.match(line):
                    structure["lists_count"] += 1
                    break
        
        # 섹션 정리 및 요약
        if structure["sections"]:
            # 중복 제거 (같은 라인의 섹션 제거)
            seen_lines = set()
            unique_sections = []
            for section in structure["sections"]:
                if section["line"] not in seen_lines:
                    seen_lines.add(section["line"])
                    unique_sections.append(section)
            
            structure["sections"] = unique_sections
            structure["total_sections"] = len(unique_sections)
            structure["max_heading_level"] = max(structure["headings_hierarchy"]) if structure["headings_hierarchy"] else 0
            
            # 섹션을 레벨별로 분류
            sections_by_level = {}
            for section in unique_sections:
                level = section.get("level", 1)
                if level not in sections_by_level:
                    sections_by_level[level] = []
                sections_by_level[level].append(section["title"])
            
            structure["sections_by_level"] = sections_by_level
            
            # 주요 섹션만 추출 (상위 20개)
            structure["main_sections"] = [s["title"] for s in unique_sections[:20]]
        else:
            # 섹션이 없는 경우 기본값 설정
            structure["total_sections"] = 0
            structure["max_heading_level"] = 0
            structure["sections_by_level"] = {}
            structure["main_sections"] = []
        
        # 문서 구조 요약
        structure["document_outline"] = {
            "has_table_of_contents": any("목차" in s.get("title", "") or "Contents" in s.get("title", "") for s in structure["sections"]),
            "has_introduction": any("서론" in s.get("title", "") or "Introduction" in s.get("title", "") or "개요" in s.get("title", "") for s in structure["sections"]),
            "has_conclusion": any("결론" in s.get("title", "") or "Conclusion" in s.get("title", "") or "맺음" in s.get("title", "") for s in structure["sections"]),
            "has_references": structure["references_count"] > 0,
            "has_appendix": any("부록" in s.get("title", "") or "Appendix" in s.get("title", "") for s in structure["sections"]),
            "structure_quality": "good" if structure.get("total_sections", 0) > 3 else "poor"
        }
        
        return structure
    
    def count_sentences(self, text: str) -> int:
        """문장 개수 계산"""
        import re
        # 한국어와 영어 문장 종결 부호 고려
        sentence_endings = re.compile(r'[.!?。！？]+[\s\n]')
        sentences = sentence_endings.split(text)
        # 빈 문장 제외
        return len([s for s in sentences if s.strip()])
    
    def analyze_document_structure_with_llm(self, text: str, file_path: str, file_extension: str, overrides: Dict[str, Any] = None) -> Dict[str, Any]:
        """LLM을 사용한 문서 구조 분석 (Ollama/OpenAI/Gemini)
        
        overrides: 요청 단위로 LLM 구성을 덮어쓰는 옵션(dict)
        예) {"enabled": true, "provider": "gemini", "model": "models/gemini-2.0-flash", "api_key": "...", "base_url": "...", "max_tokens": 1000, "temperature": 0.2}
        """
        import logging
        import json
        from services.config_service import ConfigService
        from prompts.templates import DocumentStructurePrompts
        from utils.llm_logger import log_prompt_and_response
        
        logger = logging.getLogger(__name__)
        
        # LLM 설정 확인
        overrides = overrides or {}
        llm_enabled = overrides.get("enabled") if "enabled" in overrides else ConfigService.get_bool_config(self.db, "ENABLE_LLM_EXTRACTION", False)
        if not llm_enabled:
            logger.warning("⚠️ LLM extraction is disabled in configuration")
            return self._fallback_structure_analysis(text, file_extension)
        
        provider = overrides.get("provider") or ConfigService.get_config_value(self.db, "LLM_PROVIDER", "ollama")
        timeout_override = overrides.get("timeout")
        ollama_timeout_default = ConfigService.get_int_config(self.db, "OLLAMA_TIMEOUT", 120)
        ollama_timeout = timeout_override or ollama_timeout_default
        logger.info(f"🔍 LLM 기반 문서 구조 분석 시작 - provider={provider}")

        try:
            # Provider별 모델/엔드포인트 구성
            logger.info(f"🔍 Provider 설정 시작: {provider}")
            if provider == "ollama":
                ollama_url = overrides.get("base_url") or ConfigService.get_config_value(self.db, "OLLAMA_BASE_URL", "http://localhost:11434")
                model_name = overrides.get("model") or ConfigService.get_config_value(self.db, "OLLAMA_MODEL", "llama3.2")
                openai_conf = None
                gemini_conf = None
            elif provider == "openai":
                openai_conf = {**ConfigService.get_openai_config(self.db), **overrides}
                if timeout_override is not None:
                    openai_conf["timeout"] = timeout_override
                openai_conf.setdefault("timeout", 120)
                gemini_conf = None
                model_name = openai_conf.get("model")
            elif provider == "gemini":
                gemini_conf = {**ConfigService.get_gemini_config(self.db), **overrides}
                if timeout_override is not None:
                    gemini_conf["timeout"] = timeout_override
                gemini_conf.setdefault("timeout", 120)
                openai_conf = None
                model_name = gemini_conf.get("model")
            else:
                logger.warning(f"알 수 없는 LLM provider '{provider}', ollama로 폴백")
                provider = "ollama"
                ollama_url = overrides.get("base_url") or ConfigService.get_config_value(self.db, "OLLAMA_BASE_URL", "http://localhost:11434")
                model_name = overrides.get("model") or ConfigService.get_config_value(self.db, "OLLAMA_MODEL", "llama3.2")
                openai_conf = None
                gemini_conf = None
                ollama_timeout = timeout_override or ollama_timeout_default
        except Exception as e:
            logger.error(f"❌ LLM provider 설정 실패: {e}")
            return self._fallback_structure_analysis(text, file_extension)

        is_gemini_flash_25 = bool(provider == "gemini" and isinstance(model_name, str) and "2.5" in model_name)
        if is_gemini_flash_25 and gemini_conf is not None:
            gemini_conf.setdefault("response_mime_type", "application/json")

        logger.info(f"🔍 LLM 모델: {model_name}")
        if is_gemini_flash_25:
            logger.info("✨ Gemini 2.5 Flash 전용 프롬프트 및 응답 설정 적용")
        
        try:
            # LangChain Ollama 클라이언트 또는 HTTP 호출 준비
            ollama_client = None
            if provider == "ollama":
                try:
                    from langchain_ollama import OllamaLLM
                    ollama_client = OllamaLLM(
                        base_url=ollama_url,
                        model=model_name,
                        timeout=ollama_timeout,
                        temperature=0.2,
                    )
                except Exception as e:
                    logger.error(f"❌ Ollama 클라이언트 초기화 실패: {e}")
                    return self._fallback_structure_analysis_with_llm_attempt(text, file_extension, str(e))
            
            # 텍스트 길이 제한 (더 많은 내용 포함을 위해 증가)
            max_text_length = 15000  # 3000 -> 15000으로 증가
            truncated_text = text[:max_text_length] if len(text) > max_text_length else text
            
            # 프롬프트 템플릿 사용
            prompt_template = (
                DocumentStructurePrompts.STRUCTURE_ANALYSIS_LLM_GEMINI_FLASH25
                if is_gemini_flash_25
                else DocumentStructurePrompts.STRUCTURE_ANALYSIS_LLM
            )
            
            # 파일 정보 준비
            from pathlib import Path
            file_path_obj = Path(file_path) if isinstance(file_path, str) else file_path
            file_info = {
                "filename": file_path_obj.name,
                "extension": file_extension,
                "size": len(text),
                "truncated_size": len(truncated_text)
            }
            
            # 프롬프트 생성
            prompt = prompt_template.format(
                file_info=json.dumps(file_info, ensure_ascii=False, indent=2),
                text=truncated_text
            )
            
            logger.info(f"📤 LLM 구조 분석 요청 중... (텍스트 길이: {len(truncated_text)} 문자)")
            
            # LLM 호출
            if provider == "ollama":
                try:
                    logger.info("🔍 Ollama 호출 시작...")
                    logger.info(f"🔍 프롬프트 길이: {len(prompt)}자")
                    response = ollama_client.invoke(prompt)
                    logger.info(f"🔍 Ollama 응답 성공 - 길이: {len(response)}자")
                    logger.info(f"🔍 Ollama 응답 시작부 (300자): {response[:300]!r}")
                    logger.info(f"🔍 Ollama 응답 끝부 (300자): {response[-300:]!r}")
                except Exception as e:
                    logger.error(f"❌ Ollama 호출 중 예외 발생: {type(e).__name__}: {e}")
                    import traceback
                    logger.error(f"❌ 예외 상세: {traceback.format_exc()}")
                    raise e
                base_dir_provider = "ollama"
                base_url_meta = ollama_url
            elif provider == "openai":
                response = self._call_openai_chat(prompt, openai_conf)
                base_dir_provider = "openai"
                base_url_meta = openai_conf.get("base_url", "https://api.openai.com/v1")
            elif provider == "gemini":
                response = self._call_gemini_generate(prompt, gemini_conf)
                base_dir_provider = "gemini"
                base_url_meta = gemini_conf.get("base_url", "https://generativelanguage.googleapis.com")
            else:
                return self._fallback_structure_analysis_with_llm_attempt(text, file_extension, f"Unsupported provider: {provider}")
            
            logger.info(f"📥 LLM 응답 수신 완료 (길이: {len(response)} 문자)")
            
            # 프롬프트/응답 로깅 (결과 파일들과 같은 디렉토리에)
            base_dir = "tests/debug_outputs/llm"  # 기본값
            try:
                from services.document_parser_service import DocumentParserService
                absolute_path = self.get_absolute_path(file_path) if isinstance(file_path, str) else file_path
                parser_service = DocumentParserService()
                output_dir = parser_service.get_output_directory(absolute_path)
                base_dir = str(output_dir)
            except Exception:
                pass  # 기본값 사용
                
            log_prompt_and_response(
                label="document_structure_analysis",
                provider=base_dir_provider,
                model=model_name,
                prompt=prompt,
                response=response,
                logger=logger,
                base_dir=base_dir,
                meta={
                    "base_url": base_url_meta,
                    "temperature": 0.2,
                    "file_extension": file_extension,
                    "text_length": len(text),
                    "truncated_length": len(truncated_text)
                }
            )
            
            # JSON 파싱 시도
            try:
                # JSON 응답 추출
                json_response = self._extract_json_from_response(response)
                if json_response:
                    # 기본 구조 분석과 병합
                    basic_structure = self.analyze_document_structure(text, file_extension)
                    
                    # LLM 분석 결과 추가
                    enhanced_structure = {
                        **basic_structure,
                        "llm_analysis": json_response,
                        "analysis_method": "llm_enhanced",
                        "llm_model": model_name,
                        "llm_success": True
                    }
                    
                    # LLM에서 추출한 구조 정보로 기본 분석 보완
                    if "sections" in json_response:
                        enhanced_structure["llm_detected_sections"] = json_response["sections"]
                    
                    if "document_type" in json_response:
                        enhanced_structure["document_type"] = json_response["document_type"]
                    
                    if "main_topics" in json_response:
                        enhanced_structure["main_topics"] = json_response["main_topics"]
                    
                    logger.info("✅ LLM 기반 문서 구조 분석 성공")
                    return enhanced_structure
                else:
                    raise ValueError("JSON 응답을 추출할 수 없음")
                    
            except Exception as parse_error:
                logger.error(f"❌ LLM 응답 파싱 실패: {parse_error}")
                logger.debug(f"📄 문제가 된 응답: {response[:500]}")
                return self._fallback_structure_analysis_with_llm_attempt(text, file_extension, str(parse_error))
                
        except Exception as e:
            logger.error(f"❌ LLM 구조 분석 실패: {e}")
            return self._fallback_structure_analysis_with_llm_attempt(text, file_extension, str(e))

    def _call_openai_chat(self, prompt: str, conf: Dict[str, Any]) -> str:
        """OpenAI Chat Completions 호출 (단순 문자열 응답)."""
        import requests
        import logging
        logger = logging.getLogger(__name__)
        api_key = conf.get("api_key")
        base_url = conf.get("base_url", "https://api.openai.com/v1")
        model = conf.get("model", "gpt-3.5-turbo")
        max_tokens = conf.get("max_tokens", 8000)
        temperature = conf.get("temperature", 0.2)
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다")
        url = f"{base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        timeout = conf.get("timeout", 120)
        r = requests.post(url, headers=headers, json=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]

    def _call_gemini_generate(self, prompt: str, conf: Dict[str, Any]) -> str:
        """Google Gemini GenerateContent 호출 (v1beta REST) with streaming support."""
        import requests
        import logging
        import json
        logger = logging.getLogger(__name__)
        api_key = conf.get("api_key")
        base_url = conf.get("base_url", "https://generativelanguage.googleapis.com")
        model = conf.get("model", "models/gemini-1.5-pro")
        max_tokens = conf.get("max_tokens", 8000)
        temperature = conf.get("temperature", 0.2)
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY가 설정되지 않았습니다")

        # 스트림 활성화
        url = f"{base_url}/v1beta/{model}:streamGenerateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }

        response_mime_type = conf.get("response_mime_type")
        if response_mime_type:
            payload["generationConfig"]["responseMimeType"] = response_mime_type

        timeout = conf.get("timeout", 120)

        # 스트림 vs 비스트림 자동 선택
        try:
            # 먼저 스트림 시도
            logger.info(f"📡 Gemini 스트림 요청 시작 - 모델: {model}")
            stream_url = f"{base_url}/v1beta/{model}:streamGenerateContent?key={api_key}&alt=sse"

            headers = {
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream'
            }

            collected_response = []
            chunk_count = 0

            with requests.post(stream_url, json=payload, headers=headers, timeout=timeout, stream=True) as r:
                if r.status_code != 200:
                    error_text = r.text if hasattr(r, 'text') else "응답 본문 없음"
                    logger.error(f"❌ 스트림 요청 실패 ({r.status_code}): {error_text[:500]}")
                    logger.warning(f"⚠️ 스트림 요청 실패 ({r.status_code}), 폴백 시도...")
                    return self._call_gemini_generate_fallback(prompt, conf)

                for line in r.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        logger.debug(f"🔍 스트림 라인: {line_str}")

                        # SSE 데이터 파싱
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]  # 'data: ' 제거

                            if data_str.strip() == '[DONE]':
                                logger.info("🏁 Gemini Stream 완료")
                                break

                            try:
                                chunk_data = json.loads(data_str)
                                candidates = chunk_data.get('candidates', [])
                                if candidates:
                                    content = candidates[0].get('content', {})
                                    parts = content.get('parts', [])
                                    for part in parts:
                                        if 'text' in part:
                                            chunk_text = part['text']
                                            collected_response.append(chunk_text)
                                            chunk_count += 1

                                            # 중간 로깅 (10개 청크마다)
                                            if chunk_count % 10 == 0:
                                                total_text = ''.join(collected_response)
                                                logger.info(f"📝 Gemini Stream 진행 중: {chunk_count}개 청크, {len(total_text)}자 수신")
                                                logger.debug(f"현재까지 내용 미리보기: {total_text[:200]}...")

                            except json.JSONDecodeError as e:
                                logger.warning(f"⚠️ 스트림 청크 파싱 실패: {e}")
                                continue

            final_response = ''.join(collected_response)

            if final_response:
                logger.info(f"✅ Gemini 스트림 완료: {chunk_count}개 청크, 총 {len(final_response)}자")
                return final_response
            else:
                logger.warning("⚠️ 스트림에서 빈 응답, 폴백 시도...")
                return self._call_gemini_generate_fallback(prompt, conf)

        except Exception as e:
            logger.error(f"❌ Gemini 스트림 처리 실패: {e}")
            logger.info("🔄 기본 생성 방식으로 폴백...")
            return self._call_gemini_generate_fallback(prompt, conf)

    def _call_gemini_generate_fallback(self, prompt: str, conf: Dict[str, Any]) -> str:
        """Gemini 기본 생성 방식 (스트림 없음)"""
        import requests
        import logging
        logger = logging.getLogger(__name__)

        api_key = conf.get("api_key")
        base_url = conf.get("base_url", "https://generativelanguage.googleapis.com")
        model = conf.get("model", "models/gemini-1.5-pro")
        max_tokens = conf.get("max_tokens", 8000)
        temperature = conf.get("temperature", 0.2)

        logger.info(f"📡 Gemini 폴백 요청 시작 - 모델: {model}")

        # 기본 생성 엔드포인트
        url = f"{base_url}/v1beta/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }

        response_mime_type = conf.get("response_mime_type")
        if response_mime_type:
            payload["generationConfig"]["responseMimeType"] = response_mime_type

        timeout = conf.get("timeout", 120)
        try:
            r = requests.post(url, json=payload, timeout=timeout)
            logger.info(f"📊 폴백 응답 상태: {r.status_code}")

            if r.status_code != 200:
                error_text = r.text[:500] if r.text else "응답 본문 없음"
                logger.error(f"❌ 폴백 요청 실패 ({r.status_code}): {error_text}")
                return ""

            r.raise_for_status()
            data = r.json()
            logger.debug(f"📥 폴백 응답 데이터: {str(data)[:300]}...")

            candidates = data.get("candidates", [])
            if not candidates:
                logger.warning("⚠️ 폴백 응답에 candidates 없음")
                logger.debug(f"전체 응답: {data}")
                return ""

            parts = candidates[0].get("content", {}).get("parts", [])
            result = "\n".join(part.get("text", "") for part in parts if isinstance(part, dict))

            logger.info(f"✅ Gemini 폴백 완료 - {len(result)}자")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 폴백 요청 예외: {e}")
            return ""
        except Exception as e:
            logger.error(f"❌ 폴백 처리 예외: {e}")
            return ""
    
    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """LLM 응답에서 JSON 부분을 추출 (문서 구조 분석에 특화)"""
        import json
        import re
        import logging

        logger = logging.getLogger(__name__)

        logger.info(f"🔍 JSON 추출 시작 - 응답 길이: {len(response)}자")
        logger.info(f"🔍 응답 시작부 (200자): {response[:200]!r}")
        logger.info(f"🔍 응답 끝부 (200자): {response[-200:]!r}")

        # 1. JSON 코드 블록 추출 (우선순위)
        json_text = None

        # 방법 1: ```json ... ``` 블록 (강화된 패턴)
        json_patterns = [
            r'```json\s*(.*?)\s*```',           # 기본 json 블록
            r'```JSON\s*(.*?)\s*```',           # 대문자 JSON
            r'```\s*json\s*(.*?)\s*```',        # json 앞에 공백
            r'```\s*{.*?}\s*```',               # 중괄호로 시작하는 블록
        ]

        for pattern in json_patterns:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                json_text = match.group(1).strip()
                logger.debug(f"📝 JSON 코드 블록에서 추출 (패턴: {pattern[:20]}...)")
                break

        # 방법 2: ``` ... ``` 일반 블록
        if not json_text and "```" in response:
            pattern = r'```\s*(.*?)\s*```'
            match = re.search(pattern, response, re.DOTALL)
            if match:
                candidate = match.group(1).strip()
                # JSON 같은 내용인지 확인
                if candidate.startswith('{') and candidate.endswith('}'):
                    json_text = candidate
                    logger.debug("📝 일반 코드 블록에서 추출")

        # 방법 3: 중괄호 매칭 (복잡한 JSON 구조 지원)
        if not json_text:
            # documentInfo나 structureAnalysis 키를 찾아서 시작점 결정
            start_patterns = [
                r'\{\s*"documentInfo"',
                r'\{\s*"structureAnalysis"',
                r'\{\s*"coreContent"',
                r'\{\s*"metaInfo"'
            ]

            start_pos = -1
            needs_opening_brace = False

            for pattern in start_patterns:
                match = re.search(pattern, response)
                if match:
                    start_pos = match.start()
                    break

            # 중괄호가 없는 경우 주요 필드를 찾아서 시작점 결정
            if start_pos == -1:
                field_patterns = [
                    r'"documentInfo"',
                    r'"structureAnalysis"',
                    r'"coreContent"',
                    r'"metaInfo"'
                ]
                for pattern in field_patterns:
                    match = re.search(pattern, response)
                    if match:
                        # 필드 앞에서 개행/공백을 찾아 그 지점을 시작점으로 설정
                        field_start = match.start()
                        # 필드 앞의 공백/개행을 찾아서 시작점 설정
                        line_start = response.rfind('\n', 0, field_start)
                        if line_start != -1:
                            # 개행 후 공백을 무시하고 시작점 설정
                            while line_start + 1 < len(response) and response[line_start + 1] in ' \t':
                                line_start += 1
                            start_pos = line_start + 1
                        else:
                            start_pos = field_start
                        needs_opening_brace = True
                        logger.info(f"🔧 중괄호 없는 JSON 감지: '{pattern}' 필드부터 시작, start_pos={start_pos}")
                        break

            if start_pos == -1:
                # 첫 번째 { 찾기
                start_pos = response.find('{')

            if start_pos != -1:
                # 중괄호 균형 맞추기로 끝점 찾기
                # needs_opening_brace가 True면 시작 중괄호가 없으므로 카운트를 1로 시작
                brace_count = 1 if needs_opening_brace else 0
                end_pos = -1
                in_string = False
                escape_next = False

                for i in range(start_pos, len(response)):
                    char = response[i]

                    if escape_next:
                        escape_next = False
                        continue

                    if char == '\\':
                        escape_next = True
                        continue

                    if char == '"' and not escape_next:
                        in_string = not in_string
                        continue

                    if not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_pos = i + 1
                                break

                if end_pos > start_pos:
                    json_text = response[start_pos:end_pos]
                    # 중괄호가 누락된 경우 추가
                    if needs_opening_brace and not json_text.strip().startswith('{'):
                        json_text = '{' + json_text
                        logger.info(f"🔧 누락된 시작 중괄호 추가: {json_text[:100]}...")
                    logger.debug("📝 중괄호 매칭으로 추출")
                else:
                    # 닫는 중괄호를 찾지 못했지만 주요 필드에서 시작한 경우
                    # 남은 텍스트를 사용하고 누락된 중괄호를 보정
                    if needs_opening_brace:
                        candidate = response[start_pos:].strip()
                        if not candidate.startswith('{'):
                            candidate = '{' + candidate
                            logger.info("🔧 누락된 시작 중괄호 보정 추가")
                        # 괄호 균형 맞추기
                        open_braces = candidate.count('{')
                        close_braces = candidate.count('}')
                        if close_braces < open_braces:
                            candidate = candidate + ('}' * (open_braces - close_braces))
                            logger.info(f"🔧 누락된 닫는 중괄호 {open_braces - close_braces}개 추가")
                        json_text = candidate
                        logger.debug("📝 중괄호 종결 보정으로 추출")

        # 방법 4: 최후의 수단 - 전체 텍스트
        if not json_text:
            json_text = response.strip()
            logger.debug("📝 전체 응답 사용")

        # JSON 추출 결과 로깅
        if json_text:
            logger.debug(f"📝 JSON 추출 성공 - 길이: {len(json_text)}자, 방법: {'코드블록' if '```' in response else '중괄호매칭' if json_text != response.strip() else '전체응답'}")
            logger.debug(f"📝 추출된 JSON 시작: {json_text[:200]}")
        else:
            logger.error("❌ JSON 추출 실패 - 모든 방법으로 JSON을 찾을 수 없음")
            logger.debug(f"📝 원본 응답 시작 200자: {response[:200]}")
            logger.debug(f"📝 원본 응답 끝 200자: {response[-200:]}")
            return None

        # JSON 정리
        if json_text:
            # 앞뒤 불필요한 텍스트 제거
            json_text = json_text.strip()

            # 마크다운 코드펜스 제거 (혹시 남아있을 경우)
            json_text = re.sub(r'^```json\s*', '', json_text, flags=re.IGNORECASE)
            json_text = re.sub(r'^```JSON\s*', '', json_text, flags=re.IGNORECASE)
            json_text = re.sub(r'\s*```$', '', json_text)
            json_text = re.sub(r'^```\s*', '', json_text)

            # 문서 시작/끝의 BOM 및 개행 제어 문자 정규화
            if json_text.startswith('\ufeff'):
                json_text = json_text.lstrip('\ufeff')
            json_text = json_text.replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')

            # Gemini 특화: 설명 텍스트 제거는
            # JSON이 '{'로 바로 시작하지 않을 때만 적용하여
            # 정상 JSON 내부 문자열을 잘못 잘라내지 않도록 함
            if not json_text.lstrip().startswith('{'):
                explanation_patterns = [
                    r'^[^{]*?(다음은|결과는|분석|구조|JSON)\s*:?\s*\n*\s*{',
                    r'^[^{]*?(Here is|The result|Analysis|Structure|JSON)\s*:?\s*\n*\s*{',
                    r'^.*?분석.*?결과.*?\n*\s*{',
                    r'^.*?구조.*?분석.*?\n*\s*{'
                ]

                for pattern in explanation_patterns:
                    match = re.search(pattern, json_text, re.IGNORECASE | re.DOTALL)
                    if match:
                        # 설명 부분을 제거하고 { 부터 시작
                        start_pos = match.end() - 1  # { 문자 포함
                        json_text = json_text[start_pos:]
                        logger.debug("📝 설명 텍스트 제거")
                        break

            # 불완전한 JSON 수정 시도
            if not json_text.endswith('}') and json_text.count('{') > json_text.count('}'):
                missing_braces = json_text.count('{') - json_text.count('}')
                json_text += '}' * missing_braces
                logger.debug(f"📝 누락된 중괄호 {missing_braces}개 추가")

        try:
            # 기본 JSON 파싱 시도
            logger.debug(f"📝 JSON 파싱 시도 - 길이: {len(json_text)}자")
            logger.info(f"🔍 파싱할 JSON 내용 (첫 200자): {json_text[:200]!r}")
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.error(f"❌ 기본 JSON 파싱 실패: {e}")
            logger.debug(f"📝 문제가 된 JSON 앞부분(500자): {json_text[:500]}")
            logger.debug(f"📝 문제가 된 JSON 뒷부분(500자): {json_text[-500:]}")

            try:
                # 대안 1: JSON5 라이브러리 시도 (더 관대한 파싱)
                try:
                    import json5
                    logger.debug("🔧 JSON5 파싱 시도")
                    result = json5.loads(json_text)
                    logger.debug("✅ JSON5 파싱 성공")
                    return result
                except ImportError:
                    logger.debug("⚠️ json5 라이브러리가 설치되지 않음")
                except Exception as e_json5:
                    logger.debug(f"❌ JSON5 파싱 실패: {e_json5}")

                # 대안 2: 강화된 자체 수정 시도
                try:
                    logger.debug("🔧 강화된 JSON 수정 시도")
                    fixed_json = self._aggressive_json_repair(json_text)
                    if fixed_json != json_text:
                        logger.debug("✅ JSON 구조 수정 완료")
                        result = json.loads(fixed_json)
                        logger.debug("✅ 수정된 JSON 파싱 성공")
                        return result
                except json.JSONDecodeError as e_aggressive:
                    logger.debug(f"❌ 강화된 수정도 실패: {e_aggressive}")
                except Exception as e_repair:
                    logger.debug(f"❌ JSON 수정 중 오류: {e_repair}")

                # 대안 3: 기존 수정 방식
                logger.debug("🔧 기존 JSON 수정 시도")
                cleaned_json = self._repair_json(json_text)
                logger.debug(f"📝 수정된 JSON 앞부분(300자): {cleaned_json[:300]}")
                return json.loads(cleaned_json)

            except json.JSONDecodeError as e2:
                logger.error(f"❌ 수정 후에도 JSON 파싱 실패: {e2}")
                logger.debug(f"📝 최종 실패한 JSON 앞부분(200자): {cleaned_json[:200] if 'cleaned_json' in locals() else 'N/A'}")
                return None
            except Exception as e3:
                logger.error(f"❌ JSON 수정 중 예외 발생: {e3}")
                return None
    
    def _repair_json(self, json_text: str) -> str:
        """JSON 수정 (문서 구조 분석에 특화)"""
        import re
        import logging

        logger = logging.getLogger(__name__)

        # 1. 기본적인 문자 수정
        # 스마트 인용부호를 ASCII로 변환
        json_text = json_text.replace(""", '"').replace(""", '"').replace("'", "'")
        json_text = json_text.replace("'", "'").replace("`", "'")

        # 2. 인용부호 수정
        # 단일 인용부호를 이중 인용부호로 변환 (키)
        json_text = re.sub(r"'([^']*)':", r'"\1":', json_text)
        # 단일 인용부호를 이중 인용부호로 변환 (값)
        json_text = re.sub(r":\s*'([^']*)'", r': "\1"', json_text)

        # 3. 배열 내 단일 인용부호 수정
        json_text = re.sub(r'\[\s*\'([^\']*)\'\s*\]', r'["\1"]', json_text)
        json_text = re.sub(r',\s*\'([^\']*)\'\s*(?=[,\]])', r', "\1"', json_text)

        # 4. 키-값 쌍에서 키가 인용부호 없이 있는 경우 수정
        json_text = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_text)

        # 5. 끝에 붙은 쉼표 제거
        json_text = re.sub(r",\s*([}\]])", r"\1", json_text)

        # 6. 줄바꿈/탭 문자 처리 (문자열 내부만 안전하게 치환)
        def _escape_in_strings(s: str) -> str:
            result = []
            in_string = False
            escape_next = False
            for ch in s:
                if escape_next:
                    result.append(ch)
                    escape_next = False
                    continue
                if ch == '\\':
                    result.append(ch)
                    escape_next = True
                    continue
                if ch == '"':
                    result.append(ch)
                    in_string = not in_string
                    continue
                if in_string:
                    if ch == '\n':
                        result.append('\\n')
                        continue
                    if ch == '\r':
                        result.append('\\r')
                        continue
                    if ch == '\t':
                        result.append('\\t')
                        continue
                result.append(ch)
            return ''.join(result)

        json_text = _escape_in_strings(json_text)

        # 7. 제어 문자 제거 및 치환 (강화)
        # Invalid control character 오류 해결
        def clean_control_chars(text: str) -> str:
            result = []
            in_string = False
            escape_next = False

            for ch in text:
                if escape_next:
                    result.append(ch)
                    escape_next = False
                    continue

                if ch == '\\':
                    result.append(ch)
                    escape_next = True
                    continue

                if ch == '"':
                    result.append(ch)
                    in_string = not in_string
                    continue

                # 제어 문자 처리
                if ord(ch) < 32:  # 제어 문자
                    if in_string:
                        # 문자열 내부의 제어 문자는 이스케이프
                        if ch == '\n':
                            result.append('\\n')
                        elif ch == '\r':
                            result.append('\\r')
                        elif ch == '\t':
                            result.append('\\t')
                        else:
                            # 기타 제어 문자는 제거
                            continue
                    else:
                        # 문자열 외부의 제어 문자는 공백으로 치환
                        if ch in '\n\r\t':
                            result.append(ch)  # 개행/탭은 유지
                        else:
                            result.append(' ')  # 기타 제어 문자는 공백으로
                else:
                    result.append(ch)

            return ''.join(result)

        json_text = clean_control_chars(json_text)

        # 8. Unterminated string 수정 - 고급 문자열 균형 검사
        def fix_unterminated_strings(text: str) -> str:
            lines = text.split('\n')
            fixed_lines = []

            for i, line in enumerate(lines):
                # 이스케이프되지 않은 따옴표 개수 계산
                quote_positions = []
                escape_next = False

                for j, ch in enumerate(line):
                    if escape_next:
                        escape_next = False
                        continue
                    if ch == '\\':
                        escape_next = True
                        continue
                    if ch == '"':
                        quote_positions.append(j)

                # 홀수개의 따옴표가 있으면 unterminated string
                if len(quote_positions) % 2 == 1:
                    # 마지막 따옴표 위치 찾기
                    last_quote_pos = quote_positions[-1]

                    # 줄 끝까지의 내용 확인
                    remaining = line[last_quote_pos + 1:].strip()

                    # 다음 줄이 새로운 키/값으로 시작하는지 확인
                    is_end_of_value = False
                    if i < len(lines) - 1:
                        next_line = lines[i + 1].strip()
                        # 다음 줄이 새로운 키, 배열 끝, 객체 끝으로 시작하면 문자열 종료
                        if (next_line.startswith('"') and ':' in next_line) or \
                           next_line.startswith('}') or next_line.startswith(']') or \
                           next_line.startswith(','):
                            is_end_of_value = True
                    else:
                        # 마지막 줄이면 종료
                        is_end_of_value = True

                    if is_end_of_value:
                        # 문자열 내용에 불완전한 부분이 있으면 제거하고 따옴표 추가
                        if remaining and not remaining.endswith((',', '}', ']')):
                            # 불완전한 끝부분 제거 (마지막 단어/문자 제거)
                            content = line[:last_quote_pos + 1]
                            if remaining:
                                # 마지막 완전한 단어까지만 유지
                                words = remaining.split()
                                if len(words) > 1:
                                    clean_content = ' '.join(words[:-1])
                                    content += clean_content
                            line = content + '"'
                        else:
                            line = line.rstrip() + '"'

                        logger.debug(f"📝 Unterminated string 수정: 줄 {i+1}")

                fixed_lines.append(line)

            return '\n'.join(fixed_lines)

        json_text = fix_unterminated_strings(json_text)

        # 8. Extra data 오류 해결 - JSON 뒤의 추가 데이터 제거
        # 첫 번째 완전한 JSON 객체만 추출
        brace_count = 0
        json_end = -1
        in_string = False
        escape_next = False

        for i, char in enumerate(json_text):
            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break

        if json_end > 0 and json_end < len(json_text):
            original_length = len(json_text)
            json_text = json_text[:json_end]
            logger.debug(f"📝 Extra data 제거: {original_length - len(json_text)}자 삭제")

        # 9. 빈 키워드/분류 배열 수정
        json_text = re.sub(r'"keywords"\s*:\s*\[\s*\]', '"keywords": []', json_text)
        json_text = re.sub(r'"classificationTags"\s*:\s*\[\s*\]', '"classificationTags": []', json_text)

        # 10. 불완전한 객체 수정
        # 키워드/분류 객체에 필수 필드가 없는 경우 기본값 추가
        def fix_keyword_objects(match):
            obj = match.group(1)
            if '"name"' not in obj:
                return match.group(0)  # name 필드가 없으면 그대로 둠
            if '"desc"' not in obj:
                obj = obj.rstrip('} ') + ', "desc": ""}'
            if '"readme"' not in obj:
                obj = obj.rstrip('} ') + ', "readme": ""}'
            return '{"' + obj

        json_text = re.sub(r'\{([^{}]*"name"[^{}]*)\}', fix_keyword_objects, json_text)

        # 11. 불완전한 JSON 마무리
        if json_text.count('{') > json_text.count('}'):
            missing_braces = json_text.count('{') - json_text.count('}')
            json_text += '}' * missing_braces
            logger.debug(f"📝 JSON 수정: 누락된 중괄호 {missing_braces}개 추가")

        if json_text.count('[') > json_text.count(']'):
            missing_brackets = json_text.count('[') - json_text.count(']')
            json_text += ']' * missing_brackets
            logger.debug(f"📝 JSON 수정: 누락된 대괄호 {missing_brackets}개 추가")

        return json_text.strip()

    def _aggressive_json_repair(self, json_text: str) -> str:
        """매우 적극적인 JSON 수정 (demjson 대체)"""
        import re
        import logging

        logger = logging.getLogger(__name__)
        original = json_text

        # 1. 인용부호 없는 키 수정 (JavaScript 스타일)
        json_text = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_text)

        # 2. 단일 인용부호를 이중 인용부호로 변환 (전체)
        json_text = re.sub(r"'([^'\\]*(\\.[^'\\]*)*)'", r'"\1"', json_text)

        # 3. 잘린 문자열 복구 시도 (개선된 버전)
        lines = json_text.split('\n')
        fixed_lines = []
        in_string = False
        escape_next = False

        for i, line in enumerate(lines):
            temp_in_string = in_string
            temp_escape_next = escape_next

            # 줄별로 문자열 상태 추적
            for char in line:
                if temp_escape_next:
                    temp_escape_next = False
                    continue
                if char == '\\':
                    temp_escape_next = True
                    continue
                if char == '"':
                    temp_in_string = not temp_in_string

            # 문자열이 열려있고 다음 조건 중 하나를 만족하면 닫기
            if temp_in_string:
                # 마지막 줄이거나
                # 다음 줄이 새로운 키로 시작하거나
                # 다음 줄이 닫는 괄호로 시작하면
                if (i == len(lines) - 1 or
                    (i < len(lines) - 1 and re.match(r'^\s*["}]', lines[i+1]))):
                    line = line.rstrip() + '"'
                    temp_in_string = False
                    logger.debug(f"📝 Unterminated string 수정: 줄 {i+1}")

            fixed_lines.append(line)
            in_string = temp_in_string
            escape_next = temp_escape_next

        json_text = '\n'.join(fixed_lines)

        # 4. 마지막 원소 뒤 쉼표 제거
        json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)

        # 5. 중복 쉼표 제거
        json_text = re.sub(r',\s*,', ',', json_text)

        # 6. JavaScript 주석 제거
        json_text = re.sub(r'//.*$', '', json_text, flags=re.MULTILINE)
        json_text = re.sub(r'/\*.*?\*/', '', json_text, flags=re.DOTALL)

        # 7. 불완전한 배열/객체 닫기
        open_braces = json_text.count('{') - json_text.count('}')
        open_brackets = json_text.count('[') - json_text.count(']')

        if open_braces > 0:
            json_text += '}' * open_braces
        if open_brackets > 0:
            json_text += ']' * open_brackets

        # 8. 연속된 공백 정리
        json_text = re.sub(r'\s+', ' ', json_text)
        json_text = json_text.strip()

        if json_text != original:
            logger.debug(f"📝 적극적 수정 완료: {len(original)}자 → {len(json_text)}자")

        return json_text

    def _fallback_structure_analysis(self, text: str, file_extension: str) -> Dict[str, Any]:
        """LLM이 비활성화된 경우 기본 구조 분석으로 폴백"""
        basic_structure = self.analyze_document_structure(text, file_extension)
        basic_structure.update({
            "analysis_method": "basic_only",
            "llm_success": False,
            "llm_error": "LLM extraction disabled"
        })
        return basic_structure
    
    def _fallback_structure_analysis_with_llm_attempt(self, text: str, file_extension: str, error_msg: str) -> Dict[str, Any]:
        """LLM 실패 시 실패 상태를 명시적으로 반환 (더 이상 결과 생성하지 않음)"""
        import logging
        logger = logging.getLogger(__name__)

        logger.error(f"❌ LLM 구조 분석 완전 실패: {error_msg}")

        # 실패 상태만 반환 (llm_analysis 없음)
        return {
            "analysis_method": "llm_failed",
            "llm_success": False,
            "llm_error": error_msg,
            "file_info": {},
            "analysis_timestamp": "",
            "source_parser": ""
            # llm_analysis는 의도적으로 누락 - 이로 인해 HTTPException 발생
        }
    
    def extract_keywords(self, content: str, extractors: Optional[List[str]] = None, filename: str = "local_analysis.txt") -> List[Dict[str, Any]]:
        """키워드 추출 수행"""
        if extractors is None:
            extractors = ConfigService.get_json_config(
                self.db, "DEFAULT_EXTRACTORS", ["llm"]
            )
        
        # ExtractorManager를 사용하여 키워드 추출
        keywords = self._ensure_extractor_manager().extract_keywords(content, extractors, filename)
        
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
    
    def analyze_file(self, file_path: str, extractors: Optional[List[str]] = None, force_reanalyze: bool = False, use_docling: bool = False) -> Dict[str, Any]:
        """파일 분석 수행
        
        Args:
            file_path: 분석할 파일 경로
            extractors: 사용할 추출기 목록
            force_reanalyze: 재분석 여부
            use_docling: Docling 파서 사용 여부 (PDF 파일에만 적용)
        """
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
            
            # DocumentParserService를 통해 기존 파싱 결과 확인
            from services.document_parser_service import DocumentParserService
            parser_service = DocumentParserService()
            
            content = None
            parsing_used = "new_parsing"
            
            # 기존 파싱 결과 확인
            if parser_service.has_parsing_results(absolute_path):
                try:
                    # 기존 파싱 결과에서 텍스트 추출
                    existing_results = parser_service.load_existing_parsing_results(absolute_path)
                    best_parser = existing_results.get("summary", {}).get("best_parser")
                    
                    if best_parser and best_parser in existing_results.get("parsing_results", {}):
                        parser_dir = parser_service.get_output_directory(absolute_path) / best_parser
                        text_file = parser_dir / f"{best_parser}_text.txt"
                        if text_file.exists():
                            with open(text_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                                parsing_used = f"existing_{best_parser}"
                                print(f"✅ 기존 파싱 결과 재사용: {best_parser} ({len(content)} 문자)")
                except Exception as e:
                    print(f"⚠️ 기존 파싱 결과 로드 실패, 새로 파싱: {e}")
            
            # 파싱 결과가 없거나 로드 실패 시 새로 파싱
            if not content:
                content = self.parse_file_content(file_path, use_docling=use_docling)
                parsing_used = "new_parsing"
            
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
                    "extractors_used": extractors if extractors is not None else ConfigService.get_json_config(
                        self.db, "DEFAULT_EXTRACTORS", ["llm"]
                    ),
                    "total_keywords": len(keywords),
                    "parsing_method": parsing_used
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
