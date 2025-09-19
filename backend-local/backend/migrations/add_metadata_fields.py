"""
데이터베이스 마이그레이션 스크립트
Dublin Core 메타데이터 필드 추가

실행 방법:
PYTHONPATH=/Users/selmo/Workspaces/DocExtract/backend python migrations/add_metadata_fields.py
"""

import sys
import os
from pathlib import Path
from sqlalchemy import Column, String, Integer, DateTime, Text, create_engine, inspect
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# 백엔드 디렉토리를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

try:
    from db.db import engine
    from db.models import Base, File
except ImportError:
    # 직접 데이터베이스 연결 생성
    from sqlalchemy import create_engine
    import sqlite3
    
    # 데이터베이스 파일 경로
    db_path = backend_dir / "data" / "database.db"
    db_path.parent.mkdir(exist_ok=True)
    
    # SQLite 엔진 생성
    engine = create_engine(f"sqlite:///{db_path}", echo=False)

def check_column_exists(table_name: str, column_name: str) -> bool:
    """테이블에 컬럼이 이미 존재하는지 확인"""
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    return any(col['name'] == column_name for col in columns)

def add_metadata_fields():
    """메타데이터 필드들을 files 테이블에 추가"""
    print("🔧 Dublin Core 메타데이터 필드 추가를 시작합니다...")
    
    # 추가할 필드 목록
    metadata_fields = [
        # Dublin Core 메타데이터
        ('dc:title', String, '문서 제목'),
        ('dc:creator', String, '주 저작자/작성자'),
        ('dc:subject', String, '주제/키워드'),
        ('dc:description', Text, '문서 설명'),
        ('dc:publisher', String, '발행자'),
        ('dc:contributor', String, '기여자'),
        ('dc:date', String, '생성/발행 날짜'),
        ('dc:type', String, '문서 타입'),
        ('dc:format', String, '파일 형식/MIME 타입'),
        ('dc:identifier', String, '고유 식별자'),
        ('dc:source', String, '원본 소스'),
        ('dc:language', String, '언어'),
        ('dc:relation', String, '관련 자료'),
        ('dc:coverage', String, '적용 범위'),
        ('dc:rights', String, '권리/라이선스'),
        
        # Dublin Core Terms 확장
        ('dcterms:created', String, '생성 날짜'),
        ('dcterms:modified', String, '수정 날짜'),
        ('dcterms:extent', String, '크기/범위'),
        ('dcterms:medium', String, '매체'),
        ('dcterms:audience', String, '대상 독자'),
        
        # 파일 관련 메타데이터
        ('file:name', String, '파일명'),
        ('file:path', String, '파일 경로'),
        ('file:size', Integer, '파일 크기'),
        ('file:extension', String, '파일 확장자'),
        
        # 문서 관련 메타데이터
        ('doc:page_count', Integer, '페이지 수'),
        ('doc:word_count', Integer, '단어 수'),
        ('doc:character_count', Integer, '문자 수'),
        ('doc:type_code', String, '문서 타입 코드'),
        ('doc:supported', String, '지원 여부'),
        
        # 애플리케이션 메타데이터
        ('app:version', String, '애플리케이션 버전'),
        
        # 파서 관련 정보
        ('parser:name', String, '사용된 파서명'),
        ('parser:version', String, '파서 버전'),
        ('extraction:date', DateTime, '메타데이터 추출 날짜'),
    ]
    
    added_fields = 0
    skipped_fields = 0
    
    with engine.connect() as connection:
        for field_name, field_type, description in metadata_fields:
            try:
                # 필드가 이미 존재하는지 확인
                if check_column_exists('files', field_name):
                    print(f"⏭️  '{field_name}' 필드는 이미 존재합니다. 건너뜁니다.")
                    skipped_fields += 1
                    continue
                
                # ALTER TABLE 구문 생성
                if field_type == String:
                    sql = f"ALTER TABLE files ADD COLUMN {field_name} VARCHAR"
                elif field_type == Integer:
                    sql = f"ALTER TABLE files ADD COLUMN {field_name} INTEGER"
                elif field_type == Text:
                    sql = f"ALTER TABLE files ADD COLUMN {field_name} TEXT"
                elif field_type == DateTime:
                    sql = f"ALTER TABLE files ADD COLUMN {field_name} DATETIME"
                else:
                    sql = f"ALTER TABLE files ADD COLUMN {field_name} VARCHAR"
                
                # 필드 추가 실행
                from sqlalchemy import text
                connection.execute(text(sql))
                connection.commit()
                print(f"✅ '{field_name}' 필드 추가 완료 - {description}")
                added_fields += 1
                
            except Exception as e:
                print(f"❌ '{field_name}' 필드 추가 실패: {str(e)}")
                # 에러가 발생해도 계속 진행
                continue
    
    print(f"\n📊 마이그레이션 완료:")
    print(f"   ✅ 추가된 필드: {added_fields}개")
    print(f"   ⏭️  건너뛴 필드: {skipped_fields}개")
    print(f"   📝 총 필드: {len(metadata_fields)}개")

def verify_migration():
    """마이그레이션이 성공적으로 적용되었는지 확인"""
    print("\n🔍 마이그레이션 검증을 시작합니다...")
    
    inspector = inspect(engine)
    columns = inspector.get_columns('files')
    column_names = [col['name'] for col in columns]
    
    # 확인할 핵심 필드들
    core_fields = ['dc:title', 'dc:creator', 'doc_page_count', 'file_size', 'parser_name']
    
    all_present = True
    for field in core_fields:
        if field in column_names:
            print(f"✅ '{field}' 필드 확인됨")
        else:
            print(f"❌ '{field}' 필드 없음")
            all_present = False
    
    if all_present:
        print("🎉 모든 핵심 메타데이터 필드가 성공적으로 추가되었습니다!")
    else:
        print("⚠️  일부 필드가 누락되었습니다. 다시 확인해주세요.")
    
    print(f"\n📋 files 테이블의 총 컬럼 수: {len(column_names)}")

if __name__ == "__main__":
    try:
        print("🚀 메타데이터 필드 추가 마이그레이션을 시작합니다...\n")
        
        # 데이터베이스 연결 확인
        with engine.connect() as connection:
            print("✅ 데이터베이스 연결 성공")
        
        # 마이그레이션 실행
        add_metadata_fields()
        
        # 검증
        verify_migration()
        
        print("\n🎊 마이그레이션이 성공적으로 완료되었습니다!")
        
    except Exception as e:
        print(f"\n💥 마이그레이션 중 오류 발생: {str(e)}")
        sys.exit(1)