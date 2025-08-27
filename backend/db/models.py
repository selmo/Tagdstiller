from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    files = relationship("File", back_populates="project")

class File(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    filename = Column(String)
    filepath = Column(String)
    size = Column(Integer)
    mime_type = Column(String)  # MIME type of the file
    content = Column(Text)  # Parsed text content
    parse_status = Column(String, default="not_parsed")  # not_parsed, success, failed
    parse_error = Column(Text)  # Error message if parsing failed
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    # Dublin Core 메타데이터
    dc_title = Column(String)  # 문서 제목
    dc_creator = Column(String)  # 주 저작자/작성자
    dc_subject = Column(String)  # 주제/키워드
    dc_description = Column(Text)  # 문서 설명
    dc_publisher = Column(String)  # 발행자
    dc_contributor = Column(String)  # 기여자
    dc_date = Column(String)  # 생성/발행 날짜
    dc_type = Column(String)  # 문서 타입
    dc_format = Column(String)  # 파일 형식/MIME 타입
    dc_identifier = Column(String)  # 고유 식별자
    dc_source = Column(String)  # 원본 소스
    dc_language = Column(String)  # 언어
    dc_relation = Column(String)  # 관련 자료
    dc_coverage = Column(String)  # 적용 범위
    dc_rights = Column(String)  # 권리/라이선스
    
    # Dublin Core Terms 확장
    dcterms_created = Column(String)  # 생성 날짜
    dcterms_modified = Column(String)  # 수정 날짜
    dcterms_extent = Column(String)  # 크기/범위
    dcterms_medium = Column(String)  # 매체
    dcterms_audience = Column(String)  # 대상 독자
    
    # 파일 관련 메타데이터
    file_name = Column(String)  # 파일명
    file_path = Column(String)  # 파일 경로
    file_size = Column(Integer)  # 파일 크기
    file_extension = Column(String)  # 파일 확장자
    
    # 문서 관련 메타데이터
    doc_page_count = Column(Integer)  # 페이지 수
    doc_word_count = Column(Integer)  # 단어 수
    doc_character_count = Column(Integer)  # 문자 수
    doc_type_code = Column(String)  # 문서 타입 코드
    doc_supported = Column(String)  # 지원 여부
    
    # 애플리케이션 메타데이터
    app_version = Column(String)  # 애플리케이션 버전
    
    # 파서 관련 정보
    parser_name = Column(String)  # 사용된 파서명
    parser_version = Column(String)  # 파서 버전
    extraction_date = Column(DateTime, default=datetime.utcnow)  # 메타데이터 추출 날짜

    project = relationship("Project", back_populates="files")
    keyword_occurrences = relationship("KeywordOccurrence", back_populates="file")

class Config(Base):
    __tablename__ = "configs"
    key = Column(String, primary_key=True, index=True)
    value = Column(Text)
    value_type = Column(String, default="string")  # string, int, float, bool, json
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class KeywordOccurrence(Base):
    __tablename__ = "keyword_occurrences"
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"))
    keyword = Column(String, index=True)
    extractor_name = Column(String)
    score = Column(Float)
    category = Column(String)
    start_position = Column(Integer)
    end_position = Column(Integer)
    context_snippet = Column(Text)
    page_number = Column(Integer)
    line_number = Column(Integer)
    column_number = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    file = relationship("File", back_populates="keyword_occurrences")

class KeywordStatisticsCache(Base):
    __tablename__ = "keyword_statistics_cache"
    id = Column(Integer, primary_key=True, index=True)
    cache_type = Column(String, index=True)  # 'global' or 'project'
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)  # NULL for global stats
    total_keywords = Column(Integer, default=0)
    total_occurrences = Column(Integer, default=0) 
    total_files = Column(Integer, default=0)
    total_projects = Column(Integer, default=0)  # Only for global stats
    extractors_used = Column(JSON)  # JSON array of extractor names
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", foreign_keys=[project_id])