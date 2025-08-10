from typing import List, Dict, Any, Optional
from pathlib import Path
import time
from .base import KeywordExtractor, Keyword
from utils.text_cleaner import TextCleaner
from utils.position_mapper import PositionMapper
from utils.debug_logger import get_debug_logger

class SpaCyNERExtractor(KeywordExtractor):
    """spaCy NER 기반 키워드 추출기"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("spacy_ner", config)
        self.nlp = None
        self.model_name = config.get('model', 'ko_core_news_sm') if config else 'ko_core_news_sm'
        self.auto_download = config.get('auto_download', True) if config else True
    
    def load_model(self) -> bool:
        """spaCy NER 모델을 로드합니다."""
        try:
            import spacy
            import logging
            
            logger = logging.getLogger(__name__)
            logger.info(f"📦 spaCy NER 모델 '{self.model_name}' 로드 시작...")
            
            # 사용 가능한 모델 목록 확인
            available_models = ['ko_core_news_sm', 'ko_core_news_md', 'ko_core_news_lg', 'en_core_web_sm', 'en_core_web_md', 'en_core_web_lg']
            
            # 요청된 모델이 없으면 fallback 순서로 시도
            models_to_try = [self.model_name]
            if self.model_name not in models_to_try:
                # 한국어 문서라면 한국어 모델 우선
                if 'ko' in self.model_name or 'korean' in self.model_name.lower():
                    models_to_try.extend(['ko_core_news_sm', 'ko_core_news_md', 'ko_core_news_lg'])
                else:
                    models_to_try.extend(['en_core_web_sm', 'en_core_web_md', 'en_core_web_lg'])
                    
                # 마지막으로 한국어 모델들도 시도
                models_to_try.extend(['ko_core_news_sm', 'en_core_web_sm'])
            
            for model_name in models_to_try:
                try:
                    logger.info(f"  🔄 '{model_name}' 모델 로드 시도...")
                    self.nlp = spacy.load(model_name)
                    self.actual_model_name = model_name
                    self.is_loaded = True
                    logger.info(f"✅ spaCy NER 모델 '{model_name}' 로드 성공")
                    return True
                except OSError:
                    logger.warning(f"⚠️ 모델 '{model_name}'을 찾을 수 없음, 자동 다운로드 시도...")
                    
                    # 자동 다운로드가 활성화된 경우에만 다운로드 시도
                    if self.auto_download and self._download_model(model_name, logger):
                        try:
                            logger.info(f"  🔄 다운로드한 '{model_name}' 모델 로드 시도...")
                            self.nlp = spacy.load(model_name)
                            self.actual_model_name = model_name
                            self.is_loaded = True
                            logger.info(f"✅ spaCy NER 모델 '{model_name}' 다운로드 및 로드 성공")
                            return True
                        except Exception as load_error:
                            logger.error(f"❌ 다운로드한 모델 '{model_name}' 로드 실패: {load_error}")
                            continue
                    else:
                        logger.warning(f"⚠️ 모델 '{model_name}' 다운로드 실패, 다음 모델 시도...")
                        continue
                except Exception as model_error:
                    logger.warning(f"⚠️ 모델 '{model_name}' 로드 실패: {model_error}")
                    continue
            
            # 모든 모델 로드 실패
            logger.error(f"❌ 사용 가능한 spaCy 모델을 찾을 수 없음. 설치된 모델 확인 필요")
            logger.info(f"💡 모델 설치 명령어: python -m spacy download ko_core_news_sm")
            self.is_loaded = False
            return False
            
        except ImportError:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"❌ spaCy 라이브러리를 찾을 수 없음. 설치 필요: pip install spacy")
            self.is_loaded = False
            return False
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"❌ spaCy NER 모델 로드 실패: {e}")
            self.is_loaded = False
            return False
    
    def _download_model(self, model_name: str, logger) -> bool:
        """spaCy 모델을 자동으로 다운로드합니다."""
        try:
            import subprocess
            import sys
            
            logger.info(f"📥 spaCy 모델 '{model_name}' 다운로드 시작...")
            
            # spacy download 명령어 실행
            result = subprocess.run(
                [sys.executable, "-m", "spacy", "download", model_name],
                capture_output=True,
                text=True,
                timeout=300  # 5분 타임아웃
            )
            
            if result.returncode == 0:
                logger.info(f"✅ spaCy 모델 '{model_name}' 다운로드 완료")
                return True
            else:
                logger.error(f"❌ spaCy 모델 '{model_name}' 다운로드 실패: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"❌ spaCy 모델 '{model_name}' 다운로드 타임아웃 (5분 초과)")
            return False
        except Exception as e:
            logger.error(f"❌ spaCy 모델 '{model_name}' 다운로드 중 오류: {e}")
            return False
    
    def is_available(self) -> bool:
        """spaCy NER는 모델 로드 실패 시에도 패턴 기반 추출이 가능하므로 항상 사용 가능합니다."""
        return True
    
    def extract(self, text: str, file_path: Optional[Path] = None) -> List[Keyword]:
        """텍스트에서 개체명을 키워드로 추출합니다."""
        import logging
        logger = logging.getLogger(__name__)
        debug_logger = get_debug_logger()
        start_time = time.time()
        
        logger.info(f"🔍 spaCy NER 키워드 추출 시작 - 원본 텍스트 길이: {len(text)} 문자")
        
        # 디버그 로깅: 추출 시작
        debug_logger.start_extraction(
            extractor_name="spacy_ner",
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
            extractor_name="spacy_ner",
            original_text=original_text_copy,
            preprocessed_text=cleaned_text,
            preprocessing_steps=["clean_text", "normalize_whitespace", "spacy_preprocessing"]
        )
        
        if not self.is_loaded:
            logger.info("📦 spaCy NER 모델 로드 시도...")
            self.load_model()
        
        if not self.is_loaded:
            logger.warning("⚠️ spaCy NER 모델 로드 실패, 패턴 기반 추출로 fallback")
            return self._extract_entities_simple(cleaned_text, text, position_mapper, position_map)
        
        try:
            logger.info(f"🎯 spaCy 모델 '{getattr(self, 'actual_model_name', self.model_name)}'으로 NER 추출 중...")
            # 실제 spaCy NER 사용
            entities = self._extract_entities_spacy(cleaned_text, text, position_mapper, position_map)
            
            # 최종 결과 로깅
            extraction_time = time.time() - start_time
            debug_logger.log_final_results(
                extractor_name="spacy_ner",
                final_keywords=[{
                    "keyword": ent.text,
                    "score": getattr(ent, 'score', 1.0),
                    "category": ent.category,
                    "start_position": ent.start_position,
                    "end_position": ent.end_position,
                    "page_number": ent.page_number,
                    "line_number": ent.line_number,
                    "context": ent.context_snippet
                } for ent in entities],
                extraction_time=extraction_time,
                total_processing_time=time.time() - start_time
            )
            
            return entities
        except Exception as e:
            logger.error(f"❌ spaCy NER 추출 실패, 패턴 기반 추출로 fallback: {e}")
            fallback_entities = self._extract_entities_simple(cleaned_text, text, position_mapper, position_map)
            
            # 폴백 결과 로깅
            extraction_time = time.time() - start_time
            debug_logger.log_final_results(
                extractor_name="spacy_ner",
                final_keywords=[{
                    "keyword": ent.text,
                    "score": getattr(ent, 'score', 1.0),
                    "category": ent.category,
                    "start_position": ent.start_position,
                    "end_position": ent.end_position,
                    "context": ent.context_snippet
                } for ent in fallback_entities],
                extraction_time=extraction_time,
                total_processing_time=time.time() - start_time
            )
            
            return fallback_entities
        finally:
            # 디버그 세션 저장
            debug_logger.save_debug_session()
    
    def _extract_entities_spacy(self, text: str, original_text: str, position_mapper: PositionMapper, position_map: Dict[str, any]) -> List[Keyword]:
        """실제 spaCy NER을 사용한 개체명 추출"""
        import logging
        import time
        logger = logging.getLogger(__name__)
        debug_logger = get_debug_logger()
        
        try:
            # NER 설정 로깅
            max_keywords = self.config.get('max_keywords', 15) if self.config else 15
            actual_model_name = getattr(self, 'actual_model_name', self.model_name)
            logger.info(f"⚙️ spaCy NER 설정 - 모델: {actual_model_name}, 최대개체명: {max_keywords}")
            
            # 디버그 로깅: 모델 정보
            debug_logger.log_embeddings(
                extractor_name="spacy_ner",
                model_name=actual_model_name
            )
            
            # spaCy 문서 처리 시작
            start_time = time.time()
            logger.info(f"🔍 spaCy 문서 처리 시작 (텍스트 길이: {len(text)} 문자)...")
            
            doc = self.nlp(text)
            processing_time = time.time() - start_time
            logger.info(f"⚡ spaCy 문서 처리 완료 (소요시간: {processing_time:.3f}초)")
            
            results = []
            
            # 발견된 개체명들 로깅
            entities_found = []
            raw_entities = list(doc.ents)  # Convert to list for indexing
            
            for ent in raw_entities:
                entities_found.append(f"{ent.text}({ent.label_})")
            
            if entities_found:
                logger.info(f"🔍 spaCy NER 발견된 개체명 ({len(entities_found)}개): {', '.join(entities_found[:10])}{'...' if len(entities_found) > 10 else ''}")
                
                # 디버그 로깅: 발견된 개체명 후보들
                entity_candidates = [ent.text for ent in raw_entities]
                debug_logger.log_candidate_generation(
                    extractor_name="spacy_ner",
                    candidates=entity_candidates,
                    generation_method="spacy_named_entity_recognition",
                    params={
                        "model": actual_model_name,
                        "processing_time": processing_time,
                        "total_entities_found": len(raw_entities)
                    }
                )
            else:
                logger.warning("⚠️ spaCy NER에서 개체명을 찾지 못함")
                debug_logger.log_candidate_generation(
                    extractor_name="spacy_ner",
                    candidates=[],
                    generation_method="spacy_named_entity_recognition",
                    params={"model": actual_model_name, "processing_time": processing_time}
                )
                return []
            
            # 개체명 처리 시작
            logger.info(f"🔄 개체명 키워드 변환 시작 ({len(raw_entities)}개 처리 예정)...")
            
            # 개체명을 키워드로 변환 (진행률 표시)
            total_entities = len(raw_entities)
            processed_entities = 0
            valid_entities = 0
            
            for i, ent in enumerate(raw_entities, 1):
                processed_entities += 1
                
                # 진행률 로깅 (10%마다 또는 상위 3개)
                progress_percent = int((processed_entities / total_entities) * 100)
                if progress_percent % 25 == 0 or i <= 3:
                    logger.info(f"📊 개체명 처리 진행률: {processed_entities}/{total_entities} ({progress_percent}%)")
                
                # 개체명 유효성 검사 (TextCleaner 사용)
                entity_text = ent.text.strip()
                if not TextCleaner.is_meaningful_keyword(entity_text):
                    logger.debug(f"⏩ 건너뜀 (유효하지 않은 키워드): '{entity_text}'")
                    continue
                
                # 개체명 정규화
                normalized_entity = TextCleaner.normalize_keyword(entity_text)
                if not normalized_entity:
                    logger.debug(f"⏩ 건너뜀 (정규화 실패): '{entity_text}'")
                    continue
                
                # 개체명 타입별 신뢰도 설정
                confidence = self._get_entity_confidence(ent.label_)
                
                # 개체명 주변 컨텍스트 추출
                context = self._extract_context(text, ent.start_char, ent.end_char)
                
                # 페이지/줄/컬럼 번호 계산
                page_number, line_number, column_number = position_mapper.get_position_info(ent.start_char, position_map)
                
                keyword = Keyword(
                    text=normalized_entity,
                    score=confidence,
                    extractor=self.name,
                    category=ent.label_,  # PERSON, ORG, LOC, MISC 등
                    start_position=ent.start_char,
                    end_position=ent.end_char,
                    context_snippet=context,
                    page_number=page_number,
                    line_number=line_number,
                    column_number=column_number
                )
                results.append(keyword)
                valid_entities += 1
                
                # 개별 개체명 정보 로깅 (상위 5개만)
                if valid_entities <= 5:
                    logger.info(f"  📍 [{i}/{total_entities}] '{ent.text}' ({ent.label_}) - 위치: {ent.start_char}-{ent.end_char}, 신뢰도: {confidence:.3f}")
            
            # 후처리 단계 시작
            logger.info(f"🔧 후처리 시작 - 중복 제거 및 정렬 ({len(results)}개 → 최대 {max_keywords}개)")
            
            # 중복 제거 및 점수 순 정렬 (정규화된 키워드 기준으로)
            unique_results = {}
            duplicates_removed = 0
            
            for result in results:
                # 키워드를 다시 한번 정규화하여 중복 체크
                normalized_text = TextCleaner.normalize_keyword(result.text)
                key = (normalized_text.lower(), result.category)
                
                if key not in unique_results or unique_results[key].score < result.score:
                    if key in unique_results:
                        duplicates_removed += 1
                        logger.debug(f"중복 제거: '{unique_results[key].text}' -> '{result.text}' (정규화: '{normalized_text}')")
                    
                    # 결과에 정규화된 텍스트 적용
                    result.text = normalized_text
                    unique_results[key] = result
            
            if duplicates_removed > 0:
                logger.info(f"🧹 중복 제거: {duplicates_removed}개 개체명 제거")
            
            final_results = list(unique_results.values())
            final_results.sort(key=lambda x: x.score, reverse=True)
            
            # 상위 N개만 반환
            before_limit = len(final_results)
            final_results = final_results[:max_keywords]
            
            if before_limit > max_keywords:
                logger.info(f"📊 상위 키워드 제한: {before_limit}개 → {len(final_results)}개")
            
            # 개체명 타입별 통계
            category_stats = {}
            for result in final_results:
                category = result.category
                if category not in category_stats:
                    category_stats[category] = 0
                category_stats[category] += 1
            
            # 통계 로깅
            stats_text = [f"{cat}:{count}개" for cat, count in sorted(category_stats.items())]
            logger.info(f"📈 개체명 타입별 분포: {', '.join(stats_text)}")
            
            # 최종 결과 로깅
            if final_results:
                top_entities = [f"{kw.text}({kw.category},{kw.score:.3f})" for kw in final_results[:5]]
                logger.info(f"✅ spaCy NER 추출 완료 - 총 {len(final_results)}개 개체명 (처리: {processed_entities}, 유효: {valid_entities})")
                logger.info(f"🏆 상위 개체명: {', '.join(top_entities)}")
            else:
                logger.warning("⚠️ spaCy NER 처리 후 유효한 개체명이 없음")
            
            return final_results
            
        except Exception as e:
            logger.error(f"❌ spaCy NER 처리 중 오류 발생: {str(e)}")
            return []
    
    def _extract_entities_simple(self, text: str, original_text: str, position_mapper: PositionMapper, position_map: Dict[str, any]) -> List[Keyword]:
        """간단한 개체명 추출 (패턴 기반)"""
        import re
        import logging
        
        logger = logging.getLogger(__name__)
        logger.info(f"🔧 spaCy fallback - 패턴 기반 개체명 추출 시작 (텍스트 길이: {len(text)} 문자)")
        logger.info(f"⚙️ 패턴 기반 설정 - 최대개체명: {self.config.get('max_keywords', 10) if self.config else 10}")
        
        results = []
        patterns_applied = 0
        
        # 패턴 1: 숫자 + 년도 패턴 (DATE)
        patterns_applied += 1
        logger.info(f"🔍 패턴 {patterns_applied}: 년도 패턴 적용 중...")
        year_pattern = r'\d{4}년'
        years = list(re.finditer(year_pattern, text))
        year_count = 0
        for match in years:
            matched_text = match.group()
            if TextCleaner.is_meaningful_keyword(matched_text):
                normalized_text = TextCleaner.normalize_keyword(matched_text)
                if normalized_text:
                    context = self._extract_context(text, match.start(), match.end())
                    page_number, line_number, column_number = position_mapper.get_position_info(match.start(), position_map)
                    results.append(Keyword(
                        text=normalized_text,
                        score=0.8,
                        extractor=self.name,
                        category="DATE",
                        start_position=match.start(),
                        end_position=match.end(),
                        context_snippet=context,
                        page_number=page_number,
                        line_number=line_number,
                        column_number=column_number
                    ))
                    year_count += 1
        if year_count > 0:
            logger.info(f"  📅 년도 패턴: {year_count}개 발견")
        
        # 패턴 2: 숫자 + 원 패턴 (MONEY)
        patterns_applied += 1
        logger.info(f"🔍 패턴 {patterns_applied}: 금액 패턴 적용 중...")
        money_pattern = r'\d+[억만천]?원'
        money_matches = list(re.finditer(money_pattern, text))
        money_count = 0
        for match in money_matches:
            matched_text = match.group()
            if TextCleaner.is_meaningful_keyword(matched_text):
                normalized_text = TextCleaner.normalize_keyword(matched_text)
                if normalized_text:
                    context = self._extract_context(text, match.start(), match.end())
                    page_number, line_number, column_number = position_mapper.get_position_info(match.start(), position_map)
                    results.append(Keyword(
                        text=normalized_text,
                        score=0.85,
                        extractor=self.name,
                        category="MONEY",
                        start_position=match.start(),
                        end_position=match.end(),
                        context_snippet=context,
                        page_number=page_number,
                        line_number=line_number,
                        column_number=column_number
                    ))
                    money_count += 1
        if money_count > 0:
            logger.info(f"  💰 금액 패턴: {money_count}개 발견")
        
        # 패턴 3: 한국어 회사명 패턴 (ORG)
        patterns_applied += 1
        logger.info(f"🔍 패턴 {patterns_applied}: 기관명 패턴 적용 중...")
        org_pattern = r'[가-힣]{2,}(?:전자|그룹|회사|기업|산업|코퍼레이션|Corporation|Inc|Ltd)'
        orgs = list(re.finditer(org_pattern, text))
        org_count = 0
        for match in orgs:
            context = self._extract_context(text, match.start(), match.end())
            page_number, line_number, column_number = position_mapper.get_position_info(match.start(), position_map)
            results.append(Keyword(
                text=match.group(),
                score=0.75,
                extractor=self.name,
                category="ORG",
                start_position=match.start(),
                end_position=match.end(),
                context_snippet=context,
                page_number=page_number,
                line_number=line_number,
                column_number=column_number
            ))
            org_count += 1
        if org_count > 0:
            logger.info(f"  🏢 기관명 패턴: {org_count}개 발견")
        
        # 패턴 4: 지역명 패턴 (LOC)
        patterns_applied += 1
        logger.info(f"🔍 패턴 {patterns_applied}: 지역명 패턴 적용 중...")
        loc_pattern = r'[가-힣]{2,}(?:시|도|구|군|동|면|읍|특별시|광역시)'
        locs = list(re.finditer(loc_pattern, text))
        loc_count = 0
        for match in locs:
            context = self._extract_context(text, match.start(), match.end())
            page_number, line_number, column_number = position_mapper.get_position_info(match.start(), position_map)
            results.append(Keyword(
                text=match.group(),
                score=0.7,
                extractor=self.name,
                category="LOC",
                start_position=match.start(),
                end_position=match.end(),
                context_snippet=context,
                page_number=page_number,
                line_number=line_number,
                column_number=column_number
            ))
            loc_count += 1
        if loc_count > 0:
            logger.info(f"  🌍 지역명 패턴: {loc_count}개 발견")
        
        # 패턴 5: 대문자로 시작하는 영어 개체명 (MISC)
        patterns_applied += 1
        logger.info(f"🔍 패턴 {patterns_applied}: 영어 개체명 패턴 적용 중...")
        english_entity_pattern = r'\b[A-Z][A-Za-z]{2,}\b'
        english_entities = list(re.finditer(english_entity_pattern, text))
        english_count = 0
        for match in english_entities:
            # 일반적인 영어 단어는 제외
            word = match.group()
            if word.lower() not in {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'this', 'that', 'with', 'from', 'they', 'have', 'more', 'will', 'been', 'were', 'said', 'each', 'which', 'their', 'time', 'would', 'there', 'what', 'about', 'when', 'after', 'first', 'other', 'many', 'some', 'very', 'come', 'could', 'make', 'know', 'just', 'into', 'over', 'think', 'also', 'back', 'only', 'good', 'work', 'life', 'way', 'even', 'new', 'want', 'because', 'any', 'these', 'give', 'day', 'most', 'us'}:
                context = self._extract_context(text, match.start(), match.end())
                page_number, line_number, column_number = position_mapper.get_position_info(match.start(), position_map)
                results.append(Keyword(
                    text=word,
                    score=0.6,
                    extractor=self.name,
                    category="MISC",
                    start_position=match.start(),
                    end_position=match.end(),
                    context_snippet=context,
                    page_number=page_number,
                    line_number=line_number,
                    column_number=column_number
                ))
                english_count += 1
        if english_count > 0:
            logger.info(f"  🔤 영어 개체명 패턴: {english_count}개 발견")
        
        logger.info(f"📊 패턴 매칭 완료 - {patterns_applied}개 패턴 적용, 총 {len(results)}개 후보 발견")
        
        # 중복 제거 및 점수 순 정렬 (정규화된 키워드 기준으로)
        unique_results = {}
        duplicates_removed = 0
        
        for result in results:
            # 키워드를 정규화하여 중복 체크
            normalized_text = TextCleaner.normalize_keyword(result.text)
            key = (normalized_text.lower(), result.category)
            
            if key not in unique_results or unique_results[key].score < result.score:
                if key in unique_results:
                    duplicates_removed += 1
                    logger.debug(f"패턴 기반 중복 제거: '{unique_results[key].text}' -> '{result.text}' (정규화: '{normalized_text}')")
                
                # 결과에 정규화된 텍스트 적용
                result.text = normalized_text
                unique_results[key] = result
        
        if duplicates_removed > 0:
            logger.info(f"🧹 패턴 기반 중복 제거: {duplicates_removed}개 개체명 제거")
        
        final_results = list(unique_results.values())
        final_results.sort(key=lambda x: x.score, reverse=True)
        
        # 상위 N개만 반환
        max_keywords = self.config.get('max_keywords', 10)
        final_results = final_results[:max_keywords]
        
        # 패턴 기반 추출 결과 로깅
        if final_results:
            pattern_entities = [f"{kw.text}({kw.category},{kw.score:.3f})" for kw in final_results[:5]]
            logger.info(f"🔧 패턴 기반 추출 완료 - {len(final_results)}개 개체명, 상위: {', '.join(pattern_entities)}")
        else:
            logger.warning("⚠️ 패턴 기반 추출에서도 개체명을 찾지 못함")
        
        return final_results
    
    def _find_entity_positions(self, text: str, entity: str) -> List[tuple]:
        """텍스트에서 개체명 위치를 찾습니다."""
        positions = []
        start = 0
        while True:
            pos = text.find(entity, start)
            if pos == -1:
                break
            positions.append((pos, pos + len(entity)))
            start = pos + 1
        return positions
    
    def _get_entity_confidence(self, label: str) -> float:
        """개체명 타입별 신뢰도를 반환합니다."""
        confidence_map = {
            # 영어 spaCy 모델 레이블
            "PERSON": 0.9,
            "ORG": 0.85,
            "LOC": 0.8,
            "DATE": 0.75,
            "TIME": 0.7,
            "MONEY": 0.85,
            "PERCENT": 0.8,
            "MISC": 0.6,
            # 한국어 spaCy 모델 레이블 (ko_core_news_sm)
            "PS": 0.85,  # Person (인명)
            "LC": 0.8,   # Location (지명)
            "OG": 0.85,  # Organization (기관명)
            "DT": 0.75,  # Date/Time (날짜/시간)
            "TI": 0.7,   # Time (시간)
            "QT": 0.8,   # Quantity (수량)
            "CV": 0.75,  # Civilization (문명)
            "AM": 0.7,   # Animal (동물)
            "PT": 0.7,   # Plant (식물)
            "MT": 0.7,   # Material (물질)
            "TR": 0.7,   # Term (용어)
            "EV": 0.75,  # Event (사건)
            "AF": 0.7,   # Artifact (인공물)
            "FD": 0.75,  # Field (분야)
            "TM": 0.7    # Theory/Method (이론/방법)
        }
        return confidence_map.get(label, 0.65)
    
    def _extract_context(self, text: str, start_pos: int, end_pos: int, context_size: int = 50) -> str:
        """개체명 주변의 컨텍스트를 추출합니다."""
        context_start = max(0, start_pos - context_size)
        context_end = min(len(text), end_pos + context_size)
        
        context = text[context_start:context_end]
        
        # 앞뒤에 생략 표시 추가
        if context_start > 0:
            context = "..." + context
        if context_end < len(text):
            context = context + "..."
            
        return context