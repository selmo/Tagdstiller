"""
Document parser module

Supported file formats:
- TXT: Plain text files (.txt, .text, .log, .csv, .tsv)
- PDF: PDF documents (.pdf)
- DOCX: Microsoft Word documents (.docx, .docm)
- HTML: HTML documents (.html, .htm, .xhtml)
- Markdown: Markdown documents (.md, .markdown, .mdown, .mkd)
"""

from .base import DocumentParser, ParseResult, DocumentMetadata
from .txt_parser import TxtParser
from .pdf_parser import PdfParser
from .docx_parser import DocxParser
from .html_parser import HtmlParser
from .md_parser import MarkdownParser
from .auto_parser import AutoParser

__all__ = [
    # Base classes
    'DocumentParser',
    'ParseResult', 
    'DocumentMetadata',
    
    # Parser classes
    'TxtParser',
    'PdfParser',
    'DocxParser',
    'HtmlParser',
    'MarkdownParser',
    'AutoParser'
]

# Convenience functions
def get_parser_for_file(file_path) -> DocumentParser:
    """Returns a suitable parser for the file."""
    auto_parser = AutoParser()
    return auto_parser

def get_supported_extensions():
    """Returns a list of supported file extensions."""
    auto_parser = AutoParser()
    return auto_parser.get_supported_formats()["extensions"]

def get_supported_mime_types():
    """Returns a list of supported MIME types."""
    auto_parser = AutoParser()
    return auto_parser.get_supported_formats()["mime_types"]