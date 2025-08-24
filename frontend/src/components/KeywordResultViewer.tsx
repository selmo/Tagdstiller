import React, { useState } from 'react';
import { KeywordOccurrence, UploadedFile } from '../types/api';
import KeywordDetailModal from './KeywordDetailModal';

interface KeywordResultViewerProps {
  keywords: KeywordOccurrence[];
  extractorsUsed: string[];
  totalKeywords: number;
  onViewDocument?: (file: UploadedFile, keywords?: string[] | KeywordOccurrence[]) => void;
  files?: UploadedFile[]; // 프로젝트 파일 목록
}

// 추출기별 통계 정보 인터페이스
interface ExtractorStats {
  name: string;
  totalKeywords: number;
  uniqueKeywords: number;
  avgScore: number;
  maxScore: number;
  categories: string[];
  topKeywords: string[];
}

const KeywordResultViewer: React.FC<KeywordResultViewerProps> = ({ 
  keywords, 
  extractorsUsed, 
  totalKeywords,
  onViewDocument,
  files = []
}: KeywordResultViewerProps) => {
  
  // 키워드 상세 모달 상태
  const [selectedKeywordDetail, setSelectedKeywordDetail] = useState<string | null>(null);

  // 추출기별 통계 계산
  const calculateExtractorStats = (): ExtractorStats[] => {
    return extractorsUsed.map(extractorName => {
      const extractorKeywords = keywords.filter(k => k.extractor_name === extractorName);
      const uniqueKeywords = new Set(extractorKeywords.map(k => k.keyword.toLowerCase().trim())).size;
      const scores = extractorKeywords.map(k => k.score);
      const avgScore = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
      const maxScore = scores.length > 0 ? Math.max(...scores) : 0;
      const categories = Array.from(new Set(extractorKeywords.map(k => k.category).filter(Boolean))) as string[];
      
      // 상위 키워드 5개 (점수순)
      const topKeywords = extractorKeywords
        .sort((a, b) => b.score - a.score)
        .slice(0, 5)
        .map(k => k.keyword);

      return {
        name: extractorName,
        totalKeywords: extractorKeywords.length,
        uniqueKeywords,
        avgScore,
        maxScore,
        categories,
        topKeywords
      };
    });
  };

  const extractorStats = calculateExtractorStats();

  // 파일별로 그룹화된 키워드 정보
  const getFileKeywordMap = () => {
    const fileMap = new Map<number, { file: UploadedFile | null, keywords: KeywordOccurrence[] }>();
    
    keywords.forEach(keyword => {
      if (!fileMap.has(keyword.file_id)) {
        // files 배열에서 실제 파일 정보 찾기
        const actualFile = files.find(f => f.id === keyword.file_id);
        fileMap.set(keyword.file_id, { 
          file: actualFile || null, 
          keywords: [] 
        });
      }
      fileMap.get(keyword.file_id)!.keywords.push(keyword);
    });
    
    return fileMap;
  };

  const fileKeywordMap = getFileKeywordMap();

  const getScoreColor = (score: number): string => {
    if (score >= 0.8) return 'bg-green-100 text-green-800';
    if (score >= 0.6) return 'bg-yellow-100 text-yellow-800';
    if (score >= 0.4) return 'bg-orange-100 text-orange-800';
    return 'bg-red-100 text-red-800';
  };

  const getExtractorColor = (extractor: string): string => {
    const colors: { [key: string]: string } = {
      'keybert': 'bg-blue-100 text-blue-800',
      'spacy_ner': 'bg-green-100 text-green-800',
      'llm': 'bg-purple-100 text-purple-800',
      'konlpy': 'bg-orange-100 text-orange-800',
      'langextract': 'bg-teal-100 text-teal-800',
      'metadata': 'bg-slate-100 text-slate-800'
    };
    return colors[extractor] || 'bg-gray-100 text-gray-800';
  };

  const getCategoryColor = (category: string): string => {
    const colors: { [key: string]: string } = {
      // spaCy NER 카테고리
      'PERSON': 'bg-indigo-100 text-indigo-800',
      'ORG': 'bg-emerald-100 text-emerald-800',
      'LOC': 'bg-amber-100 text-amber-800',
      'DATE': 'bg-lime-100 text-lime-800',
      'MONEY': 'bg-rose-100 text-rose-800',
      
      // LangExtract 카테고리
      'technology': 'bg-cyan-100 text-cyan-800',
      'person': 'bg-indigo-100 text-indigo-800',
      'organization': 'bg-emerald-100 text-emerald-800',
      'location': 'bg-amber-100 text-amber-800',
      'concept': 'bg-purple-100 text-purple-800',
      'general': 'bg-gray-100 text-gray-800',
      
      // LangExtract 의미적 유형
      'technology_noun': 'bg-cyan-100 text-cyan-800',
      'person_noun': 'bg-indigo-100 text-indigo-800',
      'organization_noun': 'bg-emerald-100 text-emerald-800',
      'location_noun': 'bg-amber-100 text-amber-800',
      'concept_noun': 'bg-purple-100 text-purple-800',
      'general_noun': 'bg-gray-100 text-gray-800',
      
      // Metadata 카테고리
      'title_h1': 'bg-slate-100 text-slate-800',
      'title_h2': 'bg-slate-100 text-slate-700',
      'title_h3': 'bg-slate-100 text-slate-600',
      'title_h4_h6': 'bg-slate-100 text-slate-600',
      'list_item': 'bg-gray-100 text-gray-700',
      'numbered_item': 'bg-gray-100 text-gray-700',
      'doc_length': 'bg-blue-100 text-blue-700',
      'word_count': 'bg-blue-100 text-blue-700',
      'sentence_count': 'bg-blue-100 text-blue-700',
      'paragraph_count': 'bg-blue-100 text-blue-700',
      'sentence_length': 'bg-blue-100 text-blue-700',
      'complexity': 'bg-blue-100 text-blue-700',
      'url_reference': 'bg-green-100 text-green-700',
      'email_reference': 'bg-green-100 text-green-700',
      'date_korean': 'bg-yellow-100 text-yellow-700',
      'date_iso': 'bg-yellow-100 text-yellow-700',
      'date_us': 'bg-yellow-100 text-yellow-700',
      'date_eu': 'bg-yellow-100 text-yellow-700',
      'numeric_content': 'bg-purple-100 text-purple-700',
      'file_format': 'bg-red-100 text-red-700',
      'filename_keyword': 'bg-red-100 text-red-700',
      'file_size': 'bg-red-100 text-red-700',
      
      // 요약 메타데이터 카테고리
      'summary_intro': 'bg-emerald-100 text-emerald-800',
      'summary_conclusion': 'bg-emerald-200 text-emerald-900',
      'summary_core': 'bg-teal-200 text-teal-900',
      'summary_topic': 'bg-cyan-100 text-cyan-800',
      'summary_tone': 'bg-sky-100 text-sky-800',
      
      // 기타 카테고리
      'noun': 'bg-violet-100 text-violet-800'
    };
    return colors[category] || 'bg-gray-100 text-gray-800';
  };

  // LangExtract 키워드 전용 컴포넌트
  const LangExtractKeywordCard: React.FC<{ keyword: KeywordOccurrence }> = ({ keyword }) => (
    <div className="border rounded-lg p-3 bg-teal-50 border-teal-200">
      <div className="flex justify-between items-start mb-2">
        <span className="font-medium text-teal-900">{keyword.keyword}</span>
        <div className="flex gap-2">
          {/* 신뢰도 표시 */}
          <span className={`px-2 py-1 rounded text-xs font-medium ${
            keyword.score > 0.8 ? 'bg-green-100 text-green-800' :
            keyword.score > 0.6 ? 'bg-yellow-100 text-yellow-800' :
            'bg-red-100 text-red-800'
          }`}>
            {(keyword.score * 100).toFixed(0)}%
          </span>
          
          {/* 카테고리 표시 */}
          {keyword.category && (
            <span className={`px-2 py-1 rounded text-xs font-medium ${getCategoryColor(keyword.category)}`}>
              {keyword.category}
            </span>
          )}
        </div>
      </div>
      
      {/* 위치 정보 */}
      {keyword.start_position !== null && (
        <div className="text-xs text-teal-600 mb-1">
          📍 위치: {keyword.start_position}-{keyword.end_position}
          {keyword.page_number && ` (페이지 ${keyword.page_number})`}
        </div>
      )}
      
      {/* 컨텍스트 */}
      {keyword.context_snippet && (
        <div className="text-xs text-gray-600 bg-white p-2 rounded border">
          "{keyword.context_snippet}"
        </div>
      )}
    </div>
  );

  // 신뢰도 표시 컴포넌트
  const ConfidenceIndicator: React.FC<{ score: number; size?: 'sm' | 'md' }> = ({ score, size = 'sm' }) => {
    const confidence = score * 100;
    const getConfidenceColor = () => {
      if (confidence >= 80) return 'bg-green-500';
      if (confidence >= 60) return 'bg-yellow-500';
      return 'bg-red-500';
    };
    
    const sizeClasses = size === 'sm' ? 'w-12 h-2' : 'w-16 h-3';
    
    return (
      <div className="flex items-center gap-2">
        <div className={`${sizeClasses} bg-gray-200 rounded-full overflow-hidden`}>
          <div 
            className={`h-full ${getConfidenceColor()} transition-all duration-300`}
            style={{ width: `${Math.min(confidence, 100)}%` }}
          />
        </div>
        <span className={`text-gray-600 ${size === 'sm' ? 'text-xs' : 'text-sm'}`}>
          {confidence.toFixed(0)}%
        </span>
      </div>
    );
  };

  if (keywords.length === 0) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold mb-4">키워드 추출 결과</h3>
        <div className="text-center py-8 text-gray-500">
          추출된 키워드가 없습니다.
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold">🎯 키워드 추출 완료</h3>
        <div className="text-sm text-gray-500">
          총 {totalKeywords}개 키워드 추출됨
        </div>
      </div>

      {/* 전체 요약 */}
      <div className="bg-gradient-to-r from-green-50 to-blue-50 p-4 rounded-lg mb-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-green-600">{totalKeywords}</div>
            <div className="text-xs text-gray-600">총 키워드</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-blue-600">{extractorsUsed.length}</div>
            <div className="text-xs text-gray-600">사용된 추출기</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-purple-600">
              {new Set(keywords.map(k => k.keyword.toLowerCase().trim())).size}
            </div>
            <div className="text-xs text-gray-600">고유 키워드</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-orange-600">
              {Array.from(new Set(keywords.map(k => k.category).filter(Boolean))).length}
            </div>
            <div className="text-xs text-gray-600">카테고리</div>
          </div>
        </div>
      </div>

      {/* 추출기별 통계 */}
      <div className="space-y-4">
        <h4 className="text-md font-semibold text-gray-800 mb-3">📊 추출기별 상세 통계</h4>
        
        {extractorStats.map((stats, index) => (
          <div key={index} className={`border rounded-lg p-4 ${
            stats.name === 'langextract' 
              ? 'border-teal-200 bg-teal-50' 
              : 'border-gray-200 bg-gray-50'
          }`}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getExtractorColor(stats.name)}`}>
                  {stats.name}
                </span>
                <span className="font-semibold text-gray-800">
                  {stats.totalKeywords}개 키워드
                </span>
              </div>
              <div className="text-right">
                <div className="text-sm text-gray-600">
                  고유: {stats.uniqueKeywords}개
                </div>
                {/* LangExtract의 경우 평균 신뢰도 표시 */}
                {stats.name === 'langextract' && (
                  <div className="mt-1">
                    <ConfidenceIndicator score={stats.avgScore} size="sm" />
                  </div>
                )}
              </div>
            </div>

            {/* LangExtract 전용 향상된 정보 */}
            {stats.name === 'langextract' && (
              <div className="mb-3 p-3 bg-white rounded border border-teal-100">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-3 h-3 bg-teal-400 rounded-full"></div>
                  <span className="text-sm font-medium text-teal-800">구조화된 추출 정보</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="text-gray-600">
                    <span className="font-medium">평균 신뢰도:</span> {(stats.avgScore * 100).toFixed(1)}%
                  </div>
                  <div className="text-gray-600">
                    <span className="font-medium">최고 점수:</span> {(stats.maxScore * 100).toFixed(1)}%
                  </div>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
              <div className="text-center bg-white p-2 rounded">
                <div className="text-lg font-bold text-green-600">
                  {(stats.maxScore * 100).toFixed(1)}%
                </div>
                <div className="text-xs text-gray-600">최고 점수</div>
              </div>
              <div className="text-center bg-white p-2 rounded">
                <div className="text-lg font-bold text-blue-600">
                  {(stats.avgScore * 100).toFixed(1)}%
                </div>
                <div className="text-xs text-gray-600">평균 점수</div>
              </div>
              <div className="text-center bg-white p-2 rounded">
                <div className="text-lg font-bold text-purple-600">
                  {stats.uniqueKeywords}
                </div>
                <div className="text-xs text-gray-600">고유 키워드</div>
              </div>
              <div className="text-center bg-white p-2 rounded">
                <div className="text-lg font-bold text-orange-600">
                  {stats.categories.length}
                </div>
                <div className="text-xs text-gray-600">카테고리</div>
              </div>
            </div>

            {/* 상위 키워드 */}
            {stats.topKeywords.length > 0 && (
              <div className="mb-3">
                <div className="text-xs font-medium text-gray-700 mb-2">상위 키워드:</div>
                <div className="flex flex-wrap gap-1">
                  {stats.topKeywords.map((keyword: string, kIndex: number) => (
                    <button
                      key={kIndex}
                      onClick={() => setSelectedKeywordDetail(keyword)}
                      className="px-2 py-1 bg-white text-gray-800 text-xs rounded border hover:bg-blue-50 hover:border-blue-300 transition-colors cursor-pointer"
                    >
                      {keyword} 🔍
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* 문서에서 보기 버튼 */}
            {onViewDocument && (
              <div className="mt-3 pt-3 border-t border-gray-200">
                <div className="text-xs font-medium text-gray-700 mb-2">관련 문서:</div>
                <div className="flex flex-wrap gap-2">
                  {Array.from(fileKeywordMap.entries())
                    .filter(([_, fileInfo]) => 
                      fileInfo.file && fileInfo.keywords.some(k => k.extractor_name === stats.name)
                    )
                    .slice(0, 3) // 최대 3개 파일만 표시
                    .map(([fileId, fileInfo]) => (
                      <button
                        key={fileId}
                        onClick={() => {
                          if (fileInfo.file) {
                            const extractorKeywords = fileInfo.keywords
                              .filter(k => k.extractor_name === stats.name)
                              .map(k => k.keyword);
                            onViewDocument(fileInfo.file, extractorKeywords);
                          }
                        }}
                        className="px-2 py-1 text-xs bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100 transition-colors"
                      >
                        📄 {fileInfo.file?.filename || `파일 ${fileId}`}
                      </button>
                    ))
                  }
                  {Array.from(fileKeywordMap.entries())
                    .filter(([_, fileInfo]) => 
                      fileInfo.keywords.some(k => k.extractor_name === stats.name)
                    ).length === 0 && (
                    <span className="text-xs text-gray-500">관련 문서 없음</span>
                  )}
                </div>
              </div>
            )}

            {/* 카테고리 */}
            {stats.categories.length > 0 && (
              <div>
                <div className="text-xs font-medium text-gray-700 mb-2">발견된 카테고리:</div>
                <div className="flex flex-wrap gap-1">
                  {stats.categories.map((category: string, cIndex: number) => (
                    <span key={cIndex} className={`px-2 py-1 text-xs rounded ${getCategoryColor(category)}`}>
                      {category}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 성공 메시지 */}
      <div className="mt-6 p-4 bg-green-50 border-l-4 border-green-400 rounded">
        <div className="flex items-center">
          <div className="text-green-600 text-lg mr-2">✅</div>
          <div>
            <div className="text-sm font-medium text-green-800">키워드 추출이 성공적으로 완료되었습니다!</div>
            <div className="text-xs text-green-600 mt-1">
              이제 왼쪽 패널에서 '키워드 관리'를 클릭하여 상세한 키워드 분석을 확인할 수 있습니다.
            </div>
          </div>
        </div>
      </div>

      {/* 키워드 상세 정보 모달 */}
      {selectedKeywordDetail && (
        <KeywordDetailModal
          keyword={selectedKeywordDetail}
          occurrences={keywords.filter(k => k.keyword === selectedKeywordDetail)}
          files={files}
          onViewDocument={onViewDocument}
          onClose={() => setSelectedKeywordDetail(null)}
        />
      )}
    </div>
  );
};

export default KeywordResultViewer;