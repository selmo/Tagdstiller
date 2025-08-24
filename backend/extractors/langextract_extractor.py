from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import time
import logging
from .base import KeywordExtractor, Keyword
from utils.text_cleaner import TextCleaner
from utils.position_mapper import PositionMapper
from utils.debug_logger import get_debug_logger


class LangExtractExtractor(KeywordExtractor):
    """LangExtract 기반 구조화된 정보 추출기"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, db_session = None):
        super().__init__("langextract", config)
        self.langextract_client = None
        self.ollama_config = self._get_ollama_config()
        
    def _get_ollama_config(self) -> Dict[str, Any]:
        """기존 Ollama 설정 가져오기"""
        return {
            'base_url': self.config.get('ollama_base_url', 'http://localhost:11434'),
            'model': self.config.get('ollama_model', 'llama3.2'),
            'timeout': self.config.get('ollama_timeout', 30)
        }
    
    def load_model(self) -> bool:
        """LangExtract 클라이언트 초기화"""
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"LangExtract 추출기 로드 시작 - Ollama 설정: {self.ollama_config}")
            
            # LangExtract import 및 초기화
            import langextract
            from langextract import factory
            
            # Ollama 모델 생성 (새로운 API 사용)
            model_id = self.ollama_config['model']
            logger.info(f"🔄 Ollama 모델 생성 시도: {model_id}")
            
            # factory를 사용하여 Ollama 모델 생성
            ollama_model = factory.create_model_from_id(
                model_id=model_id,
                provider="ollama",
                base_url=self.ollama_config['base_url'],
                timeout=self.ollama_config['timeout']
            )
            
            # Ollama 연결 테스트 (예제 데이터 포함)
            logger.info(f"🔄 Ollama 연결 테스트 시작...")
            
            # 예제 데이터 생성
            from langextract.data import ExampleData
            examples = [
                ExampleData(
                    text="Apple Inc. is a technology company based in Cupertino.",
                    extractions={
                        "keywords": [
                            {"text": "Apple Inc.", "category": "organization"},
                            {"text": "technology", "category": "concept"},
                            {"text": "Cupertino", "category": "location"}
                        ]
                    }
                )
            ]
            
            test_result = langextract.extract(
                "Test document for keyword extraction",
                prompt_description="Extract important keywords and their categories",
                examples=examples,
                model=ollama_model,
                max_char_buffer=100
            )
            if test_result:
                self.langextract_client = {
                    'langextract': langextract,
                    'model': ollama_model,
                    'schema': self._get_extraction_schema(),
                    'config': self._get_langextract_config()
                }
                self.is_loaded = True
                logger.info(f"✅ LangExtract 추출기 로드 성공 - Ollama 모델: {self.ollama_config['model']}")
            else:
                self.is_loaded = False
                logger.error(f"❌ Ollama 연결 테스트 실패")
                
            return self.is_loaded
            
        except ImportError as e:
            logger.error(f"❌ LangExtract 라이브러리 import 실패: {e}")
            # 대체 구현: 직접 Ollama 호출 방식 사용
            try:
                logger.info("🔄 대체 구현으로 전환 - 직접 Ollama 호출 방식")
                import requests
                
                # Ollama 연결 테스트
                response = requests.get(f"{self.ollama_config['base_url']}/api/tags", timeout=5)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_found = any(model["name"].startswith(self.ollama_config['model']) for model in models)
                    
                    if model_found:
                        self.langextract_client = {
                            'mode': 'direct_ollama',
                            'schema': self._get_extraction_schema(),
                            'config': self._get_langextract_config()
                        }
                        self.is_loaded = True
                        logger.info(f"✅ LangExtract 추출기 로드 성공 (직접 Ollama 방식) - 모델: {self.ollama_config['model']}")
                    else:
                        logger.error(f"❌ 모델 '{self.ollama_config['model']}' 없음")
                        self.is_loaded = False
                else:
                    logger.error(f"❌ Ollama 서버 연결 실패: {response.status_code}")
                    self.is_loaded = False
                    
                return self.is_loaded
                
            except Exception as fallback_e:
                logger.error(f"❌ 대체 구현도 실패: {fallback_e}")
                self.is_loaded = False
                return False
        except Exception as e:
            logger.error(f"❌ LangExtract 추출기 초기화 실패: {e}")
            self.is_loaded = False
            return False
    
    def _get_extraction_schema(self) -> Dict[str, Any]:
        """키워드 추출용 스키마 정의"""
        return {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "추출된 키워드 또는 핵심 구문"
                            },
                            "category": {
                                "type": "string",
                                "description": "키워드 카테고리 (예: 기술, 인물, 개념, 조직 등)"
                            },
                            "confidence": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                                "description": "추출 신뢰도 (0.0-1.0)"
                            },
                            "importance": {
                                "type": "string",
                                "enum": ["high", "medium", "low"],
                                "description": "중요도 수준"
                            },
                            "semantic_type": {
                                "type": "string",
                                "description": "의미적 유형 (명사, 동사, 전문용어 등)"
                            }
                        },
                        "required": ["text", "confidence"]
                    }
                }
            },
            "required": ["keywords"]
        }
    
    def _get_langextract_config(self) -> Dict[str, Any]:
        """LangExtract 설정 가져오기"""
        return {
            'max_entities': self.config.get('max_keywords', 15),
            'chunk_size': self.config.get('chunk_size', 2000),
            'overlap': self.config.get('overlap', 200),
            'confidence_threshold': self.config.get('confidence_threshold', 0.6),
            'temperature': 0.1,
            'max_tokens': 1500
        }
    
    def extract(self, text: str, file_path: Optional[Path] = None) -> List[Keyword]:
        """LangExtract를 사용하여 키워드를 추출합니다."""
        logger = logging.getLogger(__name__)
        debug_logger = get_debug_logger()
        start_time = time.time()
        
        logger.info(f"🔍 LangExtract 키워드 추출 시작 - 원본 텍스트 길이: {len(text)} 문자")
        
        # 디버그 로깅: 추출 시작
        debug_logger.start_extraction(
            extractor_name="langextract",
            file_info={"filename": str(file_path) if file_path else "unknown", "id": None},
            text=text,
            config=self.config
        )
        
        # 위치 매핑 생성
        position_mapper = PositionMapper()
        position_map = position_mapper.create_position_map(text, file_path)
        logger.info(f"📍 위치 매핑 생성 완료 - 총 {position_map['total_pages']}페이지, {position_map['total_lines']}줄")
        
        # 텍스트 전처리
        original_text_copy = text
        cleaned_text = TextCleaner.clean_text(text)
        logger.info(f"🧹 텍스트 정제 완료 - 정제된 길이: {len(cleaned_text)} 문자")
        
        # 디버그 로깅: 전처리 결과
        debug_logger.log_preprocessing(
            extractor_name="langextract",
            original_text=original_text_copy,
            preprocessed_text=cleaned_text,
            preprocessing_steps=["clean_text", "normalize_unicode", "langextract_preprocessing"]
        )
        
        if not self.is_loaded:
            self.load_model()
        
        if not self.is_loaded:
            return []
        
        try:
            # 텍스트 청킹 (긴 텍스트 처리)
            chunks = self._chunk_text(cleaned_text)
            logger.info(f"📄 텍스트 청킹 완료 - {len(chunks)}개 청크")
            
            all_keywords = []
            langextract_config = self._get_langextract_config()
            
            # 디버그 로깅: 모델 정보
            debug_logger.log_embeddings(
                extractor_name="langextract",
                model_name=f"ollama:{self.ollama_config['model']}"
            )
            
            for i, chunk in enumerate(chunks, 1):
                logger.info(f"🔄 청크 {i}/{len(chunks)} 처리 중 (길이: {len(chunk)} 문자)...")
                
                # LangExtract 프롬프트 생성
                prompt = self._create_extraction_prompt(chunk, langextract_config)
                
                # Ollama를 통한 추출 실행
                if self.langextract_client.get('mode') == 'direct_ollama':
                    # 직접 Ollama 호출 방식
                    response = self._call_ollama_direct(prompt, langextract_config)
                else:
                    # 새로운 LangExtract API 방식
                    try:
                        langextract_lib = self.langextract_client['langextract']
                        model = self.langextract_client['model']
                        
                        # 예제 데이터 가져오기
                        examples = self._get_extraction_examples()
                        
                        # 새로운 API를 사용하여 추출
                        result = langextract_lib.extract(
                            chunk,
                            prompt_description=self._create_extraction_prompt_description(),
                            examples=examples,
                            model=model,
                            max_char_buffer=langextract_config.get('max_tokens', 1000),
                            temperature=langextract_config.get('temperature', 0.3)
                        )
                        
                        # 결과를 문자열로 변환
                        response = str(result) if result else None
                        
                    except Exception as e:
                        logger.warning(f"⚠️ 새 API 실패, 직접 호출로 대체: {e}")
                        response = self._call_ollama_direct(prompt, langextract_config)
                
                if response:
                    chunk_keywords = self._parse_langextract_response(
                        response, original_text_copy, position_mapper, position_map, i
                    )
                    all_keywords.extend(chunk_keywords)
                    logger.info(f"  ✅ 청크 {i} 처리 완료 - {len(chunk_keywords)}개 키워드 추출")
                else:
                    logger.warning(f"  ⚠️ 청크 {i} 처리 실패 - 응답 없음")
            
            # 중복 제거 및 점수 정규화
            final_keywords = self._deduplicate_and_normalize(all_keywords, langextract_config)
            
            # 디버그 로깅: 최종 결과
            extraction_time = time.time() - start_time
            debug_logger.log_final_results(
                extractor_name="langextract",
                final_keywords=[{
                    "keyword": kw.text,
                    "score": kw.score,
                    "category": kw.category,
                    "start_position": kw.start_position,
                    "end_position": kw.end_position,
                    "page_number": kw.page_number,
                    "line_number": kw.line_number,
                    "context": kw.context_snippet
                } for kw in final_keywords],
                extraction_time=extraction_time,
                total_processing_time=time.time() - start_time
            )
            
            logger.info(f"✅ LangExtract 추출 완료 - {len(final_keywords)}개 키워드, 처리시간: {extraction_time:.2f}초")
            return final_keywords
            
        except Exception as e:
            logger.error(f"❌ LangExtract 추출 실패: {e}")
            
            # 실패 시에도 디버그 로깅
            extraction_time = time.time() - start_time
            debug_logger.log_final_results(
                extractor_name="langextract",
                final_keywords=[],
                extraction_time=extraction_time,
                total_processing_time=time.time() - start_time
            )
            return []
        finally:
            # 디버그 세션 저장
            debug_logger.save_debug_session()
    
    def _chunk_text(self, text: str) -> List[str]:
        """텍스트를 청크로 분할"""
        chunk_size = self.config.get('chunk_size', 2000)
        overlap = self.config.get('overlap', 200)
        
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # 문장 경계에서 자르기 시도
            if end < len(text):
                last_period = text.rfind('.', start, end)
                last_newline = text.rfind('\n', start, end)
                
                if last_period > start + chunk_size // 2:
                    end = last_period + 1
                elif last_newline > start + chunk_size // 2:
                    end = last_newline + 1
            
            chunks.append(text[start:end])
            
            if end >= len(text):
                break
                
            start = end - overlap
        
        return chunks
    
    def _create_extraction_prompt(self, text: str, config: Dict[str, Any]) -> str:
        """LangExtract용 추출 프롬프트 생성"""
        max_keywords = config.get('max_entities', 15)
        
        return f"""You are an expert keyword extraction system. Extract exactly {max_keywords} important keywords and key phrases from the given text.

