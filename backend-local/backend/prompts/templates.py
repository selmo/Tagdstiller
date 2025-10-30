"""
LLM 프롬프트 템플릿 정의

이 파일은 DocExtract 시스템에서 사용하는 모든 LLM 프롬프트 템플릿을 관리합니다.
템플릿은 용도별로 분류되어 있으며, 설정을 통해 커스터마이징할 수 있습니다.
"""

from typing import Dict, Any, Optional
import json


class PromptTemplate:
    """프롬프트 템플릿 기본 클래스"""
    
    def __init__(self, template: str, variables: Dict[str, Any] = None):
        self.template = template
        self.variables = variables or {}
    
    def format(self, **kwargs) -> str:
        """템플릿에 변수를 적용하여 최종 프롬프트 생성"""
        format_vars = {**self.variables, **kwargs}
        return self.template.format(**format_vars)
    
    def validate_variables(self, **kwargs) -> bool:
        """필수 변수가 모두 제공되었는지 확인"""
        import re
        required_vars = re.findall(r'\{(\w+)\}', self.template)
        provided_vars = set(self.variables.keys()) | set(kwargs.keys())
        return all(var in provided_vars for var in required_vars)


class KeywordExtractionPrompts:
    """키워드 추출용 프롬프트 템플릿들"""
    
    # 기본 키워드 추출 프롬프트 (영어)
    BASIC_EXTRACTION_EN = PromptTemplate(
        """You are a keyword extraction system. Extract exactly {max_keywords} important keywords from the text below.

Text: {text}

Return ONLY a JSON array with this exact format (no other text):
[{{"keyword":"word1","score":0.9,"category":"noun"}},{{"keyword":"word2","score":0.8,"category":"technology"}}]

Instructions:
- Focus on meaningful nouns, technical terms, and key concepts
- Assign relevance scores between 0.0 and 1.0
- Use categories like: noun, technology, person, organization, concept, method
- Limit each keyword to 1-3 words
- Avoid common words and stopwords

Output:"""
    )
    
    # 한국어 키워드 추출 프롬프트
    BASIC_EXTRACTION_KO = PromptTemplate(
        """당신은 키워드 추출 시스템입니다. 아래 텍스트에서 정확히 {max_keywords}개의 중요한 키워드를 추출하세요.

텍스트: {text}

다음 JSON 배열 형식으로만 응답하세요 (다른 텍스트 없이):
[{{"keyword":"키워드1","score":0.9,"category":"명사"}},{{"keyword":"키워드2","score":0.8,"category":"기술"}}]

지침:
- 의미있는 명사, 전문용어, 핵심 개념에 집중
- 관련성 점수는 0.0에서 1.0 사이로 지정
- 카테고리 예시: 명사, 기술, 인물, 조직, 개념, 방법론, 분야
- 각 키워드는 1-3 단어로 제한
- 일반적인 단어나 불용어는 피하세요

출력:"""
    )
    
    # 학술 문서용 키워드 추출 프롬프트
    ACADEMIC_EXTRACTION = PromptTemplate(
        """You are an academic keyword extraction system. Extract {max_keywords} scholarly keywords from the research text below.

Text: {text}

Return ONLY a JSON array with this exact format:
[{{"keyword":"research_term","score":0.95,"category":"methodology"}},{{"keyword":"domain_concept","score":0.90,"category":"theory"}}]

Focus on:
- Research methodologies and approaches
- Theoretical concepts and frameworks
- Technical terminology
- Academic disciplines and fields
- Key findings and conclusions

Categories to use: methodology, theory, technique, field, finding, concept, model, analysis

Output:"""
    )
    
    # 기술 문서용 키워드 추출 프롬프트
    TECHNICAL_EXTRACTION = PromptTemplate(
        """You are a technical keyword extraction system. Extract {max_keywords} technical keywords from the documentation below.

Text: {text}

Return ONLY a JSON array with this exact format:
[{{"keyword":"technology_name","score":0.95,"category":"technology"}},{{"keyword":"programming_concept","score":0.90,"category":"concept"}}]

Focus on:
- Programming languages and frameworks
- Software tools and platforms
- Technical methodologies
- System architectures
- Implementation details

Categories to use: technology, framework, tool, architecture, concept, method, platform, language

Output:"""
    )


