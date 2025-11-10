# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## System Overview

This is a **backend-local analysis server** for advanced document processing, implementing intelligent document chunking, multi-parser support, and LLM-integrated analysis. The system provides comprehensive document analysis capabilities including structure recognition, knowledge graph generation, and **advanced OCR for scanned documents with automatic detection**.

### Latest Updates (2025-11-04)
- **🧠 3-Level KG 추출 시스템**: Brief(10-20)/Standard(30-50)/Deep(100-300+) 추출 깊이 선택
- **📊 구조화된 테이블 추출**: 마크다운 테이블을 Table/TableRow/TableColumn 엔티티로 변환
- **🔄 2-Phase 추출 전략**: Phase 1(엔티티) + Phase 2(관계) 분리로 43% 추출량 증가
- **⚙️ KG → Cypher 변환기**: Knowledge Graph JSON을 Neo4j/Memgraph Cypher로 자동 변환
- **🔁 청킹 기반 완전 KG**: 대용량 문서의 구조 기반 청킹 및 계층적 병합
- **🛡️ JSON 자동 복구**: LLM 응답 잘림 시 불완전 JSON 자동 수정으로 데이터 손실 방지
- **🔄 자동 재시도**: Rate limit 429 초과 시 exponential backoff 재시도 (최대 3회)
- **🖼️ GPU/MPS 자동 감지**: CUDA/MPS 디바이스 자동 활성화로 OCR 성능 향상
- **🔍 스캔 문서 자동 감지**: 텍스트 품질 평가를 통한 스캔 문서 자동 판별
- **🎯 전체 페이지 OCR 시스템**: Docling + EasyOCR/Tesseract 통합 파서
- **🌏 다국어 OCR 지원**: 한글+영문 혼합 텍스트 최적화 (EasyOCR)
- **🖼️ 적응형 이미지 전처리**: 적응형 이진화, 노이즈 제거, 선명화
- **⚡ OCR 엔진 선택 지원**: auto/easyocr/tesseract 모드 전환
- **📊 Gemini 스트리밍 개선**: 비스트리밍 모드 사용으로 안정성 향상

## Core Architecture

### Service Layer Architecture
The backend follows a service-oriented architecture with clear separation of concerns:

- **routers/knowledge_graph.py**: Main API endpoint handling document analysis requests
  - `/knowledge-graph`: Basic KG extraction (single document, no chunking)
  - `/full-knowledge-graph-chunked`: **NEW** - Structure-based chunking with hierarchical merging and 3-level extraction depth
