import axios, { AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import { Config, Project, UploadedFile, ExtractionResponse, AvailableExtractors, GlobalKeywordStatistics, ProjectKeywordStatistics } from '../types/api';
import { logger } from '../utils/logger';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:58000';

// API 로거 생성
const apiLogger = logger.createComponentLogger('API');

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 요청 인터셉터 - 로깅
api.interceptors.request.use(
  (config: any) => {
    const startTime = Date.now();
    config.metadata = { startTime };
    
    apiLogger.debug(`API 요청 시작: ${config.method?.toUpperCase()} ${config.url}`, {
      action: 'request_start',
      method: config.method?.toUpperCase(),
      url: config.url,
      params: config.params,
      // POST/PUT 데이터는 민감할 수 있으므로 크기만 로깅
      dataSize: config.data ? JSON.stringify(config.data).length : 0
    });

    return config;
  },
  (error: AxiosError) => {
    apiLogger.error('API 요청 설정 오류', error);
    return Promise.reject(error);
  }
);

// 응답 인터셉터 - 로깅
api.interceptors.response.use(
  (response: AxiosResponse) => {
    const endTime = Date.now();
    const config = response.config as any;
    const duration = endTime - (config.metadata?.startTime || endTime);
    
    apiLogger.debug(`API 응답 성공: ${response.config.method?.toUpperCase()} ${response.config.url}`, {
      action: 'response_success',
      method: response.config.method?.toUpperCase(),
      url: response.config.url,
      status: response.status,
      duration,
      dataSize: response.data ? JSON.stringify(response.data).length : 0
    });

    // 성능 경고 (5초 이상)
    if (duration > 5000) {
      apiLogger.warn(`느린 API 응답: ${response.config.method?.toUpperCase()} ${response.config.url}`, {
        action: 'slow_response',
        duration
      });
    }

    return response;
  },
  (error: AxiosError) => {
    const endTime = Date.now();
    const config = error.config as any;
    const duration = endTime - (config?.metadata?.startTime || endTime);
    
    apiLogger.error(`API 응답 오류: ${error.config?.method?.toUpperCase()} ${error.config?.url}`, error, {
      action: 'response_error',
      method: error.config?.method?.toUpperCase(),
      url: error.config?.url,
      status: error.response?.status,
      statusText: error.response?.statusText,
      duration,
      errorMessage: error.message
    });

    return Promise.reject(error);
  }
);

// TypeScript 확장 - metadata 속성 추가

// Config API
export const configApi = {
  getAll: (): Promise<Config[]> => api.get('/configs/').then(res => res.data),
  getByKey: (key: string): Promise<Config> => api.get(`/configs/${key}`).then(res => res.data),
  update: (key: string, data: { value: string; description?: string }): Promise<Config> => 
    api.put(`/configs/${key}`, data).then(res => res.data),
  getKeyBERTModels: () => api.get('/configs/keybert/models').then(res => res.data),
};

// Project API
export const projectApi = {
  getAll: (): Promise<Project[]> => api.get('/projects/').then(res => res.data),
  create: (name: string): Promise<Project> => 
    api.post('/projects/', { name }).then(res => res.data),
  get: (projectId: number): Promise<Project> =>
    api.get(`/projects/${projectId}`).then(res => res.data),
  update: (projectId: number, name: string): Promise<Project> =>
    api.put(`/projects/${projectId}`, { name }).then(res => res.data),
  delete: (projectId: number): Promise<{ message: string }> =>
    api.delete(`/projects/${projectId}`).then(res => res.data),
  getFiles: (projectId: number): Promise<UploadedFile[]> => 
    api.get(`/projects/${projectId}/files`).then(res => res.data),
  extractKeywords: (projectId: number, methods: string[]): Promise<ExtractionResponse> =>
    api.post(`/projects/${projectId}/extract_keywords/`, { methods }).then(res => res.data),
  getKeywords: (projectId: number) => 
    api.get(`/projects/${projectId}/keywords/`).then(res => res.data),
  getFileKeywords: (fileId: number) => 
    api.get(`/files/${fileId}/keywords/`).then(res => res.data),
  getGlobalStatistics: (): Promise<GlobalKeywordStatistics> => 
    api.get('/projects/statistics/global').then(res => res.data),
  getProjectStatistics: (projectId: number): Promise<ProjectKeywordStatistics> => 
    api.get(`/projects/${projectId}/statistics`).then(res => res.data),
};

// File API
export const fileApi = {
  upload: (projectId: number, file: File): Promise<UploadedFile> => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/projects/${projectId}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }).then(res => res.data);
  },
  uploadBulk: (projectId: number, files: File[]): Promise<UploadedFile[]> => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });
    return api.post(`/projects/${projectId}/upload_bulk`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }).then(res => res.data);
  },
  delete: (projectId: number, fileId: number): Promise<{ message: string }> =>
    api.delete(`/projects/${projectId}/files/${fileId}`).then(res => res.data),
  extractKeywords: (fileId: number, methods: string[]): Promise<ExtractionResponse> =>
    api.post(`/files/${fileId}/extract_keywords/`, { methods }).then(res => res.data),
  getKeywords: (fileId: number) => 
    api.get(`/files/${fileId}/keywords/`).then(res => res.data),
  getContent: (fileId: number): Promise<{ content: string }> =>
    api.get(`/files/${fileId}/content`).then(res => res.data),
  download: (fileId: number): string =>
    `/api/files/${fileId}/download`,
};

// Extraction API
export const extractionApi = {
  getAvailableExtractors: (): Promise<AvailableExtractors> => 
    api.get('/extractors/available').then(res => res.data),
};

// Keywords API
export const keywordsApi = {
  getStatistics: (projectId?: number) => {
    const url = projectId ? `/keywords/statistics?project_id=${projectId}` : '/keywords/statistics';
    return api.get(url).then(res => res.data);
  },
  getList: (params?: {
    project_id?: number;
    extractor?: string;
    category?: string;
    limit?: number;
    offset?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.project_id) searchParams.append('project_id', params.project_id.toString());
    if (params?.extractor) searchParams.append('extractor', params.extractor);
    if (params?.category) searchParams.append('category', params.category);
    if (params?.limit) searchParams.append('limit', params.limit.toString());
    if (params?.offset) searchParams.append('offset', params.offset.toString());
    
    const url = `/keywords/list${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
    return api.get(url).then(res => res.data);
  },
};