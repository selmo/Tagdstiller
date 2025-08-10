import React from 'react';
import { KeywordOccurrence, UploadedFile } from '../types/api';

interface KeywordDetailProps {
  keyword: string;
  occurrences: KeywordOccurrence[];
  files: UploadedFile[];
  onViewDocument?: (file: UploadedFile, keywords?: string[]) => void;
  onClose: () => void;
}

const KeywordDetailModal: React.FC<KeywordDetailProps> = ({
  keyword,
  occurrences,
  files,
  onViewDocument,
  onClose
}) => {
  // 통계 계산
  const stats = {
    totalOccurrences: occurrences.length,
    uniqueFiles: new Set(occurrences.map(o => o.file_id)).size,
    extractors: Array.from(new Set(occurrences.map(o => o.extractor_name))),
    categories: Array.from(new Set(occurrences.map(o => o.category).filter(Boolean))) as string[],
    avgScore: occurrences.length > 0 ? occurrences.reduce((sum, o) => sum + o.score, 0) / occurrences.length : 0,
    maxScore: occurrences.length > 0 ? Math.max(...occurrences.map(o => o.score)) : 0,
    minScore: occurrences.length > 0 ? Math.min(...occurrences.map(o => o.score)) : 0
  };

  // 파일별 그룹화
  const fileGroups = new Map<number, { file: UploadedFile | null, occurrences: KeywordOccurrence[] }>();
  occurrences.forEach(occ => {
    if (!fileGroups.has(occ.file_id)) {
      const file = files.find(f => f.id === occ.file_id) || null;
      fileGroups.set(occ.file_id, { file, occurrences: [] });
    }
    fileGroups.get(occ.file_id)!.occurrences.push(occ);
  });

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
      'DATE': 'bg-amber-100 text-amber-800',
      'MONEY': 'bg-lime-100 text-lime-800',
      'technology': 'bg-cyan-100 text-cyan-800',
      'noun': 'bg-violet-100 text-violet-800'
    };
    return colors[category] || 'bg-gray-100 text-gray-800';
  };

  const getScoreColor = (score: number): string => {
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.6) return 'text-yellow-600';
    if (score >= 0.4) return 'text-orange-600';
    return 'text-red-600';
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden">
        {/* 헤더 */}
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-6 border-b">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">"{keyword}" 상세 정보</h2>
              <div className="flex items-center space-x-4 text-sm text-gray-600">
                <span>📊 {stats.totalOccurrences}회 발견</span>
                <span>📄 {stats.uniqueFiles}개 파일</span>
                <span>🔧 {stats.extractors.length}개 추출기</span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl font-bold"
            >
              ×
            </button>
          </div>
        </div>

        <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
          {/* 요약 통계 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-blue-50 p-4 rounded-lg text-center">
              <div className="text-2xl font-bold text-blue-600">{stats.totalOccurrences}</div>
              <div className="text-xs text-gray-600">총 발견 횟수</div>
            </div>
            <div className="bg-green-50 p-4 rounded-lg text-center">
              <div className="text-2xl font-bold text-green-600">{stats.uniqueFiles}</div>
              <div className="text-xs text-gray-600">발견된 파일</div>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg text-center">
              <div className={`text-2xl font-bold ${getScoreColor(stats.maxScore)}`}>
                {(stats.maxScore * 100).toFixed(1)}%
              </div>
              <div className="text-xs text-gray-600">최고 점수</div>
            </div>
            <div className="bg-orange-50 p-4 rounded-lg text-center">
              <div className={`text-2xl font-bold ${getScoreColor(stats.avgScore)}`}>
                {(stats.avgScore * 100).toFixed(1)}%
              </div>
              <div className="text-xs text-gray-600">평균 점수</div>
            </div>
          </div>

          {/* 추출기 및 카테고리 */}
          <div className="mb-6">
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">사용된 추출기</h3>
                <div className="flex flex-wrap gap-1">
                  {stats.extractors.map(extractor => (
                    <span key={extractor} className={`px-2 py-1 text-xs rounded ${getExtractorColor(extractor)}`}>
                      {extractor}
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">발견된 카테고리</h3>
                <div className="flex flex-wrap gap-1">
                  {stats.categories.length > 0 ? stats.categories.map(category => (
                    <span key={category} className={`px-2 py-1 text-xs rounded ${getCategoryColor(category)}`}>
                      {category}
                    </span>
                  )) : (
                    <span className="text-xs text-gray-500">카테고리 없음</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* 파일별 상세 정보 */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">파일별 발견 정보</h3>
            <div className="space-y-4">
              {Array.from(fileGroups.entries()).map(([fileId, group]) => (
                <div key={fileId} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-3">
                      <div className="text-sm font-medium text-gray-900">
                        📄 {group.file?.filename || `파일 ${fileId}`}
                      </div>
                      <div className="text-xs text-gray-500">
                        {group.occurrences.length}회 발견
                      </div>
                    </div>
                    {onViewDocument && group.file && (
                      <button
                        onClick={() => onViewDocument(group.file!, [keyword])}
                        className="px-3 py-1 text-xs bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100 transition-colors"
                      >
                        📄 뷰어에서 보기
                      </button>
                    )}
                  </div>

                  {/* 발견 위치들 */}
                  <div className="space-y-2">
                    {group.occurrences.map((occ, index) => (
                      <div key={index} className="bg-gray-50 p-3 rounded border-l-4 border-blue-200">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center space-x-2">
                            <span className={`px-2 py-1 text-xs rounded ${getExtractorColor(occ.extractor_name)}`}>
                              {occ.extractor_name}
                            </span>
                            <span className={`px-2 py-1 text-xs rounded bg-gray-200 ${getScoreColor(occ.score)}`}>
                              {(occ.score * 100).toFixed(1)}%
                            </span>
                            {occ.category && (
                              <span className={`px-2 py-1 text-xs rounded ${getCategoryColor(occ.category)}`}>
                                {occ.category}
                              </span>
                            )}
                          </div>
                          {(occ.start_position !== null && occ.end_position !== null) && (
                            <div className="text-xs text-gray-500">
                              {occ.page_number && occ.line_number ? (
                                <span>
                                  📍 페이지 {occ.page_number}, 라인 {occ.line_number}
                                  {occ.column_number && <span>, 컬럼 {occ.column_number}</span>}
                                  <span className="text-gray-400 ml-1">({occ.start_position}-{occ.end_position})</span>
                                </span>
                              ) : (
                                <span>위치: {occ.start_position}-{occ.end_position}</span>
                              )}
                            </div>
                          )}
                        </div>
                        {occ.context_snippet && (
                          <div className="text-sm text-gray-700 italic">
                            "{occ.context_snippet}"
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 푸터 */}
        <div className="bg-gray-50 px-6 py-4 border-t flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  );
};

export default KeywordDetailModal;