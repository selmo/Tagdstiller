import React, { useState, useEffect } from 'react';
import { configApi } from '../services/api';
import { Config, KeyBERTModelsResponse, KeyBERTModel } from '../types/api';

interface SettingsPanelProps {
  onClose: () => void;
  inline?: boolean;
}

interface LLMConnectionTest {
  status: 'idle' | 'testing' | 'success' | 'error';
  message: string;
  provider?: string;
  model?: string;
  base_url?: string;
  test_keywords?: string[];
}

interface OllamaModel {
  name: string;
  display_name: string;
  size: number;
  size_gb: number;
  modified_at: string;
}

interface OllamaModelsResponse {
  status: 'success' | 'error';
  message?: string;
  base_url: string;
  models: OllamaModel[];
  total_models: number;
}

const SettingsPanel: React.FC<SettingsPanelProps> = ({ onClose, inline = false }) => {
  const [configs, setConfigs] = useState<Config[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [connectionTest, setConnectionTest] = useState<LLMConnectionTest>({
    status: 'idle',
    message: ''
  });
  const [ollamaModels, setOllamaModels] = useState<OllamaModel[]>([]);
  const [ollamaModelsLoading, setOllamaModelsLoading] = useState(false);
  const [keyBERTModels, setKeyBERTModels] = useState<KeyBERTModelsResponse | null>(null);
  const [keyBERTModelsLoading, setKeyBERTModelsLoading] = useState(false);
  const [pendingChanges, setPendingChanges] = useState<Record<string, string>>({});
  const [hasChanges, setHasChanges] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState<{[key: string]: {
    progress: number;
    message: string;
    status: string;
  }}>({});
  
  // 설정 카테고리별 분류
  const [extractorBaseSettings, setExtractorBaseSettings] = useState<Config[]>([]);
  const [keyBERTSettings, setKeyBERTSettings] = useState<Config[]>([]);
  const [nerSettings, setNERSettings] = useState<Config[]>([]);
  const [llmSettings, setLLMSettings] = useState<Config[]>([]);
  const [konlpySettings, setKonlpySettings] = useState<Config[]>([]);
  const [ollamaSettings, setOllamaSettings] = useState<Config[]>([]);
  const [fileSettings, setFileSettings] = useState<Config[]>([]);
  const [appSettings, setAppSettings] = useState<Config[]>([]);
  
  // 탭 상태 관리
  const [activeExtractorTab, setActiveExtractorTab] = useState<'keybert' | 'ner' | 'llm' | 'konlpy'>('keybert');
  
  // 탭 스타일 헬퍼 함수
  const getTabButtonClass = (tabKey: string, color: string, isActive: boolean) => {
    const baseClass = "py-2 px-1 border-b-2 font-medium text-sm transition-colors duration-200";
    
    if (isActive) {
      const activeClasses = {
        blue: "border-blue-500 text-blue-600",
        green: "border-green-500 text-green-600", 
        purple: "border-purple-500 text-purple-600",
        orange: "border-orange-500 text-orange-600"
      };
      return `${baseClass} ${activeClasses[color as keyof typeof activeClasses]}`;
    } else {
      return `${baseClass} border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300`;
    }
  };
  
  const getTabCountClass = (color: string, isActive: boolean) => {
    const baseClass = "ml-2 px-2 py-1 text-xs rounded-full";
    
    if (isActive) {
      const activeClasses = {
        blue: "bg-blue-100 text-blue-800",
        green: "bg-green-100 text-green-800",
        purple: "bg-purple-100 text-purple-800", 
        orange: "bg-orange-100 text-orange-800"
      };
      return `${baseClass} ${activeClasses[color as keyof typeof activeClasses]}`;
    } else {
      return `${baseClass} bg-gray-100 text-gray-600`;
    }
  };

  useEffect(() => {
    loadConfigs();
    // Ollama 모델 목록을 자동으로 로드
    loadOllamaModels();
    // KeyBERT 모델 목록 로드
    loadKeyBERTModels();
  }, []);

  const loadConfigs = async () => {
    try {
      setLoading(true);
      const configData = await configApi.getAll();
      setConfigs(configData);
      
      // 카테고리별로 세분화하여 분류
      setExtractorBaseSettings(configData.filter(c => 
        c.key === 'DEFAULT_EXTRACTORS' ||
        c.key === 'MAX_KEYWORDS_PER_DOCUMENT'
      ));
      
      setKeyBERTSettings(configData.filter(c => 
        c.key.startsWith('extractor.keybert.')
      ));
      
      setNERSettings(configData.filter(c => 
        c.key.startsWith('extractor.ner.')
      ));
      
      // LLM 설정 (OpenAI 제외)
      setLLMSettings(configData.filter(c => 
        c.key.startsWith('OLLAMA_') ||
        c.key === 'ENABLE_LLM_EXTRACTION'
      ));
      
      setKonlpySettings(configData.filter(c => 
        c.key.startsWith('extractor.konlpy.')
      ));
      
      // Ollama 설정은 LLM 탭으로 통합됨
      setOllamaSettings([]);
      
      setFileSettings(configData.filter(c => 
        c.key === 'ALLOWED_EXTENSIONS' ||
        c.key === 'FILE_MAX_SIZE_MB'
      ));
      
      setAppSettings(configData.filter(c => 
        c.key.startsWith('APP_')
      ));
    } catch (error) {
      console.error('설정 로드 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateConfig = (key: string, value: string) => {
    // 변경사항을 임시로 저장
    setPendingChanges(prev => ({
      ...prev,
      [key]: value
    }));
    setHasChanges(true);
    
    // 로컬 상태 업데이트 (UI 반영용)
    setConfigs(prev => prev.map(config => 
      config.key === key ? { ...config, value } : config
    ));
    
    // 카테고리별 상태도 업데이트
    const updateCategoryState = (setState: React.Dispatch<React.SetStateAction<Config[]>>) => {
      setState(prev => prev.map(config => 
        config.key === key ? { ...config, value } : config
      ));
    };
    
    if (key === 'DEFAULT_EXTRACTORS' || key === 'MAX_KEYWORDS_PER_DOCUMENT') {
      updateCategoryState(setExtractorBaseSettings);
    } else if (key.startsWith('extractor.keybert.')) {
      updateCategoryState(setKeyBERTSettings);
    } else if (key.startsWith('extractor.ner.')) {
      updateCategoryState(setNERSettings);
    } else if (key.startsWith('OLLAMA_') || key === 'ENABLE_LLM_EXTRACTION') {
      updateCategoryState(setLLMSettings);
    } else if (key.startsWith('extractor.konlpy.')) {
      updateCategoryState(setKonlpySettings);
    } else if (key === 'ALLOWED_EXTENSIONS' || key === 'FILE_MAX_SIZE_MB') {
      updateCategoryState(setFileSettings);
    } else if (key.startsWith('APP_')) {
      updateCategoryState(setAppSettings);
    }
  };

  const saveAllChanges = async () => {
    try {
      setSaving(true);
      
      // KeyBERT 모델 변경사항 확인
      const keyBERTModelChange = pendingChanges['extractor.keybert.model'];
      
      // 모든 변경사항을 병렬로 저장
      const savePromises = Object.entries(pendingChanges).map(([key, value]) =>
        configApi.update(key, { value })
      );
      
      await Promise.all(savePromises);
      
      // KeyBERT 모델이 변경된 경우 다운로드 처리
      if (keyBERTModelChange) {
        try {
          const modelName = keyBERTModelChange;
          console.log(`KeyBERT 모델 다운로드 시작: ${modelName}`);
          
          // 모델 상태 확인
          const statusResponse = await fetch(`http://localhost:58000/configs/keybert/models/${encodeURIComponent(modelName)}/status`);
          const statusData = await statusResponse.json();
          
          if (statusData.status === 'success' && !statusData.is_cached) {
            // 모델이 캐시되지 않은 경우 다운로드
            console.log(`모델 '${modelName}' 다운로드 필요`);
            
            const downloadResponse = await fetch(`http://localhost:58000/configs/keybert/models/${encodeURIComponent(modelName)}/download`, {
              method: 'POST'
            });
            const downloadData = await downloadResponse.json();
            
            if (downloadData.status === 'success') {
              // 진행률 추적 시작
              if (downloadData.progress_key) {
                trackDownloadProgress(downloadData.progress_key, modelName);
              }
              
              const action = downloadData.was_cached ? '로드' : '다운로드';
              const sizeInfo = downloadData.model_size_mb ? ` (${downloadData.model_size_mb}MB)` : '';
              console.log(`모델 '${modelName}' ${action} 완료 (${downloadData.download_time_seconds}초 소요)`);
              
              // 진행률이 있으면 alert를 표시하지 않음 (진행률로 대체)
              if (!downloadData.progress_key) {
                alert(`KeyBERT 모델 '${modelName}'이 성공적으로 ${action}되었습니다.\n소요시간: ${downloadData.download_time_seconds}초${sizeInfo}`);
              }
            } else {
              console.error(`모델 다운로드 실패: ${downloadData.message}`);
              alert(`KeyBERT 모델 다운로드에 실패했습니다: ${downloadData.message}`);
            }
          } else if (statusData.is_cached) {
            console.log(`모델 '${modelName}'은 이미 다운로드되어 있습니다 (${statusData.total_size_mb}MB)`);
          }
        } catch (modelError) {
          console.error('KeyBERT 모델 처리 중 오류:', modelError);
          alert('KeyBERT 모델 처리 중 오류가 발생했습니다. 모델은 필요 시 자동으로 다운로드됩니다.');
        }
      }
      
      // 저장 성공 시 변경사항 초기화
      setPendingChanges({});
      setHasChanges(false);
      
      // 설정 다시 로드하여 동기화
      await loadConfigs();
      
      alert('설정이 성공적으로 저장되었습니다.');
    } catch (error) {
      console.error('설정 저장 실패:', error);
      alert('설정 저장에 실패했습니다. 다시 시도해주세요.');
    } finally {
      setSaving(false);
    }
  };

  const discardChanges = () => {
    if (hasChanges) {
      if (window.confirm('저장하지 않은 변경사항이 있습니다. 정말 취소하시겠습니까?')) {
        setPendingChanges({});
        setHasChanges(false);
        loadConfigs();
      }
    }
  };

  // 추출기 활성화 상태 확인 함수
  const isExtractorEnabled = (extractorType: 'keybert' | 'ner' | 'llm' | 'konlpy') => {
    // DEFAULT_EXTRACTORS 또는 extractor.default_method에서 활성화 상태 확인
    const defaultExtractorsConfig = configs.find(c => c.key === 'DEFAULT_EXTRACTORS') || 
                                   extractorBaseSettings.find(c => c.key === 'DEFAULT_EXTRACTORS');
    const defaultMethodConfig = configs.find(c => c.key === 'extractor.default_method') || 
                               extractorBaseSettings.find(c => c.key === 'extractor.default_method');
    
    // 변경사항이 있으면 pendingChanges에서 확인
    const currentDefaultExtractors = pendingChanges['DEFAULT_EXTRACTORS'] || 
                                   (defaultExtractorsConfig ? defaultExtractorsConfig.value : '[]');
    const currentDefaultMethod = pendingChanges['extractor.default_method'] || 
                                (defaultMethodConfig ? defaultMethodConfig.value : '');
    
    try {
      // DEFAULT_EXTRACTORS가 JSON 배열인 경우
      if (currentDefaultExtractors.startsWith('[')) {
        const extractors = JSON.parse(currentDefaultExtractors);
        // ner과 spacy_ner 둘 다 확인
        if (extractorType === 'ner') {
          return extractors.includes('ner') || extractors.includes('spacy_ner');
        }
        return extractors.includes(extractorType);
      }
      
      // extractor.default_method가 단일 값인 경우
      if (currentDefaultMethod === extractorType) {
        return true;
      }
      
      // 쉼표로 구분된 값들인 경우
      const extractors = currentDefaultExtractors.split(',').map((e: string) => e.trim());
      if (extractorType === 'ner') {
        return extractors.includes('ner') || extractors.includes('spacy_ner');
      }
      return extractors.includes(extractorType);
    } catch {
      // 파싱 실패 시 기본값으로 keybert만 활성화
      return extractorType === 'keybert';
    }
  };

  const loadOllamaModels = async () => {
    try {
      setOllamaModelsLoading(true);
      const response = await fetch('http://localhost:58000/llm/ollama/models');
      const result: OllamaModelsResponse = await response.json();
      
      if (result.status === 'success') {
        setOllamaModels(result.models);
      } else {
        console.warn('Ollama 모델 목록 로드 실패:', result.message);
        setOllamaModels([]);
      }
    } catch (error) {
      console.error('Ollama 모델 목록 로드 중 오류:', error);
      setOllamaModels([]);
    } finally {
      setOllamaModelsLoading(false);
    }
  };

  const loadKeyBERTModels = async () => {
    try {
      setKeyBERTModelsLoading(true);
      const result = await configApi.getKeyBERTModels();
      setKeyBERTModels(result);
    } catch (error) {
      console.error('KeyBERT 모델 목록 로드 중 오류:', error);
      setKeyBERTModels(null);
    } finally {
      setKeyBERTModelsLoading(false);
    }
  };

  const trackDownloadProgress = (progressKey: string, modelName: string) => {
    const eventSource = new EventSource(`http://localhost:58000/configs/keybert/models/download/progress/${progressKey}`);
    
    eventSource.onmessage = (event) => {
      try {
        const progressData = JSON.parse(event.data);
        
        setDownloadProgress(prev => ({
          ...prev,
          [modelName]: {
            progress: progressData.progress || 0,
            message: progressData.message || '',
            status: progressData.status || 'unknown'
          }
        }));
        
        // 완료되거나 오류가 발생하면 EventSource 종료
        if (progressData.status === 'completed' || progressData.status === 'error') {
          eventSource.close();
          
          // 3초 후 진행률 표시 제거
          setTimeout(() => {
            setDownloadProgress(prev => {
              const newProgress = { ...prev };
              delete newProgress[modelName];
              return newProgress;
            });
          }, 3000);
        }
      } catch (error) {
        console.error('진행률 파싱 오류:', error);
      }
    };
    
    eventSource.onerror = () => {
      console.warn('진행률 스트림 연결 오류');
      eventSource.close();
    };
    
    // 컴포넌트 언마운트 시 정리
    return () => eventSource.close();
  };

  const testLLMConnection = async () => {
    try {
      setConnectionTest({ status: 'testing', message: 'LLM 서버 연결을 테스트 중입니다...' });
      
      const response = await fetch('http://localhost:58000/llm/test_connection');
      const result = await response.json();
      
      setConnectionTest({
        status: result.status === 'success' ? 'success' : 'error',
        message: result.message,
        provider: result.provider,
        model: result.model,
        base_url: result.base_url,
        test_keywords: result.test_keywords
      });
      
      // 연결 테스트 성공 시 모델 목록도 로드
      if (result.status === 'success') {
        loadOllamaModels();
      }
    } catch (error) {
      setConnectionTest({
        status: 'error',
        message: '연결 테스트 중 오류가 발생했습니다: ' + error
      });
    }
  };

  // 설정 키를 사용자 친화적인 한글 레이블로 변환하는 함수
  const getConfigLabel = (key: string): string => {
    const labels: { [key: string]: string } = {
      // 기본 추출기 설정
      'extractor.default_method': '기본 추출 방법',
      'DEFAULT_EXTRACTORS': '기본 추출기',
      'MAX_KEYWORDS_PER_DOCUMENT': '문서당 최대 키워드',
      
      // KeyBERT 설정
      'extractor.keybert.enabled': 'KeyBERT 사용',
      'extractor.keybert.model': 'KeyBERT 모델',
      'extractor.keybert.use_mmr': 'MMR 사용',
      'extractor.keybert.use_maxsum': 'MaxSum 사용',
      'extractor.keybert.diversity': '다양성 (0.0-1.0)',
      'extractor.keybert.keyphrase_ngram_range': 'N-gram 범위',
      'extractor.keybert.stop_words': '불용어 언어',
      'extractor.keybert.max_keywords': '최대 키워드 수',
      
      // NER 설정
      'extractor.ner.enabled': 'NER 사용',
      'extractor.ner.model': 'NER 모델',
      
      // KoNLPy 설정
      'extractor.konlpy.enabled': 'KoNLPy 사용',
      'extractor.konlpy.analyzer': 'KoNLPy 분석기',
      'extractor.konlpy.filter_pos': '품사 필터',
      
      // LLM/Ollama 설정
      'ENABLE_LLM_EXTRACTION': 'LLM 추출 사용',
      'OLLAMA_BASE_URL': '서버 주소',
      'OLLAMA_MODEL': '모델',
      'OLLAMA_TIMEOUT': '타임아웃 (초)',
      'OLLAMA_MAX_TOKENS': '최대 토큰',
      'OLLAMA_TEMPERATURE': '온도 (0.0-1.0)',
      
      // OpenAI 설정
      'OPENAI_API_KEY': 'API 키',
      'OPENAI_MODEL': '모델',
      'OPENAI_MAX_TOKENS': '최대 토큰',
      
      // 파일 설정
      'ALLOWED_EXTENSIONS': '허용 확장자',
      'FILE_MAX_SIZE_MB': '최대 크기 (MB)',
      
      // 앱 설정
      'APP_DEBUG_MODE': '디버그 모드'
    };
    
    return labels[key] || key;
  };

  // 설정을 논리적인 순서로 정렬하는 함수
  const sortConfigs = (configs: Config[]): Config[] => {
    const order: { [key: string]: number } = {
      // KeyBERT 설정 순서
      'extractor.keybert.enabled': 1,
      'extractor.keybert.model': 2,
      'extractor.keybert.use_mmr': 3,
      'extractor.keybert.use_maxsum': 4,
      'extractor.keybert.diversity': 5,
      'extractor.keybert.keyphrase_ngram_range': 6,
      'extractor.keybert.stop_words': 7,
      'extractor.keybert.max_keywords': 8,
      
      // NER 설정 순서
      'extractor.ner.enabled': 1,
      'extractor.ner.model': 2,
      
      // KoNLPy 설정 순서
      'extractor.konlpy.enabled': 1,
      'extractor.konlpy.analyzer': 2,
      'extractor.konlpy.filter_pos': 3,
      
      // LLM 설정 순서
      'ENABLE_LLM_EXTRACTION': 1,
      'OLLAMA_BASE_URL': 2,
      'OLLAMA_MODEL': 3,
      'OLLAMA_TIMEOUT': 4,
      'OLLAMA_MAX_TOKENS': 5,
      'OLLAMA_TEMPERATURE': 6,
      'OPENAI_API_KEY': 7,
      'OPENAI_MODEL': 8,
      'OPENAI_MAX_TOKENS': 9
    };
    
    return [...configs].sort((a, b) => {
      const orderA = order[a.key] || 999;
      const orderB = order[b.key] || 999;
      return orderA - orderB;
    });
  };

  // 기본 추출기 체크박스 렌더링
  const renderDefaultExtractorsCheckboxes = (config: Config) => {
    const extractors = ['keybert', 'ner', 'llm', 'konlpy'];
    const extractorLabels: { [key: string]: string } = {
      'keybert': 'KeyBERT',
      'ner': 'NER',
      'llm': 'LLM',
      'konlpy': 'KoNLPy'
    };
    
    // 현재 선택된 추출기들
    let selectedExtractors: string[] = [];
    try {
      if (config.value.startsWith('[')) {
        selectedExtractors = JSON.parse(config.value);
      } else if (config.value) {
        selectedExtractors = config.value.split(',').map(e => e.trim());
      }
    } catch {
      selectedExtractors = ['keybert'];
    }
    
    const handleExtractorToggle = (extractor: string, checked: boolean) => {
      let newExtractors = [...selectedExtractors];
      if (checked) {
        if (!newExtractors.includes(extractor)) {
          newExtractors.push(extractor);
        }
      } else {
        newExtractors = newExtractors.filter(e => e !== extractor);
      }
      
      // 최소 하나의 추출기는 선택되어야 함
      if (newExtractors.length === 0) {
        newExtractors = ['keybert'];
      }
      
      updateConfig(config.key, JSON.stringify(newExtractors));
    };
    
    return (
      <div className="space-y-2">
        <div className="grid grid-cols-2 gap-2">
          {extractors.map(extractor => (
            <label key={extractor} className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={selectedExtractors.includes(extractor)}
                onChange={(e) => handleExtractorToggle(extractor, e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                disabled={saving}
              />
              <span className="text-sm text-gray-700">{extractorLabels[extractor]}</span>
            </label>
          ))}
        </div>
        <div className="text-xs text-gray-500">
          선택된 추출기: {selectedExtractors.map(e => extractorLabels[e] || e).join(', ')}
        </div>
      </div>
    );
  };

  // 허용 확장자 체크박스 렌더링
  const renderAllowedExtensionsCheckboxes = (config: Config) => {
    const extensions = ['.txt', '.pdf', '.docx', '.html', '.md', '.json', '.csv'];
    
    let selectedExtensions: string[] = [];
    try {
      selectedExtensions = JSON.parse(config.value);
    } catch {
      selectedExtensions = ['.txt', '.pdf'];
    }
    
    const handleExtensionToggle = (extension: string, checked: boolean) => {
      let newExtensions = [...selectedExtensions];
      if (checked) {
        if (!newExtensions.includes(extension)) {
          newExtensions.push(extension);
        }
      } else {
        newExtensions = newExtensions.filter(e => e !== extension);
      }
      
      // 최소 하나의 확장자는 선택되어야 함
      if (newExtensions.length === 0) {
        newExtensions = ['.txt'];
      }
      
      updateConfig(config.key, JSON.stringify(newExtensions));
    };
    
    return (
      <div className="space-y-2">
        <div className="grid grid-cols-4 gap-2">
          {extensions.map(extension => (
            <label key={extension} className="flex items-center space-x-1 cursor-pointer">
              <input
                type="checkbox"
                checked={selectedExtensions.includes(extension)}
                onChange={(e) => handleExtensionToggle(extension, e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                disabled={saving}
              />
              <span className="text-sm text-gray-700">{extension}</span>
            </label>
          ))}
        </div>
      </div>
    );
  };

  // KoNLPy 품사 필터 체크박스 렌더링
  const renderPosFilterCheckboxes = (config: Config) => {
    const posOptions = [
      { value: 'Noun', label: '명사' },
      { value: 'Verb', label: '동사' },
      { value: 'Adjective', label: '형용사' },
      { value: 'Adverb', label: '부사' },
      { value: 'Determiner', label: '관형사' },
      { value: 'Exclamation', label: '감탄사' }
    ];
    
    let selectedPos: string[] = [];
    try {
      selectedPos = JSON.parse(config.value);
    } catch {
      selectedPos = ['Noun', 'Verb', 'Adjective'];
    }
    
    const handlePosToggle = (pos: string, checked: boolean) => {
      let newPos = [...selectedPos];
      if (checked) {
        if (!newPos.includes(pos)) {
          newPos.push(pos);
        }
      } else {
        newPos = newPos.filter(p => p !== pos);
      }
      
      // 최소 하나의 품사는 선택되어야 함
      if (newPos.length === 0) {
        newPos = ['Noun'];
      }
      
      updateConfig(config.key, JSON.stringify(newPos));
    };
    
    return (
      <div className="space-y-2">
        <div className="grid grid-cols-3 gap-2">
          {posOptions.map(pos => (
            <label key={pos.value} className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={selectedPos.includes(pos.value)}
                onChange={(e) => handlePosToggle(pos.value, e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                disabled={saving}
              />
              <span className="text-sm text-gray-700">{pos.label}</span>
            </label>
          ))}
        </div>
      </div>
    );
  };

  // N-gram 범위 선택 렌더링
  const renderNgramRangeSelector = (config: Config) => {
    const ngramOptions = [
      { value: '[1, 1]', label: '1-gram (단일 단어)' },
      { value: '[1, 2]', label: '1-2 gram (단일 단어 + 두 단어 조합)' },
      { value: '[1, 3]', label: '1-3 gram (단일 단어 ~ 세 단어 조합)' },
      { value: '[2, 2]', label: '2-gram (두 단어 조합만)' },
      { value: '[2, 3]', label: '2-3 gram (두 단어 ~ 세 단어 조합)' },
      { value: '[3, 3]', label: '3-gram (세 단어 조합만)' }
    ];
    
    return (
      <select
        value={config.value}
        onChange={(e) => updateConfig(config.key, e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        disabled={saving}
      >
        {ngramOptions.map(option => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    );
  };

  const renderConfigInput = (config: Config) => {
    // 특별한 렌더링이 필요한 설정들
    if (config.key === 'DEFAULT_EXTRACTORS' || config.key === 'extractor.default_method') {
      return renderDefaultExtractorsCheckboxes(config);
    }
    
    if (config.key === 'ALLOWED_EXTENSIONS') {
      return renderAllowedExtensionsCheckboxes(config);
    }
    
    if (config.key === 'extractor.konlpy.filter_pos') {
      return renderPosFilterCheckboxes(config);
    }
    
    if (config.key === 'extractor.keybert.keyphrase_ngram_range') {
      return renderNgramRangeSelector(config);
    }

    const isBoolean = config.value === 'true' || config.value === 'false';
    const isJSON = config.value.startsWith('[') || config.value.startsWith('{');
    
    // 모델 선택을 위한 드롭다운 옵션들
    const getModelOptions = (configKey: string) => {
      if (configKey === 'OLLAMA_MODEL') {
        let options: { value: string; label: string }[] = [];
        
        // 현재 설정된 모델을 먼저 추가 (서버 목록에 없더라도)
        if (config.value && config.value !== '') {
          const isInServerList = ollamaModels.some(model => model.name === config.value);
          if (!isInServerList) {
            options.push({
              value: config.value,
              label: `${config.value} (현재 설정됨)`
            });
          }
        }
        
        // Ollama 서버에서 가져온 실제 모델 목록 추가
        if (ollamaModels.length > 0) {
          options.push(...ollamaModels.map(model => ({
            value: model.name,
            label: `${model.display_name} (${model.size_gb}GB)`
          })));
        } else {
          // 모델 목록이 없으면 기본 옵션들 제공
          options.push(
            { value: 'mistral', label: 'Mistral (서버에서 로드 필요)' },
            { value: 'llama2', label: 'Llama 2 (서버에서 로드 필요)' },
            { value: 'llama3.2', label: 'Llama 3.2 (서버에서 로드 필요)' }
          );
        }
        
        // 중복 제거
        const uniqueOptions = options.filter((option, index, self) => 
          index === self.findIndex(o => o.value === option.value)
        );
        
        return uniqueOptions;
      }
      
      if (configKey === 'extractor.keybert.model') {
        let options: { value: string; label: string; category?: string }[] = [];
        
        if (keyBERTModels) {
          // 다국어 모델
          keyBERTModels.models.multilingual.forEach(model => {
            options.push({
              value: model.name,
              label: `${model.name} - ${model.description} (${model.size})${model.recommended ? ' 🌟' : ''}`,
              category: 'multilingual'
            });
          });
          
          // 한국어 최적화 모델
          keyBERTModels.models.korean_optimized.forEach(model => {
            options.push({
              value: model.name,
              label: `${model.name} - ${model.description} (${model.size})${model.recommended ? ' 🌟' : ''}`,
              category: 'korean_optimized'
            });
          });
          
          // 영어 전용 모델
          keyBERTModels.models.english_only.forEach(model => {
            options.push({
              value: model.name,
              label: `${model.name} - ${model.description} (${model.size})`,
              category: 'english_only'
            });
          });
        } else {
          // KeyBERT 모델 목록이 로드되지 않은 경우 기본 옵션들
          options = [
            { value: 'all-MiniLM-L6-v2', label: 'all-MiniLM-L6-v2 (기본 다국어 모델)' },
            { value: 'jhgan/ko-sroberta-multitask', label: 'jhgan/ko-sroberta-multitask (한국어 최적화)' },
            { value: 'paraphrase-multilingual-MiniLM-L12-v2', label: 'paraphrase-multilingual-MiniLM-L12-v2 (다국어 고품질)' }
          ];
        }
        
        return options;
      }
      
      if (configKey === 'extractor.ner.model') {
        return [
          { value: 'ko_core_news_sm', label: 'Korean Small Model' },
          { value: 'ko_core_news_md', label: 'Korean Medium Model' },
          { value: 'ko_core_news_lg', label: 'Korean Large Model' },
          { value: 'en_core_web_sm', label: 'English Small Model' },
          { value: 'en_core_web_md', label: 'English Medium Model' },
          { value: 'en_core_web_lg', label: 'English Large Model' }
        ];
      }
      
      if (configKey === 'extractor.keybert.stop_words') {
        return [
          { value: 'none', label: '사용 안 함' },
          { value: 'english', label: '영어' },
          { value: 'korean', label: '한국어' },
          { value: 'chinese', label: '중국어' },
          { value: 'japanese', label: '일본어' },
          { value: 'spanish', label: '스페인어' },
          { value: 'french', label: '프랑스어' },
          { value: 'german', label: '독일어' },
          { value: 'italian', label: '이탈리아어' },
          { value: 'portuguese', label: '포르투갈어' },
          { value: 'russian', label: '러시아어' },
          { value: 'arabic', label: '아랍어' }
        ];
      }
      
      if (configKey === 'extractor.konlpy.analyzer') {
        return [
          { value: 'Okt', label: 'Okt (Open Korean Text)' },
          { value: 'Komoran', label: 'Komoran' },
          { value: 'Hannanum', label: '한나눔' },
          { value: 'Kkma', label: '꼬꼬마' },
          { value: 'Mecab', label: 'Mecab' }
        ];
      }
      
      if (configKey === 'extractor.llm.provider' || configKey === 'LLM_PROVIDER') {
        return [
          { value: 'ollama', label: 'Ollama' },
          { value: 'openai', label: 'OpenAI' },
          { value: 'anthropic', label: 'Anthropic' }
        ];
      }
      
      return null;
    };

    const modelOptions = getModelOptions(config.key);
    
    if (isBoolean) {
      return (
        <select
          value={config.value}
          onChange={(e) => updateConfig(config.key, e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={saving}
        >
          <option value="true">활성화</option>
          <option value="false">비활성화</option>
        </select>
      );
    }

    if (modelOptions) {
      const isOllamaModel = config.key === 'OLLAMA_MODEL';
      const isKeyBERTModel = config.key === 'extractor.keybert.model';
      
      return (
        <div className="space-y-2">
          <div className="flex space-x-2">
            <select
              value={config.value}
              onChange={(e) => updateConfig(config.key, e.target.value)}
              className="flex-1 px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={saving || (isOllamaModel && ollamaModelsLoading) || (isKeyBERTModel && keyBERTModelsLoading)}
            >
              {isKeyBERTModel && keyBERTModels ? (
                <>
                  <optgroup label="🌍 다국어 모델">
                    {keyBERTModels.models.multilingual.map((model) => (
                      <option key={model.name} value={model.name}>
                        {model.name}{model.recommended ? ' 🌟' : ''}
                      </option>
                    ))}
                  </optgroup>
                  <optgroup label="🇰🇷 한국어 최적화">
                    {keyBERTModels.models.korean_optimized.map((model) => (
                      <option key={model.name} value={model.name}>
                        {model.name}{model.recommended ? ' 🌟' : ''}
                      </option>
                    ))}
                  </optgroup>
                  <optgroup label="🇺🇸 영어 전용">
                    {keyBERTModels.models.english_only.map((model) => (
                      <option key={model.name} value={model.name}>
                        {model.name}
                      </option>
                    ))}
                  </optgroup>
                </>
              ) : (
                modelOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))
              )}
            </select>
            {isOllamaModel && (
              <button
                onClick={loadOllamaModels}
                disabled={ollamaModelsLoading || saving}
                className="px-3 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:bg-gray-50 disabled:cursor-not-allowed"
                title="모델 목록 새로고침"
              >
                {ollamaModelsLoading ? '🔄' : '🔄'}
              </button>
            )}
            {isKeyBERTModel && (
              <button
                onClick={loadKeyBERTModels}
                disabled={keyBERTModelsLoading || saving}
                className="px-3 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:bg-gray-50 disabled:cursor-not-allowed"
                title="모델 목록 새로고침"
              >
                {keyBERTModelsLoading ? '🔄' : '🔄'}
              </button>
            )}
          </div>
          {isOllamaModel && ollamaModels.length === 0 && !ollamaModelsLoading && (
            <div className="text-xs text-amber-600">
              ⚠️ Ollama 서버에 연결하여 모델 목록을 가져오려면 위의 "연결 테스트" 버튼을 클릭하세요
            </div>
          )}
          {isKeyBERTModel && keyBERTModels && (
            <>
              <div className="text-xs text-gray-600 bg-blue-50 p-2 rounded">
                💡 {keyBERTModels.recommendation}
              </div>
              {/* 선택된 모델의 상세 정보 표시 */}
              {(() => {
                const allModels = [
                  ...keyBERTModels.models.multilingual,
                  ...keyBERTModels.models.korean_optimized,
                  ...keyBERTModels.models.english_only
                ];
                const selectedModel = allModels.find(m => m.name === config.value);
                if (selectedModel) {
                  return (
                    <div className="mt-2 p-3 bg-gray-50 border border-gray-200 rounded-lg">
                      <div className="text-xs space-y-1">
                        <div className="font-medium text-gray-700">{selectedModel.name}</div>
                        <div className="text-gray-600">
                          <span className="font-medium">설명:</span> {selectedModel.description}
                        </div>
                        <div className="text-gray-600">
                          <span className="font-medium">크기:</span> {selectedModel.size}
                        </div>
                        <div className="text-gray-600">
                          <span className="font-medium">지원 언어:</span> {selectedModel.languages.join(', ')}
                        </div>
                        <div className="flex gap-4">
                          <div className="text-gray-600">
                            <span className="font-medium">속도:</span> {selectedModel.speed}
                          </div>
                          <div className="text-gray-600">
                            <span className="font-medium">품질:</span> {selectedModel.quality}
                          </div>
                        </div>
                        {selectedModel.recommended && (
                          <div className="text-green-600 font-medium">
                            🌟 추천 모델
                          </div>
                        )}
                      </div>
                    </div>
                  );
                }
                return null;
              })()}
            </>
          )}
          {isKeyBERTModel && !keyBERTModels && !keyBERTModelsLoading && (
            <div className="text-xs text-amber-600">
              ⚠️ KeyBERT 모델 목록을 불러올 수 없습니다. 새로고침 버튼을 클릭해보세요.
            </div>
          )}
          {isKeyBERTModel && downloadProgress[config.value] && (
            <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-blue-800">
                  모델 {downloadProgress[config.value].status === 'downloading' ? '다운로드' : '로드'} 중...
                </span>
                <span className="text-xs text-blue-600">
                  {downloadProgress[config.value].progress}%
                </span>
              </div>
              <div className="w-full bg-blue-200 rounded-full h-2 mb-2">
                <div 
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300" 
                  style={{ width: `${downloadProgress[config.value].progress}%` }}
                ></div>
              </div>
              <div className="text-xs text-blue-700">
                {downloadProgress[config.value].message}
              </div>
            </div>
          )}
          {isKeyBERTModel && (
            <div className="flex space-x-2 mt-2">
              <button
                onClick={async () => {
                  if (window.confirm(`현재 선택된 모델 '${config.value}'의 캐시를 삭제하시겠습니까?\n다음 사용 시 다시 다운로드됩니다.`)) {
                    try {
                      const response = await fetch(`http://localhost:58000/configs/keybert/models/${encodeURIComponent(config.value)}/cache`, {
                        method: 'DELETE'
                      });
                      const result = await response.json();
                      
                      if (result.status === 'success') {
                        alert(`모델 캐시가 삭제되었습니다.\n삭제된 크기: ${result.total_size_mb}MB`);
                      } else {
                        alert(`캐시 삭제 실패: ${result.message}`);
                      }
                    } catch (error) {
                      console.error('캐시 삭제 중 오류:', error);
                      alert('캐시 삭제 중 오류가 발생했습니다.');
                    }
                  }
                }}
                disabled={saving}
                className="px-3 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed"
                title="모델 캐시 삭제"
              >
                🗑️ 캐시 삭제
              </button>
              <button
                onClick={async () => {
                  try {
                    const response = await fetch(`http://localhost:58000/configs/keybert/models/${encodeURIComponent(config.value)}/download`, {
                      method: 'POST'
                    });
                    const result = await response.json();
                    
                    if (result.status === 'success') {
                      // 진행률 추적 시작
                      if (result.progress_key) {
                        trackDownloadProgress(result.progress_key, config.value);
                      }
                      
                      const action = result.was_cached ? '로드' : '다운로드';
                      const sizeInfo = result.model_size_mb ? ` (${result.model_size_mb}MB)` : '';
                      
                      // 진행률이 있으면 alert를 표시하지 않음
                      if (!result.progress_key) {
                        alert(`모델이 다시 ${action}되었습니다.\n소요시간: ${result.download_time_seconds}초${sizeInfo}`);
                      }
                    } else {
                      alert(`모델 재로드 실패: ${result.message}`);
                    }
                  } catch (error) {
                    console.error('모델 재로드 중 오류:', error);
                    alert('모델 재로드 중 오류가 발생했습니다.');
                  }
                }}
                disabled={saving || !!downloadProgress[config.value]}
                className="px-3 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed"
                title="모델 다시 다운로드"
              >
                🔄 재로드
              </button>
              <button
                onClick={async () => {
                  try {
                    const response = await fetch(`http://localhost:58000/configs/keybert/models/${encodeURIComponent(config.value)}/status`);
                    const result = await response.json();
                    
                    if (result.status === 'success') {
                      const status = result.is_cached ? '다운로드됨' : '다운로드 필요';
                      const size = result.total_size_mb > 0 ? ` (${result.total_size_mb}MB)` : '';
                      alert(`모델 '${config.value}' 상태: ${status}${size}`);
                    } else {
                      alert(`상태 확인 실패: ${result.message}`);
                    }
                  } catch (error) {
                    console.error('상태 확인 중 오류:', error);
                    alert('상태 확인 중 오류가 발생했습니다.');
                  }
                }}
                disabled={saving}
                className="px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed"
                title="모델 상태 확인"
              >
                ℹ️ 상태
              </button>
            </div>
          )}
        </div>
      );
    }

    if (isJSON) {
      return (
        <textarea
          value={config.value}
          onChange={(e) => updateConfig(config.key, e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
          rows={3}
          disabled={saving}
        />
      );
    }

    return (
      <input
        type="text"
        value={config.value}
        onChange={(e) => updateConfig(config.key, e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        disabled={saving}
      />
    );
  };

  const renderConfigSection = (title: string, configs: Config[]) => {
    // 설정을 논리적인 순서로 정렬
    const sortedConfigs = sortConfigs(configs);
    
    return (
      <div className="mb-8">
        {title && <h3 className="text-lg font-semibold mb-4 text-gray-800">{title}</h3>}
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 w-1/3">설정 항목</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">설정 값</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {sortedConfigs.map((config) => {
                const hasChange = pendingChanges.hasOwnProperty(config.key);
                return (
                  <tr 
                    key={config.key} 
                    className={`group relative transition-colors hover:bg-gray-50 ${
                      hasChange ? 'bg-amber-50' : ''
                    }`}
                  >
                    <td className="px-4 py-4 w-1/3">
                      <div className="relative">
                        <div className="flex items-center">
                          <span className="text-sm font-medium text-gray-900">
                            {getConfigLabel(config.key)}
                          </span>
                          {hasChange && (
                            <span className="ml-2 text-xs text-amber-600 font-normal">
                              (변경됨)
                            </span>
                          )}
                        </div>
                        
                        {/* 마우스 오버 시 나타나는 설명 오버레이 */}
                        <div className="absolute left-0 top-full mt-2 w-80 max-w-sm bg-gray-900 text-white text-xs rounded-lg p-3 shadow-lg z-10 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 pointer-events-none">
                          <div className="relative">
                            <div className="font-medium mb-1">{config.key}</div>
                            <div>{config.description}</div>
                            {/* 말풍선 화살표 */}
                            <div className="absolute -top-1 left-4 w-2 h-2 bg-gray-900 transform rotate-45"></div>
                          </div>
                        </div>
                      </div>
                    </td>
                  <td className="px-4 py-4">
                    <div className="flex items-center space-x-2">
                      <div className="flex-1">
                        {renderConfigInput(config)}
                      </div>
                      {hasChange && (
                        <button
                          onClick={() => {
                            // 개별 변경사항 되돌리기
                            setPendingChanges(prev => {
                              const newChanges = { ...prev };
                              delete newChanges[config.key];
                              setHasChanges(Object.keys(newChanges).length > 0);
                              return newChanges;
                            });
                            // 원래 값으로 되돌리기 위해 설정 다시 로드
                            loadConfigs();
                          }}
                          className="text-amber-600 hover:text-amber-700 text-sm px-2 py-1 rounded hover:bg-amber-100"
                          title="변경사항 되돌리기"
                        >
                          ↶
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
    );
  };

  if (loading) {
    return (
      <div className={inline ? "flex items-center justify-center p-8" : "fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"}>
        <div className={inline ? "text-center" : "bg-white p-6 rounded-lg"}>
          <div className="text-center">설정을 로드하는 중...</div>
        </div>
      </div>
    );
  }

  const content = (
    <div className="flex flex-col h-full">
      {/* 스크롤 가능한 메인 컨텐츠 영역 */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 space-y-8">
          {/* 기본 추출기 설정 */}
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            {renderConfigSection('기본 키워드 추출기 설정', extractorBaseSettings)}
          </div>
          
          {/* 추출기별 설정 탭 */}
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <h3 className="text-lg font-semibold mb-4 text-gray-800">추출기별 세부 설정</h3>
        
        {/* 탭 헤더 */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            {[
              { key: 'keybert', label: 'KeyBERT', color: 'blue', count: keyBERTSettings.length },
              { key: 'ner', label: 'NER', color: 'green', count: nerSettings.length },
              { key: 'llm', label: 'LLM', color: 'purple', count: llmSettings.length },
              { key: 'konlpy', label: 'KoNLPy', color: 'orange', count: konlpySettings.length }
            ].map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveExtractorTab(tab.key as any)}
                className={getTabButtonClass(tab.key, tab.color, activeExtractorTab === tab.key)}
              >
                {tab.label}
                {tab.count > 0 && (
                  <span className={getTabCountClass(tab.color, activeExtractorTab === tab.key)}>
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>
        
        {/* 탭 내용 */}
        <div className="tab-content">
          {activeExtractorTab === 'keybert' && keyBERTSettings.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center space-x-2 mb-4">
                <div className="w-4 h-4 bg-blue-500 rounded"></div>
                <h4 className="text-md font-medium text-gray-900">KeyBERT 추출기 설정</h4>
                {isExtractorEnabled('keybert') ? (
                  <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded-full">활성화됨</span>
                ) : (
                  <span className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded-full">비활성화됨</span>
                )}
              </div>
              {renderConfigSection('', keyBERTSettings)}
            </div>
          )}
          
          {activeExtractorTab === 'ner' && nerSettings.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center space-x-2 mb-4">
                <div className="w-4 h-4 bg-green-500 rounded"></div>
                <h4 className="text-md font-medium text-gray-900">NER 추출기 설정</h4>
                {isExtractorEnabled('ner') ? (
                  <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded-full">활성화됨</span>
                ) : (
                  <span className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded-full">비활성화됨</span>
                )}
              </div>
              {renderConfigSection('', nerSettings)}
            </div>
          )}
          
          {activeExtractorTab === 'llm' && llmSettings.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-4 bg-purple-500 rounded"></div>
                  <h4 className="text-md font-medium text-gray-900">LLM 추출기 설정</h4>
                  {isExtractorEnabled('llm') ? (
                    <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded-full">활성화됨</span>
                  ) : (
                    <span className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded-full">비활성화됨</span>
                  )}
                </div>
                <button
                  onClick={testLLMConnection}
                  disabled={connectionTest.status === 'testing'}
                  className="px-3 py-1.5 text-sm bg-purple-500 text-white rounded hover:bg-purple-600 disabled:bg-gray-400 disabled:cursor-not-allowed"
                >
                  {connectionTest.status === 'testing' ? '테스트 중...' : '연결 테스트'}
                </button>
              </div>
              
              {/* 연결 테스트 결과 */}
              {connectionTest.message && (
                <div className={`mb-4 p-4 rounded-lg border ${
                  connectionTest.status === 'success' 
                    ? 'bg-green-50 text-green-800 border-green-200' 
                    : connectionTest.status === 'error'
                    ? 'bg-red-50 text-red-800 border-red-200'
                    : 'bg-blue-50 text-blue-800 border-blue-200'
                }`}>
                  <div className="font-medium">{connectionTest.message}</div>
                  {connectionTest.provider && (
                    <div className="text-sm mt-2 space-y-1">
                      <div><span className="font-medium">Provider:</span> {connectionTest.provider}</div>
                      <div><span className="font-medium">Model:</span> {connectionTest.model}</div>
                      <div><span className="font-medium">URL:</span> {connectionTest.base_url}</div>
                      {connectionTest.test_keywords && (
                        <div><span className="font-medium">Test Keywords:</span> {connectionTest.test_keywords.join(', ')}</div>
                      )}
                    </div>
                  )}
                </div>
              )}
              
              {renderConfigSection('', llmSettings)}
            </div>
          )}
          
          {activeExtractorTab === 'konlpy' && konlpySettings.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center space-x-2 mb-4">
                <div className="w-4 h-4 bg-orange-500 rounded"></div>
                <h4 className="text-md font-medium text-gray-900">KoNLPy 추출기 설정</h4>
                {isExtractorEnabled('konlpy') ? (
                  <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded-full">활성화됨</span>
                ) : (
                  <span className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded-full">비활성화됨</span>
                )}
              </div>
              {renderConfigSection('', konlpySettings)}
            </div>
          )}
          
          {/* 탭에 해당하는 설정이 없는 경우 */}
          {((activeExtractorTab === 'keybert' && keyBERTSettings.length === 0) ||
            (activeExtractorTab === 'ner' && nerSettings.length === 0) ||
            (activeExtractorTab === 'llm' && llmSettings.length === 0) ||
            (activeExtractorTab === 'konlpy' && konlpySettings.length === 0)) && (
            <div className="text-center py-8 text-gray-500">
              <div className="text-lg mb-2">📋</div>
              <div>이 추출기에 대한 설정이 없습니다.</div>
              <div className="text-sm mt-1">백엔드에서 설정을 추가해주세요.</div>
            </div>
          )}
            </div>
          </div>
          
          {/* 파일 설정 */}
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            {renderConfigSection('파일 업로드 설정', fileSettings)}
          </div>
          
          {/* 앱 설정 */}
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            {renderConfigSection('애플리케이션 설정', appSettings)}
          </div>
        </div>
      </div>
    </div>
  );

  if (inline) {
    return (
      <div className="flex flex-col h-full">
        {/* 인라인 모드용 버튼 영역 - 고정 */}
        <div className="px-4 py-3 border-b bg-gray-50 flex-shrink-0">
          <div className="flex justify-between items-center">
            <div className="text-sm text-gray-600">
              {hasChanges ? (
                <span className="text-amber-600 font-medium">
                  ⚠️ 저장하지 않은 변경사항이 있습니다
                </span>
              ) : (
                <span>설정을 변경하고 저장하세요</span>
              )}
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => {
                  if (hasChanges) {
                    if (window.confirm('저장하지 않은 변경사항이 있습니다. 새로고침하면 변경사항이 사라집니다. 계속하시겠습니까?')) {
                      setPendingChanges({});
                      setHasChanges(false);
                      loadConfigs();
                    }
                  } else {
                    loadConfigs();
                  }
                }}
                className="px-3 py-1.5 text-sm text-gray-600 bg-white border border-gray-300 rounded hover:bg-gray-50"
                disabled={saving}
              >
                🔄 새로고침
              </button>
              {hasChanges && (
                <>
                  <button
                    onClick={discardChanges}
                    className="px-3 py-1.5 text-sm text-gray-600 bg-white border border-gray-300 rounded hover:bg-gray-50"
                  >
                    취소
                  </button>
                  <button
                    onClick={saveAllChanges}
                    disabled={saving}
                    className="px-3 py-1.5 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-400"
                  >
                    {saving ? '💾 저장중...' : '💾 저장'}
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
        
        {/* 인라인 모드용 스크롤 가능한 내용 */}
        <div className="flex-1 overflow-y-auto min-h-0">
          {content}
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg w-full max-w-6xl max-h-full flex flex-col" style={{ height: 'calc(100vh - 2rem)' }}>
        {/* 헤더 영역 - 완전 고정 */}
        <div className="flex items-center justify-between p-6 border-b bg-white rounded-t-lg flex-shrink-0">
          <h2 className="text-xl font-semibold">시스템 설정</h2>
          <button
            onClick={() => {
              if (hasChanges) {
                if (window.confirm('저장하지 않은 변경사항이 있습니다. 정말 닫으시겠습니까?')) {
                  setPendingChanges({});
                  setHasChanges(false);
                  onClose();
                }
              } else {
                onClose();
              }
            }}
            className="text-gray-400 hover:text-gray-600 text-2xl"
          >
            ×
          </button>
        </div>
        
        {/* 버튼 영역 - 완전 고정 */}
        <div className="px-6 py-4 border-b bg-gray-50 flex-shrink-0">
          <div className="flex justify-between items-center">
            <div className="text-sm text-gray-600">
              {hasChanges ? (
                <span className="text-amber-600 font-medium">
                  ⚠️ 저장하지 않은 변경사항이 있습니다
                </span>
              ) : (
                <span>설정을 변경하고 저장하세요</span>
              )}
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => {
                  if (hasChanges) {
                    if (window.confirm('저장하지 않은 변경사항이 있습니다. 새로고침하면 변경사항이 사라집니다. 계속하시겠습니까?')) {
                      setPendingChanges({});
                      setHasChanges(false);
                      loadConfigs();
                    }
                  } else {
                    loadConfigs();
                  }
                }}
                className="px-3 py-1.5 text-sm text-gray-600 bg-white border border-gray-300 rounded hover:bg-gray-50"
                disabled={saving}
              >
                🔄 새로고침
              </button>
              {hasChanges && (
                <>
                  <button
                    onClick={discardChanges}
                    className="px-3 py-1.5 text-sm text-gray-600 bg-white border border-gray-300 rounded hover:bg-gray-50"
                  >
                    취소
                  </button>
                  <button
                    onClick={saveAllChanges}
                    disabled={saving}
                    className="px-3 py-1.5 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-400"
                  >
                    {saving ? '💾 저장중...' : '💾 저장'}
                  </button>
                </>
              )}
              <button
                onClick={() => {
                  if (hasChanges) {
                    if (window.confirm('저장하지 않은 변경사항이 있습니다. 정말 닫으시겠습니까?')) {
                      setPendingChanges({});
                      setHasChanges(false);
                      onClose();
                    }
                  } else {
                    onClose();
                  }
                }}
                className="px-3 py-1.5 text-sm text-gray-600 bg-white border border-gray-300 rounded hover:bg-gray-50"
              >
                ✕ 닫기
              </button>
            </div>
          </div>
        </div>
        
        {/* 스크롤 가능한 콘텐츠 영역만 */}
        <div className="flex-1 overflow-y-auto min-h-0">
          {content}
        </div>
      </div>
    </div>
  );
};

export default SettingsPanel;