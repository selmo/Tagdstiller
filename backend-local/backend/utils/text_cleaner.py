"""
텍스트 정제 및 키워드 필터링 유틸리티
"""
import re
import unicodedata
from typing import List, Set, Tuple
import logging

logger = logging.getLogger(__name__)

class TextCleaner:
    """텍스트 정제 및 키워드 필터링 클래스"""
    
    # 한국어 불용어 확장
    KOREAN_STOPWORDS = {
        '있습니다', '같습니다', '됩니다', '합니다', '입니다', '때문에', '그리고', '하지만', '또한', 
        '이것은', '그것은', '아니다', '아닙니다', '무엇', '어떤', '어떻게', '언제', '어디서', '누가',
        '그런데', '그러나', '그래서', '따라서', '하지만', '그렇지만', '그러므로', '그러니까',
        '이런', '저런', '그런', '이러한', '저러한', '그러한', '이렇게', '저렇게', '그렇게',
        '입니다', '합니다', '습니다', '았습니다', '었습니다', '했습니다',
        '이다', '하다', '되다', '있다', '없다', '같다', '다르다',
        '우리', '저희', '그들', '이들', '저들', '여러분', '자신', '서로',
        '여기', '저기', '거기', '어기', '이곳', '저곳', '그곳',
        '지금', '그때', '언제', '항상', '가끔', '때때로', '자주', '늘',
        '그냥', '단지', '오직', '단순히', '정말', '진짜', '사실', '실제로'
    }
    
    # 영어 불용어 확장
    ENGLISH_STOPWORDS = {
        'and', 'the', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 
        'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 
        'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 
        'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use', 'may', 'will',
        'would', 'could', 'should', 'might', 'must', 'shall', 'can', 'cannot',
        'this', 'that', 'these', 'those', 'such', 'very', 'just', 'only',
        'about', 'after', 'again', 'against', 'before', 'being', 'below',
        'between', 'both', 'during', 'each', 'from', 'further', 'having',
        'into', 'more', 'most', 'other', 'over', 'same', 'some', 'than',
        'through', 'under', 'until', 'where', 'while', 'with', 'without'
    }
    
    @staticmethod
    def is_valid_unicode(text: str) -> bool:
        """유니코드 문자가 유효한지 검사"""
        try:
            # NFC 정규화로 문자를 표준화
            normalized = unicodedata.normalize('NFC', text)
            # 문자가 실제로 표시 가능한 문자인지 확인
            if not any(unicodedata.category(c) in ['Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nd', 'Nl', 'No'] for c in normalized):
                return False
            return True
        except:
            return False
    
    @staticmethod
    def clean_text(text: str) -> str:
        """텍스트 기본 정제 - 비정상 문자 완전 제거"""
        if not text:
            return ""
        
        # 1. 유니코드 정규화
        text = unicodedata.normalize('NFC', text)
        
        # 2. 제어 문자 제거
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', text)
        
        # 3. 비정상적인 유니코드 범위 문자 제거
        # 사설 영역 (Private Use Area)
        text = re.sub(r'[\uE000-\uF8FF]', '', text)
        text = re.sub(r'[\U000F0000-\U000FFFFF]', '', text)
        text = re.sub(r'[\U00100000-\U0010FFFF]', '', text)
        
        # Specials 블록 (특수 용도 영역)
        text = re.sub(r'[\uFFF0-\uFFFF]', '', text)
        
        # 4. 깨진 한글 자모 조합 제거 (조합되지 않은 자모)
        text = re.sub(r'[\u1100-\u11FF\u3130-\u318F\uA960-\uA97F\uD7B0-\uD7FF]', '', text)
        
        # 5. 의심스러운 데바나가리, 아랍어, 기타 스크립트 문자 제거
        # (한국 문서에서 정상적으로 사용되지 않는 스크립트들)
        text = re.sub(r'[\u0600-\u06FF]', '', text)  # 아랍어
        text = re.sub(r'[\u0700-\u074F]', '', text)  # 시리아어
        text = re.sub(r'[\u0750-\u077F]', '', text)  # 아랍어 보조
        text = re.sub(r'[\u0900-\u097F]', '', text)  # 데바나가리
        text = re.sub(r'[\u0980-\u09FF]', '', text)  # 벵골어
        text = re.sub(r'[\u0A00-\u0A7F]', '', text)  # 구르무키
        text = re.sub(r'[\u0A80-\u0AFF]', '', text)  # 구자라트어
        text = re.sub(r'[\u0B00-\u0B7F]', '', text)  # 오리야
        text = re.sub(r'[\u0B80-\u0BFF]', '', text)  # 타밀어
        text = re.sub(r'[\u0C00-\u0C7F]', '', text)  # 텔루구어
        text = re.sub(r'[\u0C80-\u0CFF]', '', text)  # 칸나다어
        text = re.sub(r'[\u0D00-\u0D7F]', '', text)  # 말라얄람어
        
        # 6. 이상한 조합 문자들과 보이지 않는 문자들 제거
        text = re.sub(r'[\u200B-\u200F\u202A-\u202E\u2060-\u206F]', '', text)  # 보이지 않는 문자들
        text = re.sub(r'[\uFEFF]', '', text)  # BOM 문자
        
        # 7. 깨진 문자 패턴 제거 (연속된 의심스러운 문자 조합)
        # 예: ࢖ࢿ੹੗, ೞ੉ץझ 등
        text = re.sub(r'[\u0A00-\u0DFF\u0900-\u097F]{1,}', '', text)  # 인도계 문자 모두 제거
        text = re.sub(r'[\u0590-\u05FF\u0600-\u06FF]{1,}', '', text)  # 셈족 문자 모두 제거
        text = re.sub(r'[\u0800-\u08FF]{1,}', '', text)  # 사마리아어, 만다이아어 등
        text = re.sub(r'[\u1680-\u169F]{1,}', '', text)  # 오검어
        text = re.sub(r'[\u16A0-\u16FF]{1,}', '', text)  # 룬 문자
        
        # 8. 특정 깨진 문자 패턴 직접 제거
        # 자주 나타나는 깨진 문자 조합들
        text = re.sub(r'[࢖ࢿ੹੗ೞ੉ץझର੉ա೒ۨ੉ઙݾ१ۅ]', '', text)
        text = re.sub(r'[ૐӂܻࢲ஖ࣃఠ֙ೞ߈ӝ઱धद੢੹ݎ࢚߈ӝ]', '', text)
        
        # 9. 조합되지 않은 한글 자모와 기타 결합 문자 제거
        text = re.sub(r'[\u0300-\u036F]', '', text)  # 결합 발음 구별 기호
        
        # 10. 탭과 개행을 공백으로 변환
        text = re.sub(r'[\t\n\r\f\v]', ' ', text)
        
        # 11. 연속된 공백을 하나로 통합
        text = re.sub(r'\s+', ' ', text)
        
        # 12. 앞뒤 공백 제거
        text = text.strip()
        
        return text
    
    @staticmethod
    def is_meaningful_keyword(keyword: str) -> bool:
        """키워드가 의미있는지 판단"""
        if not keyword or len(keyword.strip()) < 2:
            return False
        
        keyword = keyword.strip()
        
        # 유니코드 유효성 검사
        if not TextCleaner.is_valid_unicode(keyword):
            logger.debug(f"Invalid unicode keyword filtered: {repr(keyword)}")
            return False
        
        # 숫자만으로 구성된 키워드 제외
        if keyword.isdigit():
            return False
        
        # 특수문자만으로 구성된 키워드 제외
        if re.match(r'^[^\w가-힣]+$', keyword):
            logger.debug(f"Special characters only keyword filtered: {repr(keyword)}")
            return False
        
        # 너무 짧거나 너무 긴 키워드 제외
        if len(keyword) < 2 or len(keyword) > 50:
            return False
        
        # 반복되는 문자로만 구성된 키워드 제외 (예: "aaaaa", "ㅋㅋㅋㅋ")
        if len(set(keyword)) < 2 and len(keyword) > 2:
            logger.debug(f"Repetitive keyword filtered: {repr(keyword)}")
            return False
        
        # 깨진 문자 패턴 검사 (더 확장된 의심스러운 유니코드 범위)
        suspicious_chars = 0
        for char in keyword:
            code_point = ord(char)
            # 의심스러운 유니코드 범위들 (한국 문서에서 정상적으로 나타나지 않는 문자들)
            if (0x0590 <= code_point <= 0x05FF or  # 히브리어
                0x0600 <= code_point <= 0x06FF or  # 아랍어
                0x0700 <= code_point <= 0x074F or  # 시리아어
                0x0750 <= code_point <= 0x077F or  # 아랍어 보조
                0x0900 <= code_point <= 0x097F or  # 데바나가리
                0x0980 <= code_point <= 0x09FF or  # 벵골어
                0x0A00 <= code_point <= 0x0A7F or  # 구르무키
                0x0A80 <= code_point <= 0x0AFF or  # 구자라트어
                0x0B00 <= code_point <= 0x0B7F or  # 오리야
                0x0B80 <= code_point <= 0x0BFF or  # 타밀어
                0x0C00 <= code_point <= 0x0C7F or  # 텔루구어
                0x0C80 <= code_point <= 0x0CFF or  # 칸나다어
                0x0D00 <= code_point <= 0x0D7F or  # 말라얄람어
                0x1100 <= code_point <= 0x11FF or  # 한글 자모
                0x3130 <= code_point <= 0x318F or  # 한글 호환 자모
                0xE000 <= code_point <= 0xF8FF or  # 사설 영역
                0xFFF0 <= code_point <= 0xFFFF):   # 특수 용도 영역
                suspicious_chars += 1
        
        # 의심스러운 문자가 25% 이상이면 필터링 (임계값 낮춤)
        if suspicious_chars / len(keyword) > 0.25:
            logger.debug(f"Suspicious unicode keyword filtered: {repr(keyword)} (suspicious: {suspicious_chars}/{len(keyword)})")
            return False
        
        # 완전히 깨진 문자로만 구성된 경우 추가 검사
        normal_chars = 0
        for char in keyword:
            code_point = ord(char)
            # 정상적인 문자 범위: 기본 라틴, 라틴 확장, 한글, 한자, 숫자, 기본 구두점
            if ((0x0020 <= code_point <= 0x007F) or    # 기본 라틴
                (0x00A0 <= code_point <= 0x00FF) or    # 라틴 확장-A
                (0x0100 <= code_point <= 0x017F) or    # 라틴 확장-B
                (0xAC00 <= code_point <= 0xD7AF) or    # 한글 음절
                (0x4E00 <= code_point <= 0x9FFF) or    # CJK 통합 한자
                (0x3000 <= code_point <= 0x303F) or    # CJK 기호와 구두점
                (0xFF00 <= code_point <= 0xFFEF)):     # 전각 형태
                normal_chars += 1
        
        # 정상 문자가 50% 미만이면 필터링
        if normal_chars / len(keyword) < 0.5:
            logger.debug(f"Non-normal characters keyword filtered: {repr(keyword)} (normal: {normal_chars}/{len(keyword)})")
            return False
        
        # 불용어 검사
        keyword_lower = keyword.lower()
        if keyword_lower in TextCleaner.KOREAN_STOPWORDS or keyword_lower in TextCleaner.ENGLISH_STOPWORDS:
            return False
        
        # HTML 태그나 마크다운 문법 제외
        if re.match(r'^<[^>]+>$', keyword) or re.match(r'^[#*_`\[\]()]+$', keyword):
            return False
        
        return True
    
    @staticmethod
    def extract_valid_words(text: str, min_length: int = 2) -> List[str]:
        """텍스트에서 유효한 단어들을 추출"""
        if not text:
            return []
        
        # 텍스트 정제
        cleaned_text = TextCleaner.clean_text(text)
        
        # 한국어 패턴 (2글자 이상)
        korean_words = re.findall(r'[가-힣]{' + str(min_length) + ',}', cleaned_text)
        
        # 영어 패턴 (3글자 이상)
        english_words = re.findall(r'[A-Za-z]{' + str(max(3, min_length)) + ',}', cleaned_text)
        
        # 혼합 패턴 (한글+영어, 영어+숫자 등)
        mixed_words = re.findall(r'[A-Za-z가-힣][A-Za-z가-힣0-9]{' + str(min_length-1) + ',}', cleaned_text)
        
        # 모든 단어 수집
        all_words = korean_words + english_words + mixed_words
        
        # 중복 제거 및 유효성 검사
        valid_words = []
        seen = set()
        
        for word in all_words:
            word = word.strip()
            if word and word not in seen and TextCleaner.is_meaningful_keyword(word):
                valid_words.append(word)
                seen.add(word)
        
        return valid_words
    
    @staticmethod
    def filter_keywords(keywords: List[str], max_count: int = None) -> List[str]:
        """키워드 목록을 필터링하고 정제"""
        if not keywords:
            return []
        
        # 유효한 키워드만 필터링
        valid_keywords = [kw for kw in keywords if TextCleaner.is_meaningful_keyword(kw)]
        
        # 중복 제거 (대소문자 구분하여)
        unique_keywords = list(dict.fromkeys(valid_keywords))
        
        # 개수 제한
        if max_count and len(unique_keywords) > max_count:
            unique_keywords = unique_keywords[:max_count]
        
        logger.info(f"Keyword filtering: {len(keywords)} -> {len(unique_keywords)} keywords")
        if len(keywords) > len(unique_keywords):
            filtered_out = [kw for kw in keywords if not TextCleaner.is_meaningful_keyword(kw)]
            logger.debug(f"Filtered out keywords: {filtered_out[:10]}")  # 처음 10개만 로그
        
        return unique_keywords
    
    @staticmethod
    def normalize_keyword(keyword: str) -> str:
        """키워드 정규화 - 한국어 조사 제거 포함"""
        if not keyword:
            return ""
        
        # 유니코드 정규화
        normalized = unicodedata.normalize('NFC', keyword)
        
        # 앞뒤 공백 제거
        normalized = normalized.strip()
        
        # 내부 연속 공백을 하나로 통합
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # 한국어 조사 제거 (최종 명사 추출)
        normalized = TextCleaner._remove_korean_particles(normalized)
        
        return normalized
    
    @staticmethod
    def _remove_korean_particles(text: str) -> str:
        """한국어 조사 제거하여 핵심 명사만 추출"""
        if not text or len(text) < 2:
            return text
        
        # 한국어가 아닌 경우 그대로 반환
        if not re.search(r'[가-힣]', text):
            return text
        
        # 조사 패턴 정의 (빈도 높은 조사들을 우선 순위로)
        # 최소 2글자 이상의 어근이 남도록 보장
        particle_patterns = [
            # 관형격조사 (최우선)
            r'^(.{2,})의$',      # ~의 (가장 중요!)
            
            # 복합조사 (길이가 긴 것부터)
            r'^(.{2,})에서의$',  # ~에서의
            r'^(.{2,})으로는$',  # ~으로는
            r'^(.{2,})로는$',    # ~로는
            r'^(.{2,})에서는$',  # ~에서는
            r'^(.{2,})으로도$',  # ~으로도
            r'^(.{2,})로도$',    # ~로도
            r'^(.{2,})와도$',    # ~와도
            r'^(.{2,})과도$',    # ~과도
            r'^(.{2,})에는$',    # ~에는
            r'^(.{2,})에도$',    # ~에도
            r'^(.{2,})까지$',    # ~까지
            r'^(.{2,})부터$',    # ~부터
            r'^(.{2,})보다$',    # ~보다
            r'^(.{2,})처럼$',    # ~처럼
            r'^(.{2,})같이$',    # ~같이
            r'^(.{2,})하고$',    # ~하고
            r'^(.{2,})한테$',    # ~한테
            r'^(.{2,})에게$',    # ~에게
            
            # 주격조사
            r'^(.{2,})이$',      # ~이
            r'^(.{2,})가$',      # ~가
            r'^(.{2,})께서$',    # ~께서
            
            # 목적격조사  
            r'^(.{2,})을$',      # ~을
            r'^(.{2,})를$',      # ~를
            
            # 부사격조사
            r'^(.{2,})에서$',    # ~에서
            r'^(.{2,})으로$',    # ~으로
            r'^(.{2,})로$',      # ~로
            r'^(.{2,})와$',      # ~와
            r'^(.{2,})과$',      # ~과
            r'^(.{2,})랑$',      # ~랑
            r'^(.{2,})께$',      # ~께
            r'^(.{2,})에$',      # ~에
            r'^(.{2,})도$',      # ~도
            r'^(.{2,})만$',      # ~만
            
            # 서술격조사
            r'^(.{2,})이다$',    # ~이다
            r'^(.{2,})다$',      # ~다
            
            # 종결어미 (일부)
            r'^(.{2,})은$',      # ~은
            r'^(.{2,})는$',      # ~는 (보조사)
        ]
        
        original_text = text
        
        # 각 조사 패턴을 확인하여 제거
        for pattern in particle_patterns:
            match = re.match(pattern, text)
            if match:
                root_word = match.group(1)
                # 조사를 제거한 결과가 최소 2글자 이상이어야 함
                if len(root_word) >= 2:
                    logger.debug(f"한국어 조사 제거: '{original_text}' -> '{root_word}' (패턴: {pattern})")
                    return root_word
        
        # 조사가 없거나 제거할 수 없는 경우 원본 반환
        return text