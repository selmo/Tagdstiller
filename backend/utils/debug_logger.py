"""
디버그 로깅 시스템
키워드 추출 과정의 각 단계별 중간 결과물을 저장하고 분석할 수 있도록 지원
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import numpy as np


class DebugLogger:
    """키워드 추출 과정의 디버그 정보를 체계적으로 로깅하는 클래스"""
    
    def __init__(self, base_dir: str = "tests/debug_outputs", enable_debug: bool = False):
        """
        Args:
            base_dir: 디버그 로그를 저장할 기본 디렉토리
            enable_debug: 디버그 모드 활성화 여부
        """
        self.enable_debug = enable_debug or os.getenv("ENABLE_KEYWORD_DEBUG", "false").lower() == "true"
        
        if self.enable_debug:
            self.base_dir = Path(base_dir)
            self.base_dir.mkdir(exist_ok=True, parents=True)
            self.session_id = str(uuid.uuid4())[:8]
            self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 세션별 디렉토리 생성
            self.session_dir = self.base_dir / f"{self.timestamp}_{self.session_id}"
            self.session_dir.mkdir(exist_ok=True, parents=True)
            
            self.debug_data = {
                "session_info": {
                    "session_id": self.session_id,
                    "timestamp": self.timestamp,
                    "start_time": datetime.now().isoformat()
                },
                "extraction_steps": []
            }
            
            print(f"🐛 디버그 모드 활성화 - 세션: {self.session_id}")
            print(f"📁 로그 저장 위치: {self.session_dir}")
    
    def start_extraction(self, extractor_name: str, file_info: Dict, text: str, config: Dict = None):
        """키워드 추출 시작 로깅"""
        if not self.enable_debug:
            return
            
        step_data = {
            "step": "start_extraction",
            "extractor": extractor_name,
            "timestamp": datetime.now().isoformat(),
            "file_info": {
                "filename": file_info.get("filename", "unknown"),
                "file_id": file_info.get("id"),
                "file_size": len(text) if text else 0,
                "text_preview": text[:200] + "..." if text and len(text) > 200 else text
            },
            "config": config or {},
            "text_stats": self._analyze_text(text) if text else {}
        }
        
        self.debug_data["extraction_steps"].append(step_data)
        self._save_text_file("input_text.txt", text or "")
        
        print(f"🐛 [{extractor_name}] 추출 시작 - 텍스트 길이: {len(text) if text else 0}자")
    
    def log_preprocessing(self, extractor_name: str, original_text: str, 
                         preprocessed_text: str, preprocessing_steps: List[str]):
        """전처리 단계 로깅"""
        if not self.enable_debug:
            return
            
        step_data = {
            "step": "preprocessing",
            "extractor": extractor_name,
            "timestamp": datetime.now().isoformat(),
            "original_stats": self._analyze_text(original_text),
            "preprocessed_stats": self._analyze_text(preprocessed_text),
            "preprocessing_steps": preprocessing_steps,
            "text_change_ratio": len(preprocessed_text) / len(original_text) if original_text else 0
        }
        
        self.debug_data["extraction_steps"].append(step_data)
        self._save_text_file(f"{extractor_name}_preprocessed.txt", preprocessed_text)
        
        print(f"🐛 [{extractor_name}] 전처리 완료 - {len(original_text)} → {len(preprocessed_text)}자")
    
    def log_candidate_generation(self, extractor_name: str, candidates: List[str], 
                               generation_method: str, params: Dict = None):
        """키워드 후보 생성 단계 로깅"""
        if not self.enable_debug:
            return
            
        step_data = {
            "step": "candidate_generation", 
            "extractor": extractor_name,
            "timestamp": datetime.now().isoformat(),
            "method": generation_method,
            "params": params or {},
            "candidate_count": len(candidates),
            "candidates": candidates[:50],  # 처음 50개만 저장
            "candidate_stats": self._analyze_candidates(candidates)
        }
        
        self.debug_data["extraction_steps"].append(step_data)
        self._save_json_file(f"{extractor_name}_candidates.json", {
            "method": generation_method,
            "count": len(candidates),
            "candidates": candidates
        })
        
        print(f"🐛 [{extractor_name}] 후보 생성 완료 - {generation_method}: {len(candidates)}개")
    
    def log_embeddings(self, extractor_name: str, model_name: str,
                      doc_embedding: Optional[np.ndarray] = None,
                      candidate_embeddings: Optional[np.ndarray] = None):
        """임베딩 계산 단계 로깅"""
        if not self.enable_debug:
            return
            
        step_data = {
            "step": "embeddings",
            "extractor": extractor_name, 
            "timestamp": datetime.now().isoformat(),
            "model_name": model_name,
            "doc_embedding_shape": doc_embedding.shape if doc_embedding is not None else None,
            "candidate_embeddings_shape": candidate_embeddings.shape if candidate_embeddings is not None else None,
            "embedding_stats": {}
        }
        
        if doc_embedding is not None:
            step_data["embedding_stats"]["doc_embedding"] = {
                "mean": float(np.mean(doc_embedding)),
                "std": float(np.std(doc_embedding)),
                "norm": float(np.linalg.norm(doc_embedding))
            }
        
        if candidate_embeddings is not None:
            step_data["embedding_stats"]["candidate_embeddings"] = {
                "mean": float(np.mean(candidate_embeddings)),
                "std": float(np.std(candidate_embeddings)),
                "min_norm": float(np.min(np.linalg.norm(candidate_embeddings, axis=1))),
                "max_norm": float(np.max(np.linalg.norm(candidate_embeddings, axis=1)))
            }
            
            # 임베딩 저장 (선택사항 - 용량 많이 차지함)
            if os.getenv("SAVE_EMBEDDINGS", "false").lower() == "true":
                np.save(self.session_dir / f"{extractor_name}_doc_embedding.npy", doc_embedding)
                np.save(self.session_dir / f"{extractor_name}_candidate_embeddings.npy", candidate_embeddings)
        
        self.debug_data["extraction_steps"].append(step_data)
        print(f"🐛 [{extractor_name}] 임베딩 완료 - 모델: {model_name}")
    
    def log_similarity_calculation(self, extractor_name: str, similarities: np.ndarray,
                                 candidates: List[str], method: str = "cosine"):
        """유사도 계산 단계 로깅"""
        if not self.enable_debug:
            return
            
        # 유사도-키워드 매핑
        similarity_results = [
            {"candidate": candidate, "similarity": float(sim)}
            for candidate, sim in zip(candidates, similarities)
        ]
        
        # 상위/하위 결과
        sorted_results = sorted(similarity_results, key=lambda x: x["similarity"], reverse=True)
        
        step_data = {
            "step": "similarity_calculation",
            "extractor": extractor_name,
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "similarity_stats": {
                "count": len(similarities),
                "mean": float(np.mean(similarities)),
                "std": float(np.std(similarities)),
                "min": float(np.min(similarities)),
                "max": float(np.max(similarities)),
                "median": float(np.median(similarities))
            },
            "top_10": sorted_results[:10],
            "bottom_5": sorted_results[-5:] if len(sorted_results) > 5 else []
        }
        
        self.debug_data["extraction_steps"].append(step_data)
        self._save_json_file(f"{extractor_name}_similarities.json", {
            "method": method,
            "results": similarity_results
        })
        
        print(f"🐛 [{extractor_name}] 유사도 계산 완료 - {method}, 범위: {np.min(similarities):.3f}~{np.max(similarities):.3f}")
    
    def log_algorithm_application(self, extractor_name: str, algorithm: str,
                                input_candidates: List[tuple], output_keywords: List[tuple],
                                algorithm_params: Dict = None):
        """알고리즘 적용 단계 로깅 (MMR, Max Sum 등)"""
        if not self.enable_debug:
            return
            
        step_data = {
            "step": "algorithm_application",
            "extractor": extractor_name,
            "timestamp": datetime.now().isoformat(),
            "algorithm": algorithm,
            "algorithm_params": algorithm_params or {},
            "input_count": len(input_candidates),
            "output_count": len(output_keywords),
            "input_candidates": input_candidates[:20],  # 처음 20개
            "output_keywords": output_keywords,
            "selection_ratio": len(output_keywords) / len(input_candidates) if input_candidates else 0
        }
        
        # 선택/제외된 키워드 분석
        selected_keywords = {kw[0] for kw in output_keywords}
        excluded_keywords = [(kw, score) for kw, score in input_candidates if kw not in selected_keywords]
        step_data["excluded_keywords"] = excluded_keywords[:10]
        
        self.debug_data["extraction_steps"].append(step_data)
        self._save_json_file(f"{extractor_name}_{algorithm}_results.json", {
            "algorithm": algorithm,
            "params": algorithm_params,
            "input": input_candidates,
            "output": output_keywords,
            "excluded": excluded_keywords
        })
        
        print(f"🐛 [{extractor_name}] {algorithm} 적용 완료 - {len(input_candidates)} → {len(output_keywords)}개")
    
    def log_position_analysis(self, extractor_name: str, keywords_with_positions: List[Dict],
                            text: str, analysis_method: str = "simple_search"):
        """키워드 위치 분석 단계 로깅"""
        if not self.enable_debug:
            return
            
        step_data = {
            "step": "position_analysis",
            "extractor": extractor_name,
            "timestamp": datetime.now().isoformat(),
            "analysis_method": analysis_method,
            "keywords_count": len(keywords_with_positions),
            "keywords_with_positions": keywords_with_positions[:10],  # 처음 10개만
            "position_stats": self._analyze_positions(keywords_with_positions, text)
        }
        
        self.debug_data["extraction_steps"].append(step_data)
        self._save_json_file(f"{extractor_name}_positions.json", {
            "method": analysis_method,
            "text_length": len(text),
            "keywords": keywords_with_positions
        })
        
        positioned_count = sum(1 for kw in keywords_with_positions if kw.get("positions"))
        print(f"🐛 [{extractor_name}] 위치 분석 완료 - {positioned_count}/{len(keywords_with_positions)}개 위치 확인")
    
    def log_final_results(self, extractor_name: str, final_keywords: List[Dict],
                         extraction_time: float, total_processing_time: float):
        """최종 결과 로깅"""
        if not self.enable_debug:
            return
            
        step_data = {
            "step": "final_results",
            "extractor": extractor_name,
            "timestamp": datetime.now().isoformat(),
            "final_keywords": final_keywords,
            "keyword_count": len(final_keywords),
            "extraction_time": extraction_time,
            "total_processing_time": total_processing_time,
            "performance_stats": {
                "keywords_per_second": len(final_keywords) / extraction_time if extraction_time > 0 else 0,
                "avg_score": np.mean([kw.get("score", 0) for kw in final_keywords]) if final_keywords else 0
            }
        }
        
        self.debug_data["extraction_steps"].append(step_data)
        self.debug_data["session_info"]["end_time"] = datetime.now().isoformat()
        self.debug_data["session_info"]["total_time"] = total_processing_time
        
        # 최종 요약 저장
        self._save_final_summary(extractor_name, final_keywords, extraction_time)
        
        print(f"🐛 [{extractor_name}] 추출 완료 - {len(final_keywords)}개 키워드, {extraction_time:.2f}초")
    
    def save_debug_session(self):
        """디버그 세션 전체 데이터를 저장"""
        if not self.enable_debug:
            return
            
        # 메인 디버그 데이터 저장
        debug_file = self.session_dir / "debug_session.json"
        with open(debug_file, 'w', encoding='utf-8') as f:
            json.dump(self.debug_data, f, ensure_ascii=False, indent=2, default=str)
        
        # 요약 리포트 생성
        self._generate_summary_report()
        
        print(f"🐛 디버그 세션 저장 완료: {debug_file}")
        print(f"📊 요약 리포트: {self.session_dir / 'summary_report.html'}")
    
    def _analyze_text(self, text: str) -> Dict:
        """텍스트 기본 통계 분석"""
        if not text:
            return {}
            
        words = text.split()
        sentences = text.split('.')
        
        return {
            "length": len(text),
            "word_count": len(words),
            "sentence_count": len([s for s in sentences if s.strip()]),
            "avg_word_length": np.mean([len(word) for word in words]) if words else 0,
            "unique_words": len(set(words)),
            "word_diversity": len(set(words)) / len(words) if words else 0
        }
    
    def _analyze_candidates(self, candidates: List[str]) -> Dict:
        """키워드 후보들 통계 분석"""
        if not candidates:
            return {}
            
        lengths = [len(candidate) for candidate in candidates]
        word_counts = [len(candidate.split()) for candidate in candidates]
        
        return {
            "total_count": len(candidates),
            "unique_count": len(set(candidates)),
            "avg_length": np.mean(lengths),
            "avg_word_count": np.mean(word_counts),
            "single_word_ratio": sum(1 for wc in word_counts if wc == 1) / len(word_counts),
            "multi_word_ratio": sum(1 for wc in word_counts if wc > 1) / len(word_counts)
        }
    
    def _analyze_positions(self, keywords_with_positions: List[Dict], text: str) -> Dict:
        """키워드 위치 정보 통계 분석"""
        if not keywords_with_positions:
            return {}
            
        positioned_keywords = [kw for kw in keywords_with_positions if kw.get("positions")]
        all_positions = []
        
        for kw in positioned_keywords:
            positions = kw.get("positions", [])
            all_positions.extend([pos.get("start", 0) for pos in positions])
        
        return {
            "positioned_count": len(positioned_keywords),
            "total_positions": len(all_positions),
            "coverage_ratio": len(positioned_keywords) / len(keywords_with_positions) if keywords_with_positions else 0,
            "avg_positions_per_keyword": len(all_positions) / len(positioned_keywords) if positioned_keywords else 0,
            "text_coverage": {
                "start": min(all_positions) if all_positions else 0,
                "end": max(all_positions) if all_positions else 0,
                "span": max(all_positions) - min(all_positions) if all_positions else 0
            }
        }
    
    def _save_text_file(self, filename: str, content: str):
        """텍스트 파일 저장"""
        if not self.enable_debug:
            return
            
        file_path = self.session_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _save_json_file(self, filename: str, data: Any):
        """JSON 파일 저장"""
        if not self.enable_debug:
            return
            
        file_path = self.session_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    
    def _save_final_summary(self, extractor_name: str, final_keywords: List[Dict], extraction_time: float):
        """최종 요약 정보 저장"""
        summary = {
            "extractor": extractor_name,
            "session_id": self.session_id,
            "extraction_time": extraction_time,
            "keyword_count": len(final_keywords),
            "keywords": final_keywords,
            "top_keywords": sorted(final_keywords, key=lambda x: x.get("score", 0), reverse=True)[:5]
        }
        
        self._save_json_file(f"{extractor_name}_summary.json", summary)
    
    def _generate_summary_report(self):
        """HTML 형식의 요약 리포트 생성"""
        if not self.enable_debug:
            return
            
        html_content = self._build_html_report()
        report_file = self.session_dir / "summary_report.html"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _build_html_report(self) -> str:
        """HTML 리포트 빌드"""
        extractors = list(set([step.get("extractor") for step in self.debug_data["extraction_steps"] if step.get("extractor")]))
        
        html = f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>키워드 추출 디버그 리포트</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 40px; }}
                .header {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                .extractor {{ margin-bottom: 30px; padding: 20px; border: 1px solid #dee2e6; border-radius: 8px; }}
                .step {{ margin: 10px 0; padding: 15px; background: #f1f3f4; border-radius: 4px; }}
                .keyword {{ display: inline-block; padding: 4px 8px; margin: 2px; background: #e3f2fd; border-radius: 4px; }}
                .score {{ color: #1976d2; font-weight: bold; }}
                table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 15px 0; }}
                .stat-card {{ padding: 15px; background: white; border: 1px solid #e0e0e0; border-radius: 6px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🐛 키워드 추출 디버그 리포트</h1>
                <p><strong>세션 ID:</strong> {self.session_id}</p>
                <p><strong>생성 시간:</strong> {self.timestamp}</p>
                <p><strong>추출기:</strong> {', '.join(extractors)}</p>
            </div>
        """
        
        for extractor in extractors:
            extractor_steps = [step for step in self.debug_data["extraction_steps"] if step.get("extractor") == extractor]
            html += f"<div class='extractor'><h2>📊 {extractor} 추출기</h2>"
            
            for step in extractor_steps:
                step_name = step.get("step", "unknown")
                html += f"<div class='step'><h3>{step_name}</h3>"
                
                if step_name == "final_results":
                    keywords = step.get("final_keywords", [])
                    html += f"<p><strong>최종 키워드 {len(keywords)}개:</strong></p><div>"
                    for kw in keywords[:10]:  # 상위 10개만
                        score = kw.get("score", 0)
                        html += f"<span class='keyword'>{kw.get('keyword', 'N/A')} <span class='score'>({score:.3f})</span></span>"
                    html += "</div>"
                
                html += "</div>"
            
            html += "</div>"
        
        html += """
            <div style="margin-top: 40px; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                <h3>📁 생성된 파일들</h3>
                <ul>
                    <li><code>debug_session.json</code> - 전체 세션 데이터</li>
                    <li><code>*_candidates.json</code> - 키워드 후보들</li>
                    <li><code>*_similarities.json</code> - 유사도 계산 결과</li>
                    <li><code>*_positions.json</code> - 키워드 위치 정보</li>
                    <li><code>*_summary.json</code> - 최종 요약</li>
                </ul>
            </div>
        </body>
        </html>
        """
        
        return html


# 전역 디버그 로거 인스턴스
debug_logger: Optional[DebugLogger] = None

def get_debug_logger() -> DebugLogger:
    """전역 디버그 로거 인스턴스 반환"""
    global debug_logger
    if debug_logger is None:
        debug_logger = DebugLogger()
    return debug_logger

def init_debug_logger(enable_debug: bool = None) -> DebugLogger:
    """디버그 로거 초기화"""
    global debug_logger
    if enable_debug is None:
        enable_debug = os.getenv("ENABLE_KEYWORD_DEBUG", "false").lower() == "true"
    
    debug_logger = DebugLogger(enable_debug=enable_debug)
    return debug_logger