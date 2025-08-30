#!/usr/bin/env python3
"""
Docling 파서 테스트 스크립트
"""

import sys
from pathlib import Path

# backend 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from services.parser.docling_parser import DoclingParser
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_docling_parser():
    """Docling 파서 테스트"""
    print("=" * 60)
    print("🧪 Docling 파서 테스트 시작")
    print("=" * 60)
    
    # 파서 생성
    parser = DoclingParser()
    print(f"✅ 파서 생성 완료: {parser.parser_name}")
    
    # 테스트용 PDF 파일 찾기
    test_files_dir = Path("/Users/selmo/Workspaces/RAG-Evaluation-Dataset-KO/finance")
    
    if not test_files_dir.exists():
        print("❌ 테스트 디렉토리가 존재하지 않습니다")
        return
    
    # PDF 파일 찾기
    pdf_files = list(test_files_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ PDF 파일을 찾을 수 없습니다")
        return
    
    # 첫 번째 PDF 파일로 테스트
    test_file = pdf_files[0]
    print(f"\n📄 테스트 파일: {test_file.name}")
    print(f"   파일 크기: {test_file.stat().st_size:,} bytes")
    
    # 파싱 수행
    print("\n⚙️ Docling으로 파싱 중...")
    result = parser.parse(test_file)
    
    if result.success:
        print("\n✅ 파싱 성공!")
        print(f"   파서: {result.parser_name}")
        print(f"   텍스트 길이: {len(result.text):,} 문자")
        
        if result.metadata:
            print("\n📊 메타데이터:")
            print(f"   제목: {result.metadata.title}")
            print(f"   페이지 수: {result.metadata.page_count}")
            print(f"   단어 수: {result.metadata.word_count:,}")
            
            if hasattr(result.metadata, 'tables_count'):
                print(f"   테이블 수: {result.metadata.tables_count}")
            if hasattr(result.metadata, 'images_count'):
                print(f"   이미지 수: {result.metadata.images_count}")
            
            if hasattr(result.metadata, 'document_structure'):
                structure = result.metadata.document_structure
                if structure:
                    if 'sections' in structure:
                        print(f"   섹션 수: {len(structure['sections'])}")
                        if structure['sections']:
                            print("\n   📑 섹션 구조 (상위 5개):")
                            for section in structure['sections'][:5]:
                                indent = "  " * section['level']
                                print(f"      {indent}• {section['title']}")
        
        # 텍스트 샘플 출력
        print("\n📝 텍스트 샘플 (처음 500자):")
        print("-" * 40)
        print(result.text[:500])
        print("-" * 40)
        
    else:
        print(f"\n❌ 파싱 실패: {result.error_message}")
    
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)

if __name__ == "__main__":
    test_docling_parser()