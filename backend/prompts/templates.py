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

문서 내용:
{text}

### 분석 지침:

1. **문서 기본정보 추출**
   - 제목, 부제목
   - 저자/작성자 정보
   - 발행일자, 발행기관
   - 문서유형 (보고서/논문/정책자료 등)
   - 문서번호나 식별자

2. **구조 분석**
   - 장(Chapter) 및 절(Section) 단위로 계층구조 파악
   - 각 단위별 제목과 페이지 범위
   - 주요 내용 요약 (2-3문장)
   - 핵심 키워드 추출 (5-10개)

3. **내용 분석**
   - 문서의 주요 주제와 목적
   - 핵심 논점이나 연구질문
   - 주요 발견사항이나 결론
   - 정책제언이나 시사점

4. **데이터 추출**
   - 주요 통계수치나 정량적 데이터
   - 중요 날짜나 시점
   - 인용된 법규나 제도
   - 참조된 기관이나 조직명

5. **메타정보 도출**
   - 연구방법론 (해당시)
   - 대상 독자층
   - 활용 가능 분야
   - 관련 주제 분류

### 출력 형식:

```json
{{
  "문서정보": {{
    "제목": "",
    "부제목": "",
    "문서유형": "",
    "발행정보": {{
      "발행일자": "",
      "발행기관": "",
      "문서번호": ""
    }},
    "저자정보": [
      {{
        "이름": "",
        "소속": "",
        "역할": ""
      }}
    ]
  }},
  
  "구조분석": [
    {{
      "단위": "장/절",
      "제목": "",
      "페이지": "",
      "주요내용": "",
      "키워드": [],
      "하위구조": [
        {{
          "단위": "소절",
          "제목": "",
          "주요내용": "",
          "키워드": []
        }}
      ]
    }}
  ],
  
  "핵심내용": {{
    "주제": [],
    "목적": "",
    "주요발견": [],
    "결론": [],
    "제언": []
  }},
  
  "주요데이터": {{
    "통계": {{
      "수치명": "값",
      "단위": "설명"
    }},
    "일자": {{
      "기준일": "",
      "중요시점": []
    }},
    "제도": [],
    "기관": []
  }},
  
  "메타정보": {{
    "방법론": "",
    "대상독자": "",
    "활용분야": [],
    "분류태그": []
  }}
}}
```

JSON 형식으로만 응답해주세요:"""
    )
    
    # 간단한 구조 분석 프롬프트
    SIMPLE_STRUCTURE_ANALYSIS = PromptTemplate(
        """문서의 기본 구조를 분석해주세요.

문서 내용:
{text}

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
{
  "graph": {
    "nodes": [
      {
        "id": "string",
        "type": "string",
        "properties": {}
      }
    ],
    "edges": [
      {
        "id": "string",
        "source": "string",
        "target": "string",
        "type": "string",
        "properties": {}
      }
    ]
  },
  "metadata": {
    "version": "1.0",
    "node_count": 0,
    "edge_count": 0,
    "extraction_date": "YYYY-MM-DD"
  }
}
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
{
  "graph": {
    "nodes": [
      {
        "id": "country_1",
        "type": "Country",
        "properties": {
          "name": "일본",
          "code": "JP",
          "aging_rate": 23.3,
          "reference_year": 2011
        }
      },
      {
        "id": "phase_1",
        "type": "Phase",
        "properties": {
          "name": "고령화사회",
          "threshold": 7.0,
          "description": "65세 이상 인구 7% 이상"
        }
      }
    ],
    "edges": [
      {
        "id": "edge_1",
        "source": "country_1",
        "target": "phase_1",
        "type": "ENTERED_PHASE",
        "properties": {
          "year": 1970,
          "rate": 7.0
        }
      }
    ]
  },
  "metadata": {
    "version": "1.0",
    "node_count": 2,
    "edge_count": 1,
    "extraction_date": "2024-01-01"
  }
}
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