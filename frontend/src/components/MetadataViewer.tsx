import React, { useState, useEffect } from 'react';
import { projectApi, fileApi } from '../services/api';
import { KeywordOccurrence, UploadedFile } from '../types/api';

interface MetadataViewerProps {
  projectId?: number;
  fileId?: number;
  onClose?: () => void;
}

interface MetadataSection {
  title: string;
  icon: string;
  keywords: KeywordOccurrence[];
  color: string;
  description: string;
}

const MetadataViewer: React.FC<MetadataViewerProps> = ({ projectId, fileId, onClose }) => {
  const [metadata, setMetadata] = useState<KeywordOccurrence[]>([]);
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<UploadedFile | null>(null);
  const [selectedFileId, setSelectedFileId] = useState<number | null>(fileId || null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<string>('summary');
  const [viewMode, setViewMode] = useState<'project' | 'file'>('file');

  useEffect(() => {
    loadData();
  }, [projectId, selectedFileId, viewMode]);

  // 키보드 단축키 추가
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.altKey || e.ctrlKey || e.metaKey) return; // 다른 단축키와 충돌 방지
      
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        const currentIndex = files.findIndex(f => f.id === selectedFileId);
        if (currentIndex > 0) {
          const prevFile = files[currentIndex - 1];
          setSelectedFileId(prevFile.id);
          setSelectedFile(prevFile);
        }
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        const currentIndex = files.findIndex(f => f.id === selectedFileId);
        if (currentIndex < files.length - 1) {
          const nextFile = files[currentIndex + 1];
          setSelectedFileId(nextFile.id);
          setSelectedFile(nextFile);
        }
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [files, selectedFileId]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      // 먼저 프로젝트의 모든 파일 목록 가져오기
      if (projectId) {
        const allFiles = await projectApi.getFiles(projectId);
        setFiles(allFiles);
        
        // 선택된 파일이 없으면 첫 번째 파일을 선택
        if (!selectedFileId && allFiles.length > 0) {
          setSelectedFileId(allFiles[0].id);
          setSelectedFile(allFiles[0]);
          return; // useEffect가 다시 실행되도록 리턴
        }
        
        if (selectedFileId) {
          // 특정 파일의 메타데이터 로드
          const response = await fileApi.getKeywords(selectedFileId);
          const keywords = response.keywords || [];
          const metadataKeywords = keywords.filter((kw: KeywordOccurrence) => kw.extractor_name === 'metadata');
          setMetadata(metadataKeywords);
          
          const file = allFiles.find(f => f.id === selectedFileId);
          if (file) {
            setSelectedFile(file);
          }
        }
      }
    } catch (err: any) {
      setError(err.message || '메타데이터를 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const getMetadataSections = (): MetadataSection[] => {
    const sections: MetadataSection[] = [
      {
        title: '📝 문서 요약',
        icon: '📝',
        keywords: metadata.filter(kw => kw.category?.startsWith('summary_')),
        color: 'emerald',
        description: 'AI가 생성한 문서의 핵심 요약'
      },
      {
        title: '🏗️ 문서 구조',
        icon: '🏗️',
        keywords: metadata.filter(kw => 
          kw.category?.includes('title_') || 
          kw.category?.includes('list_') ||
          kw.category === 'structure'
        ),
        color: 'blue',
        description: '제목, 목록, 문서 구조 분석'
      },
      {
        title: '📊 통계 정보',
        icon: '📊',
        keywords: metadata.filter(kw => 
          kw.category?.includes('stat_') ||
          kw.category === 'statistics'
        ),
        color: 'purple',
        description: '문자 수, 단어 수, 문장 수 등'
      },
      {
        title: '🔗 콘텐츠 정보',
        icon: '🔗',
        keywords: metadata.filter(kw => 
          kw.category?.includes('url_') ||
          kw.category?.includes('email_') ||
          kw.category?.includes('date_') ||
          kw.category?.includes('number_') ||
          kw.category === 'content'
        ),
        color: 'orange',
        description: 'URL, 이메일, 날짜, 숫자 패턴'
      },
      {
        title: '📁 파일 정보',
        icon: '📁',
        keywords: metadata.filter(kw => 
          kw.category?.includes('file_') ||
          kw.category === 'file_info'
        ),
        color: 'gray',
        description: '파일 형식, 크기, 생성일 등'
      }
    ];

    return sections.filter(section => section.keywords.length > 0);
  };

  const getSectionColorClasses = (color: string, isActive: boolean = false) => {
    const colorMap: { [key: string]: { bg: string; border: string; text: string; activeBg: string; activeText: string } } = {
      emerald: {
        bg: 'bg-emerald-50',
        border: 'border-emerald-200',
        text: 'text-emerald-700',
        activeBg: 'bg-emerald-100',
        activeText: 'text-emerald-800'
      },
      blue: {
        bg: 'bg-blue-50',
        border: 'border-blue-200', 
        text: 'text-blue-700',
        activeBg: 'bg-blue-100',
        activeText: 'text-blue-800'
      },
      purple: {
        bg: 'bg-purple-50',
        border: 'border-purple-200',
        text: 'text-purple-700',
        activeBg: 'bg-purple-100',
        activeText: 'text-purple-800'
      },
      orange: {
        bg: 'bg-orange-50',
        border: 'border-orange-200',
        text: 'text-orange-700',
        activeBg: 'bg-orange-100',
        activeText: 'text-orange-800'
      },
      gray: {
        bg: 'bg-gray-50',
        border: 'border-gray-200',
        text: 'text-gray-700',
        activeBg: 'bg-gray-100',
        activeText: 'text-gray-800'
      }
    };

    const colors = colorMap[color] || colorMap.gray;
    
    if (isActive) {
      return `${colors.activeBg} ${colors.border} ${colors.activeText}`;
    }
    return `${colors.bg} ${colors.border} ${colors.text}`;
  };

  // 키워드에서 PREFIX 제거하는 함수
  const cleanKeyword = (keyword: string, category?: string) => {
    if (!category) return keyword;
    
    // LLM이 생성한 PREFIX 패턴들 제거
    const prefixPatterns = [
      /^핵심키워드_/i,
      /^주제키워드_/i,
      /^도입부_/i,
      /^결론부_/i,
      /^핵심내용_/i,
      /^문서톤_/i,
      /^summary_[a-z]+_/i,
      /^stat_[a-z]+_/i,
      /^title_[a-z0-9]+_/i,
      /^file_[a-z]+_/i,
    ];
    
    let cleaned = keyword;
    for (const pattern of prefixPatterns) {
      cleaned = cleaned.replace(pattern, '');
    }
    
    return cleaned || keyword; // 빈 문자열이 되면 원본 반환
  };

  // 카테고리별로 키워드를 그룹화하고 렌더링
  const renderGroupedKeywords = (keywords: KeywordOccurrence[]) => {
    // 카테고리별로 그룹화
    const grouped: { [key: string]: KeywordOccurrence[] } = {};
    
    keywords.forEach(kw => {
      const category = kw.category || 'general';
      if (!grouped[category]) {
        grouped[category] = [];
      }
      grouped[category].push(kw);
    });

    // 요약 카테고리를 먼저, 나머지는 알파벳 순으로 정렬
    const sortedCategories = Object.keys(grouped).sort((a, b) => {
      if (a.startsWith('summary_') && !b.startsWith('summary_')) return -1;
      if (!a.startsWith('summary_') && b.startsWith('summary_')) return 1;
      return a.localeCompare(b);
    });

    return sortedCategories.map(category => {
      const categoryKeywords = grouped[category];
      
      // 카테고리 타입에 따른 렌더링 방식 결정
      if (category.startsWith('summary_')) {
        // 요약은 텍스트 형태로 표시
        return renderSummarySection(category, categoryKeywords);
      } else if (category.startsWith('stat_')) {
        // 통계는 간단한 값으로 표시
        return renderStatSection(category, categoryKeywords);
      } else {
        // 나머지는 키워드 목록으로 표시
        return renderKeywordSection(category, categoryKeywords);
      }
    });
  };

  // 요약 섹션 렌더링
  const renderSummarySection = (category: string, keywords: KeywordOccurrence[]) => {
    const categoryLabels: { [key: string]: string } = {
      'summary_intro': '📝 도입부 요약',
      'summary_conclusion': '📑 결론부 요약',
      'summary_core': '💎 핵심 내용',
      'summary_topic': '🏷️ 주제 키워드',
      'summary_tone': '🎭 문서 톤'
    };

    const label = categoryLabels[category] || category;
    
    // 중복 제거 및 점수 기준 정렬
    const uniqueKeywords = Array.from(
      new Map(keywords.map(kw => [cleanKeyword(kw.keyword, kw.category), kw])).values()
    ).sort((a, b) => (b.score || 0) - (a.score || 0));

    return (
      <div key={category} className="mb-6">
        <h4 className="text-sm font-semibold text-gray-700 mb-3">{label}</h4>
        <div className="bg-gray-50 rounded-lg p-4">
          {category === 'summary_topic' ? (
            // 주제 키워드는 태그 형태로 표시
            <div className="flex flex-wrap gap-2">
              {uniqueKeywords.map((kw, idx) => (
                <span 
                  key={idx} 
                  className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
                  title={`점수: ${kw.score?.toFixed(2)}`}
                >
                  {cleanKeyword(kw.keyword, kw.category)}
                </span>
              ))}
            </div>
          ) : (
            // 다른 요약은 텍스트 형태로 표시
            <div className="text-sm text-gray-700 space-y-2">
              {uniqueKeywords.map((kw, idx) => (
                <p key={idx}>{cleanKeyword(kw.keyword, kw.category)}</p>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  };

  // 통계 섹션 렌더링
  const renderStatSection = (category: string, keywords: KeywordOccurrence[]) => {
    const categoryLabels: { [key: string]: string } = {
      'stat_characters': '문자 수',
      'stat_words': '단어 수',
      'stat_sentences': '문장 수',
      'stat_paragraphs': '단락 수'
    };

    return (
      <div key={category} className="mb-4">
        {keywords.map((kw, idx) => (
          <div key={idx} className="flex justify-between py-2 border-b border-gray-200">
            <span className="text-sm text-gray-600">
              {categoryLabels[kw.category || ''] || kw.category}
            </span>
            <span className="text-sm font-medium text-gray-900">
              {cleanKeyword(kw.keyword, kw.category)}
            </span>
          </div>
        ))}
      </div>
    );
  };

  // 일반 키워드 섹션 렌더링
  const renderKeywordSection = (category: string, keywords: KeywordOccurrence[]) => {
    const categoryLabels: { [key: string]: string } = {
      'title_h1': '📌 주요 제목',
      'title_h2': '📍 부제목',
      'title_h3': '📎 소제목',
      'list_item': '▪️ 목록 항목',
      'url_reference': '🔗 URL 참조',
      'email_reference': '📧 이메일',
      'date_korean': '📅 날짜',
      'file_format': '📄 파일 정보'
    };

    const label = categoryLabels[category] || category;
    
    // 중복 제거
    const uniqueKeywords = Array.from(
      new Map(keywords.map(kw => [cleanKeyword(kw.keyword, kw.category), kw])).values()
    );

    return (
      <div key={category} className="mb-4">
        <h5 className="text-xs font-medium text-gray-600 mb-2">{label}</h5>
        <div className="space-y-1">
          {uniqueKeywords.map((kw, idx) => (
            <div key={idx} className="flex items-center justify-between py-1">
              <span className="text-sm text-gray-800">
                {cleanKeyword(kw.keyword, kw.category)}
              </span>
              {kw.score !== undefined && (
                <span className="text-xs text-gray-400">
                  {kw.score.toFixed(2)}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  // 기존의 renderKeywordCard 함수는 사용하지 않음

  const sections = getMetadataSections();
  const activeData = sections.find(s => s.title.includes(activeSection)) || sections[0];

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-lg">
        <div className="p-6">
          <div className="animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
            <div className="space-y-3">
              <div className="h-10 bg-gray-200 rounded"></div>
              <div className="h-10 bg-gray-200 rounded"></div>
              <div className="h-10 bg-gray-200 rounded"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-lg">
        <div className="p-6">
          <div className="text-red-600 text-center">
            <div className="text-lg mb-2">❌</div>
            <div>{error}</div>
            <button 
              onClick={loadData}
              className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              다시 시도
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (metadata.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-lg h-full overflow-hidden">
        {/* 헤더 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-white">
          <div className="flex-1">
            <h2 className="text-xl font-bold text-gray-900">📋 메타데이터 분석</h2>
            
            {/* 파일 선택 드롭다운 */}
            <div className="mt-2 flex items-center space-x-3">
              <label className="text-sm text-gray-600">파일 선택:</label>
              
              {/* 이전/다음 버튼 */}
              <div className="flex items-center space-x-1">
                <button
                  onClick={() => {
                    const currentIndex = files.findIndex(f => f.id === selectedFileId);
                    if (currentIndex > 0) {
                      const prevFile = files[currentIndex - 1];
                      setSelectedFileId(prevFile.id);
                      setSelectedFile(prevFile);
                    }
                  }}
                  disabled={files.findIndex(f => f.id === selectedFileId) <= 0}
                  className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
                  title="이전 파일"
                >
                  ◀
                </button>
                
                <button
                  onClick={() => {
                    const currentIndex = files.findIndex(f => f.id === selectedFileId);
                    if (currentIndex < files.length - 1) {
                      const nextFile = files[currentIndex + 1];
                      setSelectedFileId(nextFile.id);
                      setSelectedFile(nextFile);
                    }
                  }}
                  disabled={files.findIndex(f => f.id === selectedFileId) >= files.length - 1}
                  className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
                  title="다음 파일"
                >
                  ▶
                </button>
              </div>
              
              <select
                value={selectedFileId || ''}
                onChange={(e) => {
                  const newFileId = parseInt(e.target.value);
                  setSelectedFileId(newFileId);
                  const file = files.find(f => f.id === newFileId);
                  setSelectedFile(file || null);
                }}
                className="text-sm border border-gray-300 rounded-md px-3 py-1 bg-white hover:border-gray-400 focus:border-blue-500 focus:outline-none min-w-48 max-w-96"
              >
                {files.map(file => (
                  <option key={file.id} value={file.id}>
                    📄 {file.filename}
                  </option>
                ))}
              </select>
              <div className="text-xs text-gray-500">
                {files.length}개 파일 중 {selectedFile ? files.findIndex(f => f.id === selectedFileId) + 1 : 0}번째
              </div>
              <div className="text-xs text-gray-400">
                (←→ 키로 파일 이동)
              </div>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="text-sm text-gray-500">
              총 <span className="font-semibold text-gray-700">0</span>개 항목
            </div>
            {onClose && (
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 text-2xl font-bold transition-colors"
              >
                ×
              </button>
            )}
          </div>
        </div>
        
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-gray-500">
            <div className="text-4xl mb-4">📋</div>
            <div className="text-lg font-medium mb-2">
              {selectedFile?.filename ? `"${selectedFile.filename}"의 메타데이터가 없습니다` : '메타데이터가 없습니다'}
            </div>
            <div className="text-sm">
              먼저 메타데이터 추출기를 사용하여 이 파일의 키워드를 추출해주세요.
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-lg h-full overflow-hidden">
      {/* 헤더 */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-white">
        <div className="flex-1">
          <h2 className="text-xl font-bold text-gray-900">📋 메타데이터 분석</h2>
          
          {/* 파일 선택 드롭다운 */}
          <div className="mt-2 flex items-center space-x-3">
            <label className="text-sm text-gray-600">파일 선택:</label>
            
            {/* 이전/다음 버튼 */}
            <div className="flex items-center space-x-1">
              <button
                onClick={() => {
                  const currentIndex = files.findIndex(f => f.id === selectedFileId);
                  if (currentIndex > 0) {
                    const prevFile = files[currentIndex - 1];
                    setSelectedFileId(prevFile.id);
                    setSelectedFile(prevFile);
                  }
                }}
                disabled={files.findIndex(f => f.id === selectedFileId) <= 0}
                className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
                title="이전 파일"
              >
                ◀
              </button>
              
              <button
                onClick={() => {
                  const currentIndex = files.findIndex(f => f.id === selectedFileId);
                  if (currentIndex < files.length - 1) {
                    const nextFile = files[currentIndex + 1];
                    setSelectedFileId(nextFile.id);
                    setSelectedFile(nextFile);
                  }
                }}
                disabled={files.findIndex(f => f.id === selectedFileId) >= files.length - 1}
                className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
                title="다음 파일"
              >
                ▶
              </button>
            </div>
            
            <select
              value={selectedFileId || ''}
              onChange={(e) => {
                const newFileId = parseInt(e.target.value);
                setSelectedFileId(newFileId);
                const file = files.find(f => f.id === newFileId);
                setSelectedFile(file || null);
              }}
              className="text-sm border border-gray-300 rounded-md px-3 py-1 bg-white hover:border-gray-400 focus:border-blue-500 focus:outline-none min-w-48 max-w-96"
            >
              {files.map(file => (
                <option key={file.id} value={file.id}>
                  📄 {file.filename}
                </option>
              ))}
            </select>
            <div className="text-xs text-gray-500">
              {files.length}개 파일 중 {selectedFile ? files.findIndex(f => f.id === selectedFileId) + 1 : 0}번째
            </div>
            <div className="text-xs text-gray-400">
              (←→ 키로 파일 이동)
            </div>
          </div>
        </div>
        
        <div className="flex items-center space-x-4">
          <div className="text-sm text-gray-500">
            총 <span className="font-semibold text-gray-700">{metadata.length}</span>개 항목
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl font-bold transition-colors"
            >
              ×
            </button>
          )}
        </div>
      </div>

      <div className="flex h-[calc(100%-120px)]">
        {/* 사이드바 - 섹션 목록 */}
        <div className="w-64 bg-gray-50 border-r border-gray-200 p-4 overflow-y-auto">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">섹션 선택</h3>
          <div className="space-y-1">
            {sections.map((section, index) => (
              <button
                key={index}
                onClick={() => setActiveSection(section.title.toLowerCase())}
                className={`w-full text-left p-3 rounded-lg transition-all ${
                  section.title.toLowerCase().includes(activeSection)
                    ? 'bg-white shadow-sm border-l-4 border-blue-500'
                    : 'hover:bg-white hover:shadow-sm border-l-4 border-transparent'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="text-lg">{section.icon}</span>
                    <span className="text-sm font-medium text-gray-700">
                      {section.title.replace(section.icon, '').trim()}
                    </span>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    section.title.toLowerCase().includes(activeSection)
                      ? 'bg-blue-100 text-blue-700 font-semibold'
                      : 'bg-gray-100 text-gray-600'
                  }`}>
                    {section.keywords.length}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* 메인 콘텐츠 */}
        <div className="flex-1 p-6 overflow-y-auto bg-white">
          {activeData && activeData.keywords.length > 0 ? (
            <div>
              <div className="border-b border-gray-200 pb-4 mb-6">
                <div className="flex items-center space-x-3">
                  <span className="text-2xl">{activeData.icon}</span>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">
                      {activeData.title.replace(activeData.icon, '').trim()}
                    </h3>
                    <p className="text-sm text-gray-500 mt-0.5">
                      {activeData.description}
                    </p>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                {renderGroupedKeywords(activeData.keywords)}
              </div>
            </div>
          ) : activeData ? (
            <div className="text-center text-gray-400 py-16">
              <div className="text-5xl mb-4 opacity-50">{activeData.icon}</div>
              <div className="text-lg font-medium text-gray-500">데이터 없음</div>
              <div className="text-sm text-gray-400 mt-2">
                이 섹션에 해당하는 메타데이터가 없습니다
              </div>
            </div>
          ) : (
            <div className="text-center text-gray-400 py-16">
              <div className="text-5xl mb-4">📂</div>
              <div className="text-lg font-medium text-gray-500">섹션을 선택하세요</div>
              <div className="text-sm text-gray-400 mt-2">
                왼쪽에서 확인하고 싶은 메타데이터 섹션을 선택해주세요
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MetadataViewer;