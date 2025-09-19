from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil
import mimetypes
from pathlib import Path
from db.models import Project, File as FileModel
from response_models import FileResponse
from dependencies import get_db
from services.parser import AutoParser, get_supported_extensions
from services.parser.zip_parser import ZipParser

router = APIRouter(prefix="/projects", tags=["files"])
files_router = APIRouter(prefix="/files", tags=["files-direct"])

UPLOAD_DIR = Path(__file__).parent.parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/{project_id}/upload", response_model=FileResponse)
async def upload_file(
    project_id: int, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    auto_parse: bool = False
):
    # Check if project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check file extension
    file_path_obj = Path(file.filename)
    file_extension = file_path_obj.suffix.lower()
    supported_extensions = get_supported_extensions()
    
    if file_extension not in supported_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"지원하지 않는 파일 형식입니다. 지원 형식: {', '.join(supported_extensions)}"
        )
    
    # Create project-specific directory
    project_dir = UPLOAD_DIR / str(project_id)
    project_dir.mkdir(exist_ok=True)
    
    # Save file
    file_path = project_dir / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Get file info
    file_size = os.path.getsize(file_path)
    mime_type, _ = mimetypes.guess_type(str(file_path))
    
    # Parse document if auto_parse is enabled
    parsed_content = None
    parse_status = "not_parsed"
    parse_error = None
    metadata = None
    
    if auto_parse:
        try:
            parser = AutoParser()
            parse_result = parser.parse(file_path)
            
            if parse_result.success:
                parsed_content = parse_result.text
                parse_status = "success"
                metadata = parse_result.metadata
            else:
                parse_status = "failed"
                parse_error = parse_result.error_message
                
        except Exception as e:
            parse_status = "failed"
            parse_error = str(e)
    
    # Save file info to database with metadata
    db_file = FileModel(
        project_id=project_id,
        filename=file.filename,
        filepath=str(file_path),
        size=file_size,
        mime_type=mime_type,
        content=parsed_content,
        parse_status=parse_status,
        parse_error=parse_error,
        
        # Dublin Core 메타데이터
        dc_title=metadata.dc_title if metadata else None,
        dc_creator=metadata.dc_creator if metadata else None,
        dc_subject=metadata.dc_subject if metadata else None,
        dc_description=metadata.dc_description if metadata else None,
        dc_publisher=metadata.dc_publisher if metadata else None,
        dc_contributor=metadata.dc_contributor if metadata else None,
        dc_date=metadata.dc_date if metadata else None,
        dc_type=metadata.dc_type if metadata else None,
        dc_format=metadata.dc_format if metadata else mime_type,
        dc_identifier=metadata.dc_identifier if metadata else file.filename,
        dc_source=metadata.dc_source if metadata else str(file_path),
        dc_language=metadata.dc_language if metadata else None,
        dc_relation=metadata.dc_relation if metadata else None,
        dc_coverage=metadata.dc_coverage if metadata else None,
        dc_rights=metadata.dc_rights if metadata else None,
        
        # Dublin Core Terms
        dcterms_created=metadata.dcterms_created if metadata else None,
        dcterms_modified=metadata.dcterms_modified if metadata else None,
        dcterms_extent=metadata.dcterms_extent if metadata else f"{file_size} bytes",
        dcterms_medium=metadata.dcterms_medium if metadata else "digital",
        dcterms_audience=metadata.dcterms_audience if metadata else None,
        
        # 파일 메타데이터
        file_name=metadata.file_name if metadata else file.filename,
        file_path=metadata.file_path if metadata else str(file_path),
        file_size=metadata.file_size if metadata else file_size,
        file_extension=metadata.file_extension if metadata else file_path_obj.suffix.lower(),
        
        # 문서 메타데이터
        doc_page_count=metadata.doc_page_count if metadata else None,
        doc_word_count=metadata.doc_word_count if metadata else None,
        doc_character_count=metadata.doc_character_count if metadata else None,
        doc_type_code=metadata.doc_type_code if metadata else None,
        doc_supported=metadata.doc_supported if metadata else "yes",
        
        # 애플리케이션 메타데이터
        app_version=metadata.app_version if metadata else None,
        
        # 파서 정보
        parser_name=metadata.parser_name if metadata else None,
        parser_version=metadata.parser_version if metadata else None
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    
    return db_file


@router.post("/{project_id}/upload_bulk", response_model=List[FileResponse])
async def upload_bulk_files(
    project_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    auto_parse: bool = False,
    extract_zip: bool = True
):
    """여러 파일을 한 번에 업로드합니다. ZIP 파일은 자동으로 추출됩니다."""
    # Check if project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    uploaded_files = []
    supported_extensions = get_supported_extensions()
    
    # Create project-specific directory
    project_dir = UPLOAD_DIR / str(project_id)
    project_dir.mkdir(exist_ok=True)
    
    for file in files:
        try:
            print(f"Processing uploaded file: {file.filename}")
            # Check file extension
            file_path_obj = Path(file.filename)
            file_extension = file_path_obj.suffix.lower()
            
            if file_extension not in supported_extensions and file_extension != '.zip':
                print(f"Skipping unsupported file: {file.filename}")
                continue  # Skip unsupported files
            
            # Save file
            file_path = project_dir / file.filename
            print(f"Saving file to: {file_path}")
            
            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            print(f"File saved successfully: {file_path}")
            
            # Handle ZIP files
            if file_extension == '.zip' and extract_zip:
                zip_parser = ZipParser()
                success, extracted_files, error = zip_parser.extract_files(
                    file_path, project_dir / f"{file_path_obj.stem}_extracted"
                )
                
                if success:
                    # Process extracted files
                    for extracted_file_path in extracted_files:
                        # ZIP 파일에서 추출된 파일의 원본 경로 구조 유지
                        extraction_dir = project_dir / f"{file_path_obj.stem}_extracted"
                        rel_path = extracted_file_path.relative_to(extraction_dir)
                        
                        # 실제 프로젝트 디렉토리에 파일을 디렉토리 구조를 유지하며 복사
                        target_path = project_dir / rel_path
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # 파일 복사
                        try:
                            shutil.copy2(extracted_file_path, target_path)
                            print(f"Successfully copied {extracted_file_path} to {target_path}")
                        except Exception as copy_error:
                            print(f"Failed to copy {extracted_file_path} to {target_path}: {copy_error}")
                            continue
                        
                        uploaded_file = await _process_uploaded_file(
                            project_id, target_path, str(rel_path), 
                            db, auto_parse, None
                        )
                        if uploaded_file:
                            uploaded_files.append(uploaded_file)
                    
                    # 임시 추출 디렉토리 정리
                    try:
                        shutil.rmtree(extraction_dir)
                    except Exception as e:
                        print(f"Warning: Could not remove temporary extraction directory {extraction_dir}: {e}")
                    
                    # Also save ZIP file info
                    zip_file = await _process_uploaded_file(
                        project_id, file_path, file.filename, db, auto_parse, None
                    )
                    if zip_file:
                        uploaded_files.append(zip_file)
                else:
                    # If extraction failed, still process as regular file
                    uploaded_file = await _process_uploaded_file(
                        project_id, file_path, file.filename, db, auto_parse, None
                    )
                    if uploaded_file:
                        uploaded_files.append(uploaded_file)
            else:
                # Regular file processing
                uploaded_file = await _process_uploaded_file(
                    project_id, file_path, file.filename, db, auto_parse, None
                )
                if uploaded_file:
                    uploaded_files.append(uploaded_file)
                    
        except Exception as e:
            # Log error but continue with other files
            print(f"Error processing file {file.filename}: {str(e)}")
            continue
    
    return uploaded_files

async def _process_uploaded_file(
    project_id: int, 
    file_path: Path, 
    filename: str, 
    db: Session, 
    auto_parse: bool = False,
    subdirectory: Optional[str] = None
) -> Optional[FileModel]:
    """개별 파일을 처리하고 데이터베이스에 저장합니다."""
    try:
        # Get file info
        file_size = os.path.getsize(file_path)
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        # Parse document if auto_parse is enabled
        parsed_content = None
        parse_status = "not_parsed"
        parse_error = None
        metadata = None
        
        if auto_parse:
            try:
                parser = AutoParser()
                parse_result = parser.parse(file_path)
                
                if parse_result.success:
                    parsed_content = parse_result.text
                    parse_status = "success"
                    metadata = parse_result.metadata
                else:
                    parse_status = "failed"
                    parse_error = parse_result.error_message
                    
            except Exception as e:
                parse_status = "failed"
                parse_error = str(e)
        
        # Save file info to database with metadata
        db_file = FileModel(
            project_id=project_id,
            filename=filename,
            filepath=str(file_path),
            size=file_size,
            mime_type=mime_type,
            content=parsed_content,
            parse_status=parse_status,
            parse_error=parse_error,
            
            # Dublin Core 메타데이터
            dc_title=metadata.dc_title if metadata else None,
            dc_creator=metadata.dc_creator if metadata else None,
            dc_subject=metadata.dc_subject if metadata else None,
            dc_description=metadata.dc_description if metadata else None,
            dc_publisher=metadata.dc_publisher if metadata else None,
            dc_contributor=metadata.dc_contributor if metadata else None,
            dc_date=metadata.dc_date if metadata else None,
            dc_type=metadata.dc_type if metadata else None,
            dc_format=metadata.dc_format if metadata else mime_type,
            dc_identifier=metadata.dc_identifier if metadata else filename,
            dc_source=metadata.dc_source if metadata else str(file_path),
            dc_language=metadata.dc_language if metadata else None,
            dc_relation=metadata.dc_relation if metadata else None,
            dc_coverage=metadata.dc_coverage if metadata else None,
            dc_rights=metadata.dc_rights if metadata else None,
            
            # Dublin Core Terms
            dcterms_created=metadata.dcterms_created if metadata else None,
            dcterms_modified=metadata.dcterms_modified if metadata else None,
            dcterms_extent=metadata.dcterms_extent if metadata else f"{file_size} bytes",
            dcterms_medium=metadata.dcterms_medium if metadata else "digital",
            dcterms_audience=metadata.dcterms_audience if metadata else None,
            
            # 파일 메타데이터
            file_name=metadata.file_name if metadata else filename,
            file_path=metadata.file_path if metadata else str(file_path),
            file_size=metadata.file_size if metadata else file_size,
            file_extension=metadata.file_extension if metadata else file_path.suffix.lower(),
            
            # 문서 메타데이터
            doc_page_count=metadata.doc_page_count if metadata else None,
            doc_word_count=metadata.doc_word_count if metadata else None,
            doc_character_count=metadata.doc_character_count if metadata else None,
            doc_type_code=metadata.doc_type_code if metadata else None,
            doc_supported=metadata.doc_supported if metadata else "yes",
            
            # 애플리케이션 메타데이터
            app_version=metadata.app_version if metadata else None,
            
            # 파서 정보
            parser_name=metadata.parser_name if metadata else None,
            parser_version=metadata.parser_version if metadata else None
        )
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        
        return db_file
        
    except Exception as e:
        print(f"Error processing file {filename}: {str(e)}")
        return None

@router.get("/{project_id}/files", response_model=List[FileResponse])
def list_project_files(project_id: int, db: Session = Depends(get_db)):
    # Check if project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    files = db.query(FileModel).filter(FileModel.project_id == project_id).all()
    return files

@router.post("/{project_id}/files/{file_id}/reparse")
def reparse_file(
    project_id: int, 
    file_id: int, 
    parser_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """파일을 다시 파싱합니다."""
    # Check if file exists
    db_file = db.query(FileModel).filter(
        FileModel.id == file_id,
        FileModel.project_id == project_id
    ).first()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = Path(db_file.filepath)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Physical file not found")
    
    try:
        parser = AutoParser()
        
        # Use specific parser if requested
        if parser_name:
            parse_result = parser.parse_with_specific_parser(file_path, parser_name)
        else:
            parse_result = parser.parse(file_path)
        
        # Update database
        if parse_result.success:
            db_file.content = parse_result.text
            db_file.parse_status = "success"
            db_file.parse_error = None
        else:
            db_file.parse_status = "failed"
            db_file.parse_error = parse_result.error_message
        
        db.commit()
        db.refresh(db_file)
        
        return {
            "message": "파일 재파싱 완료",
            "success": parse_result.success,
            "parser_used": parse_result.parser_name,
            "error": parse_result.error_message
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파싱 오류: {str(e)}")

@router.get("/supported-formats")
def get_supported_formats():
    """지원하는 파일 형식 정보를 반환합니다."""
    parser = AutoParser()
    return parser.get_supported_formats()

@router.get("/{project_id}/files/{file_id}/analyze")
def analyze_file(project_id: int, file_id: int, db: Session = Depends(get_db)):
    """파일을 분석하여 상세 정보를 반환합니다."""
    # Check if file exists
    db_file = db.query(FileModel).filter(
        FileModel.id == file_id,
        FileModel.project_id == project_id
    ).first()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = Path(db_file.filepath)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Physical file not found")
    
    try:
        parser = AutoParser()
        analysis = parser.analyze_file(file_path)
        return analysis
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 오류: {str(e)}")

@router.get("/{project_id}/files/{file_id}/content")
def get_file_content(project_id: int, file_id: int, db: Session = Depends(get_db)):
    """파일의 파싱된 텍스트 내용을 반환합니다."""
    # Check if file exists
    db_file = db.query(FileModel).filter(
        FileModel.id == file_id,
        FileModel.project_id == project_id
    ).first()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    return {
        "file_id": file_id,
        "filename": db_file.filename,
        "content": db_file.content,
        "parse_status": db_file.parse_status,
        "parse_error": db_file.parse_error,
        "word_count": len(db_file.content.split()) if db_file.content else 0
    }

@router.delete("/{project_id}/files/{file_id}")
def delete_file(project_id: int, file_id: int, db: Session = Depends(get_db)):
    """프로젝트의 특정 파일을 삭제합니다."""
    # Check if file exists
    db_file = db.query(FileModel).filter(
        FileModel.id == file_id,
        FileModel.project_id == project_id
    ).first()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    filename = db_file.filename
    file_path = Path(db_file.filepath)
    
    # Delete physical file
    try:
        if file_path.exists():
            os.remove(file_path)
    except Exception as e:
        print(f"Warning: Could not delete physical file {file_path}: {str(e)}")
    
    # Delete from database
    db.delete(db_file)
    db.commit()
    
    return {"message": f"File '{filename}' deleted successfully"}

@router.get("/{file_id}/content")
def get_file_content_direct(file_id: int, db: Session = Depends(get_db)):
    """파일의 파싱된 텍스트 내용을 반환합니다 (파일 ID로 직접 접근)."""
    # 파일 정보 조회
    db_file = db.query(FileModel).filter(FileModel.id == file_id).first()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    return {
        "file_id": file_id,
        "filename": db_file.filename,
        "content": db_file.content,
        "parse_status": db_file.parse_status,
        "parse_error": db_file.parse_error,
        "word_count": len(db_file.content.split()) if db_file.content else 0
    }

@router.get("/{file_id}/metadata")
def get_file_metadata(file_id: int, db: Session = Depends(get_db)):
    """프로젝트 컨텍스트에서 파일의 메타데이터를 반환합니다 (메타데이터 스키마 준수)."""
    # 파일 정보 조회
    db_file = db.query(FileModel).filter(FileModel.id == file_id).first()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # 데이터베이스 값을 DocumentMetadata 객체로 변환
    from services.parser.base import DocumentMetadata
    
    metadata = DocumentMetadata(
        # 기본 필드
        title=db_file.filename,
        author=db_file.dc_creator,
        created_date=db_file.dcterms_created,
        modified_date=db_file.dcterms_modified,
        page_count=db_file.doc_page_count,
        word_count=db_file.doc_word_count,
        file_size=getattr(db_file, 'file_size', db_file.size),
        mime_type=db_file.dc_format or db_file.mime_type,
        
        # Dublin Core 필드
        dc_title=db_file.dc_title or db_file.filename,
        dc_creator=db_file.dc_creator,
        dc_subject=db_file.dc_subject,
        dc_description=db_file.dc_description,
        dc_publisher=db_file.dc_publisher,
        dc_contributor=db_file.dc_contributor,
        dc_date=db_file.dc_date,
        dc_type=db_file.dc_type,
        dc_format=db_file.dc_format or db_file.mime_type,
        dc_identifier=db_file.dc_identifier,
        dc_source=db_file.dc_source,
        dc_language=db_file.dc_language,
        dc_relation=db_file.dc_relation,
        dc_coverage=db_file.dc_coverage,
        dc_rights=db_file.dc_rights,
        
        # Dublin Core Terms
        dcterms_created=db_file.dcterms_created,
        dcterms_modified=db_file.dcterms_modified,
        dcterms_extent=db_file.dcterms_extent,
        dcterms_medium=db_file.dcterms_medium,
        dcterms_audience=db_file.dcterms_audience,
        dcterms_accessrights=getattr(db_file, 'dcterms_accessrights', 'public'),
        
        # 파일 정보
        file_name=db_file.filename,
        file_path=db_file.filepath,
        file_extension=Path(db_file.filename).suffix if db_file.filename else None,
        
        # 문서 정보
        doc_page_count=db_file.doc_page_count,
        doc_word_count=db_file.doc_word_count,
        doc_character_count=db_file.doc_character_count,
        doc_type_code=db_file.doc_type_code,
        doc_supported=db_file.doc_supported,
        
        # 처리 정보
        app_version=db_file.app_version,
        parser_name=db_file.parser_name,
        parser_version=db_file.parser_version,
    )
    
    # 스키마 준수 형식으로 변환
    return metadata.to_schema_compliant_dict(file_id=file_id, project_id=db_file.project_id)

@router.get("/{project_id}/files/{file_id}/metadata")
def get_project_file_metadata(project_id: int, file_id: int, db: Session = Depends(get_db)):
    """프로젝트 내 파일의 메타데이터를 반환합니다 (메타데이터 스키마 준수)."""
    # 파일 정보 조회
    db_file = db.query(FileModel).filter(
        FileModel.id == file_id,
        FileModel.project_id == project_id
    ).first()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # 데이터베이스 값을 DocumentMetadata 객체로 변환
    from services.parser.base import DocumentMetadata
    
    metadata = DocumentMetadata(
        # 기본 필드
        title=db_file.filename,
        author=db_file.dc_creator,
        created_date=db_file.dcterms_created,
        modified_date=db_file.dcterms_modified,
        page_count=db_file.doc_page_count,
        word_count=db_file.doc_word_count,
        file_size=getattr(db_file, 'file_size', db_file.size),
        mime_type=db_file.dc_format or db_file.mime_type,
        
        # Dublin Core 필드
        dc_title=db_file.dc_title or db_file.filename,
        dc_creator=db_file.dc_creator,
        dc_subject=db_file.dc_subject,
        dc_description=db_file.dc_description,
        dc_publisher=db_file.dc_publisher,
        dc_contributor=db_file.dc_contributor,
        dc_date=db_file.dc_date,
        dc_type=db_file.dc_type,
        dc_format=db_file.dc_format or db_file.mime_type,
        dc_identifier=db_file.dc_identifier,
        dc_source=db_file.dc_source,
        dc_language=db_file.dc_language,
        dc_relation=db_file.dc_relation,
        dc_coverage=db_file.dc_coverage,
        dc_rights=db_file.dc_rights,
        
        # Dublin Core Terms
        dcterms_created=db_file.dcterms_created,
        dcterms_modified=db_file.dcterms_modified,
        dcterms_extent=db_file.dcterms_extent,
        dcterms_medium=db_file.dcterms_medium,
        dcterms_audience=db_file.dcterms_audience,
        dcterms_accessrights=getattr(db_file, 'dcterms_accessrights', 'public'),
        
        # 파일 정보
        file_name=db_file.filename,
        file_path=db_file.filepath,
        file_extension=Path(db_file.filename).suffix if db_file.filename else None,
        
        # 문서 정보
        doc_page_count=db_file.doc_page_count,
        doc_word_count=db_file.doc_word_count,
        doc_character_count=db_file.doc_character_count,
        doc_type_code=db_file.doc_type_code,
        doc_supported=db_file.doc_supported,
        
        # 처리 정보
        app_version=db_file.app_version,
        parser_name=db_file.parser_name,
        parser_version=db_file.parser_version,
    )
    
    # 스키마 준수 형식으로 변환
    return metadata.to_schema_compliant_dict(file_id=file_id, project_id=project_id)

# 직접 파일 접근용 메타데이터 엔드포인트
@files_router.get("/{file_id}/metadata")
def get_direct_file_metadata(file_id: int, db: Session = Depends(get_db)):
    """파일의 메타데이터를 반환합니다 (직접 접근, 메타데이터 스키마 준수)."""
    # 파일 정보 조회
    db_file = db.query(FileModel).filter(FileModel.id == file_id).first()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # 데이터베이스 값을 DocumentMetadata 객체로 변환
    from services.parser.base import DocumentMetadata
    
    metadata = DocumentMetadata(
        # 기본 필드
        title=db_file.filename,
        author=db_file.dc_creator,
        created_date=db_file.dcterms_created,
        modified_date=db_file.dcterms_modified,
        page_count=db_file.doc_page_count,
        word_count=db_file.doc_word_count,
        file_size=getattr(db_file, 'file_size', db_file.size),
        mime_type=db_file.dc_format or db_file.mime_type,
        
        # Dublin Core 필드
        dc_title=db_file.dc_title or db_file.filename,
        dc_creator=db_file.dc_creator,
        dc_subject=db_file.dc_subject,
        dc_description=db_file.dc_description,
        dc_publisher=db_file.dc_publisher,
        dc_contributor=db_file.dc_contributor,
        dc_date=db_file.dc_date,
        dc_type=db_file.dc_type,
        dc_format=db_file.dc_format or db_file.mime_type,
        dc_identifier=db_file.dc_identifier,
        dc_source=db_file.dc_source,
        dc_language=db_file.dc_language,
        dc_relation=db_file.dc_relation,
        dc_coverage=db_file.dc_coverage,
        dc_rights=db_file.dc_rights,
        
        # Dublin Core Terms
        dcterms_created=db_file.dcterms_created,
        dcterms_modified=db_file.dcterms_modified,
        dcterms_extent=db_file.dcterms_extent,
        dcterms_medium=db_file.dcterms_medium,
        dcterms_audience=db_file.dcterms_audience,
        dcterms_accessrights=getattr(db_file, 'dcterms_accessrights', 'public'),
        
        # 파일 정보
        file_name=db_file.filename,
        file_path=db_file.filepath,
        file_extension=Path(db_file.filename).suffix if db_file.filename else None,
        
        # 문서 정보
        doc_page_count=db_file.doc_page_count,
        doc_word_count=db_file.doc_word_count,
        doc_character_count=db_file.doc_character_count,
        doc_type_code=db_file.doc_type_code,
        doc_supported=db_file.doc_supported,
        
        # 처리 정보
        app_version=db_file.app_version,
        parser_name=db_file.parser_name,
        parser_version=db_file.parser_version,
    )
    
    # 스키마 준수 형식으로 변환
    return metadata.to_schema_compliant_dict(file_id=file_id, project_id=db_file.project_id)

@files_router.get("/{file_id}/download")
def download_direct_file(file_id: int, db: Session = Depends(get_db)):
    """파일을 다운로드합니다 (직접 접근)."""
    from fastapi.responses import FileResponse
    
    # 파일 정보 조회
    db_file = db.query(FileModel).filter(FileModel.id == file_id).first()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = Path(db_file.filepath)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    return FileResponse(
        path=str(file_path),
        filename=db_file.filename,
        media_type=db_file.mime_type or 'application/octet-stream'
    )

@files_router.get("/{file_id}/content")
def get_direct_file_content(file_id: int, db: Session = Depends(get_db)):
    """파일의 내용을 반환합니다 (직접 접근)."""
    # 파일 정보 조회
    db_file = db.query(FileModel).filter(FileModel.id == file_id).first()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    return {
        "file_id": file_id,
        "filename": db_file.filename,
        "content": db_file.content or "",
        "parse_status": db_file.parse_status,
        "parse_error": db_file.parse_error,
        "word_count": len(db_file.content.split()) if db_file.content else 0
    }

@router.get("/{file_id}/download")
def download_file(file_id: int, db: Session = Depends(get_db)):
    """파일을 다운로드합니다."""
    from fastapi.responses import FileResponse
    
    # 파일 정보 조회
    db_file = db.query(FileModel).filter(FileModel.id == file_id).first()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = Path(db_file.filepath)
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    # 파일 타입에 따른 적절한 MIME 타입 설정
    mime_types = {
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.html': 'text/html',
        '.htm': 'text/html',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.webp': 'image/webp'
    }
    
    file_extension = file_path.suffix.lower()
    media_type = mime_types.get(file_extension, 'application/octet-stream')
    
    return FileResponse(
        path=str(file_path),
        filename=db_file.filename,
        media_type=media_type
    )

