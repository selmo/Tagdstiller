# spaCy NER 키워드 추출 프로세스

spaCy의 Named Entity Recognition (NER)을 사용한 키워드 추출 과정을 단계별로 설명합니다.

## 📋 목차
1. [개요](#개요)
2. [초기화 및 설정](#초기화-및-설정)
3. [텍스트 전처리](#텍스트-전처리)
4. [spaCy NER 추출](#spacy-ner-추출)
5. [후처리 및 정리](#후처리-및-정리)
6. [Fallback 메커니즘](#fallback-메커니즘)
7. [실제 예제](#실제-예제)

---

## 개요

spaCy NER 추출기는 자연어 처리 라이브러리인 spaCy의 Named Entity Recognition 기능을 활용하여 텍스트에서 **인명, 기관명, 지명, 날짜** 등의 개체명을 키워드로 추출합니다.

### 주요 특징
- ✅ **다국어 지원**: 한국어(`ko_core_news_sm`) 및 영어(`en_core_web_sm`) 모델
- ✅ **자동 모델 관리**: 모델 자동 다운로드 및 fallback 지원
- ✅ **패턴 기반 백업**: spaCy 모델 실패 시 정규식 패턴 사용
- ✅ **상세한 위치 정보**: 페이지, 줄, 컬럼 번호 및 컨텍스트 제공

---

## 초기화 및 설정

### 1. 모델 선택 및 로드

```python
extractor = SpaCyNERExtractor(config={
    'model': 'ko_core_news_sm',  # 한국어 모델
    'auto_download': True,       # 자동 다운로드 활성화
    'max_keywords': 15           # 최대 추출 키워드 수
})
```

### 2. 지원되는 모델 목록

| 언어 | 모델명 | 설명 |
|------|--------|------|
| 한국어 | `ko_core_news_sm` | 소형 한국어 뉴스 모델 |
| 한국어 | `ko_core_news_md` | 중형 한국어 뉴스 모델 |
| 한국어 | `ko_core_news_lg` | 대형 한국어 뉴스 모델 |
| 영어 | `en_core_web_sm` | 소형 영어 웹 모델 |
| 영어 | `en_core_web_md` | 중형 영어 웹 모델 |
| 영어 | `en_core_web_lg` | 대형 영어 웹 모델 |

---

## 텍스트 전처리

### 1. 텍스트 정제
```python
# 원본 텍스트 보관
original_text = "삼성전자는 2023년에 서울 강남구에서 새로운 AI 연구소를 설립했다."

# 텍스트 정제
cleaned_text = TextCleaner.clean_text(original_text)
# 결과: "삼성전자는 2023년에 서울 강남구에서 새로운 AI 연구소를 설립했다."
```

### 2. 위치 매핑 생성
```python
position_mapper = PositionMapper()
position_map = position_mapper.create_position_map(text, file_path)
# 페이지, 줄, 컬럼 정보를 포함한 매핑 테이블 생성
```

---

## spaCy NER 추출

### 1. 문서 처리
```python
doc = self.nlp(cleaned_text)  # spaCy 파이프라인 적용
```

### 2. 개체명 추출 및 분석

```python
# 예제 텍스트에서 추출되는 개체명들
for ent in doc.ents:
    print(f"텍스트: {ent.text}")
    print(f"레이블: {ent.label_}")
    print(f"위치: {ent.start_char}-{ent.end_char}")
    print(f"설명: {spacy.explain(ent.label_)}")
    print("---")
```

**추출 결과 예시:**
```
텍스트: 삼성전자
레이블: OG (Organization - 기관명)
위치: 0-4
설명: 조직, 회사, 기관 등

텍스트: 2023년
레이블: DT (Date - 날짜)
위치: 6-11
설명: 날짜 표현

텍스트: 서울 강남구
레이블: LC (Location - 지명)
위치: 14-20
설명: 지리적 위치
```

### 3. 개체명 타입별 신뢰도

| 개체명 타입 | 한국어 레이블 | 영어 레이블 | 신뢰도 |
|-------------|---------------|-------------|--------|
| 인명 | PS | PERSON | 0.90 |
| 기관명 | OG | ORG | 0.85 |
| 지명 | LC | LOC | 0.80 |
| 금액 | QT | MONEY | 0.85 |
| 날짜 | DT | DATE | 0.75 |
| 기타 | - | MISC | 0.60 |

### 4. 키워드 객체 생성

각 개체명을 `Keyword` 객체로 변환:

```python
keyword = Keyword(
    text="삼성전자",           # 정규화된 키워드
    score=0.85,               # 신뢰도 점수
    extractor="spacy_ner",    # 추출기 이름
    category="OG",            # 개체명 타입
    start_position=0,         # 시작 위치
    end_position=4,           # 끝 위치
    context_snippet="...삼성전자는 2023년에 서울...",  # 컨텍스트
    page_number=1,            # 페이지 번호
    line_number=1,            # 줄 번호
    column_number=1           # 컬럼 번호
)
```

---

## 후처리 및 정리

### 1. 중복 제거
```python
# 정규화된 키워드 + 카테고리 기준으로 중복 제거
unique_results = {}
for result in results:
    normalized_text = TextCleaner.normalize_keyword(result.text)
    key = (normalized_text.lower(), result.category)
    
    if key not in unique_results or unique_results[key].score < result.score:
        unique_results[key] = result
```

### 2. 점수 기반 정렬 및 제한
```python
final_results = list(unique_results.values())
final_results.sort(key=lambda x: x.score, reverse=True)
final_results = final_results[:max_keywords]  # 상위 N개만 선택
```

---

## Fallback 메커니즘

spaCy 모델 로드가 실패한 경우, 정규식 패턴 기반으로 개체명을 추출합니다.

### 지원 패턴

| 패턴 | 정규식 | 카테고리 | 점수 | 예시 |
|------|--------|----------|------|------|
| 년도 | `\d{4}년` | DATE | 0.8 | "2023년" |
| 금액 | `\d+[억만천]?원` | MONEY | 0.85 | "1000만원" |
| 기관명 | `[가-힣]{2,}(?:전자\|그룹\|회사...)` | ORG | 0.75 | "삼성전자" |
| 지역명 | `[가-힣]{2,}(?:시\|도\|구...)` | LOC | 0.7 | "강남구" |
| 영어 개체명 | `\b[A-Z][A-Za-z]{2,}\b` | MISC | 0.6 | "Samsung" |

### 패턴 매칭 예제
```python
# 패턴 기반 추출 결과
pattern_results = [
    ("2023년", "DATE", 0.8),
    ("1000만원", "MONEY", 0.85),
    ("삼성전자", "ORG", 0.75),
    ("강남구", "LOC", 0.7)
]
```

---

## 실제 예제

### 입력 텍스트
```text
삼성전자는 2023년 3월에 서울 강남구 테헤란로에 위치한 새로운 AI 연구소를 
5000억원을 투자하여 설립했다. 이 연구소는 Apple, Google과 경쟁하기 위한 
전략적 거점으로 활용될 예정이다. 김철수 연구소장은 "혁신적인 기술 개발에 
집중하겠다"고 발표했다.
```

### 추출 과정

#### 1단계: spaCy NER 처리
```
🔍 spaCy NER 키워드 추출 시작 - 원본 텍스트 길이: 156 문자
📦 spaCy NER 모델 'ko_core_news_sm' 로드 시작...
✅ spaCy NER 모델 'ko_core_news_sm' 로드 성공
🎯 spaCy 모델 'ko_core_news_sm'으로 NER 추출 중...
```

#### 2단계: 개체명 발견
```
🔍 spaCy NER 발견된 개체명 (7개): 삼성전자(OG), 2023년(DT), 서울(LC), 강남구(LC), 
테헤란로(LC), 5000억원(QT), Apple(OG), Google(OG), 김철수(PS)
```

#### 3단계: 키워드 변환
```
📍 [1/7] '삼성전자' (OG) - 위치: 0-4, 신뢰도: 0.850
📍 [2/7] '2023년' (DT) - 위치: 6-11, 신뢰도: 0.750
📍 [3/7] '서울' (LC) - 위치: 16-18, 신뢰도: 0.800
📍 [4/7] '강남구' (LC) - 위치: 19-22, 신뢰도: 0.800
📍 [5/7] '김철수' (PS) - 위치: 89-92, 신뢰도: 0.900
```

#### 4단계: 최종 결과
```json
[
  {
    "text": "김철수",
    "score": 0.900,
    "category": "PS",
    "context": "...예정이다. 김철수 연구소장은..."
  },
  {
    "text": "삼성전자", 
    "score": 0.850,
    "category": "OG",
    "context": "삼성전자는 2023년 3월에..."
  },
  {
    "text": "서울",
    "score": 0.800,
    "category": "LC", 
    "context": "...3월에 서울 강남구 테헤란로에..."
  }
]
```

### 로그 출력 예시
```
📈 개체명 타입별 분포: OG:3개, LC:3개, PS:1개, DT:1개, QT:1개
✅ spaCy NER 추출 완료 - 총 9개 개체명 (처리: 9, 유효: 9)
🏆 상위 개체명: 김철수(PS,0.900), 삼성전자(OG,0.850), Apple(OG,0.850)
```

---

## 성능 및 특징

### 처리 성능
- **소형 모델**: 1,000자당 약 0.1초
- **중형 모델**: 1,000자당 약 0.3초
- **대형 모델**: 1,000자당 약 0.5초

### 정확도
- **한국어 개체명**: 85-95% (뉴스 도메인 기준)
- **영어 개체명**: 90-95% (웹 텍스트 기준)
- **패턴 기반**: 70-80% (특정 패턴에 한정)

### 장단점

**장점:**
- 🎯 높은 정확도의 개체명 인식
- 🌐 다국어 지원 (한국어, 영어)
- 🔄 자동 모델 관리 및 fallback
- 📍 정확한 위치 정보 제공

**단점:**
- 💾 모델 크기가 큰 편 (50MB ~ 500MB)
- ⚡ 상대적으로 느린 처리 속도
- 📚 도메인 특화 개체명은 인식률 저하 가능

---

## 설정 및 최적화

### 추천 설정

```python
# 일반적인 용도
config = {
    'model': 'ko_core_news_sm',  # 빠른 처리
    'max_keywords': 15,
    'auto_download': True
}

# 높은 정확도가 필요한 경우
config = {
    'model': 'ko_core_news_lg',  # 높은 정확도
    'max_keywords': 20,
    'auto_download': True
}
```

### 메모리 최적화
```python
# 모델 언로드 (메모리 절약)
extractor.nlp = None
extractor.is_loaded = False

# 필요 시 재로드
extractor.load_model()
```

---

## 참고 자료

- [spaCy 공식 문서](https://spacy.io/)
- [한국어 모델 정보](https://spacy.io/models/ko)
- [영어 모델 정보](https://spacy.io/models/en)
- 구현 파일: `/backend/extractors/spacy_ner_extractor.py`