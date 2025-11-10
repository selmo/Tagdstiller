"""
구조 기반 문서 청킹 시스템

이 모듈은 문서의 논리적 구조(Chapter, Section, Subsection)를 분석하여
지능적으로 청크를 생성하는 시스템입니다.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


@dataclass
class DocumentNode:
    """문서 구조 노드"""
    node_id: str
    node_type: str  # "document", "chapter", "section", "subsection"
    level: int      # 0=document, 1=chapter, 2=section, 3=subsection
    number: str     # "1", "1.1", "1.1.1"
    title: str
    content: str
    start_pos: int  # 문서 내 시작 위치
    end_pos: int    # 문서 내 끝 위치
    children: List['DocumentNode'] = field(default_factory=list)
    parent: Optional['DocumentNode'] = None

    def get_full_path(self) -> str:
        """전체 경로 반환"""
        return self.number

    def get_root_chapter_number(self) -> str:
        """최상위 Chapter 번호 반환"""
        return self.number.split('.')[0]

    def get_total_content(self) -> str:
        """자신과 모든 하위 노드의 내용을 합친 텍스트 반환 (제목 포함)"""
        content_parts = []

        # 제목이 있고 루트가 아니면 제목을 먼저 추가
        if self.title and self.node_type != "document":
            # 마크다운 형식으로 제목 추가 (레벨 구분)
            if self.node_type == "chapter":
                content_parts.append(f"# {self.title}")      # H1: Chapter
            elif self.node_type == "section":
                content_parts.append(f"## {self.title}")     # H2: Section
            elif self.node_type == "subsection":
                content_parts.append(f"### {self.title}")    # H3: Subsection

        # 본문 내용 추가
        if self.content.strip():
            content_parts.append(self.content)

        # 자식 노드 내용 추가
        for child in self.children:
            child_content = child.get_total_content()
            if child_content.strip():
                content_parts.append(child_content)

        return "\n\n".join(content_parts)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (JSON 직렬화용)"""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "level": self.level,
            "number": self.number,
            "title": self.title,
            "content_preview": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "content_length": len(self.content),
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "children": [child.to_dict() for child in self.children]
        }


@dataclass
class ChunkGroup:
    """청킹 그룹"""
    chunk_id: str
    level: str          # "document", "chapter", "section", "subsection"
    nodes: List[DocumentNode]
    parent_context: Optional[str] = None
    boundary_rule: str = "auto"

    def get_total_content(self) -> str:
        """그룹 내 모든 노드의 내용을 합친 텍스트"""
        content_parts = []
        for node in self.nodes:
            node_content = node.get_total_content()
            if node_content.strip():
                content_parts.append(node_content)
        return "\n\n".join(content_parts)

    def get_content_length(self) -> int:
        """총 내용 길이"""
        return len(self.get_total_content())

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "chunk_id": self.chunk_id,
            "level": self.level,
            "content_length": self.get_content_length(),
            "parent_context": self.parent_context,
            "boundary_rule": self.boundary_rule,
            "nodes": [node.to_dict() for node in self.nodes],
            "content_preview": self.get_total_content()[:300] + "..." if self.get_content_length() > 300 else self.get_total_content()
        }


