#!/usr/bin/env python3
"""
Docling 직접 테스트
"""

import sys
from pathlib import Path

# backend 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent / "backend"))

print("1. Docling 임포트 테스트...")
try:
    from docling.document_converter import DocumentConverter
    print("   ✅ DocumentConverter 임포트 성공")
except ImportError as e:
    print(f"   ❌ DocumentConverter 임포트 실패: {e}")
    sys.exit(1)

print("\n2. DoclingParser 임포트 테스트...")
try:
    from services.parser.docling_parser import DoclingParser
    print("   ✅ DoclingParser 임포트 성공")
except ImportError as e:
    print(f"   ❌ DoclingParser 임포트 실패: {e}")
    sys.exit(1)

print("\n3. 파서 인스턴스 생성...")
parser = DoclingParser()
print(f"   ✅ 파서 생성 완료: {parser.parser_name}")

print("\n4. 테스트 PDF 파싱...")
test_file = Path("test_document.pdf")
if not test_file.exists():
    print(f"   ❌ 테스트 파일이 없습니다: {test_file}")
    sys.exit(1)

result = parser.parse(test_file)

print(f"\n5. 파싱 결과:")
print(f"   성공 여부: {result.success}")
print(f"   파서 이름: {result.parser_name}")
if result.success:
    print(f"   텍스트 길이: {len(result.text)} 문자")
    if result.metadata:
        print(f"   페이지 수: {result.metadata.page_count}")
        if hasattr(result.metadata, 'tables_count'):
            print(f"   테이블 수: {result.metadata.tables_count}")
        if hasattr(result.metadata, 'document_structure'):
            structure = result.metadata.document_structure
            if structure:
                print(f"   구조 정보 포함: Yes")
                if 'tables' in structure:
                    print(f"   테이블 개수: {len(structure['tables'])}")
                if 'sections' in structure:
                    print(f"   섹션 개수: {len(structure['sections'])}")
else:
    print(f"   오류: {result.error_message}")

print("\n✅ 테스트 완료")