from typing import List, Dict, Any, Optional
from pathlib import Path
from collections import Counter
import time
from .base import KeywordExtractor, Keyword
from utils.text_cleaner import TextCleaner
from utils.position_mapper import PositionMapper
from utils.debug_logger import get_debug_logger

class KoNLPyExtractor(KeywordExtractor):
    """KoNLPy 기반 한국어 명사 추출기"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("konlpy", config)
        self.tagger = None
        self.tagger_type = config.get('tagger', 'Okt') if config else 'Okt'  # Okt, Komoran, Hannanum 등
    
    def load_model(self) -> bool:
        """KoNLPy 형태소 분석기를 로드합니다."""
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            logger.info(f"📦 KoNLPy '{self.tagger_type}' 형태소 분석기 로드 시작...")
            
            # KoNLPy 라이브러리 로드
            from konlpy.tag import Okt, Komoran, Hannanum, Kkma
            
            # 지원되는 형태소 분석기 목록
            available_taggers = {
                'Okt': Okt,
                'Komoran': Komoran, 
                'Hannanum': Hannanum,
                'Kkma': Kkma
            }
            
            # 요청된 형태소 분석기가 지원되는지 확인
            if self.tagger_type not in available_taggers:
                logger.warning(f"⚠️ 지원하지 않는 형태소 분석기: '{self.tagger_type}', Okt로 대체됨")
                self.tagger_type = 'Okt'
            
            # 형태소 분석기 로드 시도
            tagger_class = available_taggers[self.tagger_type]
            logger.info(f"🔄 '{self.tagger_type}' 형태소 분석기 초기화 중...")
            
            self.tagger = tagger_class()
            self.actual_tagger_type = self.tagger_type
            self.is_loaded = True
            
            logger.info(f"✅ KoNLPy '{self.tagger_type}' 형태소 분석기 로드 성공")
            return True
            
        except ImportError as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"❌ KoNLPy 라이브러리를 찾을 수 없음: {e}")
            logger.info(f"💡 KoNLPy 설치 명령어: pip install konlpy")
            self.is_loaded = False
            return False
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"❌ KoNLPy '{self.tagger_type}' 형태소 분석기 로드 실패: {e}")
            self.is_loaded = False
            return False
    
    def extract(self, text: str, file_path: Optional[Path] = None) -> List[Keyword]:
        """한국어 텍스트에서 명사를 추출하여 키워드로 반환합니다."""
        import logging
        logger = logging.getLogger(__name__)
        debug_logger = get_debug_logger()
        start_time = time.time()
        
        logger.info(f"🔍 KoNLPy 키워드 추출 시작 - 원본 텍스트 길이: {len(text)} 문자")
        
        # 디버그 로깅: 추출 시작
        debug_logger.start_extraction(
            extractor_name="konlpy",
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
            extractor_name="konlpy",
            original_text=original_text_copy,
            preprocessed_text=cleaned_text,
            preprocessing_steps=["clean_text", "normalize_korean", "konlpy_preprocessing"]
        )
        
        if not self.is_loaded:
            logger.info("📦 KoNLPy 형태소 분석기 로드 시도...")
            self.load_model()
        
        if not self.is_loaded:
            logger.warning("⚠️ KoNLPy 형태소 분석기 로드 실패, 패턴 기반 추출로 fallback")
            return self._extract_korean_nouns_simple(cleaned_text, text, position_mapper, position_map)
        
        try:
            logger.info(f"🎯 KoNLPy '{getattr(self, 'actual_tagger_type', self.tagger_type)}'로 명사 추출 중...")
            # 실제 KoNLPy 사용
            keywords = self._extract_korean_nouns_konlpy(cleaned_text, text, position_mapper, position_map)
            
            # 최종 결과 로깅
            extraction_time = time.time() - start_time
            debug_logger.log_final_results(
                extractor_name="konlpy",
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
            logger.error(f"❌ KoNLPy 명사 추출 실패, 패턴 기반 추출로 fallback: {e}")
            fallback_keywords = self._extract_korean_nouns_simple(cleaned_text, text, position_mapper, position_map)
            
            # 폴백 결과 로깅
            extraction_time = time.time() - start_time
            debug_logger.log_final_results(
                extractor_name="konlpy",
                final_keywords=[{
                    "keyword": kw.text,
                    "score": kw.score,
                    "category": kw.category,
                    "start_position": kw.start_position,
                    "end_position": kw.end_position,
                    "context": kw.context_snippet
                } for kw in fallback_keywords],
                extraction_time=extraction_time,
                total_processing_time=time.time() - start_time
            )
            
            return fallback_keywords
        finally:
            # 디버그 세션 저장
            debug_logger.save_debug_session()
    
    def _extract_korean_nouns_konlpy(self, text: str, original_text: str, position_mapper: PositionMapper, position_map: Dict[str, any]) -> List[Keyword]:
        """KoNLPy를 사용한 실제 한국어 명사 추출"""
        import logging
        import time
        logger = logging.getLogger(__name__)
        debug_logger = get_debug_logger()
        
        try:
            # KoNLPy 설정 로깅
            max_keywords = self.config.get('max_keywords', 15) if self.config else 15
            min_length = self.config.get('min_length', 2) if self.config else 2
            min_frequency = self.config.get('min_frequency', 1) if self.config else 1
            
            actual_tagger_name = getattr(self, 'actual_tagger_type', self.tagger_type)
            logger.info(f"⚙️ KoNLPy 설정 - 형태소분석기: {actual_tagger_name}, 최대명사: {max_keywords}, 최소길이: {min_length}, 최소빈도: {min_frequency}")
            
            # 디버그 로깅: 모델 정보
            debug_logger.log_embeddings(
                extractor_name="konlpy",
                model_name=f"konlpy_{actual_tagger_name}"
            )
            
            # KoNLPy 형태소 분석 시작
            start_time = time.time()
            logger.info(f"🔍 KoNLPy 형태소 분석 시작 (텍스트 길이: {len(text)} 문자)...")
            
            # 명사만 추출 (품사가 N으로 시작하는 것들)
            nouns = self.tagger.nouns(text)
            processing_time = time.time() - start_time
            logger.info(f"⚡ KoNLPy 형태소 분석 완료 (소요시간: {processing_time:.3f}초)")
            
            # 디버그 로깅: 후보 생성
            debug_logger.log_candidate_generation(
                extractor_name="konlpy",
                candidates=nouns,
                generation_method=f"konlpy_{actual_tagger_name}_nouns",
                params={
                    "tagger": actual_tagger_name,
                    "processing_time": processing_time,
                    "total_nouns_found": len(nouns),
                    "min_length": min_length,
                    "min_frequency": min_frequency
                }
            )
            
            # 명사 필터링 및 전처리
            logger.info(f"🔄 명사 필터링 시작 ({len(nouns)}개 처리 예정)...")
            
            valid_nouns = []
            filtered_count = 0
            
            for noun in nouns:
                # 길이 체크
                if len(noun) < min_length:
                    filtered_count += 1
                    continue
                
                # 유효성 체크 (TextCleaner 사용)
                if not TextCleaner.is_meaningful_keyword(noun):
                    filtered_count += 1
                    continue
                
                # 정규화
                normalized_noun = TextCleaner.normalize_keyword(noun)
                if not normalized_noun:
                    filtered_count += 1
                    continue
                
                valid_nouns.append(normalized_noun)
            
            logger.info(f"🧹 명사 필터링 완료 - 유효: {len(valid_nouns)}개, 제외: {filtered_count}개")
            
            if not valid_nouns:
                logger.warning("⚠️ KoNLPy에서 유효한 명사를 찾지 못함")
                return []
            
            # 빈도수 계산
            noun_counts = Counter(valid_nouns)
            
            # 최소 빈도 필터링
            filtered_nouns = {
                noun: count for noun, count in noun_counts.items()
                if count >= min_frequency
            }
            
            if not filtered_nouns:
                logger.warning(f"⚠️ 최소 빈도({min_frequency}) 조건을 만족하는 명사가 없음")
                return []
            
            # 빈도수 기반 점수 계산
            max_count = max(filtered_nouns.values())
            logger.info(f"📊 명사 빈도 분석 - 총 고유명사: {len(filtered_nouns)}개, 최대빈도: {max_count}")
            
            # 디버그 로깅: 유사도 계산 (빈도수 기반)
            frequencies = list(filtered_nouns.values())
            candidates_only = list(filtered_nouns.keys())
            import numpy as np
            frequency_array = np.array(frequencies, dtype=float)
            normalized_frequencies = frequency_array / max_count  # 정규화
            
            debug_logger.log_similarity_calculation(
                extractor_name="konlpy",
                similarities=normalized_frequencies,
                candidates=candidates_only,
                method="frequency_based"
            )
            
            results = []
            processed_nouns = 0
            
            # 명사를 키워드로 변환
            for noun, count in filtered_nouns.items():
                processed_nouns += 1
                
                # 정규화된 점수 계산 (빈도 기반)
                frequency_score = count / max_count
                # 길이 보너스 (긴 명사일수록 중요할 가능성 높음)
                length_bonus = min(0.2, (len(noun) - 2) * 0.05)
                final_score = min(1.0, frequency_score + length_bonus)
                
                # 텍스트에서 위치 찾기
                positions = self._find_keyword_positions(text, noun)
                
                # 각 위치마다 키워드 객체 생성
                for start_pos, end_pos in positions:
                    context = self._extract_context(text, start_pos, end_pos)
                    page_number, line_number, column_number = position_mapper.get_position_info(start_pos, position_map)
                    results.append(Keyword(
                        text=noun,
                        score=final_score,
                        extractor=self.name,
                        category="noun",
                        start_position=start_pos,
                        end_position=end_pos,
                        context_snippet=context,
                        page_number=page_number,
                        line_number=line_number,
                        column_number=column_number
                    ))
                
                # 진행률 로깅 (상위 5개만)
                if processed_nouns <= 5:
                    logger.info(f"  📍 [{processed_nouns}/{len(filtered_nouns)}] '{noun}' - 빈도: {count}, 점수: {final_score:.3f}, 위치: {len(positions)}곳")
            
            # 중복 제거 및 점수 순 정렬
            logger.info(f"🔧 후처리 시작 - 중복 제거 및 정렬 ({len(results)}개 → 최대 {max_keywords}개)")
            
            # 중복 제거 (같은 텍스트, 같은 위치)
            unique_results = {}
            duplicates_removed = 0
            
            for result in results:
                key = (result.text, result.start_position, result.end_position)
                if key not in unique_results or unique_results[key].score < result.score:
                    if key in unique_results:
                        duplicates_removed += 1
                    unique_results[key] = result
            
            if duplicates_removed > 0:
                logger.info(f"🧹 중복 제거: {duplicates_removed}개 명사 제거")
            
            final_results = list(unique_results.values())
            final_results.sort(key=lambda x: x.score, reverse=True)
            
            # 상위 N개만 반환
            before_limit = len(final_results)
            final_results = final_results[:max_keywords]
            
            if before_limit > max_keywords:
                logger.info(f"📊 상위 키워드 제한: {before_limit}개 → {len(final_results)}개")
            
            # 디버그 로깅: 위치 분석 결과
            keywords_with_positions = []
            for kw in final_results:
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
                extractor_name="konlpy",
                keywords_with_positions=keywords_with_positions,
                text=text,
                analysis_method="simple_text_search"
            )
            
            # 최종 결과 로깅
            if final_results:
                top_nouns = [f"{kw.text}({kw.score:.3f})" for kw in final_results[:5]]
                logger.info(f"✅ KoNLPy 명사 추출 완료 - 총 {len(final_results)}개 명사 (처리: {processed_nouns}, 유효: {len(valid_nouns)})")
                logger.info(f"🏆 상위 명사: {', '.join(top_nouns)}")
            else:
                logger.warning("⚠️ KoNLPy 처리 후 유효한 명사가 없음")
            
            return final_results
            
        except Exception as e:
            logger.error(f"❌ KoNLPy 명사 추출 중 오류 발생: {str(e)}")
            return []
    
    def _extract_korean_nouns_simple(self, text: str, original_text: str, position_mapper: PositionMapper, position_map: Dict[str, any]) -> List[Keyword]:
        """간단한 한국어 명사 추출 (KoNLPy 없이)"""
        import re
        
        # 유효한 단어 추출 (TextCleaner 사용)
        min_length = self.config.get('min_length', 2) if self.config else 2
        valid_words = TextCleaner.extract_valid_words(text, min_length=min_length)
        
        # 한국어 명사 필터링 (한글로만 구성된 단어)
        korean_nouns = []
        for word in valid_words:
            if re.match(r'^[가-힣]+$', word) and self._is_likely_noun(word):
                korean_nouns.append(word)
        
        # 빈도수 계산
        noun_counts = Counter(korean_nouns)
        
        # 최소 빈도 필터링
        min_frequency = self.config.get('min_frequency', 1) if self.config else 1
        filtered_nouns = {
            noun: count for noun, count in noun_counts.items()
            if count >= min_frequency
        }
        
        if not filtered_nouns:
            return []
        
        # 빈도수 기반 점수 계산
        max_count = max(filtered_nouns.values())
        
        results = []
        for noun, count in filtered_nouns.items():
            score = min(1.0, count / max(1, max_count))  # 정규화된 점수
            
            # 텍스트에서 위치 찾기
            positions = self._find_keyword_positions(text, noun)
            
            for start_pos, end_pos in positions:
                context = self._extract_context(text, start_pos, end_pos)
                page_number, line_number, column_number = position_mapper.get_position_info(start_pos, position_map)
                results.append(Keyword(
                    text=noun,
                    score=score,
                    extractor=self.name,
                    category="noun",
                    start_position=start_pos,
                    end_position=end_pos,
                    context_snippet=context,
                    page_number=page_number,
                    line_number=line_number,
                    column_number=column_number
                ))
        
        # 점수 순으로 정렬하고 상위 키워드만 반환
        results.sort(key=lambda x: x.score, reverse=True)
        max_keywords = self.config.get('max_keywords', 10) if self.config else 10
        return results[:max_keywords]
    
    def _is_likely_noun(self, word: str) -> bool:
        """단어가 명사일 가능성이 높은지 간단히 판단"""
        # 기술 관련 명사 패턴
        tech_patterns = [
            '기술', '시스템', '데이터', '정보', '분석', '개발', '연구', '서비스', '프로그램',
            '소프트웨어', '하드웨어', '네트워크', '보안', '인터넷', '웹사이트', '애플리케이션',
            '인공지능', '머신러닝', '딥러닝', '알고리즘', '빅데이터', '클라우드', '모바일',
            '자동화', '최적화', '효율화', '디지털', '온라인', '플랫폼', '솔루션'
        ]
        
        # 기술 관련 어근이 포함된 경우
        for pattern in tech_patterns:
            if pattern in word:
                return True
        
        # 명사 어미 패턴
        noun_endings = ['기술', '시스템', '정보', '방법', '과정', '결과', '목적', '수단', '도구', '장치', '설비']
        for ending in noun_endings:
            if word.endswith(ending):
                return True
        
        # 기본적으로 2글자 이상이면 명사로 간주
        return len(word) >= 2
    
    def _find_keyword_positions(self, text: str, keyword: str) -> List[tuple]:
        """텍스트에서 키워드 위치를 찾습니다."""
        positions = []
        start = 0
        
        while True:
            pos = text.find(keyword, start)
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