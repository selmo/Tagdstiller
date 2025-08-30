#!/usr/bin/env python3
"""
프롬프트 템플릿 시스템 테스트 스크립트

이 스크립트는 새로 구현된 프롬프트 템플릿 시스템의 기능을 테스트합니다.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from prompts.templates import get_prompt_template, list_available_templates
from prompts.config import PromptConfig, get_available_templates_with_info


def test_template_loading():
    """템플릿 로딩 테스트"""
    print("🧪 템플릿 로딩 테스트 시작...")
    
    # 사용 가능한 템플릿 목록
    templates = list_available_templates()
    print(f"📋 사용 가능한 템플릿: {templates}")
    
    # 각 카테고리별 템플릿 테스트
    for category, template_names in templates.items():
        print(f"\n📂 카테고리: {category}")
        for template_name in template_names:
            print(f"  📄 템플릿: {template_name}")


def test_keyword_extraction_templates():
    """키워드 추출 템플릿 테스트"""
    print("\n🔍 키워드 추출 템플릿 테스트...")
    
    test_text = "인공지능과 머신러닝은 현대 기술의 핵심입니다. 딥러닝 알고리즘을 통해 복잡한 문제를 해결할 수 있습니다."
    
    # 한국어 기본 템플릿
    try:
        prompt = get_prompt_template(
            'keyword_extraction', 
            'basic_ko', 
            text=test_text, 
            max_keywords=5
        )
        print("✅ 한국어 키워드 추출 템플릿 생성 성공")
        print(f"프롬프트 길이: {len(prompt)} 문자")
        print(f"프롬프트 미리보기: {prompt[:200]}...")
    except Exception as e:
        print(f"❌ 한국어 키워드 추출 템플릿 실패: {e}")
    
    # 영어 기본 템플릿
    try:
        prompt = get_prompt_template(
            'keyword_extraction', 
            'basic_en', 
            text="Artificial intelligence and machine learning are core technologies of modern era.",
            max_keywords=10
        )
        print("✅ 영어 키워드 추출 템플릿 생성 성공")
        print(f"프롬프트 길이: {len(prompt)} 문자")
    except Exception as e:
        print(f"❌ 영어 키워드 추출 템플릿 실패: {e}")


def test_document_summary_templates():
    """문서 요약 템플릿 테스트"""
    print("\n📝 문서 요약 템플릿 테스트...")
    
    test_document = """
    인공지능 기술의 발전

    인공지능(AI)은 21세기의 가장 혁신적인 기술 중 하나입니다. 머신러닝과 딥러닝의 발전으로 
    컴퓨터가 인간과 유사한 지능을 갖게 되었습니다.
    
    특히 자연어 처리, 컴퓨터 비전, 음성 인식 분야에서 괄목할 만한 성과를 보이고 있습니다.
    
    앞으로 AI 기술은 의료, 교육, 자동차 등 다양한 분야에 적용되어 우리 생활을 크게 변화시킬 것으로 예상됩니다.
    """
    
    try:
        prompt = get_prompt_template(
            'document_summary', 
            'basic_ko', 
            text=test_document.strip()
        )
        print("✅ 한국어 문서 요약 템플릿 생성 성공")
        print(f"프롬프트 길이: {len(prompt)} 문자")
        print(f"프롬프트 미리보기: {prompt[:300]}...")
    except Exception as e:
        print(f"❌ 한국어 문서 요약 템플릿 실패: {e}")


def test_prompt_config():
    """프롬프트 설정 테스트"""
    print("\n⚙️ 프롬프트 설정 테스트...")
    
    # 기본 설정
    config = PromptConfig()
    print(f"기본 설정: {config.settings}")
    
    # 커스텀 설정
    custom_config = {
        'keyword_extraction': {
            'language': 'ko',
            'domain': 'technical',
            'max_keywords': 15
        }
    }
    
    config_with_custom = PromptConfig(custom_config)
    print(f"커스텀 설정: {config_with_custom.settings['keyword_extraction']}")
    
    # 템플릿 이름 결정 테스트
    template_name = config_with_custom.get_template_name('keyword_extraction')
    print(f"선택된 템플릿: {template_name}")
    
    # LLM 파라미터 테스트
    llm_params = config_with_custom.get_llm_params('keyword_extraction')
    print(f"LLM 파라미터: {llm_params}")


def test_template_info():
    """템플릿 정보 테스트"""
    print("\n📊 템플릿 정보 테스트...")
    
    try:
        templates_info = get_available_templates_with_info()
        
        for category, templates in templates_info.items():
            print(f"\n📂 {category}:")
            for name, info in templates.items():
                print(f"  📄 {name}:")
                print(f"    설명: {info['description']}")
                print(f"    필수 변수: {info['required_variables']}")
                print(f"    기본 변수: {info['default_variables']}")
                print(f"    미리보기: {info['preview'][:100]}...")
    except Exception as e:
        print(f"❌ 템플릿 정보 조회 실패: {e}")


def main():
    """메인 테스트 함수"""
    print("🚀 프롬프트 템플릿 시스템 테스트 시작\n")
    
    test_template_loading()
    test_keyword_extraction_templates()
    test_document_summary_templates()
    test_prompt_config()
    test_template_info()
    
    print("\n🎉 프롬프트 템플릿 시스템 테스트 완료!")


if __name__ == "__main__":
    main()