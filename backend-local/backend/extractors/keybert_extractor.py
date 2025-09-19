from typing import List, Dict, Any, Optional
from pathlib import Path
import re
import time
import numpy as np
from .base import KeywordExtractor, Keyword
from utils.text_cleaner import TextCleaner
from utils.position_mapper import PositionMapper
from utils.debug_logger import get_debug_logger

class KeyBERTExtractor(KeywordExtractor):
    """KeyBERT 기반 키워드 추출기"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, db_session = None):
        super().__init__("keybert", config)
        self.model = None
        self.model_name = config.get('model', 'all-MiniLM-L6-v2') if config else 'all-MiniLM-L6-v2'
    
    def load_model(self) -> bool:
        """KeyBERT 모델을 로드합니다."""
        try:
            from keybert import KeyBERT
            import logging
            
            logger = logging.getLogger(__name__)
            
            # 이미 로드된 모델이 있지만 다른 모델을 요청하는 경우 재로드
            if self.model is not None and hasattr(self.model, '_model_name'):
                if self.model._model_name != self.model_name:
                    logger.info(f"🔄 KeyBERT 모델 변경: {self.model._model_name} -> {self.model_name}")
                    self.model = None
                    self.is_loaded = False
            
            if not self.is_loaded or self.model is None:
                logger.info(f"📥 KeyBERT 모델 '{self.model_name}' 로드 시작...")
                self.model = KeyBERT(model=self.model_name)
                # 로드된 모델 이름을 저장 (차후 비교용)
                self.model._model_name = self.model_name
                self.is_loaded = True
                logger.info(f"✅ KeyBERT 모델 '{self.model_name}' 로드 성공")
            
            return True
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"❌ KeyBERT 모델 '{self.model_name}' 로드 실패: {e}")
            self.is_loaded = False
            return False
    
    def extract(self, text: str, file_path: Optional[Path] = None) -> List[Keyword]:
        """텍스트에서 키워드를 추출합니다."""
        import logging
        logger = logging.getLogger(__name__)
        debug_logger = get_debug_logger()
        start_time = time.time()
        
        logger.info(f"🔍 KeyBERT 키워드 추출 시작 - 원본 텍스트 길이: {len(text)} 문자")
        
        # 디버그 로깅: 추출 시작
        debug_logger.start_extraction(
            extractor_name="keybert",
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
            extractor_name="keybert",
            original_text=original_text_copy,
            preprocessed_text=cleaned_text,
            preprocessing_steps=["clean_text", "remove_extra_whitespace", "normalize_unicode"]
        )
        
        if not self.is_loaded:
            logger.info("📦 KeyBERT 모델 로드 시도...")
            self.load_model()
        
        if not self.is_loaded:
            logger.warning("⚠️ KeyBERT 모델 로드 실패, 간단한 추출로 fallback")
            # KeyBERT 로드 실패 시 간단한 추출로 fallback
            return self._extract_keywords_simple(cleaned_text)
        
        try:
            logger.info(f"🎯 KeyBERT 모델 '{self.model_name}'으로 키워드 추출 중...")
            # 실제 KeyBERT를 사용한 키워드 추출
            keywords = self._extract_keywords_keybert(cleaned_text, text, position_mapper, position_map)
            
            # 추출된 키워드 로깅
            extraction_time = time.time() - start_time
            if keywords:
                top_keywords = sorted(keywords, key=lambda x: x.score, reverse=True)[:5]
                keyword_summary = [f"{kw.text}({kw.score:.3f})" for kw in top_keywords]
                logger.info(f"✅ KeyBERT 추출 완료 - {len(keywords)}개 키워드, 상위: {', '.join(keyword_summary)}")
            else:
                logger.warning("⚠️ KeyBERT에서 키워드를 추출하지 못함")
            
            # 디버그 로깅: 최종 결과
            debug_logger.log_final_results(
                extractor_name="keybert",
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
        except Exception as e:
            logger.error(f"❌ KeyBERT 추출 실패, 간단한 추출로 fallback: {e}")
            return self._extract_keywords_simple(cleaned_text)
    
    def is_available(self) -> bool:
        """KeyBERT는 모델 로드 실패 시에도 fallback 추출이 가능하므로 항상 사용 가능합니다."""
        return True
    
    def _extract_keywords_simple(self, text: str) -> List[Keyword]:
        """간단한 키워드 추출 (실제 텍스트 기반)"""
        import re
        import logging
        from collections import Counter
        
        logger = logging.getLogger(__name__)
        logger.info(f"🔧 KeyBERT fallback - 간단한 키워드 추출 시작 (텍스트 길이: {len(text)} 문자)")
        
        # 한국어 명사 패턴과 영어 단어 패턴을 결합
        korean_pattern = r'[가-힣]{2,}'  # 2글자 이상 한글
        english_pattern = r'[A-Za-z]{3,}'  # 3글자 이상 영어
        
        # 유효한 단어 추출 (TextCleaner 사용)
        valid_words = TextCleaner.extract_valid_words(text, min_length=2)
        
        # 빈도 계산
        word_freq = Counter(valid_words)
        
        # 상위 키워드 선택
        max_keywords = self.config.get('max_keywords', 10)
        top_words = word_freq.most_common(max_keywords)
        
        # 간단한 추출 결과 로깅
        if top_words:
            simple_keywords = [f"{word}({freq})" for word, freq in top_words[:5]]
            logger.info(f"🔧 간단한 추출 결과 ({len(top_words)}개): {', '.join(simple_keywords)}")
        else:
            logger.warning("⚠️ 간단한 추출에서도 키워드를 찾지 못함")
        
        results = []
        for word, freq in top_words:
            # 점수 계산 (빈도 기반, 0-1 정규화)
            score = min(1.0, freq / max(1, len(word_freq)) * 10)  # 빈도를 0-1로 정규화
            
            # 텍스트에서 위치 찾기
            positions = self._find_keyword_positions(text, word)
            if positions:
                start_pos, end_pos = positions[0]  # 첫 번째 위치
                context = self._extract_context(text, start_pos, end_pos)
                
                results.append(Keyword(
                    text=word,
                    score=score,
                    extractor=self.name,
                    category="keyword",
                    start_position=start_pos,
                    end_position=end_pos,
                    context_snippet=context,
                    page_number=None,
                    line_number=None,
                    column_number=None
                ))
        
        logger.info(f"✅ 간단한 추출 완료 - {len(results)}개 키워드 반환")
        return results
    
    def _extract_keywords_keybert(self, text: str, original_text: str, position_mapper: PositionMapper, position_map: Dict[str, any]) -> List[Keyword]:
        """실제 KeyBERT를 사용한 키워드 추출"""
        import logging
        logger = logging.getLogger(__name__)
        debug_logger = get_debug_logger()
        
        try:
            # KeyBERT 설정 (데이터베이스 설정 우선, config fallback)
            max_keywords = self.config.get('max_keywords', 10) if self.config else 10
            keyphrase_ngram_range = tuple(self.config.get('keyphrase_ngram_range', [1, 2])) if self.config else (1, 2)
            stop_words = self.config.get('stop_words', 'english') if self.config else 'english'
            use_maxsum = self.config.get('use_maxsum', False) if self.config else False
            use_mmr = self.config.get('use_mmr', True) if self.config else True
            diversity = self.config.get('diversity', 0.5) if self.config else 0.5
            
            # 추출 설정 로깅
            algorithm = "MMR" if use_mmr else "MaxSum" if use_maxsum else "CosineSim"
            logger.info(f"⚙️ KeyBERT 설정 - 알고리즘: {algorithm}, 최대키워드: {max_keywords}, n-gram: {keyphrase_ngram_range}, 다양성: {diversity if use_mmr else 'N/A'}")
            
            # N-gram 후보 생성 (디버깅용)
            from sklearn.feature_extraction.text import CountVectorizer
            try:
                vectorizer = CountVectorizer(
                    ngram_range=keyphrase_ngram_range,
                    stop_words=stop_words if stop_words != 'korean' else None,
                    max_features=1000  # 후보 제한
                )
                vectorizer.fit([text])
                candidates = vectorizer.get_feature_names_out().tolist()
                
                # 디버그 로깅: 후보 생성
                debug_logger.log_candidate_generation(
                    extractor_name="keybert",
                    candidates=candidates,
                    generation_method=f"CountVectorizer_ngram_{keyphrase_ngram_range}",
                    params={
                        "ngram_range": keyphrase_ngram_range,
                        "stop_words": stop_words,
                        "max_features": 1000
                    }
                )
            except Exception as e:
                logger.debug(f"후보 생성 디버깅 실패: {e}")
                candidates = []
            
            # 임베딩 로깅 (KeyBERT 내부 모델 정보)
            debug_logger.log_embeddings(
                extractor_name="keybert",
                model_name=self.model_name
            )
            
            # KeyBERT로 키워드 추출 (새 API 사용)
            if use_mmr:
                # MMR (Maximal Marginal Relevance) 사용 - 다양성 확보
                logger.info(f"🧠 MMR 알고리즘으로 키워드 추출 중 (다양성: {diversity})...")
                keywords_scores = self.model.extract_keywords(
                    text, 
                    keyphrase_ngram_range=keyphrase_ngram_range,
                    stop_words=stop_words,
                    use_mmr=True,
                    diversity=diversity
                )[:max_keywords]
            elif use_maxsum:
                # Max Sum Similarity 사용
                logger.info(f"📊 MaxSum 알고리즘으로 키워드 추출 중 (후보: {max_keywords * 2})...")
                keywords_scores = self.model.extract_keywords(
                    text,
                    keyphrase_ngram_range=keyphrase_ngram_range,
                    stop_words=stop_words,
                    use_maxsum=True,
                    nr_candidates=max_keywords * 2
                )[:max_keywords]
            else:
                # 기본 cosine similarity 사용
                logger.info("🎯 Cosine Similarity 알고리즘으로 키워드 추출 중...")
                keywords_scores = self.model.extract_keywords(
                    text,
                    keyphrase_ngram_range=keyphrase_ngram_range,
                    stop_words=stop_words
                )[:max_keywords]
            
            # 원시 KeyBERT 결과 로깅
            if keywords_scores:
                raw_keywords = [f"{kw}({score:.3f})" for kw, score in keywords_scores[:5]]
                logger.info(f"🔍 KeyBERT 원시 결과 ({len(keywords_scores)}개): {', '.join(raw_keywords)}")
                
                # 디버그 로깅: 유사도 계산 결과
                similarities = np.array([score for _, score in keywords_scores])
                candidates_only = [kw for kw, _ in keywords_scores]
                debug_logger.log_similarity_calculation(
                    extractor_name="keybert",
                    similarities=similarities,
                    candidates=candidates_only,
                    method=algorithm
                )
                
                # 디버그 로깅: 알고리즘 적용 결과
                debug_logger.log_algorithm_application(
                    extractor_name="keybert",
                    algorithm=algorithm,
                    input_candidates=keywords_scores,
                    output_keywords=keywords_scores,  # KeyBERT는 한번에 최종 결과 반환
                    algorithm_params={
                        "use_mmr": use_mmr,
                        "use_maxsum": use_maxsum,
                        "diversity": diversity if use_mmr else None,
                        "nr_candidates": max_keywords * 2 if use_maxsum else None
                    }
                )
            else:
                logger.warning("⚠️ KeyBERT에서 키워드를 찾지 못함")
            
            results = []
            positioned_keywords = 0
            abstract_keywords = 0
            
            for keyword, score in keywords_scores:
                # 키워드 유효성 검사
                if not TextCleaner.is_meaningful_keyword(keyword):
                    logger.debug(f"Invalid keyword filtered: {repr(keyword)}")
                    continue
                
                # 키워드 정규화
                normalized_keyword = TextCleaner.normalize_keyword(keyword)
                if not normalized_keyword:
                    continue
                
                # 텍스트에서 위치 찾기
                positions = self._find_keyword_positions(text, normalized_keyword)
                
                if positions:
                    positioned_keywords += 1
                    # 첫 번째 위치 사용
                    start_pos, end_pos = positions[0]
                    context = self._extract_context(text, start_pos, end_pos)
                    
                    # 페이지/줄/컬럼 번호 계산
                    page_number, line_number, column_number = position_mapper.get_position_info(start_pos, position_map)
                    logger.debug(f"📍 '{keyword}' 위치 계산: 문자 {start_pos}-{end_pos} -> 페이지 {page_number}, 줄 {line_number}, 컬럼 {column_number}")
                    
                    results.append(Keyword(
                        text=normalized_keyword,
                        score=float(score),
                        extractor=self.name,
                        category="keybert_keyword",
                        start_position=start_pos,
                        end_position=end_pos,
                        context_snippet=context,
                        page_number=page_number,
                        line_number=line_number,
                        column_number=column_number
                    ))
                    
                    # 개별 키워드 위치 로깅 (상위 3개만)
                    if len(results) <= 3:
                        logger.info(f"  📍 '{keyword}' (점수: {score:.3f}) - 위치: {start_pos}-{end_pos}, 컨텍스트: '{context[:50]}{'...' if len(context) > 50 else ''}'")
                else:
                    abstract_keywords += 1
                    # 위치를 찾을 수 없는 경우 (변형된 키워드일 수 있음)
                    results.append(Keyword(
                        text=normalized_keyword,
                        score=float(score),
                        extractor=self.name,
                        category="keybert_keyword",
                        start_position=None,
                        end_position=None,
                        context_snippet=text[:100] + "..." if len(text) > 100 else text,
                        page_number=None,
                        line_number=None,
                        column_number=None
                    ))
                    
                    # 추상 키워드 로깅 (상위 3개만)
                    if abstract_keywords <= 3:
                        logger.info(f"  🔮 '{keyword}' (점수: {score:.3f}) - 추상 키워드 (텍스트에서 정확한 위치 없음)")
            
            # 최종 키워드 통계 로깅
            logger.info(f"📋 KeyBERT 키워드 처리 완료 - 총 {len(results)}개 (위치있음: {positioned_keywords}, 추상: {abstract_keywords})")
            
            # 디버그 로깅: 위치 분석 결과
            keywords_with_positions = []
            for kw in results:
                kw_data = {
                    "keyword": kw.text,
                    "score": kw.score,
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
                extractor_name="keybert",
                keywords_with_positions=keywords_with_positions,
                text=text,
                analysis_method="simple_text_search"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"❌ KeyBERT 추출 중 오류 발생: {str(e)}")
            return []
        finally:
            # 디버그 세션 저장
            debug_logger.save_debug_session()
    
    def _find_keyword_positions(self, text: str, keyword: str) -> List[tuple]:
        """텍스트에서 키워드 위치를 찾습니다."""
        positions = []
        start = 0
        while True:
            pos = text.find(keyword.lower(), start)
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