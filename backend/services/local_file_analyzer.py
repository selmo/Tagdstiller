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
from utils.llm_logger import log_prompt_and_response
from services.parser_file_manager import save_parser_results, file_manager

from langchain_ollama import OllamaLLM
LANGCHAIN_AVAILABLE = True

class LocalFileAnalyzer:
    """로컬 파일 분석을 위한 서비스 클래스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.extractor_manager = ExtractorManager(db)
        
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
                    llm_metadata = self.extract_metadata_with_llm(text[:5000])
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
                    llm_metadata = self.extract_metadata_with_llm(parse_result.text[:5000])  # 처음 5000자만 사용
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
    
    def extract_metadata_with_llm(self, text: str) -> Optional[Dict[str, Any]]:
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
        # 텍스트 크기 제한 (타임아웃 방지를 위해 더 짧게)
        max_text_length = 800  # 1500 -> 800으로 감소
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
            
            # 프롬프트/응답 파일 저장
            log_prompt_and_response(
                label="local_metadata_langchain",
                provider="ollama",
                model=model_name,
                prompt=prompt,
                response=response_text,
                logger=logger,
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
                log_prompt_and_response(
                    label="local_metadata_langchain_error",
                    provider="ollama",
                    model=model_name,
                    prompt=prompt,
                    response="",
                    logger=logger,
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

{text[:1500]}

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
            
            # 프롬프트/응답 로깅
            log_prompt_and_response(
                label="local_metadata_langchain",
                provider="ollama",
                model=model_name,
                prompt=prompt,
                response=response,
                logger=logger,
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
            
            # 파일 내용 파싱 (use_docling 옵션 전달)
            content = self.parse_file_content(file_path, use_docling=use_docling)
            
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
                        self.db, "DEFAULT_EXTRACTORS", ["keybert", "ner", "konlpy", "metadata"]
                    ),
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
