import React, { useState, useEffect } from 'react';
import { projectApi } from '../services/api';
import { UploadedFile, KeywordOccurrence } from '../types/api';
import KeywordGridViewer from './KeywordGridViewer';
import KeywordSpreadsheetViewer from './KeywordSpreadsheetViewer';
import KeywordDetailModal from './KeywordDetailModal';

interface KeywordManagementProps {
  projectId: number;
  onClose: () => void;
  inline?: boolean;
  onViewDocument?: (file: UploadedFile, keywords?: string[] | KeywordOccurrence[]) => void;
}

interface KeywordExtractorEntry {
  keyword: string;
  extractor: string;
  totalOccurrences: number;
  files: {
    file: UploadedFile;
    occurrences: KeywordOccurrence[];
  }[];
  categories: string[];
  maxScore: number;
  avgScore: number;
}

interface UnifiedKeywordEntry {
  keyword: string;
  totalOccurrences: number;
  extractors: {
    name: string;
    occurrences: number;
    maxScore: number;
    categories: string[];
  }[];
  allCategories: string[];
  maxScore: number;
  avgScore: number;
  files: {
    file: UploadedFile;
    occurrences: KeywordOccurrence[];
  }[];
}

// 한국어 조사 제거 함수 (백엔드 로직과 동일)
const normalizeKeyword = (keyword: string): string => {
  if (!keyword) return "";
  
  const text = keyword.trim();
  
  // 한국어가 아닌 경우 그대로 반환
  if (!/[가-힣]/.test(text)) {
    return text;
  }
  
  // 조사 패턴 정의 (최소 2글자 어근 보장)
  const particlePatterns = [
    // 관형격조사 (최우선)
    /^(.{2,})의$/,      // ~의 (가장 중요!)
    
    // 복합조사 (긴 것부터)
    /^(.{2,})에서의$/,  // ~에서의
    /^(.{2,})으로는$/,  // ~으로는
    /^(.{2,})로는$/,    // ~로는
    /^(.{2,})에서는$/,  // ~에서는
    /^(.{2,})으로도$/,  // ~으로도
    /^(.{2,})로도$/,    // ~로도
    /^(.{2,})와도$/,    // ~와도
    /^(.{2,})과도$/,    // ~과도
    /^(.{2,})에는$/,    // ~에는
    /^(.{2,})에도$/,    // ~에도
    /^(.{2,})까지$/,    // ~까지
    /^(.{2,})부터$/,    // ~부터
    /^(.{2,})보다$/,    // ~보다
    /^(.{2,})처럼$/,    // ~처럼
    /^(.{2,})같이$/,    // ~같이
    /^(.{2,})하고$/,    // ~하고
    /^(.{2,})한테$/,    // ~한테
    /^(.{2,})에게$/,    // ~에게
    
    // 주격조사
    /^(.{2,})이$/,      // ~이
    /^(.{2,})가$/,      // ~가
    /^(.{2,})께서$/,    // ~께서
    
    // 목적격조사
    /^(.{2,})을$/,      // ~을
    /^(.{2,})를$/,      // ~를
    
    // 부사격조사
    /^(.{2,})에서$/,    // ~에서
    /^(.{2,})으로$/,    // ~으로
    /^(.{2,})로$/,      // ~로
    /^(.{2,})와$/,      // ~와
    /^(.{2,})과$/,      // ~과
    /^(.{2,})랑$/,      // ~랑
    /^(.{2,})께$/,      // ~께
    /^(.{2,})에$/,      // ~에
    /^(.{2,})도$/,      // ~도
    /^(.{2,})만$/,      // ~만
    
    // 서술격조사
    /^(.{2,})이다$/,    // ~이다
    /^(.{2,})다$/,      // ~다
    
    // 종결어미 (일부)
    /^(.{2,})은$/,      // ~은
    /^(.{2,})는$/,      // ~는 (보조사)
  ];
  
  // 각 조사 패턴을 확인하여 제거
  for (const pattern of particlePatterns) {
    const match = text.match(pattern);
    if (match && match[1]) {
      console.debug(`한국어 조사 제거: '${text}' -> '${match[1]}'`);
      return match[1];
    }
  }
  
  return text;
};

