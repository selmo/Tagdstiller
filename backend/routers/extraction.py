import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from dependencies import get_db
from db.models import Project, File, KeywordOccurrence
from extractors.keybert_extractor import KeyBERTExtractor
from extractors.spacy_ner_extractor import SpaCyNERExtractor
from extractors.llm_extractor import LLMExtractor
from extractors.konlpy_extractor import KoNLPyExtractor
from extractors.langextract_extractor import LangExtractExtractor
from extractors.metadata_extractor import MetadataExtractor
from services.config_service import ConfigService
from services.statistics_cache_service import StatisticsCacheService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["extraction"])

class ExtractionRequest(BaseModel):
    methods: List[str]  # ["keybert", "spacy_ner", "llm", "konlpy", "langextract", "metadata"]
    
class KeywordOccurrenceResponse(BaseModel):
    keyword: str
    extractor_name: str
    score: float
    category: Optional[str] = None
    start_position: Optional[int] = None
    end_position: Optional[int] = None
    context_snippet: Optional[str] = None
    page_number: Optional[int] = None
    line_number: Optional[int] = None
    column_number: Optional[int] = None

class ExtractionResponse(BaseModel):
    project_id: Optional[int] = None
    file_id: Optional[int] = None
    keywords: List[KeywordOccurrenceResponse]
    extractors_used: List[str]
    total_keywords: int