class DocumentStructureAnalyzer:
    """문서 구조 분석기"""

    # 구조 인식 패턴
    STRUCTURE_PATTERNS = {
        "chapter": [
            r"^(\d+)\.\s+(.+?)(?:\n|$)",           # "1. 제목"
            r"^제\s*(\d+)\s*장\s*[:\.\s]*(.+?)(?:\n|$)",  # "제 1 장: 제목"
            r"^Chapter\s+(\d+)[\.\:\s]*(.+?)(?:\n|$)",     # "Chapter 1: 제목"
            r"^CHAPTER\s+([IVX]+)[\.\:\s]*(.+?)(?:\n|$)",  # "CHAPTER I: 제목"
            r"^#\s+(\d+)\s+(.+?)(?:\n|$)",         # "# 1 제목" (마크다운)
            r"^#\s+(\d{2})\s+(.+?)(?:\n|$)",       # "# 01 제목" (마크다운)
            r"^(\d{2})$",                          # "01" (단독 숫자 라인)
        ],

        "section": [
            r"^(\d+)\.(\d+)\s+(.+?)(?:\n|$)",      # "1.1 제목"
            r"^(\d+)-(\d+)[\.\s]+(.+?)(?:\n|$)",   # "1-1. 제목"
            r"^제\s*(\d+)\s*절\s*[:\.\s]*(.+?)(?:\n|$)",  # "제 1 절: 제목"
            r"^##\s+(\d+)\.(\d+)\s+(.+?)(?:\n|$)", # "## 1.1 제목" (마크다운)
            r"^##\s+(\d{2})\s+(.+?)(?:\n|$)",      # "## 01 제목" (마크다운)
            r"^##\s+(.+?)(?:\n|$)",                # "## 제목" (마크다운 일반)
        ],

        "subsection": [
            r"^(\d+)\.(\d+)\.(\d+)\s+(.+?)(?:\n|$)",  # "1.1.1 제목"
            r"^(\d+)-(\d+)-(\d+)[\.\s]+(.+?)(?:\n|$)", # "1-1-1. 제목"
            r"^\((\d+)\)\s+(.+?)(?:\n|$)",             # "(1) 제목"
            r"^([가-힣])\.\s+(.+?)(?:\n|$)",           # "가. 제목"
            r"^###\s+(.+?)(?:\n|$)",               # "### 제목" (마크다운)
        ]
    }

    def analyze_structure(self, text: str) -> DocumentNode:
        """문서 구조 분석"""
        import time
        structure_start = time.time()
        logger.info(f"📊 문서 구조 분석 시작 - 텍스트 길이: {len(text)} 문자")

        # 루트 문서 노드 생성
        root = DocumentNode(
            node_id="document_root",
            node_type="document",
            level=0,
            number="0",
            title="Document Root",
            content="",
            start_pos=0,
            end_pos=len(text)
        )

        # 텍스트를 라인별로 분석
        lines = text.split('\n')
        current_pos = 0

        current_chapter = None
        current_section = None

        # 자동 번호 카운터
        auto_chapter_counter = 1
        auto_section_counter = 1
        auto_subsection_counter = 1

        content_buffer = []

        for i, line in enumerate(lines):
            line_start_pos = current_pos
            line_end_pos = current_pos + len(line) + 1  # +1 for \n
            current_pos = line_end_pos

            # 각 구조 레벨 확인
            structure_match = self._match_structure_pattern(line)

            if structure_match:
                # 이전 content_buffer를 현재 노드에 저장
                if content_buffer:
                    content_text = '\n'.join(content_buffer)
                    if current_section:
                        current_section.content += content_text + '\n'
                    elif current_chapter:
                        current_chapter.content += content_text + '\n'
                    else:
                        root.content += content_text + '\n'
                    content_buffer = []

                level, number, title = structure_match

                # 자동 번호 처리
                if number == "auto":
                    if level == "chapter":
                        number = str(auto_chapter_counter)
                        auto_chapter_counter += 1
                        auto_section_counter = 1  # 새 챕터 시작시 섹션 카운터 리셋
                    elif level == "section":
                        number = str(auto_section_counter)
                        auto_section_counter += 1
                        auto_subsection_counter = 1  # 새 섹션 시작시 서브섹션 카운터 리셋
                    elif level == "subsection":
                        number = str(auto_subsection_counter)
                        auto_subsection_counter += 1

                if level == "chapter":
                    current_chapter = DocumentNode(
                        node_id=f"chapter_{number}",
                        node_type="chapter",
                        level=1,
                        number=number,
                        title=title,
                        content="",
                        start_pos=line_start_pos,
                        end_pos=line_end_pos,
                        parent=root
                    )
                    root.children.append(current_chapter)
                    current_section = None
                    logger.debug(f"📖 Chapter 발견: {number} - {title}")

                elif level == "section":
                    # Section은 Chapter가 없어도 생성 (마크다운 문서의 경우)
                    if not current_chapter:
                        # 암시적 Chapter 생성
                        current_chapter = DocumentNode(
                            node_id=f"chapter_auto",
                            node_type="chapter",
                            level=1,
                            number="1",
                            title="Document Sections",
                            content="",
                            start_pos=line_start_pos,
                            end_pos=line_start_pos,
                            parent=root
                        )
                        root.children.append(current_chapter)
                        logger.debug(f"📖 암시적 Chapter 생성: Document Sections")

                    current_section = DocumentNode(
                        node_id=f"section_{number}",
                        node_type="section",
                        level=2,
                        number=number,
                        title=title,
                        content="",
                        start_pos=line_start_pos,
                        end_pos=line_end_pos,
                        parent=current_chapter
                    )
                    current_chapter.children.append(current_section)
                    logger.debug(f"📝 Section 발견: {number} - {title}")

                elif level == "subsection":
                    if current_section:
                        subsection = DocumentNode(
                            node_id=f"subsection_{number}",
                            node_type="subsection",
                            level=3,
                            number=number,
                            title=title,
                            content="",
                            start_pos=line_start_pos,
                            end_pos=line_end_pos,
                            parent=current_section
                        )
                        current_section.children.append(subsection)
                        logger.debug(f"📄 Subsection 발견: {number} - {title}")
            else:
                # 일반 내용 라인
                content_buffer.append(line)

        # 마지막 content_buffer 처리
        if content_buffer:
            content_text = '\n'.join(content_buffer)
            if current_section:
                current_section.content += content_text
            elif current_chapter:
                current_chapter.content += content_text
            else:
                root.content += content_text

        # 구조 분석 결과 로그
        structure_duration = time.time() - structure_start
        self._log_structure_summary(root)
        logger.info(f"⏱️ 구조 분석 소요시간: {structure_duration:.2f}초")

        return root

    def _match_structure_pattern(self, line: str) -> Optional[Tuple[str, str, str]]:
        """라인이 구조 패턴에 매치되는지 확인"""
        line = line.strip()
        if not line:
            return None

        # Chapter 패턴 확인
        for i, pattern in enumerate(self.STRUCTURE_PATTERNS["chapter"]):
            match = re.match(pattern, line)
            if match:
                groups = match.groups()

                # "01" 같은 단독 숫자 패턴
                if i == 6 and len(groups) == 1:  # "(\d{2})$" 패턴
                    number = groups[0]
                    return ("chapter", number, f"Chapter {number}")

                # 일반 패턴 (번호, 제목)
                elif len(groups) == 2:
                    number, title = groups
                    return ("chapter", number, title.strip())

        # Section 패턴 확인
        for i, pattern in enumerate(self.STRUCTURE_PATTERNS["section"]):
            match = re.match(pattern, line)
            if match:
                groups = match.groups()

                # "## 제목" 일반 마크다운 패턴
                if i == 5 and len(groups) == 1:  # "^##\s+(.+?)(?:\n|$)" 패턴
                    title = groups[0].strip()
                    # 자동으로 section 번호 생성 (임시)
                    return ("section", "auto", title)

                # "## 01 제목" 패턴
                elif i == 4 and len(groups) == 2:  # "^##\s+(\d{2})\s+(.+?)(?:\n|$)" 패턴
                    number, title = groups
                    return ("section", number, title.strip())

                # "1.1 제목" 패턴
                elif len(groups) == 3:
                    number = f"{groups[0]}.{groups[1]}"
                    title = groups[2].strip()
                    return ("section", number, title)

                # 기타 패턴
                elif len(groups) == 2:
                    number, title = groups
                    return ("section", number, title.strip())

        # Subsection 패턴 확인
        for i, pattern in enumerate(self.STRUCTURE_PATTERNS["subsection"]):
            match = re.match(pattern, line)
            if match:
                groups = match.groups()

                # "### 제목" 마크다운 패턴
                if i == 4 and len(groups) == 1:  # "^###\s+(.+?)(?:\n|$)" 패턴
                    title = groups[0].strip()
                    return ("subsection", "auto", title)

                # 복합 번호 패턴
                elif len(groups) == 4:
                    number = f"{groups[0]}.{groups[1]}.{groups[2]}"
                    title = groups[3].strip()
                    return ("subsection", number, title)

                # 간단한 패턴
                elif len(groups) == 2:
                    number, title = groups
                    return ("subsection", number, title.strip())

        return None

    def _log_structure_summary(self, root: DocumentNode):
        """구조 분석 결과 요약 로그"""
        chapter_count = len(root.children)
        section_count = sum(len(chapter.children) for chapter in root.children)
        subsection_count = sum(
            len(section.children)
            for chapter in root.children
            for section in chapter.children
        )

        logger.info(f"📊 구조 분석 완료:")
        logger.info(f"  📖 Chapter: {chapter_count}개")
        logger.info(f"  📝 Section: {section_count}개")
        logger.info(f"  📄 Subsection: {subsection_count}개")

        for chapter in root.children:
            logger.debug(f"  📖 {chapter.number}: {chapter.title} ({len(chapter.children)}개 section)")


