"""
청크별 프롬프트 관리 및 로깅 시스템

각 청크에 대해 개별적인 프롬프트 생성, 실행 로그, 결과 파일을 관리합니다.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import uuid

from prompts.templates import get_prompt_template, list_available_templates


@dataclass
class ChunkPromptRequest:
    """청크 프롬프트 요청 정보"""
    chunk_id: str
    chunk_level: str
    content: str
    content_length: int

    # 프롬프트 설정
    prompt_category: str  # "keyword_extraction", "document_summary", etc.
    prompt_template: str  # "basic_ko", "academic", etc.
    prompt_parameters: Dict[str, Any]

    # 메타데이터
    source_file: str
    chunk_context: Dict[str, Any]
    request_timestamp: str = None

    def __post_init__(self):
        if self.request_timestamp is None:
            self.request_timestamp = datetime.now().isoformat()


@dataclass
class ChunkPromptResult:
    """청크 프롬프트 실행 결과"""
    request_id: str
    chunk_id: str

    # 프롬프트 정보
    generated_prompt: str
    prompt_length: int

    # 실행 결과
    llm_response: str
    response_length: int
    processing_time_seconds: float

    # 상태 정보
    success: bool
    completion_timestamp: str

    # 선택적 필드들
    error_message: Optional[str] = None
    llm_provider: str = "unknown"
    llm_model: str = "unknown"

    def __post_init__(self):
        if not hasattr(self, 'completion_timestamp') or self.completion_timestamp is None:
            self.completion_timestamp = datetime.now().isoformat()


class ChunkPromptManager:
    """청크별 프롬프트 관리 시스템"""

    def __init__(self, base_output_directory: str):
        self.base_output_directory = Path(base_output_directory)
        self.logger = logging.getLogger(__name__)

        # 디렉토리 구조 생성
        self.prompts_dir = self.base_output_directory / "chunk_prompts"
        self.logs_dir = self.base_output_directory / "chunk_logs"
        self.results_dir = self.base_output_directory / "chunk_results"

        for directory in [self.prompts_dir, self.logs_dir, self.results_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"📁 청크 프롬프트 관리자 초기화: {self.base_output_directory}")

    def create_chunk_prompt_set(
        self,
        chunk_info: Dict[str, Any],
        source_file: str,
        prompt_categories: List[str] = None
    ) -> List[ChunkPromptRequest]:
        """
        청크에 대한 전체 프롬프트 세트를 생성합니다.

        Args:
            chunk_info: 청크 정보
            source_file: 원본 파일 경로
            prompt_categories: 생성할 프롬프트 카테고리 목록

        Returns:
            List[ChunkPromptRequest]: 프롬프트 요청 목록
        """
        chunk_id = chunk_info.get('chunk_id', 'unknown')
        chunk_level = chunk_info.get('level', 'unknown')

        # 우선순위로 전체 콘텐츠 추출 시도
        content = ''

        # 1순위: ChunkAnalyzer에서 제공한 full_content
        if 'full_content' in chunk_info:
            content = chunk_info['full_content']
            self.logger.info(f"✅ full_content 키 사용: {len(content)}자")

        # 2순위: chunks_text 디렉토리에서 텍스트 파일 읽기
        elif Path(self.output_directory).exists():
            chunk_text_file = Path(self.output_directory) / "chunks_text" / f"{chunk_id}.txt"
            if chunk_text_file.exists():
                content = chunk_text_file.read_text(encoding='utf-8')
                self.logger.info(f"✅ 청크 텍스트 파일에서 전체 콘텐츠 로드: {len(content)}자")

        # 3순위: content_preview 사용
        if not content or len(content.strip()) < 50:
            content = chunk_info.get('content_preview', '')
            self.logger.info(f"🔄 content_preview 폴백 사용: {len(content)}자")

        # 디버그: 최종 콘텐츠 확인
        self.logger.info(f"🔍 청크 {chunk_id} 최종 콘텐츠 길이: {len(content)}자")
        if not content:
            all_keys = list(chunk_info.keys())
            self.logger.warning(f"⚠️ 모든 방법으로도 콘텐츠를 찾을 수 없음. 사용 가능한 키들: {all_keys}")

            # 마지막 대안으로 다른 콘텐츠 키들을 시도
            for alt_key in ['content', 'text', 'full_content']:
                if alt_key in chunk_info and chunk_info[alt_key]:
                    content = chunk_info[alt_key]
                    self.logger.info(f"✅ 최종 대안 키 '{alt_key}' 사용: {len(content)}자")
                    break

        # 최종 검증: 콘텐츠가 여전히 비어있으면 에러
        if not content or len(content.strip()) == 0:
            error_msg = f"청크 {chunk_id}의 콘텐츠가 비어있습니다. 프롬프트 생성을 건너뜁니다."
            self.logger.error(f"❌ {error_msg}")
            return []  # 빈 리스트 반환

        # 기본 프롬프트 카테고리 설정
        if prompt_categories is None:
            prompt_categories = ['keyword_extraction', 'document_summary', 'structure_analysis']

        requests = []

        self.logger.info(f"🎯 청크 {chunk_id}에 대한 프롬프트 세트 생성 시작 (최종 콘텐츠 길이: {len(content)}자)")

        for category in prompt_categories:
            category_requests = self._create_category_prompts(
                chunk_info=chunk_info,
                source_file=source_file,
                category=category,
                content=content,
                chunk_id=chunk_id,
                chunk_level=chunk_level
            )
            requests.extend(category_requests)

        # 프롬프트 요청들을 파일로 저장
        self._save_prompt_requests(chunk_id, requests)

        self.logger.info(f"✅ 청크 {chunk_id}: {len(requests)}개 프롬프트 요청 생성 완료")
        return requests

    def _create_category_prompts(
        self,
        chunk_info: Dict[str, Any],
        source_file: str,
        category: str,
        content: str,
        chunk_id: str,
        chunk_level: str
    ) -> List[ChunkPromptRequest]:
        """카테고리별 프롬프트 생성"""

        requests = []
        available_templates = list_available_templates()

        if category not in available_templates:
            self.logger.warning(f"⚠️ 알 수 없는 프롬프트 카테고리: {category}")
            return requests

        templates = available_templates[category]

        for template_name in templates:
            try:
                # 템플릿별 기본 파라미터 생성
                parameters = self._get_template_parameters(category, template_name, content)

                request = ChunkPromptRequest(
                    chunk_id=chunk_id,
                    chunk_level=chunk_level,
                    content=content,
                    content_length=len(content),
                    prompt_category=category,
                    prompt_template=template_name,
                    prompt_parameters=parameters,
                    source_file=source_file,
                    chunk_context=chunk_info
                )

                requests.append(request)

            except Exception as e:
                self.logger.error(f"❌ 프롬프트 생성 실패 ({category}.{template_name}): {str(e)}")

        return requests

    def _get_template_parameters(self, category: str, template_name: str, content: str) -> Dict[str, Any]:
        """템플릿별 기본 파라미터 생성"""

        base_params = {
            'text': content
        }

        if category == 'keyword_extraction':
            base_params.update({
                'max_keywords': 10,
            })
        elif category == 'knowledge_graph':
            base_params.update({
                'domain': 'general',
                'structure_info': '{"type": "chunk_analysis"}'
            })

        return base_params

    def generate_prompt(self, request: ChunkPromptRequest) -> str:
        """프롬프트 요청에서 실제 프롬프트 텍스트 생성"""

        try:
            prompt_text = get_prompt_template(
                category=request.prompt_category,
                template_name=request.prompt_template,
                **request.prompt_parameters
            )

            # 생성된 프롬프트를 파일로 저장
            self._save_generated_prompt(request, prompt_text)

            return prompt_text

        except Exception as e:
            self.logger.error(f"❌ 프롬프트 생성 실패: {str(e)}")
            raise

    def execute_prompt(self, request: ChunkPromptRequest, llm_executor) -> ChunkPromptResult:
        """
        프롬프트를 실행하고 결과를 기록합니다.

        Args:
            request: 프롬프트 요청
            llm_executor: LLM 실행 함수 (prompt_text -> response_text)

        Returns:
            ChunkPromptResult: 실행 결과
        """
        request_id = str(uuid.uuid4())
        start_time = datetime.now()

        self.logger.info(f"🚀 프롬프트 실행 시작: {request.chunk_id} ({request.prompt_category}.{request.prompt_template})")

        try:
            # 프롬프트 생성
            generated_prompt = self.generate_prompt(request)

            # LLM 실행
            llm_response = llm_executor(generated_prompt)

            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            result = ChunkPromptResult(
                request_id=request_id,
                chunk_id=request.chunk_id,
                generated_prompt=generated_prompt,
                prompt_length=len(generated_prompt),
                llm_response=llm_response,
                response_length=len(llm_response),
                processing_time_seconds=processing_time,
                success=True,
                completion_timestamp=end_time.isoformat()
            )

            # 결과 저장
            self._save_prompt_result(request, result)

            self.logger.info(f"✅ 프롬프트 실행 완료: {request.chunk_id} (소요시간: {processing_time:.2f}초)")

            return result

        except Exception as e:
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            result = ChunkPromptResult(
                request_id=request_id,
                chunk_id=request.chunk_id,
                generated_prompt=generated_prompt if 'generated_prompt' in locals() else "",
                prompt_length=len(generated_prompt) if 'generated_prompt' in locals() else 0,
                llm_response="",
                response_length=0,
                processing_time_seconds=processing_time,
                success=False,
                error_message=str(e),
                completion_timestamp=end_time.isoformat()
            )

            # 오류 결과도 저장
            self._save_prompt_result(request, result)

            self.logger.error(f"❌ 프롬프트 실행 실패: {request.chunk_id} - {str(e)}")

            return result

    def _save_prompt_requests(self, chunk_id: str, requests: List[ChunkPromptRequest]):
        """프롬프트 요청들을 파일로 저장"""

        requests_file = self.prompts_dir / f"{chunk_id}_prompt_requests.json"

        requests_data = {
            'chunk_id': chunk_id,
            'total_requests': len(requests),
            'created_at': datetime.now().isoformat(),
            'requests': [asdict(req) for req in requests]
        }

        with open(requests_file, 'w', encoding='utf-8') as f:
            json.dump(requests_data, f, ensure_ascii=False, indent=2)

        self.logger.debug(f"💾 프롬프트 요청 저장: {requests_file}")

    def _save_generated_prompt(self, request: ChunkPromptRequest, prompt_text: str):
        """생성된 프롬프트를 텍스트 파일로 저장"""

        prompt_filename = f"{request.chunk_id}_{request.prompt_category}_{request.prompt_template}.txt"
        prompt_file = self.prompts_dir / prompt_filename

        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(f"# 청크 프롬프트: {request.chunk_id}\n")
            f.write(f"카테고리: {request.prompt_category}\n")
            f.write(f"템플릿: {request.prompt_template}\n")
            f.write(f"생성일시: {datetime.now().isoformat()}\n")
            f.write(f"청크 레벨: {request.chunk_level}\n")
            f.write(f"콘텐츠 길이: {request.content_length}\n")
            f.write("=" * 80 + "\n\n")
            f.write(prompt_text)

        self.logger.debug(f"💾 프롬프트 파일 저장: {prompt_file}")

    def _save_prompt_result(self, request: ChunkPromptRequest, result: ChunkPromptResult):
        """프롬프트 실행 결과를 저장"""

        # JSON 결과 파일
        result_filename = f"{request.chunk_id}_{request.prompt_category}_{request.prompt_template}_result.json"
        result_file = self.results_dir / result_filename

        result_data = {
            'request_info': asdict(request),
            'execution_result': asdict(result),
            'metadata': {
                'saved_at': datetime.now().isoformat(),
                'result_file': str(result_file)
            }
        }

        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        # 텍스트 응답 파일 (가독성을 위해)
        response_filename = f"{request.chunk_id}_{request.prompt_category}_{request.prompt_template}_response.txt"
        response_file = self.results_dir / response_filename

        with open(response_file, 'w', encoding='utf-8') as f:
            f.write(f"# LLM 응답: {request.chunk_id}\n")
            f.write(f"카테고리: {request.prompt_category}\n")
            f.write(f"템플릿: {request.prompt_template}\n")
            f.write(f"실행일시: {result.completion_timestamp}\n")
            f.write(f"성공여부: {'성공' if result.success else '실패'}\n")
            if result.error_message:
                f.write(f"오류메시지: {result.error_message}\n")
            f.write(f"처리시간: {result.processing_time_seconds:.2f}초\n")
            f.write(f"응답길이: {result.response_length}자\n")
            f.write("=" * 80 + "\n\n")
            f.write(result.llm_response)

        # 로그 파일 업데이트
        self._update_chunk_log(request, result)

        self.logger.debug(f"💾 실행 결과 저장: {result_file}, {response_file}")

    def _update_chunk_log(self, request: ChunkPromptRequest, result: ChunkPromptResult):
        """청크별 실행 로그 업데이트"""

        log_file = self.logs_dir / f"{request.chunk_id}_execution_log.jsonl"

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'chunk_id': request.chunk_id,
            'prompt_category': request.prompt_category,
            'prompt_template': request.prompt_template,
            'success': result.success,
            'processing_time': result.processing_time_seconds,
            'prompt_length': result.prompt_length,
            'response_length': result.response_length,
            'error_message': result.error_message
        }

        # JSONL 형식으로 추가 (한 줄씩 JSON 객체)
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

    def get_chunk_prompt_summary(self, chunk_id: str) -> Dict[str, Any]:
        """청크의 프롬프트 실행 요약 정보 반환"""

        log_file = self.logs_dir / f"{chunk_id}_execution_log.jsonl"

        if not log_file.exists():
            return {
                'chunk_id': chunk_id,
                'total_executions': 0,
                'successful_executions': 0,
                'failed_executions': 0,
                'total_processing_time': 0,
                'average_processing_time': 0,
                'executions': []
            }

        executions = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                executions.append(json.loads(line.strip()))

        successful = len([ex for ex in executions if ex.get('success', False)])
        failed = len(executions) - successful
        total_time = sum(ex.get('processing_time', 0) for ex in executions)

        return {
            'chunk_id': chunk_id,
            'total_executions': len(executions),
            'successful_executions': successful,
            'failed_executions': failed,
            'total_processing_time': total_time,
            'average_processing_time': total_time / len(executions) if executions else 0,
            'executions': executions
        }

    def generate_chunk_report(self, chunk_id: str) -> str:
        """청크의 전체 분석 보고서 생성"""

        summary = self.get_chunk_prompt_summary(chunk_id)

        report_lines = [
            f"# 청크 분석 보고서: {chunk_id}",
            f"생성일시: {datetime.now().isoformat()}",
            "",
            "## 실행 요약",
            f"- 총 실행 횟수: {summary['total_executions']}",
            f"- 성공: {summary['successful_executions']}",
            f"- 실패: {summary['failed_executions']}",
            f"- 총 처리 시간: {summary['total_processing_time']:.2f}초",
            f"- 평균 처리 시간: {summary['average_processing_time']:.2f}초",
            "",
            "## 실행 세부 내역"
        ]

        for i, execution in enumerate(summary['executions'], 1):
            status = "✅" if execution.get('success', False) else "❌"
            report_lines.extend([
                f"### {i}. {execution.get('prompt_category', 'unknown')}.{execution.get('prompt_template', 'unknown')} {status}",
                f"- 실행시각: {execution.get('timestamp', 'unknown')}",
                f"- 처리시간: {execution.get('processing_time', 0):.2f}초",
                f"- 프롬프트 길이: {execution.get('prompt_length', 0):,}자",
                f"- 응답 길이: {execution.get('response_length', 0):,}자",
            ])

            if execution.get('error_message'):
                report_lines.append(f"- 오류: {execution['error_message']}")

            report_lines.append("")

        return "\n".join(report_lines)


__all__ = ["ChunkPromptManager", "ChunkPromptRequest", "ChunkPromptResult"]