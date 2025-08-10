import React from 'react';
import { useState } from 'react';
import { projectApi } from '../services/api';
import { Project } from '../types/api';

interface ProjectFormProps {
  onProjectCreated: (project: Project) => void;
}

const ProjectForm: React.FC<ProjectFormProps> = ({ onProjectCreated }: ProjectFormProps) => {
  const [projectName, setProjectName] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!projectName.trim()) {
      setError('프로젝트 이름을 입력해주세요.');
      return;
    }

    setIsCreating(true);
    setError(null);

    try {
      console.log('프로젝트 생성 요청:', projectName.trim());
      const newProject = await projectApi.create(projectName.trim());
      console.log('프로젝트 생성 성공:', newProject);
      setProjectName('');
      onProjectCreated(newProject);
    } catch (err: any) {
      console.error('프로젝트 생성 실패:', err);
      console.error('응답 데이터:', err.response?.data);
      console.error('응답 상태:', err.response?.status);
      setError(err.response?.data?.detail || '프로젝트 생성에 실패했습니다.');
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h2 className="text-xl font-semibold mb-4">새 프로젝트 생성</h2>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="projectName" className="block text-sm font-medium text-gray-700 mb-2">
            프로젝트 이름
          </label>
          <input
            type="text"
            id="projectName"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="프로젝트 이름을 입력하세요"
            disabled={isCreating}
          />
        </div>

        {error && (
          <div className="text-red-600 text-sm bg-red-50 p-3 rounded-md">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={isCreating || !projectName.trim()}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {isCreating ? '생성 중...' : '프로젝트 생성'}
        </button>
      </form>
    </div>
  );
};

export default ProjectForm;