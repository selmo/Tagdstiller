from typing import List, Dict, Any, Optional
from pathlib import Path
import re
import time
import json
import logging
from datetime import datetime
from .base import KeywordExtractor, Keyword
from utils.text_cleaner import TextCleaner
from utils.position_mapper import PositionMapper
from utils.debug_logger import get_debug_logger
from prompts.templates import get_prompt_template
from prompts.config import PromptConfig
from utils.llm_logger import log_prompt_and_response

# LangChain imports
try:
    from langchain_ollama import OllamaLLM
except ImportError:
    try:
        from langchain_community.llms import Ollama as OllamaLLM
    except ImportError:
        OllamaLLM = None


class MetadataExtractor(KeywordExtractor):
    """문서 메타데이터 기반 키워드 추출기"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, db_session = None):
        super().__init__("metadata", config)
        self.is_loaded = True  # 메타데이터 추출기는 항상 사용 가능
        
        # 프롬프트 설정 초기화
        self.prompt_config = PromptConfig(config, db_session)
        
        # LangChain Ollama 인스턴스 초기화
        self.ollama_client = None
        
    def load_model(self) -> bool:
        """메타데이터 추출기는 별도 모델 로드가 필요하지 않습니다."""
        self.is_loaded = True
        return True
    
    def extract(self, text: str, file_path: Optional[Path] = None) -> List[Keyword]:
        """문서에서 메타데이터를 추출하여 키워드로 변환합니다."""
        logger = logging.getLogger(__name__)
        debug_logger = get_debug_logger()
        start_time = time.time()
        
        logger.info(f"🔍 메타데이터 추출 시작 - 텍스트 길이: {len(text)} 문자")
        
        # 디버그 로깅: 추출 시작
        debug_logger.start_extraction(
            extractor_name="metadata",
            file_info={"filename": str(file_path) if file_path else "unknown", "id": None},
            text=text,
            config=self.config
        )
        
        # 위치 매핑 생성
        position_mapper = PositionMapper()
        position_map = position_mapper.create_position_map(text, file_path)
        
        all_metadata_keywords = []
        
        try:
            # LLM 기반 문서 요약 메타데이터 추출만 사용
            if self.config.get("extract_summary", True):
                summary_keywords = self._extract_summary_metadata(text)
                all_metadata_keywords.extend(summary_keywords)
            else:
                logger.info("📝 LLM 기반 요약이 비활성화되어 메타데이터 추출을 건너뜁니다.")
            
            # 디버그 로깅: 최종 결과
            extraction_time = time.time() - start_time
            debug_logger.log_final_results(
                extractor_name="metadata",
                final_keywords=[{
                    "keyword": kw.text,
                    "score": kw.score,
                    "category": kw.category,
                    "start_position": kw.start_position,
                    "end_position": kw.end_position,
                    "context": kw.context_snippet
                } for kw in all_metadata_keywords],
                extraction_time=extraction_time,
                total_processing_time=time.time() - start_time
            )
            
            logger.info(f"✅ 메타데이터 추출 완료 - {len(all_metadata_keywords)}개 메타데이터 키워드, 처리시간: {extraction_time:.2f}초")
            return all_metadata_keywords
            
        except Exception as e:
            logger.error(f"❌ 메타데이터 추출 실패: {e}")
            return []
        finally:
            # 디버그 세션 저장
            debug_logger.save_debug_session()
    
    def _extract_structure_metadata(self, text: str, position_mapper: PositionMapper, position_map: Dict[str, any]) -> List[Keyword]:
        """문서 구조 관련 메타데이터를 추출합니다."""
        logger = logging.getLogger(__name__)
        keywords = []
        
        # 제목 추출 (마크다운 스타일)
        heading_patterns = [
            (r'^#{1}\s+(.+)$', 'title_h1', 1.0),          # # 제목
            (r'^#{2}\s+(.+)$', 'title_h2', 0.9),          # ## 제목
            (r'^#{3}\s+(.+)$', 'title_h3', 0.8),          # ### 제목
            (r'^#{4,6}\s+(.+)$', 'title_h4_h6', 0.7),     # #### ~ ###### 제목
        ]
        
        lines = text.split('\n')
        for line_idx, line in enumerate(lines):
            line = line.strip()
            
            for pattern, category, base_score in heading_patterns:
                matches = re.finditer(pattern, line, re.MULTILINE)
                for match in matches:
                    title_text = match.group(1).strip()
                    if len(title_text) >= 2:
                        # 제목 위치 찾기
                        char_pos = text.find(line)
                        if char_pos != -1:
                            page_number, line_number, column_number = position_mapper.get_position_info(char_pos, position_map)
                            
                            keywords.append(Keyword(
                                text=title_text,
                                score=base_score,
                                extractor=self.name,
                                category=category,
                                start_position=char_pos,
                                end_position=char_pos + len(title_text),
                                context_snippet=line,
                                page_number=page_number,
                                line_number=line_number,
                                column_number=column_number
                            ))
                            
                            logger.debug(f"📋 구조 메타데이터 - {category}: '{title_text}'")
        
        # 목록 구조 감지
        list_patterns = [
            (r'^\s*[-*+]\s+(.+)$', 'list_item', 0.5),      # 불릿 목록
            (r'^\s*\d+\.\s+(.+)$', 'numbered_item', 0.6),  # 번호 목록
        ]
        
        for line in lines:
            line = line.strip()
            for pattern, category, score in list_patterns:
                match = re.match(pattern, line)
                if match:
                    item_text = match.group(1).strip()
                    if len(item_text) >= 3:
                        # 위치는 대략적으로 계산
                        char_pos = text.find(line)
                        if char_pos != -1:
                            keywords.append(Keyword(
                                text=item_text,
                                score=score,
                                extractor=self.name,
                                category=category,
                                start_position=char_pos,
                                end_position=char_pos + len(item_text),
                                context_snippet=line,
                                page_number=None,
                                line_number=None,
                                column_number=None
                            ))
        
        return keywords
    
    def _extract_statistical_metadata(self, text: str) -> List[Keyword]:
        """통계적 메타데이터를 추출합니다."""
        logger = logging.getLogger(__name__)
        keywords = []
        
        # 기본 통계 계산
        char_count = len(text)
        word_count = len(text.split())
        sentence_count = len(re.split(r'[.!?]+', text))
        paragraph_count = len([p for p in text.split('\n\n') if p.strip()])
        
        # 평균 통계
        avg_words_per_sentence = word_count / max(sentence_count, 1)
        avg_chars_per_word = char_count / max(word_count, 1)
        
        # 통계를 메타데이터 키워드로 변환
        statistical_data = [
            (self._categorize_length(char_count), "doc_length", 0.7),
            (self._categorize_word_count(word_count), "word_count", 0.6),
            (self._categorize_sentence_count(sentence_count), "sentence_count", 0.5),
            (self._categorize_paragraph_count(paragraph_count), "paragraph_count", 0.5),
            (self._categorize_sentence_length(avg_words_per_sentence), "sentence_length", 0.4),
            (self._categorize_complexity(avg_chars_per_word), "complexity", 0.6),
        ]
        
        for text_label, category, score in statistical_data:
            keywords.append(Keyword(
                text=text_label,
                score=score,
                extractor=self.name,
                category=category,
                start_position=None,
                end_position=None,
                context_snippet=f"통계: {text_label}",
                page_number=None,
                line_number=None,
                column_number=None
            ))
            
            logger.debug(f"📊 통계 메타데이터: {text_label}")
        
        return keywords
    
    def _extract_content_metadata(self, text: str, position_mapper: PositionMapper, position_map: Dict[str, any]) -> List[Keyword]:
        """콘텐츠 관련 메타데이터를 추출합니다."""
        logger = logging.getLogger(__name__)
        keywords = []
        
        # URL 패턴 찾기
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.finditer(url_pattern, text)
        
        for match in urls:
            url_text = match.group()
            # 도메인 추출
            domain_match = re.search(r'https?://([^/]+)', url_text)
            if domain_match:
                domain = domain_match.group(1)
                keywords.append(Keyword(
                    text=domain,
                    score=0.5,
                    extractor=self.name,
                    category="url_reference",
                    start_position=match.start(),
                    end_position=match.end(),
                    context_snippet=url_text,
                    page_number=None,
                    line_number=None,
                    column_number=None
                ))
        
        # 이메일 패턴 찾기
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.finditer(email_pattern, text)
        
        for match in emails:
            email_text = match.group()
            domain = email_text.split('@')[1]
            keywords.append(Keyword(
                text=domain,
                score=0.6,
                extractor=self.name,
                category="email_reference",
                start_position=match.start(),
                end_position=match.end(),
                context_snippet=email_text,
                page_number=None,
                line_number=None,
                column_number=None
            ))
        
        # 날짜 패턴 찾기
        date_patterns = [
            (r'\d{4}년\s*\d{1,2}월\s*\d{1,2}일', 'date_korean'),
            (r'\d{4}-\d{2}-\d{2}', 'date_iso'),
            (r'\d{1,2}/\d{1,2}/\d{4}', 'date_us'),
            (r'\d{1,2}\.\d{1,2}\.\d{4}', 'date_eu'),
        ]
        
        for pattern, category in date_patterns:
            dates = re.finditer(pattern, text)
            for match in dates:
                date_text = match.group()
                keywords.append(Keyword(
                    text=date_text,
                    score=0.7,
                    extractor=self.name,
                    category=category,
                    start_position=match.start(),
                    end_position=match.end(),
                    context_snippet=date_text,
                    page_number=None,
                    line_number=None,
                    column_number=None
                ))
        
        # 숫자 패턴 분석
        number_pattern = r'\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b'
        numbers = re.findall(number_pattern, text)
        
        if numbers:
            # 숫자의 분포 분석
            numeric_values = []
            for num_str in numbers:
                try:
                    numeric_values.append(float(num_str.replace(',', '')))
                except ValueError:
                    continue
            
            if numeric_values:
                avg_number = sum(numeric_values) / len(numeric_values)
                keywords.append(Keyword(
                    text=self._categorize_numbers(avg_number),
                    score=0.4,
                    extractor=self.name,
                    category="numeric_content",
                    start_position=None,
                    end_position=None,
                    context_snippet=f"평균 수치: {avg_number:.2f}",
                    page_number=None,
                    line_number=None,
                    column_number=None
                ))
        
        logger.debug(f"📄 콘텐츠 메타데이터 {len(keywords)}개 추출")
        return keywords
    
    def _extract_summary_metadata(self, text: str) -> List[Keyword]:
        """LLM을 사용하여 문서 요약 메타데이터를 추출합니다."""
        logger = logging.getLogger(__name__)
        keywords = []
        
        try:
            # 텍스트 정제
            clean_text = TextCleaner.clean_text(text)
            
            # 문서가 너무 짧은 경우 요약 건너뜀
            if len(clean_text.strip()) < 100:
                logger.debug("📝 문서가 너무 짧아 요약을 건너뜁니다.")
                return keywords
            
            # LLM 설정 가져오기
            ollama_config = self._get_ollama_config()
            if not ollama_config['enabled']:
                logger.debug("📝 LLM이 비활성화되어 규칙 기반 요약을 사용합니다.")
                return self._extract_rule_based_summary(clean_text)
            
            logger.info(f"🤖 LLM을 사용하여 문서 요약 생성 중... (텍스트 길이: {len(clean_text)}자)")
            
            # LLM을 통한 요약 생성
            summary_result = self._generate_llm_summary(clean_text, ollama_config)
            
            if summary_result:
                logger.info(f"✅ LLM 요약 생성 완료")
                keywords.extend(summary_result)
            else:
                logger.warning("⚠️ LLM 요약 실패, 규칙 기반 요약으로 대체")
                keywords.extend(self._extract_rule_based_summary(clean_text))
            
            return keywords
            
        except Exception as e:
            logger.error(f"❌ 요약 메타데이터 추출 실패: {e}")
            # 오류 발생 시 규칙 기반 요약으로 대체
            try:
                return self._extract_rule_based_summary(clean_text)
            except:
                return []
    
    def _get_ollama_config(self) -> Dict[str, any]:
        """Ollama LLM 설정을 가져옵니다."""
        # LLM이 활성화되고 LLM 요약이 활성화된 경우에만 LLM 사용
        llm_enabled = self.config.get('llm_enabled', False)
        llm_summary_enabled = self.config.get('llm_summary', True)
        
        return {
            'enabled': llm_enabled and llm_summary_enabled,
            'base_url': self.config.get('ollama_base_url', 'http://localhost:11434'),
            'model': self.config.get('ollama_model', 'gemma3n:latest'),
            'timeout': self.config.get('ollama_timeout', 30)
        }
    
    def _generate_llm_summary(self, text: str, ollama_config: Dict[str, any]) -> List[Keyword]:
        """LLM을 사용하여 문서 요약을 생성합니다."""
        import requests
        import json
        logger = logging.getLogger(__name__)
        
        try:
            # 텍스트가 너무 긴 경우 청킹
            max_chunk_size = 4000  # 토큰 한계 고려
            if len(text) > max_chunk_size:
                # 문장 단위로 청킹
                sentences = re.split(r'[.!?]+', text)
                chunks = []
                current_chunk = ""
                
                for sentence in sentences:
                    if len(current_chunk + sentence) > max_chunk_size and current_chunk:
                        chunks.append(current_chunk.strip())
                        current_chunk = sentence
                    else:
                        current_chunk += sentence + ". "
                        
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                
                # 각 청크별로 요약 생성 후 통합
                all_summaries = []
                for i, chunk in enumerate(chunks, 1):
                    logger.info(f"  📄 청크 {i}/{len(chunks)} 요약 생성 중...")
                    chunk_summary = self._call_llm_for_summary(chunk, ollama_config)
                    if chunk_summary:
                        all_summaries.extend(chunk_summary)
                
                return all_summaries
            else:
                return self._call_llm_for_summary(text, ollama_config)
                
        except Exception as e:
            logger.error(f"❌ LLM 요약 생성 실패: {e}")
            return []
    
    def _call_llm_for_summary(self, text: str, ollama_config: Dict[str, any]) -> List[Keyword]:
        """LangChain을 사용하여 LLM API를 호출하고 요약을 생성합니다."""
        logger = logging.getLogger(__name__)
        
        try:
            # LangChain Ollama 클라이언트 초기화 (필요시)
            if not self.ollama_client:
                try:
                    if not OllamaLLM:
                        raise ImportError("LangChain Ollama not available")
                    
                    self.ollama_client = OllamaLLM(
                        base_url=ollama_config['base_url'],
                        model=ollama_config['model'],
                        timeout=ollama_config['timeout']
                    )
                    logger.debug(f"✅ LangChain Ollama 클라이언트 초기화 성공")
                except Exception as e:
                    logger.error(f"❌ LangChain Ollama 클라이언트 초기화 실패: {e}")
                    # 폴백: 기존 requests 방식 사용
                    return self._call_llm_for_summary_fallback(text, ollama_config)
            
            # 프롬프트 템플릿 사용
            try:
                template_name = self.prompt_config.get_template_name('document_summary')
                variables = self.prompt_config.get_template_variables('document_summary', text)
                prompt = get_prompt_template('document_summary', template_name, **variables)
                logger.debug(f"🎯 문서 요약 템플릿 사용: document_summary.{template_name}")
            except Exception as e:
                logger.warning(f"⚠️ 프롬프트 템플릿 사용 실패, 기본 프롬프트 사용: {e}")
                # 폴백: 기존 방식
                prompt = f"""다음 문서를 분석하여 5가지 유형의 요약을 생성해주세요. 각 요약은 간결하고 핵심적인 내용으로 작성해주세요.

