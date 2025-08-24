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