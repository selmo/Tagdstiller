from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import time
import requests
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

class LLMExtractor(KeywordExtractor):
    """LLM 기반 키워드 추출기 (Ollama/OpenAI/Gemini)"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, db_session = None):
        super().__init__("llm", config)
        self.client = None
        self.provider = config.get('provider', 'ollama') if config else 'ollama'
        self.model_name = config.get('model', 'llama3.2') if config else 'llama3.2'
        self.base_url = config.get('base_url', 'http://localhost:11434') if config else 'http://localhost:11434'
        
        # 프롬프트 설정 초기화
        self.prompt_config = PromptConfig(config, db_session)
        
        # LangChain Ollama 인스턴스 초기화
        self.ollama_client = None
    
    def load_model(self) -> bool:
        """LLM 클라이언트를 초기화합니다."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"LLM 추출기 로드 시작: provider={self.provider}, model={self.model_name}, base_url={self.base_url}")
            
            if self.provider == 'ollama':
                # LangChain Ollama 클라이언트 초기화
                try:
                    if not OllamaLLM:
                        raise ImportError("LangChain Ollama not available")
                    
                    self.ollama_client = OllamaLLM(
                        base_url=self.base_url,
                        model=self.model_name,
                        timeout=self.config.get('timeout', 30) if self.config else 30
                    )
                    
                    # 간단한 테스트 쿼리로 연결 확인
                    logger.info(f"LangChain Ollama 연결 테스트 중...")
                    test_response = self.ollama_client.invoke("Hello")
                    logger.info(f"✅ LangChain Ollama 연결 성공: {len(test_response)} 문자 응답")
                    
                    self.is_loaded = True
                    logger.info(f"✅ LLM 추출기 로드 성공: {self.model_name}")
                    
                except Exception as e:
                    logger.error(f"❌ LangChain Ollama 초기화 실패: {e}")
                    
                    # 폴백: 기존 방식으로 연결 확인
                    logger.info("기존 방식으로 Ollama 연결 확인 중...")
                    response = requests.get(f"{self.base_url}/api/tags", timeout=5)
                    logger.info(f"Ollama 응답 상태: {response.status_code}")
                    
                    if response.status_code == 200:
                        models = response.json().get("models", [])
                        model_names = [m['name'] for m in models]
                        logger.info(f"사용 가능한 Ollama 모델: {model_names}")
                        
                        # 모델이 존재하는지 확인
                        model_found = any(model["name"].startswith(self.model_name) for model in models)
                        logger.info(f"모델 '{self.model_name}' 검색 결과: {model_found}")
                        
                        if model_found:
                            # LangChain 클라이언트 다시 시도
                            try:
                                self.ollama_client = OllamaLLM(
                                    base_url=self.base_url,
                                    model=self.model_name,
                                    timeout=self.config.get('timeout', 30) if self.config else 30
                                )
                                self.is_loaded = True
                                logger.info(f"✅ LLM 추출기 로드 성공 (재시도): {self.model_name}")
                            except Exception as retry_e:
                                logger.error(f"❌ LangChain 재시도 실패: {retry_e}")
                                self.is_loaded = False
                        else:
                            logger.error(f"❌ 모델 '{self.model_name}'을 찾을 수 없음. 사용 가능한 모델: {model_names}")
                            self.is_loaded = False
                    else:
                        logger.error(f"❌ Ollama 서버 연결 실패: {self.base_url} (상태: {response.status_code})")
                        self.is_loaded = False
            
            elif self.provider == 'openai':
                # OpenAI는 REST 호출 기반. API 키만 확인
                import os
                api_key = self.config.get('api_key') if self.config else None
                if not api_key:
                    api_key = os.environ.get('OPENAI_API_KEY')
                if not api_key:
                    logger.error("❌ OPENAI_API_KEY가 설정되지 않았습니다")
                    self.is_loaded = False
                else:
                    self.is_loaded = True
                    logger.info("✅ OpenAI provider 준비 완료")
            elif self.provider == 'gemini':
                # Gemini도 REST 호출 기반. API 키 확인
                import os
                api_key = self.config.get('api_key') if self.config else None
                if not api_key:
                    api_key = os.environ.get('GEMINI_API_KEY')
                if not api_key:
                    logger.error("❌ GEMINI_API_KEY가 설정되지 않았습니다")
                    self.is_loaded = False
                else:
                    self.is_loaded = True
                    logger.info("✅ Gemini provider 준비 완료")
            
            logger.info(f"LLM 추출기 최종 상태: is_loaded={self.is_loaded}")
            return self.is_loaded
        except Exception as e:
            logger.error(f"❌ LLM 추출기 초기화 실패: {e}")
            self.is_loaded = False
            return False
    
    def extract(self, text: str, file_path: Optional[Path] = None) -> List[Keyword]:
        """LLM을 사용하여 키워드를 추출합니다."""
        import logging
        logger = logging.getLogger(__name__)
        debug_logger = get_debug_logger()
        start_time = time.time()
        
        logger.info(f"🔍 LLM 키워드 추출 시작 - 원본 텍스트 길이: {len(text)} 문자")
        
        # 디버그 로깅: 추출 시작
        debug_logger.start_extraction(
            extractor_name="llm",
            file_info={"filename": str(file_path) if file_path else "unknown", "id": None},
            text=text,
            config=self.config
        )
        
        # 위치 매핑 생성
        position_mapper = PositionMapper()
        position_map = position_mapper.create_position_map(text, file_path)
        logger.info(f"📍 위치 매핑 생성 완료 - 총 {position_map['total_pages']}페이지, {position_map['total_lines']}줄")
        
        # 텍스트 전처리
        original_text_copy = text  # 원본 보관
        cleaned_text = TextCleaner.clean_text(text)
        logger.info(f"🧹 텍스트 정제 완료 - 정제된 길이: {len(cleaned_text)} 문자")
        
        # 디버그 로깅: 전처리 결과
        debug_logger.log_preprocessing(
            extractor_name="llm",
            original_text=original_text_copy,
            preprocessed_text=cleaned_text,
            preprocessing_steps=["clean_text", "normalize_unicode", "llm_preprocessing"]
        )
        
        if not self.is_loaded:
            self.load_model()
        
        if not self.is_loaded:
            return []
        
        try:
            prompt = self._create_extraction_prompt(cleaned_text)
            
            # 디버그 로깅: 모델 정보 및 프롬프트
            debug_logger.log_embeddings(
                extractor_name="llm",
                model_name=f"{self.provider}:{self.model_name}"
            )
            
            logger.info(f"🎯 LLM '{self.provider}:{self.model_name}'으로 키워드 추출 중...")
            
            if self.provider == 'ollama':
                response, request_data, response_data = self._call_ollama_langchain(prompt)
                # 프롬프트/응답 파일 저장 및 로그 기록 (JSON 포함)
                log_prompt_and_response(
                    label="keyword_extraction",
                    provider=self.provider,
                    model=self.model_name,
                    prompt=prompt,
                    response=response or "",
                    logger=logger,
                    meta={
                        "base_url": self.base_url,
                        "file_path": str(file_path) if file_path else None,
                        "config_max_keywords": self.config.get('max_keywords') if self.config else None,
                        "langchain_version": True,
                    },
                    request_data=request_data,
                    response_data=response_data,
                )
                if response:
                    keywords = self._parse_llm_response(response, text, position_mapper, position_map)
                    
                    # 디버그 로깅: 최종 결과
                    extraction_time = time.time() - start_time
                    debug_logger.log_final_results(
                        extractor_name="llm",
                        final_keywords=[{
                            "keyword": kw.text,
                            "score": kw.score,
                            "category": kw.category,
                            "start_position": kw.start_position,
                            "end_position": kw.end_position,
                            "page_number": kw.page_number,
                            "line_number": kw.line_number,
                            "context": kw.context_snippet
                        } for kw in keywords],
                        extraction_time=extraction_time,
                        total_processing_time=time.time() - start_time
                    )
                    
                    return keywords
            elif self.provider == 'openai':
                response = self._call_openai(prompt)
                # 프롬프트/응답 파일 저장 및 로그 기록
                log_prompt_and_response(
                    label="keyword_extraction",
                    provider=self.provider,
                    model=self.model_name,
                    prompt=prompt,
                    response=response or "",
                    logger=logger,
                    meta={
                        "file_path": str(file_path) if file_path else None,
                        "config_max_keywords": self.config.get('max_keywords') if self.config else None,
                    },
                )
                if response:
                    keywords = self._parse_llm_response(response, text, position_mapper, position_map)
                    
                    # 디버그 로깅: 최종 결과
                    extraction_time = time.time() - start_time
                    debug_logger.log_final_results(
                        extractor_name="llm",
                        final_keywords=[{
                            "keyword": kw.text,
                            "score": kw.score,
                            "category": kw.category,
                            "start_position": kw.start_position,
                            "end_position": kw.end_position,
                            "context": kw.context_snippet
                        } for kw in keywords],
                        extraction_time=extraction_time,
                        total_processing_time=time.time() - start_time
                    )
                    
                    return keywords
            elif self.provider == 'gemini':
                response = self._call_gemini(prompt)
                # 프롬프트/응답 파일 저장 및 로그 기록
                log_prompt_and_response(
                    label="keyword_extraction",
                    provider=self.provider,
                    model=self.model_name,
                    prompt=prompt,
                    response=response or "",
                    logger=logger,
                    meta={
                        "file_path": str(file_path) if file_path else None,
                        "config_max_keywords": self.config.get('max_keywords') if self.config else None,
                    },
                )
                if response:
                    keywords = self._parse_llm_response(response, text, position_mapper, position_map)
                    
                    # 디버그 로깅: 최종 결과
                    extraction_time = time.time() - start_time
                    debug_logger.log_final_results(
                        extractor_name="llm",
                        final_keywords=[{
                            "keyword": kw.text,
                            "score": kw.score,
                            "category": kw.category,
                            "start_position": kw.start_position,
                            "end_position": kw.end_position,
                            "context": kw.context_snippet
                        } for kw in keywords],
                        extraction_time=extraction_time,
                        total_processing_time=time.time() - start_time
                    )
                    
                    return keywords
            
            # 실패 시 빈 리스트 반환
            empty_result = []
            extraction_time = time.time() - start_time
            debug_logger.log_final_results(
                extractor_name="llm",
                final_keywords=[],
                extraction_time=extraction_time,
                total_processing_time=time.time() - start_time
            )
            return empty_result
        except Exception as e:
            logger.error(f"❌ LLM 추출 실패: {e}")
            
            # 실패 시에도 디버그 로깅
            extraction_time = time.time() - start_time
            debug_logger.log_final_results(
                extractor_name="llm",
                final_keywords=[],
                extraction_time=extraction_time,
                total_processing_time=time.time() - start_time
            )
            return []
        finally:
            # 디버그 세션 저장
            debug_logger.save_debug_session()
    
    
    def _create_extraction_prompt(self, text: str) -> str:
        """키워드 추출을 위한 프롬프트를 생성합니다."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # 템플릿 이름 결정
            template_name = self.prompt_config.get_template_name('keyword_extraction')
            
            # 템플릿 변수 생성 (텍스트 길이 제한을 15000자로 증가)
            variables = self.prompt_config.get_template_variables('keyword_extraction', text[:15000])
            
            # 프롬프트 생성
            prompt = get_prompt_template('keyword_extraction', template_name, **variables)
            
            logger.debug(f"🎯 프롬프트 템플릿 사용: keyword_extraction.{template_name}")
            return prompt
            
        except Exception as e:
            logger.warning(f"⚠️ 프롬프트 템플릿 사용 실패, 기본 프롬프트 사용: {e}")
            
            # 폴백: 기존 방식
            max_keywords = min(self.config.get('max_keywords', 20), 8)
            return f"""You are a keyword extraction system. Extract exactly {max_keywords} important keywords from the text below.

