# 🎯 KeyBERT 키워드 추출 가이드

> **KeyBERT를 이용한 텍스트에서 키워드 추출 프로세스 완전 가이드**

## 📚 목차
1. [KeyBERT 개요](#keybert-개요)
2. [추출 프로세스](#추출-프로세스)
3. [실제 예제](#실제-예제)
4. [알고리즘 상세](#알고리즘-상세)
5. [모델 선택 가이드](#모델-선택-가이드)
6. [매개변수 설정](#매개변수-설정)
7. [결과 해석](#결과-해석)

---

## KeyBERT 개요

**KeyBERT**는 BERT 기반 임베딩을 사용하여 문서에서 의미적으로 관련성이 높은 키워드를 추출하는 기술입니다.

### 핵심 원리
1. **문서 임베딩**: 전체 문서를 고차원 벡터로 변환
2. **키워드 후보 생성**: N-gram 기반 키워드 후보 추출
3. **유사도 계산**: 문서와 키워드 간 코사인 유사도 계산
4. **최적화**: MMR 또는 Max Sum 알고리즘으로 다양성 확보

---

## 추출 프로세스

### 1단계: 텍스트 전처리
```python
# 입력 텍스트 예시
text = """
인공지능과 머신러닝은 현대 기술의 핵심이다. 
딥러닝 알고리즘을 통해 복잡한 패턴을 학습하고, 
자연어 처리와 컴퓨터 비전 분야에서 혁신적인 성과를 보이고 있다.
"""

# 전처리 단계
1. 문장 분할
2. 토큰화
3. N-gram 생성 (1-gram, 2-gram)
```

### 2단계: 키워드 후보 생성
```python
# N-gram 후보 생성
ngram_candidates = [
    "인공지능", "머신러닝", "현대", "기술", "핵심",
    "딥러닝", "알고리즘", "복잡한", "패턴", "학습",
    "자연어", "처리", "컴퓨터", "비전", "분야", "혁신적인", "성과",
    # 2-gram
    "인공지능과", "머신러닝은", "현대 기술", "딥러닝 알고리즘",
    "자연어 처리", "컴퓨터 비전"
]
```

### 3단계: 임베딩 계산
```python
# 1. 문서 임베딩
document_embedding = model.encode([text])
# Shape: (1, 384) for all-MiniLM-L6-v2

# 2. 키워드 후보 임베딩
candidate_embeddings = model.encode(ngram_candidates)
# Shape: (n_candidates, 384)
```

### 4단계: 유사도 계산 및 순위화
```python
# 코사인 유사도 계산
from sklearn.metrics.pairwise import cosine_similarity

similarities = cosine_similarity(document_embedding, candidate_embeddings)
# Shape: (1, n_candidates)

# 상위 키워드 선택
top_k = 5
keyword_scores = [
    (candidate, score) for candidate, score in 
    zip(ngram_candidates, similarities[0])
]
keyword_scores.sort(key=lambda x: x[1], reverse=True)
initial_keywords = keyword_scores[:top_k]
```

---

## 실제 예제

### 입력 텍스트
```text
"인공지능과 머신러닝 기술이 발전하면서 자율주행 자동차와 스마트 홈 시스템이 
현실이 되고 있다. 딥러닝 알고리즘을 활용한 음성 인식과 이미지 분류 기술은 
일상생활에서 광범위하게 사용되고 있으며, 빅데이터 분석을 통해 개인화된 
서비스를 제공하는 것이 가능해졌다."
```

### KeyBERT 추출 결과

#### 1. 기본 추출 (Cosine Similarity)
```python
# 설정: max_keywords=8, ngram_range=(1,2)
keywords = [
    ("머신러닝", 0.7234),
    ("딥러닝", 0.6891),
    ("인공지능", 0.6743),
    ("빅데이터", 0.6234),
    ("자율주행", 0.5987),
    ("음성 인식", 0.5456),
    ("이미지 분류", 0.5321),
    ("스마트 홈", 0.4987)
]
```

#### 2. MMR 알고리즘 적용 (다양성 0.5)
```python
# MMR로 다양성 확보
keywords_mmr = [
    ("머신러닝", 0.7234),
    ("자율주행", 0.5987),    # 머신러닝과 다른 의미영역
    ("딥러닝", 0.6891),
    ("빅데이터", 0.6234),    # 딥러닝과 구별되는 영역
    ("음성 인식", 0.5456),
    ("스마트 홈", 0.4987),   # 하드웨어/서비스 영역
    ("개인화", 0.4234),
    ("분석", 0.3987)
]
```

#### 3. Max Sum Similarity 적용
```python
# Max Sum으로 의미적 다양성 최대화
keywords_maxsum = [
    ("머신러닝", 0.7234),
    ("자율주행", 0.5987),
    ("빅데이터", 0.6234),
    ("스마트 홈", 0.4987),
    ("개인화", 0.4234)
]
```

---

## 알고리즘 상세

### 1. Cosine Similarity (기본)
```python
def extract_keywords_cosine(doc_embedding, candidate_embeddings, top_k=5):
    """기본 코사인 유사도 방법"""
    similarities = cosine_similarity([doc_embedding], candidate_embeddings)[0]
    top_indices = similarities.argsort()[-top_k:][::-1]
    return [(candidates[i], similarities[i]) for i in top_indices]
```

**특징:**
- ✅ 단순하고 빠름
- ❌ 유사한 키워드들이 중복 선택될 수 있음
- 📊 문서와 가장 유사한 키워드 우선 선택

### 2. MMR (Maximal Marginal Relevance)
```python
def extract_keywords_mmr(doc_embedding, candidate_embeddings, 
                        candidates, top_k=5, diversity=0.5):
    """MMR 알고리즘으로 다양성과 관련성의 균형"""
    selected = []
    remaining = list(range(len(candidates)))
    
    # 첫 번째 키워드: 가장 유사한 것
    similarities = cosine_similarity([doc_embedding], candidate_embeddings)[0]
    first_idx = similarities.argmax()
    selected.append(first_idx)
    remaining.remove(first_idx)
    
    for _ in range(top_k - 1):
        mmr_scores = []
        
        for idx in remaining:
            # 문서 유사도
            doc_sim = similarities[idx]
            
            # 이미 선택된 키워드들과의 최대 유사도
            max_sim_selected = max([
                cosine_similarity([candidate_embeddings[idx]], 
                                [candidate_embeddings[s]])[0][0]
                for s in selected
            ])
            
            # MMR 점수 계산
            mmr_score = diversity * doc_sim - (1 - diversity) * max_sim_selected
            mmr_scores.append((idx, mmr_score))
        
        # 최고 MMR 점수 선택
        best_idx = max(mmr_scores, key=lambda x: x[1])[0]
        selected.append(best_idx)
        remaining.remove(best_idx)
    
    return [(candidates[i], similarities[i]) for i in selected]
```

**MMR 매개변수:**
- `diversity=0.0`: 오직 관련성만 고려 (Cosine Similarity와 동일)
- `diversity=0.5`: 관련성과 다양성의 균형
- `diversity=1.0`: 오직 다양성만 고려

### 3. Max Sum Similarity
```python
def extract_keywords_maxsum(candidate_embeddings, candidates, top_k=5):
    """Max Sum으로 가장 다양한 키워드 조합 선택"""
    from itertools import combinations
    
    max_sum = 0
    best_combination = None
    
    # 모든 top_k 조합을 확인
    for combination in combinations(range(len(candidates)), top_k):
        # 조합 내 키워드들 간의 거리 합 계산
        total_distance = 0
        for i, j in combinations(combination, 2):
            similarity = cosine_similarity([candidate_embeddings[i]], 
                                         [candidate_embeddings[j]])[0][0]
            total_distance += (1 - similarity)  # 거리 = 1 - 유사도
        
        if total_distance > max_sum:
            max_sum = total_distance
            best_combination = combination
    
    return [(candidates[i], 1.0) for i in best_combination]
```

**특징:**
- ✅ 최대 다양성 보장
- ❌ 문서 관련성이 낮을 수 있음
- 🔄 계산 복잡도가 높음 (조합 최적화)

---

## 모델 선택 가이드

### 다국어 모델 (5개)

#### 1. all-MiniLM-L6-v2 ⭐ **추천**
```python
model_name = "all-MiniLM-L6-v2"
# 크기: 90MB, 임베딩 차원: 384
# 속도: 매우 빠름, 품질: 우수
```
**최적 용도:**
- 일반적인 다국어 문서
- 빠른 처리가 필요한 경우
- 리소스가 제한된 환경

**예제 결과:**
```python
# 영어 텍스트
text = "Machine learning algorithms are transforming healthcare industry"
keywords = [("machine learning", 0.73), ("algorithms", 0.68), ("healthcare", 0.61)]

# 한국어 텍스트  
text = "머신러닝 알고리즘이 의료산업을 변화시키고 있다"
keywords = [("머신러닝", 0.69), ("알고리즘", 0.64), ("의료산업", 0.58)]
```

#### 2. paraphrase-multilingual-mpnet-base-v2
```python
model_name = "paraphrase-multilingual-mpnet-base-v2"
# 크기: 1.1GB, 임베딩 차원: 768
# 속도: 느림, 품질: 최고
```
**최적 용도:**
- 고품질이 중요한 연구/분석
- 복잡한 전문 용어가 많은 문서
- 정확도가 속도보다 중요한 경우

### 한국어 최적화 모델 (4개)

#### 1. jhgan/ko-sroberta-multitask ⭐ **한국어 추천**
```python
model_name = "jhgan/ko-sroberta-multitask"
# 크기: 400MB, 임베딩 차원: 768
# 한국어 특화 학습, 다중 태스크 최적화
```

**한국어 특화 예제:**
```python
text = """
블록체인 기술은 암호화폐 거래의 투명성을 보장한다. 
스마트 컨트랙트를 통해 중개자 없이도 신뢰할 수 있는 
거래가 가능하며, 탈중앙화된 금융 시스템을 구현할 수 있다.
"""

keywords = [
    ("블록체인", 0.82),      # 높은 정확도
    ("암호화폐", 0.79), 
    ("스마트 컨트랙트", 0.76),
    ("탈중앙화", 0.71),
    ("금융 시스템", 0.68)
]
```

#### 2. jhgan/ko-sbert-nli
```python
# NLI(Natural Language Inference) 태스크로 학습
# 문장 간 의미 관계 파악에 특화
```

### 영어 전용 모델 (5개)

#### 1. all-mpnet-base-v2
```python
model_name = "all-mpnet-base-v2"
# 영어 문서 처리 시 최고 성능
# 크기: 420MB, 임베딩 차원: 768
```

---

## 매개변수 설정

### 1. N-gram 범위 (keyphrase_ngram_range)
```python
# 설정 예제
ngram_ranges = {
    "단일어만": (1, 1),           # ["인공지능", "머신러닝"]
    "일반적": (1, 2),             # ["인공지능", "머신러닝 기술"]  
    "구문 포함": (1, 3),          # ["자연어 처리 기술"]
    "긴 구문": (2, 4)             # ["딥러닝 알고리즘 최적화 방법"]
}
```

**선택 가이드:**
- **학술 논문**: (1, 3) - 전문 용어 구문 추출
- **뉴스 기사**: (1, 2) - 핵심 키워드와 간단한 구문
- **기술 문서**: (1, 4) - 복합 기술 용어 포함

### 2. 최대 키워드 수 (max_keywords)
```python
# 문서 길이별 권장 설정
document_lengths = {
    "짧은 글 (< 500자)": 3-5,
    "보통 글 (500-2000자)": 5-10,
    "긴 글 (2000-5000자)": 10-20,
    "논문/보고서 (> 5000자)": 15-30
}
```

### 3. 다양성 매개변수 (diversity)
```python
diversity_settings = {
    0.0: "최대 관련성 (중복 키워드 가능)",
    0.3: "관련성 우선, 약간의 다양성",
    0.5: "관련성과 다양성의 균형 ⭐ 추천",
    0.7: "다양성 우선, 관련성도 고려",
    1.0: "최대 다양성 (관련성 낮을 수 있음)"
}
```

### 4. 불용어 설정 (stop_words)
```python
stop_words_options = {
    "english": ["the", "and", "or", "but", "in", "on", "at", "to"],
    "korean": ["이", "그", "저", "것", "들", "에", "를", "을", "의"],
    None: "불용어 제거하지 않음"
}
```

---

## 결과 해석

### 점수 범위 이해
```python
score_interpretation = {
    "0.8 - 1.0": "매우 높은 관련성 - 핵심 키워드",
    "0.6 - 0.8": "높은 관련성 - 중요 키워드", 
    "0.4 - 0.6": "보통 관련성 - 보조 키워드",
    "0.2 - 0.4": "낮은 관련성 - 참고 키워드",
    "0.0 - 0.2": "매우 낮은 관련성 - 노이즈 가능성"
}
```

### 품질 평가 기준
```python
# 좋은 키워드 추출 결과의 특징
quality_indicators = {
    "의미적 다양성": "서로 다른 주제 영역의 키워드",
    "적절한 추상화": "너무 구체적이지도, 일반적이지도 않음",
    "문서 대표성": "문서의 주요 내용을 잘 반영",
    "중복 최소화": "유사한 의미의 키워드 반복 없음"
}
```

### 실제 평가 예제
```python
# 좋은 결과 예제
good_keywords = [
    ("딥러닝", 0.78),        # 핵심 기술
    ("자율주행", 0.72),      # 응용 분야  
    ("컴퓨터 비전", 0.68),   # 관련 기술
    ("빅데이터", 0.61),      # 연관 개념
    ("개인화 서비스", 0.55)  # 활용 영역
]
# ✅ 다양한 측면을 포괄, 적절한 점수 분포

# 개선 필요한 결과 예제  
poor_keywords = [
    ("딥러닝", 0.78),
    ("딥러닝 기술", 0.75),   # ❌ 중복성
    ("딥러닝 알고리즘", 0.72), # ❌ 중복성
    ("기술", 0.45),          # ❌ 너무 일반적
    ("시스템", 0.42)         # ❌ 너무 일반적
]
```

---

## DocExtract에서의 구현

### 설정 파라미터
```json
{
  "extractor.keybert.model": "all-MiniLM-L6-v2",
  "KeyBERT_MMR": true,
  "extractor.keybert.diversity": 0.5,
  "extractor.keybert.keyphrase_ngram_range": "[1, 2]",
  "extractor.keybert.max_keywords": 10,
  "extractor.keybert.stop_words": "korean",
  "extractor.keybert.use_maxsum": false
}
```

### 추출 로그 예제
```
🔍 KeyBERT 키워드 추출 시작 - 텍스트 길이: 1,247 문자
📥 KeyBERT 모델 'all-MiniLM-L6-v2' 로드 시작...
✅ KeyBERT 모델 'all-MiniLM-L6-v2' 로드 성공 (0.8초)
⚙️ KeyBERT 설정 - 알고리즘: MMR, 최대키워드: 10, n-gram: (1, 2), 다양성: 0.5
🧠 MMR 알고리즘으로 키워드 추출 중 (다양성: 0.5)...
🔍 KeyBERT 원시 결과 (8개): 머신러닝(0.856), 딥러닝(0.743), 인공지능(0.621)
📍 '머신러닝' (점수: 0.856) - 위치: 15-19, 컨텍스트: '현대 기술에서 머신러닝과...'
📋 KeyBERT 키워드 처리 완료 - 총 8개 (위치있음: 6, 추상: 2)  
✅ KeyBERT 추출 완료 - 8개 키워드, 상위: 머신러닝(0.856), 딥러닝(0.743)
```

---

## 최적화 팁

### 1. 모델 선택 전략
```python
# 용도별 최적 모델
use_cases = {
    "한국어 논문/보고서": "jhgan/ko-sroberta-multitask",
    "다국어 일반 문서": "all-MiniLM-L6-v2", 
    "영어 기술 문서": "all-mpnet-base-v2",
    "빠른 처리 필요": "all-MiniLM-L6-v2",
    "최고 품질 필요": "paraphrase-multilingual-mpnet-base-v2"
}
```

### 2. 매개변수 튜닝
```python
# 문서 유형별 권장 설정
parameter_tuning = {
    "뉴스/블로그": {
        "ngram_range": (1, 2),
        "max_keywords": 8,
        "diversity": 0.5
    },
    "학술논문": {
        "ngram_range": (1, 3), 
        "max_keywords": 15,
        "diversity": 0.3
    },
    "기술문서": {
        "ngram_range": (1, 4),
        "max_keywords": 12,  
        "diversity": 0.4
    }
}
```

### 3. 성능 최적화
```python
# 대용량 처리 시 최적화
optimization_tips = {
    "배치 처리": "여러 문서를 한번에 임베딩",
    "캐시 활용": "모델과 임베딩 결과 캐싱",
    "병렬 처리": "다중 프로세스로 처리 분산",
    "메모리 관리": "큰 문서는 청크 단위로 분할"
}
```

---

**작성일**: 2025년 8월 7일  
**DocExtract 프로젝트**: KeyBERT 키워드 추출기 구현 가이드