class ExtractorManager:
    """추출기 관리 클래스 (싱글톤)"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, db_session: Session = None):
        if cls._instance is None:
            cls._instance = super(ExtractorManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, db_session: Session = None):
        if not ExtractorManager._initialized:
            self.db_session = db_session
            self.extractors = {}
            self._available_extractors_cache = None
            self._cache_timestamp = 0
            self._cache_duration = 300  # 5분 캐시
            self._initialization_logged = False
            self._initialize_extractors()
            ExtractorManager._initialized = True
            logger.info("🏭 ExtractorManager 싱글톤 인스턴스 초기화 완료")
        else:
            logger.debug("🔄 ExtractorManager 기존 인스턴스 재사용")
    
    def _initialize_extractors(self):
        """설정에 따라 추출기들을 초기화합니다."""
        logger.info("🚀 추출기 초기화 시작...")
        extractor_config = ConfigService.get_extractor_config(self.db_session)
        
        # KeyBERT 추출기
        if extractor_config.get("keybert_enabled", True):
            logger.info("📦 KeyBERT 추출기 등록 중...")
            self.extractors["keybert"] = KeyBERTExtractor({
                "model": extractor_config.get("keybert_model", "all-MiniLM-L6-v2"),
                "max_keywords": extractor_config.get("keybert_max_keywords", 10),
                "use_mmr": extractor_config.get("keybert_use_mmr", True),
                "use_maxsum": extractor_config.get("keybert_use_maxsum", False),
                "diversity": extractor_config.get("keybert_diversity", 0.5),
                "keyphrase_ngram_range": extractor_config.get("keybert_keyphrase_ngram_range", [1, 2]),
                "stop_words": extractor_config.get("keybert_stop_words", "english")
            }, db_session=self.db_session)
            logger.info("✅ KeyBERT 추출기 등록 완료")
        
        # spaCy NER 추출기
        if extractor_config.get("ner_enabled", True):
            logger.info("📦 spaCy NER 추출기 등록 중...")
            self.extractors["spacy_ner"] = SpaCyNERExtractor({
                "model": extractor_config.get("ner_model", "ko_core_news_sm"),
                "auto_download": extractor_config.get("ner_auto_download", True),
                "max_keywords": extractor_config.get("max_keywords", 20)
            }, db_session=self.db_session)
            logger.info("✅ spaCy NER 추출기 등록 완료")
        
        # LLM 추출기
        llm_enabled = extractor_config.get("llm_enabled", False)
        if llm_enabled:
            logger.info("📦 LLM 추출기 등록 중...")
            ollama_config = ConfigService.get_ollama_config(self.db_session)
            llm_extractor = LLMExtractor({
                "provider": extractor_config.get("llm_provider", "ollama"),
                "model": ollama_config.get("model", "llama3.2"),
                "base_url": ollama_config.get("base_url", "http://localhost:11434"),
                "max_keywords": extractor_config.get("max_keywords", 20)
            }, db_session=self.db_session)
            self.extractors["llm"] = llm_extractor
            logger.info("✅ LLM 추출기 등록 완료")
        
        # KoNLPy 추출기
        if extractor_config.get("konlpy_enabled", False):
            logger.info("📦 KoNLPy 추출기 등록 중...")
            self.extractors["konlpy"] = KoNLPyExtractor({
                "tagger": extractor_config.get("konlpy_tagger", "Okt"),
                "min_length": extractor_config.get("konlpy_min_length", 2),
                "min_frequency": extractor_config.get("konlpy_min_frequency", 1),
                "max_keywords": extractor_config.get("konlpy_max_keywords", 15)
            }, db_session=self.db_session)
            logger.info("✅ KoNLPy 추출기 등록 완료")
        
        # LangExtract 추출기 (API 호환성 문제로 기본 비활성화)
        if extractor_config.get("langextract_enabled", False):
            logger.info("📦 LangExtract 추출기 등록 중...")
            ollama_config = ConfigService.get_ollama_config(self.db_session)
            self.extractors["langextract"] = LangExtractExtractor({
                "ollama_base_url": ollama_config.get("base_url", "http://localhost:11434"),
                "ollama_model": ollama_config.get("model", "llama3.2"),
                "ollama_timeout": ollama_config.get("timeout", 30),
                "max_keywords": extractor_config.get("langextract_max_keywords", 15),
                "chunk_size": extractor_config.get("langextract_chunk_size", 2000),
                "overlap": extractor_config.get("langextract_overlap", 200),
                "confidence_threshold": extractor_config.get("langextract_confidence_threshold", 0.6)
            }, db_session=self.db_session)
            logger.info("✅ LangExtract 추출기 등록 완료")
        
        # Metadata 추출기
        if extractor_config.get("metadata_enabled", True):
            logger.info("📦 Metadata 추출기 등록 중...")
            self.extractors["metadata"] = MetadataExtractor({
                "extract_structure": extractor_config.get("metadata_extract_structure", True),
                "extract_statistics": extractor_config.get("metadata_extract_statistics", True),
                "extract_content": extractor_config.get("metadata_extract_content", True),
                "extract_file_info": extractor_config.get("metadata_extract_file_info", True),
                "extract_summary": extractor_config.get("metadata_extract_summary", True),
                "include_filename": extractor_config.get("metadata_include_filename", True),
                "min_heading_length": extractor_config.get("metadata_min_heading_length", 2),
                "max_metadata_keywords": extractor_config.get("metadata_max_metadata_keywords", 20),
                # LLM 설정 추가
                "llm_enabled": extractor_config.get("llm_enabled", False),
                "llm_summary": extractor_config.get("metadata_llm_summary", True),
                "ollama_base_url": ollama_config.get("base_url", "http://localhost:11434"),
                "ollama_model": ollama_config.get("model", "gemma3n:latest"),
                "ollama_timeout": ollama_config.get("timeout", 30)
            }, db_session=self.db_session)
            logger.info("✅ Metadata 추출기 등록 완료")
        
        logger.info(f"🎉 추출기 초기화 완료 - 등록된 추출기: {list(self.extractors.keys())}")
    
    def get_available_extractors(self) -> List[str]:
        """사용 가능한 추출기 목록을 반환합니다 (캐싱 적용)."""
        import time
        
        current_time = time.time()
        
        # 캐시가 유효한 경우 캐시된 결과 반환
        if (self._available_extractors_cache is not None and 
            current_time - self._cache_timestamp < self._cache_duration):
            logger.debug(f"🔄 캐시된 추출기 목록 반환: {self._available_extractors_cache}")
            return self._available_extractors_cache
        
        # 캐시가 없거나 만료된 경우 다시 계산
        available = []
        
        # 첫 번째 확인이거나 캐시 만료 시에만 상세 로깅
        should_log_details = (self._available_extractors_cache is None or 
                            not self._initialization_logged)
        
        if should_log_details:
            logger.info(f"🔍 추출기 가용성 확인 - 등록된 추출기: {list(self.extractors.keys())}")
        else:
            logger.debug(f"🔍 추출기 가용성 재확인 - 등록된 추출기: {list(self.extractors.keys())}")
        
        for name, extractor in self.extractors.items():
            # 모델이 로드되지 않은 경우에만 로드 시도
            if not extractor.is_loaded:
                if should_log_details:
                    logger.info(f"🔄 추출기 '{name}' 모델 로드 시도...")
                load_success = extractor.load_model()
                if should_log_details:
                    logger.info(f"📊 추출기 '{name}': load_model={load_success}, is_available={extractor.is_available()}")
            else:
                logger.debug(f"✅ 추출기 '{name}': 이미 로드됨, is_available={extractor.is_available()}")
            
            if extractor.is_available():
                available.append(name)
        
        # 결과 캐싱
        self._available_extractors_cache = available
        self._cache_timestamp = current_time
        self._initialization_logged = True
        
        if should_log_details:
            logger.info(f"✅ 모든 추출기 유효성 확인 완료")
            logger.info(f"🎯 사용 가능한 추출기: {available}")
        else:
            logger.debug(f"✅ 추출기 재확인 완료 - 사용 가능: {available}")
        
        return available
    
    def invalidate_cache(self):
        """추출기 캐시를 무효화합니다."""
        self._available_extractors_cache = None
        self._cache_timestamp = 0
        self._initialization_logged = False
        logger.debug("🗑️ 추출기 캐시 무효화됨")
    
    def extract_keywords(self, text: str, methods: List[str], filename: str = None, file_path: str = None) -> List[KeywordOccurrenceResponse]:
        """지정된 방법들로 키워드를 추출합니다."""
        all_keywords = []
        
        logger.info(f"키워드 추출 시작 - 파일: {filename or '알 수 없음'}, 추출기: {methods}, 텍스트 길이: {len(text)} 문자")
        
        for method in methods:
            if method in self.extractors:
                extractor = self.extractors[method]
                try:
                    logger.info(f"  '{method}' 추출기로 키워드 추출 중...")
                    from pathlib import Path
                    file_path_obj = Path(file_path) if file_path else None
                    keywords = extractor.extract(text, file_path_obj)
                    
                    method_keywords = []
                    for keyword in keywords:
                        kw_response = KeywordOccurrenceResponse(
                            keyword=keyword.text,
                            extractor_name=keyword.extractor,
                            score=keyword.score,
                            category=keyword.category,
                            start_position=keyword.start_position,
                            end_position=keyword.end_position,
                            context_snippet=keyword.context_snippet,
                            page_number=keyword.page_number,
                            line_number=keyword.line_number,
                            column_number=keyword.column_number
                        )
                        all_keywords.append(kw_response)
                        method_keywords.append(kw_response)
                    
                    # 추출된 키워드 로그 (상위 5개)
                    top_keywords = sorted(method_keywords, key=lambda x: x.score, reverse=True)[:5]
                    keyword_texts = [f"{kw.keyword}({kw.score:.3f})" for kw in top_keywords]
                    logger.info(f"  ✓ '{method}': {len(method_keywords)}개 키워드 추출 완료 - 상위: {', '.join(keyword_texts)}")
                    
                except Exception as e:
                    logger.error(f"  ✗ '{method}' 추출기 오류: {str(e)}")
        
        # 점수 순으로 정렬
        all_keywords.sort(key=lambda x: x.score, reverse=True)
        logger.info(f"키워드 추출 완료 - 총 {len(all_keywords)}개 키워드")
        return all_keywords

@router.post("/projects/{project_id}/extract_keywords", response_model=ExtractionResponse)
def extract_keywords_from_project(
    project_id: int,
    request: ExtractionRequest,
    db: Session = Depends(get_db)
):
    """프로젝트의 모든 파일에서 키워드를 추출합니다."""
    
    logger.info(f"🚀 프로젝트 {project_id} 키워드 추출 요청 - 추출기: {request.methods}")
    
    # 프로젝트 존재 확인
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        logger.error(f"❌ 프로젝트 {project_id}를 찾을 수 없음")
        raise HTTPException(status_code=404, detail="Project not found")
    
    logger.info(f"📁 프로젝트 '{project.name}' 발견")
    
    # 프로젝트의 파일들 가져오기
    files = db.query(File).filter(File.project_id == project_id).all()
    if not files:
        logger.error(f"❌ 프로젝트 {project_id}에 파일이 없음")
        raise HTTPException(status_code=404, detail="No files found in project")
    
    logger.info(f"📄 처리할 파일 {len(files)}개 발견")
    
    # 추출기 관리자 초기화
    extractor_manager = ExtractorManager(db)
    
    # 요청된 방법들이 사용 가능한지 확인
    available_extractors = extractor_manager.get_available_extractors()
    invalid_methods = [method for method in request.methods if method not in available_extractors]
    if invalid_methods:
        logger.error(f"❌ 유효하지 않은 추출기: {invalid_methods}, 사용 가능: {available_extractors}")
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid extraction methods: {invalid_methods}. Available: {available_extractors}"
        )
    
    logger.info(f"✅ 모든 추출기 유효성 확인 완료")
    
    all_keywords = []
    processed_files = 0
    failed_files = 0
    
    # 각 파일에서 키워드 추출
    for file_index, file in enumerate(files, 1):
        try:
            logger.info(f"\n📄 [{file_index}/{len(files)}] 파일 '{file.filename}' 처리 시작")
            
            # 파싱된 텍스트 내용 사용 (파싱이 안된 경우 자동 파싱)
            if file.content and file.parse_status == "success":
                text = file.content
                logger.info(f"  📝 파싱된 콘텐츠 사용 ({len(text)} 문자)")
            else:
                # 파싱이 안된 경우 자동 파싱 시도
                logger.info(f"  🔄 파일 '{file.filename}' 자동 파싱 시작...")
                try:
                    from services.parser import AutoParser
                    from pathlib import Path
                    
                    parser = AutoParser()
                    file_path = Path(file.filepath)
                    
                    if not file_path.exists():
                        logger.error(f"  ❌ 파일이 존재하지 않음: {file.filepath}")
                        failed_files += 1
                        continue
                    
                    parse_result = parser.parse(file_path)
                    
                    if parse_result.success:
                        text = parse_result.text
                        logger.info(f"  ✅ 자동 파싱 성공 ({len(text)} 문자)")
                        
                        # 파싱 결과를 데이터베이스에 저장
                        file.content = text
                        file.parse_status = "success"
                        file.parse_error = None
                        db.commit()
                        db.refresh(file)
                        logger.info(f"  💾 파싱 결과 데이터베이스 저장 완료")
                    else:
                        logger.error(f"  ❌ 파싱 실패: {parse_result.error_message}")
                        text = ""
                        
                        # 파싱 실패 정보를 데이터베이스에 저장
                        file.parse_status = "failed"
                        file.parse_error = parse_result.error_message
                        db.commit()
                        
                        failed_files += 1
                        continue
                        
                except Exception as parse_error:
                    logger.error(f"  ❌ 파싱 중 오류 발생: {parse_error}")
                    
                    # 파싱 오류 정보를 데이터베이스에 저장
                    file.parse_status = "failed"
                    file.parse_error = str(parse_error)
                    db.commit()
                    
                    failed_files += 1
                    continue
            
            # 키워드 추출
            keywords = extractor_manager.extract_keywords(text, request.methods, file.filename, file.filepath)
            
            # 기존 키워드 삭제 (재추출을 위해)
            deleted_count = db.query(KeywordOccurrence).filter(
                KeywordOccurrence.file_id == file.id,
                KeywordOccurrence.extractor_name.in_(request.methods)
            ).delete()
            
            if deleted_count > 0:
                logger.info(f"  🗑️ 기존 키워드 {deleted_count}개 삭제")
            
            # 데이터베이스에 저장
            for keyword_data in keywords:
                keyword_occurrence = KeywordOccurrence(
                    file_id=file.id,
                    keyword=keyword_data.keyword,
                    extractor_name=keyword_data.extractor_name,
                    score=keyword_data.score,
                    category=keyword_data.category,
                    start_position=keyword_data.start_position,
                    end_position=keyword_data.end_position,
                    context_snippet=keyword_data.context_snippet,
                    page_number=keyword_data.page_number,
                    line_number=keyword_data.line_number,
                    column_number=keyword_data.column_number
                )
                db.add(keyword_occurrence)
            
            all_keywords.extend(keywords)
            processed_files += 1
            logger.info(f"  ✅ 파일 '{file.filename}' 처리 완료 - {len(keywords)}개 키워드 추출")
            
        except Exception as e:
            logger.error(f"  ❌ 파일 {file.filename} 처리 중 오류: {str(e)}")
            failed_files += 1
    
    db.commit()
    logger.info(f"💾 데이터베이스 저장 완료")
    
    # 통계 캐시 무효화
    try:
        cache_service = StatisticsCacheService(db)
        cache_service.invalidate_global_cache()
        cache_service.invalidate_project_cache(project_id)
        logger.info(f"🗑️ 키워드 통계 캐시 무효화 완료 (프로젝트 {project_id})")
    except Exception as cache_error:
        logger.warning(f"⚠️ 통계 캐시 무효화 실패: {str(cache_error)}")
    
    # 중복 제거 및 점수 순 정렬
    unique_keywords = {}
    for kw in all_keywords:
        key = (kw.keyword, kw.extractor_name)
        if key not in unique_keywords or unique_keywords[key].score < kw.score:
            unique_keywords[key] = kw
    
    final_keywords = list(unique_keywords.values())
    final_keywords.sort(key=lambda x: x.score, reverse=True)
    
    logger.info(f"🎉 프로젝트 {project_id} 키워드 추출 완료!")
    logger.info(f"  📊 통계: 처리된 파일 {processed_files}개, 실패 {failed_files}개")
    logger.info(f"  🏆 최종 키워드: {len(final_keywords)}개 (중복 제거 후)")
    
    # 상위 키워드 로그
    top_keywords = final_keywords[:10]
    if top_keywords:
        top_keyword_texts = [f"{kw.keyword}({kw.score:.3f})" for kw in top_keywords]
        logger.info(f"  🔝 상위 키워드: {', '.join(top_keyword_texts)}")
    
    return ExtractionResponse(
        project_id=project_id,
        keywords=final_keywords,
        extractors_used=request.methods,
        total_keywords=len(final_keywords)
    )

@router.post("/files/{file_id}/extract_keywords", response_model=ExtractionResponse)
def extract_keywords_from_file(
    file_id: int,
    request: ExtractionRequest,
    db: Session = Depends(get_db)
):
    """특정 파일에서 키워드를 추출합니다."""
    
    logger.info(f"🎯 파일 {file_id} 키워드 추출 요청 - 추출기: {request.methods}")
    
    # 파일 존재 확인
    file = db.query(File).filter(File.id == file_id).first()
    if not file:
        logger.error(f"❌ 파일 {file_id}를 찾을 수 없음")
        raise HTTPException(status_code=404, detail="File not found")
    
    logger.info(f"📄 파일 '{file.filename}' 발견")
    
    # 추출기 관리자 초기화
    extractor_manager = ExtractorManager(db)
    
    # 요청된 방법들이 사용 가능한지 확인
    available_extractors = extractor_manager.get_available_extractors()
    invalid_methods = [method for method in request.methods if method not in available_extractors]
    if invalid_methods:
        logger.error(f"❌ 유효하지 않은 추출기: {invalid_methods}, 사용 가능: {available_extractors}")
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid extraction methods: {invalid_methods}. Available: {available_extractors}"
        )
    
    logger.info(f"✅ 모든 추출기 유효성 확인 완료")
    
    try:
        # 파싱된 텍스트 내용 사용 (파싱이 안된 경우 자동 파싱)
        if file.content and file.parse_status == "success":
            text = file.content
            logger.info(f"📝 파싱된 콘텐츠 사용 ({len(text)} 문자)")
        else:
            # 파싱이 안된 경우 자동 파싱 시도
            logger.info(f"🔄 파일 '{file.filename}' 자동 파싱 시작...")
            try:
                from services.parser import AutoParser
                from pathlib import Path
                
                parser = AutoParser()
                file_path = Path(file.filepath)
                
                if not file_path.exists():
                    logger.error(f"❌ 파일이 존재하지 않음: {file.filepath}")
                    raise HTTPException(status_code=404, detail=f"Physical file not found: {file.filepath}")
                
                parse_result = parser.parse(file_path)
                
                if parse_result.success:
                    text = parse_result.text
                    logger.info(f"✅ 자동 파싱 성공 ({len(text)} 문자)")
                    
                    # 파싱 결과를 데이터베이스에 저장
                    file.content = text
                    file.parse_status = "success"
                    file.parse_error = None
                    db.commit()
                    db.refresh(file)
                    logger.info(f"💾 파싱 결과 데이터베이스 저장 완료")
                else:
                    logger.error(f"❌ 파싱 실패: {parse_result.error_message}")
                    
                    # 파싱 실패 정보를 데이터베이스에 저장
                    file.parse_status = "failed"
                    file.parse_error = parse_result.error_message
                    db.commit()
                    
                    raise HTTPException(
                        status_code=400, 
                        detail=f"파일 파싱 실패: {parse_result.error_message}"
                    )
                    
            except HTTPException:
                raise
            except Exception as parse_error:
                logger.error(f"❌ 파싱 중 오류 발생: {parse_error}")
                
                # 파싱 오류 정보를 데이터베이스에 저장
                file.parse_status = "failed"
                file.parse_error = str(parse_error)
                db.commit()
                
                raise HTTPException(
                    status_code=500, 
                    detail=f"파싱 중 오류 발생: {str(parse_error)}"
                )
        
        # 키워드 추출
        keywords = extractor_manager.extract_keywords(text, request.methods, file.filename)
        
        # 기존 키워드 삭제 (재추출의 경우)
        deleted_count = db.query(KeywordOccurrence).filter(
            KeywordOccurrence.file_id == file_id,
            KeywordOccurrence.extractor_name.in_(request.methods)
        ).delete()
        
        if deleted_count > 0:
            logger.info(f"🗑️ 기존 키워드 {deleted_count}개 삭제")
        
        # 데이터베이스에 저장
        for keyword_data in keywords:
            keyword_occurrence = KeywordOccurrence(
                file_id=file.id,
                keyword=keyword_data.keyword,
                extractor_name=keyword_data.extractor_name,
                score=keyword_data.score,
                category=keyword_data.category,
                start_position=keyword_data.start_position,
                end_position=keyword_data.end_position,
                context_snippet=keyword_data.context_snippet,
                page_number=keyword_data.page_number,
                line_number=keyword_data.line_number,
                column_number=keyword_data.column_number
            )
            db.add(keyword_occurrence)
        
        db.commit()
        logger.info(f"💾 데이터베이스 저장 완료")
        
        # 통계 캐시 무효화 (파일 기반 추출)
        try:
            cache_service = StatisticsCacheService(db)
            cache_service.invalidate_global_cache()
            cache_service.invalidate_project_cache(file.project_id)
            logger.info(f"🗑️ 키워드 통계 캐시 무효화 완료 (파일 {file_id})")
        except Exception as cache_error:
            logger.warning(f"⚠️ 통계 캐시 무효화 실패: {str(cache_error)}")
        
        logger.info(f"🎉 파일 '{file.filename}' 키워드 추출 완료 - {len(keywords)}개 키워드")
        
        # 상위 키워드 로그
        top_keywords = keywords[:5]
        if top_keywords:
            top_keyword_texts = [f"{kw.keyword}({kw.score:.3f})" for kw in top_keywords]
            logger.info(f"🔝 상위 키워드: {', '.join(top_keyword_texts)}")
        
        return ExtractionResponse(
            file_id=file_id,
            keywords=keywords,
            extractors_used=request.methods,
            total_keywords=len(keywords)
        )
        
    except Exception as e:
        logger.error(f"❌ 파일 {file.filename} 처리 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@router.get("/extractors/available")
def get_available_extractors(db: Session = Depends(get_db)):
    """사용 가능한 추출기 목록을 반환합니다."""
    extractor_manager = ExtractorManager(db)
    available = extractor_manager.get_available_extractors()
    
    # 기본 추출기 설정 가져오기
    default_extractors = ConfigService.get_config_value(
        db, "extractor.default_methods", ["keybert", "spacy_ner"]
    )
    
    return {
        "available_extractors": available,
        "default_extractors": default_extractors,
        "total_available": len(available)
    }

@router.get("/projects/{project_id}/keywords")
def get_project_keywords(project_id: int, db: Session = Depends(get_db)):
    """프로젝트의 추출된 키워드들을 조회합니다."""
    
    # 프로젝트 존재 확인
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # 프로젝트의 모든 파일의 키워드 가져오기
    keywords = db.query(KeywordOccurrence).join(File).filter(
        File.project_id == project_id
    ).all()
    
    # 키워드별 통계
    keyword_stats = {}
    for kw in keywords:
        key = kw.keyword
        if key not in keyword_stats:
            keyword_stats[key] = {
                "keyword": kw.keyword,
                "extractors": [],
                "max_score": 0,
                "occurrences": 0,
                "categories": set()
            }
        
        keyword_stats[key]["extractors"].append(kw.extractor_name)
        keyword_stats[key]["max_score"] = max(keyword_stats[key]["max_score"], kw.score)
        keyword_stats[key]["occurrences"] += 1
        if kw.category:
            keyword_stats[key]["categories"].add(kw.category)
    
    # 결과 정리
    result = []
    for stats in keyword_stats.values():
        stats["categories"] = list(stats["categories"])
        stats["extractors"] = list(set(stats["extractors"]))
        result.append(stats)
    
    # 점수 순으로 정렬
    result.sort(key=lambda x: x["max_score"], reverse=True)
    
    return {
        "project_id": project_id,
        "keywords": result,
        "total_unique_keywords": len(result)
    }

@router.get("/files/{file_id}/keywords")
def get_file_keywords(file_id: int, db: Session = Depends(get_db)):
    """파일의 추출된 키워드들을 조회합니다."""
    
    # 파일 존재 확인
    file = db.query(File).filter(File.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # 파일의 키워드 가져오기
    keywords = db.query(KeywordOccurrence).filter(
        KeywordOccurrence.file_id == file_id
    ).order_by(KeywordOccurrence.score.desc()).all()
    
    keyword_responses = []
    for kw in keywords:
        keyword_responses.append(KeywordOccurrenceResponse(
            keyword=kw.keyword,
            extractor_name=kw.extractor_name,
            score=kw.score,
            category=kw.category,
            start_position=kw.start_position,
            end_position=kw.end_position,
            context_snippet=kw.context_snippet,
            page_number=kw.page_number,
            line_number=kw.line_number,
            column_number=kw.column_number
        ))
    
    return {
        "file_id": file_id,
        "filename": file.filename,
        "keywords": keyword_responses,
        "total_keywords": len(keyword_responses)
    }

@router.get("/keywords/statistics")
def get_keywords_statistics(
    project_id: Optional[int] = None, 
    db: Session = Depends(get_db)
):
    """키워드 통계를 조회합니다. project_id가 지정되면 해당 프로젝트만, 없으면 전체를 프로젝트별로 구분하여 반환합니다."""
    
    logger.info(f"📊 키워드 통계 조회 요청 - 프로젝트 ID: {project_id or '전체'}")
    
    if project_id:
        # 특정 프로젝트의 키워드 통계
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        logger.info(f"📁 프로젝트 '{project.name}' 키워드 통계 조회")
        
        # 프로젝트의 키워드들 가져오기
        keywords = db.query(KeywordOccurrence).join(File).filter(
            File.project_id == project_id
        ).all()
        
        # 키워드별 통계 계산
        keyword_stats = {}
        extractor_stats = {}
        category_stats = {}
        
        for kw in keywords:
            # 키워드별 통계
            key = kw.keyword
            if key not in keyword_stats:
                keyword_stats[key] = {
                    "keyword": kw.keyword,
                    "extractors": set(),
                    "max_score": 0,
                    "occurrences": 0,
                    "categories": set(),
                    "files": set()
                }
            
            keyword_stats[key]["extractors"].add(kw.extractor_name)
            keyword_stats[key]["max_score"] = max(keyword_stats[key]["max_score"], kw.score)
            keyword_stats[key]["occurrences"] += 1
            keyword_stats[key]["files"].add(kw.file_id)
            if kw.category:
                keyword_stats[key]["categories"].add(kw.category)
            
            # 추출기별 통계
            extractor = kw.extractor_name
            if extractor not in extractor_stats:
                extractor_stats[extractor] = {
                    "extractor": extractor,
                    "keywords_count": 0,
                    "unique_keywords": set(),
                    "avg_score": 0,
                    "scores": []
                }
            extractor_stats[extractor]["unique_keywords"].add(kw.keyword)
            extractor_stats[extractor]["keywords_count"] += 1
            extractor_stats[extractor]["scores"].append(kw.score)
            
            # 카테고리별 통계
            if kw.category:
                if kw.category not in category_stats:
                    category_stats[kw.category] = {
                        "category": kw.category,
                        "keywords_count": 0,
                        "unique_keywords": set()
                    }
                category_stats[kw.category]["keywords_count"] += 1
                category_stats[kw.category]["unique_keywords"].add(kw.keyword)
        
        # 키워드 통계 정리
        keyword_result = []
        for stats in keyword_stats.values():
            stats["extractors"] = list(stats["extractors"])
            stats["categories"] = list(stats["categories"])
            stats["files_count"] = len(stats["files"])
            del stats["files"]  # 파일 ID 목록은 제거
            keyword_result.append(stats)
        
        # 점수 순으로 정렬
        keyword_result.sort(key=lambda x: x["max_score"], reverse=True)
        
        # 추출기 통계 정리
        extractor_result = []
        for stats in extractor_stats.values():
            stats["unique_keywords_count"] = len(stats["unique_keywords"])
            stats["avg_score"] = round(sum(stats["scores"]) / len(stats["scores"]), 3) if stats["scores"] else 0
            del stats["unique_keywords"]
            del stats["scores"]
            extractor_result.append(stats)
        
        # 카테고리 통계 정리
        category_result = []
        for stats in category_stats.values():
            stats["unique_keywords_count"] = len(stats["unique_keywords"])
            del stats["unique_keywords"]
            category_result.append(stats)
        
        # 카테고리별 정렬 (키워드 수 기준)
        category_result.sort(key=lambda x: x["keywords_count"], reverse=True)
        
        logger.info(f"✅ 프로젝트 '{project.name}' 통계 완료 - 키워드: {len(keyword_result)}개, 추출기: {len(extractor_result)}개, 카테고리: {len(category_result)}개")
        
        return {
            "type": "single_project",
            "project": {
                "id": project.id,
                "name": project.name
            },
            "keywords": keyword_result,
            "extractors": extractor_result,
            "categories": category_result,
            "summary": {
                "total_keywords": len(keywords),
                "unique_keywords": len(keyword_result),
                "extractors_used": len(extractor_result),
                "categories_found": len(category_result)
            }
        }
    
    else:
        # 전체 키워드 통계 (프로젝트별 구분)
        logger.info("🌐 전체 프로젝트 키워드 통계 조회")
        
        # 모든 프로젝트와 키워드 가져오기
        projects = db.query(Project).all()
        all_keywords = db.query(KeywordOccurrence).join(File).join(Project).all()
        
        # 프로젝트별 통계
        project_stats = {}
        global_keyword_stats = {}
        global_extractor_stats = {}
        global_category_stats = {}
        
        for kw in all_keywords:
            project_id = kw.file.project_id
            project_name = kw.file.project.name
            
            # 프로젝트별 통계
            if project_id not in project_stats:
                project_stats[project_id] = {
                    "project_id": project_id,
                    "project_name": project_name,
                    "keywords_count": 0,
                    "unique_keywords": set(),
                    "extractors": set(),
                    "categories": set(),
                    "files": set(),
                    "top_keywords": {},
                    "scores": []
                }
            
            project_stats[project_id]["keywords_count"] += 1
            project_stats[project_id]["unique_keywords"].add(kw.keyword)
            project_stats[project_id]["extractors"].add(kw.extractor_name)
            project_stats[project_id]["files"].add(kw.file_id)
            project_stats[project_id]["scores"].append(kw.score)
            if kw.category:
                project_stats[project_id]["categories"].add(kw.category)
            
            # 프로젝트별 상위 키워드 추적
            if kw.keyword not in project_stats[project_id]["top_keywords"]:
                project_stats[project_id]["top_keywords"][kw.keyword] = {
                    "score": kw.score,
                    "count": 1
                }
            else:
                project_stats[project_id]["top_keywords"][kw.keyword]["score"] = max(
                    project_stats[project_id]["top_keywords"][kw.keyword]["score"], 
                    kw.score
                )
                project_stats[project_id]["top_keywords"][kw.keyword]["count"] += 1
            
            # 전역 키워드 통계
            key = kw.keyword
            if key not in global_keyword_stats:
                global_keyword_stats[key] = {
                    "keyword": kw.keyword,
                    "projects": set(),
                    "extractors": set(),
                    "max_score": 0,
                    "occurrences": 0,
                    "categories": set()
                }
            
            global_keyword_stats[key]["projects"].add(project_id)
            global_keyword_stats[key]["extractors"].add(kw.extractor_name)
            global_keyword_stats[key]["max_score"] = max(global_keyword_stats[key]["max_score"], kw.score)
            global_keyword_stats[key]["occurrences"] += 1
            if kw.category:
                global_keyword_stats[key]["categories"].add(kw.category)
            
            # 전역 추출기 통계
            extractor = kw.extractor_name
            if extractor not in global_extractor_stats:
                global_extractor_stats[extractor] = {
                    "extractor": extractor,
                    "keywords_count": 0,
                    "unique_keywords": set(),
                    "projects": set(),
                    "scores": []
                }
            global_extractor_stats[extractor]["keywords_count"] += 1
            global_extractor_stats[extractor]["unique_keywords"].add(kw.keyword)
            global_extractor_stats[extractor]["projects"].add(project_id)
            global_extractor_stats[extractor]["scores"].append(kw.score)
            
            # 전역 카테고리 통계
            if kw.category:
                if kw.category not in global_category_stats:
                    global_category_stats[kw.category] = {
                        "category": kw.category,
                        "keywords_count": 0,
                        "unique_keywords": set(),
                        "projects": set()
                    }
                global_category_stats[kw.category]["keywords_count"] += 1
                global_category_stats[kw.category]["unique_keywords"].add(kw.keyword)
                global_category_stats[kw.category]["projects"].add(project_id)
        
        # 프로젝트별 통계 정리
        project_result = []
        for stats in project_stats.values():
            # 상위 키워드 선별 (점수 기준 상위 5개)
            top_keywords_list = []
            for keyword, data in stats["top_keywords"].items():
                top_keywords_list.append({
                    "keyword": keyword,
                    "score": data["score"],
                    "count": data["count"]
                })
            top_keywords_list.sort(key=lambda x: x["score"], reverse=True)
            
            project_result.append({
                "project_id": stats["project_id"],
                "project_name": stats["project_name"],
                "keywords_count": stats["keywords_count"],
                "unique_keywords_count": len(stats["unique_keywords"]),
                "extractors_count": len(stats["extractors"]),
                "categories_count": len(stats["categories"]),
                "files_count": len(stats["files"]),
                "avg_score": round(sum(stats["scores"]) / len(stats["scores"]), 3) if stats["scores"] else 0,
                "extractors": list(stats["extractors"]),
                "categories": list(stats["categories"]),
                "top_keywords": top_keywords_list[:5]
            })
        
        # 프로젝트를 키워드 수 기준으로 정렬
        project_result.sort(key=lambda x: x["keywords_count"], reverse=True)
        
        # 전역 키워드 통계 정리
        global_keyword_result = []
        for stats in global_keyword_stats.values():
            stats["projects_count"] = len(stats["projects"])
            stats["extractors"] = list(stats["extractors"])
            stats["categories"] = list(stats["categories"])
            del stats["projects"]  # 프로젝트 ID 목록은 제거
            global_keyword_result.append(stats)
        
        # 점수 순으로 정렬
        global_keyword_result.sort(key=lambda x: x["max_score"], reverse=True)
        
        # 전역 추출기 통계 정리
        global_extractor_result = []
        for stats in global_extractor_stats.values():
            stats["unique_keywords_count"] = len(stats["unique_keywords"])
            stats["projects_count"] = len(stats["projects"])
            stats["avg_score"] = round(sum(stats["scores"]) / len(stats["scores"]), 3) if stats["scores"] else 0
            del stats["unique_keywords"]
            del stats["projects"]
            del stats["scores"]
            global_extractor_result.append(stats)
        
        # 전역 카테고리 통계 정리
        global_category_result = []
        for stats in global_category_stats.values():
            stats["unique_keywords_count"] = len(stats["unique_keywords"])
            stats["projects_count"] = len(stats["projects"])
            del stats["unique_keywords"]
            del stats["projects"]
            global_category_result.append(stats)
        
        # 카테고리별 정렬 (키워드 수 기준)
        global_category_result.sort(key=lambda x: x["keywords_count"], reverse=True)
        
        logger.info(f"✅ 전체 통계 완료 - 프로젝트: {len(project_result)}개, 전역 키워드: {len(global_keyword_result)}개, 추출기: {len(global_extractor_result)}개, 카테고리: {len(global_category_result)}개")
        
        return {
            "type": "all_projects",
            "projects": project_result,
            "global_keywords": global_keyword_result[:50],  # 상위 50개만
            "global_extractors": global_extractor_result,
            "global_categories": global_category_result,
            "summary": {
                "total_projects": len(project_result),
                "total_keywords": len(all_keywords),
                "unique_keywords": len(global_keyword_result),
                "extractors_used": len(global_extractor_result),
                "categories_found": len(global_category_result)
            }
        }

@router.get("/keywords/list")
def get_keywords_list(
    project_id: Optional[int] = None,
    extractor: Optional[str] = None,
    category: Optional[str] = None,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    db: Session = Depends(get_db)
):
    """키워드 목록을 조회합니다. 필터링 옵션과 페이지네이션을 지원합니다."""
    
    logger.info(f"📋 키워드 목록 조회 - 프로젝트: {project_id or '전체'}, 추출기: {extractor or '전체'}, 카테고리: {category or '전체'}")
    
    # 기본 쿼리 구성
    query = db.query(KeywordOccurrence).join(File).join(Project)
    
    # 프로젝트 필터
    if project_id:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        query = query.filter(File.project_id == project_id)
        logger.info(f"📁 프로젝트 '{project.name}' 필터 적용")
    
    # 추출기 필터
    if extractor:
        query = query.filter(KeywordOccurrence.extractor_name == extractor)
        logger.info(f"🔧 추출기 '{extractor}' 필터 적용")
    
    # 카테고리 필터
    if category:
        query = query.filter(KeywordOccurrence.category == category)
        logger.info(f"🏷️ 카테고리 '{category}' 필터 적용")
    
    # 전체 개수 조회
    total_count = query.count()
    
    # 페이지네이션 적용 및 점수 순 정렬
    keywords = query.order_by(KeywordOccurrence.score.desc()).offset(offset).limit(limit).all()
    
    # 결과 정리
    keyword_list = []
    for kw in keywords:
        keyword_list.append({
            "keyword": kw.keyword,
            "score": kw.score,
            "extractor_name": kw.extractor_name,
            "category": kw.category,
            "start_position": kw.start_position,
            "end_position": kw.end_position,
            "context_snippet": kw.context_snippet,
            "file": {
                "id": kw.file.id,
                "filename": kw.file.filename,
                "project": {
                    "id": kw.file.project.id,
                    "name": kw.file.project.name
                }
            }
        })
    
    logger.info(f"✅ 키워드 목록 조회 완료 - {len(keyword_list)}개 반환 (전체: {total_count}개)")
    
    return {
        "keywords": keyword_list,
        "pagination": {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_next": offset + limit < total_count,
            "has_prev": offset > 0
        },
        "filters": {
            "project_id": project_id,
            "extractor": extractor,
            "category": category
        }
    }

@router.get("/llm/test_connection")
def test_llm_connection(db: Session = Depends(get_db)):
    """LLM 서버 연결을 테스트합니다."""
    try:
        # 설정 가져오기
        ollama_config = ConfigService.get_ollama_config(db)
        extractor_config = ConfigService.get_extractor_config(db)
        
        # LLM 추출기 초기화
        llm_extractor = LLMExtractor({
            "provider": extractor_config.get("llm_provider", "ollama"),
            "model": ollama_config.get("model", "llama3.2"),
            "base_url": ollama_config.get("base_url", "http://localhost:11434"),
            "timeout": ollama_config.get("timeout", 30)
        }, db_session=db)
        
        # 연결 테스트
        connection_success = llm_extractor.load_model()
        
        if connection_success:
            # 간단한 키워드 추출 테스트
            test_text = "인공지능과 머신러닝은 현대 기술의 핵심입니다."
            keywords = llm_extractor.extract(test_text)
            
            return {
                "status": "success",
                "message": "LLM 서버 연결 성공",
                "provider": llm_extractor.provider,
                "model": llm_extractor.model_name,
                "base_url": llm_extractor.base_url,
                "test_keywords_count": len(keywords),
                "test_keywords": [kw.text for kw in keywords[:5]]  # 처음 5개만
            }
        else:
            return {
                "status": "error",
                "message": "LLM 서버 연결 실패",
                "provider": llm_extractor.provider,
                "model": llm_extractor.model_name,
                "base_url": llm_extractor.base_url
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"LLM 연결 테스트 중 오류 발생: {str(e)}",
            "provider": "ollama",
            "model": "llama3.2",
            "base_url": "http://localhost:11434"
        }

@router.get("/llm/ollama/models")
def get_ollama_models(db: Session = Depends(get_db)):
    """Ollama 서버에서 사용 가능한 모델 목록을 가져옵니다."""
    try:
        # 설정에서 Ollama 서버 정보 가져오기
        ollama_config = ConfigService.get_ollama_config(db)
        base_url = ollama_config.get("base_url", "http://localhost:11434")
        
        # Ollama API를 통해 모델 목록 가져오기
        import requests
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        
        if response.status_code == 200:
            models_data = response.json().get("models", [])
            
            # 모델 정보 정리
            models = []
            for model in models_data:
                model_name = model.get("name", "")
                size = model.get("size", 0)
                modified_at = model.get("modified_at", "")
                
                models.append({
                    "name": model_name,
                    "display_name": model_name.split(":")[0],  # 태그 제거
                    "size": size,
                    "size_gb": round(size / (1024**3), 2) if size else 0,
                    "modified_at": modified_at
                })
            
            return {
                "status": "success",
                "base_url": base_url,
                "models": models,
                "total_models": len(models)
            }
        else:
            return {
                "status": "error",
                "message": f"Ollama 서버 응답 오류: {response.status_code}",
                "base_url": base_url,
                "models": [],
                "total_models": 0
            }
            
    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "message": "Ollama 서버에 연결할 수 없습니다",
            "base_url": ollama_config.get("base_url", "http://localhost:11434"),
            "models": [],
            "total_models": 0
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"모델 목록 조회 중 오류 발생: {str(e)}",
            "base_url": ollama_config.get("base_url", "http://localhost:11434"),
            "models": [],
            "total_models": 0
        }