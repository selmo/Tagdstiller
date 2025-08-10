import React from 'react';
import { useState, useRef } from 'react';
import { fileApi } from '../services/api';
import { UploadedFile } from '../types/api';

interface FileUploaderProps {
  projectId: number;
  onFileUploaded: (file: UploadedFile) => void;
  onUploadComplete?: () => void;
}

const FileUploader: React.FC<FileUploaderProps> = ({ projectId, onFileUploaded, onUploadComplete }: FileUploaderProps) => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploadMode, setUploadMode] = useState<'single' | 'multiple' | 'directory'>('single');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const directoryInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (files: File | File[]) => {
    const fileList = Array.isArray(files) ? files : [files];
    if (fileList.length === 0) return;

    setIsUploading(true);
    setError(null);
    setUploadProgress(0);

    try {
      const allowedTypes = ['.txt', '.pdf', '.docx', '.html', '.md', '.text', '.log', '.csv', '.tsv', '.htm', '.xhtml', '.markdown', '.mdown', '.mkd', '.zip'];
      const maxSize = 50 * 1024 * 1024;
      
      // Validate all files first
      const validFiles: File[] = [];
      const errors: string[] = [];

      for (const file of fileList) {
        try {
          // 파일 크기 체크 (50MB 제한)
          if (file.size > maxSize) {
            throw new Error(`${file.name}: 파일 크기는 50MB를 초과할 수 없습니다.`);
          }

          // 지원하는 파일 형식 체크
          const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
          if (!allowedTypes.includes(fileExtension)) {
            throw new Error(`${file.name}: 지원하지 않는 파일 형식입니다. (지원: TXT, PDF, DOCX, HTML, MD, ZIP)`);
          }

          validFiles.push(file);
        } catch (err: any) {
          errors.push(err.message || `${file.name}: 검증 실패`);
        }
      }

      if (validFiles.length === 0) {
        throw new Error(`업로드할 수 있는 유효한 파일이 없습니다. ${errors.join('; ')}`);
      }

      setUploadProgress(50);

      // Upload files
      if (validFiles.length === 1) {
        const uploadedFile = await fileApi.upload(projectId, validFiles[0]);
        onFileUploaded(uploadedFile);
      } else {
        const uploadedFiles = await fileApi.uploadBulk(projectId, validFiles);
        uploadedFiles.forEach(file => onFileUploaded(file));
      }

      setUploadProgress(100);
      
      if (errors.length > 0) {
        setError(`${validFiles.length}개 성공, ${errors.length}개 실패: ${errors.slice(0, 3).join('; ')}${errors.length > 3 ? '...' : ''}`);
      }

      // 업로드 완료 콜백 호출 (에러가 있어도 일부 파일이 성공했으면 호출)
      if (validFiles.length > 0 && onUploadComplete) {
        onUploadComplete();
      }
    } catch (err: any) {
      setError(err.message || err.response?.data?.detail || '파일 업로드에 실패했습니다.');
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      if (uploadMode === 'single') {
        handleFileUpload(files[0]);
      } else {
        handleFileUpload(Array.from(files));
      }
    }
  };

  const handleDirectorySelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileUpload(Array.from(files));
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      if (uploadMode === 'single') {
        handleFileUpload(files[0]);
      } else {
        handleFileUpload(Array.from(files));
      }
    }
  };

  const openFileDialog = () => {
    if (uploadMode === 'directory') {
      directoryInputRef.current?.click();
    } else {
      fileInputRef.current?.click();
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4">파일 업로드</h3>
      
      {/* 업로드 모드 선택 */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">업로드 방식</label>
        <div className="flex space-x-4">
          <button
            onClick={() => setUploadMode('single')}
            className={`px-3 py-2 text-sm rounded-md border ${
              uploadMode === 'single' 
                ? 'bg-blue-100 border-blue-300 text-blue-700' 
                : 'bg-gray-100 border-gray-300 text-gray-700 hover:bg-gray-200'
            }`}
          >
            단일 파일
          </button>
          <button
            onClick={() => setUploadMode('multiple')}
            className={`px-3 py-2 text-sm rounded-md border ${
              uploadMode === 'multiple' 
                ? 'bg-blue-100 border-blue-300 text-blue-700' 
                : 'bg-gray-100 border-gray-300 text-gray-700 hover:bg-gray-200'
            }`}
          >
            여러 파일
          </button>
          <button
            onClick={() => setUploadMode('directory')}
            className={`px-3 py-2 text-sm rounded-md border ${
              uploadMode === 'directory' 
                ? 'bg-blue-100 border-blue-300 text-blue-700' 
                : 'bg-gray-100 border-gray-300 text-gray-700 hover:bg-gray-200'
            }`}
          >
            디렉토리
          </button>
        </div>
      </div>

      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
          dragOver 
            ? 'border-blue-400 bg-blue-50' 
            : 'border-gray-300 hover:border-gray-400'
        } ${isUploading ? 'pointer-events-none opacity-50' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={openFileDialog}
      >
        <div className="space-y-4">
          <div className="text-4xl text-gray-400">📄</div>
          
          {isUploading ? (
            <div className="space-y-2">
              <div className="text-sm text-gray-600">업로드 중...</div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="text-gray-600">
                {uploadMode === 'single' && '파일을 드래그하여 놓거나 클릭하여 선택하세요'}
                {uploadMode === 'multiple' && '여러 파일을 드래그하여 놓거나 클릭하여 선택하세요'}
                {uploadMode === 'directory' && '디렉토리를 선택하여 모든 파일을 업로드하세요'}
              </div>
              <div className="text-sm text-gray-500">
                지원 형식: TXT, PDF, DOCX, HTML, MD, ZIP (최대 50MB)
              </div>
            </div>
          )}
        </div>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept=".txt,.pdf,.docx,.html,.md,.text,.log,.csv,.tsv,.htm,.xhtml,.markdown,.mdown,.mkd,.zip"
        onChange={handleFileSelect}
        className="hidden"
        disabled={isUploading}
        multiple={uploadMode === 'multiple'}
      />

      <input
        ref={directoryInputRef}
        type="file"
        onChange={handleDirectorySelect}
        className="hidden"
        disabled={isUploading}
        webkitdirectory=""
        multiple
      />

      {error && (
        <div className="mt-4 text-red-600 text-sm bg-red-50 p-3 rounded-md">
          {error}
        </div>
      )}
    </div>
  );
};

export default FileUploader;