For each keyword, determine:
1. text: The actual keyword or phrase
2. category: Type (technology, person, concept, organization, location, etc.)
3. confidence: How confident you are (0.0-1.0)
4. importance: high/medium/low
5. semantic_type: grammatical/semantic classification

TEXT TO ANALYZE:
{text[:1500]}

Return ONLY a valid JSON object with this exact structure:
{{
  "keywords": [
    {{
      "text": "example keyword",
      "category": "technology", 
      "confidence": 0.9,
      "importance": "high",
      "semantic_type": "noun"
    }}
  ]
}}

JSON OUTPUT:"""
    
    def _call_ollama_direct(self, prompt: str, config: Dict[str, Any]) -> str:
        """직접 Ollama API 호출"""
        import requests
        logger = logging.getLogger(__name__)
        
        try:
            payload = {
                "model": self.ollama_config['model'],
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": config.get('temperature', 0.1),
                    "num_predict": config.get('max_tokens', 1500)
                }
            }
            
            logger.debug(f"🚀 Ollama API 직접 호출 - 모델: {self.ollama_config['model']}")
            
            response = requests.post(
                f"{self.ollama_config['base_url']}/api/generate",
                json=payload,
                timeout=self.ollama_config['timeout']
            )
            
            if response.status_code == 200:
                result = response.json().get("response", "")
                logger.debug(f"✅ Ollama API 호출 성공 - 응답 길이: {len(result)} 문자")
                return result.strip()
            else:
                logger.error(f"❌ Ollama API 오류: {response.status_code}")
                return ""
                
        except Exception as e:
            logger.error(f"❌ Ollama API 직접 호출 실패: {e}")
            return ""
    
    def _parse_langextract_response(self, response: str, original_text: str, 
                                  position_mapper: PositionMapper, position_map: Dict[str, any], 
                                  chunk_id: int) -> List[Keyword]:
        """LangExtract 응답을 파싱하여 키워드 목록 생성"""
        logger = logging.getLogger(__name__)
        debug_logger = get_debug_logger()
        
        try:
            # JSON 추출
            json_str = self._extract_json_from_response(response)
            logger.debug(f"청크 {chunk_id} JSON 추출 완료: {len(json_str)} 문자")
            
            data = json.loads(json_str)
            keywords_data = data.get('keywords', [])
            
            # 디버그 로깅: 후보 생성
            raw_candidates = [item.get('text', '') for item in keywords_data if item.get('text')]
            debug_logger.log_candidate_generation(
                extractor_name="langextract",
                candidates=raw_candidates,
                generation_method="langextract_schema_based",
                params={
                    "chunk_id": chunk_id,
                    "schema_validation": True,
                    "response_length": len(response),
                    "json_length": len(json_str),
                    "parsed_items": len(keywords_data)
                }
            )
            
            results = []
            positioned_keywords = 0
            abstract_keywords = 0
            
            for i, item in enumerate(keywords_data, 1):
                keyword_text = item.get('text', '').strip()
                confidence = float(item.get('confidence', 0.7))
                category = item.get('category', 'general')
                importance = item.get('importance', 'medium')
                semantic_type = item.get('semantic_type', 'unknown')
                
                # 키워드 유효성 검사
                if not TextCleaner.is_meaningful_keyword(keyword_text):
                    logger.debug(f"⏩ 건너뜀 (유효하지 않은 키워드): '{keyword_text}'")
                    continue
                
                # 키워드 정규화
                normalized_keyword = TextCleaner.normalize_keyword(keyword_text)
                if not normalized_keyword:
                    logger.debug(f"⏩ 건너뜀 (정규화 실패): '{keyword_text}'")
                    continue
                
                # 텍스트에서 위치 찾기
                positions = self._find_keyword_positions(original_text, normalized_keyword)
                
                # 점수 계산 (신뢰도 + 중요도 가중치)
                importance_weight = {'high': 1.0, 'medium': 0.8, 'low': 0.6}.get(importance, 0.8)
                final_score = confidence * importance_weight
                
                if positions:
                    positioned_keywords += 1
                    for start_pos, end_pos in positions[:1]:  # 첫 번째 위치만 사용
                        context = self._extract_context(original_text, start_pos, end_pos)
                        page_number, line_number, column_number = position_mapper.get_position_info(start_pos, position_map)
                        
                        results.append(Keyword(
                            text=normalized_keyword,
                            score=final_score,
                            extractor=self.name,
                            category=f"{category}_{semantic_type}",
                            start_position=start_pos,
                            end_position=end_pos,
                            context_snippet=context,
                            page_number=page_number,
                            line_number=line_number,
                            column_number=column_number
                        ))
                        
                        # 상위 키워드 로깅
                        if len(results) <= 3:
                            logger.info(f"  📍 [{i}] '{keyword_text}' (신뢰도: {confidence:.3f}, 중요도: {importance}) - 위치: {start_pos}-{end_pos}")
                else:
                    abstract_keywords += 1
                    results.append(Keyword(
                        text=normalized_keyword,
                        score=final_score,
                        extractor=self.name,
                        category=f"{category}_{semantic_type}",
                        start_position=None,
                        end_position=None,
                        context_snippet=original_text[:100] + "..." if len(original_text) > 100 else original_text,
                        page_number=None,
                        line_number=None,
                        column_number=None
                    ))
                    
                    if abstract_keywords <= 3:
                        logger.info(f"  🔮 [{i}] '{keyword_text}' (신뢰도: {confidence:.3f}, 중요도: {importance}) - 추상 키워드")
            
            # 디버그 로깅: 위치 분석 결과
            keywords_with_positions = []
            for kw in results:
                kw_data = {
                    "keyword": kw.text,
                    "score": kw.score,
                    "category": kw.category,
                    "positions": []
                }
                if kw.start_position is not None:
                    kw_data["positions"].append({
                        "start": kw.start_position,
                        "end": kw.end_position,
                        "page": kw.page_number,
                        "line": kw.line_number,
                        "context": kw.context_snippet
                    })
                keywords_with_positions.append(kw_data)
            
            debug_logger.log_position_analysis(
                extractor_name="langextract",
                keywords_with_positions=keywords_with_positions,
                text=original_text,
                analysis_method="schema_based_text_search"
            )
            
            logger.debug(f"청크 {chunk_id} 키워드 처리 완료 - 총 {len(results)}개 (위치있음: {positioned_keywords}, 추상: {abstract_keywords})")
            return results
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ 청크 {chunk_id} JSON 파싱 실패: {e}")
            logger.error(f"응답 내용: {response[:200]}...")
            return []
        except Exception as e:
            logger.error(f"❌ 청크 {chunk_id} 응답 파싱 중 오류: {e}")
            return []
    
    def _extract_json_from_response(self, response: str) -> str:
        """응답에서 JSON 부분만 추출"""
        import re
        
        # 마크다운 코드 블록 제거
        response = re.sub(r'```json\s*', '', response, flags=re.IGNORECASE)
        response = re.sub(r'```\s*', '', response)
        
        # JSON 객체 찾기 (중괄호로 시작하고 끝나는 것)
        json_pattern = r'\{[^{}]*"keywords"[^{}]*\[[^\]]*\][^{}]*\}'
        matches = re.findall(json_pattern, response, re.DOTALL)
        if matches:
            return matches[0]
        
        # 더 관대한 JSON 패턴
        broad_pattern = r'\{.*?"keywords".*?\}' 
        matches = re.findall(broad_pattern, response, re.DOTALL)
        if matches:
            return matches[0]
        
        # JSON 마커 이후의 내용 찾기
        json_markers = ['JSON OUTPUT:', 'OUTPUT:', '{']
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
    
    def _find_keyword_positions(self, text: str, keyword: str) -> List[tuple]:
        """텍스트에서 키워드 위치를 찾습니다."""
        positions = []
        start = 0
        text_lower = text.lower()
        keyword_lower = keyword.lower()
        
        while True:
            pos = text_lower.find(keyword_lower, start)
            if pos == -1:
                break
            positions.append((pos, pos + len(keyword)))
            start = pos + 1
        return positions
    
    def _extract_context(self, text: str, start_pos: int, end_pos: int, context_size: int = 50) -> str:
        """키워드 주변의 컨텍스트를 추출합니다."""
        context_start = max(0, start_pos - context_size)
        context_end = min(len(text), end_pos + context_size)
        
        context = text[context_start:context_end]
        
        # 앞뒤에 생략 표시 추가
        if context_start > 0:
            context = "..." + context
        if context_end < len(text):
            context = context + "..."
            
        return context
    
    def _deduplicate_and_normalize(self, keywords: List[Keyword], config: Dict[str, Any]) -> List[Keyword]:
        """중복 제거 및 점수 정규화"""
        # 키워드 텍스트별로 그룹화
        keyword_groups = {}
        for kw in keywords:
            key = kw.text.lower()
            if key not in keyword_groups:
                keyword_groups[key] = []
            keyword_groups[key].append(kw)
        
        # 각 그룹에서 최고 점수 선택 및 점수 병합
        final_keywords = []
        for group in keyword_groups.values():
            if len(group) == 1:
                final_keywords.append(group[0])
            else:
                # 가장 높은 점수의 키워드를 기반으로 하되, 점수는 평균 사용
                best_kw = max(group, key=lambda x: x.score)
                avg_score = sum(kw.score for kw in group) / len(group)
                best_kw.score = avg_score
                final_keywords.append(best_kw)
        
        # 점수 순으로 정렬
        final_keywords.sort(key=lambda x: x.score, reverse=True)
        
        # 최대 개수 제한
        max_keywords = config.get('max_entities', 15)
        return final_keywords[:max_keywords]
    
    def _create_extraction_prompt_description(self) -> str:
        """새로운 LangExtract API용 간단한 프롬프트 설명"""
        max_keywords = self.config.get('max_keywords', 15)
        return f"Extract {max_keywords} important keywords and key phrases from the text, including their categories and confidence scores in JSON format."
    
    def _get_extraction_examples(self):
        """LangExtract API용 예제 데이터 생성"""
        from langextract.data import ExampleData
        
        examples = [
            ExampleData(
                text="Apple Inc. is a technology company based in Cupertino, California. The company develops smartphones and computers.",
                extractions={
                    "keywords": [
                        {"text": "Apple Inc.", "category": "organization", "confidence": 0.95},
                        {"text": "technology", "category": "concept", "confidence": 0.85},
                        {"text": "Cupertino", "category": "location", "confidence": 0.90},
                        {"text": "California", "category": "location", "confidence": 0.90},
                        {"text": "smartphones", "category": "technology", "confidence": 0.80},
                        {"text": "computers", "category": "technology", "confidence": 0.80}
                    ]
                }
            ),
            ExampleData(
                text="한국은행은 2024년 금리를 인상했다. 경제 전문가들은 인플레이션 억제 효과를 기대한다고 말했다.",
                extractions={
                    "keywords": [
                        {"text": "한국은행", "category": "organization", "confidence": 0.95},
                        {"text": "2024년", "category": "time", "confidence": 0.90},
                        {"text": "금리", "category": "concept", "confidence": 0.85},
                        {"text": "경제 전문가", "category": "person", "confidence": 0.80},
                        {"text": "인플레이션", "category": "concept", "confidence": 0.85}
                    ]
                }
            ),
            ExampleData(
                text="The research paper discusses machine learning algorithms for natural language processing. Deep learning models show promising results.",
                extractions={
                    "keywords": [
                        {"text": "machine learning", "category": "technology", "confidence": 0.90},
                        {"text": "algorithms", "category": "concept", "confidence": 0.80},
                        {"text": "natural language processing", "category": "technology", "confidence": 0.95},
                        {"text": "deep learning", "category": "technology", "confidence": 0.90},
                        {"text": "models", "category": "concept", "confidence": 0.75}
                    ]
                }
            )
        ]
        
        return examples