class StructuralChunker:
    """구조 기반 청킹 시스템"""

    def __init__(self):
        self.analyzer = DocumentStructureAnalyzer()

    def determine_chunking_level(self, doc_size: int, structure: DocumentNode) -> str:
        """문서 크기와 구조를 기반으로 청킹 단위 결정"""
        chapter_count = len(structure.children)
        section_count = sum(len(chapter.children) for chapter in structure.children)

        logger.info(f"📏 청킹 레벨 결정 - 문서크기: {doc_size}, Chapter: {chapter_count}, Section: {section_count}")

        # LLM 처리를 위해 청크 크기를 더 작게 조정 (10K 이하 권장)
        if doc_size < 8000:     # 8K 이하: 전체 문서
            level = "document"
        elif doc_size < 50000:  # 50K 이하: 구조 기반 분할
            if chapter_count >= 3:
                level = "chapter"
            elif section_count >= 3:  # 5 → 3으로 낮춤
                level = "section"
            elif chapter_count >= 2:  # Chapter가 2개 이상이면 분할
                level = "chapter"
            else:
                level = "document"
        else:                   # 50K 이상: 적극적 분할
            avg_chapter_size = doc_size / max(chapter_count, 1)
            if avg_chapter_size > 15000:  # 30K → 15K로 낮춤
                level = "section" if section_count >= chapter_count * 2 else "chapter"
            else:
                level = "chapter"

        logger.info(f"🎯 선택된 청킹 레벨: {level} (LLM 최적화: 8K 이하 선호)")
        return level

    def create_chunks(
        self,
        structure: DocumentNode,
        chunk_level: str,
        max_chunk_tokens: int = 16000  # 기본값 증가: 청크 수 감소
    ) -> List[ChunkGroup]:
        """구조 기반 청크 그룹 생성

        Args:
            structure: 문서 구조 트리
            chunk_level: 청킹 레벨 ("document", "chapter", "section")
            max_chunk_tokens: 청크당 최대 토큰 수 (기본값: 16000)
        """
        import time
        chunking_start = time.time()
        logger.info(f"✂️ 청크 생성 시작 - 레벨: {chunk_level}, 최대 토큰: {max_chunk_tokens}")

        chunks = []

        if chunk_level == "document":
            # 전체 문서를 하나의 청크로
            chunk = ChunkGroup(
                chunk_id="document_full",
                level="document",
                nodes=[structure],
                boundary_rule="document_boundary"
            )
            chunks.append(chunk)

        elif chunk_level == "chapter":
            # Chapter 단위로 그룹핑
            for i, chapter in enumerate(structure.children):
                chunk = ChunkGroup(
                    chunk_id=f"chapter_{chapter.number}",
                    level="chapter",
                    nodes=[chapter],
                    parent_context=f"Document: {structure.title}",
                    boundary_rule="chapter_boundary"
                )
                chunks.append(chunk)

        elif chunk_level == "section":
            # Section 단위로 그룹핑하되, 토큰 크기 기반으로 병합
            for chapter in structure.children:
                if chapter.children:  # Section이 있는 경우
                    # 토큰 크기 기반으로 섹션들을 병합
                    merged_chunks = self._merge_sections_by_token_size(
                        chapter.children,
                        max_tokens=max_chunk_tokens,  # 파라미터로 전달받은 값 사용
                        parent_context=f"Chapter {chapter.number}: {chapter.title}"
                    )
                    chunks.extend(merged_chunks)
                else:  # Section이 없으면 Chapter 전체
                    chunk = ChunkGroup(
                        chunk_id=f"chapter_{chapter.number}",
                        level="chapter",
                        nodes=[chapter],
                        parent_context=f"Document: {structure.title}",
                        boundary_rule="chapter_boundary"
                    )
                    chunks.append(chunk)

        # 청크 경계 검증
        chunks = self._validate_chunk_boundaries(chunks)

        chunking_duration = time.time() - chunking_start
        logger.info(f"✅ 청크 생성 완료 - 총 {len(chunks)}개 청크 (소요시간: {chunking_duration:.2f}초)")
        for chunk in chunks:
            logger.debug(f"  🧩 {chunk.chunk_id}: {chunk.get_content_length()} 문자")

        return chunks

    def _merge_sections_by_token_size(
        self,
        sections: List[DocumentNode],
        max_tokens: int = 8000,
        parent_context: str = ""
    ) -> List[ChunkGroup]:
        """토큰 크기 기반으로 섹션들을 병합하여 청크 생성

        Args:
            sections: 병합할 섹션 노드 리스트
            max_tokens: 청크당 최대 토큰 수
            parent_context: 부모 컨텍스트 (Chapter 정보 등)

        Returns:
            병합된 청크 그룹 리스트
        """
        chunks = []
        current_nodes = []
        current_tokens = 0

        for section in sections:
            # 섹션의 토큰 수 추정 (문자 수 / 4)
            section_content = section.get_total_content()
            section_tokens = len(section_content) // 4

            # 현재 청크에 추가했을 때 max_tokens를 초과하는지 확인
            if current_nodes and (current_tokens + section_tokens > max_tokens):
                # 현재 청크 저장
                chunk_id = f"merged_{sections[0].number}_to_{current_nodes[-1].number}"
                chunk = ChunkGroup(
                    chunk_id=chunk_id,
                    level="section",
                    nodes=current_nodes.copy(),
                    parent_context=parent_context,
                    boundary_rule="token_based_merge"
                )
                chunks.append(chunk)
                logger.debug(f"  📦 병합 청크 생성: {len(current_nodes)}개 섹션, ~{current_tokens} 토큰")

                # 새 청크 시작
                current_nodes = [section]
                current_tokens = section_tokens
            else:
                # 현재 청크에 추가
                current_nodes.append(section)
                current_tokens += section_tokens

        # 마지막 청크 추가
        if current_nodes:
            chunk_id = f"merged_{current_nodes[0].number}_to_{current_nodes[-1].number}"
            chunk = ChunkGroup(
                chunk_id=chunk_id,
                level="section",
                nodes=current_nodes,
                parent_context=parent_context,
                boundary_rule="token_based_merge"
            )
            chunks.append(chunk)
            logger.debug(f"  📦 병합 청크 생성: {len(current_nodes)}개 섹션, ~{current_tokens} 토큰")

        logger.info(f"✅ 섹션 병합 완료: {len(sections)}개 섹션 → {len(chunks)}개 청크")
        return chunks

    def _validate_chunk_boundaries(self, chunks: List[ChunkGroup]) -> List[ChunkGroup]:
        """청크 경계 검증 및 수정"""
        validated_chunks = []

        for chunk in chunks:
            # 토큰 기반 병합된 청크는 검증 건너뛰기
            if chunk.boundary_rule == "token_based_merge":
                validated_chunks.append(chunk)
                continue

            # 규칙: 서로 다른 Chapter의 내용이 같은 청크에 있으면 안됨
            chapter_numbers = set()
            for node in chunk.nodes:
                if node.node_type == "chapter":
                    chapter_numbers.add(node.number)
                else:
                    chapter_numbers.add(node.get_root_chapter_number())

            if len(chapter_numbers) > 1:
                logger.warning(f"⚠️ 잘못된 청크 경계 발견: {chunk.chunk_id}")
                # 잘못된 경계 -> Chapter별로 분할
                split_chunks = self._split_by_chapter(chunk)
                validated_chunks.extend(split_chunks)
            else:
                validated_chunks.append(chunk)

        return validated_chunks

    def _split_by_chapter(self, chunk: ChunkGroup) -> List[ChunkGroup]:
        """Chapter별로 청크 분할"""
        chapter_groups = defaultdict(list)

        for node in chunk.nodes:
            if node.node_type == "chapter":
                chapter_num = node.number
            else:
                chapter_num = node.get_root_chapter_number()
            chapter_groups[chapter_num].append(node)

        split_chunks = []
        for chapter_num, nodes in chapter_groups.items():
            split_chunk = ChunkGroup(
                chunk_id=f"chapter_{chapter_num}_split",
                level="chapter",
                nodes=nodes,
                boundary_rule="chapter_boundary_corrected"
            )
            split_chunks.append(split_chunk)

        return split_chunks

    def analyze_and_chunk(self, text: str) -> Tuple[DocumentNode, List[ChunkGroup]]:
        """문서 분석 및 청킹 통합 프로세스"""
        logger.info(f"🚀 문서 분석 및 청킹 시작")

        # 1. 구조 분석
        structure = self.analyzer.analyze_structure(text)

        # 2. 청킹 레벨 결정
        chunk_level = self.determine_chunking_level(len(text), structure)

        # 3. 청크 생성
        chunks = self.create_chunks(structure, chunk_level)

        logger.info(f"🎉 분석 및 청킹 완료")
        return structure, chunks


