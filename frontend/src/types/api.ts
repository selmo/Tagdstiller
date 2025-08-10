// API 응답 타입 정의

export interface Config {
  key: string;
  value: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: number;
  name: string;
  created_at: string;
}

export interface UploadedFile {
  id: number;
  project_id: number;
  filename: string;
  filepath: string;
  size: number;
  mime_type?: string;
  content?: string | null;
  parse_status: string;
  parse_error?: string | null;
  uploaded_at?: string;
  created_at?: string;
}

export interface KeywordOccurrence {
  id?: number;
  file_id: number;
  keyword: string;
  extractor_name: string;
  score: number;
  category?: string;
  start_position?: number;
  end_position?: number;
  context_snippet?: string;
  page_number?: number;
  line_number?: number;
  column_number?: number;
  created_at?: string;
}

export interface ExtractionResponse {
  project_id?: number;
  file_id?: number;
  keywords: KeywordOccurrence[];
  extractors_used: string[];
  total_keywords: number;
}

export interface AvailableExtractors {
  available_extractors: string[];
  default_extractors: string[];
  total_available: number;
}

export interface KeyBERTModel {
  name: string;
  description: string;
  size: string;
  languages: string[];
  speed: string;
  quality: string;
  recommended?: boolean;
}

export interface KeyBERTModelsResponse {
  models: {
    multilingual: KeyBERTModel[];
    korean_optimized: KeyBERTModel[];
    english_only: KeyBERTModel[];
  };
  current_model: string;
  recommendation: string;
}

// 키워드 통계 관련 타입들
export interface KeywordStatisticsProject {
  project_id: number;
  project_name: string;
  keywords_count: number;
  unique_keywords_count: number;
  extractors_count: number;
  categories_count: number;
  files_count: number;
  avg_score: number;
  extractors: string[];
  categories: string[];
  top_keywords: Array<{
    keyword: string;
    score: number;
    count: number;
  }>;
}

export interface KeywordStatisticsSingle {
  type: 'single_project';
  project: {
    id: number;
    name: string;
  };
  keywords: Array<{
    keyword: string;
    extractors: string[];
    max_score: number;
    occurrences: number;
    categories: string[];
    files_count: number;
  }>;
  extractors: Array<{
    extractor: string;
    keywords_count: number;
    unique_keywords_count: number;
    avg_score: number;
  }>;
  categories: Array<{
    category: string;
    keywords_count: number;
    unique_keywords_count: number;
  }>;
  summary: {
    total_keywords: number;
    unique_keywords: number;
    extractors_used: number;
    categories_found: number;
  };
}

export interface KeywordStatisticsAll {
  type: 'all_projects';
  projects: KeywordStatisticsProject[];
  global_keywords: Array<{
    keyword: string;
    projects_count: number;
    extractors: string[];
    max_score: number;
    occurrences: number;
    categories: string[];
  }>;
  global_extractors: Array<{
    extractor: string;
    keywords_count: number;
    unique_keywords_count: number;
    projects_count: number;
    avg_score: number;
  }>;
  global_categories: Array<{
    category: string;
    keywords_count: number;
    unique_keywords_count: number;
    projects_count: number;
  }>;
  summary: {
    total_projects: number;
    total_keywords: number;
    unique_keywords: number;
    extractors_used: number;
    categories_found: number;
  };
}

export type KeywordStatisticsResponse = KeywordStatisticsSingle | KeywordStatisticsAll;

// 새로운 효율적인 통계 API 타입
export interface GlobalKeywordStatistics {
  total_projects: number;
  total_files: number;
  total_keywords: number;
  total_occurrences: number;
  extractors_used: string[];
}

export interface ProjectKeywordStatistics {
  project_id: number;
  project_name: string;
  total_files: number;
  total_keywords: number;
  total_occurrences: number;
  extractors_used: string[];
}