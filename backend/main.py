import logging
import sys
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.db import Base, engine, SessionLocal
from routers import projects, files, configs, extraction, admin, spacy_models, prompts, local_analysis, kg, memgraph
from response_models import StatusResponse
from services.config_service import ConfigService

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backend.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="DocExtract API",
    description="문서 업로드 및 키워드 추출 API 서버",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://127.0.0.1:3001", "http://localhost:8088", "http://127.0.0.1:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB 테이블 생성
Base.metadata.create_all(bind=engine)
logger.info("데이터베이스 테이블 생성 완료")

# 기본 설정 값 초기화 및 캐시 초기화
import os
from services.config_cache import config_cache

# 환경변수 확인
offline_mode = os.getenv('OFFLINE_MODE') == 'true'
skip_checks = os.getenv('SKIP_EXTERNAL_CHECKS') == 'true'

if offline_mode or skip_checks:
    logger.info("🔄 오프라인/빠른 시작 모드 활성화")

db = SessionLocal()
try:
    ConfigService.initialize_default_configs(db)
    config_cache.initialize(db)
    logger.info("기본 설정 초기화 및 캐시 초기화 완료")
finally:
    db.close()

# 라우터 등록
app.include_router(projects.router)
app.include_router(files.router)
app.include_router(files.files_router)  # 직접 파일 접근용 라우터 추가
app.include_router(configs.router)
app.include_router(extraction.router)
app.include_router(admin.router)
app.include_router(spacy_models.router)
app.include_router(prompts.router)
app.include_router(local_analysis.router)
app.include_router(kg.router)
app.include_router(memgraph.router)
logger.info("모든 라우터 등록 완료")

@app.get("/", response_model=StatusResponse)
def read_root():
    logger.info("루트 엔드포인트 접근")
    return {"message": "Keyword Extraction Server with SQLite is running."}