def export_analysis_results(structure: DocumentNode, chunks: List[ChunkGroup],
                          output_path: Path) -> Dict[str, str]:
    """분석 결과를 파일로 내보내기"""
    output_path.mkdir(exist_ok=True)
    exported_files = {}

    # 1. 구조 분석 결과 JSON
    structure_file = output_path / "document_structure.json"
    with open(structure_file, 'w', encoding='utf-8') as f:
        json.dump(structure.to_dict(), f, ensure_ascii=False, indent=2)
    exported_files["structure"] = str(structure_file)

    # 2. 청크 정보 JSON
    chunks_file = output_path / "chunks_info.json"
    chunks_data = {
        "total_chunks": len(chunks),
        "chunks": [chunk.to_dict() for chunk in chunks]
    }
    with open(chunks_file, 'w', encoding='utf-8') as f:
        json.dump(chunks_data, f, ensure_ascii=False, indent=2)
    exported_files["chunks"] = str(chunks_file)

    # 3. 각 청크별 텍스트 파일
    chunks_dir = output_path / "chunks_text"
    chunks_dir.mkdir(exist_ok=True)

    for chunk in chunks:
        chunk_file = chunks_dir / f"{chunk.chunk_id}.txt"
        with open(chunk_file, 'w', encoding='utf-8') as f:
            f.write(f"# {chunk.chunk_id}\n")
            f.write(f"Level: {chunk.level}\n")
            f.write(f"Content Length: {chunk.get_content_length()}\n")
            if chunk.parent_context:
                f.write(f"Parent Context: {chunk.parent_context}\n")
            f.write(f"Boundary Rule: {chunk.boundary_rule}\n")
            f.write("=" * 50 + "\n\n")
            f.write(chunk.get_total_content())
        exported_files[chunk.chunk_id] = str(chunk_file)

    logger.info(f"📁 분석 결과 내보내기 완료: {output_path}")
    return exported_files


