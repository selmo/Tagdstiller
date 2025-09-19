"""
spaCy 모델 관리 서비스
설치된 모델 조회, 다운로드, 삭제 등의 기능을 제공합니다.
"""

import subprocess
import sys
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class SpaCyModelService:
    """spaCy 모델 관리 서비스"""
    
    # 지원하는 spaCy 모델 목록
    SUPPORTED_MODELS = {
        'ko_core_news_sm': {
            'name': 'ko_core_news_sm',
            'language': 'Korean',
            'size': 'Small (~50MB)',
            'description': '한국어 소형 모델 - 토큰화, 품사 태깅, 의존성 파싱, NER',
            'recommended': True
        },
        'ko_core_news_md': {
            'name': 'ko_core_news_md',
            'language': 'Korean', 
            'size': 'Medium (~100MB)',
            'description': '한국어 중형 모델 - 단어 벡터 포함, 더 정확한 NER',
            'recommended': False
        },
        'ko_core_news_lg': {
            'name': 'ko_core_news_lg',
            'language': 'Korean',
            'size': 'Large (~400MB)', 
            'description': '한국어 대형 모델 - 고품질 단어 벡터, 최고 정확도',
            'recommended': False
        },
        'en_core_web_sm': {
            'name': 'en_core_web_sm',
            'language': 'English',
            'size': 'Small (~13MB)',
            'description': '영어 소형 모델 - 기본 NLP 기능',
            'recommended': False
        },
        'en_core_web_md': {
            'name': 'en_core_web_md', 
            'language': 'English',
            'size': 'Medium (~40MB)',
            'description': '영어 중형 모델 - 단어 벡터 포함',
            'recommended': False
        },
        'en_core_web_lg': {
            'name': 'en_core_web_lg',
            'language': 'English', 
            'size': 'Large (~560MB)',
            'description': '영어 대형 모델 - 고품질 단어 벡터',
            'recommended': False
        }
    }
    
    @classmethod
    def get_installed_models(cls) -> List[Dict[str, Any]]:
        """설치된 spaCy 모델 목록을 반환합니다."""
        try:
            import spacy
            from spacy.util import get_installed_models
            
            installed_model_names = get_installed_models()
            installed_models = []
            
            for model_name in installed_model_names:
                model_info = cls.SUPPORTED_MODELS.get(model_name, {
                    'name': model_name,
                    'language': 'Unknown',
                    'size': 'Unknown',
                    'description': f'설치된 모델: {model_name}',
                    'recommended': False
                })
                
                # 모델이 실제로 로드 가능한지 확인
                try:
                    spacy.load(model_name)
                    model_info['status'] = 'available'
                    model_info['installed'] = True
                except Exception:
                    model_info['status'] = 'installed_but_not_loadable'
                    model_info['installed'] = False
                
                installed_models.append(model_info)
            
            return installed_models
            
        except ImportError:
            logger.error("spaCy 라이브러리가 설치되지 않음")
            return []
        except Exception as e:
            logger.error(f"설치된 모델 조회 실패: {e}")
            return []
    
    @classmethod
    def get_available_models(cls) -> List[Dict[str, Any]]:
        """다운로드 가능한 모든 spaCy 모델 목록을 반환합니다."""
        installed_models = {model['name'] for model in cls.get_installed_models()}
        
        available_models = []
        for model_name, model_info in cls.SUPPORTED_MODELS.items():
            model_data = model_info.copy()
            model_data['installed'] = model_name in installed_models
            available_models.append(model_data)
        
        return available_models
    
    @classmethod
    def download_model(cls, model_name: str) -> Tuple[bool, str]:
        """지정된 spaCy 모델을 다운로드합니다."""
        if model_name not in cls.SUPPORTED_MODELS:
            return False, f"지원하지 않는 모델: {model_name}"
        
        try:
            logger.info(f"📥 spaCy 모델 '{model_name}' 다운로드 시작...")
            
            # spacy download 명령어 실행
            result = subprocess.run(
                [sys.executable, "-m", "spacy", "download", model_name],
                capture_output=True,
                text=True,
                timeout=600  # 10분 타임아웃
            )
            
            if result.returncode == 0:
                logger.info(f"✅ spaCy 모델 '{model_name}' 다운로드 완료")
                return True, f"모델 '{model_name}' 다운로드 성공"
            else:
                error_msg = result.stderr or result.stdout or "알 수 없는 오류"
                logger.error(f"❌ spaCy 모델 '{model_name}' 다운로드 실패: {error_msg}")
                return False, f"다운로드 실패: {error_msg}"
                
        except subprocess.TimeoutExpired:
            error_msg = f"다운로드 타임아웃 (10분 초과)"
            logger.error(f"❌ spaCy 모델 '{model_name}' {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"다운로드 중 오류: {str(e)}"
            logger.error(f"❌ spaCy 모델 '{model_name}' {error_msg}")
            return False, error_msg
    
    @classmethod
    def test_model(cls, model_name: str) -> Tuple[bool, str]:
        """모델이 정상적으로 로드되고 작동하는지 테스트합니다."""
        try:
            import spacy
            
            logger.info(f"🧪 spaCy 모델 '{model_name}' 테스트 시작...")
            
            # 모델 로드 테스트
            nlp = spacy.load(model_name)
            
            # 간단한 텍스트 처리 테스트
            test_text = "안녕하세요. 이것은 테스트입니다." if model_name.startswith('ko') else "Hello. This is a test."
            doc = nlp(test_text)
            
            # NER 기능 테스트
            entities = [(ent.text, ent.label_) for ent in doc.ents]
            
            logger.info(f"✅ spaCy 모델 '{model_name}' 테스트 성공")
            return True, f"모델 '{model_name}' 정상 작동 확인"
            
        except Exception as e:
            error_msg = f"모델 테스트 실패: {str(e)}"
            logger.error(f"❌ spaCy 모델 '{model_name}' {error_msg}")
            return False, error_msg
    
    @classmethod
    def get_model_info(cls, model_name: str) -> Optional[Dict[str, Any]]:
        """특정 모델의 상세 정보를 반환합니다."""
        if model_name not in cls.SUPPORTED_MODELS:
            return None
        
        model_info = cls.SUPPORTED_MODELS[model_name].copy()
        
        # 설치 상태 확인
        installed_models = {model['name'] for model in cls.get_installed_models()}
        model_info['installed'] = model_name in installed_models
        
        # 로드 가능 여부 확인
        if model_info['installed']:
            try:
                import spacy
                spacy.load(model_name)
                model_info['status'] = 'available'
            except Exception:
                model_info['status'] = 'installed_but_not_loadable'
        else:
            model_info['status'] = 'not_installed'
        
        return model_info