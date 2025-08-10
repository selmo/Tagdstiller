import React, { useState, useEffect, useCallback } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { UploadedFile } from '../types/api';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';

// PDF.js worker 설정 - 로컬 public 폴더의 worker 파일 사용
pdfjs.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.js';

console.log('PDF.js version:', pdfjs.version);
console.log('Worker URL:', pdfjs.GlobalWorkerOptions.workerSrc);

const API_BASE_URL = 'http://localhost:58000';

interface AdvancedPDFViewerProps {
  file: UploadedFile;
  keywords: string[];
  targetPosition?: { page?: number; line?: number; column?: number };
  onClose: () => void;
}

interface TextMatch {
  pageNumber: number;
  x: number;
  y: number;
  width: number;
  height: number;
  text: string;
}

export default function AdvancedPDFViewer({ 
  file, 
  keywords, 
  targetPosition,
  onClose 
}: AdvancedPDFViewerProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [scale, setScale] = useState<number>(1.2);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [textMatches, setTextMatches] = useState<TextMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // PDF URL 생성
  useEffect(() => {
    const fetchPDF = async () => {
      try {
        console.log('PDF 다운로드 시작:', file.filename, file.id);
        const response = await fetch(`${API_BASE_URL}/projects/${file.id}/download`);
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const blob = await response.blob();
        console.log('PDF 블롭 생성:', blob.size, 'bytes, 타입:', blob.type);
        
        if (blob.size === 0) {
          throw new Error('빈 PDF 파일입니다.');
        }
        
        // MIME 타입 검증 및 수정
        let pdfBlob = blob;
        if (!blob.type || !blob.type.includes('pdf')) {
          console.warn('PDF MIME 타입이 올바르지 않음:', blob.type, '-> application/pdf로 변경');
          pdfBlob = new Blob([blob], { type: 'application/pdf' });
        }
        
        const url = URL.createObjectURL(pdfBlob);
        setPdfUrl(url);
        console.log('PDF URL 생성 완료:', url);
        setLoading(false); // URL 생성 후 로딩 상태 해제
        
        return () => {
          URL.revokeObjectURL(url);
        };
      } catch (err) {
        console.error('PDF 다운로드 오류:', err);
        const errorMessage = err instanceof Error ? err.message : 'Unknown error';
        setError(`PDF를 불러올 수 없습니다: ${errorMessage}`);
        setLoading(false);
      }
    };
    
    fetchPDF();
  }, [file.id]);

  // 초기 페이지 설정
  useEffect(() => {
    if (targetPosition?.page) {
      setCurrentPage(targetPosition.page);
    }
  }, [targetPosition]);

  // PDF 로드 후 키워드 검색 실행 (한 번만)
  useEffect(() => {
    if (numPages > 0 && keywords.length > 0 && pdfUrl && !loading) {
      console.log('키워드 검색 실행 조건 충족');
      const timer = setTimeout(() => searchKeywordsInPDF(), 500);
      return () => clearTimeout(timer);
    }
  }, [numPages, pdfUrl]); // keywords와 loading 제거하여 재실행 방지

  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    console.log('PDF 로드 성공! 페이지 수:', numPages);
    setNumPages(numPages);
    setLoading(false);
  }, []);
  
  const onDocumentLoadError = (error: Error) => {
    console.error('PDF 로드 실패:', error);
    setError(`PDF 로드 실패: ${error.message}`);
    setLoading(false);
  };

  const searchKeywordsInPDF = async () => {
    if (!pdfUrl || keywords.length === 0 || numPages === 0) {
      console.log('키워드 검색 조건 불충족:', { pdfUrl: !!pdfUrl, keywordsLength: keywords.length, numPages });
      return;
    }
    
    try {
      console.log('키워드 검색 시작:', keywords);
      const pdf = await pdfjs.getDocument(pdfUrl).promise;
      const matches: TextMatch[] = [];
      
      // 최대 5페이지까지만 검색 (성능 최적화)
      const maxPages = Math.min(pdf.numPages, 5);
      
      for (let pageNum = 1; pageNum <= maxPages; pageNum++) {
        try {
          const page = await pdf.getPage(pageNum);
          const textContent = await page.getTextContent();
          const viewport = page.getViewport({ scale: 1.0 }); // 기본 스케일로 계산
          
          console.log(`페이지 ${pageNum} 텍스트 항목 수:`, textContent.items.length);
          
          // 각 텍스트 항목에서 키워드 검색 (최대 100개 항목만)
          const maxItems = Math.min(textContent.items.length, 100);
          
          for (let i = 0; i < maxItems; i++) {
            const textItem = textContent.items[i] as any;
            const text = textItem.str || '';
            if (!text.trim()) continue;
            
            for (const keyword of keywords) {
              const keywordLower = keyword.toLowerCase();
              const textLower = text.toLowerCase();
              
              if (textLower.includes(keywordLower)) {
                try {
                  // transform 행렬에서 위치 정보 추출
                  const transform = textItem.transform;
                  if (!transform || transform.length < 6) continue;
                  
                  const x = transform[4];
                  const y = transform[5];
                  const scaleX = Math.abs(transform[0]) || 12;
                  const scaleY = Math.abs(transform[3]) || 12;
                  
                  // viewport를 통한 좌표 변환
                  const [viewX, viewY] = viewport.convertToViewportPoint(x, y);
                  
                  // 텍스트 크기 계산
                  const textWidth = text.length * scaleX * 0.6;
                  const textHeight = scaleY;
                  
                  matches.push({
                    pageNumber: pageNum,
                    x: viewX * scale,
                    y: (viewY - textHeight) * scale,
                    width: textWidth * scale,
                    height: textHeight * scale,
                    text: keyword
                  });
                  
                  console.log(`키워드 "${keyword}" 발견 - 페이지 ${pageNum}, 위치: (${(viewX * scale).toFixed(1)}, ${((viewY - textHeight) * scale).toFixed(1)})`);
                } catch (itemError) {
                  console.warn('텍스트 항목 처리 오류:', itemError);
                }
              }
            }
          }
        } catch (pageError) {
          console.warn(`페이지 ${pageNum} 처리 오류:`, pageError);
        }
      }
      
      setTextMatches(matches);
      console.log(`PDF에서 총 ${matches.length}개의 키워드 매치 발견`);
      
    } catch (error) {
      console.error('PDF 키워드 검색 실패:', error);
      setTextMatches([]); // 에러 시 빈 배열로 설정
    }
  };

  const goToPreviousPage = () => {
    setCurrentPage(prev => Math.max(1, prev - 1));
  };

  const goToNextPage = () => {
    setCurrentPage(prev => Math.min(numPages, prev + 1));
  };

  const zoomIn = () => {
    setScale(prev => Math.min(3.0, prev + 0.2));
  };

  const zoomOut = () => {
    setScale(prev => Math.max(0.5, prev - 0.2));
  };

  const goToNextMatch = () => {
    const currentPageMatches = textMatches.filter(m => m.pageNumber >= currentPage);
    if (currentPageMatches.length > 0) {
      const nextMatch = currentPageMatches[0];
      if (nextMatch.pageNumber !== currentPage) {
        setCurrentPage(nextMatch.pageNumber);
      }
    }
  };

  const goToPreviousMatch = () => {
    const previousPageMatches = textMatches.filter(m => m.pageNumber <= currentPage);
    if (previousPageMatches.length > 0) {
      const prevMatch = previousPageMatches[previousPageMatches.length - 1];
      if (prevMatch.pageNumber !== currentPage) {
        setCurrentPage(prevMatch.pageNumber);
      }
    }
  };

  if (error) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-30 z-50 flex items-center justify-center">
        <div className="bg-white p-6 rounded-lg max-w-md">
          <div className="text-red-600 text-center">
            <p className="text-xl mb-2">⚠️</p>
            <p>{error}</p>
            <button
              onClick={onClose}
              className="mt-4 px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
            >
              닫기
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-30 z-50">
      <div className="bg-white h-full flex flex-col">
        {/* 헤더 */}
        <div className="flex items-center justify-between p-4 border-b bg-gray-50">
          <div className="flex items-center space-x-4">
            <h2 className="text-lg font-semibold">{file.filename}</h2>
            {keywords.length > 0 && (
              <div className="flex items-center space-x-2">
                <span className="text-sm bg-green-100 text-green-800 px-2 py-1 rounded">
                  🔍 {keywords.join(', ')}
                </span>
                <span className="text-xs text-gray-600">
                  {textMatches.length}개 발견
                </span>
                {textMatches.length > 0 && (
                  <div className="flex items-center space-x-1">
                    <button
                      onClick={goToPreviousMatch}
                      className="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded hover:bg-yellow-200"
                    >
                      ◀ 이전 매치
                    </button>
                    <button
                      onClick={goToNextMatch}
                      className="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded hover:bg-yellow-200"
                    >
                      다음 매치 ▶
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl"
          >
            ×
          </button>
        </div>

        {/* 컨트롤 바 */}
        <div className="flex items-center justify-between p-4 border-b bg-gray-50">
          <div className="flex items-center space-x-4">
            <button
              onClick={goToPreviousPage}
              disabled={currentPage <= 1}
              className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
            >
              ◀ 이전
            </button>
            <span className="text-sm">
              {currentPage} / {numPages}
            </span>
            <button
              onClick={goToNextPage}
              disabled={currentPage >= numPages}
              className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
            >
              다음 ▶
            </button>
          </div>
          
          <div className="flex items-center space-x-4">
            <button
              onClick={zoomOut}
              className="px-3 py-1 bg-gray-600 text-white rounded hover:bg-gray-700"
            >
              축소
            </button>
            <span className="text-sm">{Math.round(scale * 100)}%</span>
            <button
              onClick={zoomIn}
              className="px-3 py-1 bg-gray-600 text-white rounded hover:bg-gray-700"
            >
              확대
            </button>
          </div>
        </div>

        {/* PDF 컨텐츠 */}
        <div className="flex-1 overflow-auto bg-gray-100 p-4">
          {loading && !pdfUrl ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p>PDF를 불러오는 중...</p>
                <p className="text-sm text-gray-500 mt-2">서버에서 PDF 다운로드 중...</p>
              </div>
            </div>
          ) : pdfUrl ? (
            <div className="flex justify-center">
              <div className="relative">
                {pdfUrl && (
                  <Document
                    file={pdfUrl}
                    onLoadSuccess={onDocumentLoadSuccess}
                    onLoadError={onDocumentLoadError}
                    loading={
                      <div className="text-center">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
                        <p>PDF 문서 로딩 중...</p>
                        <p className="text-xs text-gray-500 mt-1">시간이 오래 걸리면 페이지를 새로고침하세요</p>
                      </div>
                    }
                    error={
                      <div className="text-red-600 text-center">
                        <p>PDF 로드 실패</p>
                        <p className="text-sm mt-2">브라우저 콘솔을 확인하세요</p>
                        <button
                          onClick={() => window.location.reload()}
                          className="mt-2 px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
                        >
                          페이지 새로고침
                        </button>
                      </div>
                    }
                  >
                    <Page
                      pageNumber={currentPage}
                      scale={scale}
                      renderTextLayer={true}
                      renderAnnotationLayer={true}
                      className="shadow-lg"
                      loading={
                        <div className="text-center p-4">
                          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto mb-2"></div>
                          <p className="text-sm">페이지 로딩 중...</p>
                        </div>
                      }
                      error={
                        <div className="text-red-600 text-center p-4">
                          <p>페이지 로드 실패</p>
                        </div>
                      }
                    />
                  </Document>
                )}
                
                {/* 키워드 하이라이트 오버레이 */}
                {textMatches
                  .filter(match => match.pageNumber === currentPage)
                  .map((match, index) => (
                    <div
                      key={`highlight-${index}`}
                      className="absolute pointer-events-none border border-orange-400 z-10"
                      style={{
                        left: match.x,
                        top: match.y,
                        width: match.width,
                        height: match.height,
                        backgroundColor: 'rgba(255, 235, 59, 0.4)',
                        borderRadius: '2px',
                      }}
                      title={`키워드: ${match.text}`}
                    />
                  ))}
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center text-gray-500">
                <p>PDF를 로드할 수 없습니다.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}