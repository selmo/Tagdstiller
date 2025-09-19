from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
from typing import Any, Dict, Optional

from services.kg_builder import KGBuilder


router = APIRouter(prefix="/kg", tags=["kg"])


class BuildFromMetadataRequest(BaseModel):
    metadata_path: str  # Path to saved *.json metadata file
    save_files: bool = True  # Save .kg.json and .kg.cypher alongside the metadata file


@router.post("/build-from-metadata")
def build_from_metadata(req: BuildFromMetadataRequest) -> Dict[str, Any]:
    meta_path = Path(req.metadata_path)
    if not meta_path.exists() or not meta_path.is_file():
        raise HTTPException(status_code=400, detail=f"Metadata file not found: {meta_path}")
    if meta_path.suffix.lower() != ".json":
        raise HTTPException(status_code=400, detail="metadata_path must be a JSON file produced by the parsers")

    try:
        builder = KGBuilder()
        metadata = builder.load_metadata(str(meta_path))
        graph = builder.build(metadata)
        cypher_bundle = builder.to_cypher(graph)
        outputs = {}
        if req.save_files:
            outputs = builder.save_outputs(str(meta_path), graph, cypher_bundle)
        return {
            "status": "ok",
            "nodes": {
                "documents": graph.documents,
                "topics": graph.topics,
                "keywords": graph.keywords,
                "orgs": graph.orgs,
                "urls": graph.urls,
                "sections": graph.sections,
            },
            "relationships": {
                "doc_topics": graph.doc_topics,
                "doc_keywords": graph.doc_keywords,
                "doc_orgs": graph.doc_orgs,
                "doc_urls": graph.doc_urls,
                "doc_sections": graph.doc_sections,
                "section_hierarchy": graph.section_hierarchy,
            },
            "cypher": {
                "statements": cypher_bundle["statements"],
                "params_preview": {k: (v[:3] if isinstance(v, list) else v) for k, v in cypher_bundle["params"].items()},
            },
            "outputs": outputs,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"KG build failed: {e}")

