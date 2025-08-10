import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { FileText, Download, X, ChevronLeft, ChevronRight, ZoomIn, ZoomOut, RotateCw } from 'lucide-react';
import { UploadedFile } from '../types/api';

const API_BASE_URL = 'http://localhost:58000';

interface DocumentViewerProps {
  file: UploadedFile;
  selectedKeywords?: string[];
  onClose: () => void;
}

export default function DocumentViewer({ file, selectedKeywords = [], onClose }: DocumentViewerProps) {
  // selectedKeywords가 배열인지 확인하고 문자열 배열로 변환
  const safeKeywords = Array.isArray(selectedKeywords) 
    ? selectedKeywords.map(k => typeof k === 'string' ? k : String(k)).filter(Boolean)
    : [];
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fileType, setFileType] = useState<string>('');
  const [highlightKeywords, setHighlightKeywords] = useState(true);
  const [selectedKeyword, setSelectedKeyword] = useState<string | null>(null);
  
  // PDF specific states
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  // const [totalPages, setTotalPages] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [rotation, setRotation] = useState(0);

  useEffect(() => {
    fetchFileContent();
    return () => {
      if (pdfUrl) {
        URL.revokeObjectURL(pdfUrl);
      }
    };
  }, [file.id]);

  const fetchFileContent = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Determine file type from filename
      const extension = file.filename.split('.').pop()?.toLowerCase() || '';
      setFileType(extension);
      
      if (extension === 'pdf') {
        // For PDF files, fetch as blob for download endpoint
        const response = await axios.get(`${API_BASE_URL}/files/${file.id}/download`, {
          responseType: 'blob'
        });
        const url = URL.createObjectURL(response.data);
        setPdfUrl(url);
      } else {
        // For other files, fetch as text
        const response = await axios.get(`${API_BASE_URL}/files/${file.id}/content`);
        setContent(response.data.content || '');
      }
    } catch (err) {
      console.error('Error fetching file content:', err);
      setError('파일 내용을 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const highlightText = (text: string): string => {
    if (!highlightKeywords || safeKeywords.length === 0) return text;
    
    let highlightedText = text;
    
    safeKeywords.forEach((keyword, index) => {
      if (!keyword) return;
      
      // 정규식에서 특수문자 이스케이프
      const escapedKeyword = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const regex = new RegExp(`(${escapedKeyword})`, 'gi');
      const color = getKeywordColor(index);
      highlightedText = highlightedText.replace(
        regex,
        `<span class="highlighted-keyword" style="background-color: ${color}; padding: 2px 4px; border-radius: 3px; font-weight: 500;">$1</span>`
      );
    });
    
    return highlightedText;
  };

  const getKeywordColor = (index: number): string => {
    const colors = [
      'rgba(59, 130, 246, 0.3)', // blue
      'rgba(34, 197, 94, 0.3)',  // green
      'rgba(168, 85, 247, 0.3)', // purple
      'rgba(251, 146, 60, 0.3)', // orange
      'rgba(236, 72, 153, 0.3)', // pink
      'rgba(250, 204, 21, 0.3)', // yellow
      'rgba(14, 165, 233, 0.3)', // sky
      'rgba(220, 38, 38, 0.3)',  // red
    ];
    return colors[index % colors.length];
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

    switch (fileType) {
      case 'pdf':
        return (
          <div className="flex flex-col h-full">
            <div className="flex items-center justify-between p-4 border-b bg-gray-50">
              <div className="flex items-center space-x-4">
                <button
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                  className="p-2 rounded hover:bg-gray-200 disabled:opacity-50"
                >
                  <ChevronLeft size={20} />
                </button>
                <span className="text-sm">
                  {currentPage} / 1
                </span>
                <button
                  onClick={() => setCurrentPage(Math.min(1, currentPage + 1))}
                  disabled={currentPage === 1}
                  className="p-2 rounded hover:bg-gray-200 disabled:opacity-50"
                >
                  <ChevronRight size={20} />
                </button>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setScale(Math.max(0.5, scale - 0.1))}
                  className="p-2 rounded hover:bg-gray-200"
                >
                  <ZoomOut size={20} />
                </button>
                <span className="text-sm w-16 text-center">{Math.round(scale * 100)}%</span>
                <button
                  onClick={() => setScale(Math.min(2, scale + 0.1))}
                  className="p-2 rounded hover:bg-gray-200"
                >
                  <ZoomIn size={20} />
                </button>
                <button
                  onClick={() => setRotation((rotation + 90) % 360)}
                  className="p-2 rounded hover:bg-gray-200"
                >
                  <RotateCw size={20} />
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-auto p-4 bg-gray-100">
              {pdfUrl && (
                <iframe
                  src={`${pdfUrl}#page=${currentPage}`}
                  title={`PDF Viewer - ${file.filename}`}
                  className="w-full h-full border-0 bg-white shadow-lg"
                  style={{
                    transform: `scale(${scale}) rotate(${rotation}deg)`,
                    transformOrigin: 'top left',
                    width: `${100 / scale}%`,
                    height: `${100 / scale}%`,
                  }}
                />
              )}
            </div>
          </div>
        );

      case 'md':
        return (
          <div className="p-6 overflow-auto">
            <div 
              className="prose prose-lg max-w-none"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
            />
          </div>
        );

      case 'html':
        return (
          <div className="p-6 overflow-auto">
            <div 
              className="prose prose-lg max-w-none"
              dangerouslySetInnerHTML={{ __html: highlightText(content) }}
            />
          </div>
        );

      case 'docx':
        return (
          <div className="p-6 overflow-auto">
            <div className="bg-white p-8 shadow-inner rounded">
              <div 
                className="whitespace-pre-wrap font-serif text-gray-800"
                dangerouslySetInnerHTML={{ __html: highlightText(content) }}
              />
            </div>
          </div>
        );

      default:
        return (
          <div className="p-6 overflow-auto">
            <pre 
              className="whitespace-pre-wrap font-mono text-sm"
              dangerouslySetInnerHTML={{ __html: highlightText(content) }}
            />
          </div>
        );
    }
  };

  const renderMarkdown = (markdown: string): string => {
    // Simple markdown to HTML conversion
    let html = markdown
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      .replace(/^\* (.*$)/gim, '<li>$1</li>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/\*([^*]+)\*/g, '<em>$1</em>')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-blue-600 hover:underline">$1</a>')
      .replace(/\n\n/g, '</p><p>')
      .replace(/^/, '<p>')
      .replace(/$/, '</p>');
    
    // Wrap lists
    html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    
    return highlightText(html);
  };

  // 안전성 체크
  if (!file || !file.filename) {
    return null;
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-11/12 h-5/6 max-w-6xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center space-x-3">
            <FileText className="text-gray-600" size={24} />
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
              href={`${API_BASE_URL}/files/${file.id}/download`}
              className="flex items-center space-x-2 px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              <Download size={16} />
              <span>다운로드</span>
            </a>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-full"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Keyword pills */}
        {safeKeywords.length > 0 && highlightKeywords && (
          <div className="px-4 py-2 border-b bg-gray-50 flex flex-wrap gap-2">
            <span className="text-sm text-gray-600 mr-2">키워드:</span>
            {safeKeywords.map((keyword, index) => (
              <span
                key={keyword}
                className="px-3 py-1 text-xs rounded-full cursor-pointer transition-all"
                style={{
                  backgroundColor: selectedKeyword === keyword 
                    ? getKeywordColor(index).replace('0.3', '0.6')
                    : getKeywordColor(index),
                  border: selectedKeyword === keyword ? '2px solid #333' : 'none'
                }}
                onClick={() => setSelectedKeyword(selectedKeyword === keyword ? null : keyword)}
              >
                {keyword}
              </span>
            ))}
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          {renderContent()}
        </div>
      </div>
    </div>
  );
}