문서 내용:
{text}

다음 JSON 형식으로 응답해주세요:
{{
  "intro": "문서의 도입부나 시작 부분을 한 문장으로 요약",
  "conclusion": "문서의 결론이나 마무리 부분을 한 문장으로 요약", 
  "core": "문서의 가장 핵심적인 내용을 한 문장으로 요약",
  "topics": ["주요", "키워드", "목록", "5개", "이내"],
  "tone": "문서의 전반적인 톤이나 성격 (예: 공식적, 학술적, 기술적, 설명적, 정보제공적)"
}}

JSON 형식으로만 응답해주세요:"""
        
            # LangChain을 통해 LLM 호출
            logger.debug(f"🚀 LangChain Ollama 호출 - 모델: {ollama_config['model']}")
            
            start_time = time.time()
            response = self.ollama_client.invoke(prompt)
            call_duration = time.time() - start_time
            
            logger.debug(f"✅ LangChain LLM 응답 수신 - 길이: {len(response)}자, 소요시간: {call_duration:.2f}초")

            # 프롬프트/응답 파일 저장 및 로그 기록
            log_prompt_and_response(
                label="document_summary",
                provider="ollama",
                model=ollama_config['model'],
                prompt=prompt,
                response=response,
                logger=logger,
                meta={
                    "base_url": ollama_config['base_url'],
                    "timeout": ollama_config['timeout'],
                    "langchain_version": True,
                    "call_duration": call_duration,
                },
            )

            # JSON 응답 파싱
            return self._parse_llm_summary_response(response)
                
        except Exception as e:
            logger.error(f"❌ LangChain LLM API 호출 실패: {e}")
            # 폴백: 기존 requests 방식 사용
            logger.info("기존 requests 방식으로 폴백 시도...")
            return self._call_llm_for_summary_fallback(text, ollama_config)
    
    def _call_llm_for_summary_fallback(self, text: str, ollama_config: Dict[str, any]) -> List[Keyword]:
        """기존 requests 방식의 LLM API 호출 (폴백용)."""
        import requests
        import json
        logger = logging.getLogger(__name__)
        
        try:
            # 프롬프트 템플릿 사용
            try:
                template_name = self.prompt_config.get_template_name('document_summary')
                variables = self.prompt_config.get_template_variables('document_summary', text)
                prompt = get_prompt_template('document_summary', template_name, **variables)
                logger.debug(f"🎯 문서 요약 템플릿 사용 (폴백): document_summary.{template_name}")
            except Exception as e:
                logger.warning(f"⚠️ 프롬프트 템플릿 사용 실패, 기본 프롬프트 사용: {e}")
                # 폴백: 기존 방식
                prompt = f"""다음 문서를 분석하여 5가지 유형의 요약을 생성해주세요. 각 요약은 간결하고 핵심적인 내용으로 작성해주세요.