class DocumentSummaryPrompts:
    """문서 요약용 프롬프트 템플릿들"""
    
    # 기본 문서 요약 프롬프트 (한국어)
    BASIC_SUMMARY_KO = PromptTemplate(
        """다음 문서를 분석하여 5가지 유형의 요약을 생성해주세요. 각 요약은 간결하고 핵심적인 내용으로 작성해주세요.

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
    )
    
    # 영어 문서 요약 프롬프트
    BASIC_SUMMARY_EN = PromptTemplate(
        """Analyze the following document and generate 5 types of summaries. Each summary should be concise and capture the essential content.

Document content:
{text}

Respond in the following JSON format:
{{
  "intro": "Summarize the introduction or opening section in one sentence",
  "conclusion": "Summarize the conclusion or closing section in one sentence", 
  "core": "Summarize the most essential content of the document in one sentence",
  "topics": ["main", "keyword", "list", "up to", "five"],
  "tone": "Overall tone or character of the document (e.g., formal, academic, technical, explanatory, informational)"
}}

Respond only in JSON format:"""
    )
    
    # 학술 문서 요약 프롬프트
    ACADEMIC_SUMMARY = PromptTemplate(
        """Analyze this academic document and provide a structured summary for research purposes.

Document content:
{text}

Respond in the following JSON format:
{{
  "abstract": "One-sentence abstract of the research",
  "methodology": "Brief description of research methods used",
  "findings": "Key findings or results in one sentence",
  "implications": "Research implications or significance",
  "keywords": ["academic", "research", "terms", "up to", "six"],
  "field": "Primary academic field or discipline"
}}

JSON format only:"""
    )
    
    # 기술 문서 요약 프롬프트
    TECHNICAL_SUMMARY = PromptTemplate(
        """Analyze this technical document and provide a structured summary for development purposes.

Document content:
{text}

Respond in the following JSON format:
{{
  "purpose": "Main purpose or goal of the technical content",
  "approach": "Technical approach or methodology described",
  "implementation": "Key implementation details or steps",
  "requirements": "Technical requirements or dependencies",
  "keywords": ["technical", "development", "terms", "up to", "six"],
  "complexity": "Technical complexity level (basic, intermediate, advanced, expert)"
}}

JSON format only:"""
    )


class MetadataExtractionPrompts:
    """메타데이터 추출용 프롬프트 템플릿들"""
    
    # 기본 메타데이터 분석 프롬프트
    BASIC_METADATA = PromptTemplate(
        """문서의 메타데이터를 분석하여 구조화된 정보를 추출해주세요.

문서 내용:
{text}

다음 JSON 형식으로 응답해주세요:
{{
  "document_type": "문서 유형 (보고서, 논문, 매뉴얼, 프레젠테이션 등)",
  "language": "주요 언어",
  "formality": "문서의 격식 수준 (공식적, 비공식적, 학술적)",
  "structure": {{
    "has_titles": true,
    "has_lists": false,
    "has_tables": false,
    "has_references": false
  }},
  "content_features": ["특징1", "특징2", "특징3"],
  "target_audience": "대상 독자층",
  "estimated_length": "문서 길이 추정 (짧음, 보통, 김, 매우김)"
}}

JSON 형식으로만 응답하세요:"""
    )


class DocumentStructurePrompts:
    """문서 구조 분석용 프롬프트 템플릿들"""
    
    # LLM 기반 문서 구조 분석 프롬프트
    STRUCTURE_ANALYSIS_LLM = PromptTemplate(
        """당신은 문서 분석 전문가입니다. 제공된 문서를 체계적으로 분석하여 구조화된 정보를 JSON 형식으로 추출해주세요.

**중요**: 제공된 문서가 마크다운 형식일 수 있습니다. 마크다운 구문을 정확히 해석하여 문서 구조를 파악하세요.

문서 내용:
```
{text}
```

### 마크다운 형식 처리 지침:
- `# 제목`: 1레벨 헤더 (장/Chapter)
- `## 제목`: 2레벨 헤더 (절/Section)
- `### 제목`: 3레벨 헤더 (소절/Subsection)
- `#### 제목`: 4레벨 헤더 (소소절/Subsubsection)
- `- 항목` 또는 `* 항목`: 리스트 항목
- `| 컬럼1 | 컬럼2 |`: 테이블 구조
- ``` 코드 ```: 코드 블록 (내용으로 처리)
- **굵은글씨**, *기울임*: 강조 표현 (일반 텍스트로 처리)

### 분석 지침:

1. **문서 기본정보 추출**
   - 제목, 부제목
   - 저자/작성자 정보
   - 발행일자, 발행기관
   - 문서유형 (보고서/논문/정책자료 등)
   - 문서번호나 식별자

2. **구조 분석**
   - 장(Chapter) 및 절(Section), 소절(Subsection), 소소절(Subsubsection) 단위로 계층구조 파악
   - 각 단위별 제목과 페이지 범위
   - 주요 내용 요약 (2-3문장, `mainContent` 필드에 작성, 150자 이내)
   - 모든 구조 항목은 반드시 `subStructure` 배열을 포함하고, 하위 구조가 없을 경우 빈 배열([])을 명시
   - 각 구조 항목의 필수 키: `unit`, `number`, `title`, `pageRange`, `mainContent`, `keywords`, `classificationTags`, `subStructure`
   - `unit` 필드는 `장`, `절`, `소절`, `소소절`, `chapter`, `section`, `subsection`, `subsubsection` 중 하나만 사용
   - `number` 필드는 숫자만 포함 (문자열로 입력해도 무방하나 숫자 외 문자는 금지)
   - `subStructure`에 포함된 항목도 동일한 필드 구성을 유지하며 추가적인 하위 구조를 재귀적으로 포함
   - 상위 구조는 중요도 기준 상위 6개까지만 포함하고, 각 구조의 `subStructure`는 상위 4개까지만 포함 (그 이하 레벨도 동일 기준 적용, 최대 3개)
   - 전체 `structureAnalysis` 출력 길이는 10,000자 이내로 유지
   - 중요도가 낮거나 유사한 항목은 합쳐 간단히 요약하고, 세부 내용은 `mainContent`에 통합
   - 제목이 없거나 불분명한 경우 `title` 필드에 간결한 요약 제목을 생성해 채울 것
   - `keywords`와 `classificationTags`는 각 항목마다 최대 3개만 제공 (핵심 용어 위주)
   - 각 키워드에 대한 정의와 설명적 기술 포함 (각 설명은 80자 이내)
   - 해당 구조의 분류 태그 및 설명 포함

3. **내용 분석**
   - 문서의 주요 주제와 목적
   - 핵심 논점이나 연구질문
   - 주요 발견사항이나 결론
   - 정책제언이나 시사점
   - 전체 내용에 대한 키워드와 분류 태그 포함

4. **데이터 추출**
   - 주요 통계수치나 정량적 데이터
   - 중요 날짜나 시점
   - 인용된 법규나 제도
   - 참조된 기관이나 조직명

5. **메타정보 도출**
   - 연구방법론 (해당시)
   - 대상 독자층
   - 활용 가능 분야
   - 관련 주제 분류 (상세 정보 포함)
   - 문서 전체 키워드 (상세 정보 포함) 

### 키워드 및 분류 태그 형식:
- **keywords**: 각 키워드는 name(용어명), desc(정의 설명), readme(상세 기술)를 포함
- **classificationTags**: 각 분류는 name(분류명), desc(분류 정의), readme(분류 상세 설명)을 포함
- keywords와 classificationTags는 구조의 모든 관련 위치에 함께 포함

### 키워드 추출 제외 대상 (일반적 단어):
**문서 구조 관련**: 목차, 개요, 서론, 결론, 부록, 참고문헌, 색인, 머리말, 맺음말, 요약, 초록
**일반 형식어**: 문서, 보고서, 자료, 내용, 정보, 데이터, 현황, 상황, 방안, 대책, 계획, 정책
**시간 표현**: 년도, 월, 일, 오늘, 현재, 과거, 미래, 최근, 당시
**위치/순서**: 첫째, 둘째, 다음, 이전, 위, 아래, 앞, 뒤
**연결어**: 그리고, 또한, 하지만, 따라서, 그러므로, 즉, 예를 들어
**형식어**: 그림, 표, 도표, 차트, 페이지, 장, 절, 항목, 번호

### 키워드 선정 기준:
1. **전문성**: 해당 분야의 전문 용어나 고유 개념
2. **구체성**: 추상적이지 않은 구체적인 대상이나 방법
3. **의미성**: 문서의 핵심 내용을 나타내는 의미 있는 용어
4. **차별성**: 다른 문서와 구별되는 고유한 특성을 나타내는 용어

### 키워드 선정 예시:
**나쁜 키워드 (추출 금지)**:
- "목차", "서론", "결론" (문서 구조어)
- "문서", "자료", "내용" (일반적 형식어)
- "현재", "최근", "앞으로" (시간 표현)
- "첫째", "둘째", "다음" (순서어)
- "방안", "대책", "정책" (추상적 일반어)

**좋은 키워드 (추출 권장)**:
- "도로터널", "결로현상", "방수공법" (구체적 전문용어)
- "IoT센서", "빅데이터분석", "머신러닝" (기술용어)
- "탄소중립", "신재생에너지", "ESG경영" (특화 개념)
- "디지털전환", "블록체인", "메타버스" (혁신기술)
- "감염병대응", "백신개발", "방역시스템" (분야별 전문용어)

### 응답 예시 (정확한 JSON 형식):

응답은 반드시 다음과 같은 순수한 JSON 구조여야 합니다:

- documentInfo: 문서의 기본 정보
- structureAnalysis: 문서의 구조적 분석 (배열)
- coreContent: 핵심 내용 분석
- keyData: 핵심 데이터 추출
- metaInfo: 메타 정보

각 섹션의 keywords와 classificationTags는 다음 구조를 따라야 합니다:
- name: 키워드/분류명 (문자열)
- desc: 간단한 정의 (문자열)
- readme: 상세 설명 (문자열)

모든 필드는 빈 문자열이라도 반드시 포함해야 합니다.

### 출력 형식 제약:
- 순수 JSON만 반환 (추가 텍스트, 설명, 마크다운, 코드 블록 ``` 금지)
- 모든 객체/배열은 반드시 닫힌 형태로 완결된 JSON이어야 함
   - JSON 마지막에는 닫는 중괄호로 정상 종료하고 개행으로 마무리
- 숫자나 null 표기는 표준 JSON 규칙을 따름

### 정확한 JSON 예시:

{{
  "documentInfo": {{
    "title": "도로터널 결로대책 가이드라인",
    "subtitle": "터널 내부 습도 관리 및 구조물 보호 방안",
    "author": "국토교통부",
    "publishDate": "2024-03-15",
    "publisher": "한국도로공사",
    "documentType": "기술지침서",
    "documentId": "MOLIT-2024-001",
    "keywords": [
      {{
        "name": "결로대책",
        "desc": "터널 결로를 억제하기 위한 기술",
        "readme": "환기·제습·단열을 조합한 종합 대응"
      }}
    ],
    "classificationTags": [
      {{
        "name": "터널공학",
        "desc": "터널 설계와 시공을 다루는 분야",
        "readme": "지하구조물의 안전성과 유지관리 기술"
      }}
    ]
  }},
  "structureAnalysis": [
    {{
      "unit": "장",
      "number": "1",
      "title": "결로현상 개요",
      "pageRange": "1-12",
      "mainContent": "결로 발생의 물리 원리와 터널 환경 특성을 요약한다.",
      "keywords": [
        {{
          "name": "결로",
          "desc": "수증기가 물방울로 변하는 현상",
          "readme": "터널 내 온습도 차이로 벽면에 응결수가 형성"
        }},
        {{
          "name": "이슬점",
          "desc": "결로가 시작되는 임계 온도",
          "readme": "주어진 습도에서 수증기가 응축하기 시작하는 조건"
        }}
      ],
      "classificationTags": [
        {{
          "name": "물리현상",
          "desc": "자연계 물리 변화를 다루는 분야",
          "readme": "온도와 습도 변화가 만드는 상변화"
        }},
        {{
          "name": "환경조건",
          "desc": "주변 환경이 미치는 영향",
          "readme": "기온·환기·지하수 등 결로를 좌우하는 변수"
        }}
      ],
      "subStructure": [
        {{
          "unit": "절",
          "number": "1.1",
          "title": "결로 발생 원리",
          "pageRange": "1-6",
          "mainContent": "열전달과 습공기 이론으로 결로 임계 조건을 설명한다.",
          "keywords": [
            {{
              "name": "열교환",
              "desc": "온도 차에 따른 에너지 이동",
              "readme": "터널 벽면과 공기 사이의 열전달 과정"
            }}
          ],
          "classificationTags": [
            {{
              "name": "열역학",
              "desc": "에너지 변환을 연구하는 학문",
              "readme": "상변화와 에너지 보존 법칙을 활용"
            }}
          ],
          "subStructure": [
            {{
              "unit": "소절",
              "number": "1.1.1",
              "title": "임계 조건",
              "pageRange": "4-6",
              "mainContent": "이슬점 계산과 벽면 온도 유지 방법을 요약한다.",
              "keywords": [
                {{
                  "name": "이슬점 계산",
                  "desc": "온도·습도 기반 결로 판정 방법",
                  "readme": "환기량과 표면온도를 고려한 임계 분석"
                }}
              ],
              "classificationTags": [
                {{
                  "name": "환경모델",
                  "desc": "환경 조건을 수치화한 모델",
                  "readme": "온습도 조합을 반영한 결로 시뮬레이션"
                }}
              ],
              "subStructure": []
            }}
          ]
        }},
        {{
          "unit": "절",
          "number": "1.2",
          "title": "터널 환경 요인",
          "pageRange": "7-12",
          "mainContent": "환기, 지하수, 교통량 등 결로에 영향을 주는 주요 요인을 정리한다.",
          "keywords": [
            {{
              "name": "환기",
              "desc": "공기를 순환시키는 과정",
              "readme": "기계·자연 환기로 습도를 조절"
            }}
          ],
          "classificationTags": [
            {{
              "name": "환경공학",
              "desc": "환경 문제를 공학적으로 해결하는 분야",
              "readme": "터널 공조와 습도 제어 기술"
            }}
          ],
          "subStructure": []
        }}
      ]
    }},
    {{
      "unit": "장",
      "number": "2",
      "title": "결로 대응 전략",
      "pageRange": "13-24",
      "mainContent": "환기·제습·단열 기술을 조합한 결로 저감 전략을 제시한다.",
      "keywords": [
        {{
          "name": "제습",
          "desc": "습도를 낮추는 기술",
          "readme": "흡착식·냉각식 제습기 운용 방안"
        }}
      ],
      "classificationTags": [
        {{
          "name": "설비공학",
          "desc": "설비 시스템을 설계·운영하는 공학",
          "readme": "공조·열교환 설비 최적화"
        }}
      ],
      "subStructure": [
        {{
          "unit": "절",
          "number": "2.1",
          "title": "결로 대응시설",
          "pageRange": "13-18",
          "mainContent": "환기설비, 제습설비, 단열시설의 기능과 적용 기준을 설명한다.",
          "keywords": [
            {{
              "name": "환기설비",
              "desc": "공기 순환을 담당하는 장치",
              "readme": "팬·덕트 구성과 운전 전략"
            }}
          ],
          "classificationTags": [
            {{
              "name": "공조설계",
              "desc": "공간 공기질을 제어하는 설계",
              "readme": "풍량 계산과 장비 선정 기준"
            }}
          ],
          "subStructure": [
            {{
              "unit": "소절",
              "number": "2.1.1",
              "title": "제습기 운용",
              "pageRange": "16-18",
              "mainContent": "제습기 용량 산정과 유지관리 절차를 요약한다.",
              "keywords": [
                {{
                  "name": "유지관리",
                  "desc": "설비 성능을 유지하는 활동",
                  "readme": "필터 교체와 에너지 모니터링"
                }}
              ],
              "classificationTags": [
                {{
                  "name": "운영관리",
                  "desc": "설비 운전 계획을 수립·관리하는 분야",
                  "readme": "운전 스케줄과 점검 체계"
                }}
              ],
              "subStructure": []
            }}
          ]
        }},
        {{
          "unit": "절",
          "number": "2.2",
          "title": "운영 및 유지관리",
          "pageRange": "19-24",
          "mainContent": "모니터링, 데이터 분석, 점검 계획 수립 절차를 정리한다.",
          "keywords": [
            {{
              "name": "모니터링",
              "desc": "상태를 지속 관찰하는 활동",
              "readme": "센서 기반 습도·온도 실시간 진단"
            }}
          ],
          "classificationTags": [
            {{
              "name": "자산관리",
              "desc": "시설 자산의 수명과 가치를 관리",
              "readme": "점검 주기 설정과 기록 관리"
            }}
          ],
          "subStructure": []
        }}
      ]
    }}
  ],
  "coreContent": {{
    "mainTopic": "터널 결로 방지",
    "purpose": "결로로 인한 구조물 손상과 안전사고를 예방하기 위한 운영 지침 제시",
    "keyFindings": [
      "환기·제습·단열 결합이 결로 저감에 효과적",
      "실시간 모니터링과 유지관리 체계가 재발을 최소화"
    ],
    "recommendations": [
      "결로 다발 구간을 우선 모니터링",
      "설비 성능 지표 기반 유지관리 계획 수립"
    ],
    "keywords": [
      {{
        "name": "운영전략",
        "desc": "설비 운용 방향을 결정하는 계획",
        "readme": "목표 습도 유지와 에너지 효율 관리"
      }}
    ],
    "classificationTags": [
      {{
        "name": "인프라관리",
        "desc": "기반시설의 성능을 지속적으로 유지하는 활동",
        "readme": "점검, 보수, 리스크 관리를 포함"
      }}
    ]
  }},
  "keyData": {{
    "statistics": [
      "환기량 15% 증가 시 습도 10% 감소",
      "단열 개선 후 표면온도 3℃ 상승"
    ],
    "dates": [
      "가이드라인 제정: 2024-04-18"
    ],
    "regulations": [
      "도로터널 안전관리 지침 2024"
    ],
    "organizations": [
      "국토교통부",
      "한국도로공사"
    ]
  }},
  "metaInfo": {{
    "methodology": "문헌 조사와 현장 사례 분석",
    "targetAudience": "터널 설계·운영 담당자",
    "applicableFields": [
      "터널공학",
      "시설물 유지관리"
    ],
    "keywords": [
      {{
        "name": "습도제어",
        "desc": "공간 습도를 적정하게 유지하는 기술",
        "readme": "결로 위험 감소를 위한 공조·제습 설계"
      }}
    ],
    "classificationTags": [
      {{
        "name": "환경제어",
        "desc": "온습도 등 환경 조건을 조절하는 기술",
        "readme": "센서 데이터 기반 제어 전략"
      }}
    ]
  }}
}}

### 추가 지침:
1. **desc 필드**: 해당 키워드나 분류에 대한 간결한 정의나 설명을 작성
2. **readme 필드**: 해당 키워드나 분류에 대한 보다 상세하고 설명적인 기술을 작성
3. **일관성**: keywords와 classificationTags는 구조상 관련된 모든 위치에 함께 포함
4. **품질**: 각 키워드와 분류는 문서의 맥락에 맞는 의미 있는 정보 제공

### 분류 태그 제외 대상 (일반적 분류):
**일반적 분류**: 일반, 기본, 표준, 공통, 보편, 전체, 종합, 기타, 미분류
**형식 분류**: 텍스트, 문서, 파일, 자료, 내용물, 정보물
**시간 분류**: 과거, 현재, 미래, 최신, 구식, 임시

### 분류 태그 선정 예시:
**나쁜 분류 (사용 금지)**:
- "일반", "기본", "표준" (너무 추상적)
- "문서", "자료", "정보" (형식적 분류)
- "전체", "종합", "기타" (의미 없는 분류)

**좋은 분류 (사용 권장)**:
- "건설기술", "교통인프라", "환경공학" (전문분야)
- "AI기술", "데이터사이언스", "클라우드컴퓨팅" (기술영역)
- "정책연구", "경제분석", "사회조사" (연구방법)
- "보건의료", "교육혁신", "문화콘텐츠" (주제영역)

### JSON 응답 규칙 (필수 준수):
1. **표준 JSON 형식**: 반드시 유효한 JSON으로 응답
2. **인용부호**: 모든 문자열은 이중 인용부호(") 사용, 단일 인용부호(') 금지
3. **필드 완성도**: 키워드/분류 객체는 name, desc, readme 필드 모두 포함
4. **쉼표 규칙**: 마지막 항목 뒤에 쉼표 사용 금지
5. **순수 JSON**: JSON 외 설명, 주석, 추가 텍스트 금지
6. **키워드 품질**: 위의 제외 대상 단어들은 키워드/분류로 사용 금지
7. **구조 완성**: 모든 중괄호와 대괄호 올바르게 닫기

**중요**: 설명 없이 순수 JSON만 제공하고, 코드블록( ``` )이나 추가 텍스트를 절대 포함하지 마세요.

순수한 JSON만 응답:"""
    )

    STRUCTURE_ANALYSIS_LLM_GEMINI_FLASH25 = PromptTemplate(
        STRUCTURE_ANALYSIS_LLM.template
        + """

### Gemini Flash 2.5 추가 엄수 규칙:
- 마크다운 코드 펜스(\`\`\` 등)나 설명 문장을 절대 포함하지 말 것
- JSON 외의 텍스트, 이모지, 주석, 경고 문구를 응답 앞뒤에 추가하지 말 것
- 문자열 내 줄바꿈이 필요하면 반드시 `\\n`과 같이 이스케이프한 제어문자를 사용할 것 (원시 개행 금지)
- 숫자는 숫자 타입으로, 불리언은 true/false, null 은 소문자 null 로 표현할 것
- 모든 배열과 객체는 JSON 스펙에 맞게 콤마/괄호를 정확히 닫고 종료 후 개행 1회만 추가할 것
- 요구된 필드 외의 임의 필드는 생성하지 말고, 필수 필드가 비어도 빈 문자열("") 또는 빈 배열([])로 유지할 것
- JSON Schema 검증에 실패할 수 있는 제어문자, 비가시 문자(U+0000~U+001F, U+007F~U+009F)는 사용하지 말 것
"""
    )
    
    # 간단한 구조 분석 프롬프트
    SIMPLE_STRUCTURE_ANALYSIS = PromptTemplate(
        """문서의 기본 구조를 분석해주세요.

문서 내용:
```
{text}
```

다음 JSON 형식으로 응답해주세요:
{{
  "제목": "문서 제목",
  "문서유형": "보고서/논문/매뉴얼 등",
  "주요섹션": [
    {{
      "번호": "1",
      "제목": "섹션 제목",
      "내용요약": "2-3문장 요약"
    }}
  ],
  "핵심키워드": [],
  "주요통계": [],
  "결론": "문서의 핵심 결론"
}}

JSON 형식으로만 응답하세요:"""
    )


class KnowledgeGraphPrompts:
    """도메인별 지식그래프 추출용 프롬프트 템플릿들"""
    
    # 기본 KG 추출 프롬프트
    BASIC_KG_EXTRACTION = PromptTemplate(
        """문서에서 지식 그래프를 구성할 엔티티와 관계를 추출해주세요.

문서 내용:
{text}

문서 도메인: {domain}
구조 정보: {structure_info}

다음 JSON 형식으로 응답해주세요:
{{
  "entities": [
    {{"id": "entity_1", "type": "Document", "properties": {{"title": "문서명", "domain": "{domain}"}}}},
    {{"id": "entity_2", "type": "Concept", "properties": {{"name": "개념명", "category": "기술"}}}},
    {{"id": "entity_3", "type": "Keyword", "properties": {{"text": "키워드", "score": 0.9}}}}
  ],
  "relationships": [
    {{"source": "entity_1", "target": "entity_2", "type": "RELATED_TO", "properties": {{"relationship_name": "CONTAINS_CONCEPT", "context": "언급맥락"}}}},
    {{"source": "entity_1", "target": "entity_3", "type": "RELATED_TO", "properties": {{"relationship_name": "HAS_KEYWORD", "relevance": 0.8}}}}
  ]
}}

지침:
- 엔티티 ID는 고유해야 합니다
- 관계의 relationship_name에 구체적인 관계 유형을 명시하세요
- 도메인에 적합한 엔티티 타입을 사용하세요

JSON 형식으로만 응답하세요:"""
    )
    
    # 기술 문서용 KG 추출 프롬프트
    TECHNICAL_KG_EXTRACTION = PromptTemplate(
        """기술 문서에서 지식 그래프를 구성할 엔티티와 관계를 추출해주세요.

문서 내용:
{text}

구조 정보: {structure_info}

다음 JSON 형식으로 응답해주세요:
{{
  "entities": [
    {{"id": "doc_1", "type": "Document", "properties": {{"title": "기술문서명", "domain": "technical"}}}},
    {{"id": "tech_1", "type": "Technology", "properties": {{"name": "기술명", "version": "v1.0", "category": "software"}}}},
    {{"id": "api_1", "type": "API", "properties": {{"name": "API명", "endpoint": "/api/v1", "method": "GET"}}}},
    {{"id": "func_1", "type": "Function", "properties": {{"name": "함수명", "parameters": ["param1", "param2"], "return_type": "string"}}}}
  ],
  "relationships": [
    {{"source": "doc_1", "target": "tech_1", "type": "RELATED_TO", "properties": {{"relationship_name": "USES", "context": "기술 사용 맥락"}}}},
    {{"source": "tech_1", "target": "api_1", "type": "RELATED_TO", "properties": {{"relationship_name": "PROVIDES", "version": "1.0"}}}},
    {{"source": "api_1", "target": "func_1", "type": "RELATED_TO", "properties": {{"relationship_name": "IMPLEMENTS", "role": "handler"}}}}
  ]
}}

엔티티 타입 사용: Technology, API, Function, Class, Database, Server, Framework, Tool, Algorithm, Protocol
관계명 사용: DEPENDS_ON, IMPLEMENTS, EXTENDS, USES, CALLS, CONNECTS_TO, CONFIGURED_BY, STORES_IN, RUNS_ON

JSON 형식으로만 응답하세요:"""
    )
    
    # 학술 문서용 KG 추출 프롬프트
    ACADEMIC_KG_EXTRACTION = PromptTemplate(
        """학술 문서에서 지식 그래프를 구성할 엔티티와 관계를 추출해주세요.

문서 내용:
{text}

구조 정보: {structure_info}

다음 JSON 형식으로 응답해주세요:
{{
  "entities": [
    {{"id": "doc_1", "type": "Document", "properties": {{"title": "논문제목", "domain": "academic"}}}},
    {{"id": "author_1", "type": "Author", "properties": {{"name": "저자명", "affiliation": "소속기관"}}}},
    {{"id": "method_1", "type": "Research_Method", "properties": {{"name": "연구방법", "type": "실험연구"}}}},
    {{"id": "finding_1", "type": "Finding", "properties": {{"description": "주요발견", "significance": "중요도"}}}}
  ],
  "relationships": [
    {{"source": "doc_1", "target": "author_1", "type": "RELATED_TO", "properties": {{"relationship_name": "AUTHORED_BY", "role": "first_author"}}}},
    {{"source": "author_1", "target": "method_1", "type": "RELATED_TO", "properties": {{"relationship_name": "USES_METHOD", "purpose": "데이터수집"}}}},
    {{"source": "method_1", "target": "finding_1", "type": "RELATED_TO", "properties": {{"relationship_name": "PRODUCES", "confidence": 0.95}}}}
  ]
}}

엔티티 타입 사용: Author, Institution, Research_Method, Theory, Dataset, Experiment, Citation, Finding, Hypothesis, Variable
관계명 사용: CONDUCTED_BY, CITES, BUILDS_ON, PROVES, SUPPORTS, USES_METHOD, BASED_ON, VALIDATED_BY

JSON 형식으로만 응답하세요:"""
    )
    
    # 비즈니스 문서용 KG 추출 프롬프트
    BUSINESS_KG_EXTRACTION = PromptTemplate(
        """비즈니스 문서에서 지식 그래프를 구성할 엔티티와 관계를 추출해주세요.

문서 내용:
{text}

구조 정보: {structure_info}

다음 JSON 형식으로 응답해주세요:
{{
  "entities": [
    {{"id": "doc_1", "type": "Document", "properties": {{"title": "비즈니스문서명", "domain": "business"}}}},
    {{"id": "company_1", "type": "Company", "properties": {{"name": "회사명", "industry": "산업분야", "size": "대기업"}}}},
    {{"id": "product_1", "type": "Product", "properties": {{"name": "제품명", "category": "소프트웨어", "market_share": 25.3}}}},
    {{"id": "strategy_1", "type": "Strategy", "properties": {{"name": "전략명", "timeline": "2024-2026", "objectives": ["목표1", "목표2"]}}}}
  ],
  "relationships": [
    {{"source": "doc_1", "target": "company_1", "type": "RELATED_TO", "properties": {{"relationship_name": "DESCRIBES", "focus": "기업분석"}}}},
    {{"source": "company_1", "target": "product_1", "type": "RELATED_TO", "properties": {{"relationship_name": "PRODUCES", "revenue_contribution": 45.2}}}},
    {{"source": "company_1", "target": "strategy_1", "type": "RELATED_TO", "properties": {{"relationship_name": "IMPLEMENTS", "priority": "high"}}}}
  ]
}}

엔티티 타입 사용: Company, Product, Market, Stakeholder, Process, KPI, Risk, Opportunity, Strategy, Department
관계명 사용: COMPETES_WITH, SUPPLIES_TO, PARTNERS_WITH, MANAGES, MEASURES, IMPACTS, ALIGNS_WITH, SUPPORTS

JSON 형식으로만 응답하세요:"""
    )
    
    # 법률 문서용 KG 추출 프롬프트
    LEGAL_KG_EXTRACTION = PromptTemplate(
        """법률 문서에서 지식 그래프를 구성할 엔티티와 관계를 추출해주세요.

문서 내용:
{text}

구조 정보: {structure_info}

다음 JSON 형식으로 응답해주세요:
{{
  "entities": [
    {{"id": "doc_1", "type": "Document", "properties": {{"title": "법률문서명", "domain": "legal"}}}},
    {{"id": "law_1", "type": "Law", "properties": {{"name": "법률명", "jurisdiction": "대한민국", "effective_date": "2024-01-01"}}}},
    {{"id": "party_1", "type": "Party", "properties": {{"name": "당사자명", "type": "법인", "role": "계약자"}}}},
    {{"id": "obligation_1", "type": "Obligation", "properties": {{"description": "의무내용", "deadline": "2024-12-31", "penalty": "위약금"}}}}
  ],
  "relationships": [
    {{"source": "doc_1", "target": "law_1", "type": "RELATED_TO", "properties": {{"relationship_name": "GOVERNED_BY", "scope": "전체문서"}}}},
    {{"source": "party_1", "target": "obligation_1", "type": "RELATED_TO", "properties": {{"relationship_name": "OBLIGATED_TO", "enforcement": "강제"}}}},
    {{"source": "law_1", "target": "obligation_1", "type": "RELATED_TO", "properties": {{"relationship_name": "DEFINES", "article": "제12조"}}}}
  ]
}}

엔티티 타입 사용: Law, Regulation, Contract, Case, Party, Obligation, Right, Precedent
관계명 사용: GOVERNED_BY, SUBJECT_TO, CONTRACTS_WITH, REPRESENTS, OBLIGATED_TO, ENTITLED_TO, CITES_PRECEDENT

JSON 형식으로만 응답하세요:"""
    )

    GENERAL_KG_EXTRAION = PromptTemplate(
        """# PDF to Knowledge Graph Extraction Prompt

## System Instructions

You are a knowledge extraction specialist. Your task is to convert text into a structured knowledge graph in JSON format. Follow these instructions precisely.

## Input/Output Specification

**Input**: Text containing information about policies, demographics, social phenomena, or organizational data.

**Output**: Valid JSON following the exact structure below:

```json
{{
  "graph": {{
    "nodes": [
      {{
        "id": "string",
        "type": "string",
        "properties": {{}}
      }}
    ],
    "edges": [
      {{
        "id": "string",
        "source": "string",
        "target": "string",
        "type": "string",
        "properties": {{}}
      }}
    ]
  }},
  "metadata": {{
    "version": "1.0",
    "node_count": 0,
    "edge_count": 0,
    "extraction_date": "YYYY-MM-DD"
  }}
}}
```

## Entity Types and Extraction Rules

### 1. Core Entity Types

| Entity Type | Required Properties | Optional Properties | ID Format |
|------------|-------------------|-------------------|-----------|
| Country | name, code | current_stats, year | country_{seq} |
| Policy | name, year, type | description, law_number | policy_{seq} |
| Demographic | name | age_range, birth_years, population | demo_{seq} |
| Institution | name, type | role, sector | inst_{seq} |
| Impact | name, type, severity | description, metrics | impact_{seq} |
| Strategy | name, type | target, implementation_year | strategy_{seq} |
| Phase | name, threshold | description, criteria | phase_{seq} |
| Challenge | name, severity | country, description | challenge_{seq} |
| FinancialProduct | name, type | provider, target_group | product_{seq} |

### 2. Relationship Types

| Edge Type | Usage | Required Properties |
|----------|-------|-------------------|
| ENTERED_PHASE | Country → Phase | year, rate |
| EXPECTED_TO_ENTER | Country → Phase | year, projected_rate |
| IMPLEMENTS | Country/Institution → Policy/Strategy | start_year |
| CAUSES | Event/Phase → Impact | severity |
| PROVIDES | Institution → Product/Service | since_year |
| FACES | Country → Challenge | severity |
| NEEDS | Country → Strategy/Policy | urgency |
| BASED_ON | Policy → Policy | relationship_type |
| HAS_DEMOGRAPHIC | Country → Demographic | percentage |

## Extraction Guidelines

### Step 1: Entity Identification
```
SCAN FOR:
- Years (4-digit numbers between 1900-2100)
- Percentages (N% or N.N%)
- Proper nouns (capitalized terms)
- Policy/Law names (in quotes or with 法/Act/Law)
- Monetary values (with currency symbols/units)
- Age ranges (N세, N-N세, N years)
```

### Step 2: Relationship Extraction
```
IDENTIFY PATTERNS:
- Temporal: "In [YEAR], [ENTITY] became/reached/entered [STATE]"
- Causal: "[A] leads to/causes/results in [B]"
- Implementation: "[ACTOR] implements/adopts/introduces [POLICY]"
- Provision: "[INSTITUTION] provides/offers [SERVICE]"
```

### Step 3: Property Assignment
```
FOR EACH ENTITY:
- Assign all numeric values found within 50 characters
- Include units for all measurements
- Preserve original language terms
- Add contextual description if available
```

## Special Processing Rules

1. **Temporal Data**:
   - Convert all years to integers
   - For year ranges, create separate properties: start_year, end_year
   - If only decade mentioned (e.g., "1990s"), use start year (1990)

2. **Percentage Handling**:
   - Always store as float (7% → 7.0)
   - Include context as separate property (e.g., "rate_type": "aging")

3. **Multi-language Content**:
   - Preserve original terms in name field
   - Add translation in description if needed
   - Use original language for official document names

4. **Hierarchical Relationships**:
   - Create parent-child relationships for policy structures
   - Link demographic groups to parent populations
   - Connect phases in sequential order

## Validation Rules

✓ Every node must have: id, type, properties.name
✓ Every edge must have: id, source, target, type
✓ All edge source/target must reference existing node IDs
✓ Years must be integers between 1900-2100
✓ Percentages must be floats between 0-100
✓ No duplicate node IDs
✓ Metadata must include accurate counts

## Error Handling

| Situation | Action |
|-----------|--------|
| Ambiguous year | Use earliest mentioned year |
| Missing percentage context | Add to most relevant nearby entity |
| Unclear relationship | Skip edge creation |
| Duplicate entity names | Append _2, _3 to ID |
| Long descriptions | Truncate to 500 characters |

## Output Example

```json
{{
  "graph": {{
    "nodes": [
      {{
        "id": "country_1",
        "type": "Country",
        "properties": {{
          "name": "일본",
          "code": "JP",
          "aging_rate": 23.3,
          "reference_year": 2011
        }}
      }},
      {{
        "id": "phase_1",
        "type": "Phase",
        "properties": {{
          "name": "고령화사회",
          "threshold": 7.0,
          "description": "65세 이상 인구 7% 이상"
        }}
      }}
    ],
    "edges": [
      {{
        "id": "edge_1",
        "source": "country_1",
        "target": "phase_1",
        "type": "ENTERED_PHASE",
        "properties": {{
          "year": 1970,
          "rate": 7.0
        }}
      }}
    ]
  }},
  "metadata": {{
    "version": "1.0",
    "node_count": 2,
    "edge_count": 1,
    "extraction_date": "2024-01-01"
  }}
}}
```

## Processing Instructions

1. Read the entire text first
2. Extract all entities matching the types above
3. Identify relationships between entities
4. Build the JSON structure
5. Validate against rules
6. Output only the JSON, no explanations

---

**INPUT TEXT:**
{text}

**OUTPUT JSON:**
""")


class PromptTemplateManager:
    """프롬프트 템플릿 관리자"""
    
    def __init__(self):
        self.templates = {
            'keyword_extraction': {
                'basic_en': KeywordExtractionPrompts.BASIC_EXTRACTION_EN,
                'basic_ko': KeywordExtractionPrompts.BASIC_EXTRACTION_KO,
                'academic': KeywordExtractionPrompts.ACADEMIC_EXTRACTION,
                'technical': KeywordExtractionPrompts.TECHNICAL_EXTRACTION,
            },
            'document_summary': {
                'basic_ko': DocumentSummaryPrompts.BASIC_SUMMARY_KO,
                'basic_en': DocumentSummaryPrompts.BASIC_SUMMARY_EN,
                'academic': DocumentSummaryPrompts.ACADEMIC_SUMMARY,
                'technical': DocumentSummaryPrompts.TECHNICAL_SUMMARY,
            },
            'metadata_extraction': {
                'basic': MetadataExtractionPrompts.BASIC_METADATA,
            },
            'knowledge_graph': {
                'basic': KnowledgeGraphPrompts.GENERAL_KG_EXTRAION,
                'technical': KnowledgeGraphPrompts.GENERAL_KG_EXTRAION,
                'academic': KnowledgeGraphPrompts.GENERAL_KG_EXTRAION,
                'business': KnowledgeGraphPrompts.GENERAL_KG_EXTRAION,
                'legal': KnowledgeGraphPrompts.GENERAL_KG_EXTRAION,
                # 'basic': KnowledgeGraphPrompts.BASIC_KG_EXTRACTION,
                # 'technical': KnowledgeGraphPrompts.TECHNICAL_KG_EXTRACTION,
                # 'academic': KnowledgeGraphPrompts.ACADEMIC_KG_EXTRACTION,
                # 'business': KnowledgeGraphPrompts.BUSINESS_KG_EXTRACTION,
                # 'legal': KnowledgeGraphPrompts.LEGAL_KG_EXTRACTION,
            }
        }
    
    def get_template(self, category: str, template_name: str) -> Optional[PromptTemplate]:
        """카테고리와 템플릿 이름으로 템플릿 가져오기"""
        return self.templates.get(category, {}).get(template_name)
    
    def list_templates(self, category: str = None) -> Dict[str, Any]:
        """사용 가능한 템플릿 목록 반환"""
        if category:
            return list(self.templates.get(category, {}).keys())
        return {cat: list(templates.keys()) for cat, templates in self.templates.items()}
    
    def add_custom_template(self, category: str, name: str, template: PromptTemplate):
        """커스텀 템플릿 추가"""
        if category not in self.templates:
            self.templates[category] = {}
        self.templates[category][name] = template
    
    def validate_template(self, category: str, template_name: str, **kwargs) -> bool:
        """템플릿 변수 유효성 검사"""
        template = self.get_template(category, template_name)
        if not template:
            return False
        return template.validate_variables(**kwargs)


# 전역 템플릿 매니저 인스턴스
template_manager = PromptTemplateManager()


def get_prompt_template(category: str, template_name: str, **kwargs) -> str:
    """프롬프트 템플릿을 가져와서 포맷팅된 문자열로 반환"""
    template = template_manager.get_template(category, template_name)
    if not template:
        raise ValueError(f"Template not found: {category}.{template_name}")
    
    if not template.validate_variables(**kwargs):
        raise ValueError(f"Missing required variables for template: {category}.{template_name}")
    
    return template.format(**kwargs)


def list_available_templates() -> Dict[str, Any]:
    """사용 가능한 모든 템플릿 목록 반환"""
    return template_manager.list_templates()
