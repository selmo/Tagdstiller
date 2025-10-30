"""
PDF 이미지 추출 및 멀티모달 LLM 분석 서비스
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import fitz  # PyMuPDF
import requests
from PIL import Image
import io

from services.config_service import ConfigService
from sqlalchemy.orm import Session

# OCR 관련 imports - 선택적 임포트
try:
    import pytesseract
    import cv2
    import numpy as np
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    pytesseract = None
    cv2 = None
    np = None

logger = logging.getLogger(__name__)


class ImageAnalyzer:
    """PDF 이미지 추출 및 멀티모달 LLM 분석"""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(__name__)

    def extract_full_text_from_scanned_pdf(self, file_path: Path, output_dir: Path) -> Dict[str, Any]:
        """스캔된 PDF 문서에서 전체 페이지 OCR을 통해 텍스트 추출"""
        if not OCR_AVAILABLE:
            self.logger.warning("⚠️ OCR 라이브러리가 없어 스캔 문서 처리를 건너뜀")
            return {
                "success": False,
                "error": "OCR libraries not available",
                "extracted_text": "",
                "pages_processed": 0
            }

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            doc = fitz.open(str(file_path))

            full_text = []
            pages_processed = 0
            total_pages = len(doc)

            self.logger.info(f"📄 스캔 문서 OCR 처리 시작: {total_pages}페이지")

            for page_num in range(total_pages):
                try:
                    # 페이지를 고해상도 이미지로 렌더링
                    page = doc.load_page(page_num)

                    # 해상도 설정 (DPI가 높을수록 OCR 정확도 향상)
                    zoom = 2  # 2배 확대
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat)

                    # PIL Image로 변환
                    img_data = pix.tobytes("png")
                    pil_image = Image.open(io.BytesIO(img_data))

                    # NumPy 배열로 변환
                    img_array = np.array(pil_image)

                    # 그레이스케일 변환
                    if len(img_array.shape) == 3:
                        img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                    else:
                        img_gray = img_array

                    # 이미지 전처리 (OCR 성능 향상)
                    # 1. 노이즈 제거
                    denoised = cv2.medianBlur(img_gray, 3)

                    # 2. 대비 향상
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                    enhanced = clahe.apply(denoised)

                    # 3. 이진화
                    _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

                    # OCR 실행 (한국어 + 영어)
                    page_text = pytesseract.image_to_string(
                        thresh,
                        lang='kor+eng',
                        config='--oem 3 --psm 6'  # 좋은 OCR 설정
                    )

                    # 페이지 텍스트 정리
                    page_text = page_text.strip()
                    if page_text:
                        full_text.append(f"=== 페이지 {page_num + 1} ===\n{page_text}")
                        pages_processed += 1
                        self.logger.info(f"✅ 페이지 {page_num + 1} OCR 완료 ({len(page_text)} 문자)")
                    else:
                        self.logger.info(f"⚪ 페이지 {page_num + 1} OCR 결과 없음")

                    # 메모리 정리
                    pix = None

                except Exception as e:
                    self.logger.warning(f"⚠️ 페이지 {page_num + 1} OCR 실패: {e}")
                    continue

            doc.close()

            # 전체 텍스트 결합
            extracted_text = "\n\n".join(full_text)

            # OCR 결과 파일로 저장
            ocr_file_path = output_dir / "full_document_ocr.txt"
            ocr_file_path.write_text(extracted_text, encoding='utf-8')

            result = {
                "success": True,
                "extracted_text": extracted_text,
                "pages_processed": pages_processed,
                "total_pages": total_pages,
                "ocr_file_path": str(ocr_file_path),
                "text_length": len(extracted_text)
            }

            self.logger.info(f"🎉 스캔 문서 OCR 완료: {pages_processed}/{total_pages}페이지, {len(extracted_text)}문자 추출")
            return result

        except Exception as e:
            self.logger.error(f"❌ 스캔 문서 OCR 처리 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "extracted_text": "",
                "pages_processed": 0
            }

    def extract_images_from_pdf(self, file_path: Path, output_dir: Path) -> List[Dict[str, Any]]:
        """PDF에서 이미지를 추출하여 파일로 저장"""
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            images_info = []

            doc = fitz.open(str(file_path))

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                image_list = page.get_images(full=True)

                for img_index, img in enumerate(image_list):
                    try:
                        # 이미지 데이터 추출
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)

                        # 이미지가 너무 작으면 스킵 (아이콘 등)
                        if pix.width < 50 or pix.height < 50:
                            pix = None
                            continue

                        # 이미지 파일명 생성
                        image_filename = f"page_{page_num + 1}_img_{img_index + 1}.png"
                        image_path = output_dir / image_filename

                        # PNG로 저장
                        if pix.n - pix.alpha < 4:  # GRAY or RGB
                            pix.save(str(image_path))
                        else:  # CMYK: convert to RGB first
                            pix1 = fitz.Pixmap(fitz.csRGB, pix)
                            pix1.save(str(image_path))
                            pix1 = None

                        # 이미지 정보 저장
                        image_info = {
                            "filename": image_filename,
                            "path": str(image_path),
                            "page": page_num + 1,
                            "width": pix.width,
                            "height": pix.height,
                            "size_bytes": image_path.stat().st_size if image_path.exists() else 0,
                            "format": "PNG"
                        }

                        images_info.append(image_info)
                        self.logger.info(f"📸 이미지 추출: {image_filename} ({pix.width}x{pix.height})")

                        pix = None

                    except Exception as e:
                        self.logger.warning(f"⚠️ 페이지 {page_num + 1}, 이미지 {img_index + 1} 추출 실패: {e}")
                        continue

            doc.close()
            self.logger.info(f"✅ 총 {len(images_info)}개 이미지 추출 완료")
            return images_info

        except Exception as e:
            self.logger.error(f"❌ PDF 이미지 추출 실패: {e}")
            return []

    def analyze_image_with_llm(self, image_path: Path, context: str = "", llm_config: Optional[Dict[str, Any]] = None, output_dir: Optional[Path] = None) -> Dict[str, Any]:
        """이미지 내용에 따른 차별화된 분석 수행"""
        if llm_config and llm_config.get("provider"):
            provider = llm_config["provider"]
        else:
            provider = ConfigService.get_config_value(self.db, "LLM_PROVIDER", "gemini")

        self.logger.info(f"🤖 이미지 분석 시작: provider={provider}, 이미지={image_path.name}")

        # 1. 이미지 콘텐츠 타입 판단 (텍스트 중심 vs 시각적 콘텐츠)
        content_type_analysis = self._analyze_image_content_type(image_path)
        is_text_heavy = content_type_analysis["is_text_heavy"]

        self.logger.info(f"📊 이미지 콘텐츠 분석: {content_type_analysis['content_type']} "
                        f"(텍스트 비율: {content_type_analysis['text_ratio']:.2f}, "
                        f"텍스트 중심: {is_text_heavy})")

        # 2. 콘텐츠 타입에 따른 차별화된 처리
        if is_text_heavy:
            # 텍스트 중심 이미지 -> OCR로 텍스트 추출
            result = self._extract_text_from_image(image_path, context)
            result["processing_method"] = "ocr_text_extraction"
        else:
            # 시각적 콘텐츠 -> 멀티모달 LLM으로 내용 분석
            if provider == "gemini":
                result = self._analyze_with_gemini(image_path, context, llm_config, output_dir)
            elif provider == "openai":
                result = self._analyze_with_openai(image_path, context, llm_config)
            else:
                result = {"success": False, "error": f"멀티모달 분석을 지원하지 않는 provider: {provider}"}
            result["processing_method"] = "multimodal_llm_analysis"

        # 3. 공통 메타데이터 추가
        result["content_type_analysis"] = content_type_analysis

        self.logger.info(f"🎯 이미지 분석 결과: success={result.get('success', False)}, "
                        f"처리방법={result.get('processing_method')}")
        return result

    def _analyze_with_gemini(self, image_path: Path, context: str, llm_config: Optional[Dict[str, Any]] = None, output_dir: Optional[Path] = None) -> Dict[str, Any]:
        """Gemini Vision으로 이미지 분석"""
        try:
            # LLM 설정 우선 사용, 없으면 기본 설정 사용
            if llm_config:
                conf = llm_config.copy()
                # 기본값으로 DB 설정 보완
                db_conf = ConfigService.get_gemini_config(self.db)
                for key, value in db_conf.items():
                    if key not in conf:
                        conf[key] = value
            else:
                conf = ConfigService.get_gemini_config(self.db)

            api_key = conf.get("api_key")
            model = conf.get("model", "gemini-2.0-flash-exp")

            if not api_key:
                return {"error": "GEMINI_API_KEY가 설정되지 않았습니다"}

            # 이미지를 base64로 인코딩
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')

            # 프롬프트 생성
            prompt_text = self._get_image_analysis_prompt(context)

            # Gemini API 호출용 payload
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt_text},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": image_data
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 2000,
                    "responseMimeType": "application/json"
                }
            }

            # 재시도 로직 (503 에러 대응)
            import time
            max_retries = 3
            retry_delay = 2

            url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={api_key}"

            for attempt in range(max_retries):
                try:
                    response = requests.post(url, json=payload, timeout=60)
                    response.raise_for_status()
                    break  # 성공하면 루프 종료
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 503 and attempt < max_retries - 1:
                        self.logger.warning(f"⚠️ Gemini Vision API 503 에러, {retry_delay}초 후 재시도 ({attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 지수 백오프
                    else:
                        raise  # 마지막 시도거나 다른 에러면 예외 발생

            data = response.json()

            # 토큰 사용량 추출 및 로깅
            usage_metadata = data.get("usageMetadata", {})
            prompt_tokens = usage_metadata.get("promptTokenCount", 0)
            response_tokens = usage_metadata.get("candidatesTokenCount", 0)
            total_tokens = usage_metadata.get("totalTokenCount", 0)

            if usage_metadata:
                self.logger.info(
                    f"📊 Gemini Vision 토큰 사용량 - 프롬프트: {prompt_tokens}, 응답: {response_tokens}, 총합: {total_tokens}"
                )

            # 응답 텍스트 추출
            text_chunks = []
            for candidate in data.get("candidates", []):
                parts = candidate.get("content", {}).get("parts", [])
                for part in parts:
                    if isinstance(part, dict) and "text" in part:
                        text_chunks.append(part["text"])

            if not text_chunks:
                return {"error": "Gemini 응답에서 텍스트를 찾을 수 없습니다"}

            # JSON 파싱 시도
            analysis_text = "".join(text_chunks).strip()

            # 프롬프트 및 응답 로깅 (output_dir이 제공된 경우)
            if output_dir:
                from utils.llm_logger import log_prompt_and_response
                log_prompt_and_response(
                    label=f"image_analysis_{image_path.stem}",
                    provider="gemini",
                    model=model,
                    prompt=prompt_text,
                    response=analysis_text,
                    logger=self.logger,
                    base_dir=str(output_dir),
                    request_data=payload,
                    response_data=data,
                    meta={
                        "image_file": str(image_path),
                        "image_size_bytes": image_path.stat().st_size,
                        "context": context,
                        "tokens": {
                            "prompt_tokens": prompt_tokens,
                            "response_tokens": response_tokens,
                            "total_tokens": total_tokens
                        }
                    }
                )

            try:
                analysis_json = json.loads(analysis_text)
                return {
                    "success": True,
                    "analysis": analysis_json,
                    "raw_response": analysis_text
                }
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "LLM 응답을 JSON으로 파싱할 수 없습니다",
                    "raw_response": analysis_text
                }

        except Exception as e:
            self.logger.error(f"❌ Gemini 이미지 분석 실패: {e}")
            return {"error": str(e)}

    def _analyze_with_openai(self, image_path: Path, context: str, llm_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """OpenAI Vision으로 이미지 분석"""
        try:
            # LLM 설정 우선 사용, 없으면 기본 설정 사용
            if llm_config:
                conf = llm_config.copy()
                # 기본값으로 DB 설정 보완
                db_conf = ConfigService.get_openai_config(self.db)
                for key, value in db_conf.items():
                    if key not in conf:
                        conf[key] = value
            else:
                conf = ConfigService.get_openai_config(self.db)

            api_key = conf.get("api_key")
            model = conf.get("model", "gpt-4-turbo")  # Vision 지원 모델 사용

            if not api_key:
                return {"error": "OPENAI_API_KEY가 설정되지 않았습니다"}

            # 이미지를 base64로 인코딩
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')

            # OpenAI API 호출용 payload
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self._get_image_analysis_prompt(context)},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_data}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 2000,
                "temperature": 0.2
            }

            response = requests.post(
                f"{conf.get('base_url', 'https://api.openai.com/v1')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=60
            )
            response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # JSON 파싱 시도
            try:
                analysis_json = json.loads(content)
                return {
                    "success": True,
                    "analysis": analysis_json,
                    "raw_response": content
                }
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "LLM 응답을 JSON으로 파싱할 수 없습니다",
                    "raw_response": content
                }

        except Exception as e:
            self.logger.error(f"❌ OpenAI 이미지 분석 실패: {e}")
            return {"error": str(e)}

    def _get_image_analysis_prompt(self, context: str) -> str:
        """시각적 콘텐츠 분석용 프롬프트 생성 (텍스트 추출 제외)"""
        prompt = """
