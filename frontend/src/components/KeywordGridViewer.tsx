import React, { useState, useEffect, useMemo } from 'react';
import { keywordsApi } from '../services/api';

interface KeywordItem {
  keyword: string;
  score: number;
  extractor_name: string;
  category?: string;
  start_position?: number;
  end_position?: number;
  context_snippet?: string;
  file: {
    id: number;
    filename: string;
    project: {
      id: number;
      name: string;
    };
  };
}

interface KeywordGridViewerProps {
  projectId?: number;
  onClose?: () => void;
}

const KeywordGridViewer: React.FC<KeywordGridViewerProps> = ({ projectId, onClose }) => {
  const [keywords, setKeywords] = useState<KeywordItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedKeyword, setSelectedKeyword] = useState<KeywordItem | null>(null);
  const [filters, setFilters] = useState({
    extractor: '',
    category: '',
    searchTerm: '',
  });
  const [pagination, setPagination] = useState({
    limit: 50,
    offset: 0,
    total: 0,
    hasNext: false,
    hasPrev: false,
  });
  const [sortBy, setSortBy] = useState<'score' | 'keyword' | 'extractor'>('score');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // 고유한 추출기와 카테고리 목록 추출
  const [availableExtractors, setAvailableExtractors] = useState<string[]>([]);
  const [availableCategories, setAvailableCategories] = useState<string[]>([]);

  useEffect(() => {
    loadKeywords();
  }, [projectId, filters, pagination.limit, pagination.offset, sortBy, sortOrder]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    // 키워드가 로드될 때마다 사용 가능한 필터 옵션 업데이트
    const extractors = Array.from(new Set(keywords.map(k => k.extractor_name).filter(Boolean)));
    const categories = Array.from(new Set(keywords.map(k => k.category).filter(Boolean))) as string[];
    setAvailableExtractors(extractors);
    setAvailableCategories(categories);
  }, [keywords]);

  const loadKeywords = async () => {
    try {
      setLoading(true);
      setError(null);

      const params: any = {
        limit: pagination.limit,
        offset: pagination.offset,
      };

      if (projectId) {
        params.project_id = projectId;
      }

      if (filters.extractor) {
        params.extractor = filters.extractor;
      }

      if (filters.category) {
        params.category = filters.category;
      }

      const response = await keywordsApi.getList(params);
      
      let filteredKeywords = response.keywords || [];

      // 클라이언트 사이드 검색 필터링
      if (filters.searchTerm) {
        const searchLower = filters.searchTerm.toLowerCase();
        filteredKeywords = filteredKeywords.filter((keyword: KeywordItem) =>
          keyword.keyword.toLowerCase().includes(searchLower) ||
          keyword.file.filename.toLowerCase().includes(searchLower) ||
          keyword.file.project.name.toLowerCase().includes(searchLower) ||
          (keyword.context_snippet && keyword.context_snippet.toLowerCase().includes(searchLower))
        );
      }

      // 클라이언트 사이드 정렬
      filteredKeywords.sort((a: KeywordItem, b: KeywordItem) => {
        let aValue: string | number;
        let bValue: string | number;

        switch (sortBy) {
          case 'score':
            aValue = a.score;
            bValue = b.score;
            break;
          case 'keyword':
            aValue = a.keyword.toLowerCase();
            bValue = b.keyword.toLowerCase();
            break;
          case 'extractor':
            aValue = a.extractor_name.toLowerCase();
            bValue = b.extractor_name.toLowerCase();
            break;
          default:
            aValue = a.score;
            bValue = b.score;
        }

        if (typeof aValue === 'string' && typeof bValue === 'string') {
          const comparison = aValue.localeCompare(bValue);
          return sortOrder === 'asc' ? comparison : -comparison;
        } else {
          const comparison = (aValue as number) - (bValue as number);
          return sortOrder === 'asc' ? comparison : -comparison;
        }
      });

      setKeywords(filteredKeywords);
      setPagination(prev => ({
        ...prev,
        total: response.pagination?.total || filteredKeywords.length,
        hasNext: response.pagination?.has_next || false,
        hasPrev: response.pagination?.has_prev || false,
      }));
    } catch (err: any) {
      setError('키워드를 불러오는데 실패했습니다: ' + (err.message || '알 수 없는 오류'));
      console.error('키워드 로딩 실패:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key: string, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPagination(prev => ({ ...prev, offset: 0 })); // 필터 변경 시 첫 페이지로
  };

  const handlePageChange = (newOffset: number) => {
    setPagination(prev => ({ ...prev, offset: newOffset }));
  };

  const handleSortChange = (column: 'score' | 'keyword' | 'extractor') => {
    if (sortBy === column) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  // 키워드별 추출기 맵 생성 (다중 추출기 검출용)
  const keywordExtractorMap = useMemo(() => {
    const map: { [keyword: string]: Set<string> } = {};
    keywords.forEach(item => {
      const key = `${item.keyword}_${item.file.id}`;  // 파일별로 구분
      if (!map[key]) {
        map[key] = new Set();
      }
      map[key].add(item.extractor_name);
    });
    return map;
  }, [keywords]);

  // 키워드가 다중 추출기에 의해 추출되었는지 확인
  const isMultiExtractorKeyword = (keyword: KeywordItem) => {
    const key = `${keyword.keyword}_${keyword.file.id}`;
    return keywordExtractorMap[key]?.size > 1;
  };

  const getExtractorColor = (keyword: KeywordItem) => {
    const extractor = keyword.extractor_name;
    const isMultiExtractor = isMultiExtractorKeyword(keyword);
    
    if (isMultiExtractor) {
      // 다중 추출기 키워드는 황금색/오렌지색 계열로 표시
      return 'bg-gradient-to-r from-yellow-100 to-orange-100 text-orange-900 border border-orange-300';
    }
    
    // 단일 추출기 키워드는 기존 색상
    switch (extractor) {
      case 'keybert':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'spacy_ner':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'llm':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'konlpy':
        return 'bg-pink-100 text-pink-800 border-pink-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  // 다중 추출기 키워드의 모든 추출기 목록 표시
  const getMultiExtractorInfo = (keyword: KeywordItem) => {
    const key = `${keyword.keyword}_${keyword.file.id}`;
    const extractors = keywordExtractorMap[key];
    if (extractors && extractors.size > 1) {
      return Array.from(extractors).join(', ');
    }
    return keyword.extractor_name;
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'PERSON':
      case 'PS':
        return 'bg-red-100 text-red-800';
      case 'ORG':
      case 'OG':
        return 'bg-blue-100 text-blue-800';
      case 'LOC':
      case 'LC':
        return 'bg-green-100 text-green-800';
      case 'DATE':
      case 'DT':
        return 'bg-yellow-100 text-yellow-800';
      case 'MONEY':
        return 'bg-emerald-100 text-emerald-800';
      case 'MISC':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-indigo-100 text-indigo-800';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">키워드를 불러오는 중...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
        <div className="text-red-800 font-medium">오류 발생</div>
        <div className="text-red-600 text-sm mt-1">{error}</div>
        <button
          onClick={loadKeywords}
          className="mt-2 px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700"
        >
          다시 시도
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">
            키워드 그리드 뷰
            {projectId && (
              <span className="text-sm font-normal text-gray-600 ml-2">
                - 프로젝트별
              </span>
            )}
          </h3>
          <p className="text-sm text-gray-600">
            총 {pagination.total}개의 키워드
          </p>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl"
          >
            ×
          </button>
        )}
      </div>

      {/* 필터 및 검색 */}
      <div className="bg-gray-50 p-4 rounded-lg space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          {/* 검색 */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">검색</label>
            <input
              type="text"
              value={filters.searchTerm}
              onChange={(e) => handleFilterChange('searchTerm', e.target.value)}
              placeholder="키워드, 파일명, 프로젝트명..."
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* 추출기 필터 */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">추출기</label>
            <select
              value={filters.extractor}
              onChange={(e) => handleFilterChange('extractor', e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">전체</option>
              {availableExtractors.map(extractor => (
                <option key={extractor} value={extractor}>{extractor}</option>
              ))}
            </select>
          </div>

          {/* 카테고리 필터 */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">카테고리</label>
            <select
              value={filters.category}
              onChange={(e) => handleFilterChange('category', e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">전체</option>
              {availableCategories.map(category => (
                <option key={category} value={category}>{category}</option>
              ))}
            </select>
          </div>

          {/* 페이지 크기 */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">표시 개수</label>
            <select
              value={pagination.limit}
              onChange={(e) => {
                const newLimit = parseInt(e.target.value);
                setPagination(prev => ({ ...prev, limit: newLimit, offset: 0 }));
              }}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value={25}>25개</option>
              <option value={50}>50개</option>
              <option value={100}>100개</option>
              <option value={200}>200개</option>
            </select>
          </div>
        </div>

        {/* 정렬 옵션 */}
        <div className="flex items-center space-x-4">
          <span className="text-xs font-medium text-gray-700">정렬:</span>
          {(['score', 'keyword', 'extractor'] as const).map(column => (
            <button
              key={column}
              onClick={() => handleSortChange(column)}
              className={`text-xs px-2 py-1 rounded border ${
                sortBy === column
                  ? 'bg-blue-100 text-blue-800 border-blue-200'
                  : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
              }`}
            >
              {column === 'score' ? '점수' : column === 'keyword' ? '키워드' : '추출기'}
              {sortBy === column && (
                <span className="ml-1">
                  {sortOrder === 'asc' ? '↑' : '↓'}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* 필터 요약 */}
        {(filters.extractor || filters.category || filters.searchTerm) && (
          <div className="flex items-center space-x-2">
            <span className="text-xs text-gray-600">활성 필터:</span>
            {filters.searchTerm && (
              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                검색: "{filters.searchTerm}"
              </span>
            )}
            {filters.extractor && (
              <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded">
                추출기: {filters.extractor}
              </span>
            )}
            {filters.category && (
              <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                카테고리: {filters.category}
              </span>
            )}
            <button
              onClick={() => {
                setFilters({ extractor: '', category: '', searchTerm: '' });
                setPagination(prev => ({ ...prev, offset: 0 }));
              }}
              className="text-xs text-gray-500 hover:text-gray-700 underline"
            >
              모든 필터 지우기
            </button>
          </div>
        )}
      </div>

      {/* 키워드 그리드 */}
      {keywords.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <div className="text-gray-400 text-4xl mb-4">🔍</div>
          <div className="text-gray-600">키워드가 없습니다</div>
          <div className="text-sm text-gray-500 mt-1">
            {(filters.extractor || filters.category || filters.searchTerm) 
              ? '필터 조건을 변경해 보세요' 
              : '키워드 추출을 먼저 실행해 주세요'}
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {keywords.map((keyword, index) => (
            <div
              key={`${keyword.keyword}-${keyword.extractor_name}-${index}`}
              className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow hover:border-blue-300 cursor-pointer"
              onClick={() => setSelectedKeyword(keyword)}
            >
              {/* 키워드 헤더 */}
              <div className="flex items-start justify-between mb-2">
                <h4 className="font-medium text-gray-900 text-sm leading-tight">
                  {keyword.keyword}
                </h4>
                <div className="text-right text-xs text-gray-500 ml-2 flex-shrink-0">
                  <div className="font-semibold text-blue-600">
                    {(keyword.score * 100).toFixed(1)}%
                  </div>
                </div>
              </div>

              {/* 추출기 및 카테고리 */}
              <div className="flex flex-wrap gap-1 mb-2">
                <span className={`text-xs px-2 py-1 rounded border ${getExtractorColor(keyword)}`}>
                  {isMultiExtractorKeyword(keyword) ? (
                    <span title={`다중 추출기: ${getMultiExtractorInfo(keyword)}`}>
                      🌟 {getMultiExtractorInfo(keyword)}
                    </span>
                  ) : (
                    keyword.extractor_name
                  )}
                </span>
                {keyword.category && (
                  <span className={`text-xs px-2 py-1 rounded ${getCategoryColor(keyword.category)}`}>
                    {keyword.category}
                  </span>
                )}
              </div>

              {/* 파일 정보 */}
              <div className="text-xs text-gray-600 mb-2">
                <div className="truncate" title={keyword.file.filename}>
                  📄 {keyword.file.filename}
                </div>
                {!projectId && (
                  <div className="truncate text-gray-500" title={keyword.file.project.name}>
                    📁 {keyword.file.project.name}
                  </div>
                )}
              </div>

              {/* 컨텍스트 */}
              {keyword.context_snippet && (
                <div className="text-xs text-gray-600 bg-gray-50 p-2 rounded border-l-2 border-gray-300">
                  <div 
                    className="overflow-hidden"
                    style={{
                      display: '-webkit-box',
                      WebkitLineClamp: 3,
                      WebkitBoxOrient: 'vertical',
                      lineHeight: '1.2em',
                      maxHeight: '3.6em'
                    }}
                    title={keyword.context_snippet}
                  >
                    {keyword.context_snippet}
                  </div>
                </div>
              )}

              {/* 위치 정보 */}
              {keyword.start_position !== undefined && keyword.end_position !== undefined && (
                <div className="text-xs text-gray-500 mt-2">
                  위치: {keyword.start_position}-{keyword.end_position}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 페이지네이션 */}
      {keywords.length > 0 && (
        <div className="flex items-center justify-between bg-white p-4 border border-gray-200 rounded-lg">
          <div className="text-sm text-gray-600">
            {pagination.offset + 1}-{Math.min(pagination.offset + pagination.limit, pagination.total)} / {pagination.total}개
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => handlePageChange(Math.max(0, pagination.offset - pagination.limit))}
              disabled={!pagination.hasPrev || pagination.offset <= 0}
              className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              이전
            </button>
            <button
              onClick={() => handlePageChange(pagination.offset + pagination.limit)}
              disabled={!pagination.hasNext || pagination.offset + pagination.limit >= pagination.total}
              className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              다음
            </button>
          </div>
        </div>
      )}

      {/* 키워드 상세 모달 */}
      {selectedKeyword && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedKeyword(null)}
        >
          <div 
            className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6">
              {/* 헤더 */}
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-semibold text-gray-900">키워드 상세 정보</h3>
                <button
                  onClick={() => setSelectedKeyword(null)}
                  className="text-gray-400 hover:text-gray-600 text-2xl"
                >
                  ×
                </button>
              </div>

              {/* 키워드 정보 */}
              <div className="space-y-4">
                <div>
                  <h4 className="text-2xl font-bold text-gray-900 mb-2">{selectedKeyword.keyword}</h4>
                  <div className="flex items-center space-x-3">
                    <span className={`px-3 py-1 rounded-full text-sm border ${getExtractorColor(selectedKeyword)}`}>
                      {isMultiExtractorKeyword(selectedKeyword) ? (
                        <span title={`다중 추출기: ${getMultiExtractorInfo(selectedKeyword)}`}>
                          🌟 {getMultiExtractorInfo(selectedKeyword)}
                        </span>
                      ) : (
                        selectedKeyword.extractor_name
                      )}
                    </span>
                    {selectedKeyword.category && (
                      <span className={`px-3 py-1 rounded-full text-sm ${getCategoryColor(selectedKeyword.category)}`}>
                        {selectedKeyword.category}
                      </span>
                    )}
                    <div className="text-lg font-semibold text-blue-600">
                      {(selectedKeyword.score * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>

                {/* 파일 정보 */}
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h5 className="font-medium text-gray-900 mb-2">파일 정보</h5>
                  <div className="space-y-1 text-sm text-gray-600">
                    <div><strong>파일명:</strong> {selectedKeyword.file.filename}</div>
                    <div><strong>프로젝트:</strong> {selectedKeyword.file.project.name}</div>
                    {selectedKeyword.start_position !== undefined && selectedKeyword.end_position !== undefined && (
                      <div>
                        <strong>위치:</strong> {selectedKeyword.start_position}-{selectedKeyword.end_position}
                      </div>
                    )}
                  </div>
                </div>

                {/* 컨텍스트 */}
                {selectedKeyword.context_snippet && (
                  <div className="bg-blue-50 p-4 rounded-lg border-l-4 border-blue-400">
                    <h5 className="font-medium text-gray-900 mb-2">컨텍스트</h5>
                    <div className="text-sm text-gray-700 leading-relaxed">
                      {selectedKeyword.context_snippet}
                    </div>
                  </div>
                )}

                {/* 통계 정보 */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-green-50 p-3 rounded-lg">
                    <div className="text-sm text-green-600 font-medium">점수</div>
                    <div className="text-lg font-bold text-green-800">
                      {(selectedKeyword.score * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div className="bg-purple-50 p-3 rounded-lg">
                    <div className="text-sm text-purple-600 font-medium">추출기</div>
                    <div className="text-lg font-bold text-purple-800">
                      {selectedKeyword.extractor_name}
                    </div>
                  </div>
                </div>
              </div>

              {/* 닫기 버튼 */}
              <div className="mt-6 flex justify-end">
                <button
                  onClick={() => setSelectedKeyword(null)}
                  className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 transition-colors"
                >
                  닫기
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default KeywordGridViewer;