const KeywordManagement: React.FC<KeywordManagementProps> = ({ projectId, onClose, inline = false, onViewDocument }) => {
  const [view, setView] = useState<'keywords' | 'documents'>('keywords');
  const [displayMode, setDisplayMode] = useState<'list' | 'grid' | 'spreadsheet'>('list');
  const [loading, setLoading] = useState(true);
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [keywordsByFile, setKeywordsByFile] = useState<{ [fileId: number]: KeywordOccurrence[] }>({});
  const [keywordData, setKeywordData] = useState<KeywordExtractorEntry[]>([]);
  const [unifiedKeywordData, setUnifiedKeywordData] = useState<UnifiedKeywordEntry[]>([]);
  const [selectedKeyword, setSelectedKeyword] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<UploadedFile | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterExtractor, setFilterExtractor] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'name' | 'count' | 'score'>('score');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [selectedKeywordDetail, setSelectedKeywordDetail] = useState<string | null>(null);
  const [keywordListHeight, setKeywordListHeight] = useState(576); // 기본 576px (h-96의 1.5배)
  const [keywordDetailHeight, setKeywordDetailHeight] = useState(576); // 기본 576px
  const [isResizingList, setIsResizingList] = useState(false);
  const [isResizingDetail, setIsResizingDetail] = useState(false);

  useEffect(() => {
    loadData();
  }, [projectId]);

  const loadData = async () => {
    try {
      setLoading(true);
      
      // 프로젝트의 파일 목록 가져오기
      const filesData = await projectApi.getFiles(projectId);
      setFiles(filesData);
      
      // 각 파일의 키워드 가져오기
      const keywordsData: { [fileId: number]: KeywordOccurrence[] } = {};
      for (const file of filesData) {
        try {
          const fileKeywords = await projectApi.getFileKeywords(file.id);
          keywordsData[file.id] = fileKeywords.keywords || [];
        } catch (error) {
          console.error(`Failed to load keywords for file ${file.id}:`, error);
          keywordsData[file.id] = [];
        }
      }
      
      setKeywordsByFile(keywordsData);
      
      // 키워드-추출기 조합별 데이터 생성
      const keywordExtractorMap = new Map<string, KeywordExtractorEntry>();
      
      Object.entries(keywordsData).forEach(([fileIdStr, keywords]) => {
        const fileId = parseInt(fileIdStr);
        const file = filesData.find(f => f.id === fileId);
        if (!file) return;
        
        keywords.forEach(kw => {
          // 키워드 정규화: 한국어 조사 제거, 소문자 변환, 공백 정리
          const normalizedKeyword = normalizeKeyword(kw.keyword).toLowerCase().trim();
          const key = `${normalizedKeyword}::${kw.extractor_name}`;
          
          if (!keywordExtractorMap.has(key)) {
            keywordExtractorMap.set(key, {
              keyword: kw.keyword, // 원본 키워드 유지
              extractor: kw.extractor_name,
              totalOccurrences: 0,
              files: [],
              categories: [],
              maxScore: 0,
              avgScore: 0
            });
          }
          
          const keywordInfo = keywordExtractorMap.get(key)!;
          keywordInfo.totalOccurrences++;
          keywordInfo.maxScore = Math.max(keywordInfo.maxScore, kw.score);
          
          // 카테고리 중복 체크
          if (kw.category && !keywordInfo.categories.includes(kw.category)) {
            keywordInfo.categories.push(kw.category);
          }
          
          // 파일별 그룹화 (해당 추출기의 결과만)
          let fileEntry = keywordInfo.files.find(f => f.file.id === fileId);
          if (!fileEntry) {
            fileEntry = { file, occurrences: [] };
            keywordInfo.files.push(fileEntry);
          }
          fileEntry.occurrences.push(kw);
        });
      });
      
      // 평균 점수 계산 및 정렬
      const keywordEntries = Array.from(keywordExtractorMap.values()).map(entry => {
        const allScores = entry.files.flatMap(f => f.occurrences.map(occ => occ.score));
        entry.avgScore = allScores.length > 0 ? allScores.reduce((a, b) => a + b, 0) / allScores.length : 0;
        return entry;
      });
      
      setKeywordData(keywordEntries.sort((a, b) => b.maxScore - a.maxScore));
      
      // 키워드별로 통합된 데이터 생성
      const unifiedMap = new Map<string, UnifiedKeywordEntry>();
      
      keywordEntries.forEach(entry => {
        const normalizedKeyword = normalizeKeyword(entry.keyword).toLowerCase().trim();
        
        if (!unifiedMap.has(normalizedKeyword)) {
          unifiedMap.set(normalizedKeyword, {
            keyword: normalizeKeyword(entry.keyword), // 정규화된 키워드 사용
            totalOccurrences: 0,
            extractors: [],
            allCategories: [],
            maxScore: 0,
            avgScore: 0,
            files: []
          });
        }
        
        const unified = unifiedMap.get(normalizedKeyword)!;
        
        // 추출기 정보 추가
        unified.extractors.push({
          name: entry.extractor,
          occurrences: entry.totalOccurrences,
          maxScore: entry.maxScore,
          categories: entry.categories
        });
        
        // 전체 통계 업데이트
        unified.totalOccurrences += entry.totalOccurrences;
        unified.maxScore = Math.max(unified.maxScore, entry.maxScore);
        
        // 카테고리 통합 (중복 제거)
        entry.categories.forEach(cat => {
          if (!unified.allCategories.includes(cat)) {
            unified.allCategories.push(cat);
          }
        });
        
        // 파일 정보 통합
        entry.files.forEach(fileEntry => {
          const existingFile = unified.files.find(f => f.file.id === fileEntry.file.id);
          if (existingFile) {
            existingFile.occurrences.push(...fileEntry.occurrences);
          } else {
            unified.files.push({
              file: fileEntry.file,
              occurrences: [...fileEntry.occurrences]
            });
          }
        });
      });
      
      // 평균 점수 재계산
      const unifiedEntries = Array.from(unifiedMap.values()).map(entry => {
        const allScores = entry.files.flatMap(f => f.occurrences.map(occ => occ.score));
        entry.avgScore = allScores.length > 0 ? allScores.reduce((a, b) => a + b, 0) / allScores.length : 0;
        
        // 추출기별로 정렬 (점수 높은 순)
        entry.extractors.sort((a, b) => b.maxScore - a.maxScore);
        
        return entry;
      });
      
      setUnifiedKeywordData(unifiedEntries.sort((a, b) => b.maxScore - a.maxScore));
      
    } catch (error) {
      console.error('Failed to load keyword data:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredUnifiedKeywords = unifiedKeywordData
    .filter(kw => {
      const matchesSearch = kw.keyword.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesExtractor = filterExtractor === 'all' || kw.extractors.some(e => e.name === filterExtractor);
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
      }
      
      return sortOrder === 'asc' ? comparison : -comparison;
    });

  const allExtractors = Array.from(new Set(keywordData.map(kw => kw.extractor)));

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

  if (loading) {
    return (
      <div className={inline ? "flex items-center justify-center p-8" : "fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"}>
        <div className={inline ? "text-center" : "bg-white p-6 rounded-lg"}>
          <div className="text-center">키워드 데이터를 로드하는 중...</div>
        </div>
      </div>
    );
  }

  const content = (
    <>
      <div className={`mb-6 ${inline ? 'space-y-4' : ''}`}>
        {!inline && (
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">키워드 관리</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl"
            >
              ×
            </button>
          </div>
        )}
        
        <div className={`flex ${inline ? 'flex-col space-y-3' : 'items-center justify-between'}`}>
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
      </div>

      <div className="flex-1 overflow-hidden flex flex-col">
          {displayMode === 'grid' ? (
            <KeywordGridViewer 
              projectId={projectId}
              onClose={inline ? undefined : onClose}
            />
          ) : displayMode === 'spreadsheet' ? (
            <KeywordSpreadsheetViewer 
              projectId={projectId}
              viewType={view}
              onClose={inline ? undefined : onClose}
            />
          ) : view === 'keywords' ? (
            <>
              {/* 키워드 중심 리스트 뷰 */}
              <div className="mb-3 flex-shrink-0">
                <div className="flex items-center space-x-3 mb-2">
                  <input
                    type="text"
                    placeholder="키워드 검색..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="flex-1 px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <select
                    value={filterExtractor}
                    onChange={(e) => setFilterExtractor(e.target.value)}
                    className="px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="all">모든 추출기</option>
                    {allExtractors.map(extractor => (
                      <option key={extractor} value={extractor}>{extractor}</option>
                    ))}
                  </select>
                </div>
                
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm text-gray-600">정렬:</span>
                    <select
                      value={sortBy}
                      onChange={(e) => setSortBy(e.target.value as 'name' | 'count' | 'score')}
                      className="px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="score">점수</option>
                      <option value="count">빈도</option>
                      <option value="name">이름</option>
                    </select>
                    <button
                      onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                      className="px-2 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      title={`현재: ${sortOrder === 'asc' ? '오름차순' : '내림차순'}`}
                    >
                      {sortOrder === 'asc' ? '↑' : '↓'}
                    </button>
                  </div>
                  <div className="text-sm text-gray-600">
                    {filteredUnifiedKeywords.length}개 키워드
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
                {/* 키워드 목록 */}
                <div className="lg:col-span-2 flex flex-col">
                  <h3 className="font-semibold mb-2">키워드 목록</h3>
                  <div 
                    className="overflow-y-auto space-y-1 pr-2 border border-gray-200 rounded-lg p-2 relative"
                    style={{ height: `${keywordListHeight}px` }}
                  >
                    {filteredUnifiedKeywords.map((kw: UnifiedKeywordEntry, index: number) => (
                      <div
                        key={index}
                        onClick={() => setSelectedKeyword(kw.keyword)}
                        className={`px-3 py-3 border rounded cursor-pointer transition-colors ${
                          selectedKeyword === kw.keyword ? 'bg-blue-50 border-blue-300' : 'hover:bg-gray-50'
                        }`}
                      >
                        <div className="flex flex-col space-y-2">
                          {/* 키워드 강조 */}
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-gray-900 text-base truncate pr-2">{kw.keyword}</span>
                            <span className="text-sm text-gray-600 flex-shrink-0">{kw.totalOccurrences}회</span>
                          </div>
                          
                          {/* 통계 정보 */}
                          <div className="space-y-1">
                            <div className="flex flex-wrap gap-1">
                              {kw.extractors.map((ext, idx) => (
                                <span key={idx} className={`px-1.5 py-0.5 rounded text-xs ${getExtractorColor(ext.name)}`}>
                                  {ext.name}
                                </span>
                              ))}
                            </div>
                            <div className="flex items-center justify-between text-xs">
                              <span className="text-gray-600">점수: 최고 {(kw.maxScore * 100).toFixed(0)}% / 평균 {(kw.avgScore * 100).toFixed(0)}%</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  {/* 키워드 목록 리사이저 */}
                  <div 
                    className="h-1 bg-gray-200 hover:bg-blue-400 cursor-row-resize mx-2 mt-1 relative group"
                    onMouseDown={(e) => {
                      setIsResizingList(true);
                      const startY = e.clientY;
                      const startHeight = keywordListHeight;
                      
                      const handleMouseMove = (e: MouseEvent) => {
                        const newHeight = startHeight + (e.clientY - startY);
                        setKeywordListHeight(Math.max(200, Math.min(800, newHeight)));
                      };
                      
                      const handleMouseUp = () => {
                        setIsResizingList(false);
                        document.removeEventListener('mousemove', handleMouseMove);
                        document.removeEventListener('mouseup', handleMouseUp);
                      };
                      
                      document.addEventListener('mousemove', handleMouseMove);
                      document.addEventListener('mouseup', handleMouseUp);
                    }}
                  >
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="h-0.5 w-8 bg-gray-400 group-hover:bg-blue-500 transition-colors" />
                    </div>
                  </div>
                </div>

                {/* 선택된 키워드 상세 정보 */}
                <div className="lg:col-span-3 flex flex-col">
                  <h3 className="font-semibold mb-2">키워드 상세 정보</h3>
                  <div 
                    className="overflow-y-auto border border-gray-200 rounded-lg p-2 relative"
                    style={{ height: `${keywordDetailHeight}px` }}
                  >
                    {selectedKeyword ? (
                      <div className="border rounded-lg p-4">
                      {(() => {
                        const keywordEntries = keywordData.filter(kw => kw.keyword === selectedKeyword);
                        if (keywordEntries.length === 0) return null;
                        
                        const totalOccurrences = keywordEntries.reduce((sum, entry) => sum + entry.totalOccurrences, 0);
                        const maxScore = Math.max(...keywordEntries.map(entry => entry.maxScore));
                        const avgScore = keywordEntries.reduce((sum, entry) => sum + (entry.avgScore * entry.totalOccurrences), 0) / totalOccurrences;
                        const allExtractors = keywordEntries.map(entry => entry.extractor);
                        const allCategories = Array.from(new Set(keywordEntries.flatMap(entry => entry.categories)));
                        const uniqueFiles = new Set(keywordEntries.flatMap(entry => entry.files.map(f => f.file.id))).size;
                        
                        return (
                          <>
                            {/* 키워드 제목 강조 */}
                            <h4 className="text-xl font-bold text-gray-900 mb-3">{selectedKeyword}</h4>
                            
                            {/* 요약 정보 */}
                            <div className="grid grid-cols-3 gap-4 mb-3 text-sm">
                              <div className="flex items-center justify-center bg-blue-50 rounded-lg p-2">
                                <div className="text-center">
                                  <div className="font-bold text-blue-600">{totalOccurrences}</div>
                                  <div className="text-xs text-gray-600">총 발견</div>
                                </div>
                              </div>
                              <div className="flex items-center justify-center bg-green-50 rounded-lg p-2">
                                <div className="text-center">
                                  <div className="font-bold text-green-600">{uniqueFiles}</div>
                                  <div className="text-xs text-gray-600">파일 수</div>
                                </div>
                              </div>
                              <div className="flex items-center justify-center bg-purple-50 rounded-lg p-2">
                                <div className="text-center">
                                  <div className="font-bold text-purple-600">{(maxScore * 100).toFixed(0)}%</div>
                                  <div className="text-xs text-gray-600">최고 점수</div>
                                </div>
                              </div>
                            </div>

                            {/* 추출기 정보 */}
                            <div className="mb-3">
                              <h5 className="text-xs font-medium text-gray-600 mb-2">추출기별 정보</h5>
                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                {keywordEntries.map((entry, idx) => (
                                  <div key={idx} className="flex items-center justify-between bg-gray-50 rounded-lg p-2">
                                    <div className="flex items-center space-x-2">
                                      <span className={`text-xs px-2 py-1 rounded ${getExtractorColor(entry.extractor)}`}>
                                        {entry.extractor}
                                      </span>
                                      {entry.categories.length > 0 && (
                                        <span className={`text-xs px-1.5 py-0.5 rounded ${getCategoryColor(entry.categories[0])}`}>
                                          {entry.categories[0]}
                                        </span>
                                      )}
                                    </div>
                                    <div className="flex items-center space-x-2 text-xs">
                                      <span className="text-gray-600">{entry.totalOccurrences}회</span>
                                      <span className="font-semibold text-gray-700">{(entry.maxScore * 100).toFixed(0)}%</span>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                            
                            
                            {/* 파일별 상세 정보 */}
                            <div className="space-y-4">
                              <div>
                                <h5 className="text-sm font-medium text-gray-700 mb-3">파일별 발견 정보 ({uniqueFiles}개 파일)</h5>
                                <div className="max-h-60 overflow-y-auto border rounded-lg">
                                  <table className="min-w-full divide-y divide-gray-200 text-sm">
                                    <thead className="bg-gray-50">
                                      <tr>
                                        <th className="px-2 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">파일</th>
                                        <th className="px-2 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">페이지</th>
                                        <th className="px-2 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">라인</th>
                                        <th className="px-2 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">추출기</th>
                                        <th className="px-2 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">보기</th>
                                      </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                      {(() => {
                                        // 모든 추출기 엔트리에서 파일 정보를 합치기
                                        const allOccurrences: { file: UploadedFile; occurrence: KeywordOccurrence }[] = [];
                                        keywordEntries.forEach(entry => {
                                          entry.files.forEach(fileEntry => {
                                            fileEntry.occurrences.forEach(occ => {
                                              allOccurrences.push({
                                                file: fileEntry.file,
                                                occurrence: occ
                                              });
                                            });
                                          });
                                        });
                                        
                                        return allOccurrences.map((item, idx) => {
                                          const isTxtFile = item.file.filename.toLowerCase().endsWith('.txt');
                                          return (
                                            <tr key={idx} className="hover:bg-gray-50">
                                              <td className="px-2 py-2 text-xs text-gray-900 truncate max-w-32" title={item.file.filename}>
                                                {item.file.filename.length > 20 ? item.file.filename.substring(0, 20) + '...' : item.file.filename}
                                              </td>
                                              <td className="px-2 py-2 text-xs text-center text-gray-900">
                                                {!isTxtFile && item.occurrence.page_number ? item.occurrence.page_number : '-'}
                                              </td>
                                              <td className="px-2 py-2 text-xs text-center text-gray-900">
                                                {item.occurrence.line_number || '-'}
                                              </td>
                                              <td className="px-2 py-2 text-xs text-center">
                                                <span className={`inline-flex px-1.5 py-0.5 text-xs rounded ${getExtractorColor(item.occurrence.extractor_name)}`}>
                                                  {item.occurrence.extractor_name}
                                                </span>
                                              </td>
                                              <td className="px-2 py-2 text-xs text-center">
                                                {onViewDocument && (
                                                  <button
                                                    onClick={(e) => {
                                                      e.stopPropagation();
                                                      console.log('🔍 뷰어로 보기 클릭:', {
                                                        file: item.file.filename,
                                                        occurrence: item.occurrence,
                                                        page: item.occurrence.page_number,
                                                        line: item.occurrence.line_number,
                                                        column: item.occurrence.column_number,
                                                        position: `${item.occurrence.start_position}-${item.occurrence.end_position}`
                                                      });
                                                      onViewDocument(item.file, [item.occurrence]);
                                                    }}
                                                    className="inline-flex items-center px-1.5 py-0.5 text-xs bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100 transition-colors"
                                                  >
                                                    보기
                                                  </button>
                                                )}
                                              </td>
                                            </tr>
                                          );
                                        });
                                      })()}
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            </div>
                          </>
                        );
                      })()}
                      </div>
                    ) : (
                      <div className="border rounded-lg p-4 text-center text-gray-500 h-full flex items-center justify-center">
                        <div>키워드를 선택하여 상세 정보를 확인하세요</div>
                      </div>
                    )}
                  </div>
                  {/* 키워드 상세 정보 리사이저 */}
                  <div 
                    className="h-1 bg-gray-200 hover:bg-blue-400 cursor-row-resize mx-2 mt-1 relative group"
                    onMouseDown={(e) => {
                      setIsResizingDetail(true);
                      const startY = e.clientY;
                      const startHeight = keywordDetailHeight;
                      
                      const handleMouseMove = (e: MouseEvent) => {
                        const newHeight = startHeight + (e.clientY - startY);
                        setKeywordDetailHeight(Math.max(200, Math.min(800, newHeight)));
                      };
                      
                      const handleMouseUp = () => {
                        setIsResizingDetail(false);
                        document.removeEventListener('mousemove', handleMouseMove);
                        document.removeEventListener('mouseup', handleMouseUp);
                      };
                      
                      document.addEventListener('mousemove', handleMouseMove);
                      document.addEventListener('mouseup', handleMouseUp);
                    }}
                  >
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="h-0.5 w-8 bg-gray-400 group-hover:bg-blue-500 transition-colors" />
                    </div>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <>
              {/* 문서 중심 리스트 뷰 */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* 문서 목록 */}
                <div className="space-y-3">
                  <h3 className="font-semibold">문서 목록</h3>
                  <div className="max-h-96 overflow-y-auto space-y-2">
                    {files.map((file) => {
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
                                보기
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
                            뷰어에서 보기
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
                                  {kw.page_number && kw.line_number ? (
                                    <span>
                                      📍 페이지 {kw.page_number}, 라인 {kw.line_number}
                                      {kw.column_number && <span>, 컬럼 {kw.column_number}</span>}
                                    </span>
                                  ) : (
                                    <span>위치: {kw.start_position}-{kw.end_position}</span>
                                  )}
                                </span>
                              )}
                            </div>
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
            </>
          )}
        </div>

        {/* 키워드 상세 정보 모달 */}
        {selectedKeywordDetail && (
          <KeywordDetailModal
            keyword={selectedKeywordDetail}
            occurrences={Object.values(keywordsByFile).flat().filter(k => k.keyword === selectedKeywordDetail)}
            files={files}
            onViewDocument={onViewDocument}
            onClose={() => setSelectedKeywordDetail(null)}
          />
        )}
      </>
    );

  if (inline) {
    return content;
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-2">
      <div className="bg-white rounded-lg w-full max-w-7xl h-full max-h-[100vh] flex flex-col">
        <div className="p-6 flex-1 overflow-hidden">
          {content}
        </div>
      </div>
    </div>
  );
};

export default KeywordManagement;