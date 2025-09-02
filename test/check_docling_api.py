#!/usr/bin/env python3
"""
Docling API 확인
"""

from docling.document_converter import DocumentConverter
import inspect

print("DocumentConverter 생성자 시그니처:")
print(inspect.signature(DocumentConverter.__init__))
print("\n")

print("DocumentConverter.convert 메서드 시그니처:")
print(inspect.signature(DocumentConverter.convert))
print("\n")

# 실제 사용 예제
print("간단한 사용 예제:")
converter = DocumentConverter()
print("Converter 생성 성공")

# 속성 확인
print("\nConverter 속성:")
for attr in dir(converter):
    if not attr.startswith('_'):
        print(f"  - {attr}")