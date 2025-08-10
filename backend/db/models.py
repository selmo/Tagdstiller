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