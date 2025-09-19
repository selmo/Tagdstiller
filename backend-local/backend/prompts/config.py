"""
프롬프트 설정 관리

이 파일은 프롬프트 템플릿의 설정과 커스터마이징을 관리합니다.
사용자는 설정을 통해 프롬프트를 조정하고 새로운 템플릿을 추가할 수 있습니다.
"""

from typing import Dict, Any, Optional
from .templates import PromptTemplate, template_manager


class PromptConfig:
    """프롬프트 설정 관리 클래스"""
    
    # 기본 설정값
    DEFAULT_SETTINGS = {
        'keyword_extraction': {
            'max_keywords': 20,
            'language': 'auto',  # auto, ko, en
            'domain': 'general',  # general, academic, technical
            'temperature': 0.1,
            'max_tokens': 500,
        },
        'document_summary': {
            'language': 'auto',  # auto, ko, en  
            'domain': 'general',  # general, academic, technical
            'temperature': 0.3,
            'max_tokens': 1000,
            'chunk_size': 4000,
        },
        'metadata_extraction': {
            'language': 'ko',
            'temperature': 0.2,
            'max_tokens': 800,
        }
    }
    
    def __init__(self, config_dict: Dict[str, Any] = None, db_session = None):
        """설정 초기화"""
        # 데이터베이스에서 프롬프트 설정 로드
        db_config = {}
        if db_session:
            db_config = self._load_from_database(db_session)
        
        # 설정 병합 (우선순위: config_dict > database > defaults)
        self.settings = self._merge_settings(config_dict or {}, db_config)
    
    def _load_from_database(self, db_session) -> Dict[str, Any]:
        """데이터베이스에서 프롬프트 설정 로드"""
        try:
            from services.config_service import ConfigService
            
            db_config = {
                'keyword_extraction': {
                    'language': ConfigService.get_config_value(db_session, 'prompt.keyword_extraction.language', 'auto'),
                    'domain': ConfigService.get_config_value(db_session, 'prompt.keyword_extraction.domain', 'general'),
                    'max_keywords': ConfigService.get_int_config(db_session, 'prompt.keyword_extraction.max_keywords', 20),
                    'temperature': ConfigService.get_float_config(db_session, 'prompt.keyword_extraction.temperature', 0.1),
                    'max_tokens': ConfigService.get_int_config(db_session, 'prompt.keyword_extraction.max_tokens', 500),
                },
                'document_summary': {
                    'language': ConfigService.get_config_value(db_session, 'prompt.document_summary.language', 'auto'),
                    'domain': ConfigService.get_config_value(db_session, 'prompt.document_summary.domain', 'general'),
                    'temperature': ConfigService.get_float_config(db_session, 'prompt.document_summary.temperature', 0.3),
                    'max_tokens': ConfigService.get_int_config(db_session, 'prompt.document_summary.max_tokens', 1000),
                    'chunk_size': ConfigService.get_int_config(db_session, 'prompt.document_summary.chunk_size', 4000),
                },
                'metadata_extraction': {
                    'language': ConfigService.get_config_value(db_session, 'prompt.metadata_extraction.language', 'ko'),
                    'temperature': ConfigService.get_float_config(db_session, 'prompt.metadata_extraction.temperature', 0.2),
                    'max_tokens': ConfigService.get_int_config(db_session, 'prompt.metadata_extraction.max_tokens', 800),
                }
            }
            return db_config
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"데이터베이스에서 프롬프트 설정 로드 실패: {e}")
            return {}
    
    def _merge_settings(self, config_dict: Dict[str, Any], db_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """기본 설정과 사용자 설정을 병합"""
        merged = {}
        db_config = db_config or {}
        
        for category, defaults in self.DEFAULT_SETTINGS.items():
            # 우선순위: config_dict > db_config > defaults
            merged[category] = {
                **defaults, 
                **db_config.get(category, {}), 
                **config_dict.get(category, {})
            }
        return merged
    
    def get_template_name(self, category: str) -> str:
        """설정에 따른 적절한 템플릿 이름 결정"""
        settings = self.settings.get(category, {})
        language = settings.get('language', 'auto')
        domain = settings.get('domain', 'general')
        
        # 언어 자동 감지 (추후 구현)
        if language == 'auto':
            language = 'ko'  # 임시로 한국어 기본값
        
        # 템플릿 이름 조합
        if domain == 'general':
            if category == 'keyword_extraction':
                return f'basic_{language}'
            elif category == 'document_summary':
                return f'basic_{language}'
            else:
                return 'basic'
        else:
            return domain
    
    def get_llm_params(self, category: str) -> Dict[str, Any]:
        """LLM 호출 파라미터 반환"""
        settings = self.settings.get(category, {})
        return {
            'temperature': settings.get('temperature', 0.3),
            'num_predict': settings.get('max_tokens', 1000),
        }
    
    def get_template_variables(self, category: str, text: str) -> Dict[str, Any]:
        """템플릿 변수 생성"""
        settings = self.settings.get(category, {})
        
        variables = {'text': text}
        
        if category == 'keyword_extraction':
            variables['max_keywords'] = min(settings.get('max_keywords', 20), 8)  # Ollama 제한
        
        return variables


def load_custom_templates_from_config(db_session) -> None:
    """데이터베이스에서 커스텀 템플릿 로드"""
    from services.config_service import ConfigService
    
    try:
        # 커스텀 프롬프트 설정 가져오기
        custom_prompts = ConfigService.get_config(db_session, 'custom_prompts', {})
        
        if isinstance(custom_prompts, dict):
            for category, templates in custom_prompts.items():
                if isinstance(templates, dict):
                    for name, template_data in templates.items():
                        if isinstance(template_data, dict) and 'template' in template_data:
                            template = PromptTemplate(
                                template=template_data['template'],
                                variables=template_data.get('variables', {})
                            )
                            template_manager.add_custom_template(category, name, template)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"커스텀 템플릿 로드 실패: {e}")