Text: {text[:15000]}

Return ONLY a JSON array with this exact format (no other text):
[{{"keyword":"word1","score":0.9,"category":"noun"}},{{"keyword":"word2","score":0.8,"category":"technology"}}]

Output:"""
    
    def _call_ollama_langchain(self, prompt: str) -> tuple[str, dict, dict]:
        """LangChain을 사용하여 Ollama API를 호출합니다. (JSON 데이터 포함 반환)"""
        import logging
        logger = logging.getLogger(__name__)
        debug_logger = get_debug_logger()
        
        try:
            if not self.ollama_client:
                logger.error("❌ LangChain Ollama 클라이언트가 초기화되지 않음")
                return "", {}, {}
            
            # 프롬프트 설정에서 LLM 파라미터 가져오기
            llm_params = self.prompt_config.get_llm_params('keyword_extraction')
            
            # 요청 데이터 구성 (LangChain에서 사용될 데이터)
            request_data = {
                "model": self.model_name,
                "prompt": prompt,
                "base_url": self.base_url,
                "options": llm_params,
                "langchain_version": True
            }
            
            logger.info(f"🚀 LangChain Ollama 호출 시작 - 모델: {self.model_name}")
            logger.debug(f"LLM 파라미터: {llm_params}")
            
            # LangChain을 통해 Ollama 호출
            start_time = time.time()
            result = self.ollama_client.invoke(prompt)
            call_duration = time.time() - start_time
            
            # 응답 데이터 구성
            response_data = {
                "response": result,
                "model": self.model_name,
                "created_at": time.time(),
                "done": True,
                "total_duration": call_duration * 1e9,  # nanoseconds (Ollama API 호환)
                "load_duration": 0,
                "prompt_eval_count": len(prompt.split()),
                "eval_count": len(result.split()) if result else 0,
                "langchain_wrapper": True
            }
            
            logger.info(f"✅ LangChain Ollama 호출 성공 - 응답 길이: {len(result)} 문자, 소요시간: {call_duration:.2f}초")
            logger.info(f"🔍 JSON 데이터 생성 확인 - request_data: {bool(request_data)}, response_data: {bool(response_data)}")
            
            # 디버그 로깅: LLM 응답 분석
            debug_logger.log_algorithm_application(
                extractor_name="llm",
                algorithm=f"{self.provider}_langchain_generation",
                input_candidates=[("prompt", len(prompt))],  # 프롬프트를 입력으로 간주
                output_keywords=[("response", len(result))],  # 응답을 출력으로 간주
                algorithm_params={
                    "provider": self.provider,
                    "model": self.model_name,
                    "langchain_version": True,
                    "call_duration": call_duration,
                    **llm_params
                }
            )
            
            return result.strip(), request_data, response_data
                
        except Exception as e:
            logger.error(f"❌ LangChain Ollama 호출 실패: {e}")
            # 폴백: 기존 requests 방식으로 시도
            logger.info("기존 requests 방식으로 폴백 시도...")
            return self._call_ollama_fallback(prompt)
    
    def _call_ollama_fallback(self, prompt: str) -> tuple[str, dict, dict]:
        """기존 requests 방식의 Ollama API 호출 (폴백용). JSON 데이터 포함 반환."""
        import logging
        logger = logging.getLogger(__name__)
        debug_logger = get_debug_logger()
        
        try:
            # 프롬프트 설정에서 LLM 파라미터 가져오기
            llm_params = self.prompt_config.get_llm_params('keyword_extraction')
            
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": llm_params
            }
            
            logger.info(f"🚀 Ollama API 폴백 호출 시작 - 모델: {self.model_name}")
            
            timeout = self.config.get('timeout', 30) if self.config else 30
            response = requests.post(
                f"{self.base_url}/api/generate", 
                json=payload, 
                timeout=timeout
            )
            
            if response.status_code == 200:
                response_json = response.json()
                result = response_json.get("response", "")
                logger.info(f"✅ Ollama API 폴백 성공 - 응답 길이: {len(result)} 문자")
                
                # 디버그 로깅: LLM 응답 분석
                debug_logger.log_algorithm_application(
                    extractor_name="llm",
                    algorithm=f"{self.provider}_fallback_generation",
                    input_candidates=[("prompt", len(prompt))],  # 프롬프트를 입력으로 간주
                    output_keywords=[("response", len(result))],  # 응답을 출력으로 간주
                    algorithm_params={
                        "provider": self.provider,
                        "model": self.model_name,
                        "fallback_mode": True,
                        "timeout": timeout,
                        **llm_params
                    }
                )
                
                return result.strip(), payload, response_json
            else:
                logger.error(f"❌ Ollama API 폴백 오류: {response.status_code} - {response.text}")
                return "", payload, {"error": response.text, "status_code": response.status_code}
                
        except requests.exceptions.Timeout:
            logger.error(f"❌ Ollama API 폴백 타임아웃 ({timeout}초)")
            return "", {}, {"error": "timeout", "timeout": timeout}
        except Exception as e:
            logger.error(f"❌ Ollama API 폴백 호출 실패: {e}")
            return "", {}, {"error": str(e)}
    
    def _call_openai(self, prompt: str) -> str:
        """OpenAI Chat Completions REST 호출."""
        import os
        base_url = (self.config or {}).get('base_url') or os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        api_key = (self.config or {}).get('api_key') or os.environ.get('OPENAI_API_KEY')
        if not api_key:
            return ""
        model = self.model_name or 'gpt-3.5-turbo'
        max_tokens = (self.config or {}).get('max_tokens', 1000)
        temperature = (self.config or {}).get('temperature', 0.2)
        url = f"{base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=(self.config or {}).get('timeout', 120))
            if r.status_code != 200:
                return ""
            data = r.json()
            return data.get('choices', [{}])[0].get('message', {}).get('content', '')
        except Exception:
            return ""

    def _call_gemini(self, prompt: str) -> str:
        """Google Generative Language (Gemini) REST 호출."""
        import os
        base_url = (self.config or {}).get('base_url') or os.environ.get('GEMINI_API_BASE', 'https://generativelanguage.googleapis.com')
        api_key = (self.config or {}).get('api_key') or os.environ.get('GEMINI_API_KEY')
        if not api_key:
            return ""
        model = self.model_name or 'models/gemini-1.5-pro'
        max_tokens = (self.config or {}).get('max_tokens', 1000)
        temperature = (self.config or {}).get('temperature', 0.2)
        url = f"{base_url}/v1beta/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        try:
            r = requests.post(url, json=payload, timeout=(self.config or {}).get('timeout', 120))
            if r.status_code != 200:
                return ""
            data = r.json()
            candidates = data.get('candidates', [])
            if not candidates:
                return ""
            parts = candidates[0].get('content', {}).get('parts', [])
            return "\n".join(part.get('text', '') for part in parts if isinstance(part, dict))
        except Exception:
            return ""
    
    def _parse_llm_response(self, response: str, original_text: str, position_mapper: PositionMapper, position_map: Dict[str, any]) -> List[Keyword]:
        """LLM 응답을 파싱하여 키워드 목록을 생성합니다."""
        import logging
        logger = logging.getLogger(__name__)
        debug_logger = get_debug_logger()
        
        try:
            # JSON 부분만 추출 시도
            json_str = self._extract_json_from_response(response)
            logger.info(f"🔍 LLM 응답 파싱 시작 - JSON 추출 완료: {len(json_str)} 문자")
            
            data = json.loads(json_str)
            results = []
            
            # 디버그 로깅: 후보 생성 (LLM이 생성한 키워드들)
            raw_candidates = [item.get('keyword', '') for item in data if item.get('keyword')]
            debug_logger.log_candidate_generation(
                extractor_name="llm",
                candidates=raw_candidates,
                generation_method="llm_generation",
                params={
                    "provider": self.provider,
                    "model": self.model_name,
                    "response_length": len(response),
                    "json_length": len(json_str),
                    "parsed_items": len(data)
                }
            )
            
            logger.info(f"📝 LLM에서 {len(data)}개 키워드 후보 추출됨")
            
            positioned_keywords = 0
            abstract_keywords = 0
            
            for i, item in enumerate(data, 1):
                keyword = item.get('keyword', '')
                score = item.get('score', 0.0)
                category = item.get('category', 'general')
                
                # 키워드 유효성 검사
                if not TextCleaner.is_meaningful_keyword(keyword):
                    logger.debug(f"⏩ 건너뜀 (유효하지 않은 키워드): '{keyword}'")
                    continue
                
                # 키워드 정규화
                normalized_keyword = TextCleaner.normalize_keyword(keyword)
                if not normalized_keyword:
                    logger.debug(f"⏩ 건너뜀 (정규화 실패): '{keyword}'")
                    continue
                
                # 텍스트에서 위치 찾기
                positions = self._find_keyword_positions(original_text, normalized_keyword)
                
                if positions:
                    positioned_keywords += 1
                    for start_pos, end_pos in positions[:1]:
                        context = self._extract_context(original_text, start_pos, end_pos)
                        page_number, line_number, column_number = position_mapper.get_position_info(start_pos, position_map)
                        results.append(Keyword(
                            text=normalized_keyword,
                            score=score,
                            extractor=self.name,
                            category=category,
                            start_position=start_pos,
                            end_position=end_pos,
                            context_snippet=context,
                            page_number=page_number,
                            line_number=line_number,
                            column_number=column_number
                        ))
                        
                        # 개별 키워드 위치 로깅 (상위 3개만)
                        if len(results) <= 3:
                            logger.info(f"  📍 [{i}/{len(data)}] '{keyword}' (점수: {score:.3f}) - 위치: {start_pos}-{end_pos}, 컨텍스트: '{context[:50]}{'...' if len(context) > 50 else ''}'")
                else:
                    abstract_keywords += 1
                    results.append(Keyword(
                        text=normalized_keyword,
                        score=score,
                        extractor=self.name,
                        category=category,
                        start_position=None,
                        end_position=None,
                        context_snippet=original_text[:100] + "..." if len(original_text) > 100 else original_text,
                        page_number=None,
                        line_number=None,
                        column_number=None
                    ))
                    
                    # 추상 키워드 로깅 (상위 3개만)
                    if abstract_keywords <= 3:
                        logger.info(f"  🔮 [{i}/{len(data)}] '{keyword}' (점수: {score:.3f}) - 추상 키워드 (텍스트에서 정확한 위치 없음)")
            
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
                extractor_name="llm",
                keywords_with_positions=keywords_with_positions,
                text=original_text,
                analysis_method="simple_text_search"
            )
            
            # 최종 키워드 통계 로깅
            logger.info(f"📋 LLM 키워드 처리 완료 - 총 {len(results)}개 (위치있음: {positioned_keywords}, 추상: {abstract_keywords})")
            
            # 최종 결과 로깅
            if results:
                top_keywords = [f"{kw.text}({kw.category},{kw.score:.3f})" for kw in results[:5]]
                logger.info(f"✅ LLM 추출 완료 - {len(results)}개 키워드, 상위: {', '.join(top_keywords)}")
            else:
                logger.warning("⚠️ LLM 처리 후 유효한 키워드가 없음")
            
            return results
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
        response = re.sub(r'```json\s*', '', response)
        response = re.sub(r'```\s*', '', response)
        
        # 대괄호로 시작하고 끝나는 JSON 배열 찾기
        json_pattern = r'\[\s*\{.*?\}\s*\]'
        matches = re.findall(json_pattern, response, re.DOTALL)
        if matches:
            # 가장 완전한 JSON 배열 선택
            longest_match = max(matches, key=len)
            return longest_match
        
        # 단일 JSON 객체를 배열로 변환
        object_pattern = r'\{[^{}]*"keyword"[^{}]*\}'
        objects = re.findall(object_pattern, response, re.DOTALL)
        if objects:
            return '[' + ','.join(objects) + ']'
        
        # JSON 마커 이후의 내용 찾기
        json_markers = ['Output:', 'JSON:', 'json:', '[', '{']
        for marker in json_markers:
            if marker in response:
                json_part = response[response.find(marker):].strip()
                if marker in ['Output:', 'JSON:', 'json:']:
                    json_part = json_part[len(marker):].strip()
                
                # 첫 번째 [ 부터 마지막 ] 까지 추출
                start_idx = json_part.find('[')
                if start_idx != -1:
                    end_idx = json_part.rfind(']')
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
