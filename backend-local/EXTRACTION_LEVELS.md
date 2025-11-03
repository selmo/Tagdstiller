# 3-Level Extraction System Documentation

## Overview

This document describes the 3-level entity extraction system implemented for the Knowledge Graph builder, which allows users to control the depth and granularity of entity extraction.

**Implementation Date**: 2025-11-03

## Extraction Levels

### 1. Brief (간략) - Quick Overview
- **Target**: 10-20 key entities
- **Focus**: Only the most important entities
- **Use Case**:
  - Quick document overview
  - Main subject identification
  - Fast processing needed
- **Example**: Extract only main characters, organizations, and key concepts from a document

### 2. Standard (기본) - Balanced Analysis
- **Target**: 30-50 entities
- **Focus**: Balanced coverage of major and important supporting entities
- **Use Case**:
  - General document analysis (default)
  - Balanced between speed and detail
  - Recommended for most scenarios
- **Example**: Extract main entities plus important supporting details

### 3. Deep (심층) - Comprehensive Extraction
- **Target**: 100-300+ entities (no artificial limits)
- **Focus**: Exhaustive extraction of ALL entities without limits
- **Use Case**:
  - Complete knowledge extraction
  - Detailed analysis required
  - When no entity should be missed
  - Long technical documents requiring comprehensive coverage
- **Example**: Extract ALL entities including minor details, ALL specific data values, ALL dates, ALL locations, ALL numerical values, ALL measurements

## Technical Implementation

### Files Modified

1. **backend/prompts/templates.py**
   - Added 3 new prompt templates:
     - `PHASE1_ENTITY_BRIEF`
     - `PHASE1_ENTITY_STANDARD`
     - `PHASE1_ENTITY_DEEP`
   - Maintained backward compatibility with `PHASE1_ENTITY_ONLY = PHASE1_ENTITY_STANDARD`

2. **backend/services/knowledge_graph_builder.py**
   - Modified `_extract_kg_from_chunk_2phase()` to accept `extraction_level` parameter
   - Added prompt selection logic using dictionary mapping
   - Modified `build_full_knowledge_graph_with_chunking()` to pass `extraction_level` through

3. **backend/routers/knowledge_graph.py**
   - Added `extraction_level: str = "standard"` to `ChunkedKnowledgeGraphRequest` model
   - Updated endpoint to pass `extraction_level` to kg_builder

4. **README.md**
   - Added documentation for 3-level system
   - Added usage examples for each level

## API Usage

### Request Model

```python
class ChunkedKnowledgeGraphRequest(BaseModel):
    file_path: str
    directory: Optional[str] = None
    domain: str = "general"
    force_reparse: bool = False
    include_structure: bool = True
    save_format: str = "json"
    max_chunk_tokens: int = 8000
    llm: Optional[Dict[str, Any]] = None
    extraction_level: str = "standard"  # NEW: "brief", "standard", "deep"
```

### Usage Examples

#### Brief Extraction
```bash
curl -X POST http://localhost:58000/local-analysis/full-knowledge-graph-chunked \
  -H 'Content-Type: application/json' \
  -d '{
    "file_path": "/path/to/document.pdf",
    "extraction_level": "brief"
  }'
```

#### Standard Extraction (Default)
```bash
curl -X POST http://localhost:58000/local-analysis/full-knowledge-graph-chunked \
  -H 'Content-Type: application/json' \
  -d '{
    "file_path": "/path/to/document.pdf",
    "extraction_level": "standard"
  }'
```

#### Deep Extraction
```bash
curl -X POST http://localhost:58000/local-analysis/full-knowledge-graph-chunked \
  -H 'Content-Type: application/json' \
  -d '{
    "file_path": "/path/to/document.pdf",
    "extraction_level": "deep"
  }'
```

## Testing

Test configuration files have been created in `/tmp/`:
- `/tmp/kg_test_brief.json` - Brief extraction test
- `/tmp/kg_test_extraction_levels.json` - Standard extraction test (default)
- `/tmp/kg_test_deep.json` - Deep extraction test

### Test Command
```bash
# Test brief extraction
curl -X POST http://localhost:58000/local-analysis/full-knowledge-graph-chunked \
  -H 'Content-Type: application/json' \
  -d @/tmp/kg_test_brief.json

# Test standard extraction
curl -X POST http://localhost:58000/local-analysis/full-knowledge-graph-chunked \
  -H 'Content-Type: application/json' \
  -d @/tmp/kg_test_extraction_levels.json

# Test deep extraction
curl -X POST http://localhost:58000/local-analysis/full-knowledge-graph-chunked \
  -H 'Content-Type: application/json' \
  -d @/tmp/kg_test_deep.json
```

## Prompt Design Principles

### Brief Level
- Focus on main subjects only
- Avoid minor details
- Ultra-short properties (name only)
- 10-20 entity target explicitly stated

### Standard Level
- Balanced coverage
- Include main and important supporting entities
- 30-50 entity target
- Good balance between speed and comprehensiveness

### Deep Level
- Comprehensive entity types (12 types vs 6 in brief)
- Include ALL entities: major, minor, supporting details
- Specific data values, dates, locations
- 50-80 entity target
- Exhaustive extraction instruction

## Performance Characteristics

| Level | Target Entities | Processing Time | Use Case |
|-------|----------------|-----------------|----------|
| Brief | 10-20 | Fastest | Quick overview |
| Standard | 30-50 | Medium (default) | General analysis |
| Deep | 100-300+ | Slowest | Complete extraction (no limits) |

## Integration with 2-Phase System

The extraction levels work seamlessly with the existing 2-phase extraction system:

1. **Phase 1**: Uses selected level prompt (brief/standard/deep) to extract entities
2. **Phase 2**: Uses the same relationship extraction logic for all levels

This means:
- More entities in Phase 1 (deep) → More potential relationships in Phase 2
- Fewer entities in Phase 1 (brief) → Focused relationships between key entities

## Backward Compatibility

- Default value: `extraction_level = "standard"`
- If parameter omitted, uses standard level (30-50 entities)
- Existing API calls without this parameter will continue to work as before

## Future Enhancements

Potential improvements:
1. Add validation to ensure only valid levels ("brief", "standard", "deep") are accepted
2. Add level-specific relationship extraction strategies
3. Add performance metrics comparison between levels
4. Add automatic level recommendation based on document size