def save_custom_template_to_config(db_session, category: str, name: str, 
                                 template: str, variables: Dict[str, Any] = None) -> bool:
    """커스텀 템플릿을 데이터베이스에 저장"""
    from services.config_service import ConfigService
    
    try:
        # 기존 커스텀 프롬프트 가져오기
        custom_prompts = ConfigService.get_config(db_session, 'custom_prompts', {})
        
        if not isinstance(custom_prompts, dict):
            custom_prompts = {}
        
        # 카테고리별 템플릿 구조 생성
        if category not in custom_prompts:
            custom_prompts[category] = {}
        
        # 새 템플릿 추가
        custom_prompts[category][name] = {
            'template': template,
            'variables': variables or {},
            'created_at': None,  # ConfigService에서 자동 설정
        }
        
        # 데이터베이스에 저장
        ConfigService.set_config(db_session, 'custom_prompts', custom_prompts)
        
        # 메모리에도 추가
        prompt_template = PromptTemplate(template, variables)
        template_manager.add_custom_template(category, name, prompt_template)
        
        return True
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"커스텀 템플릿 저장 실패: {e}")
        return False


def get_available_templates_with_info() -> Dict[str, Any]:
    """사용 가능한 템플릿 정보 반환"""
    templates_info = {}
    
    for category, templates in template_manager.templates.items():
        templates_info[category] = {}
        for name, template in templates.items():
            # 템플릿에서 필요한 변수 추출
            import re
            required_vars = re.findall(r'\{(\w+)\}', template.template)
            
            templates_info[category][name] = {
                'description': _get_template_description(category, name),
                'required_variables': required_vars,
                'default_variables': template.variables,
                'preview': template.template[:200] + '...' if len(template.template) > 200 else template.template
            }
    
    return templates_info


def _get_template_description(category: str, name: str) -> str:
    """템플릿 설명 반환"""
    descriptions = {
        'keyword_extraction': {
            'basic_en': '영어 문서용 기본 키워드 추출',
            'basic_ko': '한국어 문서용 기본 키워드 추출', 
            'academic': '학술 문서용 전문 키워드 추출',
            'technical': '기술 문서용 전문 키워드 추출',
        },
        'document_summary': {
            'basic_ko': '한국어 문서용 기본 요약',
            'basic_en': '영어 문서용 기본 요약',
            'academic': '학술 문서용 전문 요약',
            'technical': '기술 문서용 전문 요약',
        },
        'metadata_extraction': {
            'basic': '기본 메타데이터 추출',
        }
    }
    
    return descriptions.get(category, {}).get(name, f'{category}용 {name} 템플릿')