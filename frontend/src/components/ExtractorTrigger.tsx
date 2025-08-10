import React from 'react';
import { useState, useEffect } from 'react';
import { extractionApi, projectApi, fileApi } from '../services/api';
import { AvailableExtractors, ExtractionResponse, UploadedFile } from '../types/api';

interface ExtractorTriggerProps {
  projectId?: number;
  fileId?: number;
  fileIds?: number[];
  onExtractionComplete: (result: ExtractionResponse) => void;
}

const ExtractorTrigger: React.FC<ExtractorTriggerProps> = ({ 
  projectId, 
  fileId, 
  fileIds,
  onExtractionComplete 
}: ExtractorTriggerProps) => {
  const [availableExtractors, setAvailableExtractors] = useState<AvailableExtractors | null>(null);
  const [selectedMethods, setSelectedMethods] = useState<string[]>([]);
  const [isExtracting, setIsExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentFile, setCurrentFile] = useState<string | null>(null);
  const [currentExtractor, setCurrentExtractor] = useState<string | null>(null);
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [extractionLogs, setExtractionLogs] = useState<string[]>([]);

  useEffect(() => {
    loadAvailableExtractors();
  }, []);

  // 이전 선택 복원
  useEffect(() => {
    const savedSelection = localStorage.getItem('extractorSelection');
    if (savedSelection) {
      try {
        const parsed = JSON.parse(savedSelection);
        setSelectedMethods(parsed);
      } catch (error) {
        console.error('Failed to parse saved extractor selection:', error);
      }
    }
  }, []);

  // 선택 변경 시 저장
  useEffect(() => {
    if (selectedMethods.length > 0) {
      localStorage.setItem('extractorSelection', JSON.stringify(selectedMethods));
    }
  }, [selectedMethods]);

  const loadAvailableExtractors = async () => {
    try {
      const extractors = await extractionApi.getAvailableExtractors();
      setAvailableExtractors(extractors);
      
      // 저장된 선택이 없는 경우에만 기본 추출기 설정
      const savedSelection = localStorage.getItem('extractorSelection');
      if (!savedSelection) {
        setSelectedMethods(extractors.default_extractors);
      }
    } catch (err: any) {
      setError('추출기 정보를 불러오는데 실패했습니다.');
      console.error(err);
    }
  };

  const handleMethodToggle = (method: string) => {
    setSelectedMethods((prev: string[]) => 
      prev.includes(method)
        ? prev.filter((m: string) => m !== method)
        : [...prev, method]
    );
  };

  const handleExtract = async () => {
    // 추출기 선택 검증 강화
    if (selectedMethods.length === 0) {
      setError('⚠️ 키워드 추출을 위해 최소 하나의 추출기를 선택해주세요.');
      // 시각적 피드백을 위해 추출기 선택 영역으로 스크롤
      const extractorSection = document.querySelector('[data-extractor-selection]');
      if (extractorSection) {
        extractorSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      return;
    }
    
    // 추출기 유효성 추가 확인
    const validExtractors = selectedMethods.filter(method => 
      availableExtractors?.available_extractors.includes(method)
    );
    
    if (validExtractors.length !== selectedMethods.length) {
      setError('⚠️ 선택된 추출기 중 일부가 현재 사용할 수 없습니다. 페이지를 새로고침 후 다시 시도해주세요.');
      return;
    }

    setIsExtracting(true);
    setError(null);
    setCurrentFile(null);
    setCurrentExtractor(null);
    setProgress({ current: 0, total: 0 });
    setExtractionLogs([]);

    const addLog = (message: string) => {
      const timestamp = new Date().toLocaleTimeString();
      const logMessage = `[${timestamp}] ${message}`;
      console.log(logMessage);
      setExtractionLogs(prev => [...prev, logMessage]);
    };

    try {
      let result: ExtractionResponse;
      let targetFiles: UploadedFile[] = [];

      // 대상 파일 결정
      if (fileIds && fileIds.length > 0) {
        // 선택된 파일들
        try {
          const allFiles = await projectApi.getFiles(projectId || 0);
          targetFiles = allFiles.filter(f => fileIds.includes(f.id));
          addLog(`선택된 파일 ${targetFiles.length}개를 대상으로 키워드 추출 시작`);
        } catch (err) {
          console.error('파일 목록 가져오기 실패:', err);
          targetFiles = [];
        }
      } else if (fileId) {
        // 단일 파일
        try {
          const allFiles = await projectApi.getFiles(projectId || 0);
          const file = allFiles.find(f => f.id === fileId);
          if (file) {
            targetFiles = [file];
            addLog(`단일 파일 "${file.filename}"에서 키워드 추출 시작`);
          }
        } catch (err) {
          console.error('파일 정보 가져오기 실패:', err);
          targetFiles = [];
        }
      } else if (projectId) {
        // 프로젝트 전체 파일
        try {
          targetFiles = await projectApi.getFiles(projectId);
          addLog(`프로젝트 전체 파일 ${targetFiles.length}개에서 키워드 추출 시작`);
        } catch (err) {
          console.error('프로젝트 파일 목록 가져오기 실패:', err);
          targetFiles = [];
        }
      }

      // 총 작업 수 계산: 파일 수 × 추출기 수
      const totalTasks = targetFiles.length * selectedMethods.length;
      setProgress({ current: 0, total: totalTasks });
      
      addLog(`총 ${targetFiles.length}개 파일 × ${selectedMethods.length}개 추출기 = ${totalTasks}개 작업`);
      addLog(`선택된 추출기: ${selectedMethods.join(', ')}`);

      let totalKeywords = 0;
      const allKeywords: any[] = [];
      const extractorsUsed: string[] = [];
      let currentTaskIndex = 0;

      // 각 파일에 대해 각 추출기로 순차 처리
      for (let fileIndex = 0; fileIndex < targetFiles.length; fileIndex++) {
        const file = targetFiles[fileIndex];
        setCurrentFile(file.filename);
        addLog(`\n파일 "${file.filename}" 처리 시작 (${fileIndex + 1}/${targetFiles.length})`);

        for (let extractorIndex = 0; extractorIndex < selectedMethods.length; extractorIndex++) {
          const extractor = selectedMethods[extractorIndex];
          setCurrentExtractor(extractor);
          currentTaskIndex++;
          
          addLog(`  - ${extractor} 추출기로 처리 중... (${currentTaskIndex}/${totalTasks})`);
          setProgress({ current: currentTaskIndex, total: totalTasks });

          try {
            // 단일 추출기로 파일 처리
            const fileResult = await fileApi.extractKeywords(file.id, [extractor]);
            
            const extractedCount = fileResult.total_keywords;
            totalKeywords += extractedCount;
            allKeywords.push(...fileResult.keywords);
            
            // 사용된 추출기 목록 합치기
            fileResult.extractors_used.forEach(usedExtractor => {
              if (!extractorsUsed.includes(usedExtractor)) {
                extractorsUsed.push(usedExtractor);
              }
            });

            addLog(`    ✓ ${extractor}: ${extractedCount}개 키워드 추출 완료`);
            
            // 추출된 키워드 로그 (처음 5개만)
            if (fileResult.keywords && fileResult.keywords.length > 0) {
              const sampleKeywords = fileResult.keywords.slice(0, 5).map((kw: any) => kw.keyword || kw.text).join(', ');
              addLog(`    키워드 예시: ${sampleKeywords}${fileResult.keywords.length > 5 ? ` (외 ${fileResult.keywords.length - 5}개 더)` : ''}`);
            }
            
          } catch (err: any) {
            addLog(`    ✗ ${extractor}: 추출 실패 - ${err.message || err}`);
            console.error(`파일 ${file.filename}의 ${extractor} 추출 실패:`, err);
          }
        }
        
        addLog(`파일 "${file.filename}" 처리 완료\n`);
      }

      result = {
        total_keywords: totalKeywords,
        keywords: allKeywords,
        extractors_used: extractorsUsed
      };

      addLog(`\n🎉 전체 키워드 추출 완료!`);
      addLog(`총 키워드 수: ${totalKeywords}개`);
      addLog(`사용된 추출기: ${extractorsUsed.join(', ')}`);

      // 프로젝트 전체일 때는 기존 API 사용 (성능상 이유로)
      if (!fileIds && !fileId && projectId && targetFiles.length > 1) {
        addLog('프로젝트 전체 추출 모드로 전환 (성능 최적화)');
        setCurrentFile('프로젝트 전체 파일');
        setCurrentExtractor('통합 처리');
        setProgress({ current: totalTasks, total: totalTasks });
        result = await projectApi.extractKeywords(projectId, selectedMethods);
        addLog(`프로젝트 전체 추출 완료: ${result.total_keywords}개 키워드`);
      }

      onExtractionComplete(result);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || '키워드 추출에 실패했습니다.';
      setError(errorMessage);
      addLog(`❌ 오류 발생: ${errorMessage}`);
    } finally {
      setIsExtracting(false);
      setCurrentFile(null);
      setCurrentExtractor(null);
      setProgress({ current: 0, total: 0 });
    }
  };

  const getExtractorDisplayName = (method: string): string => {
    const displayNames: { [key: string]: string } = {
      'keybert': 'KeyBERT (의미 기반)',
      'spacy_ner': 'spaCy NER (개체명 인식)',
      'llm': 'LLM (대화형 AI)',
      'konlpy': 'KoNLPy (한국어 형태소)'
    };
    return displayNames[method] || method;
  };

  const getExtractorDescription = (method: string): string => {
    const descriptions: { [key: string]: string } = {
      'keybert': 'BERT 임베딩을 사용한 의미 기반 키워드 추출',
      'spacy_ner': '개체명 인식을 통한 인명, 기관명, 장소명 등 추출',
      'llm': 'LLM을 활용한 맥락적 키워드 및 주제 추출',
      'konlpy': '한국어 형태소 분석을 통한 명사 기반 키워드 추출'
    };
    return descriptions[method] || '';
  };

  if (!availableExtractors) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-md">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-2">
            <div className="h-10 bg-gray-200 rounded"></div>
            <div className="h-10 bg-gray-200 rounded"></div>
            <div className="h-10 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  const getExtractionTitle = () => {
    if (fileIds && fileIds.length > 0) {
      return `선택된 파일 키워드 추출 (${fileIds.length}개 파일)`;
    } else if (fileId) {
      return '파일 키워드 추출';
    } else if (projectId) {
      return '프로젝트 키워드 추출';
    }
    return '키워드 추출';
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4">{getExtractionTitle()}</h3>
      
      <div className="space-y-4">
        <div data-extractor-selection>
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-medium text-gray-700">추출 방법 선택</h4>
            <span className="text-xs text-gray-500">
              {selectedMethods.length}개 선택됨 / 총 {availableExtractors.available_extractors.length}개
            </span>
          </div>
          <div className="space-y-3">
            {availableExtractors.available_extractors.map((method: string) => {
              const isSelected = selectedMethods.includes(method);
              const isDefault = availableExtractors.default_extractors.includes(method);
              
              return (
                <label 
                  key={method} 
                  className={`flex items-start space-x-3 cursor-pointer p-3 rounded-lg border transition-colors ${
                    isSelected 
                      ? 'border-blue-200 bg-blue-50' 
                      : 'border-gray-200 hover:bg-gray-50'
                  } ${isExtracting ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => handleMethodToggle(method)}
                    className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    disabled={isExtracting}
                  />
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <div className="text-sm font-medium text-gray-900">
                        {getExtractorDisplayName(method)}
                      </div>
                      {isDefault && (
                        <span className="text-xs px-2 py-0.5 bg-green-100 text-green-800 rounded-full">
                          기본
                        </span>
                      )}
                      {isSelected && (
                        <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-800 rounded-full">
                          선택됨
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {getExtractorDescription(method)}
                    </div>
                  </div>
                </label>
              );
            })}
          </div>
        </div>

        {availableExtractors.available_extractors.length === 0 && (
          <div className="text-yellow-600 text-sm bg-yellow-50 p-3 rounded-md">
            사용 가능한 추출기가 없습니다. 서버 설정을 확인해주세요.
          </div>
        )}

        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-500">
            선택된 추출기: {selectedMethods.length}개
          </div>
          <button
            onClick={handleExtract}
            disabled={isExtracting || selectedMethods.length === 0 || availableExtractors.available_extractors.length === 0}
            className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {isExtracting ? '추출 중...' : '키워드 추출 시작'}
          </button>
        </div>

        {error && (
          <div className="text-red-600 text-sm bg-red-50 p-3 rounded-md">
            {error}
          </div>
        )}

        {isExtracting && (
          <div className="bg-blue-50 p-4 rounded-md">
            <div className="space-y-3">
              {/* 진행률 바 */}
              {progress.total > 0 && (
                <div>
                  <div className="flex items-center justify-between text-sm text-blue-800 mb-2">
                    <span>진행률</span>
                    <span>{progress.current}/{progress.total} ({Math.round((progress.current / progress.total) * 100)}%)</span>
                  </div>
                  <div className="w-full bg-blue-200 rounded-full h-2">
                    <div 
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
                      style={{ width: `${(progress.current / progress.total) * 100}%` }}
                    ></div>
                  </div>
                </div>
              )}
              
              {/* 현재 처리 중인 파일 및 추출기 */}
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                <div className="text-sm text-blue-800">
                  {currentFile ? (
                    <div>
                      <div>키워드 추출 중입니다...</div>
                      <div className="font-medium mt-1">파일: {currentFile}</div>
                      {currentExtractor && (
                        <div className="text-xs mt-1">추출기: {getExtractorDisplayName(currentExtractor)}</div>
                      )}
                    </div>
                  ) : (
                    '키워드 추출을 준비하고 있습니다...'
                  )}
                </div>
              </div>
              
              {/* 진행률이 있는 경우 예상 시간 또는 상태 메시지 */}
              {progress.total > 1 && progress.current > 0 && (
                <div className="text-xs text-blue-700">
                  {progress.current === progress.total ? 
                    '추출 완료 처리 중...' : 
                    `남은 작업: ${progress.total - progress.current}개`
                  }
                </div>
              )}
              
              {/* 추출 로그 */}
              {extractionLogs.length > 0 && (
                <div className="mt-4">
                  <details className="cursor-pointer">
                    <summary className="text-xs text-blue-700 font-medium mb-2">추출 로그 보기</summary>
                    <div className="bg-gray-900 text-gray-100 p-3 rounded text-xs font-mono max-h-40 overflow-y-auto">
                      {extractionLogs.map((log, index) => (
                        <div key={index} className="mb-1">
                          {log}
                        </div>
                      ))}
                    </div>
                  </details>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ExtractorTrigger;