- **services/**: Core business logic services
  - `document_parser_service.py`: Multi-parser document processing (PyMuPDF, Docling, python-docx, BeautifulSoup4)
  - `document_chunker.py`: **UPDATED** - Structure-based chunking with section title preservation (##)
  - `knowledge_graph_builder.py`: **ENHANCED** - 2-Phase extraction (entities + relationships), JSON auto-recovery, exponential backoff retry
  - `chunk_analyzer.py`: Chunk-level analysis and result integration
  - `chunk_prompt_manager.py`: LLM prompt generation and execution management
  - `local_file_analyzer.py`: LLM-based document structure analysis
  - `image_analyzer.py`: OCR and image analysis for scanned documents
  - `config_service.py`: Configuration management with SQLite persistence
- **services/parser/**: Document parser implementations
  - `docling_ocr_parser.py`: **UPDATED** - Docling + OCR 통합 파서 (CUDA/MPS GPU 자동 감지)
  - `base.py`: Parser base class and common interfaces
- **backend/utils/**: **NEW** - Utility modules
  - `kg_to_cypher.py`: Knowledge Graph JSON → Neo4j/Memgraph Cypher converter
- **backend/prompts/**: **ENHANCED** - LLM prompt templates
  - `templates.py`: 3-level extraction prompts (PHASE1_ENTITY_BRIEF/STANDARD/DEEP), table extraction rules

### Document Processing Pipeline
1. **Multi-Parser Processing**: Documents are processed through multiple parsers simultaneously to ensure optimal text extraction
2. **Intelligent Chunking**: Large documents are automatically chunked based on LLM token limits and document structure (chapters, sections with ## titles preserved)
3. **2-Phase LLM Analysis**: **NEW**
   - **Phase 1**: Entity extraction only (token efficiency maximized)
   - **Phase 2**: Relationship extraction using Phase 1 entities
   - Result: 43% more entities extracted vs single-phase approach
4. **JSON Auto-Recovery**: **NEW** - Incomplete JSON responses automatically repaired (handles LLM response truncation)
5. **Exponential Backoff Retry**: **NEW** - Automatic retry on rate limit (429) errors with 2s → 4s → 8s delays (max 3 attempts)
6. **Result Integration**: Chunk results are hierarchically merged to produce comprehensive document analysis

### Key Data Models
- **DocumentNode**: Represents hierarchical document structure (document → chapter → section → subsection)
- **ChunkAnalysisResult**: Individual chunk analysis containing keywords, summaries, structure analysis, and knowledge graphs
- **IntegratedAnalysisResult**: Final merged analysis combining all chunks with statistics and metadata

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt
```

### Running the Server
```bash
# Using the startup script (recommended)
./start_local_backend.sh

# Manual startup
cd backend
uvicorn main:app --reload --port 58000

# Development with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 58000
```

### Testing
```bash
# Run pytest (if tests exist)
cd backend
pytest

# Test API endpoints manually
curl -X POST "http://localhost:58000/local-analysis/knowledge-graph" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/path/to/document.pdf"}'
```

### Environment Variables for Development
```bash
# LLM API Configuration
export OPENAI_API_KEY="your-openai-key"
export GEMINI_API_KEY="your-gemini-key"

# Development Mode Settings
export OFFLINE_MODE=true          # Skip external API calls
export SKIP_EXTERNAL_CHECKS=true # Fast startup mode
```

## Code Architecture Details

### Multi-Parser Strategy
The system employs a "best result" strategy using multiple document parsers:
- **PyMuPDF**: Primary PDF parser, fast and reliable
- **Docling**: Advanced PDF parser with table/image extraction capabilities
- **DoclingOCR (NEW)**: Intelligent OCR-integrated parser with:
  - **자동 스캔 감지**: 텍스트 밀도 기반 스캔 문서 자동 판별
  - **전체 페이지 OCR**: 스캔 문서 전용 고품질 OCR 처리
  - **하이브리드 모드**: 일반 문서는 Docling, 스캔 문서는 OCR 자동 전환
  - **다중 OCR 엔진**: EasyOCR (한글 최적), Tesseract (범용), auto (자동 선택)
  - **적응형 전처리**: 이미지별 최적 전처리 알고리즘 자동 선택
- **python-docx**: DOCX document processing
- **BeautifulSoup4**: HTML/XML document parsing
- **pymupdf4llm**: Enhanced text extraction optimized for LLM processing

### Intelligent Chunking Algorithm
The chunking system preserves document logical structure:
- **Structure Recognition**: Identifies chapters, sections, and subsections using pattern matching
- **Hierarchy Preservation**: Maintains parent-child relationships between document sections
- **Token-Aware Splitting**: Automatically chunks based on LLM token limits (configurable)
- **Context Preservation**: Ensures chunks don't break mid-sentence or mid-paragraph

### LLM Integration
Multi-provider LLM support with automatic fallback:
- **Supported Providers**: OpenAI, Google Gemini, Ollama
- **Gemini Optimization (NEW)**: Non-streaming mode for improved stability
  - Avoids incomplete responses in streaming mode
  - Better handling of large documents
  - Consistent JSON response parsing
- **Dynamic Token Management**: Adjusts chunk sizes based on model capabilities
- **Prompt Templates**: Structured prompts for consistent analysis across chunks
- **Error Recovery**: Automatic retry and fallback mechanisms
- **Response Validation**: Complete payload parsing before processing

### Analysis Types
The system supports multiple analysis modes:
- **Structure Analysis**: Document hierarchy and organization patterns
- **Keyword Extraction**: Multi-algorithm keyword identification
- **Summary Generation**: Hierarchical summarization from chunk to document level
- **Knowledge Graph**: Entity and relationship extraction with graph database integration

## File Organization Patterns

### Output Structure
Analysis results are organized in predictable directory structures:
```
output_directory/
├── parsing_results.json           # Multi-parser results summary
├── llm_structure_analysis.json    # LLM-based structure analysis
├── llm_structure_response.json    # API response summary
├── docling.md                     # Docling parser output (markdown)
├── pymupdf4llm.md                 # PyMuPDF parser output (markdown)
└── chunk_analysis/                # Chunking analysis (for large docs)
    ├── chunk_analysis_report.json
    ├── chunks_text/               # Individual chunk text files
    ├── chunk_prompts/             # LLM prompts for each chunk
    └── chunk_results/             # LLM execution results
```

### Configuration Management
Configuration is stored in SQLite with in-memory caching:
- **Database**: `backend/docextract.db` (SQLite)
- **Cache**: In-memory configuration cache for performance
- **Initialization**: Default configurations auto-created on startup

## Development Guidelines

### Error Handling
- All external API calls (LLM providers) include automatic retry with exponential backoff
- Graceful degradation when optional components fail (e.g., OCR, advanced parsers)
- Comprehensive logging for debugging complex multi-step processes

### Performance Considerations
- **Parallel Processing**: Multiple chunks can be processed concurrently
- **Caching**: Parsing results are cached to avoid reprocessing
- **Memory Management**: Large documents are streamed rather than loaded entirely into memory

### Logging Strategy
- **Structured Logging**: JSON-formatted logs for parsing and analysis steps
- **Performance Metrics**: Processing time and token usage tracking
- **Debug Information**: Detailed logs for each chunk processing step

## Key Dependencies

### Core Framework
- **FastAPI**: Web framework with automatic OpenAPI documentation
- **SQLAlchemy**: Database ORM for configuration and metadata
- **Pydantic**: Data validation and serialization

### Document Processing
- **PyMuPDF**: Primary PDF processing library
- **Docling**: Advanced document layout analysis
- **python-docx**: Microsoft Word document processing
- **BeautifulSoup4**: HTML/XML parsing
- **EasyOCR**: Deep learning-based OCR (한글+영문 최적화)
- **Tesseract**: Traditional OCR engine (범용, 고속)
- **OpenCV (cv2)**: Image preprocessing and enhancement
- **Pillow**: Image format handling and conversion

### LLM Integration
- **LangChain**: LLM abstraction and prompt management
- **langchain-ollama**: Local LLM integration
- **langchain-community**: Extended LLM provider support

### Analysis Libraries
- **KeyBERT**: Keyword extraction using transformer models
- **spaCy**: Named entity recognition and NLP processing
- **sentence-transformers**: Semantic similarity and embeddings

## Advanced Knowledge Graph Extraction System (UPDATED - 2025-11-04)

### Overview
The system now features a comprehensive Knowledge Graph extraction pipeline with 3-level extraction depth, 2-phase processing, structured table support, and automatic error recovery.

### Key Features

#### 1. 3-Level Extraction Depth System
Choose extraction granularity based on your needs:

- **Brief (10-20 entities)**:
  - Quick document overview
  - Main subjects only
  - Fastest processing
  - Use case: Document triage, quick summaries

- **Standard (30-50 entities)** - **DEFAULT**:
  - Balanced coverage
  - Major and important supporting entities
  - Medium processing time
  - Use case: General document analysis

- **Deep (100-300+ entities)**:
  - Exhaustive extraction without limits
  - ALL entities including minor details
  - Comprehensive data values, dates, locations
  - Use case: Complete knowledge extraction for research

**API Usage:**
```bash
# Deep extraction for comprehensive analysis
curl -X POST http://localhost:58000/local-analysis/full-knowledge-graph-chunked \
  -H 'Content-Type: application/json' \
  -d '{
    "file_path": "/path/to/document.pdf",
    "extraction_level": "deep",
    "max_chunk_tokens": 8000
  }'
```

#### 2. 2-Phase Extraction Strategy
Dramatically improved entity extraction through separated phases:

- **Phase 1: Entity Extraction**
  - Focus 100% on identifying entities
  - Token efficiency maximized
  - No relationship overhead

- **Phase 2: Relationship Extraction**
  - Uses Phase 1 entities as context
  - Precise relationship mapping
  - Higher relationship quality

**Result**: 43% more entities extracted (80 → 274 entities in real-world test)

#### 3. Structured Table Extraction
Markdown tables are converted to graph entities with preserved structure:

**New Entity Types**:
- `Table`: Represents entire table (name, row_count, column_count)
- `TableRow`: Each data row with values array
- `TableColumn`: Each column with index
- `TableCell`: Individual cells (optional)

**New Relationship Types**:
- `HAS_ROW`: Table → TableRow
- `HAS_COLUMN`: Table → TableColumn
- `CONTAINS_VALUE`: TableRow → Data entities
- `IN_TABLE/IN_ROW/IN_COLUMN`: Reverse relationships

**Example Query**:
```cypher
// Get temperature data for "인천" location at 60% cumulative frequency
MATCH (t:Table)-[:HAS_COLUMN]->(col:TableColumn {column_name: "인천"})
MATCH (t)-[:HAS_ROW]->(row:TableRow)
WHERE row.values[0] = "온도" AND row.values[1] = "60%"
RETURN col.column_name, row.values[col.column_index] AS value
```

See `TABLE_EXTRACTION.md` for complete documentation.

#### 4. JSON Auto-Recovery System
Handles incomplete LLM responses gracefully:

- Detects truncated JSON (missing closing brackets)
- Recovers all complete entities/relationships
- Minimizes data loss from max_tokens limits
- Automatic completion of JSON arrays/objects

**Benefit**: No more failed extractions due to response truncation

#### 5. Exponential Backoff Retry
Robust handling of API rate limits:

- Automatic retry on 429 (Too Many Requests)
- Progressive delays: 2s → 4s → 8s
- Maximum 3 retry attempts
- Detailed error logging

**Benefit**: Significantly improved LLM API stability

#### 6. Knowledge Graph → Cypher Converter
Convert extracted KG to graph database queries:

**Features**:
- Converts KG JSON to Neo4j/Memgraph Cypher
- Automatic node/relationship creation
- Index generation for performance
- Database initialization (optional)

**Usage**:
```bash
# Convert KG JSON to Cypher
cd backend
python -m utils.kg_to_cypher /path/to/knowledge_graph.json output.cypher

# With options
python -m utils.kg_to_cypher input.json output.cypher --clear-db

# Bash wrapper
./scripts/kg_json_to_cypher.sh /path/to/knowledge_graph.json
```

See `KG_CYPHER_CONVERTER.md` for complete documentation.

### API Endpoints

#### Chunked Knowledge Graph (Recommended)
```bash
POST /local-analysis/full-knowledge-graph-chunked
```

**Request Parameters**:
- `file_path`: Path to document
- `extraction_level`: "brief" | "standard" | "deep" (default: "standard")
- `max_chunk_tokens`: Token limit per chunk (default: 8000)
- `domain`: Document domain (default: "general")
- `force_reparse`: Force document reparsing
- `include_structure`: Include structure analysis
- `save_format`: Output format (default: "json")

**Response**:
```json
{
  "graph": {
    "nodes": [...],
    "edges": [...]
  },
  "statistics": {
    "total_entities": 274,
    "total_relationships": 187,
    "chunks_processed": 5
  },
  "metadata": {
    "source_document": "document.pdf",
    "domain": "general",
    "extraction_level": "deep"
  }
}
```

### Document Structure Preservation

The chunking system now preserves markdown section titles:

```markdown
## Section Title     ← Preserved in chunks
Content here...
```

**Benefit**: Better context for LLM analysis and improved entity extraction accuracy

### Debug Files

Each extraction creates comprehensive debug files:

```
output_directory/
├── knowledge_graph.json              # Final merged KG
├── knowledge_graph.cypher            # Cypher conversion
├── chunk_analysis/
│   ├── chunk_analysis_report.json    # Statistics
│   ├── chunks_text/                  # Individual chunks
│   ├── chunk_prompts/                # Phase 1 & 2 prompts
│   │   ├── chunk_001_phase1_prompt.txt
│   │   └── chunk_001_phase2_prompt.txt
│   └── chunk_results/                # LLM responses
│       ├── chunk_001_phase1_response.json
│       ├── chunk_001_phase2_response.json
│       └── chunk_001_kg.json         # Merged chunk KG
```

### Performance Characteristics

| Extraction Level | Entities | Processing Time | Token Usage | Use Case |
|-----------------|----------|-----------------|-------------|----------|
| Brief | 10-20 | ~30s | Low | Quick overview |
| Standard | 30-50 | ~60s | Medium | General analysis |
| Deep | 100-300+ | ~120s | High | Comprehensive extraction |

*Based on 20-page technical document with Gemini 1.5 Pro*

### Related Documentation

- **EXTRACTION_LEVELS.md**: Detailed guide to 3-level extraction system
- **TABLE_EXTRACTION.md**: Complete table extraction documentation
- **KG_CYPHER_CONVERTER.md**: Graph database conversion guide

## Advanced OCR System (NEW - 2025-10-30)

### Overview
The system now includes a comprehensive OCR solution that automatically detects scanned documents and applies appropriate OCR processing.

### Key Features

#### 1. Automatic Scanned Document Detection
The system evaluates text quality using multiple metrics:
- **Text Density**: Characters per page ratio
- **Image Tag Count**: Number of image placeholders in Docling output
- **Blank Page Detection**: Identifies pages with minimal text
- **Combined Score**: Weighted algorithm for final classification

**Detection Logic:**
```python
is_scanned = (
    text_density < 50 chars/page OR
    image_tags > 5 per page OR
    (text_density < 100 AND image_tags > 3)
)
```

#### 2. Dual OCR Engine Support
- **EasyOCR (Recommended for Korean/Mixed)**:
  - Deep learning-based recognition
  - Excellent for mixed Korean+English text
  - GPU acceleration support
  - Higher accuracy, slower processing

- **Tesseract (Fast, General Purpose)**:
  - Traditional OCR engine
  - Fast processing speed
  - Good for clean scanned documents
  - Fallback option

- **Auto Mode (Default)**:
  - Tries EasyOCR first
  - Falls back to Tesseract if unavailable
  - Best of both worlds

#### 3. Advanced Image Preprocessing
Adaptive preprocessing pipeline with quality assessment:

**Preprocessing Techniques:**
1. **Adaptive Thresholding** (ADAPTIVE_THRESH_GAUSSIAN_C)
   - Best for documents with varying lighting
   - Preserves text edges

2. **Bilateral Filtering**
   - Noise reduction while preserving edges
   - Maintains text sharpness

3. **Morphological Operations**
   - MORPH_CLOSE for connecting broken characters
   - Kernel-based text enhancement

4. **Sharpening Filter**
   - Convolution-based edge enhancement
   - Improves OCR accuracy

**Preprocessing Selection:**
The system tries multiple preprocessing methods and selects the best result based on:
- OCR confidence scores
- Text length and completeness
- Character recognition quality

#### 4. Full-Page OCR Mode
When a document is detected as scanned:
1. Converts each PDF page to high-resolution image (300 DPI)
2. Applies adaptive preprocessing
3. Runs OCR with language detection (Korean + English)
4. Combines results with original document structure
5. Generates comprehensive markdown output

### Usage

#### API Request with OCR
```bash
curl -X POST 'http://localhost:58000/local-analysis/knowledge-graph' \
  -H 'Content-Type: application/json' \
  -d '{
    "file_path": "/path/to/scanned.pdf",
    "directory": "/path/to/output",
    "use_llm": false,
    "force_reparse": true,
    "analyze_images": true,
    "extract_images": true
  }'
```

#### OCR Engine Selection
Set via environment variable or config:
```python
# In config or initialization
ocr_engine = "auto"  # Options: "auto", "easyocr", "tesseract"
parser = DoclingOCRParser(ocr_engine=ocr_engine)
```

### Output Structure
```
output_directory/
├── docling_ocr/
│   ├── docling_ocr_text.txt          # Full OCR extracted text
│   ├── docling_ocr_metadata.json     # OCR statistics and metadata
│   ├── docling_ocr_structure.json    # Document structure
│   └── ocr_pages/                    # Per-page OCR results
│       ├── page_1.txt
│       ├── page_2.txt
│       └── ...
└── docling_ocr.md                    # Markdown with OCR text integrated
```

### Performance Metrics
- **EasyOCR**: ~3-5 seconds per page (Korean+English)
- **Tesseract**: ~1-2 seconds per page
- **Preprocessing**: ~0.5-1 second per page
- **Detection**: < 0.1 seconds

### Configuration
Key settings in `config_service.py`:
```python
OCR_ENGINE = "auto"              # OCR engine selection
OCR_CONFIDENCE_THRESHOLD = 0.3   # Minimum confidence for OCR results
OCR_DPI = 300                    # Image resolution for OCR
OCR_LANGUAGES = ['ko', 'en']     # Supported languages
```

### Testing
Refer to `DOCLING_OCR_TEST_GUIDE.md` for comprehensive testing instructions.

### Troubleshooting

#### EasyOCR Installation
```bash
pip install easyocr
# First run downloads models (~100MB)
```

#### Tesseract Installation
```bash
# macOS
brew install tesseract tesseract-lang

# Ubuntu/Debian
apt-get install tesseract-ocr tesseract-ocr-kor tesseract-ocr-eng

# Verify installation
tesseract --version
tesseract --list-langs
```

#### Common Issues
1. **Memory Error with EasyOCR**: Set `gpu=False` in initialization
2. **Poor OCR Quality**: Check image resolution (recommend 300 DPI)
3. **Missing Languages**: Install language packs for Tesseract
4. **Slow Processing**: Use `tesseract` mode for faster processing