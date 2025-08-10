import React, { useState, useEffect } from 'react';
import { projectApi } from '../services/api';
import { Project, UploadedFile, KeywordOccurrence } from '../types/api';
import KeywordDetailModal from './KeywordDetailModal';

interface GlobalKeywordManagementProps {
  projects: Project[];
  onViewDocument?: (file: UploadedFile, keywords?: string[] | KeywordOccurrence[]) => void;
  cachedStats?: {
    total_keywords: number;
    total_occurrences: number;
    total_projects: number;
    extractors_used: string[];
  } | null;
}

interface GlobalKeywordEntry {
  keyword: string;
  extractor: string;
  totalOccurrences: number;
  projects: {
    project: Project;
    files: {
      file: UploadedFile;
      occurrences: KeywordOccurrence[];
    }[];
  }[];
  categories: string[];
  maxScore: number;
  avgScore: number;
}

const GlobalKeywordManagement: React.FC<GlobalKeywordManagementProps> = ({ 
  projects, 
  onViewDocument,
  cachedStats 
}) => {
  const [view, setView] = useState<'keywords' | 'documents'>('keywords');
  const [displayMode, setDisplayMode] = useState<'list' | 'grid' | 'spreadsheet'>('list');
  const [loading, setLoading] = useState(false);
  const [hasLoadedData, setHasLoadedData] = useState(false);
  const [globalKeywordData, setGlobalKeywordData] = useState<GlobalKeywordEntry[]>([]);
  const [selectedKeyword, setSelectedKeyword] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterExtractor, setFilterExtractor] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'name' | 'count' | 'score' | 'projects'>('score');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [allFiles, setAllFiles] = useState<UploadedFile[]>([]);
  const [keywordsByFile, setKeywordsByFile] = useState<{ [fileId: number]: KeywordOccurrence[] }>({});
  const [selectedFile, setSelectedFile] = useState<UploadedFile | null>(null);
  const [selectedKeywordDetail, setSelectedKeywordDetail] = useState<string | null>(null);

  useEffect(() => {
    // 리스트 모드에서만 상세 데이터를 로드
    if (displayMode === 'list' && !hasLoadedData) {
      loadGlobalKeywordData();
    }
  }, [displayMode, hasLoadedData, projects]);

  const loadGlobalKeywordData = async () => {
    try {
      setLoading(true);
      
      const globalKeywordMap = new Map<string, GlobalKeywordEntry>();
      const allFilesData: UploadedFile[] = [];
      const keywordsData: { [fileId: number]: KeywordOccurrence[] } = {};
      
      // 모든 프로젝트의 키워드 데이터 수집
      for (const project of projects) {
        try {
          // 프로젝트의 파일 목록 가져오기
          const filesData = await projectApi.getFiles(project.id);
          allFilesData.push(...filesData);
          
          // 각 파일의 키워드 가져오기
          for (const file of filesData) {
            try {
              const fileKeywords = await projectApi.getFileKeywords(file.id);
              const keywords = fileKeywords.keywords || [];
              keywordsData[file.id] = keywords;
              
              keywords.forEach((kw: KeywordOccurrence) => {
                // 키워드 정규화
                const normalizedKeyword = kw.keyword.toLowerCase().trim();
                const key = `${normalizedKeyword}::${kw.extractor_name}`;
                
                if (!globalKeywordMap.has(key)) {
                  globalKeywordMap.set(key, {
                    keyword: kw.keyword,
                    extractor: kw.extractor_name,
                    totalOccurrences: 0,
                    projects: [],
                    categories: [],
                    maxScore: 0,
                    avgScore: 0
                  });
                }
                
                const keywordInfo = globalKeywordMap.get(key)!;
                keywordInfo.totalOccurrences++;
                keywordInfo.maxScore = Math.max(keywordInfo.maxScore, kw.score);
                
                // 카테고리 중복 체크
                if (kw.category && !keywordInfo.categories.includes(kw.category)) {
                  keywordInfo.categories.push(kw.category);
                }
                
                // 프로젝트별 그룹화
                let projectEntry = keywordInfo.projects.find(p => p.project.id === project.id);
                if (!projectEntry) {
                  projectEntry = { project, files: [] };
                  keywordInfo.projects.push(projectEntry);
                }
                
                // 파일별 그룹화
                let fileEntry = projectEntry.files.find(f => f.file.id === file.id);
                if (!fileEntry) {
                  fileEntry = { file, occurrences: [] };
                  projectEntry.files.push(fileEntry);
                }
                fileEntry.occurrences.push(kw);
              });
            } catch (error) {
              console.error(`Failed to load keywords for file ${file.id}:`, error);
              keywordsData[file.id] = [];
            }
          }
        } catch (error) {
          console.error(`Failed to load files for project ${project.id}:`, error);
        }
      }
      
      // 평균 점수 계산 및 정렬
      const keywordEntries = Array.from(globalKeywordMap.values()).map(entry => {
        const allScores = entry.projects.flatMap(p => 
          p.files.flatMap(f => f.occurrences.map(occ => occ.score))
        );
        entry.avgScore = allScores.length > 0 ? allScores.reduce((a, b) => a + b, 0) / allScores.length : 0;
        return entry;
      });
      
      setGlobalKeywordData(keywordEntries.sort((a, b) => b.maxScore - a.maxScore));
      setAllFiles(allFilesData);
      setKeywordsByFile(keywordsData);
      setHasLoadedData(true);
      
    } catch (error) {
      console.error('Failed to load global keyword data:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredKeywords = globalKeywordData
    .filter(kw => {
      const matchesSearch = kw.keyword.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesExtractor = filterExtractor === 'all' || kw.extractor === filterExtractor;
      return matchesSearch && matchesExtractor;
    })
    .sort((a, b) => {
      let comparison = 0;
      
      switch (sortBy) {
        case 'name':
          comparison = a.keyword.localeCompare(b.keyword);
          break;
        case 'count':
          comparison = a.totalOccurrences - b.totalOccurrences;
          break;
        case 'score':
          comparison = a.maxScore - b.maxScore;
          break;
        case 'projects':
          comparison = a.projects.length - b.projects.length;
          break;
      }
      
      return sortOrder === 'asc' ? comparison : -comparison;
    });

  const allExtractors = Array.from(new Set(globalKeywordData.map(kw => kw.extractor)));

  const getExtractorColor = (extractor: string): string => {
    const colors: { [key: string]: string } = {
      'keybert': 'bg-blue-100 text-blue-800',
      'spacy_ner': 'bg-purple-100 text-purple-800',
      'llm': 'bg-green-100 text-green-800',
      'konlpy': 'bg-pink-100 text-pink-800'
    };
    return colors[extractor] || 'bg-gray-100 text-gray-800';
  };

  const getCategoryColor = (category: string): string => {
    const colors: { [key: string]: string } = {
      'PERSON': 'bg-indigo-100 text-indigo-800',
      'ORG': 'bg-teal-100 text-teal-800',
      'LOC': 'bg-emerald-100 text-emerald-800',
      'technology': 'bg-cyan-100 text-cyan-800',
      'noun': 'bg-violet-100 text-violet-800'
    };
    return colors[category] || 'bg-gray-100 text-gray-800';
  };

  // 초기 로딩 상태 제거 - 캐시된 통계를 즉시 표시

  return (
    <div className="space-y-6">
      {/* 전체 통계 요약 - 캐시된 데이터 사용 */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-6 rounded-lg border">
        <h2 className="text-xl font-semibold mb-4 text-blue-900">🌐 전체 키워드 통계</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {cachedStats?.total_keywords || globalKeywordData.length}
            </div>
            <div className="text-sm text-gray-600">고유 키워드</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {cachedStats?.total_occurrences || globalKeywordData.reduce((sum, kw) => sum + kw.totalOccurrences, 0)}
            </div>
            <div className="text-sm text-gray-600">총 발견 횟수</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">
              {cachedStats?.total_projects || projects.length}
            </div>
            <div className="text-sm text-gray-600">분석된 프로젝트</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">
              {cachedStats?.extractors_used?.length || allExtractors.length}
            </div>
            <div className="text-sm text-gray-600">사용된 추출기</div>
          </div>
        </div>
      </div>

      {/* 뷰 타입 및 표시 모드 선택 */}
      <div className="flex flex-col space-y-3">
        {/* 뷰 타입 선택 (키워드 중심 vs 문서 중심) */}
        <div className="flex bg-gray-100 rounded-lg p-1">
          <button
            onClick={() => setView('keywords')}
            className={`px-4 py-2 rounded ${view === 'keywords' ? 'bg-white shadow' : 'text-gray-600'}`}
          >
            키워드 중심
          </button>
          <button
            onClick={() => setView('documents')}
            className={`px-4 py-2 rounded ${view === 'documents' ? 'bg-white shadow' : 'text-gray-600'}`}
          >
            문서 중심
          </button>
        </div>
        
        {/* 표시 모드 선택 (리스트, 그리드, 스프레드시트) */}
        <div className="flex bg-blue-50 rounded-lg p-1">
          <button
            onClick={() => setDisplayMode('list')}
            className={`px-3 py-2 text-sm rounded ${displayMode === 'list' ? 'bg-white shadow text-blue-700' : 'text-blue-600 hover:text-blue-800'}`}
            title="리스트 뷰"
          >
            📋 리스트
          </button>
          <button
            onClick={() => setDisplayMode('grid')}
            className={`px-3 py-2 text-sm rounded ${displayMode === 'grid' ? 'bg-white shadow text-blue-700' : 'text-blue-600 hover:text-blue-800'}`}
            title="그리드 뷰"
          >
            📊 그리드
          </button>
          <button
            onClick={() => setDisplayMode('spreadsheet')}
            className={`px-3 py-2 text-sm rounded ${displayMode === 'spreadsheet' ? 'bg-white shadow text-blue-700' : 'text-blue-600 hover:text-blue-800'}`}
            title="스프레드시트 뷰"
          >
            📈 스프레드시트
          </button>
        </div>
      </div>

      {/* 검색 및 필터 */}
      <div className="bg-white p-6 rounded-lg shadow-md">
        <div className="flex items-center space-x-4 mb-4">
          <input
            type="text"
            placeholder="키워드 검색..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="flex-1 px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <select
            value={filterExtractor}
            onChange={(e) => setFilterExtractor(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">모든 추출기</option>
            {allExtractors.map(extractor => (
              <option key={extractor} value={extractor}>{extractor}</option>
            ))}
          </select>
        </div>
        
        <div className="flex items-center space-x-4 mb-4">
          <span className="text-sm text-gray-600">정렬:</span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as 'name' | 'count' | 'score' | 'projects')}
            className="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="score">점수</option>
            <option value="count">빈도</option>
            <option value="projects">프로젝트 수</option>
            <option value="name">이름</option>
          </select>
          <button
            onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
            className="px-3 py-2 border border-gray-300 rounded hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
            title={`현재: ${sortOrder === 'asc' ? '오름차순' : '내림차순'}`}
          >
            {sortOrder === 'asc' ? '↑' : '↓'}
          </button>
        </div>
        
        <div className="text-sm text-gray-600">
          총 {filteredKeywords.length}개 키워드 발견
        </div>
      </div>

      {/* 메인 콘텐츠 */}
      <div className="overflow-y-auto max-h-[60vh]">
        {displayMode === 'grid' ? (
          <div className="text-center py-8">
            <div className="text-gray-500 mb-4">🔧 그리드 뷰</div>
            <div className="text-sm text-gray-600">전체 키워드 그리드 뷰는 개발 중입니다.</div>
            <div className="text-xs text-gray-500 mt-2">리스트 뷰를 이용해주세요.</div>
          </div>
        ) : displayMode === 'spreadsheet' ? (
          <div className="text-center py-8">
            <div className="text-gray-500 mb-4">📊 스프레드시트 뷰</div>
            <div className="text-sm text-gray-600">전체 키워드 스프레드시트 뷰는 개발 중입니다.</div>
            <div className="text-xs text-gray-500 mt-2">리스트 뷰를 이용해주세요.</div>
          </div>
        ) : loading ? (
          <div className="flex items-center justify-center p-8">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <div>상세 키워드 데이터를 로드하는 중...</div>
            </div>
          </div>
        ) : view === 'keywords' ? (
          /* 키워드 중심 리스트 뷰 */
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 키워드 목록 */}
            <div className="space-y-3">
              <h3 className="font-semibold">키워드 목록</h3>
              <div className="max-h-96 overflow-y-auto space-y-2">
                {filteredKeywords.map((kw, index) => (
                  <div
                    key={index}
                    onClick={() => setSelectedKeyword(kw.keyword)}
                    className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                      selectedKeyword === kw.keyword ? 'bg-blue-50 border-blue-200' : 'hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        <span className="font-medium">{kw.keyword}</span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedKeywordDetail(kw.keyword);
                          }}
                          className="text-xs text-blue-600 hover:text-blue-800 px-1"
                          title="키워드 상세 정보"
                        >
                          🔍
                        </button>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm text-gray-500">{kw.totalOccurrences}회</span>
                        <span className="text-xs text-gray-400">{kw.projects.length}개 프로젝트</span>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2 mb-2">
                      <span className={`text-xs px-2 py-1 rounded ${getExtractorColor(kw.extractor)}`}>
                        {kw.extractor}
                      </span>
                      <span className="text-xs px-2 py-1 bg-green-100 text-green-800 rounded">
                        최고 {(kw.maxScore * 100).toFixed(1)}%
                      </span>
                      <span className="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded">
                        평균 {(kw.avgScore * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex items-center space-x-1">
                      {kw.categories.map(category => (
                        <span key={category} className={`text-xs px-2 py-1 rounded ${getCategoryColor(category)}`}>
                          {category}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 선택된 키워드 상세 정보 */}
            <div>
              <h3 className="font-semibold mb-3">키워드 상세 정보</h3>
              {selectedKeyword ? (
                <div className="border rounded-lg p-4">
                  {(() => {
                    const keywordEntry = globalKeywordData.find(kw => kw.keyword === selectedKeyword);
                    if (!keywordEntry) return null;
                    
                    return (
                      <>
                        <h4 className="text-lg font-medium mb-3">{selectedKeyword}</h4>
                        
                        {/* 키워드 요약 정보 */}
                        <div className="bg-blue-50 p-3 rounded-lg mb-4">
                          <div className="grid grid-cols-2 gap-4 text-sm mb-3">
                            <div>
                              <span className="text-gray-600">총 발견 횟수:</span>
                              <span className="font-medium ml-2">{keywordEntry.totalOccurrences}회</span>
                            </div>
                            <div>
                              <span className="text-gray-600">최고 점수:</span>
                              <span className="font-medium ml-2">{(keywordEntry.maxScore * 100).toFixed(1)}%</span>
                            </div>
                            <div>
                              <span className="text-gray-600">발견 프로젝트:</span>
                              <span className="font-medium ml-2">{keywordEntry.projects.length}개</span>
                            </div>
                            <div>
                              <span className="text-gray-600">평균 점수:</span>
                              <span className="font-medium ml-2">{(keywordEntry.avgScore * 100).toFixed(1)}%</span>
                            </div>
                          </div>
                          <div className="flex items-center space-x-2 mb-2">
                            <span className={`text-xs px-2 py-1 rounded ${getExtractorColor(keywordEntry.extractor)}`}>
                              {keywordEntry.extractor}
                            </span>
                            {keywordEntry.categories.map(category => (
                              <span key={category} className={`text-xs px-2 py-1 rounded ${getCategoryColor(category)}`}>
                                {category}
                              </span>
                            ))}
                          </div>
                        </div>
                        
                        {/* 프로젝트별 상세 정보 */}
                        <div className="space-y-3">
                          <h5 className="text-sm font-medium text-gray-700">프로젝트별 상세 정보</h5>
                          <div className="max-h-64 overflow-y-auto space-y-2">
                            {keywordEntry.projects.map((projectEntry, idx) => (
                              <div key={idx} className="bg-gray-50 p-3 rounded">
                                <div className="font-medium text-sm mb-2">
                                  📁 {projectEntry.project.name}
                                </div>
                                <div className="space-y-1">
                                  {projectEntry.files.map((fileEntry, fileIdx) => (
                                    <div key={fileIdx} className="text-xs">
                                      <div className="flex items-center justify-between">
                                        <span className="text-gray-700">📄 {fileEntry.file.filename}</span>
                                        <span className="text-gray-500">
                                          {fileEntry.occurrences.length}회 발견
                                        </span>
                                      </div>
                                      {/* 뷰어에서 보기 버튼 */}
                                      {onViewDocument && (
                                        <div className="mt-1">
                                          <button
                                            onClick={(e) => {
                                              e.stopPropagation();
                                              onViewDocument(fileEntry.file, [selectedKeyword]);
                                            }}
                                            className="w-full px-2 py-1 text-xs bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100 transition-colors"
                                          >
                                            📄 뷰어에서 보기
                                          </button>
                                        </div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </>
                    );
                  })()}
                </div>
              ) : (
                <div className="border rounded-lg p-4 text-center text-gray-500">
                  키워드를 선택하여 상세 정보를 확인하세요
                </div>
              )}
            </div>
          </div>
        ) : (
          /* 문서 중심 리스트 뷰 */
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 문서 목록 */}
            <div className="space-y-3">
              <h3 className="font-semibold">문서 목록</h3>
              <div className="max-h-96 overflow-y-auto space-y-2">
                {allFiles.map((file) => {
                  const fileKeywords = keywordsByFile[file.id] || [];
                  const extractors = Array.from(new Set(fileKeywords.map(kw => kw.extractor_name)));
                  
                  return (
                    <div
                      key={file.id}
                      onClick={() => setSelectedFile(file)}
                      className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                        selectedFile?.id === file.id ? 'bg-blue-50 border-blue-200' : 'hover:bg-gray-50'
                      }`}
                    >
                      <div className="font-medium mb-1">{file.filename}</div>
                      <div className="text-sm text-gray-600 mb-2">
                        {fileKeywords.length}개 키워드 추출됨
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-1">
                          {extractors.map(extractor => (
                            <span key={extractor} className={`text-xs px-2 py-1 rounded ${getExtractorColor(extractor)}`}>
                              {extractor}
                            </span>
                          ))}
                        </div>
                        {/* 뷰어에서 보기 버튼 */}
                        {onViewDocument && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              const uniqueKeywords = Array.from(new Set(fileKeywords.map(kw => kw.keyword)));
                              onViewDocument(file, uniqueKeywords);
                            }}
                            className="px-2 py-1 text-xs bg-white border border-blue-200 text-blue-700 rounded hover:bg-blue-50 transition-colors"
                          >
                            📄 보기
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 선택된 문서의 키워드 */}
            <div>
              <h3 className="font-semibold mb-3">문서 키워드</h3>
              {selectedFile ? (
                <div className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-lg font-medium">{selectedFile.filename}</h4>
                    {/* 뷰어에서 보기 버튼 */}
                    {onViewDocument && (
                      <button
                        onClick={() => {
                          const fileKeywords = keywordsByFile[selectedFile.id] || [];
                          const uniqueKeywords = Array.from(new Set(fileKeywords.map(kw => kw.keyword)));
                          onViewDocument(selectedFile, uniqueKeywords);
                        }}
                        className="px-3 py-2 text-sm bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100 transition-colors"
                      >
                        📄 뷰어에서 보기
                      </button>
                    )}
                  </div>
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {(keywordsByFile[selectedFile.id] || []).map((kw, index) => (
                      <div key={index} className="bg-gray-50 p-3 rounded">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center space-x-2">
                            <span className="font-medium">{kw.keyword}</span>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedKeywordDetail(kw.keyword);
                              }}
                              className="text-xs text-blue-600 hover:text-blue-800 px-1"
                              title="키워드 상세 정보"
                            >
                              🔍
                            </button>
                          </div>
                          <span className="text-xs px-2 py-1 bg-green-100 text-green-800 rounded">
                            {(kw.score * 100).toFixed(1)}%
                          </span>
                        </div>
                        <div className="flex items-center space-x-2 mb-2">
                          <span className={`text-xs px-2 py-1 rounded ${getExtractorColor(kw.extractor_name)}`}>
                            {kw.extractor_name}
                          </span>
                          {kw.category && (
                            <span className={`text-xs px-2 py-1 rounded ${getCategoryColor(kw.category)}`}>
                              {kw.category}
                            </span>
                          )}
                          {kw.start_position !== null && (
                            <span className="text-xs text-gray-600">
                              위치: {kw.start_position}-{kw.end_position}
                            </span>
                          )}
                        </div>
                        {kw.context_snippet && (
                          <div className="text-sm text-gray-600 italic">
                            "{kw.context_snippet}"
                          </div>
                        )}
                      </div>
                    ))}
                    {(!keywordsByFile[selectedFile.id] || keywordsByFile[selectedFile.id].length === 0) && (
                      <div className="text-center text-gray-500 py-4">
                        이 문서에서 추출된 키워드가 없습니다
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="border rounded-lg p-4 text-center text-gray-500">
                  문서를 선택하여 키워드를 확인하세요
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 키워드 상세 정보 모달 */}
      {selectedKeywordDetail && (
        <KeywordDetailModal
          keyword={selectedKeywordDetail}
          occurrences={Object.values(keywordsByFile).flat().filter(k => k.keyword === selectedKeywordDetail)}
          files={allFiles}
          onViewDocument={onViewDocument}
          onClose={() => setSelectedKeywordDetail(null)}
        />
      )}
    </div>
  );
};

export default GlobalKeywordManagement;