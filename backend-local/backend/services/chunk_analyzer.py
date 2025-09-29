"""
청크별 분석 및 결과 통합 서비스

구조 기반으로 분할된 문서 청크를 개별 분석하고,
분석 결과를 계층적으로 병합하여 전체 문서 수준의 분석 결과를 생성합니다.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from sqlalchemy.orm import Session

from services.document_chunker import DocumentChunker, DocumentNode, ChunkInfo
from services.local_file_analyzer import LocalFileAnalyzer
from services.document_parser_service import DocumentParserService
from services.chunk_prompt_manager import ChunkPromptManager, ChunkPromptRequest, ChunkPromptResult
from prompts.templates import (
    DocumentSummaryPrompts,
    KeywordExtractionPrompts,
    DocumentStructurePrompts,
    KnowledgeGraphPrompts,
    get_prompt_template
)


@dataclass
class ChunkAnalysisResult:
    """청크 분석 결과를 담는 데이터 클래스"""
    chunk_id: str
    level: str  # "document", "chapter", "section", "subsection"
    content_length: int

    # 키워드 추출 결과
    keywords: List[Dict[str, Any]]

    # 문서 요약 결과
    summary: Dict[str, Any]

    # 구조 분석 결과 (LLM 기반)
    structure_analysis: Optional[Dict[str, Any]]

    # 지식 그래프 데이터
    knowledge_graph: Optional[Dict[str, Any]]

    # 메타데이터
    analysis_metadata: Dict[str, Any]


@dataclass
class IntegratedAnalysisResult:
    """통합 분석 결과를 담는 데이터 클래스"""
    total_chunks: int
    total_content_length: int

    # 계층적 키워드 (청크별 키워드를 중요도 기준으로 통합)
    integrated_keywords: List[Dict[str, Any]]

    # 계층적 요약 (청크별 요약을 통합하여 전체 요약 생성)
    hierarchical_summary: Dict[str, Any]

    # 통합 구조 분석
    integrated_structure: Dict[str, Any]

    # 통합 지식 그래프
    merged_knowledge_graph: Optional[Dict[str, Any]]

    # 청크별 상세 결과
    chunk_results: List[ChunkAnalysisResult]

    # 통합 메타데이터
    integration_metadata: Dict[str, Any]


class ChunkAnalyzer:
    """청크별 분석 및 결과 통합을 담당하는 서비스"""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.document_chunker = DocumentChunker()
        self.local_analyzer = LocalFileAnalyzer(db)
        self.prompt_manager = None  # 나중에 초기화

    def analyze_document_with_chunking(
        self,
        file_path: str,
        output_directory: str = None,
        max_chunk_size: int = 50000,
        use_llm: bool = True,
        extractors: List[str] = None,
        analysis_types: List[str] = None
    ) -> IntegratedAnalysisResult:
        """
        문서를 청킹하여 분석하고 결과를 통합합니다.

        Args:
            file_path: 분석할 파일 경로
            output_directory: 결과 저장 디렉토리 (선택)
            max_chunk_size: 최대 청크 크기 (기본 50,000자)
            use_llm: LLM 분석 사용 여부
            extractors: 사용할 키워드 추출기 리스트
            analysis_types: 수행할 분석 유형 리스트

        Returns:
            IntegratedAnalysisResult: 통합 분석 결과
        """
        self.logger.info(f"🔍 청크 기반 문서 분석 시작: {file_path}")

        # 기본값 설정
        extractors = extractors or ["KeyBERT", "spaCy NER", "LLM"]
        analysis_types = analysis_types or ["keywords", "summary", "structure", "knowledge_graph"]

        start_time = datetime.now()

        try:
            # 파일 경로 및 출력 디렉토리 설정
            file_path_obj = Path(file_path)
            final_output_dir = output_directory or str(file_path_obj.parent)

            # 프롬프트 매니저 초기화
            self.prompt_manager = ChunkPromptManager(final_output_dir)
            self.logger.info(f"🎯 프롬프트 매니저 초기화 완료: {final_output_dir}")

            # 1단계: 파일 파싱 (PDF 등 바이너리 파일 처리)
            self.logger.info("📄 1단계: 파일 파싱")

            # PDF 파일이나 기타 바이너리 파일의 경우 먼저 파싱
            if file_path_obj.suffix.lower() in ['.pdf', '.docx', '.doc', '.hwp']:
                self.logger.info(f"📋 바이너리 파일 파싱 시작: {file_path_obj.suffix}")
                parser_service = DocumentParserService()

                # 출력 디렉토리 설정
                output_dir_path = Path(final_output_dir)

                # 기존 파싱 결과가 있는지 확인
                if parser_service.has_parsing_results(file_path_obj, output_dir_path):
                    self.logger.info("♻️ 기존 파싱 결과 사용")
                    parsing_results = parser_service.load_existing_parsing_results(file_path_obj, output_dir_path)
                else:
                    self.logger.info("🔄 새로운 파싱 수행")
                    parsing_results = parser_service.parse_document_comprehensive(
                        file_path=file_path_obj,
                        force_reparse=False,
                        directory=output_dir_path
                    )

                # 최고 품질 파서의 텍스트 추출
                best_parser = parsing_results.get("summary", {}).get("best_parser")
                if not best_parser:
                    raise ValueError("파싱 결과에서 최적 파서를 찾을 수 없습니다")

                # 텍스트 파일 읽기
                parsing_output_dir = parser_service.get_output_directory(file_path_obj, output_dir_path)
                text_file = parsing_output_dir / best_parser / f"{best_parser}_text.txt"

                if not text_file.exists():
                    raise FileNotFoundError(f"파싱된 텍스트 파일을 찾을 수 없습니다: {text_file}")

                document_text = text_file.read_text(encoding='utf-8')
                self.logger.info(f"✅ 파싱 완료: {len(document_text):,}자 추출됨")

                # 텍스트를 임시 파일로 저장하여 청킹에 사용 (지정된 출력 디렉토리에)
                temp_text_file = output_dir_path / "parsed_document.txt"
                output_dir_path.mkdir(parents=True, exist_ok=True)
                temp_text_file.write_text(document_text, encoding='utf-8')
                text_file_for_chunking = str(temp_text_file)
            else:
                # 텍스트 파일은 그대로 사용
                text_file_for_chunking = file_path

            # 2단계: 문서 구조 분석 및 청킹
            self.logger.info("🔍 2단계: 문서 구조 분석 및 청킹")

            chunk_info = self.document_chunker.chunk_document(
                file_path=text_file_for_chunking,
                max_chunk_size=max_chunk_size,
                output_directory=final_output_dir
            )

            if not chunk_info.chunks:
                raise ValueError("문서 청킹 결과가 없습니다.")

            self.logger.info(f"✅ 청킹 완료: {len(chunk_info.chunks)}개 청크 생성")

            # 청크 텍스트 파일들이 생성되었는지 확인 (디버그)
            chunks_text_dir = Path(final_output_dir) / "chunks_text"
            if chunks_text_dir.exists():
                txt_files = list(chunks_text_dir.glob("*.txt"))
                self.logger.info(f"📁 청크 텍스트 파일 {len(txt_files)}개 발견: {[f.name for f in txt_files]}")
            else:
                self.logger.warning(f"⚠️ 청크 텍스트 디렉토리가 없습니다: {chunks_text_dir}")

            # 3단계: 각 청크별 분석 수행
            self.logger.info("🔬 3단계: 청크별 분석 수행")
            chunk_results = []

            for i, chunk in enumerate(chunk_info.chunks, 1):
                self.logger.info(f"📋 청크 {i}/{len(chunk_info.chunks)} 분석 중: {chunk['chunk_id']}")

                # 청크 데이터 구조 디버그 로그
                self.logger.info(f"🔍 청크 데이터 키들: {list(chunk.keys())}")
                content_preview_len = len(chunk.get('content_preview', ''))
                self.logger.info(f"📄 content_preview 길이: {content_preview_len}")

                # 청크별 프롬프트 생성 및 저장
                if self.prompt_manager:
                    try:
                        # 청크 텍스트 파일에서 전체 콘텐츠 읽기
                        chunk_text_file = Path(final_output_dir) / "chunks_text" / f"{chunk['chunk_id']}.txt"
                        if chunk_text_file.exists():
                            full_content = chunk_text_file.read_text(encoding='utf-8')
                            # 헤더 부분 제거 (실제 콘텐츠만 추출)
                            content_lines = full_content.split('\n')
                            content_start_idx = 0
                            for i, line in enumerate(content_lines):
                                if line.startswith('---') or line.startswith('Content:'):
                                    content_start_idx = i + 1
                                    break
                            actual_content = '\n'.join(content_lines[content_start_idx:]).strip()

                            # 청크 정보에 전체 콘텐츠 추가
                            chunk_with_content = chunk.copy()
                            chunk_with_content['full_content'] = actual_content

                            self.logger.info(f"📄 {chunk['chunk_id']} 전체 콘텐츠 로드: {len(actual_content)}자")
                            self._generate_chunk_prompts(chunk_with_content, file_path, analysis_types)
                        else:
                            self.logger.warning(f"⚠️ {chunk['chunk_id']} 텍스트 파일이 없어서 기본 방식 사용")
                            self._generate_chunk_prompts(chunk, file_path, analysis_types)

                        self.logger.info(f"✅ {chunk['chunk_id']} 프롬프트 생성 완료")
                    except Exception as e:
                        self.logger.error(f"❌ {chunk['chunk_id']} 프롬프트 생성 실패: {str(e)}")
                        import traceback
                        self.logger.error(f"프롬프트 생성 오류 상세: {traceback.format_exc()}")

                chunk_result = self._analyze_chunk(
                    chunk=chunk,
                    file_path=file_path,
                    extractors=extractors,
                    analysis_types=analysis_types,
                    use_llm=use_llm
                )
                chunk_results.append(chunk_result)

                # 청크별 분석 보고서 생성
                if self.prompt_manager:
                    self._generate_chunk_analysis_report(chunk_result)

                self.logger.info(f"✅ 청크 {i} 분석 완료")

            # 3단계: 분석 결과 통합
            self.logger.info("🔗 3단계: 분석 결과 통합")
            integrated_result = self._integrate_analysis_results(
                chunk_results=chunk_results,
                original_document_info=chunk_info,
                total_content_length=sum(chunk['content_length'] for chunk in chunk_info.chunks)
            )

            # 4단계: 결과 저장
            if output_directory:
                self._save_integrated_results(
                    integrated_result=integrated_result,
                    output_directory=output_directory,
                    file_path=file_path
                )

            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            self.logger.info(f"🎉 청크 기반 분석 완료 (소요시간: {processing_time:.2f}초)")

            # 메타데이터 업데이트
            integrated_result.integration_metadata.update({
                "processing_time_seconds": processing_time,
                "analysis_completion_time": end_time.isoformat(),
                "chunks_analyzed": len(chunk_results),
                "total_content_length": integrated_result.total_content_length
            })

            return integrated_result

        except Exception as e:
            self.logger.error(f"❌ 청크 기반 분석 실패: {str(e)}")
            raise

    def _analyze_chunk(
        self,
        chunk: Dict[str, Any],
        file_path: str,
        extractors: List[str],
        analysis_types: List[str],
        use_llm: bool
    ) -> ChunkAnalysisResult:
        """개별 청크를 분석합니다."""

        chunk_content = chunk.get('content_preview', '')
        chunk_id = chunk['chunk_id']
        level = chunk['level']
        content_length = chunk['content_length']

        analysis_results = {
            'keywords': [],
            'summary': {},
            'structure_analysis': None,
            'knowledge_graph': None
        }

        # 키워드 추출 분석
        if "keywords" in analysis_types:
            self.logger.debug(f"🔑 키워드 추출: {chunk_id}")
            analysis_results['keywords'] = self._extract_keywords_from_chunk(
                content=chunk_content,
                extractors=extractors,
                use_llm=use_llm
            )

        # 문서 요약 분석
        if "summary" in analysis_types:
            self.logger.debug(f"📝 요약 생성: {chunk_id}")
            analysis_results['summary'] = self._summarize_chunk(
                content=chunk_content,
                chunk_level=level,
                use_llm=use_llm
            )

        # 구조 분석 (기본 분석으로 대체)
        if "structure" in analysis_types:
            self.logger.debug(f"🏗️ 구조 분석: {chunk_id}")
            analysis_results['structure_analysis'] = self._analyze_chunk_structure_basic(
                content=chunk_content,
                chunk_info=chunk
            )

        # 지식 그래프 생성 (기본 분석으로 대체)
        if "knowledge_graph" in analysis_types:
            self.logger.debug(f"🕸️ 지식 그래프 생성: {chunk_id}")
            analysis_results['knowledge_graph'] = self._extract_knowledge_graph_basic(
                content=chunk_content,
                chunk_info=chunk
            )

        return ChunkAnalysisResult(
            chunk_id=chunk_id,
            level=level,
            content_length=content_length,
            keywords=analysis_results['keywords'],
            summary=analysis_results['summary'],
            structure_analysis=analysis_results['structure_analysis'],
            knowledge_graph=analysis_results['knowledge_graph'],
            analysis_metadata={
                'file_path': file_path,
                'chunk_info': chunk,
                'analysis_timestamp': datetime.now().isoformat(),
                'extractors_used': extractors,
                'analysis_types': analysis_types
            }
        )

    def _extract_keywords_from_chunk(
        self,
        content: str,
        extractors: List[str],
        use_llm: bool
    ) -> List[Dict[str, Any]]:
        """청크에서 키워드를 추출합니다."""

        keywords = []

        # LLM 기반 키워드 추출 (간단한 텍스트 기반 키워드 추출로 대체)
        if "LLM" in extractors and use_llm:
            try:
                # 간단한 키워드 추출 (실제 LLM 대신 기본 알고리즘 사용)
                simple_keywords = self._extract_simple_keywords(content)
                for i, keyword in enumerate(simple_keywords):
                    keywords.append({
                        'keyword': keyword,
                        'score': 0.8 - (i * 0.1),  # 순서별로 점수 감소
                        'category': 'noun',
                        'extractor': 'LLM_mock',
                        'chunk_source': True
                    })

            except Exception as e:
                self.logger.warning(f"⚠️ LLM 키워드 추출 실패: {str(e)}")

        # 다른 추출기들은 향후 확장 가능
        # KeyBERT, spaCy NER 등의 구현은 기존 시스템과 연동

        return keywords

    def _extract_simple_keywords(self, content: str) -> List[str]:
        """간단한 키워드 추출 (테스트용)"""
        import re

        # 간단한 정규식 기반 키워드 추출
        words = re.findall(r'\b[가-힣]{2,}|\b[a-zA-Z]{3,}\b', content)

        # 빈도 계산
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1

        # 빈도순 정렬 후 상위 10개 반환
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:10]]

    def _summarize_chunk(
        self,
        content: str,
        chunk_level: str,
        use_llm: bool
    ) -> Dict[str, Any]:
        """청크 내용을 요약합니다."""

        # 기본 요약 생성
        lines = content.split('\n')
        non_empty_lines = [line.strip() for line in lines if line.strip()]

        # 간단한 요약 정보 추출
        intro = non_empty_lines[0] if non_empty_lines else "내용 없음"
        conclusion = non_empty_lines[-1] if len(non_empty_lines) > 1 else intro

        # 간단한 주제 추출 (키워드 기반)
        keywords = self._extract_simple_keywords(content)
        topics = keywords[:5]  # 상위 5개 키워드를 주제로 사용

        return {
            'summary_type': 'basic_generated',
            'level': chunk_level,
            'intro': intro[:100] + "..." if len(intro) > 100 else intro,
            'conclusion': conclusion[:100] + "..." if len(conclusion) > 100 else conclusion,
            'core': f"{chunk_level} 수준의 내용으로 {len(content)}자의 텍스트를 포함합니다.",
            'topics': topics,
            'tone': 'informational',
            'content_length': len(content),
            'line_count': len(non_empty_lines)
        }

    def _analyze_chunk_structure_basic(
        self,
        content: str,
        chunk_info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """청크의 기본 구조를 분석합니다."""

        try:
            lines = content.split('\n')
            headers = []
            lists = []

            for line in lines:
                line = line.strip()
                if line.startswith('#'):
                    headers.append(line)
                elif line.startswith('-') or line.startswith('*') or line.startswith('•'):
                    lists.append(line)

            return {
                'analysis_method': 'basic_structure',
                'total_lines': len(lines),
                'headers_count': len(headers),
                'lists_count': len(lists),
                'headers': headers[:5],  # 상위 5개 헤더
                'structure_features': {
                    'has_titles': len(headers) > 0,
                    'has_lists': len(lists) > 0,
                    'has_paragraphs': len([l for l in lines if len(l.strip()) > 50]) > 0
                },
                'chunk_info': chunk_info
            }

        except Exception as e:
            self.logger.warning(f"⚠️ 청크 구조 분석 실패: {str(e)}")

        return None

    def _extract_knowledge_graph_basic(
        self,
        content: str,
        chunk_info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """청크에서 기본 지식 그래프를 추출합니다."""

        try:
            # 간단한 엔티티 추출 (키워드 기반)
            keywords = self._extract_simple_keywords(content)

            entities = []
            relationships = []

            # 키워드를 엔티티로 변환
            for i, keyword in enumerate(keywords[:5]):  # 상위 5개만
                entities.append({
                    'id': f'entity_{i}',
                    'type': 'Concept',
                    'properties': {
                        'name': keyword,
                        'source_chunk': chunk_info.get('chunk_id', 'unknown')
                    }
                })

            # 간단한 관계 생성 (인접한 엔티티들 간의 관계)
            for i in range(len(entities) - 1):
                relationships.append({
                    'source': entities[i]['id'],
                    'target': entities[i + 1]['id'],
                    'type': 'RELATED_TO',
                    'properties': {
                        'relationship_name': 'CO_OCCURS',
                        'context': 'same_chunk'
                    }
                })

            return {
                'extraction_method': 'basic_kg',
                'entities': entities,
                'relationships': relationships,
                'source_chunk': chunk_info.get('chunk_id', 'unknown'),
                'entity_count': len(entities),
                'relationship_count': len(relationships)
            }

        except Exception as e:
            self.logger.warning(f"⚠️ 청크 지식 그래프 추출 실패: {str(e)}")

        return None

    def _integrate_analysis_results(
        self,
        chunk_results: List[ChunkAnalysisResult],
        original_document_info: Any,
        total_content_length: int
    ) -> IntegratedAnalysisResult:
        """청크별 분석 결과를 통합합니다."""

        self.logger.info("🔗 분석 결과 통합 시작")

        # 키워드 통합 (중복 제거 및 중요도 기준 정렬)
        integrated_keywords = self._integrate_keywords(chunk_results)

        # 계층적 요약 생성
        hierarchical_summary = self._create_hierarchical_summary(chunk_results)

        # 구조 정보 통합
        integrated_structure = self._integrate_structure_info(chunk_results, original_document_info)

        # 지식 그래프 병합
        merged_kg = self._merge_knowledge_graphs(chunk_results)

        # 통합 메타데이터 생성
        integration_metadata = {
            'integration_timestamp': datetime.now().isoformat(),
            'total_chunks_processed': len(chunk_results),
            'integration_method': 'hierarchical_merge',
            'content_distribution': {
                result.level: result.content_length
                for result in chunk_results
            }
        }

        return IntegratedAnalysisResult(
            total_chunks=len(chunk_results),
            total_content_length=total_content_length,
            integrated_keywords=integrated_keywords,
            hierarchical_summary=hierarchical_summary,
            integrated_structure=integrated_structure,
            merged_knowledge_graph=merged_kg,
            chunk_results=chunk_results,
            integration_metadata=integration_metadata
        )

    def _integrate_keywords(self, chunk_results: List[ChunkAnalysisResult]) -> List[Dict[str, Any]]:
        """청크별 키워드를 통합하고 중복을 제거합니다."""

        keyword_map = {}

        for chunk_result in chunk_results:
            for keyword_data in chunk_result.keywords:
                keyword_text = keyword_data.get('keyword', '').lower()
                if not keyword_text:
                    continue

                if keyword_text in keyword_map:
                    # 기존 키워드의 점수와 비교하여 더 높은 점수 유지
                    existing_score = keyword_map[keyword_text].get('score', 0)
                    new_score = keyword_data.get('score', 0)

                    if new_score > existing_score:
                        keyword_map[keyword_text] = {
                            **keyword_data,
                            'sources': keyword_map[keyword_text].get('sources', []) + [chunk_result.chunk_id],
                            'frequency': keyword_map[keyword_text].get('frequency', 1) + 1
                        }
                    else:
                        keyword_map[keyword_text]['sources'].append(chunk_result.chunk_id)
                        keyword_map[keyword_text]['frequency'] += 1
                else:
                    keyword_map[keyword_text] = {
                        **keyword_data,
                        'sources': [chunk_result.chunk_id],
                        'frequency': 1
                    }

        # 점수와 빈도를 고려하여 정렬
        integrated_keywords = sorted(
            keyword_map.values(),
            key=lambda x: (x.get('score', 0) * x.get('frequency', 1)),
            reverse=True
        )

        return integrated_keywords[:50]  # 상위 50개 키워드만 반환

    def _create_hierarchical_summary(self, chunk_results: List[ChunkAnalysisResult]) -> Dict[str, Any]:
        """청크별 요약을 계층적으로 통합합니다."""

        # 레벨별로 요약 그룹화
        summaries_by_level = {}
        for result in chunk_results:
            level = result.level
            if level not in summaries_by_level:
                summaries_by_level[level] = []
            summaries_by_level[level].append(result.summary)

        # 계층적 구조 생성
        hierarchical_summary = {
            'document_level': {
                'total_chunks': len(chunk_results),
                'content_overview': "전체 문서를 구조적으로 분석한 결과입니다."
            }
        }

        # 각 레벨별 요약 통합
        for level, summaries in summaries_by_level.items():
            level_summary = {
                'count': len(summaries),
                'summaries': summaries,
                'combined_topics': []
            }

            # 공통 주제 추출
            all_topics = []
            for summary in summaries:
                if isinstance(summary, dict) and 'topics' in summary:
                    all_topics.extend(summary['topics'])

            # 중복 제거 및 빈도 계산
            topic_frequency = {}
            for topic in all_topics:
                if isinstance(topic, str):
                    topic_frequency[topic] = topic_frequency.get(topic, 0) + 1

            # 빈도순 정렬
            level_summary['combined_topics'] = sorted(
                topic_frequency.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]  # 상위 10개 주제

            hierarchical_summary[f'{level}_level'] = level_summary

        return hierarchical_summary

    def _integrate_structure_info(
        self,
        chunk_results: List[ChunkAnalysisResult],
        original_document_info: Any
    ) -> Dict[str, Any]:
        """구조 정보를 통합합니다."""

        integrated_structure = {
            'document_structure': {
                'total_chunks': len(chunk_results),
                'chunking_info': getattr(original_document_info, '__dict__', {}),
                'chunk_hierarchy': []
            },
            'detailed_structures': {}
        }

        # 청크별 상세 구조 정보 수집
        for result in chunk_results:
            if result.structure_analysis:
                integrated_structure['detailed_structures'][result.chunk_id] = {
                    'level': result.level,
                    'content_length': result.content_length,
                    'structure_data': result.structure_analysis
                }

                # 계층 정보 추가
                integrated_structure['document_structure']['chunk_hierarchy'].append({
                    'chunk_id': result.chunk_id,
                    'level': result.level,
                    'content_length': result.content_length,
                    'has_structure_analysis': True
                })
            else:
                integrated_structure['document_structure']['chunk_hierarchy'].append({
                    'chunk_id': result.chunk_id,
                    'level': result.level,
                    'content_length': result.content_length,
                    'has_structure_analysis': False
                })

        return integrated_structure

    def _merge_knowledge_graphs(self, chunk_results: List[ChunkAnalysisResult]) -> Optional[Dict[str, Any]]:
        """청크별 지식 그래프를 병합합니다."""

        merged_entities = {}
        merged_relationships = []

        for result in chunk_results:
            if not result.knowledge_graph:
                continue

            kg = result.knowledge_graph

            # 엔티티 병합
            if 'entities' in kg:
                for entity in kg['entities']:
                    entity_id = entity.get('id')
                    if entity_id:
                        if entity_id in merged_entities:
                            # 기존 엔티티와 속성 병합
                            existing_props = merged_entities[entity_id].get('properties', {})
                            new_props = entity.get('properties', {})
                            merged_props = {**existing_props, **new_props}
                            merged_entities[entity_id]['properties'] = merged_props
                        else:
                            merged_entities[entity_id] = entity

            # 관계 병합
            if 'relationships' in kg:
                for rel in kg['relationships']:
                    # 중복 관계 체크
                    rel_signature = f"{rel.get('source')}->{rel.get('target')}:{rel.get('type')}"
                    if not any(
                        f"{r.get('source')}->{r.get('target')}:{r.get('type')}" == rel_signature
                        for r in merged_relationships
                    ):
                        merged_relationships.append(rel)

        if not merged_entities and not merged_relationships:
            return None

        return {
            'entities': list(merged_entities.values()),
            'relationships': merged_relationships,
            'merge_metadata': {
                'total_entities': len(merged_entities),
                'total_relationships': len(merged_relationships),
                'source_chunks': len([r for r in chunk_results if r.knowledge_graph])
            }
        }

    def _save_integrated_results(
        self,
        integrated_result: IntegratedAnalysisResult,
        output_directory: str,
        file_path: str
    ):
        """통합 분석 결과를 파일로 저장합니다."""

        output_path = Path(output_directory)
        output_path.mkdir(parents=True, exist_ok=True)

        # 통합 결과 저장
        integrated_file = output_path / "integrated_analysis_result.json"
        with open(integrated_file, 'w', encoding='utf-8') as f:
            # dataclass를 dict로 변환하여 저장
            result_dict = {
                'total_chunks': integrated_result.total_chunks,
                'total_content_length': integrated_result.total_content_length,
                'integrated_keywords': integrated_result.integrated_keywords,
                'hierarchical_summary': integrated_result.hierarchical_summary,
                'integrated_structure': integrated_result.integrated_structure,
                'merged_knowledge_graph': integrated_result.merged_knowledge_graph,
                'integration_metadata': integrated_result.integration_metadata,
                'chunk_results_count': len(integrated_result.chunk_results)
            }
            json.dump(result_dict, f, ensure_ascii=False, indent=2)

        # 청크별 상세 결과 저장
        chunks_detail_file = output_path / "chunks_detailed_results.json"
        chunks_data = []
        for chunk_result in integrated_result.chunk_results:
            chunk_data = {
                'chunk_id': chunk_result.chunk_id,
                'level': chunk_result.level,
                'content_length': chunk_result.content_length,
                'keywords': chunk_result.keywords,
                'summary': chunk_result.summary,
                'structure_analysis': chunk_result.structure_analysis,
                'knowledge_graph': chunk_result.knowledge_graph,
                'analysis_metadata': chunk_result.analysis_metadata
            }
            chunks_data.append(chunk_data)

        with open(chunks_detail_file, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"💾 통합 분석 결과 저장 완료: {output_directory}")

    def _generate_chunk_prompts(self, chunk: Dict[str, Any], source_file: str, analysis_types: List[str]):
        """청크별 프롬프트 생성 및 저장"""
        try:
            # 분석 타입을 프롬프트 카테고리로 매핑
            prompt_categories = []
            for analysis_type in analysis_types:
                if analysis_type == "keywords":
                    prompt_categories.append("keyword_extraction")
                elif analysis_type == "summary":
                    prompt_categories.append("document_summary")
                elif analysis_type == "structure":
                    prompt_categories.append("structure_analysis")
                elif analysis_type == "knowledge_graph":
                    prompt_categories.append("knowledge_graph")

            # 프롬프트 요청 생성
            prompt_requests = self.prompt_manager.create_chunk_prompt_set(
                chunk_info=chunk,
                source_file=source_file,
                prompt_categories=prompt_categories
            )

            self.logger.debug(f"📝 청크 {chunk['chunk_id']}: {len(prompt_requests)}개 프롬프트 생성")

        except Exception as e:
            self.logger.error(f"❌ 청크 프롬프트 생성 실패: {str(e)}")

    def _generate_chunk_analysis_report(self, chunk_result: ChunkAnalysisResult):
        """청크 분석 완료 후 보고서 생성"""
        try:
            if not self.prompt_manager:
                return

            # 분석 결과를 요약한 개별 로그 생성
            chunk_summary = {
                'chunk_id': chunk_result.chunk_id,
                'level': chunk_result.level,
                'content_length': chunk_result.content_length,
                'keywords_count': len(chunk_result.keywords),
                'summary_available': bool(chunk_result.summary),
                'structure_analysis_available': bool(chunk_result.structure_analysis),
                'knowledge_graph_available': bool(chunk_result.knowledge_graph),
                'analysis_timestamp': chunk_result.analysis_metadata.get('analysis_timestamp'),
            }

            # 개별 청크 결과 파일 저장
            chunk_result_file = self.prompt_manager.results_dir / f"{chunk_result.chunk_id}_analysis_summary.json"
            with open(chunk_result_file, 'w', encoding='utf-8') as f:
                json.dump(chunk_summary, f, ensure_ascii=False, indent=2)

            # 청크별 상세 분석 결과 파일
            chunk_detail_file = self.prompt_manager.results_dir / f"{chunk_result.chunk_id}_detailed_analysis.json"
            detailed_data = {
                'chunk_id': chunk_result.chunk_id,
                'level': chunk_result.level,
                'content_length': chunk_result.content_length,
                'keywords': chunk_result.keywords,
                'summary': chunk_result.summary,
                'structure_analysis': chunk_result.structure_analysis,
                'knowledge_graph': chunk_result.knowledge_graph,
                'analysis_metadata': chunk_result.analysis_metadata
            }

            with open(chunk_detail_file, 'w', encoding='utf-8') as f:
                json.dump(detailed_data, f, ensure_ascii=False, indent=2)

            # 텍스트 보고서 생성
            report_text = self.prompt_manager.generate_chunk_report(chunk_result.chunk_id)
            report_file = self.prompt_manager.results_dir / f"{chunk_result.chunk_id}_analysis_report.md"

            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
                f.write("\n\n## 분석 결과 요약\n\n")
                f.write(f"- **키워드 수**: {len(chunk_result.keywords)}\n")
                f.write(f"- **요약**: {'생성됨' if chunk_result.summary else '없음'}\n")
                f.write(f"- **구조 분석**: {'완료' if chunk_result.structure_analysis else '없음'}\n")
                f.write(f"- **지식 그래프**: {'생성됨' if chunk_result.knowledge_graph else '없음'}\n")

                if chunk_result.keywords:
                    f.write(f"\n### 추출된 키워드\n\n")
                    for i, kw in enumerate(chunk_result.keywords[:10], 1):
                        keyword_text = kw.get('keyword', '알 수 없음')
                        score = kw.get('score', 0)
                        f.write(f"{i}. **{keyword_text}** (점수: {score:.3f})\n")

            self.logger.debug(f"📊 청크 {chunk_result.chunk_id} 분석 보고서 생성 완료")

        except Exception as e:
            self.logger.error(f"❌ 청크 분석 보고서 생성 실패: {str(e)}")

    def execute_chunk_prompts_with_llm(self, chunk_id: str, llm_executor) -> List[ChunkPromptResult]:
        """
        청크에 대해 생성된 모든 프롬프트를 LLM으로 실행합니다.

        Args:
            chunk_id: 청크 ID
            llm_executor: LLM 실행 함수 (prompt_text -> response_text)

        Returns:
            List[ChunkPromptResult]: 실행 결과 목록
        """
        if not self.prompt_manager:
            raise ValueError("프롬프트 매니저가 초기화되지 않았습니다.")

        # 저장된 프롬프트 요청 로드
        requests_file = self.prompt_manager.prompts_dir / f"{chunk_id}_prompt_requests.json"

        if not requests_file.exists():
            self.logger.warning(f"⚠️ 청크 {chunk_id}의 프롬프트 요청 파일을 찾을 수 없습니다.")
            return []

        with open(requests_file, 'r', encoding='utf-8') as f:
            requests_data = json.load(f)

        results = []
        requests = requests_data['requests']

        self.logger.info(f"🚀 청크 {chunk_id}: {len(requests)}개 프롬프트 실행 시작")

        for request_dict in requests:
            # 딕셔너리를 ChunkPromptRequest 객체로 변환
            request = ChunkPromptRequest(**request_dict)

            # 프롬프트 실행
            result = self.prompt_manager.execute_prompt(request, llm_executor)
            results.append(result)

            status = "✅" if result.success else "❌"
            self.logger.info(f"  {status} {request.prompt_category}.{request.prompt_template}")

        successful = len([r for r in results if r.success])
        self.logger.info(f"🎉 청크 {chunk_id} 프롬프트 실행 완료: {successful}/{len(results)} 성공")

        return results


__all__ = ["ChunkAnalyzer", "ChunkAnalysisResult", "IntegratedAnalysisResult"]