@dataclass
class ChunkInfo:
    """청킹 정보를 담는 데이터 클래스"""
    total_chunks: int
    chunks: List[Dict[str, Any]]
    original_structure: Dict[str, Any]
    chunking_metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentChunker:
    """문서 청킹을 위한 메인 클래스"""

    def __init__(self):
        self.chunker = StructuralChunker()
        self.logger = logging.getLogger(__name__)

    def chunk_document(
        self,
        file_path: str,
        max_chunk_size: int = 50000,
        output_directory: str = None
    ) -> ChunkInfo:
        """
        문서를 청킹합니다.

        Args:
            file_path: 분석할 파일 경로
            max_chunk_size: 최대 청크 크기
            output_directory: 결과 저장 디렉토리

        Returns:
            ChunkInfo: 청킹 정보
        """
        self.logger.info(f"📄 문서 청킹 시작: {file_path}")

        # 파일 읽기
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            raise ValueError(f"파일 읽기 실패: {str(e)}")

        # 구조 분석 및 청킹
        structure, chunk_groups = self.chunker.analyze_and_chunk(text)

        # ChunkInfo 형식으로 변환
        chunks_data = []
        for chunk_group in chunk_groups:
            chunk_dict = chunk_group.to_dict()
            chunks_data.append(chunk_dict)

        # 결과 저장 (선택적)
        if output_directory:
            output_path = Path(output_directory)
            export_analysis_results(structure, chunk_groups, output_path)

        chunk_info = ChunkInfo(
            total_chunks=len(chunks_data),
            chunks=chunks_data,
            original_structure=structure.to_dict(),
            chunking_metadata={
                'file_path': file_path,
                'original_size': len(text),
                'max_chunk_size': max_chunk_size,
                'chunking_level': chunk_groups[0].level if chunk_groups else 'unknown'
            }
        )

        self.logger.info(f"✅ 문서 청킹 완료: {len(chunks_data)}개 청크 생성")
        return chunk_info