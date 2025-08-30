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
    """Builds a KG from saved metadata JSON."""

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

