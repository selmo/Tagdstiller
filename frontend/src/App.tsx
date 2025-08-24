import React from 'react';
import { useState, useEffect, useRef } from 'react';
import ProjectForm from './components/ProjectForm';
import FileUploader from './components/FileUploader';
import ExtractorTrigger from './components/ExtractorTrigger';
import KeywordResultViewer from './components/KeywordResultViewer';
import SettingsPanel from './components/SettingsPanel';
import KeywordManagement from './components/KeywordManagement';
import GlobalKeywordManagement from './components/GlobalKeywordManagement';
import DocumentViewer from './components/DocumentViewerSimple';
import MetadataViewer from './components/MetadataViewer';
import { configApi, projectApi, fileApi } from './services/api';
import { Project, UploadedFile, ExtractionResponse, Config, GlobalKeywordStatistics, ProjectKeywordStatistics } from './types/api';
import { createComponentLogger } from './utils/logger';

function App() {
  // 로거 초기화
  const logger = createComponentLogger('App');
  
  const [configs, setConfigs] = useState<Config[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [extractionResult, setExtractionResult] = useState<ExtractionResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [newProjectName, setNewProjectName] = useState('');
  // const [keywordStats, setKeywordStats] = useState<KeywordStatisticsResponse | null>(null);
  const [rightPanelView, setRightPanelView] = useState<'project' | 'keywords' | 'project-keywords' | 'settings' | 'metadata'>('project');
  const [extractingFileId, setExtractingFileId] = useState<number | null>(null);
  const [selectedFileIds, setSelectedFileIds] = useState<number[]>([]);
  const [showMultiFileExtraction, setShowMultiFileExtraction] = useState(false);
  const [showFileUploader, setShowFileUploader] = useState(false);
  const [showKeywordExtractor, setShowKeywordExtractor] = useState(false);
  const [showDocumentViewer, setShowDocumentViewer] = useState(false);
  const [metadataFileId, setMetadataFileId] = useState<number | null>(null);
  const [viewerFile, setViewerFile] = useState<UploadedFile | null>(null);
  const [viewerKeywords, setViewerKeywords] = useState<string[]>([]);
  const [viewerTargetPosition, setViewerTargetPosition] = useState<{ page?: number; line?: number; column?: number } | undefined>(undefined);
  const [globalKeywordStats, setGlobalKeywordStats] = useState<GlobalKeywordStatistics | null>(null);
  const [projectKeywordStats, setProjectKeywordStats] = useState<ProjectKeywordStatistics | null>(null);
  const statsTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isMountedRef = useRef(false);
  const [leftSidebarWidth, setLeftSidebarWidth] = useState(300); // 기본 300px
  const [isResizingSidebar, setIsResizingSidebar] = useState(false);

  // 전체 키워드 통계 로드 (효율적인 API 사용)
  const loadGlobalKeywordStats = async () => {
    try {
      logger.debug('전체 키워드 통계 로드 시작', { action: 'load_global_stats_start' });
      const stats = await projectApi.getGlobalStatistics();
      setGlobalKeywordStats(stats);
      logger.info('전체 키워드 통계 로드 완료', { 
        action: 'load_global_stats_success',
        totalKeywords: stats.total_keywords,
        totalOccurrences: stats.total_occurrences,
        totalProjects: stats.total_projects
      });
    } catch (error) {
      logger.error('전체 키워드 통계 로드 실패', error, { action: 'load_global_stats_error' });
      console.error('Failed to load global keyword stats:', error);
    }
  };

  // 프로젝트별 키워드 통계 로드 (효율적인 API 사용)
  const loadProjectKeywordStats = async (projectId: number) => {
    try {
      logger.debug('프로젝트 키워드 통계 로드 시작', { 
        action: 'load_project_stats_start', 
        projectId 
      });
      const stats = await projectApi.getProjectStatistics(projectId);
      setProjectKeywordStats(stats);
      logger.info('프로젝트 키워드 통계 로드 완료', { 
        action: 'load_project_stats_success',
        projectId,
        totalKeywords: stats.total_keywords,
        totalOccurrences: stats.total_occurrences,
        totalFiles: stats.total_files
      });
    } catch (error) {
      logger.error('프로젝트 키워드 통계 로드 실패', error, { 
        action: 'load_project_stats_error', 
        projectId 
      });
      console.error('Failed to load project keyword stats:', error);
    }
  };

  const loadKeywordStatsImmediate = async (projectId?: number) => {
    // 전체 통계는 항상 로드
    if (projects.length > 0) {
      await loadGlobalKeywordStats();
    }
    
    // 선택된 프로젝트가 있으면 프로젝트 통계 로드
    if (projectId) {
      await loadProjectKeywordStats(projectId);
    } else {
      setProjectKeywordStats(null);
    }
  };

  const initializeApp = async () => {
    const startTime = performance.now();
    
    try {
      logger.info('앱 초기화 시작', { action: 'initialize_start' });
      setIsLoading(true);
      
      // 설정 데이터 로드 활성화
      logger.debug('설정 데이터 로드 시작', { action: 'load_configs' });
      const configsData = await configApi.getAll();
      setConfigs(configsData);
      logger.info('설정 데이터 로드 완료', { 
        action: 'load_configs_success', 
        configCount: configsData.length 
      });
      
      // 프로젝트 목록 불러오기
      logger.debug('프로젝트 목록 로드 시작', { action: 'load_projects' });
      const projectsData = await projectApi.getAll();
      setProjects(projectsData);
      logger.info('프로젝트 목록 로드 완료', { 
        action: 'load_projects_success', 
        projectCount: projectsData.length 
      });
      
      // 전체 키워드 통계 로드 (프로젝트가 있을 때만)
      if (projectsData.length > 0) {
        await loadGlobalKeywordStats();
      }
      
      const duration = performance.now() - startTime;
      logger.info('앱 초기화 완료', { 
        action: 'initialize_success', 
        duration: Math.round(duration) 
      });
      
      setError(null);
    } catch (err: any) {
      const duration = performance.now() - startTime;
      const errorMessage = '앱 초기화에 실패했습니다: ' + (err.message || '알 수 없는 오류');
      
      logger.error('앱 초기화 실패', err, { 
        action: 'initialize_error', 
        duration: Math.round(duration),
        errorMessage: err.message 
      });
      
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const loadProjectFiles = async (projectId: number) => {
    try {
      logger.debug('프로젝트 파일 로드 시작', { 
        action: 'load_project_files', 
        projectId 
      });
      
      const filesData = await projectApi.getFiles(projectId);
      setFiles(filesData);
      
      logger.info('프로젝트 파일 로드 완료', { 
        action: 'load_project_files_success', 
        projectId,
        fileCount: filesData.length 
      });
    } catch (err: any) {
      logger.error('파일 목록 로딩 실패', err, { 
        action: 'load_project_files_error', 
        projectId 
      });
      setFiles([]);
    }
  };

  // 디바운싱된 통계 로딩 함수 (300ms 지연)
  const loadKeywordStats = (projectId?: number) => {
    // 기존 타이머 취소
    if (statsTimeoutRef.current) {
      clearTimeout(statsTimeoutRef.current);
    }

    // 새 타이머 설정
    statsTimeoutRef.current = setTimeout(() => {
      loadKeywordStatsImmediate(projectId);
    }, 300);
  };

  useEffect(() => {
    logger.info('앱 컴포넌트 마운트됨', { action: 'mount' });
    isMountedRef.current = true;
    initializeApp();
  }, []); // 빈 의존성 배열로 마운트 시 한 번만 실행

  useEffect(() => {
    if (selectedProject) {
      logger.info('프로젝트 선택됨', { 
        action: 'project_selected', 
        projectId: selectedProject.id, 
        projectName: selectedProject.name 
      });
      loadProjectFiles(selectedProject.id);
    } else {
      logger.info('프로젝트 선택 해제됨', { action: 'project_deselected' });
    }
    // 컴포넌트가 마운트된 후에만 키워드 통계 로드
    if (isMountedRef.current) {
      loadKeywordStats(selectedProject?.id);
    }
  }, [selectedProject]); // selectedProject만 의존성으로 설정

  const handleProjectCreated = (newProject: Project) => {
    logger.info('새 프로젝트 생성됨', { 
      action: 'project_created', 
      projectId: newProject.id, 
      projectName: newProject.name 
    });
    
    setProjects((prev: Project[]) => [...prev, newProject]);
    setSelectedProject(newProject);
    setFiles([]);
    setExtractionResult(null);
  };

  const handleFileUploaded = (newFile: UploadedFile) => {
    logger.info('파일 업로드됨', { 
      action: 'file_uploaded', 
      fileId: newFile.id, 
      filename: newFile.filename,
      size: newFile.size,
      projectId: selectedProject?.id 
    });
    
    setFiles((prev: UploadedFile[]) => [...prev, newFile]);
  };

  const handleExtractionComplete = (result: ExtractionResponse) => {
    logger.info('키워드 추출 완료됨', { 
      action: 'extraction_completed', 
      extractorCount: result.extractors_used.length,
      totalKeywords: result.total_keywords,
      projectId: selectedProject?.id,
      fileId: result.file_id
    });
    
    setExtractionResult(result);
    // 키워드 추출 후 통계 즉시 업데이트 (디바운싱 없이)
    loadKeywordStatsImmediate(selectedProject?.id);
  };

  // 패널 뷰 변경 헬퍼 함수
  const changeRightPanelView = (newView: 'project' | 'keywords' | 'project-keywords' | 'settings' | 'metadata', reason?: string) => {
    if (rightPanelView !== newView) {
      logger.info('패널 뷰 변경', { 
        action: 'panel_view_change', 
        fromView: rightPanelView,
        toView: newView,
        reason,
        projectId: selectedProject?.id 
      });
      setRightPanelView(newView);
    }
  };

  const handleProjectSelect = (project: Project) => {
    // 이미 선택된 프로젝트를 다시 클릭하면 선택 해제
    if (selectedProject?.id === project.id) {
      setSelectedProject(null);
      setFiles([]);
      setExtractionResult(null);
      // setKeywordStats(null);
      setSelectedFileIds([]);
      setShowMultiFileExtraction(false);
      setExtractingFileId(null);
      setShowFileUploader(false);
      setShowKeywordExtractor(false);
      setRightPanelView('project');
    } else {
      // 새로운 프로젝트 선택
      setSelectedProject(project);
      setExtractionResult(null);
      setRightPanelView('project');
      setSelectedFileIds([]);
      setShowMultiFileExtraction(false);
      setExtractingFileId(null);
      setShowFileUploader(false);
      setShowKeywordExtractor(false);
    }
  };

  const handleRenameProject = async (project: Project) => {
    setEditingProject(project);
    setNewProjectName(project.name);
  };

  const handleSaveProjectName = async () => {
    if (!editingProject || !newProjectName.trim()) return;

    try {
      const updatedProject = await projectApi.update(editingProject.id, newProjectName.trim());
      setProjects((prev: Project[]) => prev.map((p: Project) => p.id === updatedProject.id ? updatedProject : p));
      if (selectedProject?.id === updatedProject.id) {
        setSelectedProject(updatedProject);
      }
      setEditingProject(null);
      setNewProjectName('');
    } catch (err: any) {
      alert('프로젝트 이름 변경에 실패했습니다: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleCancelEdit = () => {
    setEditingProject(null);
    setNewProjectName('');
  };

  const handleDeleteProject = async (project: Project) => {
    if (!window.confirm(`정말로 '${project.name}' 프로젝트를 삭제하시겠습니까? 모든 파일이 함께 삭제됩니다.`)) {
      return;
    }

    try {
      await projectApi.delete(project.id);
      setProjects((prev: Project[]) => prev.filter((p: Project) => p.id !== project.id));
      if (selectedProject?.id === project.id) {
        setSelectedProject(null);
        setFiles([]);
        setExtractionResult(null);
      }
    } catch (err: any) {
      alert('프로젝트 삭제에 실패했습니다: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleDeleteFile = async (file: UploadedFile) => {
    if (!window.confirm(`정말로 '${file.filename}' 파일을 삭제하시겠습니까?`)) {
      return;
    }

    try {
      await fileApi.delete(file.project_id, file.id);
      setFiles((prev: UploadedFile[]) => prev.filter((f: UploadedFile) => f.id !== file.id));
    } catch (err: any) {
      alert('파일 삭제에 실패했습니다: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleFileExtraction = (file: UploadedFile) => {
    setExtractingFileId(file.id);
    setShowKeywordExtractor(true);
    // 다른 작업들 숨기기
    setShowFileUploader(false);
    setShowMultiFileExtraction(false);
  };

  const handleFileExtractionComplete = (result: ExtractionResponse) => {
    setExtractionResult(result);
    setExtractingFileId(null);
    setShowKeywordExtractor(false);
    // 키워드 추출 후 통계 즉시 업데이트 (디바운싱 없이)
    loadKeywordStatsImmediate(selectedProject?.id);
  };

  const handleFileSelection = (fileId: number) => {
    setSelectedFileIds(prev => 
      prev.includes(fileId) 
        ? prev.filter(id => id !== fileId)
        : [...prev, fileId]
    );
  };

  const handleSelectAllFiles = () => {
    // 모든 파일을 선택할 수 있도록 변경 (파싱 상태와 무관)
    setSelectedFileIds(
      selectedFileIds.length === files.length 
        ? [] 
        : files.map(f => f.id)
    );
  };

  const handleMultiFileExtraction = () => {
    if (selectedFileIds.length === 0) {
      alert('추출할 파일을 선택해주세요.');
      return;
    }
    setShowMultiFileExtraction(true);
    setRightPanelView('project');
  };

  const handleMultiFileExtractionComplete = (result: ExtractionResponse) => {
    setExtractionResult(result);
    setShowMultiFileExtraction(false);
    setSelectedFileIds([]);
    // 키워드 추출 후 통계 즉시 업데이트 (디바운싱 없이)
    loadKeywordStatsImmediate(selectedProject?.id);
  };

  const handleShowFileUploader = () => {
    setShowFileUploader(true);
    // 다른 작업들 숨기기
    setShowMultiFileExtraction(false);
    setExtractingFileId(null);
    setShowKeywordExtractor(false);
  };

  const handleHideFileUploader = () => {
    setShowFileUploader(false);
  };

  const handleShowKeywordExtractor = () => {
    setShowKeywordExtractor(true);
    // 다른 작업들 숨기기
    setShowFileUploader(false);
    setShowMultiFileExtraction(false);
    setExtractingFileId(null);
  };

  const handleHideKeywordExtractor = () => {
    setShowKeywordExtractor(false);
  };


  const handleDeleteSelectedFiles = async () => {
    if (selectedFileIds.length === 0) {
      alert('삭제할 파일을 선택해주세요.');
      return;
    }

    const selectedFiles = files.filter(file => selectedFileIds.includes(file.id));
    const fileNames = selectedFiles.map(file => file.filename).join(', ');
    
    if (!window.confirm(`정말로 선택된 ${selectedFileIds.length}개 파일을 삭제하시겠습니까?\n\n파일 목록:\n${fileNames}`)) {
      return;
    }

    try {
      // 선택된 파일들을 하나씩 삭제
      for (const fileId of selectedFileIds) {
        const file = files.find(f => f.id === fileId);
        if (file && selectedProject) {
          await fileApi.delete(selectedProject.id, fileId);
        }
      }
      
      // 삭제된 파일들을 파일 목록에서 제거
      setFiles((prev: UploadedFile[]) => prev.filter((f: UploadedFile) => !selectedFileIds.includes(f.id)));
      
      // 선택 상태 초기화
      setSelectedFileIds([]);
      
      alert(`${selectedFileIds.length}개 파일이 성공적으로 삭제되었습니다.`);
    } catch (err: any) {
      alert('파일 삭제에 실패했습니다: ' + (err.response?.data?.detail || err.message));
    }
  };

  const getSelectedFilesInfo = () => {
    const selectedFiles = files.filter(file => selectedFileIds.includes(file.id));
    const totalSize = selectedFiles.reduce((sum, file) => sum + file.size, 0);
    const statusCount = {
      success: selectedFiles.filter(f => f.parse_status === 'success').length,
      failed: selectedFiles.filter(f => f.parse_status === 'failed').length,
      pending: selectedFiles.filter(f => f.parse_status === 'pending').length,
    };
    
    return {
      count: selectedFiles.length,
      totalSize,
      statusCount,
      files: selectedFiles
    };
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <div className="text-gray-600">Tagdstiller 시스템을 초기화하고 있습니다...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="text-red-600 mb-4">⚠️ 오류 발생</div>
          <div className="text-gray-700 mb-4">{error}</div>
          <button
            onClick={initializeApp}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
          >
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <h1 className="text-xl font-semibold text-gray-900">📄 Tagdstiller</h1>
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-500">
                문서 키워드 추출 시스템
              </div>
              <button
                onClick={() => setRightPanelView('settings')}
                className="px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
                title="시스템 설정"
              >
                ⚙️ 설정
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex gap-4">
          {/* 왼쪽 사이드바 */}
          <div className="space-y-6" style={{ width: `${leftSidebarWidth}px`, minWidth: '250px', maxWidth: '500px', flexShrink: 0 }}>
            {/* 프로젝트 생성 */}
            <ProjectForm onProjectCreated={handleProjectCreated} />

            {/* 프로젝트 목록 */}
            {projects.length > 0 && (
              <div className="bg-white p-6 rounded-lg shadow-md">
                <h3 className="text-lg font-semibold mb-4">프로젝트 목록</h3>
                <div className="space-y-2">
                  {projects.map((project: Project) => (
                    <div
                      key={project.id}
                      className={`p-3 rounded-md border transition-colors ${
                        selectedProject?.id === project.id
                          ? 'bg-blue-50 border-blue-200 text-blue-800'
                          : 'bg-gray-50 border-gray-200 hover:bg-gray-100'
                      }`}
                    >
                      {editingProject?.id === project.id ? (
                        <div className="space-y-2">
                          <input
                            type="text"
                            value={newProjectName}
                            onChange={(e) => setNewProjectName(e.target.value)}
                            className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                            placeholder="프로젝트 이름"
                            onKeyPress={(e) => e.key === 'Enter' && handleSaveProjectName()}
                          />
                          <div className="flex space-x-2">
                            <button
                              onClick={handleSaveProjectName}
                              className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
                            >
                              저장
                            </button>
                            <button
                              onClick={handleCancelEdit}
                              className="px-2 py-1 text-xs bg-gray-400 text-white rounded hover:bg-gray-500"
                            >
                              취소
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-center justify-between">
                          <button
                            onClick={() => handleProjectSelect(project)}
                            className="flex-1 text-left"
                            title={selectedProject?.id === project.id ? "클릭하여 선택 해제" : "클릭하여 선택"}
                          >
                            <div className="font-medium">
                              {selectedProject?.id === project.id ? "✓ " : ""}{project.name}
                            </div>
                            <div className="text-xs text-gray-500">
                              {new Date(project.created_at).toLocaleDateString()}
                              {selectedProject?.id === project.id && (
                                <span className="ml-2 text-blue-600">● 선택됨</span>
                              )}
                            </div>
                          </button>
                          <div className="flex space-x-1">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleRenameProject(project);
                              }}
                              className="p-1 text-gray-400 hover:text-blue-600"
                              title="이름 변경"
                            >
                              ✏️
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDeleteProject(project);
                              }}
                              className="p-1 text-gray-400 hover:text-red-600"
                              title="삭제"
                            >
                              🗑️
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 전체 키워드 통계 - 항상 표시 */}
            {projects.length > 0 && (
              <div 
                className={`bg-white p-6 rounded-lg shadow-md cursor-pointer transition-colors ${
                  rightPanelView === 'keywords' ? 'ring-2 ring-blue-500 bg-blue-50' : 'hover:bg-gray-50'
                }`}
                onClick={() => changeRightPanelView(rightPanelView === 'keywords' ? 'project' : 'keywords', 'global_keyword_toggle')}
              >
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="text-lg font-semibold">🌐 전체 키워드 통계</h3>
                  </div>
                  <div className="text-2xl">
                    {rightPanelView === 'keywords' ? '📋' : '🌐'}
                  </div>
                </div>
                {globalKeywordStats ? (
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="bg-blue-50 p-2 rounded">
                      <div className="font-semibold text-blue-800">{globalKeywordStats.total_keywords}</div>
                      <div className="text-blue-600 text-xs">고유 키워드</div>
                    </div>
                    <div className="bg-green-50 p-2 rounded">
                      <div className="font-semibold text-green-800">{globalKeywordStats.total_occurrences}</div>
                      <div className="text-green-600 text-xs">총 발견 횟수</div>
                    </div>
                    <div className="bg-purple-50 p-2 rounded">
                      <div className="font-semibold text-purple-800">{globalKeywordStats.total_projects}</div>
                      <div className="text-purple-600 text-xs">분석 프로젝트</div>
                    </div>
                    <div className="bg-orange-50 p-2 rounded">
                      <div className="font-semibold text-orange-800">{globalKeywordStats.extractors_used.length}</div>
                      <div className="text-orange-600 text-xs">사용 추출기</div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center text-gray-500 py-4">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto mb-2"></div>
                    <div className="text-xs">통계 로딩 중...</div>
                  </div>
                )}
              </div>
            )}

            {/* 프로젝트 키워드 통계 - 프로젝트 선택 시만 표시 */}
            {selectedProject && (
              <div 
                className={`bg-white p-6 rounded-lg shadow-md cursor-pointer transition-colors ${
                  rightPanelView === 'project-keywords' ? 'ring-2 ring-green-500 bg-green-50' : 'hover:bg-green-50'
                }`}
                onClick={() => changeRightPanelView(rightPanelView === 'project-keywords' ? 'project' : 'project-keywords', 'project_keyword_toggle')}
              >
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="text-lg font-semibold">📊 프로젝트 키워드 통계</h3>
                    <p className="text-sm text-gray-600 mt-1">{selectedProject.name}</p>
                  </div>
                  <div className="text-2xl">
                    {rightPanelView === 'project-keywords' ? '📋' : '📊'}
                  </div>
                </div>
                {projectKeywordStats ? (
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="bg-blue-50 p-2 rounded">
                      <div className="font-semibold text-blue-800">{projectKeywordStats.total_keywords}</div>
                      <div className="text-blue-600 text-xs">고유 키워드</div>
                    </div>
                    <div className="bg-green-50 p-2 rounded">
                      <div className="font-semibold text-green-800">{projectKeywordStats.total_occurrences}</div>
                      <div className="text-green-600 text-xs">총 발견 횟수</div>
                    </div>
                    <div className="bg-purple-50 p-2 rounded">
                      <div className="font-semibold text-purple-800">{projectKeywordStats.total_files}</div>
                      <div className="text-purple-600 text-xs">분석 파일</div>
                    </div>
                    <div className="bg-orange-50 p-2 rounded">
                      <div className="font-semibold text-orange-800">{projectKeywordStats.extractors_used.length}</div>
                      <div className="text-orange-600 text-xs">사용 추출기</div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center text-gray-500 py-4">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-600 mx-auto mb-2"></div>
                    <div className="text-xs">통계 로딩 중...</div>
                  </div>
                )}
              </div>
            )}

            {/* 메타데이터 뷰어 - 프로젝트 선택 시만 표시 */}
            {selectedProject && (
              <div 
                className={`bg-white p-6 rounded-lg shadow-md cursor-pointer transition-colors ${
                  rightPanelView === 'metadata' ? 'ring-2 ring-emerald-500 bg-emerald-50' : 'hover:bg-emerald-50'
                }`}
                onClick={() => changeRightPanelView(rightPanelView === 'metadata' ? 'project' : 'metadata', 'metadata_viewer_toggle')}
              >
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="text-lg font-semibold">📋 메타데이터 뷰어</h3>
                    <p className="text-sm text-gray-600 mt-1">문서 구조, 요약, 통계 분석</p>
                  </div>
                  <div className="text-2xl">
                    {rightPanelView === 'metadata' ? '📊' : '📋'}
                  </div>
                </div>
                <div className="text-sm text-gray-600">
                  문서의 메타데이터를 체계적으로 분석하고 확인할 수 있습니다.
                  <div className="mt-2 flex flex-wrap gap-1">
                    <span className="text-xs px-2 py-1 bg-emerald-100 text-emerald-700 rounded">📝 AI 요약</span>
                    <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded">🏗️ 문서구조</span>
                    <span className="text-xs px-2 py-1 bg-purple-100 text-purple-700 rounded">📊 통계정보</span>
                    <span className="text-xs px-2 py-1 bg-orange-100 text-orange-700 rounded">🔗 콘텐츠</span>
                  </div>
                </div>
              </div>
            )}

            {/* 시스템 정보 */}
            <div 
              className={`bg-white p-6 rounded-lg shadow-md cursor-pointer transition-colors ${
                rightPanelView === 'settings' ? 'ring-2 ring-blue-500 bg-blue-50' : 'hover:bg-gray-50'
              }`}
              onClick={() => changeRightPanelView('settings', 'settings_button_click')}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">시스템 정보</h3>
                <span className="text-sm text-gray-500">클릭하여 설정 →</span>
              </div>
              <div className="space-y-2 text-sm">
                <div>설정 항목: {configs.length}개</div>
                <div>프로젝트: {projects.length}개</div>
                {selectedProject && (
                  <div>파일: {files.length}개</div>
                )}
              </div>
            </div>
          </div>

          {/* 리사이저 */}
          <div 
            className="w-1 bg-gray-200 hover:bg-blue-400 cursor-col-resize flex-shrink-0 relative group"
            onMouseDown={(e) => {
              setIsResizingSidebar(true);
              const startX = e.clientX;
              const startWidth = leftSidebarWidth;
              
              const handleMouseMove = (e: MouseEvent) => {
                const newWidth = startWidth + (e.clientX - startX);
                setLeftSidebarWidth(Math.max(250, Math.min(500, newWidth)));
              };
              
              const handleMouseUp = () => {
                setIsResizingSidebar(false);
                document.removeEventListener('mousemove', handleMouseMove);
                document.removeEventListener('mouseup', handleMouseUp);
              };
              
              document.addEventListener('mousemove', handleMouseMove);
              document.addEventListener('mouseup', handleMouseUp);
            }}
          >
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-0.5 h-8 bg-gray-400 group-hover:bg-blue-500 transition-colors" />
            </div>
          </div>

          {/* 메인 콘텐츠 */}
          <div className="flex-1 space-y-6 min-w-0">
            {rightPanelView === 'keywords' ? (
              /* 전체 키워드 통계 뷰 */
              <div className="bg-white rounded-lg shadow-md overflow-hidden">
                <div className="p-6 border-b">
                  <div className="flex items-center justify-between">
                    <h2 className="text-xl font-semibold">🌐 전체 키워드 통계</h2>
                    <button
                      onClick={() => setRightPanelView('project')}
                      className="text-gray-400 hover:text-gray-600 text-2xl"
                    >
                      ×
                    </button>
                  </div>
                </div>
                <div className="p-6">
                  <GlobalKeywordManagement 
                    projects={projects}
                    cachedStats={globalKeywordStats}
                    onViewDocument={(file, keywords) => {
                      setViewerFile(file);
                      // keywords가 문자열 배열인지 확인하고 변환
                      let targetPos: { page?: number; line?: number; column?: number } | undefined = undefined;
                      const keywordStrings = Array.isArray(keywords) 
                        ? keywords.map(k => {
                            if (typeof k === 'string') return k;
                            if (k && typeof k === 'object') {
                              // KeywordOccurrence 객체인 경우 위치 정보 추출
                              if (!targetPos && 'line_number' in k && k.line_number) {
                                targetPos = {
                                  page: k.page_number,
                                  line: k.line_number,
                                  column: k.column_number
                                };
                              }
                              if ('keyword' in k) return k.keyword || '';
                            }
                            return String(k);
                          })
                        : [];
                      setViewerKeywords(keywordStrings);
                      setViewerTargetPosition(targetPos);
                      setShowDocumentViewer(true);
                    }}
                  />
                </div>
              </div>
            ) : rightPanelView === 'project-keywords' && selectedProject ? (
              /* 프로젝트 키워드 관리 뷰 */
              <div className="bg-white rounded-lg shadow-md overflow-hidden">
                <div className="p-6 border-b">
                  <div className="flex items-center justify-between">
                    <h2 className="text-xl font-semibold">📊 {selectedProject.name} 키워드 관리</h2>
                    <button
                      onClick={() => setRightPanelView('project')}
                      className="text-gray-400 hover:text-gray-600 text-2xl"
                    >
                      ×
                    </button>
                  </div>
                </div>
                <div className="p-6">
                  <KeywordManagement 
                    projectId={selectedProject.id} 
                    onClose={() => setRightPanelView('project')}
                    inline={true}
                    onViewDocument={(file, keywords) => {
                      setViewerFile(file);
                      // keywords가 문자열 배열인지 확인하고 변환
                      let targetPos: { page?: number; line?: number; column?: number } | undefined = undefined;
                      const keywordStrings = Array.isArray(keywords) 
                        ? keywords.map(k => {
                            if (typeof k === 'string') return k;
                            if (k && typeof k === 'object') {
                              // KeywordOccurrence 객체인 경우 위치 정보 추출
                              if (!targetPos && 'line_number' in k && k.line_number) {
                                targetPos = {
                                  page: k.page_number,
                                  line: k.line_number,
                                  column: k.column_number
                                };
                              }
                              if ('keyword' in k) return k.keyword || '';
                            }
                            return String(k);
                          })
                        : [];
                      setViewerKeywords(keywordStrings);
                      setViewerTargetPosition(targetPos);
                      setShowDocumentViewer(true);
                    }}
                  />
                </div>
              </div>
            ) : rightPanelView === 'settings' ? (
              /* 설정 관리 뷰 */
              <div className="bg-white rounded-lg shadow-md overflow-hidden">
                <div className="p-6 border-b">
                  <div className="flex items-center justify-between">
                    <h2 className="text-xl font-semibold">시스템 설정</h2>
                    <button
                      onClick={() => setRightPanelView('project')}
                      className="text-gray-400 hover:text-gray-600 text-2xl"
                    >
                      ×
                    </button>
                  </div>
                </div>
                <div className="p-6">
                  <SettingsPanel onClose={() => setRightPanelView('project')} inline={true} />
                </div>
              </div>
            ) : rightPanelView === 'metadata' && selectedProject ? (
              /* 메타데이터 뷰어 */
              <div className="bg-white rounded-lg shadow-md overflow-hidden">
                <MetadataViewer 
                  projectId={selectedProject.id} 
                  fileId={metadataFileId || undefined}
                  onClose={() => setRightPanelView('project')}
                />
              </div>
            ) : selectedProject ? (
              <>
                {/* 선택된 프로젝트 정보 */}
                <div className="bg-white p-6 rounded-lg shadow-md">
                  <div className="flex items-center justify-between mb-2">
                    <h2 className="text-xl font-semibold">{selectedProject.name}</h2>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={handleShowFileUploader}
                        className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 transition-colors"
                      >
                        📁 파일 업로드
                      </button>
                      {files.length > 0 && (
                        <button
                          onClick={handleShowKeywordExtractor}
                          className="px-4 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 transition-colors"
                        >
                          🔍 키워드 추출
                        </button>
                      )}
                    </div>
                  </div>
                  <div className="text-sm text-gray-600">
                    생성일: {new Date(selectedProject.created_at).toLocaleString()}
                  </div>
                  {files.length > 0 && (
                    <div className="mt-4">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-medium">업로드된 파일 ({files.length}개)</h4>
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={handleSelectAllFiles}
                            className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                          >
                            {selectedFileIds.length === files.length ? '전체 해제' : '전체 선택'}
                          </button>
                          {selectedFileIds.length > 0 && (
                            <>
                              <button
                                onClick={handleMultiFileExtraction}
                                className={`text-xs px-2 py-1 rounded transition-colors ${
                                  selectedFileIds.filter(id => files.find(f => f.id === id)?.parse_status === 'success').length === 0
                                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                                    : 'bg-green-100 text-green-700 hover:bg-green-200'
                                }`}
                                disabled={selectedFileIds.filter(id => files.find(f => f.id === id)?.parse_status === 'success').length === 0}
                                title={
                                  selectedFileIds.filter(id => files.find(f => f.id === id)?.parse_status === 'success').length === 0
                                    ? '키워드 추출 가능한 파일이 없습니다 (파싱 완료된 파일만 추출 가능)'
                                    : '선택된 파일들에서 키워드를 추출합니다'
                                }
                              >
                                🔍 키워드 추출 ({selectedFileIds.filter(id => files.find(f => f.id === id)?.parse_status === 'success').length}개)
                              </button>
                              <button
                                onClick={handleDeleteSelectedFiles}
                                className="text-xs px-2 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200"
                              >
                                🗑️ 삭제 ({selectedFileIds.length}개)
                              </button>
                              <button
                                onClick={() => setSelectedFileIds([])}
                                className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                                title="선택 해제"
                              >
                                ✕ 선택 해제
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                      
                      {/* 선택된 파일 정보 */}
                      {selectedFileIds.length > 0 && (
                        <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                          <div className="text-sm font-medium text-blue-800 mb-2">
                            선택된 파일 정보 ({getSelectedFilesInfo().count}개)
                          </div>
                          <div className="grid grid-cols-2 gap-4 text-xs text-blue-700">
                            <div>
                              <span className="font-medium">총 크기:</span> {(getSelectedFilesInfo().totalSize / 1024).toFixed(1)} KB
                            </div>
                            <div>
                              <span className="font-medium">상태:</span> 
                              {getSelectedFilesInfo().statusCount.success > 0 && ` 성공 ${getSelectedFilesInfo().statusCount.success}개`}
                              {getSelectedFilesInfo().statusCount.failed > 0 && ` 실패 ${getSelectedFilesInfo().statusCount.failed}개`}
                              {getSelectedFilesInfo().statusCount.pending > 0 && ` 대기 ${getSelectedFilesInfo().statusCount.pending}개`}
                            </div>
                          </div>
                        </div>
                      )}
                      
                      <div className="space-y-1">
                        {files.map((file: UploadedFile) => (
                          <div key={file.id} className={`text-sm text-gray-600 p-2 rounded transition-colors ${
                            selectedFileIds.includes(file.id) ? 'bg-blue-50 border border-blue-200' : 'bg-gray-50'
                          }`}>
                            <div className="flex items-center justify-between">
                              <div className="flex items-center space-x-2 flex-1">
                                <input
                                  type="checkbox"
                                  checked={selectedFileIds.includes(file.id)}
                                  onChange={() => handleFileSelection(file.id)}
                                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                />
                                <span className="cursor-pointer hover:text-blue-600" onClick={() => {
                                  setViewerFile(file);
                                  setViewerKeywords([]);
                                  setShowDocumentViewer(true);
                                }}>📄 {file.filename} ({(file.size / 1024).toFixed(1)} KB)</span>
                                <span className={`text-xs px-2 py-1 rounded ${
                                  file.parse_status === 'success' 
                                    ? 'bg-green-100 text-green-700' 
                                    : file.parse_status === 'failed'
                                    ? 'bg-red-100 text-red-700'
                                    : 'bg-yellow-100 text-yellow-700'
                                }`}>
                                  {file.parse_status === 'success' ? '파싱완료' : 
                                   file.parse_status === 'failed' ? '파싱실패' : '대기중'}
                                </span>
                              </div>
                              <div className="flex items-center space-x-1">
                                {file.parse_status === 'success' && (
                                  <button
                                    onClick={() => handleFileExtraction(file)}
                                    className="p-1 text-gray-400 hover:text-blue-600"
                                    title="키워드 추출"
                                  >
                                    🔍
                                  </button>
                                )}
                                <button
                                  onClick={() => handleDeleteFile(file)}
                                  className="p-1 text-gray-400 hover:text-red-600"
                                  title="파일 삭제"
                                >
                                  🗑️
                                </button>
                              </div>
                            </div>
                            {file.parse_error && (
                              <div className="text-red-500 text-xs mt-1">{file.parse_error}</div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* 파일 업로드 */}
                {showFileUploader && (
                  <div className="bg-white p-6 rounded-lg shadow-md">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold">파일 업로드</h3>
                      <button
                        onClick={handleHideFileUploader}
                        className="text-gray-400 hover:text-gray-600 text-2xl"
                      >
                        ×
                      </button>
                    </div>
                    <FileUploader 
                      projectId={selectedProject.id} 
                      onFileUploaded={handleFileUploaded}
                      onUploadComplete={() => {
                        // 모든 파일 업로드 완료 후 업로더 자동 숨기기
                        setShowFileUploader(false);
                      }}
                    />
                  </div>
                )}

                {/* 키워드 추출 */}
                {showKeywordExtractor && (
                  <div className="bg-white p-6 rounded-lg shadow-md">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold">
                        키워드 추출
                        {extractingFileId && (
                          <span className="text-sm font-normal text-gray-600 ml-2">
                            - {files.find(f => f.id === extractingFileId)?.filename}
                          </span>
                        )}
                      </h3>
                      <button
                        onClick={handleHideKeywordExtractor}
                        className="text-gray-400 hover:text-gray-600 text-2xl"
                      >
                        ×
                      </button>
                    </div>
                    <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded text-sm text-green-800">
                      {extractingFileId ? (
                        <>🔍 선택한 파일에서 키워드를 추출합니다. 기존 키워드 추출 결과가 있다면 덮어씌워집니다.</>
                      ) : (
                        <>🔍 모든 파일에서 키워드를 추출합니다. 추출 방법을 선택하고 실행하세요.</>
                      )}
                    </div>
                    <ExtractorTrigger
                      projectId={selectedProject.id}
                      fileId={extractingFileId || undefined}
                      onExtractionComplete={extractingFileId ? handleFileExtractionComplete : (result) => {
                        handleExtractionComplete(result);
                        setShowKeywordExtractor(false);
                      }}
                    />
                  </div>
                )}

                {/* 선택된 파일들 키워드 추출 */}
                {showMultiFileExtraction && (
                  <div className="bg-white p-6 rounded-lg shadow-md">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold">
                        선택된 파일 키워드 추출 ({selectedFileIds.length}개 파일)
                      </h3>
                      <button
                        onClick={() => {
                          setShowMultiFileExtraction(false);
                          setSelectedFileIds([]);
                        }}
                        className="text-gray-400 hover:text-gray-600"
                      >
                        ✕ 취소
                      </button>
                    </div>
                    <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded text-sm text-blue-800">
                      📋 선택된 파일들에서 키워드를 추출합니다. 기존 키워드 추출 결과가 있다면 덮어씌워집니다.
                    </div>
                    <div className="mb-4">
                      <h4 className="text-sm font-medium text-gray-700 mb-2">선택된 파일 목록:</h4>
                      <div className="bg-gray-50 p-3 rounded max-h-32 overflow-y-auto">
                        {selectedFileIds.map(fileId => {
                          const file = files.find(f => f.id === fileId);
                          return file ? (
                            <div key={fileId} className="text-sm text-gray-600 mb-1">
                              📄 {file.filename}
                            </div>
                          ) : null;
                        })}
                      </div>
                    </div>
                    <ExtractorTrigger
                      projectId={selectedProject.id}
                      fileIds={selectedFileIds}
                      onExtractionComplete={handleMultiFileExtractionComplete}
                    />
                  </div>
                )}


                {/* 추출 결과 */}
                {extractionResult && (
                  <KeywordResultViewer
                    keywords={extractionResult.keywords}
                    extractorsUsed={extractionResult.extractors_used}
                    totalKeywords={extractionResult.total_keywords}
                    files={files}
                    onViewDocument={(file, keywords) => {
                      setViewerFile(file);
                      // keywords가 문자열 배열인지 확인하고 변환
                      let targetPos: { page?: number; line?: number; column?: number } | undefined = undefined;
                      const keywordStrings = Array.isArray(keywords) 
                        ? keywords.map(k => {
                            if (typeof k === 'string') return k;
                            if (k && typeof k === 'object') {
                              // KeywordOccurrence 객체인 경우 위치 정보 추출
                              if (!targetPos && 'line_number' in k && k.line_number) {
                                targetPos = {
                                  page: k.page_number,
                                  line: k.line_number,
                                  column: k.column_number
                                };
                              }
                              if ('keyword' in k) return k.keyword || '';
                            }
                            return String(k);
                          })
                        : [];
                      setViewerKeywords(keywordStrings);
                      setViewerTargetPosition(targetPos);
                      setShowDocumentViewer(true);
                    }}
                  />
                )}
              </>
            ) : (
              <div className="bg-white p-12 rounded-lg shadow-md text-center">
                <div className="text-gray-400 text-6xl mb-4">📂</div>
                <h2 className="text-xl font-semibold text-gray-900 mb-2">
                  프로젝트를 선택하세요
                </h2>
                <p className="text-gray-600">
                  왼쪽에서 기존 프로젝트를 선택하거나 새 프로젝트를 생성하세요.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 문서 뷰어 */}
      {showDocumentViewer && viewerFile && (
        <DocumentViewer
          file={viewerFile}
          selectedKeywords={viewerKeywords}
          targetPosition={viewerTargetPosition}
          onClose={() => {
            setShowDocumentViewer(false);
            setViewerFile(null);
            setViewerKeywords([]);
            setViewerTargetPosition(undefined);
          }}
        />
      )}
    </div>
  );
}

export default App;