from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import List
from db.models import Project, KeywordOccurrence, File as FileModel
from response_models import ProjectCreate, ProjectResponse
from dependencies import get_db
from services.statistics_cache_service import StatisticsCacheService

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("/", response_model=ProjectResponse)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    db_project = db.query(Project).filter(Project.name == project.name).first()
    if db_project:
        raise HTTPException(status_code=400, detail="Project with this name already exists")
    
    db_project = Project(name=project.name)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

@router.get("/", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).all()
    return projects

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: int, project_update: ProjectCreate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if new name already exists (if different from current)
    if project_update.name != project.name:
        existing = db.query(Project).filter(Project.name == project_update.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Project with this name already exists")
    
    project.name = project_update.name
    db.commit()
    db.refresh(project)
    return project

@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    from db.models import File as FileModel
    import shutil
    from pathlib import Path
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Delete all files associated with the project
    files = db.query(FileModel).filter(FileModel.project_id == project_id).all()
    for file in files:
        db.delete(file)
    
    # Delete physical files directory
    try:
        upload_dir = Path("./data/uploads") / str(project_id)
        if upload_dir.exists():
            shutil.rmtree(upload_dir)
    except Exception as e:
        print(f"Warning: Could not delete physical files for project {project_id}: {str(e)}")
    
    # Delete project
    db.delete(project)
    db.commit()
    
    # 통계 캐시 무효화
    try:
        cache_service = StatisticsCacheService(db)
        cache_service.invalidate_global_cache()
        cache_service.invalidate_project_cache(project_id)
        print(f"Statistics cache invalidated for deleted project {project_id}")
    except Exception as e:
        print(f"Warning: Could not invalidate statistics cache for project {project_id}: {str(e)}")
    
    return {"message": f"Project '{project.name}' deleted successfully"}

@router.get("/statistics/global")
def get_global_keyword_statistics(force_refresh: bool = False, db: Session = Depends(get_db)):
    """전체 프로젝트의 키워드 통계를 캐시에서 조회합니다."""
    cache_service = StatisticsCacheService(db)
    return cache_service.get_global_statistics(force_refresh=force_refresh)

@router.get("/{project_id}/statistics")
def get_project_keyword_statistics(project_id: int, force_refresh: bool = False, db: Session = Depends(get_db)):
    """특정 프로젝트의 키워드 통계를 캐시에서 조회합니다."""
    try:
        cache_service = StatisticsCacheService(db)
        return cache_service.get_project_statistics(project_id, force_refresh=force_refresh)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"Error getting project keyword statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/statistics/refresh")
def refresh_all_statistics_cache(db: Session = Depends(get_db)):
    """모든 키워드 통계 캐시를 갱신합니다."""
    try:
        cache_service = StatisticsCacheService(db)
        cache_service.refresh_all_caches()
        return {"message": "All statistics cache refreshed successfully"}
    except Exception as e:
        print(f"Error refreshing statistics cache: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to refresh statistics cache")

@router.delete("/statistics/cache")
def clear_statistics_cache(db: Session = Depends(get_db)):
    """모든 키워드 통계 캐시를 삭제합니다."""
    try:
        cache_service = StatisticsCacheService(db)
        cache_service.invalidate_global_cache()
        
        # 모든 프로젝트의 캐시도 삭제
        projects = db.query(Project).all()
        for project in projects:
            cache_service.invalidate_project_cache(project.id)
            
        return {"message": "All statistics cache cleared successfully"}
    except Exception as e:
        print(f"Error clearing statistics cache: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to clear statistics cache")