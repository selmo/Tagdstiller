import React, { useEffect, useState, useCallback, useRef } from 'react';
import axios from 'axios';
import { UploadedFile } from '../types/api';
import AdvancedPDFViewer from './AdvancedPDFViewer';

const API_BASE_URL = 'http://localhost:58000';

interface DocumentViewerProps {
  file: UploadedFile;
  selectedKeywords?: string[];
  targetPosition?: { page?: number; line?: number; column?: number };
  onClose: () => void;
}

export default function DocumentViewerSimple({ file, selectedKeywords = [], targetPosition, onClose }: DocumentViewerProps) {
  const safeKeywords = Array.isArray(selectedKeywords) 
    ? selectedKeywords.map(k => typeof k === 'string' ? k : String(k)).filter(Boolean)
    : [];
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fileType, setFileType] = useState<string>('');
  const [highlightKeywords, setHighlightKeywords] = useState(true);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [showTextContent, setShowTextContent] = useState(false);
  const [useAdvancedPDFViewer, setUseAdvancedPDFViewer] = useState(false);
  
  // 드래그 및 크기 조절 상태
  const [isMaximized, setIsMaximized] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [size, setSize] = useState({ width: 1000, height: 700 });
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [resizeStart, setResizeStart] = useState({ x: 0, y: 0, width: 0, height: 0 });
  const modalRef = useRef<HTMLDivElement>(null);
  const headerRef = useRef<HTMLDivElement>(null);

  const fetchFileContent = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const extension = file.filename.split('.').pop()?.toLowerCase() || '';
      setFileType(extension);
      
      if (extension === 'pdf') {
        // For PDF files, get the binary file for browser PDF viewer
        try {
          const response = await axios.get(`${API_BASE_URL}/projects/${file.id}/download`, {
            responseType: 'blob'
          });
          let url = URL.createObjectURL(response.data);
          
          // PDF URL에 파라미터 추가
          const urlParams = [];
          
          // 페이지 파라미터
          if (targetPosition?.page) {
            urlParams.push(`page=${targetPosition.page}`);
          }
          
          // 검색 파라미터 (키워드 하이라이트)
          if (safeKeywords.length > 0) {
            // 첫 번째 키워드로 검색 (PDF.js search 기능 활용)
            const searchKeyword = safeKeywords[0];
            urlParams.push(`search=${encodeURIComponent(searchKeyword)}`);
          }
          
          if (urlParams.length > 0) {
            url += `#${urlParams.join('&')}`;
            console.log(`📍 PDF URL with parameters: ${url}`);
            console.log(`📍 Parameters: ${urlParams.join(', ')}`);
          }
          
          setPdfUrl(url);
          
          // Also try to get parsed content for keyword highlighting
          try {
            const contentResponse = await axios.get(`${API_BASE_URL}/projects/${file.project_id}/files/${file.id}/content`);
            setContent(contentResponse.data.content || '');
          } catch (contentErr) {
            setContent('');
          }
        } catch (err) {
          setError('PDF 파일을 불러올 수 없습니다.');
        }
      } else {
        const response = await axios.get(`${API_BASE_URL}/projects/${file.project_id}/files/${file.id}/content`);
        setContent(response.data.content || '문서가 파싱되지 않았습니다. 키워드 추출을 먼저 실행해주세요.');
      }
    } catch (err) {
      console.error('Error fetching file content:', err);
      setError('파일 내용을 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  }, [file.id, file.filename, file.project_id, targetPosition]);

  useEffect(() => {
    fetchFileContent();
  }, [fetchFileContent]);

  // PDF 파일에서 위치 이동이 필요한 경우 자동으로 텍스트 뷰 표시
  useEffect(() => {
    if (fileType === 'pdf' && (targetPosition || safeKeywords.length > 0)) {
      setShowTextContent(true);
    }
  }, [fileType, targetPosition, safeKeywords.length]);

  // Separate cleanup effect for pdfUrl
  useEffect(() => {
    return () => {
      // Cleanup blob URL to prevent memory leaks
      if (pdfUrl) {
        URL.revokeObjectURL(pdfUrl);
      }
    };
  }, [pdfUrl]);

  // Scroll to target position when content is loaded
  useEffect(() => {
    if (!loading && content && targetPosition) {
      console.log('📍 위치 이동 시도:', targetPosition);
      console.log('📄 콘텐츠 길이:', content.length);
      console.log('📝 콘텐츠 라인 수:', content.split('\n').length);
      
      // 지연을 늘려서 DOM이 완전히 렌더링된 후 스크롤
      setTimeout(() => {
        scrollToTargetPosition();
      }, 300);
    }
  }, [loading, content, targetPosition]);

  const scrollToTargetPosition = () => {
    if (!targetPosition) {
      console.log('❌ targetPosition이 없습니다');
      return;
    }

    console.log('🎯 scrollToTargetPosition 실행:', targetPosition);

    const contentElement = document.getElementById('document-content');
    if (!contentElement) {
      console.log('❌ document-content 요소를 찾을 수 없습니다');
      return;
    }

    console.log('✅ document-content 요소 찾음:', contentElement);

    // 1. 라인 번호 기반 스크롤
    if (targetPosition.line) {
      const lines = content.split('\n');
      const targetLine = targetPosition.line - 1; // 0-indexed
      
      console.log(`📋 총 라인 수: ${lines.length}, 대상 라인: ${targetPosition.line} (0-based: ${targetLine})`);
      
      if (targetLine >= 0 && targetLine < lines.length) {
        const lineHeight = 24; // line-height와 일치
        const scrollPosition = targetLine * lineHeight;
        
        console.log(`📏 계산된 스크롤 위치: ${scrollPosition}px (라인 높이: ${lineHeight}px)`);
        
        contentElement.scrollTo({
          top: Math.max(0, scrollPosition - 150),
          behavior: 'smooth'
        });
        
        console.log(`✅ 스크롤 완료: ${Math.max(0, scrollPosition - 150)}px로 이동`);
        
        // 해당 라인 하이라이트 효과
        highlightTargetLine(targetLine);
      } else {
        console.log(`❌ 라인 번호가 범위를 벗어남: ${targetLine} (총 라인: ${lines.length})`);
      }
    } else {
      console.log('❌ targetPosition.line이 없습니다');
    }
  };

  const highlightTargetLine = (lineNumber: number) => {
    // 임시 하이라이트 효과 추가
    const contentElement = document.getElementById('document-content');
    if (!contentElement) return;

    // 기존 하이라이트 제거
    const existingHighlight = document.querySelector('.target-line-highlight');
    if (existingHighlight) {
      existingHighlight.remove();
    }

    // 새 하이라이트 요소 생성
    const highlight = document.createElement('div');
    highlight.className = 'target-line-highlight';
    highlight.style.cssText = `
      position: absolute;
      left: 0;
      right: 0;
      height: 24px;
      background-color: rgba(255, 235, 59, 0.3);
      border-left: 4px solid #ff9800;
      pointer-events: none;
      z-index: 10;
      top: ${lineNumber * 24}px;
      animation: fadeOut 3s ease-out forwards;
    `;

    // CSS 애니메이션 추가
    if (!document.querySelector('#highlight-style')) {
      const style = document.createElement('style');
      style.id = 'highlight-style';
      style.textContent = `
        @keyframes fadeOut {
          0% { opacity: 1; }
          70% { opacity: 1; }
          100% { opacity: 0; }
        }
      `;
      document.head.appendChild(style);
    }

    contentElement.style.position = 'relative';
    contentElement.appendChild(highlight);

    // 3초 후 제거
    setTimeout(() => {
      if (highlight.parentNode) {
        highlight.remove();
      }
    }, 3000);
  };

  // 드래그 시작
  const handleMouseDown = (e: React.MouseEvent) => {
    if (isMaximized) return;
    if (e.target !== headerRef.current && !headerRef.current?.contains(e.target as Node)) return;
    
    setIsDragging(true);
    setDragStart({
      x: e.clientX - position.x,
      y: e.clientY - position.y
    });
  };

  // 크기 조절 시작
  const handleResizeStart = (e: React.MouseEvent) => {
    if (isMaximized) return;
    e.stopPropagation();
    setIsResizing(true);
    setResizeStart({
      x: e.clientX,
      y: e.clientY,
      width: size.width,
      height: size.height
    });
  };

  // 마우스 이동 처리
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging && !isMaximized) {
        setPosition({
          x: e.clientX - dragStart.x,
          y: e.clientY - dragStart.y
        });
      } else if (isResizing && !isMaximized) {
        const newWidth = Math.max(400, resizeStart.width + (e.clientX - resizeStart.x));
        const newHeight = Math.max(300, resizeStart.height + (e.clientY - resizeStart.y));
        setSize({ width: newWidth, height: newHeight });
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      setIsResizing(false);
    };

    if (isDragging || isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, isResizing, dragStart, resizeStart]);

  // 최대화/복원
  const toggleMaximize = () => {
    setIsMaximized(!isMaximized);
  };

  // 초기 위치 설정 (화면 중앙)
  useEffect(() => {
    const centerX = (window.innerWidth - size.width) / 2;
    const centerY = (window.innerHeight - size.height) / 2;
    setPosition({ x: centerX, y: centerY });
  }, []);

  // Safety check - after hooks
  if (!file || !file.filename) {
    return null;
  }

  const highlightText = (text: string): string => {
    if (!highlightKeywords || safeKeywords.length === 0) return text;
    
    let highlightedText = text;
    
    safeKeywords.forEach((keyword, index) => {
      if (!keyword) return;
      
      const escapedKeyword = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const regex = new RegExp(`(${escapedKeyword})`, 'gi');
      const colors = [
        'rgba(59, 130, 246, 0.3)', 'rgba(34, 197, 94, 0.3)', 'rgba(168, 85, 247, 0.3)',
        'rgba(251, 146, 60, 0.3)', 'rgba(236, 72, 153, 0.3)', 'rgba(250, 204, 21, 0.3)'
      ];
      const color = colors[index % colors.length];
      highlightedText = highlightedText.replace(
        regex,
        `<span style="background-color: ${color}; padding: 2px 4px; border-radius: 3px; font-weight: 500;">$1</span>`
      );
    });
    
    return highlightedText;
  };

  const renderContent = () => {
    if (loading) {
      return (
        <div className="flex items-center justify-center h-full">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      );
    }

    if (error) {
      return (
        <div className="flex items-center justify-center h-full">
          <div className="text-red-600 text-center">
            <p className="text-xl mb-2">⚠️</p>
            <p>{error}</p>
          </div>
        </div>
      );
    }

    if (fileType === 'pdf') {
      return (
        <div className="flex flex-col h-full">
          {/* PDF Viewer Controls */}
          <div className="flex items-center justify-between p-4 border-b bg-gray-50">
            <div className="flex items-center space-x-4">
              <span className="text-sm font-medium">PDF 뷰어</span>
              {targetPosition && (
                <div className="flex items-center space-x-2">
                  <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
                    📍 {targetPosition.page ? `페이지 ${targetPosition.page}` : ''}
                    {targetPosition.line ? `, 라인 ${targetPosition.line}` : ''}
                  </span>
                </div>
              )}
              {safeKeywords.length > 0 && (
                <div className="flex items-center space-x-2">
                  <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                    🔍 검색: {safeKeywords[0]} {safeKeywords.length > 1 ? `외 ${safeKeywords.length - 1}개` : ''}
                  </span>
                  <button
                    onClick={() => setUseAdvancedPDFViewer(true)}
                    className="px-3 py-1 text-xs bg-purple-100 text-purple-700 rounded hover:bg-purple-200"
                  >
                    고급 PDF 뷰어 (정밀 하이라이트)
                  </button>
                  {content && (
                    <button
                      onClick={() => setShowTextContent(!showTextContent)}
                      className="px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                    >
                      {showTextContent ? 'PDF 보기 (검색 하이라이트)' : '텍스트 보기 (정확한 위치)'}
                    </button>
                  )}
                </div>
              )}
            </div>
            <div className="flex items-center space-x-2">
              <a
                href={`${API_BASE_URL}/projects/${file.id}/download`}
                className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm"
                download
              >
                ⬇ 다운로드
              </a>
            </div>
          </div>

          {/* PDF Content */}
          <div className="flex-1 overflow-hidden">
            {showTextContent && content ? (
              <div id="document-content" className="p-6 overflow-auto h-full">
                <div className="mb-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-medium mb-2">추출된 텍스트 내용 (키워드 하이라이팅)</h3>
                    {targetPosition && (
                      <div className="text-sm bg-blue-50 text-blue-800 px-3 py-1 rounded">
                        이동 중: {targetPosition.page ? `페이지 ${targetPosition.page}` : ''}
                        {targetPosition.line ? `, 라인 ${targetPosition.line}` : ''}
                      </div>
                    )}
                  </div>
                  <p className="text-sm text-gray-600">PDF에서 추출된 텍스트에서 키워드를 검색할 수 있습니다. 위치 이동 기능을 사용하려면 텍스트 보기를 이용하세요.</p>
                </div>
                <pre 
                  className="whitespace-pre-wrap font-mono text-sm border p-4 bg-gray-50 rounded relative"
                  dangerouslySetInnerHTML={{ __html: highlightText(content) }}
                />
              </div>
            ) : (
              <div className="w-full h-full">
                {pdfUrl ? (
                  <div className="w-full h-full relative">
                    {(targetPosition || safeKeywords.length > 0) && (
                      <div className="absolute top-2 right-2 z-10 bg-yellow-100 text-yellow-800 px-3 py-1 rounded shadow text-sm max-w-xs">
                        {targetPosition && (
                          <>
                            📍 페이지 {targetPosition.page}로 이동됨 
                            {targetPosition.line && (
                              <div className="text-xs mt-1">라인 {targetPosition.line} 위치는 텍스트 보기에서 확인하세요</div>
                            )}
                          </>
                        )}
                        {safeKeywords.length > 0 && (
                          <div className="text-xs mt-1">
                            🔍 "{safeKeywords[0]}" 검색 중 - Ctrl+F로 다음 결과 탐색 가능
                          </div>
                        )}
                      </div>
                    )}
                    <iframe
                      src={pdfUrl}
                      title={`PDF Viewer - ${file.filename}`}
                      className="w-full h-full border-0"
                      style={{ minHeight: '600px' }}
                    />
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-full">
                    <div className="text-center">
                      <p className="text-gray-600 mb-4">PDF를 불러오는 중...</p>
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      );
    }

    return (
      <div id="document-content" className="p-6 overflow-auto h-full">
        <pre 
          className="whitespace-pre-wrap font-mono text-sm relative"
          style={{ lineHeight: '24px' }}
          dangerouslySetInnerHTML={{ __html: highlightText(content) }}
        />
      </div>
    );
  };

  // 고급 PDF 뷰어 사용 시
  if (useAdvancedPDFViewer && fileType === 'pdf') {
    return (
      <AdvancedPDFViewer
        file={file}
        keywords={safeKeywords}
        targetPosition={targetPosition}
        onClose={() => setUseAdvancedPDFViewer(false)}
      />
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-30 z-50">
      <div 
        ref={modalRef}
        className={`bg-white rounded-lg shadow-2xl flex flex-col border border-gray-300 ${
          isMaximized 
            ? 'fixed inset-2' 
            : 'absolute'
        }`}
        style={isMaximized ? {} : {
          left: position.x,
          top: position.y,
          width: size.width,
          height: size.height,
          minWidth: '400px',
          minHeight: '300px'
        }}
        onMouseDown={handleMouseDown}
      >
        {/* Header */}
        <div 
          ref={headerRef}
          className={`flex items-center justify-between p-3 border-b bg-gray-50 rounded-t-lg ${
            !isMaximized ? 'cursor-move' : ''
          }`}
        >
          <div className="flex items-center space-x-3">
            <span className="text-gray-600">📄</span>
            <h2 className="text-xl font-semibold">{file.filename}</h2>
          </div>
          <div className="flex items-center space-x-4">
            {safeKeywords.length > 0 && (
              <label className="flex items-center space-x-2 text-sm">
                <input
                  type="checkbox"
                  checked={highlightKeywords}
                  onChange={(e) => setHighlightKeywords(e.target.checked)}
                  className="rounded"
                />
                <span>키워드 하이라이트</span>
              </label>
            )}
            <a
              href={`${API_BASE_URL}/projects/${file.id}/download`}
              className="flex items-center space-x-2 px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              <span>⬇</span>
              <span>다운로드</span>
            </a>
            <div className="flex items-center space-x-1">
              <button
                onClick={toggleMaximize}
                className="p-1.5 hover:bg-gray-200 rounded text-sm"
                title={isMaximized ? '복원' : '최대화'}
              >
                {isMaximized ? '🗗' : '🗖'}
              </button>
              <button
                onClick={onClose}
                className="p-1.5 hover:bg-gray-200 rounded text-sm"
                title="닫기"
              >
                ✕
              </button>
            </div>
          </div>
        </div>

        {/* Keyword pills */}
        {safeKeywords.length > 0 && highlightKeywords && (
          <div className="px-4 py-2 border-b bg-gray-50 flex flex-wrap gap-2">
            <span className="text-sm text-gray-600 mr-2">키워드:</span>
            {safeKeywords.map((keyword, index) => (
              <span
                key={keyword}
                className="px-3 py-1 text-xs rounded-full"
                style={{ backgroundColor: `rgba(59, 130, 246, 0.3)` }}
              >
                {keyword}
              </span>
            ))}
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-hidden relative">
          {renderContent()}
        </div>
        
        {/* 크기 조절 핸들 */}
        {!isMaximized && (
          <div 
            className="absolute bottom-0 right-0 w-4 h-4 bg-gray-300 cursor-se-resize hover:bg-gray-400"
            style={{
              clipPath: 'polygon(100% 0%, 0% 100%, 100% 100%)'
            }}
            onMouseDown={handleResizeStart}
          />
        )}
      </div>
    </div>
  );
}