#!/usr/bin/env python3
"""
간단한 테스트 PDF 생성 스크립트
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from datetime import datetime

def create_test_pdf(filename="test_document.pdf"):
    """테스트용 PDF 문서 생성"""
    
    # PDF 문서 생성
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18,
    )
    
    # 스타일 정의
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    heading_style = styles['Heading2']
    normal_style = styles['BodyText']
    
    # 문서 내용
    story = []
    
    # 제목
    story.append(Paragraph("테스트 문서: Docling 파서 검증", title_style))
    story.append(Spacer(1, 12))
    
    # 메타데이터 정보
    story.append(Paragraph(f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
    story.append(Paragraph("작성자: DocExtract 시스템", normal_style))
    story.append(Spacer(1, 12))
    
    # 섹션 1: 소개
    story.append(Paragraph("1. 소개", heading_style))
    story.append(Paragraph(
        "이 문서는 Docling 파서의 기능을 테스트하기 위해 생성된 PDF 문서입니다. "
        "테이블, 섹션 구조, 그리고 다양한 텍스트 형식을 포함하고 있습니다.",
        normal_style
    ))
    story.append(Spacer(1, 12))
    
    # 섹션 2: 테이블
    story.append(Paragraph("2. 테이블 예제", heading_style))
    story.append(Spacer(1, 6))
    
    # 테이블 데이터
    data = [
        ['항목', '설명', '값'],
        ['파서', 'PDF 문서 파싱 도구', 'Docling'],
        ['형식', '지원 문서 형식', 'PDF, DOCX'],
        ['기능', '주요 기능', '구조 추출'],
        ['성능', '처리 속도', '중간'],
    ]
    
    # 테이블 스타일
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    story.append(table)
    story.append(Spacer(1, 12))
    
    # 섹션 3: 리스트
    story.append(Paragraph("3. 주요 특징", heading_style))
    story.append(Paragraph("• 테이블 구조 보존", normal_style))
    story.append(Paragraph("• Markdown 변환 지원", normal_style))
    story.append(Paragraph("• 섹션 계층 구조 추출", normal_style))
    story.append(Paragraph("• Dublin Core 메타데이터 표준 준수", normal_style))
    story.append(Spacer(1, 12))
    
    # 페이지 구분
    story.append(PageBreak())
    
    # 섹션 4: 추가 내용
    story.append(Paragraph("4. 추가 정보", heading_style))
    story.append(Paragraph(
        "이 페이지는 다중 페이지 문서 처리를 테스트하기 위한 추가 페이지입니다. "
        "Docling 파서는 여러 페이지에 걸친 문서도 올바르게 처리할 수 있어야 합니다.",
        normal_style
    ))
    story.append(Spacer(1, 12))
    
    # 두 번째 테이블
    story.append(Paragraph("5. 성능 비교", heading_style))
    story.append(Spacer(1, 6))
    
    perf_data = [
        ['파서', '속도', '정확도', '기능'],
        ['pypdf', '빠름', '보통', '기본'],
        ['PyMuPDF', '빠름', '좋음', '중급'],
        ['Docling', '보통', '매우 좋음', '고급'],
    ]
    
    perf_table = Table(perf_data)
    perf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    story.append(perf_table)
    
    # PDF 생성
    doc.build(story)
    print(f"✅ PDF 파일 생성 완료: {filename}")
    
    import os
    file_size = os.path.getsize(filename)
    print(f"   파일 크기: {file_size:,} bytes")

if __name__ == "__main__":
    create_test_pdf()