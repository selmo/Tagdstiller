from sqlalchemy.orm import Session
from sqlalchemy import func, text
from db.models import KeywordStatisticsCache, Project, File as FileModel, KeywordOccurrence
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class StatisticsCacheService:
    """키워드 통계 캐시를 관리하는 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        
    def get_global_statistics(self, force_refresh: bool = False) -> dict:
        """전체 키워드 통계를 캐시에서 조회하거나 갱신"""
        try:
            # 캐시된 전체 통계 조회
            cached_stats = self.db.query(KeywordStatisticsCache).filter(
                KeywordStatisticsCache.cache_type == 'global'
            ).first()
            
            # 캐시가 없거나 강제 갱신이거나 1시간이 지났으면 갱신
            should_refresh = (
                force_refresh or 
                not cached_stats or 
                cached_stats.last_updated < datetime.utcnow() - timedelta(hours=1)
            )
            
            if should_refresh:
                logger.info("전체 키워드 통계 캐시 갱신 시작")
                cached_stats = self._refresh_global_statistics()
                
            return {
                "total_projects": cached_stats.total_projects,
                "total_files": cached_stats.total_files,
                "total_keywords": cached_stats.total_keywords,
                "total_occurrences": cached_stats.total_occurrences,
                "extractors_used": cached_stats.extractors_used or []
            }
            
        except Exception as e:
            logger.error(f"전체 키워드 통계 조회 오류: {str(e)}")
            # 실패 시 실시간 계산으로 폴백
            return self._calculate_global_statistics_realtime()
    
    def get_project_statistics(self, project_id: int, force_refresh: bool = False) -> dict:
        """프로젝트별 키워드 통계를 캐시에서 조회하거나 갱신"""
        try:
            # 프로젝트 존재 확인
            project = self.db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            # 캐시된 프로젝트 통계 조회
            cached_stats = self.db.query(KeywordStatisticsCache).filter(
                KeywordStatisticsCache.cache_type == 'project',
                KeywordStatisticsCache.project_id == project_id
            ).first()
            
            # 캐시가 없거나 강제 갱신이거나 30분이 지났으면 갱신
            should_refresh = (
                force_refresh or 
                not cached_stats or 
                cached_stats.last_updated < datetime.utcnow() - timedelta(minutes=30)
            )
            
            if should_refresh:
                logger.info(f"프로젝트 {project_id} 키워드 통계 캐시 갱신 시작")
                cached_stats = self._refresh_project_statistics(project_id)
            
            return {
                "project_id": project_id,
                "project_name": project.name,
                "total_files": cached_stats.total_files,
                "total_keywords": cached_stats.total_keywords,
                "total_occurrences": cached_stats.total_occurrences,
                "extractors_used": cached_stats.extractors_used or []
            }
            
        except Exception as e:
            logger.error(f"프로젝트 {project_id} 키워드 통계 조회 오류: {str(e)}")
            # 실패 시 실시간 계산으로 폴백
            return self._calculate_project_statistics_realtime(project_id)
    
    def invalidate_global_cache(self):
        """전체 통계 캐시 무효화"""
        try:
            self.db.query(KeywordStatisticsCache).filter(
                KeywordStatisticsCache.cache_type == 'global'
            ).delete()
            self.db.commit()
            logger.info("전체 키워드 통계 캐시 무효화됨")
        except Exception as e:
            logger.error(f"전체 통계 캐시 무효화 오류: {str(e)}")
            self.db.rollback()
    
    def invalidate_project_cache(self, project_id: int):
        """특정 프로젝트 통계 캐시 무효화"""
        try:
            self.db.query(KeywordStatisticsCache).filter(
                KeywordStatisticsCache.cache_type == 'project',
                KeywordStatisticsCache.project_id == project_id
            ).delete()
            self.db.commit()
            logger.info(f"프로젝트 {project_id} 키워드 통계 캐시 무효화됨")
        except Exception as e:
            logger.error(f"프로젝트 {project_id} 통계 캐시 무효화 오류: {str(e)}")
            self.db.rollback()
    
    def refresh_all_caches(self):
        """모든 통계 캐시 갱신"""
        try:
            logger.info("모든 키워드 통계 캐시 갱신 시작")
            
            # 전체 통계 갱신
            self._refresh_global_statistics()
            
            # 모든 프로젝트 통계 갱신
            projects = self.db.query(Project).all()
            for project in projects:
                self._refresh_project_statistics(project.id)
                
            logger.info("모든 키워드 통계 캐시 갱신 완료")
            
        except Exception as e:
            logger.error(f"통계 캐시 갱신 오류: {str(e)}")
            self.db.rollback()
    
    def _refresh_global_statistics(self) -> KeywordStatisticsCache:
        """전체 통계 캐시 갱신"""
        stats = self._calculate_global_statistics_realtime()
        
        # 기존 캐시 삭제
        self.db.query(KeywordStatisticsCache).filter(
            KeywordStatisticsCache.cache_type == 'global'
        ).delete()
        
        # 새 캐시 생성
        cached_stats = KeywordStatisticsCache(
            cache_type='global',
            project_id=None,
            total_keywords=stats['total_keywords'],
            total_occurrences=stats['total_occurrences'],
            total_files=stats['total_files'],
            total_projects=stats['total_projects'],
            extractors_used=stats['extractors_used']
        )
        
        self.db.add(cached_stats)
        self.db.commit()
        self.db.refresh(cached_stats)
        
        logger.info(f"전체 키워드 통계 캐시 갱신 완료: {stats['total_keywords']}개 키워드")
        return cached_stats
    
    def _refresh_project_statistics(self, project_id: int) -> KeywordStatisticsCache:
        """프로젝트 통계 캐시 갱신"""
        stats = self._calculate_project_statistics_realtime(project_id)
        
        # 기존 캐시 삭제
        self.db.query(KeywordStatisticsCache).filter(
            KeywordStatisticsCache.cache_type == 'project',
            KeywordStatisticsCache.project_id == project_id
        ).delete()
        
        # 새 캐시 생성
        cached_stats = KeywordStatisticsCache(
            cache_type='project',
            project_id=project_id,
            total_keywords=stats['total_keywords'],
            total_occurrences=stats['total_occurrences'],
            total_files=stats['total_files'],
            total_projects=0,  # 프로젝트별 통계에서는 사용하지 않음
            extractors_used=stats['extractors_used']
        )
        
        self.db.add(cached_stats)
        self.db.commit()
        self.db.refresh(cached_stats)
        
        logger.info(f"프로젝트 {project_id} 키워드 통계 캐시 갱신 완료: {stats['total_keywords']}개 키워드")
        return cached_stats
    
    def _calculate_global_statistics_realtime(self) -> dict:
        """전체 통계 실시간 계산 (폴백용)"""
        try:
            # 전체 프로젝트 수
            total_projects = self.db.query(Project).count()
            
            # 전체 파일 수
            total_files = self.db.query(FileModel).count()
            
            # 전체 키워드 통계 - 파일과 조인하여 유효한 키워드만 계산
            keyword_stats_query = self.db.query(
                func.count().label('total_occurrences'),
                func.count(func.distinct(func.lower(func.trim(KeywordOccurrence.keyword)))).label('unique_keywords')
            ).join(FileModel, KeywordOccurrence.file_id == FileModel.id).first()
            
            # 사용된 추출기 목록 - 파일과 조인하여 유효한 추출기만 계산
            extractors_list = self.db.query(
                func.distinct(KeywordOccurrence.extractor_name)
            ).join(FileModel, KeywordOccurrence.file_id == FileModel.id)\
             .filter(KeywordOccurrence.extractor_name.isnot(None)).all()
            
            extractors = [ext[0] for ext in extractors_list if ext[0]]
            
            return {
                "total_projects": total_projects,
                "total_files": total_files,
                "total_keywords": keyword_stats_query.unique_keywords or 0,
                "total_occurrences": keyword_stats_query.total_occurrences or 0,
                "extractors_used": extractors
            }
            
        except Exception as e:
            logger.error(f"전체 통계 실시간 계산 오류: {str(e)}")
            return {
                "total_projects": 0,
                "total_files": 0,
                "total_keywords": 0,
                "total_occurrences": 0,
                "extractors_used": []
            }
    
    def _calculate_project_statistics_realtime(self, project_id: int) -> dict:
        """프로젝트 통계 실시간 계산 (폴백용)"""
        try:
            # 프로젝트의 파일 수
            total_files = self.db.query(FileModel).filter(FileModel.project_id == project_id).count()
            
            # 프로젝트의 키워드 통계
            keyword_stats_query = self.db.query(
                func.count().label('total_occurrences'),
                func.count(func.distinct(func.lower(func.trim(KeywordOccurrence.keyword)))).label('unique_keywords')
            ).join(FileModel, KeywordOccurrence.file_id == FileModel.id)\
             .filter(FileModel.project_id == project_id).first()
            
            # 사용된 추출기 목록
            extractors_list = self.db.query(
                func.distinct(KeywordOccurrence.extractor_name)
            ).join(FileModel, KeywordOccurrence.file_id == FileModel.id)\
             .filter(FileModel.project_id == project_id)\
             .filter(KeywordOccurrence.extractor_name.isnot(None)).all()
            
            extractors = [ext[0] for ext in extractors_list if ext[0]]
            
            return {
                "total_files": total_files,
                "total_keywords": keyword_stats_query.unique_keywords or 0,
                "total_occurrences": keyword_stats_query.total_occurrences or 0,
                "extractors_used": extractors
            }
            
        except Exception as e:
            logger.error(f"프로젝트 {project_id} 통계 실시간 계산 오류: {str(e)}")
            return {
                "total_files": 0,
                "total_keywords": 0,
                "total_occurrences": 0,
                "extractors_used": []
            }