문서 내용:
{text}

다음 JSON 형식으로 응답해주세요:
{{
  "intro": "문서의 도입부나 시작 부분을 한 문장으로 요약",
  "conclusion": "문서의 결론이나 마무리 부분을 한 문장으로 요약", 
  "core": "문서의 가장 핵심적인 내용을 한 문장으로 요약",
  "topics": ["주요", "키워드", "목록", "5개", "이내"],
  "tone": "문서의 전반적인 톤이나 성격 (예: 공식적, 학술적, 기술적, 설명적, 정보제공적)"
}}

JSON 형식으로만 응답해주세요:"""
            
            # 프롬프트 설정에서 LLM 파라미터 가져오기
            llm_params = self.prompt_config.get_llm_params('document_summary')
            
            payload = {
                "model": ollama_config['model'],
                "prompt": prompt,
                "stream": False,
                "options": llm_params
            }
            
            logger.debug(f"🚀 Ollama API 폴백 호출 - 모델: {ollama_config['model']}")
            
            response = requests.post(
                f"{ollama_config['base_url']}/api/generate",
                json=payload,
                timeout=ollama_config['timeout']
            )
            
            # 프롬프트/응답 파일 저장 및 로그 기록 (상태 코드 무관하게 저장)
            resp_text = ""
            if response.status_code == 200:
                resp_text = response.json().get("response", "")
            else:
                resp_text = response.text or ""

            log_prompt_and_response(
                label="document_summary",
                provider="ollama",
                model=ollama_config['model'],
                prompt=prompt,
                response=resp_text,
                logger=logger,
                meta={
                    "base_url": ollama_config['base_url'],
                    "status_code": response.status_code,
                    "timeout": ollama_config['timeout'],
                    "options": llm_params,
                    "fallback_mode": True,
                },
            )

            if response.status_code == 200:
                logger.debug(f"✅ LLM 폴백 응답 수신 - 길이: {len(resp_text)}자")
                # JSON 응답 파싱
                return self._parse_llm_summary_response(resp_text)
            else:
                logger.error(f"❌ Ollama API 폴백 오류: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ LLM API 폴백 호출 실패: {e}")
            return []
    
    def _parse_llm_summary_response(self, response: str) -> List[Keyword]:
        """LLM 응답을 파싱하여 키워드 목록을 생성합니다."""
        logger = logging.getLogger(__name__)
        keywords = []
        
        try:
            # JSON 부분 추출
            json_text = self._extract_json_from_response(response)
            summary_data = json.loads(json_text)
            
            # 도입부 요약
            if summary_data.get('intro'):
                intro_text = summary_data['intro'][:150]
                keywords.append(Keyword(
                    text=intro_text,
                    score=0.9,
                    extractor=self.name,
                    category="summary_intro",
                    start_position=None,
                    end_position=None,
                    context_snippet=intro_text,
                    page_number=None,
                    line_number=None,
                    column_number=None
                ))
            
            # 결론부 요약
            if summary_data.get('conclusion'):
                conclusion_text = summary_data['conclusion'][:150]
                keywords.append(Keyword(
                    text=conclusion_text,
                    score=0.9,
                    extractor=self.name,
                    category="summary_conclusion",
                    start_position=None,
                    end_position=None,
                    context_snippet=conclusion_text,
                    page_number=None,
                    line_number=None,
                    column_number=None
                ))
            
            # 핵심 내용
            if summary_data.get('core'):
                core_text = summary_data['core'][:150]
                keywords.append(Keyword(
                    text=core_text,
                    score=1.0,
                    extractor=self.name,
                    category="summary_core",
                    start_position=None,
                    end_position=None,
                    context_snippet=core_text,
                    page_number=None,
                    line_number=None,
                    column_number=None
                ))
            
            # 주요 토픽들
            if summary_data.get('topics') and isinstance(summary_data['topics'], list):
                for i, topic in enumerate(summary_data['topics'][:5], 1):
                    keywords.append(Keyword(
                        text=topic,
                        score=0.8,
                        extractor=self.name,
                        category="summary_topic",
                        start_position=None,
                        end_position=None,
                        context_snippet=f"주요 주제 #{i}: {topic}",
                        page_number=None,
                        line_number=None,
                        column_number=None
                    ))
            
            # 문서 톤
            if summary_data.get('tone'):
                tone_text = summary_data['tone'][:50]
                keywords.append(Keyword(
                    text=tone_text,
                    score=0.7,
                    extractor=self.name,
                    category="summary_tone",
                    start_position=None,
                    end_position=None,
                    context_snippet=f"문서의 전반적 성격: {tone_text}",
                    page_number=None,
                    line_number=None,
                    column_number=None
                ))
            
            logger.info(f"📝 LLM 요약 파싱 완료 - {len(keywords)}개 요약 키워드 생성")
            return keywords
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ LLM 응답 JSON 파싱 실패: {e}")
            logger.error(f"응답 내용: {response[:200]}...")
            return []
        except Exception as e:
            logger.error(f"❌ LLM 응답 파싱 중 오류: {e}")
            return []
    
    def _extract_json_from_response(self, response: str) -> str:
        """응답에서 JSON 부분만 추출합니다."""
        import re
        
        # 마크다운 코드 블록 제거
        response = re.sub(r'```json\s*', '', response, flags=re.IGNORECASE)
        response = re.sub(r'```\s*', '', response)
        
        # JSON 객체 찾기
        json_pattern = r'\{[^{}]*"intro"[^{}]*\}'
        match = re.search(json_pattern, response, re.DOTALL)
        if match:
            return match.group(0)
        
        # 더 관대한 JSON 패턴
        broad_pattern = r'\{.*?\}' 
        match = re.search(broad_pattern, response, re.DOTALL)
        if match:
            return match.group(0)
        
        # JSON 마커 이후의 내용 찾기
        json_markers = ['JSON:', '{']
        for marker in json_markers:
            if marker in response:
                json_part = response[response.find(marker):].strip()
                if marker != '{':
                    json_part = json_part[len(marker):].strip()
                
                # 첫 번째 { 부터 마지막 } 까지 추출
                start_idx = json_part.find('{')
                if start_idx != -1:
                    end_idx = json_part.rfind('}')
                    if end_idx != -1 and end_idx > start_idx:
                        return json_part[start_idx:end_idx + 1]
        
        # 응답 전체가 JSON일 수도 있음
        return response.strip()
    
    def _extract_rule_based_summary(self, text: str) -> List[Keyword]:
        """규칙 기반 문서 요약 (LLM 대체용)."""
        logger = logging.getLogger(__name__)
        keywords = []
        
        try:
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
            
            # 문서가 너무 짧은 경우
            if len(sentences) < 3:
                return keywords
            
            # 1. 첫 번째 문장 (도입부)
            first_sentence = sentences[0][:100] + "..." if len(sentences[0]) > 100 else sentences[0]
            keywords.append(Keyword(
                text=first_sentence,
                score=0.8,
                extractor=self.name,
                category="summary_intro",
                start_position=None,
                end_position=None,
                context_snippet=first_sentence,
                page_number=None,
                line_number=None,
                column_number=None
            ))
            
            # 2. 마지막 문장 (결론부)
            if len(sentences) > 1:
                last_sentence = sentences[-1][:100] + "..." if len(sentences[-1]) > 100 else sentences[-1]
                keywords.append(Keyword(
                    text=last_sentence,
                    score=0.8,
                    extractor=self.name,
                    category="summary_conclusion",
                    start_position=None,
                    end_position=None,
                    context_snippet=last_sentence,
                    page_number=None,
                    line_number=None,
                    column_number=None
                ))
            
            # 3. 가장 긴 문장 (핵심 내용)
            longest_sentence = max(sentences, key=len)
            if len(longest_sentence) > 50:
                core_content = longest_sentence[:120] + "..." if len(longest_sentence) > 120 else longest_sentence
                keywords.append(Keyword(
                    text=core_content,
                    score=0.9,
                    extractor=self.name,
                    category="summary_core",
                    start_position=None,
                    end_position=None,
                    context_snippet=core_content,
                    page_number=None,
                    line_number=None,
                    column_number=None
                ))
            
            # 4. 문서 주제 키워드 추출 (빈도 기반)
            word_freq = {}
            for sentence in sentences[:10]:  # 처음 10개 문장만 분석
                words = re.findall(r'\b[가-힣a-zA-Z]{2,}\b', sentence)
                for word in words:
                    if TextCleaner.is_meaningful_keyword(word):
                        word_freq[word] = word_freq.get(word, 0) + 1
            
            # 상위 3개 빈도 키워드
            top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:3]
            for word, freq in top_words:
                if freq >= 2:  # 최소 2번 이상 등장
                    keywords.append(Keyword(
                        text=word,
                        score=min(0.7, 0.4 + freq * 0.1),  # 빈도에 따른 점수
                        extractor=self.name,
                        category="summary_topic",
                        start_position=None,
                        end_position=None,
                        context_snippet=f"빈도: {freq}회",
                        page_number=None,
                        line_number=None,
                        column_number=None
                    ))
            
            # 5. 문서 분위기/톤 분석
            tone = self._analyze_document_tone(clean_text)
            if tone:
                keywords.append(Keyword(
                    text=tone,
                    score=0.6,
                    extractor=self.name,
                    category="summary_tone",
                    start_position=None,
                    end_position=None,
                    context_snippet=f"분석된 문서 분위기: {tone}",
                    page_number=None,
                    line_number=None,
                    column_number=None
                ))
            
            logger.debug(f"📝 요약 메타데이터 {len(keywords)}개 추출")
            
        except Exception as e:
            logger.warning(f"⚠️ 요약 메타데이터 추출 중 오류: {e}")
        
        return keywords
    
    def _analyze_document_tone(self, text: str) -> str:
        """문서의 톤과 분위기를 분석합니다."""
        # 감정 분석을 위한 키워드 패턴
        tone_patterns = {
            '학술적': [r'연구', r'분석', r'결과', r'방법론', r'이론', r'가설', r'실험', r'데이터'],
            '공식적': [r'공지', r'안내', r'규정', r'지침', r'절차', r'정책', r'계획'],
            '기술적': [r'시스템', r'구현', r'개발', r'코드', r'알고리즘', r'프로그래밍', r'소프트웨어'],
            '설명적': [r'방법', r'단계', r'과정', r'절차', r'예시', r'설명', r'가이드'],
            '분석적': [r'비교', r'검토', r'평가', r'분석', r'고찰', r'조사', r'연구'],
            '긍정적': [r'성공', r'향상', r'개선', r'효과', r'발전', r'좋은', r'우수한'],
            '부정적': [r'문제', r'실패', r'오류', r'위험', r'어려움', r'부족', r'나쁜']
        }
        
        text_lower = text.lower()
        tone_scores = {}
        
        for tone, patterns in tone_patterns.items():
            score = 0
            for pattern in patterns:
                score += len(re.findall(pattern, text_lower))
            
            if score > 0:
                tone_scores[tone] = score
        
        if tone_scores:
            # 가장 높은 점수의 톤 반환
            dominant_tone = max(tone_scores, key=tone_scores.get)
            return dominant_tone
        
        return "일반적"
    
    def _extract_file_metadata(self, file_path: Path, text: str) -> List[Keyword]:
        """파일 관련 메타데이터를 추출합니다."""
        logger = logging.getLogger(__name__)
        keywords = []
        
        # 파일 확장자
        file_extension = file_path.suffix.lower().lstrip('.')
        if file_extension:
            keywords.append(Keyword(
                text=file_extension,
                score=0.8,
                extractor=self.name,
                category="file_format",
                start_position=None,
                end_position=None,
                context_snippet=f"파일 형식: {file_extension}",
                page_number=None,
                line_number=None,
                column_number=None
            ))
        
        # 파일명에서 키워드 추출
        filename_without_ext = file_path.stem
        filename_keywords = self._extract_filename_keywords(filename_without_ext)
        keywords.extend(filename_keywords)
        
        # 파일 크기 카테고리 (텍스트 길이 기반 추정)
        size_category = self._categorize_file_size(len(text))
        keywords.append(Keyword(
            text=size_category,
            score=0.5,
            extractor=self.name,
            category="file_size",
            start_position=None,
            end_position=None,
            context_snippet=f"파일 크기 카테고리: {size_category}",
            page_number=None,
            line_number=None,
            column_number=None
        ))
        
        logger.debug(f"📁 파일 메타데이터 {len(keywords)}개 추출")
        return keywords
    
    def _extract_filename_keywords(self, filename: str) -> List[Keyword]:
        """파일명에서 의미있는 키워드를 추출합니다."""
        keywords = []
        
        # 파일명을 단어로 분할 (언더스코어, 하이픈, 공백 기준)
        filename_words = re.split(r'[_\-\s]+', filename)
        
        for word in filename_words:
            word = word.strip()
            if len(word) >= 2 and TextCleaner.is_meaningful_keyword(word):
                keywords.append(Keyword(
                    text=word,
                    score=0.6,
                    extractor=self.name,
                    category="filename_keyword",
                    start_position=None,
                    end_position=None,
                    context_snippet=f"파일명에서 추출: {word}",
                    page_number=None,
                    line_number=None,
                    column_number=None
                ))
        
        return keywords
    
    # 카테고리화 헬퍼 메서드들
    def _categorize_length(self, char_count: int) -> str:
        if char_count < 1000:
            return "매우짧음"
        elif char_count < 5000:
            return "짧음"
        elif char_count < 20000:
            return "보통"
        elif char_count < 50000:
            return "김"
        else:
            return "매우김"
    
    def _categorize_word_count(self, word_count: int) -> str:
        if word_count < 100:
            return "소량"
        elif word_count < 500:
            return "적음"
        elif word_count < 2000:
            return "보통"
        elif word_count < 5000:
            return "많음"
        else:
            return "대량"
    
    def _categorize_sentence_count(self, sentence_count: int) -> str:
        if sentence_count < 10:
            return "단순"
        elif sentence_count < 50:
            return "보통"
        elif sentence_count < 200:
            return "복잡"
        else:
            return "매우복잡"
    
    def _categorize_paragraph_count(self, paragraph_count: int) -> str:
        if paragraph_count < 5:
            return "단순구조"
        elif paragraph_count < 20:
            return "보통구조"
        else:
            return "복잡구조"
    
    def _categorize_sentence_length(self, avg_words: float) -> str:
        if avg_words < 8:
            return "짧은문장"
        elif avg_words < 15:
            return "보통문장"
        elif avg_words < 25:
            return "긴문장"
        else:
            return "매우긴문장"
    
    def _categorize_complexity(self, avg_chars_per_word: float) -> str:
        if avg_chars_per_word < 4:
            return "단순"
        elif avg_chars_per_word < 6:
            return "보통"
        elif avg_chars_per_word < 8:
            return "복잡"
        else:
            return "매우복잡"
    
    def _categorize_numbers(self, avg_number: float) -> str:
        if avg_number < 10:
            return "소수"
        elif avg_number < 100:
            return "중간수"
        elif avg_number < 1000:
            return "큰수"
        else:
            return "대형수"
    
    def _categorize_file_size(self, text_length: int) -> str:
        if text_length < 5000:
            return "소형"
        elif text_length < 50000:
            return "중형"
        elif text_length < 200000:
            return "대형"
        else:
            return "초대형"
