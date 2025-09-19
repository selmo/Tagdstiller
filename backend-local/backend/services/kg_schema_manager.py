"""
Knowledge Graph Schema Manager - 도메인별 엔티티/관계 스키마 관리

문서 도메인에 따라 적절한 KG 엔티티 타입과 관계를 선택하고,
RELATED_TO 관계에 구체적인 관계명을 추가하는 기능을 제공합니다.
"""

from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import re


class DocumentDomain(Enum):
    """문서 도메인 분류"""
    TECHNICAL = "technical"
    ACADEMIC = "academic" 
    BUSINESS = "business"
    LEGAL = "legal"
    MEDICAL = "medical"
    GENERAL = "general"


class KGSchemaManager:
    """도메인별 KG 스키마 관리자"""
    
    def __init__(self):
        self.domain_schemas = self._initialize_schemas()
        self.domain_detectors = self._initialize_domain_detectors()
    
    def _initialize_schemas(self) -> Dict[str, Dict[str, Any]]:
        """도메인별 스키마 초기화"""
        return {
            DocumentDomain.TECHNICAL.value: {
                "entities": {
                    "Technology": ["name", "version", "category", "vendor"],
                    "API": ["name", "version", "endpoint", "method"],
                    "Function": ["name", "parameters", "return_type", "module"],
                    "Class": ["name", "namespace", "inheritance", "methods"],
                    "Database": ["name", "type", "schema", "connection"],
                    "Server": ["name", "type", "environment", "config"],
                    "Framework": ["name", "version", "language", "purpose"],
                    "Tool": ["name", "purpose", "platform", "license"],
                    "Algorithm": ["name", "complexity", "use_case"],
                    "Protocol": ["name", "version", "purpose", "port"]
                },
                "relationships": {
                    "기술적_의존성": ["DEPENDS_ON", "REQUIRES", "USES", "IMPORTS"],
                    "구현_관계": ["IMPLEMENTS", "EXTENDS", "OVERRIDES", "INHERITS_FROM"],
                    "통신_관계": ["CONNECTS_TO", "CALLS", "SENDS_TO", "RECEIVES_FROM"],
                    "구성_관계": ["CONFIGURED_BY", "DEPLOYED_ON", "RUNS_ON", "HOSTED_BY"],
                    "데이터_관계": ["STORES_IN", "READS_FROM", "WRITES_TO", "QUERIES"]
                }
            },
            
            DocumentDomain.ACADEMIC.value: {
                "entities": {
                    "Author": ["name", "affiliation", "email", "orcid"],
                    "Institution": ["name", "country", "type", "ranking"],
                    "Research_Method": ["name", "type", "description", "validity"],
                    "Theory": ["name", "field", "key_concepts", "originator"],
                    "Dataset": ["name", "size", "source", "format"],
                    "Experiment": ["name", "conditions", "results", "duration"],
                    "Citation": ["title", "authors", "year", "doi", "journal"],
                    "Finding": ["description", "significance", "evidence", "confidence"],
                    "Hypothesis": ["statement", "variables", "prediction"],
                    "Variable": ["name", "type", "measurement", "role"]
                },
                "relationships": {
                    "연구_관계": ["CONDUCTED_BY", "SUPERVISED_BY", "COLLABORATED_WITH"],
                    "인용_관계": ["CITES", "REFERENCES", "BUILDS_ON", "CONTRADICTS"],
                    "방법론_관계": ["USES_METHOD", "APPLIES_THEORY", "MEASURES_WITH"],
                    "결과_관계": ["PROVES", "DISPROVES", "SUPPORTS", "SUGGESTS"],
                    "데이터_관계": ["BASED_ON", "DERIVED_FROM", "VALIDATED_BY"]
                }
            },
            
            DocumentDomain.BUSINESS.value: {
                "entities": {
                    "Company": ["name", "industry", "size", "revenue"],
                    "Product": ["name", "category", "price", "market_share"],
                    "Market": ["name", "size", "growth_rate", "competition"],
                    "Stakeholder": ["name", "role", "influence", "interest"],
                    "Process": ["name", "steps", "owner", "efficiency"],
                    "KPI": ["name", "value", "target", "trend"],
                    "Risk": ["description", "probability", "impact", "mitigation"],
                    "Opportunity": ["description", "value", "timeline", "requirements"],
                    "Strategy": ["name", "objectives", "timeline", "resources"],
                    "Department": ["name", "function", "headcount", "budget"]
                },
                "relationships": {
                    "조직_관계": ["REPORTS_TO", "MANAGES", "COLLABORATES_WITH", "COMPETES_WITH"],
                    "비즈니스_관계": ["SUPPLIES_TO", "PURCHASES_FROM", "PARTNERS_WITH"],
                    "프로세스_관계": ["TRIGGERS", "DEPENDS_ON", "OPTIMIZES", "MONITORS"],
                    "성과_관계": ["MEASURES", "IMPACTS", "IMPROVES", "AFFECTS"],
                    "전략_관계": ["ALIGNS_WITH", "SUPPORTS", "CONFLICTS_WITH", "ENABLES"]
                }
            },
            
            DocumentDomain.LEGAL.value: {
                "entities": {
                    "Law": ["name", "jurisdiction", "effective_date", "category"],
                    "Regulation": ["name", "authority", "scope", "compliance"],
                    "Contract": ["parties", "terms", "duration", "value"],
                    "Case": ["name", "court", "date", "outcome"],
                    "Party": ["name", "type", "role", "representation"],
                    "Obligation": ["description", "party", "deadline", "penalty"],
                    "Right": ["description", "holder", "scope", "limitations"],
                    "Precedent": ["case", "principle", "jurisdiction", "relevance"]
                },
                "relationships": {
                    "법적_관계": ["GOVERNED_BY", "SUBJECT_TO", "EXEMPT_FROM"],
                    "당사자_관계": ["CONTRACTS_WITH", "REPRESENTS", "OPPOSES"],
                    "의무_관계": ["OBLIGATED_TO", "RESPONSIBLE_FOR", "LIABLE_FOR"],
                    "권리_관계": ["ENTITLED_TO", "GRANTS", "RESTRICTS"],
                    "판례_관계": ["CITES_PRECEDENT", "OVERRULES", "DISTINGUISHES"]
                }
            },
            
            DocumentDomain.GENERAL.value: {
                "entities": {
                    "Person": ["name", "role", "title", "contact"],
                    "Organization": ["name", "type", "location", "size"],
                    "Event": ["name", "date", "location", "participants"],
                    "Location": ["name", "type", "coordinates", "description"],
                    "Concept": ["name", "definition", "category", "importance"],
                    "Topic": ["name", "scope", "relevance", "keywords"]
                },
                "relationships": {
                    "일반_관계": ["RELATED_TO", "ASSOCIATED_WITH", "CONNECTED_TO"],
                    "소속_관계": ["MEMBER_OF", "PART_OF", "BELONGS_TO"],
                    "참여_관계": ["PARTICIPATES_IN", "ATTENDS", "ORGANIZES"],
                    "위치_관계": ["LOCATED_IN", "NEAR", "CONTAINS"],
                    "시간_관계": ["OCCURS_BEFORE", "CONCURRENT_WITH", "FOLLOWS"]
                }
            }
        }
    
    def _initialize_domain_detectors(self) -> Dict[str, Dict[str, Any]]:
        """도메인 감지 규칙 초기화"""
        return {
            DocumentDomain.TECHNICAL.value: {
                "keywords": [
                    "API", "function", "class", "method", "algorithm", "database", 
                    "server", "framework", "library", "code", "programming",
                    "software", "system", "architecture", "implementation"
                ],
                "patterns": [
                    r'\b(def|function|class|import|return)\b',
                    r'\b(HTTP|REST|JSON|XML|SQL)\b',
                    r'\b(server|client|database|API)\b'
                ],
                "file_extensions": [".py", ".js", ".java", ".cpp", ".md"],
                "confidence_threshold": 0.6
            },
            
            DocumentDomain.ACADEMIC.value: {
                "keywords": [
                    "research", "study", "analysis", "methodology", "hypothesis",
                    "experiment", "result", "conclusion", "literature", "theory",
                    "dataset", "variable", "correlation", "statistical"
                ],
                "patterns": [
                    r'\b(abstract|introduction|methodology|results|conclusion)\b',
                    r'\b(p\s*<\s*0\.05|significant|correlation)\b',
                    r'\b(et\s+al\.|cited|references)\b'
                ],
                "file_extensions": [".pdf", ".tex", ".docx"],
                "confidence_threshold": 0.7
            },
            
            DocumentDomain.BUSINESS.value: {
                "keywords": [
                    "revenue", "profit", "market", "customer", "strategy", "business",
                    "sales", "marketing", "competition", "growth", "investment",
                    "ROI", "KPI", "stakeholder", "process", "budget"
                ],
                "patterns": [
                    r'\$[\d,]+|\b\d+\s*(million|billion|percent|%)\b',
                    r'\b(Q[1-4]|quarterly|annual|fiscal)\b',
                    r'\b(CEO|CFO|CTO|manager|executive)\b'
                ],
                "file_extensions": [".xlsx", ".pptx", ".docx", ".pdf"],
                "confidence_threshold": 0.6
            },
            
            DocumentDomain.LEGAL.value: {
                "keywords": [
                    "law", "legal", "contract", "agreement", "regulation", "compliance",
                    "court", "judge", "plaintiff", "defendant", "liability", "clause",
                    "statute", "precedent", "jurisdiction", "penalty"
                ],
                "patterns": [
                    r'\b(Section|Article|Clause)\s+\d+',
                    r'\b(shall|hereby|whereas|therefore)\b',
                    r'\b(court|judge|plaintiff|defendant)\b'
                ],
                "file_extensions": [".pdf", ".docx"],
                "confidence_threshold": 0.8
            }
        }
    
    def detect_document_domain(self, text: str, metadata: Dict[str, Any] = None) -> Tuple[DocumentDomain, float]:
        """문서 도메인을 감지하고 신뢰도를 반환"""
        domain_scores = {}
        
        # 텍스트 기반 점수 계산
        for domain_name, detector in self.domain_detectors.items():
            score = self._calculate_domain_score(text, detector)
            domain_scores[domain_name] = score
        
        # 메타데이터 기반 점수 보정
        if metadata:
            domain_scores = self._adjust_scores_with_metadata(domain_scores, metadata)
        
        # 최고 점수 도메인 선택
        best_domain_name = max(domain_scores, key=domain_scores.get)
        best_score = domain_scores[best_domain_name]
        best_domain = DocumentDomain(best_domain_name)
        
        return best_domain, best_score
    
    def _calculate_domain_score(self, text: str, detector: Dict[str, Any]) -> float:
        """텍스트를 기반으로 도메인 점수 계산"""
        text_lower = text.lower()
        score = 0.0
        
        # 키워드 매칭 점수
        keyword_matches = sum(1 for keyword in detector["keywords"] 
                            if keyword in text_lower)
        keyword_score = keyword_matches / len(detector["keywords"]) * 0.6
        
        # 패턴 매칭 점수
        pattern_matches = sum(1 for pattern in detector["patterns"]
                            if re.search(pattern, text, re.IGNORECASE))
        pattern_score = pattern_matches / len(detector["patterns"]) * 0.4
        
        return keyword_score + pattern_score
    
    def _adjust_scores_with_metadata(self, scores: Dict[str, float], metadata: Dict[str, Any]) -> Dict[str, float]:
        """메타데이터를 기반으로 점수 조정"""
        adjusted_scores = scores.copy()
        
        # 파일 확장자 기반 보정
        file_extension = metadata.get("extension", "")
        for domain_name, detector in self.domain_detectors.items():
            if file_extension in detector["file_extensions"]:
                adjusted_scores[domain_name] += 0.2
        
        # 문서 타입 기반 보정
        doc_type = metadata.get("document_type", "").lower()
        if "research" in doc_type or "paper" in doc_type:
            adjusted_scores[DocumentDomain.ACADEMIC.value] += 0.3
        elif "technical" in doc_type or "manual" in doc_type:
            adjusted_scores[DocumentDomain.TECHNICAL.value] += 0.3
        elif "business" in doc_type or "report" in doc_type:
            adjusted_scores[DocumentDomain.BUSINESS.value] += 0.3
        elif "contract" in doc_type or "legal" in doc_type:
            adjusted_scores[DocumentDomain.LEGAL.value] += 0.3
        
        return adjusted_scores
    
    def get_domain_schema(self, domain: DocumentDomain) -> Dict[str, Any]:
        """도메인별 엔티티/관계 스키마 반환"""
        return self.domain_schemas.get(domain.value, self.domain_schemas[DocumentDomain.GENERAL.value])
    
    def get_enhanced_relationship_type(self, source_entity: str, target_entity: str, 
                                     context: str, domain: DocumentDomain) -> Tuple[str, str]:
        """컨텍스트를 기반으로 구체적인 관계 타입 추론"""
        schema = self.get_domain_schema(domain)
        relationships = schema["relationships"]
        
        # 컨텍스트 분석을 통한 관계 추론
        context_lower = context.lower()
        
        # 도메인별 관계 패턴 매칭
        for category, relation_types in relationships.items():
            for relation_type in relation_types:
                if self._matches_relationship_pattern(context_lower, relation_type):
                    return "RELATED_TO", relation_type
        
        # 기본 관계 반환
        return "RELATED_TO", "ASSOCIATED_WITH"
    
    def _matches_relationship_pattern(self, context: str, relation_type: str) -> bool:
        """관계 타입과 컨텍스트 패턴 매칭"""
        relation_patterns = {
            "DEPENDS_ON": ["depends", "require", "need", "rely"],
            "IMPLEMENTS": ["implement", "realize", "execute"],
            "USES": ["use", "utilize", "employ", "apply"],
            "CALLS": ["call", "invoke", "execute", "trigger"],
            "CITES": ["cite", "reference", "quote", "mention"],
            "PROVES": ["prove", "demonstrate", "show", "evidence"],
            "SUPPORTS": ["support", "back", "endorse", "confirm"],
            "CONTRADICTS": ["contradict", "oppose", "conflict", "disagree"],
            "CAUSES": ["cause", "lead", "result", "trigger"],
            "CONTAINS": ["contain", "include", "comprise", "consist"]
        }
        
        if relation_type in relation_patterns:
            return any(pattern in context for pattern in relation_patterns[relation_type])
        
        return False
    
    def generate_domain_specific_entities(self, keywords: List[str], domain: DocumentDomain) -> List[Dict[str, Any]]:
        """도메인별 키워드를 엔티티로 변환"""
        schema = self.get_domain_schema(domain)
        entity_types = schema["entities"]
        
        entities = []
        for keyword in keywords:
            # 키워드를 적절한 엔티티 타입으로 분류
            entity_type = self._classify_keyword_to_entity_type(keyword, entity_types)
            
            entity = {
                "type": entity_type,
                "properties": {
                    "name": keyword,
                    "domain": domain.value,
                    "confidence": 0.8  # 기본 신뢰도
                }
            }
            
            # 도메인별 추가 속성 설정
            additional_props = self._get_additional_entity_properties(keyword, entity_type, domain)
            entity["properties"].update(additional_props)
            
            entities.append(entity)
        
        return entities
    
    def _classify_keyword_to_entity_type(self, keyword: str, entity_types: Dict[str, List[str]]) -> str:
        """키워드를 엔티티 타입으로 분류"""
        keyword_lower = keyword.lower()
        
        # 구체적인 기술별 분류 규칙 (우선순위 높음)
        specific_technology_rules = {
            "Database": ["postgresql", "postgres", "mysql", "mongodb", "sqlite", "oracle", "redis", "cassandra", "elasticsearch", "influxdb", "mariadb"],
            "Framework": ["fastapi", "django", "flask", "react", "vue", "angular", "spring", "express", "laravel", "rails", "nextjs", "nuxt"],
            "Tool": ["docker", "kubernetes", "jenkins", "git", "maven", "gradle", "webpack", "vite", "npm", "yarn"],
            "Language": ["python", "javascript", "java", "c++", "go", "rust", "typescript", "php", "ruby", "kotlin", "swift"],
            "Library": ["sqlalchemy", "pydantic", "numpy", "pandas", "tensorflow", "pytorch", "lodash", "axios", "requests", "beautifulsoup"],
        }
        
        # 구체적인 규칙 먼저 확인
        for entity_type, tech_names in specific_technology_rules.items():
            if entity_type in entity_types:
                for tech_name in tech_names:
                    if tech_name in keyword_lower:
                        return entity_type
        
        # 일반적인 카테고리 규칙
        general_classification_rules = {
            "Technology": ["api", "system", "platform", "service", "application", "software"],
            "Person": ["author", "researcher", "manager", "director", "ceo"],
            "Organization": ["company", "university", "institute", "corporation"],
            "Concept": ["method", "approach", "technique", "theory", "principle", "pattern", "concept"],
            "Process": ["workflow", "procedure", "protocol", "methodology"]
        }
        
        for entity_type, keywords in general_classification_rules.items():
            if entity_type in entity_types and any(k in keyword_lower for k in keywords):
                return entity_type
        
        # 기본값은 Technology (기술 문서에서 가장 일반적)
        return "Technology" if "Technology" in entity_types else list(entity_types.keys())[0]
    
    def _get_additional_entity_properties(self, keyword: str, entity_type: str, domain: DocumentDomain) -> Dict[str, Any]:
        """엔티티 타입과 도메인에 따른 추가 속성 생성"""
        additional_props = {}
        
        # 도메인별 추가 속성 로직
        if domain == DocumentDomain.TECHNICAL:
            if entity_type == "Technology":
                additional_props.update({
                    "category": "software",
                    "maturity": "stable"
                })
        elif domain == DocumentDomain.ACADEMIC:
            if entity_type == "Author":
                additional_props.update({
                    "field": "research",
                    "h_index": None
                })
        
        return additional_props