**중요: 모든 응답은 반드시 한국어로 작성해주세요.**

이 이미지의 시각적 내용을 상세히 분석하여 JSON 형식으로 결과를 반환해주세요.
(참고: 텍스트 추출은 별도로 처리되므로, 시각적 요소와 내용 분석에 집중해주세요)

분석해야 할 요소:
1. 이미지 타입 (chart, diagram, photo, graph, flowchart, map, infographic 등)
2. 시각적 구조와 레이아웃
3. 주요 시각적 객체 및 요소들
4. 색상, 패턴, 스타일
5. 데이터 시각화 요소 (차트, 그래프, 표 등)
6. 문서에서의 역할과 중요도
7. 시각적으로 전달하는 주요 메시지나 개념

JSON 응답 형식:
{
  "image_type": "차트/다이어그램/사진/그래프/플로우차트 등",
  "visual_description": "이미지의 시각적 내용에 대한 상세한 설명",
  "visual_elements": {
    "colors": ["주요 색상들"],
    "shapes": ["도형이나 구조적 요소들"],
    "layout": "레이아웃 및 구성 설명",
    "patterns": ["패턴이나 반복 요소들"]
  },
  "content_analysis": {
    "main_message": "이미지가 전달하는 주요 메시지",
    "key_objects": ["주요 시각적 객체들"],
    "relationships": ["객체들 간의 관계나 흐름"],
    "significance": "문서에서의 역할과 중요성"
  },
  "data_visualization": {
    "chart_type": "차트 유형 (해당하는 경우)",
    "data_insights": ["데이터에서 도출할 수 있는 주요 인사이트"],
    "trends": ["보이는 트렌드나 패턴"]
  },
  "keywords": ["이미지에서 시각적으로 식별할 수 있는 주요 개념들"],
  "confidence_score": 0.0-1.0
}
"""

        if context.strip():
            prompt += f"\n\n문서 맥락:\n{context}\n\n위 맥락을 고려하여 이미지의 시각적 내용을 분석해주세요."

        return prompt

    def analyze_document_with_images(self, file_path: Path, text_content: str, output_dir: Path, llm_config: Optional[Dict[str, Any]] = None, filter_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """문서 전체를 텍스트와 이미지를 포함하여 종합 분석"""
        try:
            # 1. PDF 문서 타입 판단 (텍스트 기반 vs 이미지 기반)
            doc_type_analysis = self._analyze_pdf_type(file_path, text_content)
            self.logger.info(f"📄 PDF 문서 타입 분석: {doc_type_analysis['document_type']} "
                           f"(텍스트 밀도: {doc_type_analysis['text_density']:.3f}, "
                           f"이미지 비율: {doc_type_analysis['image_ratio']:.3f})")

            # 2. 이미지 추출
            images_info = self.extract_images_from_pdf(file_path, output_dir / "images")

            if not images_info:
                return {
                    "success": False,
                    "message": "추출된 이미지가 없습니다",
                    "images_count": 0,
                    "document_type_analysis": doc_type_analysis
                }

            # 2-1. 이미지 필터링 (설정이 있는 경우)
            original_count = len(images_info)
            if filter_config:
                images_info = self._filter_images(images_info, filter_config)
                filtered_count = original_count - len(images_info)
                if filtered_count > 0:
                    self.logger.info(f"🔍 이미지 필터링: {original_count}개 → {len(images_info)}개 ({filtered_count}개 제외)")

            # 2-2. 각 이미지 분석
            image_analyses = []
            for img_info in images_info:
                image_path = Path(img_info["path"])
                if image_path.exists():
                    # 이미지 주변 텍스트 맥락 제공 (페이지 정보 기반)
                    page_context = f"문서: {file_path.name}, 페이지: {img_info['page']}"

                    self.logger.info(f"🔍 이미지 분석 시작: {img_info['filename']}")
                    analysis = self.analyze_image_with_llm(image_path, page_context, llm_config, output_dir)
                    analysis["image_info"] = img_info
                    image_analyses.append(analysis)

                    if analysis.get("success"):
                        self.logger.info(f"✅ 이미지 분석 성공: {img_info['filename']}")
                    else:
                        error_msg = analysis.get("error", "Unknown error")
                        self.logger.error(f"❌ 이미지 분석 실패: {img_info['filename']} - {error_msg}")

            # 3. 종합 결과 생성
            result = {
                "success": True,
                "document_path": str(file_path),
                "document_type_analysis": doc_type_analysis,
                "images_count": len(images_info),
                "successful_analyses": len([a for a in image_analyses if a.get("success")]),
                "images_analysis": image_analyses,
                "summary": self._generate_image_summary(image_analyses),
                "extracted_keywords": self._extract_keywords_from_images(image_analyses),
                "processing_strategy": self._get_processing_strategy(doc_type_analysis, image_analyses)
            }

            # 4. 결과 저장
            result_file = output_dir / "image_analysis.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            self.logger.info(f"📊 이미지 분석 완료: {len(images_info)}개 추출, {result['successful_analyses']}개 분석 성공")
            return result

        except Exception as e:
            self.logger.error(f"❌ 문서 이미지 분석 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "images_count": 0
            }

    def _analyze_pdf_type(self, file_path: Path, text_content: str) -> Dict[str, Any]:
        """PDF 문서 타입 분석 (텍스트 기반 vs 이미지 기반)"""
        try:
            doc = fitz.open(str(file_path))

            total_pages = len(doc)
            total_text_chars = len(text_content.strip())
            total_images = 0
            pages_with_images = 0
            pages_with_text = 0

            # 각 페이지별로 텍스트와 이미지 분석
            for page_num in range(total_pages):
                page = doc.load_page(page_num)

                # 페이지별 텍스트 추출
                page_text = page.get_text().strip()
                if len(page_text) > 50:  # 의미있는 텍스트가 있는 페이지
                    pages_with_text += 1

                # 페이지별 이미지 개수
                page_images = page.get_images(full=True)
                if page_images:
                    pages_with_images += 1
                    total_images += len(page_images)

            doc.close()

            # 텍스트 밀도 계산 (페이지당 평균 문자 수)
            text_density = total_text_chars / total_pages if total_pages > 0 else 0

            # 이미지 비율 계산
            image_ratio = pages_with_images / total_pages if total_pages > 0 else 0

            # 문서 타입 판단
            document_type = self._determine_document_type(text_density, image_ratio, pages_with_text, total_pages)

            return {
                "document_type": document_type,
                "text_density": text_density,
                "image_ratio": image_ratio,
                "total_pages": total_pages,
                "pages_with_text": pages_with_text,
                "pages_with_images": pages_with_images,
                "total_images": total_images,
                "total_text_chars": total_text_chars,
                "analysis": self._get_document_type_analysis(document_type)
            }

        except Exception as e:
            self.logger.error(f"❌ PDF 타입 분석 실패: {e}")
            return {
                "document_type": "unknown",
                "error": str(e),
                "text_density": 0,
                "image_ratio": 0
            }

    def _determine_document_type(self, text_density: float, image_ratio: float, pages_with_text: int, total_pages: int) -> str:
        """문서 타입 결정 로직"""

        # 텍스트가 전혀 없는 경우 -> 순수 이미지 문서
        if text_density < 10 and pages_with_text == 0:
            return "pure_image"

        # 텍스트가 매우 적고 이미지가 많은 경우 -> 스캔 문서
        elif text_density < 100 and image_ratio > 0.7:
            return "scanned_document"

        # 텍스트가 적당하지만 이미지 비율이 높은 경우 -> 이미지 중심 문서
        elif text_density < 300 and image_ratio > 0.5:
            return "image_dominant"

        # 텍스트가 충분하고 이미지도 있는 경우 -> 하이브리드 문서
        elif text_density > 300 and image_ratio > 0.3:
            return "hybrid_document"

        # 텍스트가 많고 이미지가 적은 경우 -> 텍스트 중심 문서
        elif text_density > 300 and image_ratio < 0.3:
            return "text_dominant"

        # 기타 경우
        else:
            return "mixed_content"

    def _get_document_type_analysis(self, document_type: str) -> Dict[str, Any]:
        """문서 타입별 분석 전략 반환"""

        strategies = {
            "pure_image": {
                "description": "순수 이미지 문서 (스캔본)",
                "primary_strategy": "ocr_first",
                "image_analysis_priority": "high",
                "text_extraction_method": "ocr_based",
                "recommended_approach": "모든 이미지에 대해 OCR 수행 후 멀티모달 LLM 분석"
            },
            "scanned_document": {
                "description": "스캔된 문서",
                "primary_strategy": "ocr_enhanced",
                "image_analysis_priority": "high",
                "text_extraction_method": "ocr_based",
                "recommended_approach": "OCR로 텍스트 추출 후 이미지 구조 분석"
            },
            "image_dominant": {
                "description": "이미지 중심 문서",
                "primary_strategy": "image_first",
                "image_analysis_priority": "high",
                "text_extraction_method": "hybrid",
                "recommended_approach": "이미지 분석을 우선하고 텍스트로 보완"
            },
            "hybrid_document": {
                "description": "텍스트와 이미지 균형 문서",
                "primary_strategy": "balanced",
                "image_analysis_priority": "medium",
                "text_extraction_method": "native_plus_ocr",
                "recommended_approach": "텍스트와 이미지 분석을 동등하게 수행"
            },
            "text_dominant": {
                "description": "텍스트 중심 문서",
                "primary_strategy": "text_first",
                "image_analysis_priority": "low",
                "text_extraction_method": "native",
                "recommended_approach": "텍스트 분석 중심, 핵심 이미지만 선별 분석"
            },
            "mixed_content": {
                "description": "혼합 콘텐츠 문서",
                "primary_strategy": "adaptive",
                "image_analysis_priority": "medium",
                "text_extraction_method": "hybrid",
                "recommended_approach": "페이지별 적응적 분석"
            }
        }

        return strategies.get(document_type, {
            "description": "알 수 없는 문서 타입",
            "primary_strategy": "default",
            "image_analysis_priority": "medium",
            "text_extraction_method": "native",
            "recommended_approach": "기본 분석 수행"
        })

    def _filter_images(self, images_info: List[Dict[str, Any]], filter_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """이미지 필터링 - 작은 로고/아이콘 제외, 중복 크기 이미지 제거"""
        min_width = filter_config.get("min_width", 100)
        min_height = filter_config.get("min_height", 100)
        skip_duplicates = filter_config.get("skip_duplicates", False)

        filtered = []
        seen_sizes = set()  # 중복 감지용 (width, height)

        for img_info in images_info:
            width = img_info.get("width", 0)
            height = img_info.get("height", 0)

            # 1. 최소 크기 필터
            if width < min_width or height < min_height:
                self.logger.debug(f"⏭️ 작은 이미지 제외: {img_info['filename']} ({width}x{height})")
                continue

            # 2. 중복 크기 필터 (같은 크기 이미지는 반복되는 로고/헤더일 가능성 높음)
            if skip_duplicates:
                size_key = (width, height)
                if size_key in seen_sizes:
                    self.logger.debug(f"⏭️ 중복 크기 이미지 제외: {img_info['filename']} ({width}x{height})")
                    continue
                seen_sizes.add(size_key)

            filtered.append(img_info)

        return filtered

    def _get_processing_strategy(self, doc_type_analysis: Dict[str, Any], image_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """문서 타입과 이미지 분석 결과를 바탕으로 처리 전략 제안"""

        document_type = doc_type_analysis.get("document_type", "unknown")
        analysis_strategy = doc_type_analysis.get("analysis", {})

        successful_analyses = len([a for a in image_analyses if a.get("success")])
        total_images = len(image_analyses)

        # 이미지 분석 성공률
        success_rate = successful_analyses / total_images if total_images > 0 else 0

        # 전략별 권장사항
        recommendations = []

        if document_type == "pure_image" or document_type == "scanned_document":
            recommendations.append("📄 스캔 문서로 판단됨 - OCR 기반 텍스트 추출 권장")
            recommendations.append("🖼️ 모든 이미지에 대해 멀티모달 LLM 분석 수행")
            if success_rate < 0.8:
                recommendations.append("⚠️ 이미지 분석 성공률이 낮음 - OCR 전용 도구 추가 고려")

        elif document_type == "image_dominant":
            recommendations.append("🎨 이미지 중심 문서 - 시각적 정보 우선 분석")
            recommendations.append("📊 차트, 다이어그램, 표 등의 구조적 요소 집중 분석")

        elif document_type == "hybrid_document":
            recommendations.append("🔄 텍스트와 이미지 균형 문서 - 통합 분석 수행")
            recommendations.append("🔗 텍스트와 이미지 간의 상관관계 분석")

        elif document_type == "text_dominant":
            recommendations.append("📝 텍스트 중심 문서 - 핵심 이미지만 선별 분석")
            recommendations.append("🎯 보조 자료로서의 이미지 역할 분석")

        # 성공률 기반 추가 권장사항
        if success_rate > 0.9:
            recommendations.append("✅ 이미지 분석 성공률 매우 높음 - 현재 설정 유지 권장")
        elif success_rate > 0.7:
            recommendations.append("✅ 이미지 분석 성공률 양호 - 현재 설정 유지")
        elif success_rate > 0.5:
            recommendations.append("⚠️ 이미지 분석 성공률 보통 - LLM 모델 변경 고려")
        else:
            recommendations.append("❌ 이미지 분석 성공률 낮음 - 설정 검토 필요")

        return {
            "document_type": document_type,
            "primary_strategy": analysis_strategy.get("primary_strategy", "default"),
            "image_analysis_priority": analysis_strategy.get("image_analysis_priority", "medium"),
            "success_rate": success_rate,
            "recommendations": recommendations,
            "next_steps": self._get_next_steps(document_type, success_rate)
        }

    def _get_next_steps(self, document_type: str, success_rate: float) -> List[str]:
        """문서 타입과 성공률에 따른 다음 단계 제안"""

        next_steps = []

        if document_type in ["pure_image", "scanned_document"]:
            next_steps.extend([
                "1. 추출된 텍스트와 이미지 정보를 통합하여 완전한 문서 재구성",
                "2. OCR 정확도 검증 및 수동 보정 필요 여부 확인",
                "3. 구조화된 데이터로 변환 (테이블, 목록 등)"
            ])

        elif document_type == "image_dominant":
            next_steps.extend([
                "1. 시각적 요소들 간의 관계 분석 및 플로우 차트 생성",
                "2. 이미지에서 추출한 키워드와 텍스트 키워드 통합",
                "3. 시각적 정보의 계층 구조 파악"
            ])

        elif document_type == "hybrid_document":
            next_steps.extend([
                "1. 텍스트-이미지 간 참조 관계 매핑",
                "2. 문서의 전체적인 정보 흐름 분석",
                "3. 통합된 지식 그래프 생성"
            ])

        else:  # text_dominant, mixed_content
            next_steps.extend([
                "1. 핵심 이미지와 관련된 텍스트 섹션 식별",
                "2. 이미지가 보완하는 정보의 중요도 평가",
                "3. 텍스트 중심의 요약에 시각적 정보 통합"
            ])

        # 성공률이 낮을 때의 추가 단계
        if success_rate < 0.5:
            next_steps.insert(0, "0. 이미지 분석 실패 원인 조사 및 대안 방법 모색")

        return next_steps

    def _generate_image_summary(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """이미지 분석 결과 요약 (OCR 텍스트 추출 및 시각적 분석 포함)"""
        successful = [a for a in analyses if a.get("success")]

        if not successful:
            return {"message": "성공한 이미지 분석이 없습니다"}

        # 처리 방법별 통계
        processing_methods = {}
        image_types = {}
        all_keywords = []
        total_extracted_text_length = 0
        ocr_analyses = []
        visual_analyses = []

        for analysis in successful:
            # 처리 방법 통계
            method = analysis.get("processing_method", "unknown")
            processing_methods[method] = processing_methods.get(method, 0) + 1

            # OCR 텍스트 추출 결과
            if method == "ocr_text_extraction":
                ocr_analyses.append(analysis)
                extracted_text = analysis.get("extracted_text", "")
                total_extracted_text_length += len(extracted_text)

                # OCR 키워드
                if "text_analysis" in analysis:
                    ocr_keywords = analysis["text_analysis"].get("top_keywords", [])
                    all_keywords.extend(ocr_keywords)

            # 멀티모달 LLM 시각적 분석 결과
            elif method == "multimodal_llm_analysis":
                visual_analyses.append(analysis)
                if "analysis" in analysis:
                    img_type = analysis["analysis"].get("image_type", "unknown")
                    image_types[img_type] = image_types.get(img_type, 0) + 1

                    keywords = analysis["analysis"].get("keywords", [])
                    all_keywords.extend(keywords)

        return {
            "total_analyzed": len(successful),
            "processing_summary": {
                "methods_used": processing_methods,
                "ocr_extractions": len(ocr_analyses),
                "visual_analyses": len(visual_analyses)
            },
            "ocr_results": {
                "total_text_length": total_extracted_text_length,
                "average_text_per_image": total_extracted_text_length / len(ocr_analyses) if ocr_analyses else 0
            },
            "visual_analysis": {
                "image_types": image_types,
                "average_confidence": sum(
                    a.get("analysis", {}).get("confidence_score", 0) for a in visual_analyses
                ) / len(visual_analyses) if visual_analyses else 0
            },
            "combined_keywords": list(set(all_keywords))[:30],  # 상위 30개
            "keyword_sources": {
                "from_ocr": len([kw for analysis in ocr_analyses for kw in analysis.get("text_analysis", {}).get("top_keywords", [])]),
                "from_visual": len([kw for analysis in visual_analyses for kw in analysis.get("analysis", {}).get("keywords", [])])
            }
        }

    def _analyze_image_content_type(self, image_path: Path) -> Dict[str, Any]:
        """이미지의 콘텐츠 타입 분석 (텍스트 중심 vs 시각적 콘텐츠)"""
        try:
            # OCR 사용 불가능한 경우 기본값으로 visual 처리
            if not OCR_AVAILABLE:
                self.logger.warning("⚠️ OCR 라이브러리가 설치되지 않아 모든 이미지를 시각적 콘텐츠로 처리합니다")
                with Image.open(image_path) as img:
                    width, height = img.size
                return {
                    "content_type": "mostly_visual",
                    "is_text_heavy": False,
                    "text_length": 0,
                    "text_density": 0,
                    "text_ratio": 0,
                    "image_size": {"width": width, "height": height},
                    "extracted_text_preview": "",
                    "ocr_available": False
                }

            # OCR로 텍스트 추출하여 텍스트 비율 측정
            text_content = self._extract_text_with_ocr(image_path)
            text_length = len(text_content.strip())

            # 이미지 크기 정보 얻기
            with Image.open(image_path) as img:
                width, height = img.size
                total_pixels = width * height

            # 텍스트 밀도 계산 (픽셀당 텍스트 문자 수)
            text_density = text_length / total_pixels if total_pixels > 0 else 0

            # 텍스트 비율 추정 (임의 기준점 사용)
            text_ratio = min(text_length / 100, 1.0)  # 100자를 기준으로 정규화

            # 텍스트 중심 이미지 판단 기준
            is_text_heavy = (
                text_length > 50 and  # 최소 50자 이상
                (text_density > 0.001 or text_ratio > 0.3)  # 밀도가 높거나 텍스트 비율이 높음
            )

            # 콘텐츠 타입 결정
            if text_length == 0:
                content_type = "pure_visual"
            elif is_text_heavy:
                content_type = "text_dominant"
            elif text_length > 10:
                content_type = "mixed_content"
            else:
                content_type = "mostly_visual"

            return {
                "content_type": content_type,
                "is_text_heavy": is_text_heavy,
                "text_length": text_length,
                "text_density": text_density,
                "text_ratio": text_ratio,
                "image_size": {"width": width, "height": height},
                "extracted_text_preview": text_content[:100] + "..." if len(text_content) > 100 else text_content
            }

        except Exception as e:
            self.logger.error(f"❌ 이미지 콘텐츠 타입 분석 실패: {e}")
            return {
                "content_type": "unknown",
                "is_text_heavy": False,
                "error": str(e),
                "text_length": 0,
                "text_density": 0,
                "text_ratio": 0
            }

    def _extract_text_with_ocr(self, image_path: Path) -> str:
        """OCR을 사용하여 이미지에서 텍스트 추출"""
        if not OCR_AVAILABLE:
            self.logger.warning("⚠️ OCR 라이브러리가 설치되지 않아 텍스트 추출을 건너뜁니다")
            return ""

        try:
            # 이미지 전처리 (OCR 정확도 향상을 위해)
            image = cv2.imread(str(image_path))
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # 노이즈 제거 및 이미지 향상
            denoised = cv2.fastNlMeansDenoising(gray)

            # OCR 실행 (한국어 + 영어 지원)
            custom_config = r'--oem 3 --psm 6 -l kor+eng'
            text = pytesseract.image_to_string(denoised, config=custom_config)

            return text.strip()

        except Exception as e:
            self.logger.warning(f"⚠️ OCR 텍스트 추출 실패: {e}")
            # OCR 실패 시 기본 pytesseract 시도
            try:
                text = pytesseract.image_to_string(Image.open(image_path), lang='kor+eng')
                return text.strip()
            except Exception as e2:
                self.logger.error(f"❌ 기본 OCR도 실패: {e2}")
                return ""

    def _extract_text_from_image(self, image_path: Path, context: str = "") -> Dict[str, Any]:
        """텍스트 중심 이미지에서 텍스트를 추출하여 반환"""
        try:
            if not OCR_AVAILABLE:
                return {
                    "success": False,
                    "error": "OCR 라이브러리가 설치되지 않아 텍스트 추출을 수행할 수 없습니다",
                    "extracted_text": "",
                    "ocr_available": False
                }

            # OCR로 텍스트 추출
            extracted_text = self._extract_text_with_ocr(image_path)

            if not extracted_text.strip():
                return {
                    "success": False,
                    "error": "이미지에서 텍스트를 추출할 수 없습니다",
                    "extracted_text": "",
                    "ocr_available": True
                }

            # 텍스트 정리 및 구조화
            cleaned_text = self._clean_extracted_text(extracted_text)

            # 간단한 텍스트 분석
            text_analysis = self._analyze_extracted_text(cleaned_text)

            result = {
                "success": True,
                "method": "ocr_extraction",
                "extracted_text": cleaned_text,
                "raw_text": extracted_text,
                "text_analysis": text_analysis,
                "context": context
            }

            self.logger.info(f"✅ OCR 텍스트 추출 성공: {len(cleaned_text)}자 추출")
            return result

        except Exception as e:
            self.logger.error(f"❌ 텍스트 추출 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "extracted_text": ""
            }

    def _clean_extracted_text(self, text: str) -> str:
        """OCR로 추출한 텍스트 정리"""
        # 여러 공백을 하나로
        import re
        cleaned = re.sub(r'\s+', ' ', text)

        # 줄바꿈 정리
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)

        # 앞뒤 공백 제거
        cleaned = cleaned.strip()

        return cleaned

    def _analyze_extracted_text(self, text: str) -> Dict[str, Any]:
        """추출된 텍스트의 간단한 분석"""
        words = text.split()
        lines = text.split('\n')

        # 기본 통계
        stats = {
            "total_characters": len(text),
            "total_words": len(words),
            "total_lines": len(lines),
            "avg_words_per_line": len(words) / len(lines) if lines else 0
        }

        # 언어 감지 (간단한 휴리스틱)
        korean_chars = len([c for c in text if '가' <= c <= '힣'])
        english_chars = len([c for c in text if c.isalpha() and c.isascii()])

        if korean_chars > english_chars:
            primary_language = "korean"
        elif english_chars > 0:
            primary_language = "english"
        else:
            primary_language = "unknown"

        # 간단한 키워드 추출 (빈도 기반)
        word_freq = {}
        for word in words:
            if len(word) > 2:  # 2자 이상만
                word_freq[word] = word_freq.get(word, 0) + 1

        top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "statistics": stats,
            "primary_language": primary_language,
            "language_distribution": {
                "korean_chars": korean_chars,
                "english_chars": english_chars
            },
            "top_keywords": [word for word, freq in top_keywords],
            "keyword_frequencies": dict(top_keywords)
        }

    def _extract_keywords_from_images(self, analyses: List[Dict[str, Any]]) -> List[str]:
        """이미지 분석에서 키워드 추출 (OCR 결과 포함)"""
        all_keywords = []

        for analysis in analyses:
            if analysis.get("success"):
                # 멀티모달 LLM 분석 결과에서 키워드 추출
                if "analysis" in analysis:
                    keywords = analysis["analysis"].get("keywords", [])
                    all_keywords.extend(keywords)

                # OCR 텍스트 추출 결과에서 키워드 추출
                if "text_analysis" in analysis:
                    ocr_keywords = analysis["text_analysis"].get("top_keywords", [])
                    all_keywords.extend(ocr_keywords)

        # 중복 제거 및 빈도 기반 정렬
        keyword_freq = {}
        for kw in all_keywords:
            keyword_freq[kw] = keyword_freq.get(kw, 0) + 1

        return sorted(keyword_freq.keys(), key=lambda x: keyword_freq[x], reverse=True)