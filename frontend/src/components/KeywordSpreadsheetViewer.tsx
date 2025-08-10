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

interface KeywordSpreadsheetViewerProps {
  projectId?: number;
  viewType: 'keywords' | 'documents';
  onClose?: () => void;
}

const KeywordSpreadsheetViewer: React.FC<KeywordSpreadsheetViewerProps> = ({ 
  projectId, 
  viewType, 
  onClose 
}) => {
  const [keywords, setKeywords] = useState<KeywordItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<string>('score');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [filters, setFilters] = useState({
    extractor: '',
    category: '',
    searchTerm: '',
  });
  const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set());

  useEffect(() => {
    loadKeywords();
  }, [projectId]);

  const loadKeywords = async () => {
    try {
      setLoading(true);
      setError(null);

      const params: any = { limit: 1000 }; // 스프레드시트는 많은 데이터를 한번에 로드
      if (projectId) {
        params.project_id = projectId;
      }

      const response = await keywordsApi.getList(params);
      setKeywords(response.keywords || []);
    } catch (err: any) {
      setError('키워드를 불러오는데 실패했습니다: ' + (err.message || '알 수 없는 오류'));
      console.error('키워드 로딩 실패:', err);
    } finally {
      setLoading(false);
    }
  };

  // 필터링 및 정렬된 키워드
  const processedKeywords = keywords
    .filter(keyword => {
      const matchesSearch = keyword.keyword.toLowerCase().includes(filters.searchTerm.toLowerCase()) ||
                          keyword.file.filename.toLowerCase().includes(filters.searchTerm.toLowerCase()) ||
                          keyword.file.project.name.toLowerCase().includes(filters.searchTerm.toLowerCase());
      const matchesExtractor = !filters.extractor || keyword.extractor_name === filters.extractor;
      const matchesCategory = !filters.category || keyword.category === filters.category;
      
      return matchesSearch && matchesExtractor && matchesCategory;
    })
    .sort((a, b) => {
      let aValue: any, bValue: any;
      
      switch (sortBy) {
        case 'keyword':
          aValue = a.keyword.toLowerCase();
          bValue = b.keyword.toLowerCase();
          break;
        case 'score':
          aValue = a.score;
          bValue = b.score;
          break;
        case 'extractor':
          aValue = a.extractor_name.toLowerCase();
          bValue = b.extractor_name.toLowerCase();
          break;
        case 'category':
          aValue = (a.category || '').toLowerCase();
          bValue = (b.category || '').toLowerCase();
          break;
        case 'filename':
          aValue = a.file.filename.toLowerCase();
          bValue = b.file.filename.toLowerCase();
          break;
        case 'project':
          aValue = a.file.project.name.toLowerCase();
          bValue = b.file.project.name.toLowerCase();
          break;
        default:
          aValue = a.score;
          bValue = b.score;
      }

      if (typeof aValue === 'string') {
        const comparison = aValue.localeCompare(bValue);
        return sortOrder === 'asc' ? comparison : -comparison;
      } else {
        const comparison = aValue - bValue;
        return sortOrder === 'asc' ? comparison : -comparison;
      }
    });

  // 그룹화된 데이터 (문서 중심 뷰용)
  const groupedByFile = processedKeywords.reduce((acc, keyword) => {
    const fileId = keyword.file.id;
    if (!acc[fileId]) {
      acc[fileId] = {
        file: keyword.file,
        keywords: []
      };
    }
    acc[fileId].keywords.push(keyword);
    return acc;
  }, {} as { [fileId: number]: { file: any; keywords: KeywordItem[] } });

  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  const handleSelectRow = (index: number) => {
    const newSelected = new Set(selectedRows);
    if (newSelected.has(index)) {
      newSelected.delete(index);
    } else {
      newSelected.add(index);
    }
    setSelectedRows(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedRows.size === processedKeywords.length) {
      setSelectedRows(new Set());
    } else {
      setSelectedRows(new Set(Array.from({ length: processedKeywords.length }, (_, i) => i)));
    }
  };

  const exportToCSV = () => {
    const header = viewType === 'keywords' 
      ? ['키워드', '점수', '추출기', '카테고리', '파일명', '프로젝트', '위치', '컨텍스트']
      : ['파일명', '프로젝트', '키워드', '점수', '추출기', '카테고리', '위치', '컨텍스트'];
    
    const csvData = [
      header,
      ...processedKeywords.map(kw => [
        ...(viewType === 'keywords' 
          ? [
              kw.keyword,
              (kw.score * 100).toFixed(1) + '%',
              kw.extractor_name,
              kw.category || '',
              kw.file.filename,
              kw.file.project.name,
              kw.start_position && kw.end_position ? `${kw.start_position}-${kw.end_position}` : '',
              kw.context_snippet || ''
            ]
          : [
              kw.file.filename,
              kw.file.project.name,
              kw.keyword,
              (kw.score * 100).toFixed(1) + '%',
              kw.extractor_name,
              kw.category || '',
              kw.start_position && kw.end_position ? `${kw.start_position}-${kw.end_position}` : '',
              kw.context_snippet || ''
            ]
        )
      ])
    ];

    const csvContent = csvData.map(row => 
      row.map(field => `"${field.toString().replace(/"/g, '""')}"`).join(',')
    ).join('\n');

    const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `keywords-${viewType}-${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // 키워드별 추출기 맵 생성 (다중 추출기 검출용)
  const keywordExtractorMap = useMemo(() => {
    const map: { [keyword: string]: Set<string> } = {};
    processedKeywords.forEach(item => {
      const key = `${item.keyword}_${item.file.id}`;  // 파일별로 구분
      if (!map[key]) {
        map[key] = new Set();
      }
      map[key].add(item.extractor_name);
    });
    return map;
  }, [processedKeywords]);

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
      return 'bg-gradient-to-r from-yellow-100 to-orange-100 text-orange-900 border border-orange-200';
    }
    
    // 단일 추출기 키워드는 기존 색상
    switch (extractor) {
      case 'keybert': return 'bg-blue-100 text-blue-800';
      case 'spacy_ner': return 'bg-purple-100 text-purple-800';
      case 'llm': return 'bg-green-100 text-green-800';
      case 'konlpy': return 'bg-pink-100 text-pink-800';
      default: return 'bg-gray-100 text-gray-800';
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
      case 'PS': return 'bg-red-100 text-red-800';
      case 'ORG':
      case 'OG': return 'bg-blue-100 text-blue-800';
      case 'LOC':
      case 'LC': return 'bg-green-100 text-green-800';
      case 'DATE':
      case 'DT': return 'bg-yellow-100 text-yellow-800';
      case 'MONEY': return 'bg-emerald-100 text-emerald-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">데이터를 불러오는 중...</span>
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

  // 고유한 추출기와 카테고리 목록
  const uniqueExtractors = Array.from(new Set(keywords.map(k => k.extractor_name)));
  const uniqueCategories = Array.from(new Set(keywords.map(k => k.category).filter(Boolean))) as string[];

  return (
    <div className="space-y-4">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">
            키워드 스프레드시트 뷰 - {viewType === 'keywords' ? '키워드 중심' : '문서 중심'}
            {projectId && (
              <span className="text-sm font-normal text-gray-600 ml-2">
                - 프로젝트별
              </span>
            )}
          </h3>
          <p className="text-sm text-gray-600">
            총 {processedKeywords.length}개의 키워드 {selectedRows.size > 0 && `(${selectedRows.size}개 선택됨)`}
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={exportToCSV}
            className="px-3 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition-colors"
            disabled={processedKeywords.length === 0}
          >
            📊 CSV 내보내기
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl"
            >
              ×
            </button>
          )}
        </div>
      </div>

      {/* 필터 */}
      <div className="bg-gray-50 p-4 rounded-lg">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">검색</label>
            <input
              type="text"
              value={filters.searchTerm}
              onChange={(e) => setFilters(prev => ({ ...prev, searchTerm: e.target.value }))}
              placeholder="키워드, 파일명..."
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">추출기</label>
            <select
              value={filters.extractor}
              onChange={(e) => setFilters(prev => ({ ...prev, extractor: e.target.value }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">전체</option>
              {uniqueExtractors.map(extractor => (
                <option key={extractor} value={extractor}>{extractor}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">카테고리</label>
            <select
              value={filters.category}
              onChange={(e) => setFilters(prev => ({ ...prev, category: e.target.value }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">전체</option>
              {uniqueCategories.map(category => (
                <option key={category} value={category}>{category}</option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={() => setFilters({ extractor: '', category: '', searchTerm: '' })}
              className="px-3 py-2 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition-colors"
            >
              필터 초기화
            </button>
          </div>
        </div>
      </div>

      {/* 스프레드시트 테이블 */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-3 text-left">
                  <input
                    type="checkbox"
                    checked={selectedRows.size === processedKeywords.length && processedKeywords.length > 0}
                    onChange={handleSelectAll}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                </th>
                {viewType === 'keywords' ? (
                  <>
                    <th 
                      className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                      onClick={() => handleSort('keyword')}
                    >
                      키워드 {sortBy === 'keyword' && (sortOrder === 'asc' ? '↑' : '↓')}
                    </th>
                    <th 
                      className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                      onClick={() => handleSort('score')}
                    >
                      점수 {sortBy === 'score' && (sortOrder === 'asc' ? '↑' : '↓')}
                    </th>
                    <th 
                      className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                      onClick={() => handleSort('extractor')}
                    >
                      추출기 {sortBy === 'extractor' && (sortOrder === 'asc' ? '↑' : '↓')}
                    </th>
                    <th 
                      className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                      onClick={() => handleSort('category')}
                    >
                      카테고리 {sortBy === 'category' && (sortOrder === 'asc' ? '↑' : '↓')}
                    </th>
                    <th 
                      className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                      onClick={() => handleSort('filename')}
                    >
                      파일명 {sortBy === 'filename' && (sortOrder === 'asc' ? '↑' : '↓')}
                    </th>
                    {!projectId && (
                      <th 
                        className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                        onClick={() => handleSort('project')}
                      >
                        프로젝트 {sortBy === 'project' && (sortOrder === 'asc' ? '↑' : '↓')}
                      </th>
                    )}
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      위치
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      컨텍스트
                    </th>
                  </>
                ) : (
                  <>
                    <th 
                      className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                      onClick={() => handleSort('filename')}
                    >
                      파일명 {sortBy === 'filename' && (sortOrder === 'asc' ? '↑' : '↓')}
                    </th>
                    {!projectId && (
                      <th 
                        className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                        onClick={() => handleSort('project')}
                      >
                        프로젝트 {sortBy === 'project' && (sortOrder === 'asc' ? '↑' : '↓')}
                      </th>
                    )}
                    <th 
                      className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                      onClick={() => handleSort('keyword')}
                    >
                      키워드 {sortBy === 'keyword' && (sortOrder === 'asc' ? '↑' : '↓')}
                    </th>
                    <th 
                      className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                      onClick={() => handleSort('score')}
                    >
                      점수 {sortBy === 'score' && (sortOrder === 'asc' ? '↑' : '↓')}
                    </th>
                    <th 
                      className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                      onClick={() => handleSort('extractor')}
                    >
                      추출기 {sortBy === 'extractor' && (sortOrder === 'asc' ? '↑' : '↓')}
                    </th>
                    <th 
                      className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                      onClick={() => handleSort('category')}
                    >
                      카테고리 {sortBy === 'category' && (sortOrder === 'asc' ? '↑' : '↓')}
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      위치
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      컨텍스트
                    </th>
                  </>
                )}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {processedKeywords.map((keyword, index) => (
                <tr 
                  key={index}
                  className={`hover:bg-gray-50 ${selectedRows.has(index) ? 'bg-blue-50' : ''}`}
                >
                  <td className="px-3 py-4 whitespace-nowrap">
                    <input
                      type="checkbox"
                      checked={selectedRows.has(index)}
                      onChange={() => handleSelectRow(index)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                  </td>
                  {viewType === 'keywords' ? (
                    <>
                      <td className="px-3 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {keyword.keyword}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-900">
                        <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                          {(keyword.score * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getExtractorColor(keyword)}`}>
                          {isMultiExtractorKeyword(keyword) ? (
                            <span title={`다중 추출기: ${getMultiExtractorInfo(keyword)}`}>
                              🌟 {getMultiExtractorInfo(keyword)}
                            </span>
                          ) : (
                            keyword.extractor_name
                          )}
                        </span>
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm">
                        {keyword.category && (
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getCategoryColor(keyword.category)}`}>
                            {keyword.category}
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-4 text-sm text-gray-900 max-w-xs truncate" title={keyword.file.filename}>
                        {keyword.file.filename}
                      </td>
                      {!projectId && (
                        <td className="px-3 py-4 text-sm text-gray-500 max-w-xs truncate" title={keyword.file.project.name}>
                          {keyword.file.project.name}
                        </td>
                      )}
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500">
                        {keyword.start_position !== undefined && keyword.end_position !== undefined && 
                          `${keyword.start_position}-${keyword.end_position}`
                        }
                      </td>
                      <td className="px-3 py-4 text-sm text-gray-500 max-w-md truncate" title={keyword.context_snippet || ''}>
                        {keyword.context_snippet}
                      </td>
                    </>
                  ) : (
                    <>
                      <td className="px-3 py-4 text-sm font-medium text-gray-900 max-w-xs truncate" title={keyword.file.filename}>
                        {keyword.file.filename}
                      </td>
                      {!projectId && (
                        <td className="px-3 py-4 text-sm text-gray-500 max-w-xs truncate" title={keyword.file.project.name}>
                          {keyword.file.project.name}
                        </td>
                      )}
                      <td className="px-3 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {keyword.keyword}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-900">
                        <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                          {(keyword.score * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getExtractorColor(keyword)}`}>
                          {isMultiExtractorKeyword(keyword) ? (
                            <span title={`다중 추출기: ${getMultiExtractorInfo(keyword)}`}>
                              🌟 {getMultiExtractorInfo(keyword)}
                            </span>
                          ) : (
                            keyword.extractor_name
                          )}
                        </span>
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm">
                        {keyword.category && (
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getCategoryColor(keyword.category)}`}>
                            {keyword.category}
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500">
                        {keyword.start_position !== undefined && keyword.end_position !== undefined && 
                          `${keyword.start_position}-${keyword.end_position}`
                        }
                      </td>
                      <td className="px-3 py-4 text-sm text-gray-500 max-w-md truncate" title={keyword.context_snippet || ''}>
                        {keyword.context_snippet}
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {processedKeywords.length === 0 && (
          <div className="text-center py-12">
            <div className="text-gray-400 text-4xl mb-4">📊</div>
            <div className="text-gray-600">표시할 키워드가 없습니다</div>
            <div className="text-sm text-gray-500 mt-1">
              필터 조건을 변경하거나 키워드 추출을 먼저 실행해 주세요
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default KeywordSpreadsheetViewer;