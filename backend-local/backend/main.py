import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.db import Base, engine, SessionLocal
from response_models import StatusResponse
from services.config_service import ConfigService
from routers.knowledge_graph import router as knowledge_graph_router

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backend-local.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="DocExtract Local Analysis API",
    description="Knowledge Graph 생성을 위한 경량 로컬 분석 서버",
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

# 라우터 등록 (Knowledge Graph 전용)
app.include_router(knowledge_graph_router)
logger.info("Knowledge Graph 라우터 등록 완료")

@app.get("/", response_model=StatusResponse)
def read_root():
    logger.info("루트 엔드포인트 접근")
    return {"message": "Local Knowledge Graph analysis server is running."}
