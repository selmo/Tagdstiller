#!/usr/bin/env python3
"""
간단한 Docling 테스트
"""

from pathlib import Path
from docling.document_converter import DocumentConverter

# PDF 파일 경로
pdf_path = Path("/Users/selmo/Workspaces/RAG-Evaluation-Dataset-KO/finance/★2019 제1회 증시콘서트 자료집_최종★.pdf")

if pdf_path.exists():
    print(f"파일 존재: {pdf_path.name}")
    
    # 변환기 생성
    converter = DocumentConverter()
    
    # 변환 수행
    print("변환 중...")
    result = converter.convert(str(pdf_path))
    
    print(f"변환 완료!")
    print(f"문서 타입: {type(result.document)}")
    
    # Markdown 내보내기
    try:
        markdown = result.document.export_to_markdown()
        print(f"Markdown 길이: {len(markdown)} 문자")
        print("\n처음 500자:")
        print(markdown[:500])
    except Exception as e:
        print(f"Markdown 내보내기 실패: {e}")
    
    # 텍스트 내보내기
    try:
        text = result.document.export_to_text()
        print(f"\n텍스트 길이: {len(text)} 문자")
    except Exception as e:
        print(f"텍스트 내보내기 실패: {e}")
else:
    print(f"파일을 찾을 수 없음: {pdf_path}")