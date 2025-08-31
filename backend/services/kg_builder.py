from __future__ import annotations

"""
Knowledge Graph builder for parsed document metadata.

Reads saved parser outputs (JSON) and produces a graph representation and
Memgraph/OpenCypher statements to load nodes and relationships.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from .kg_schema_manager import KGSchemaManager, DocumentDomain
from .memgraph_service import MemgraphService


def _hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()[:16]


@dataclass
class GraphData:
    documents: List[Dict[str, Any]]
    topics: List[Dict[str, Any]]
    keywords: List[Dict[str, Any]]
    orgs: List[Dict[str, Any]]
    urls: List[Dict[str, Any]]
    sections: List[Dict[str, Any]]
    # relationships (edges) represented as simple tuples/dicts
    doc_topics: List[Dict[str, str]]  # {doc_id, name}
    doc_keywords: List[Dict[str, str]]  # {doc_id, text}
    doc_orgs: List[Dict[str, str]]  # {doc_id, name}
    doc_urls: List[Dict[str, str]]  # {doc_id, url}
    doc_sections: List[Dict[str, Any]]  # {doc_id, section_id}
    section_hierarchy: List[Dict[str, Any]]  # {parent_id, child_id}


class KGBuilder:
    """Builds a KG from saved metadata JSON with domain-specific schema support."""
    
    def __init__(self, memgraph_config: Dict[str, Any] = None, auto_save_to_memgraph: bool = True):
        self.schema_manager = KGSchemaManager()
        self.auto_save_to_memgraph = auto_save_to_memgraph
        
        # Memgraph 서비스 초기화 (선택적)
        self.memgraph_service = None
        if auto_save_to_memgraph:
            try:
                self.memgraph_service = MemgraphService(
                    uri=memgraph_config.get("uri", "bolt://localhost:7687") if memgraph_config else "bolt://localhost:7687",
                    username=memgraph_config.get("username", "") if memgraph_config else "",
                    password=memgraph_config.get("password", "") if memgraph_config else ""
                )
                
                import logging
                logger = logging.getLogger(__name__)
                if self.memgraph_service.is_connected():
                    logger.info("✅ KG Builder: Memgraph 자동 저장 활성화")
                else:
                    logger.warning("⚠️ KG Builder: Memgraph 연결 실패, 로컬 저장만 수행")
                    self.memgraph_service = None
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"⚠️ KG Builder: Memgraph 초기화 실패 ({e}), 로컬 저장만 수행")
                self.memgraph_service = None
    
    def build_knowledge_graph(self, file_path: str, document_text: str, keywords: Dict[str, Any], metadata: Dict[str, Any], structure_analysis: Dict[str, Any] = None, parsing_results: Dict[str, Any] = None, force_rebuild: bool = False) -> Dict[str, Any]:
        """
        Build a knowledge graph from document analysis results with domain-specific enhancements.
        
        Args:
            file_path: Path to the document file
            document_text: Extracted text content  
            keywords: Keyword extraction results
            metadata: File metadata
            structure_analysis: Document structure analysis results
            parsing_results: Full parsing results
            force_rebuild: Whether to force rebuild (currently ignored)
            
        Returns:
            Dictionary containing entities and relationships with domain-specific types
        """
        # Detect document domain
        domain, domain_confidence = self.schema_manager.detect_document_domain(
            document_text, metadata
        )
        
        result = {
            "entities": [],
            "relationships": [],
            "metadata": {
                "created_at": self._get_timestamp(),
                "file_path": file_path,
                "structure_based": True,
                "extractors_used": list(keywords.keys()) if keywords else [],
                "detected_domain": domain.value,
                "domain_confidence": domain_confidence
            }
        }
        
        # 1. Create document entity
        doc_id = _hash(str(file_path))
        doc_entity = {
            "id": doc_id,
            "type": "Document",
            "properties": {
                "title": metadata.get("name", Path(file_path).name),
                "path": file_path,
                "size": metadata.get("size"),
                "extension": metadata.get("extension"),
                "parser_count": len(parsing_results.get("parsing_results", {})) if parsing_results else 0,
                "best_parser": parsing_results.get("summary", {}).get("best_parser") if parsing_results else None
            }
        }
        result["entities"].append(doc_entity)
        
        # 2. Extract structure-based entities if structure analysis exists
        if structure_analysis and structure_analysis.get("structure_elements"):
            sections_created = self._create_structure_entities(
                doc_id, structure_analysis, result, parsing_results
            )
            
            # 3. Extract keyword entities with domain-specific enhancements
            self._create_domain_enhanced_keyword_entities(
                doc_id, keywords, result, sections_created, domain, document_text
            )
        else:
            # Fallback: create domain-enhanced keyword entities without structure
            self._create_domain_enhanced_keyword_entities(
                doc_id, keywords, result, {}, domain, document_text
            )
        
        # 4. Memgraph에 자동 저장 (선택적)
        if self.memgraph_service and self.auto_save_to_memgraph:
            try:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"💾 Memgraph에 KG 데이터 저장 중: {file_path}")
                
                success = self.memgraph_service.insert_kg_data(result, clear_existing=True)
                if success:
                    result["metadata"]["memgraph_saved"] = True
                    result["metadata"]["memgraph_saved_at"] = self._get_timestamp()
                    logger.info(f"✅ Memgraph 저장 완료: {file_path}")
                else:
                    result["metadata"]["memgraph_saved"] = False
                    result["metadata"]["memgraph_error"] = "저장 실패"
                    logger.warning(f"⚠️ Memgraph 저장 실패: {file_path}")
                    
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"❌ Memgraph 저장 중 오류: {file_path}, 오류: {e}")
                result["metadata"]["memgraph_saved"] = False
                result["metadata"]["memgraph_error"] = str(e)
        
        return result
        
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.now().isoformat()
        
    def _create_structure_entities(self, doc_id: str, structure_analysis: Dict[str, Any], result: Dict[str, Any], parsing_results: Dict[str, Any]) -> Dict[str, str]:
        """Create structure-based entities (sections, paragraphs, etc.)."""
        sections_created = {}
        
        # Get best parser structure information
        best_parser = structure_analysis.get("summary", {}).get("best_parser")
        if not best_parser or best_parser not in structure_analysis.get("structure_elements", {}):
            return sections_created
            
        parser_structure = structure_analysis["structure_elements"][best_parser]
        
        # Create section entities from structured information
        if "structured_info" in parsing_results.get("parsing_results", {}).get(best_parser, {}):
            structured_info = parsing_results["parsing_results"][best_parser]["structured_info"]
            doc_structure = structured_info.get("document_structure", {})
            
            # Create section entities
            sections = doc_structure.get("sections", [])
            for i, section in enumerate(sections):
                section_id = f"section_{doc_id}_{i}"
                section_entity = {
                    "id": section_id,
                    "type": "Section",
                    "properties": {
                        "title": section.get("title", f"Section {i+1}"),
                        "level": section.get("level", 1),
                        "line": section.get("line"),
                        "parser": best_parser
                    }
                }
                result["entities"].append(section_entity)
                sections_created[section.get("title", f"Section {i+1}")] = section_id
                
                # Create relationship: Document -> Section
                result["relationships"].append({
                    "source": doc_id,
                    "target": section_id,
                    "type": "CONTAINS_SECTION",
                    "properties": {"parser": best_parser}
                })
            
            # Create table entities
            tables = doc_structure.get("tables", [])
            for i, table in enumerate(tables):
                table_id = f"table_{doc_id}_{i}"
                table_entity = {
                    "id": table_id,
                    "type": "Table", 
                    "properties": {
                        "content": table.get("content", "")[:200],  # Truncate for storage
                        "page": table.get("page"),
                        "parser": best_parser
                    }
                }
                result["entities"].append(table_entity)
                
                # Create relationship: Document -> Table
                result["relationships"].append({
                    "source": doc_id,
                    "target": table_id, 
                    "type": "CONTAINS_TABLE",
                    "properties": {"parser": best_parser}
                })
        
        return sections_created
    
    def _create_domain_enhanced_keyword_entities(self, doc_id: str, keywords: Dict[str, Any],
                                               result: Dict[str, Any], sections_created: Dict[str, str],
                                               domain: DocumentDomain, document_text: str):
        """Create domain-enhanced keyword entities with sophisticated relationship inference."""
        keyword_entities = {}
        domain_schema = self.schema_manager.get_domain_schema(domain)

        for extractor_name, extractor_keywords in keywords.items():
            for kw_data in extractor_keywords:
                keyword = kw_data.get("keyword", "")
                if not keyword or len(keyword) < 2:
                    continue

                # Classify keyword to domain-specific entity type
                entity_type = self.schema_manager._classify_keyword_to_entity_type(
                    keyword, domain_schema["entities"]
                )

                # Create unique ID for each word-extractor combination
                kw_id = f"{entity_type.lower()}_{_hash(keyword)}_{extractor_name}"

                if kw_id not in keyword_entities:
                    # Get additional properties for this entity type and domain
                    additional_props = self.schema_manager._get_additional_entity_properties(
                        keyword, entity_type, domain
                    )

                    keyword_entity = {
                        "id": kw_id,
                        "type": entity_type,  # Domain-specific entity type
                        "properties": {
                            "text": keyword,
                            "extractors": [],
                            "max_score": 0,
                            "categories": set(),
                            "positions": [],
                            "domain": domain.value,
                            **additional_props
                        }
                    }
                    keyword_entities[kw_id] = keyword_entity

                # Check if this extractor already exists for this keyword
                existing_extractor = None
                for ext in keyword_entities[kw_id]["properties"]["extractors"]:
                    if ext["name"] == extractor_name:
                        existing_extractor = ext
                        break

                if existing_extractor is None:
                    # Add new extractor information
                    extractor_info = {
                        "name": extractor_name,
                        "score": kw_data.get("score", 0),
                        "category": kw_data.get("category", "unknown"),
                        "occurrence_count": 1
                    }
                    keyword_entities[kw_id]["properties"]["extractors"].append(extractor_info)
                else:
                    # Update existing extractor with higher score and increment count
                    existing_extractor["score"] = max(existing_extractor["score"], kw_data.get("score", 0))
                    existing_extractor["occurrence_count"] = existing_extractor.get("occurrence_count", 1) + 1

                keyword_entities[kw_id]["properties"]["max_score"] = max(
                    keyword_entities[kw_id]["properties"]["max_score"],
                    kw_data.get("score", 0)
                )
                keyword_entities[kw_id]["properties"]["categories"].add(kw_data.get("category", "unknown"))

                # Add position information if available
                if kw_data.get("start_position") is not None:
                    keyword_entities[kw_id]["properties"]["positions"].append({
                        "start": kw_data.get("start_position"),
                        "end": kw_data.get("end_position"),
                        "page": kw_data.get("page_number"),
                        "extractor": extractor_name
                    })

        # Convert sets to lists for JSON serialization and add entities with enhanced relationships
        for kw_entity in keyword_entities.values():
            kw_entity["properties"]["categories"] = list(kw_entity["properties"]["categories"])
            result["entities"].append(kw_entity)

            # Extract context around keyword for relationship inference
            context = self._extract_keyword_context(document_text, kw_entity["properties"]["text"])

            # Get enhanced relationship type based on context and domain
            base_rel_type, specific_rel_type = self.schema_manager.get_enhanced_relationship_type(
                "Document", kw_entity["type"], context, domain
            )

            # Create relationship: Document -> Entity with specific relationship name
            result["relationships"].append({
                "source": doc_id,
                "target": kw_entity["id"],
                "type": base_rel_type,
                "properties": {
                    "relationship_name": specific_rel_type,
                    "max_score": kw_entity["properties"]["max_score"],
                    "extractor_count": len(kw_entity["properties"]["extractors"]),
                    "context_snippet": context[:100] if context else "",
                    "domain": domain.value
                }
            })

    def _extract_keyword_context(self, text: str, keyword: str, context_size: int = 100) -> str:
        """Extract context around a keyword for relationship inference."""
        text_lower = text.lower()
        keyword_lower = keyword.lower()

        pos = text_lower.find(keyword_lower)
        if pos == -1:
            return ""

        start = max(0, pos - context_size)
        end = min(len(text), pos + len(keyword) + context_size)

        return text[start:end]

    def _create_keyword_entities(self, doc_id: str, keywords: Dict[str, Any], result: Dict[str, Any], sections_created: Dict[str, str]):
        """Create keyword entities with word-focus and extractor metadata."""
        keyword_entities = {}

        for extractor_name, extractor_keywords in keywords.items():
            for kw_data in extractor_keywords:
                keyword = kw_data.get("keyword", "")
                if not keyword or len(keyword) < 2:
                    continue

                # Create unique ID for each word-extractor combination
                kw_id = f"kw_{_hash(keyword)}_{extractor_name}"

                if kw_id not in keyword_entities:
                    keyword_entity = {
                        "id": kw_id,
                        "type": "Keyword",
                        "properties": {
                            "text": keyword,
                            "extractors": [],
                            "max_score": 0,
                            "categories": set(),
                            "positions": []
                        }
                    }
                    keyword_entities[kw_id] = keyword_entity

                # Check if this extractor already exists for this keyword
                existing_extractor = None
                for ext in keyword_entities[kw_id]["properties"]["extractors"]:
                    if ext["name"] == extractor_name:
                        existing_extractor = ext
                        break

                if existing_extractor is None:
                    # Add new extractor information
                    extractor_info = {
                        "name": extractor_name,
                        "score": kw_data.get("score", 0),
                        "category": kw_data.get("category", "unknown"),
                        "occurrence_count": 1
                    }
                    keyword_entities[kw_id]["properties"]["extractors"].append(extractor_info)
                else:
                    # Update existing extractor with higher score and increment count
                    existing_extractor["score"] = max(existing_extractor["score"], kw_data.get("score", 0))
                    existing_extractor["occurrence_count"] = existing_extractor.get("occurrence_count", 1) + 1

                keyword_entities[kw_id]["properties"]["max_score"] = max(
                    keyword_entities[kw_id]["properties"]["max_score"],
                    kw_data.get("score", 0)
                )
                keyword_entities[kw_id]["properties"]["categories"].add(kw_data.get("category", "unknown"))

                # Add position information if available
                if kw_data.get("start_position") is not None:
                    keyword_entities[kw_id]["properties"]["positions"].append({
                        "start": kw_data.get("start_position"),
                        "end": kw_data.get("end_position"),
                        "page": kw_data.get("page_number"),
                        "extractor": extractor_name
                    })

        # Convert sets to lists for JSON serialization and add entities
        for kw_entity in keyword_entities.values():
            kw_entity["properties"]["categories"] = list(kw_entity["properties"]["categories"])
            result["entities"].append(kw_entity)

            # Create relationship: Document -> Keyword
            result["relationships"].append({
                "source": doc_id,
                "target": kw_entity["id"],
                "type": "CONTAINS_KEYWORD",
                "properties": {
                    "max_score": kw_entity["properties"]["max_score"],
                    "extractor_count": len(kw_entity["properties"]["extractors"])
                }
            })

    def load_metadata(self, path: str) -> Dict[str, Any]:
        p = Path(path)
        if p.suffix.lower() != ".json":
            raise ValueError("Input must be a JSON metadata file path")
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    def build(self, metadata: Dict[str, Any]) -> GraphData:
        # Determine base document identity
        file_info = metadata.get("file_info", {})
        abs_path = file_info.get("absolute_path") or metadata.get("absolute_path") or metadata.get("file_path") or "unknown"
        doc_id = _hash(str(abs_path))

        # Document node properties
        document_props = {
            "doc_id": doc_id,
            "path": abs_path,
            "title": metadata.get("title") or metadata.get("dc_title") or file_info.get("relative_path") or Path(abs_path).name,
            "document_type": metadata.get("document_type") or metadata.get("dc_type"),
            "language": metadata.get("language") or metadata.get("dc_language"),
            "organization": metadata.get("organization") or metadata.get("dc_publisher"),
            "date": metadata.get("date") or metadata.get("dc_date"),
            "size": file_info.get("size"),
            "modified": file_info.get("modified"),
            "extension": file_info.get("extension") or Path(abs_path).suffix.lower(),
        }

        # Optional summary if available
        summary = None
        if "summary" in metadata:
            summary = metadata.get("summary")
        elif "content_analysis" in metadata and isinstance(metadata["content_analysis"], dict):
            # Some LLM extractions store summary inside content_analysis
            ca = metadata["content_analysis"]
            summary = ca.get("summary") or ca.get("intro") or ca.get("core")
        if summary:
            document_props["summary"] = summary

        # Collect topics/keywords from multiple possible keys
        topics = set(self._string_list(metadata.get("main_topics")))
        # Some content_analysis may also include topics
        ca = metadata.get("content_analysis") or {}
        if isinstance(ca, dict):
            topics.update(self._string_list(ca.get("main_topics")))
            topics.update(self._string_list(ca.get("topics")))
        keywords = set(self._string_list(metadata.get("keywords")))

        # Organizations
        orgs = set()
        org = metadata.get("organization") or metadata.get("dc_publisher")
        if org:
            orgs.add(str(org))

        # URLs (from content metadata extraction if present)
        urls = set()
        content_meta = metadata.get("content_metadata") or {}
        if isinstance(content_meta, dict):
            for k in ("urls", "links"):
                for u in self._string_list(content_meta.get(k)):
                    urls.add(u)

        # Sections
        sections: List[Tuple[str, Dict[str, Any]]] = []  # (section_id, props)
        doc_sections_edges: List[Dict[str, Any]] = []
        section_hierarchy_edges: List[Dict[str, Any]] = []

        def add_section(title: str, level: int, index: int, parent_id: Optional[str]):
            if not title:
                return
            sid = f"{doc_id}:{level}:{index}:{_hash(title)[:6]}"
            sections.append(
                (
                    sid,
                    {
                        "section_id": sid,
                        "title": title,
                        "level": level,
                        "index": index,
                    },
                )
            )
            doc_sections_edges.append({"doc_id": doc_id, "section_id": sid})
            if parent_id:
                section_hierarchy_edges.append({"parent_id": parent_id, "child_id": sid})
            return sid

        # Try docling structure
        docling = metadata.get("docling_structure")
        if isinstance(docling, dict) and docling.get("sections"):
            parent_stack: List[Tuple[int, str]] = []  # (level, section_id)
            for i, sec in enumerate(docling.get("sections", []), 1):
                title = str(sec.get("title") or sec.get("name") or f"Section {i}")
                level = int(sec.get("level") or 1)
                parent_id = None
                while parent_stack and parent_stack[-1][0] >= level:
                    parent_stack.pop()
                if parent_stack:
                    parent_id = parent_stack[-1][1]
                sid = add_section(title, level, i, parent_id)
                if sid:
                    parent_stack.append((level, sid))

        # Fallback: document_structure (if present)
        doc_struct = metadata.get("document_structure")
        if isinstance(doc_struct, dict) and doc_struct.get("sections"):
            base_index = len(sections)
            for j, sec in enumerate(doc_struct.get("sections", []), 1):
                title = str(sec.get("title") or f"Section {j}")
                add_section(title, int(sec.get("level") or 1), base_index + j, None)

        # Build node dictionaries, dedup by unique keys
        documents = [document_props]
        topic_nodes = [{"name": t} for t in sorted(topics) if t]
        keyword_nodes = [{"text": k} for k in sorted(keywords) if k]
        org_nodes = [{"name": o} for o in sorted(orgs) if o]
        url_nodes = [{"url": u} for u in sorted(urls) if u]
        section_nodes = [props for _, props in sections]

        # Relationships
        doc_topic_edges = [{"doc_id": doc_id, "name": t["name"]} for t in topic_nodes]
        doc_keyword_edges = [{"doc_id": doc_id, "text": k["text"]} for k in keyword_nodes]
        doc_org_edges = [{"doc_id": doc_id, "name": o["name"]} for o in org_nodes]
        doc_url_edges = [{"doc_id": doc_id, "url": u["url"]} for u in url_nodes]

        return GraphData(
            documents=documents,
            topics=topic_nodes,
            keywords=keyword_nodes,
            orgs=org_nodes,
            urls=url_nodes,
            sections=section_nodes,
            doc_topics=doc_topic_edges,
            doc_keywords=doc_keyword_edges,
            doc_orgs=doc_org_edges,
            doc_urls=doc_url_edges,
            doc_sections=doc_sections_edges,
            section_hierarchy=section_hierarchy_edges,
        )

    def to_cypher(self, g: GraphData) -> Dict[str, Any]:
        """Return a dict with 'params' and 'statements' (list of Cypher)."""
        params = {
            "documents": g.documents,
            "topics": g.topics,
            "keywords": g.keywords,
            "orgs": g.orgs,
            "urls": g.urls,
            "sections": g.sections,
            "doc_topics": g.doc_topics,
            "doc_keywords": g.doc_keywords,
            "doc_orgs": g.doc_orgs,
            "doc_urls": g.doc_urls,
            "doc_sections": g.doc_sections,
            "section_hierarchy": g.section_hierarchy,
        }

        stmts = [
            # Nodes
            "UNWIND $documents AS doc MERGE (d:Document {doc_id: doc.doc_id}) SET d += doc;",
            "UNWIND $topics AS t MERGE (:Topic {name: t.name});",
            "UNWIND $keywords AS k MERGE (:Keyword {text: k.text});",
            "UNWIND $orgs AS o MERGE (:Organization {name: o.name});",
            "UNWIND $urls AS u MERGE (:URL {url: u.url});",
            "UNWIND $sections AS s MERGE (:Section {section_id: s.section_id}) SET s += s;",
            # Relationships
            "UNWIND $doc_topics AS rel MATCH (d:Document {doc_id: rel.doc_id}) MERGE (t:Topic {name: rel.name}) MERGE (d)-[:HAS_TOPIC]->(t);",
            "UNWIND $doc_keywords AS rel MATCH (d:Document {doc_id: rel.doc_id}) MERGE (k:Keyword {text: rel.text}) MERGE (d)-[:HAS_KEYWORD]->(k);",
            "UNWIND $doc_orgs AS rel MATCH (d:Document {doc_id: rel.doc_id}) MERGE (o:Organization {name: rel.name}) MERGE (d)-[:PUBLISHED_BY]->(o);",
            "UNWIND $doc_urls AS rel MATCH (d:Document {doc_id: rel.doc_id}) MERGE (u:URL {url: rel.url}) MERGE (d)-[:CONTAINS_URL]->(u);",
            "UNWIND $doc_sections AS rel MATCH (d:Document {doc_id: rel.doc_id}), (s:Section {section_id: rel.section_id}) MERGE (d)-[:HAS_SECTION]->(s);",
            "UNWIND $section_hierarchy AS rel MATCH (p:Section {section_id: rel.parent_id}), (c:Section {section_id: rel.child_id}) MERGE (p)-[:HAS_SUBSECTION]->(c);",
        ]

        return {"params": params, "statements": stmts}

    def save_outputs(self, metadata_path: str, g: GraphData, cypher_bundle: Dict[str, Any]) -> Dict[str, str]:
        meta_p = Path(metadata_path)
        base = meta_p.with_suffix("")  # strip .json once
        out_json = str(base.with_suffix(".kg.json"))
        out_cypher = str(base.with_suffix(".kg.cypher"))

        # Save graph JSON
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump({
                "nodes": {
                    "documents": g.documents,
                    "topics": g.topics,
                    "keywords": g.keywords,
                    "orgs": g.orgs,
                    "urls": g.urls,
                    "sections": g.sections,
                },
                "relationships": {
                    "doc_topics": g.doc_topics,
                    "doc_keywords": g.doc_keywords,
                    "doc_orgs": g.doc_orgs,
                    "doc_urls": g.doc_urls,
                    "doc_sections": g.doc_sections,
                    "section_hierarchy": g.section_hierarchy,
                }
            }, f, ensure_ascii=False, indent=2)

        # Save Cypher statements as a script with JSON params comment
        with open(out_cypher, "w", encoding="utf-8") as f:
            f.write("// Memgraph/OpenCypher import script\n")
            f.write("// Execute statements sequentially with the params below\n")
            f.write("// Params (JSON):\n")
            f.write("// ")
            f.write(json.dumps(cypher_bundle["params"], ensure_ascii=False)[:100000])  # truncate to keep file reasonable
            f.write("\n\n")
            for s in cypher_bundle["statements"]:
                f.write(s + "\n")

        return {"kg_json": out_json, "kg_cypher": out_cypher}

    @staticmethod
    def _string_list(value: Any) -> List[str]:
        if not value:
            return []
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        return [str(value).strip()]

