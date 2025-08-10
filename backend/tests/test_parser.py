import pytest
from pathlib import Path
import tempfile
import os
from services.parser import AutoParser, TxtParser, get_supported_extensions, get_supported_mime_types

class TestDocumentParsers:
    """Document parser system tests"""
    
    def test_get_supported_extensions(self):
        """Test getting supported file extensions"""
        extensions = get_supported_extensions()
        assert isinstance(extensions, list)
        assert '.txt' in extensions
        assert '.pdf' in extensions
        assert '.docx' in extensions
        assert '.html' in extensions
        assert '.md' in extensions
    
    def test_get_supported_mime_types(self):
        """Test getting supported MIME types"""
        mime_types = get_supported_mime_types()
        assert isinstance(mime_types, list)
        assert 'text/plain' in mime_types
        assert 'application/pdf' in mime_types
        assert 'text/html' in mime_types
    
    def test_txt_parser_simple_text(self):
        """Test TXT parser with simple text file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            test_content = "This is a test document.\nIt has multiple lines.\nFor testing purposes."
            f.write(test_content)
            f.flush()
            
            try:
                parser = TxtParser()
                result = parser.parse(Path(f.name))
                
                assert result.success is True
                assert result.text == test_content
                assert result.metadata.title == Path(f.name).stem
                assert result.metadata.word_count == 12
                assert result.parser_name == "txt_parser"
                
            finally:
                os.unlink(f.name)
    
    def test_txt_parser_encoding_detection(self):
        """Test TXT parser encoding detection"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            test_content = "UTF-8 테스트 문서입니다.\n한글이 포함된 내용입니다."
            f.write(test_content)
            f.flush()
            
            try:
                parser = TxtParser()
                result = parser.parse(Path(f.name))
                
                assert result.success is True
                assert "테스트" in result.text
                assert "한글" in result.text
                assert result.metadata.encoding is not None
                
            finally:
                os.unlink(f.name)
    
    def test_auto_parser_txt_detection(self):
        """Test AutoParser automatically detecting TXT files"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            test_content = "Auto parser test content."
            f.write(test_content)
            f.flush()
            
            try:
                auto_parser = AutoParser()
                result = auto_parser.parse(Path(f.name))
                
                assert result.success is True
                assert result.text == test_content
                assert "auto_parser -> txt_parser" in result.parser_name
                
            finally:
                os.unlink(f.name)
    
    def test_auto_parser_unsupported_extension(self):
        """Test AutoParser with unsupported file extension"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xyz', delete=False) as f:
            test_content = "Unsupported file content."
            f.write(test_content)
            f.flush()
            
            try:
                auto_parser = AutoParser()
                result = auto_parser.parse(Path(f.name))
                
                # Should still try txt parser as fallback
                assert result.success is True
                assert result.text == test_content
                
            finally:
                os.unlink(f.name)
    
    def test_auto_parser_can_parse_all_extensions(self):
        """Test AutoParser can handle all supported extensions"""
        auto_parser = AutoParser()
        
        # AutoParser should be able to parse any file
        test_path = Path("test.txt")
        assert auto_parser.can_parse(test_path) is True
        
        test_path = Path("test.unknown")
        assert auto_parser.can_parse(test_path) is True
    
    def test_auto_parser_supported_formats(self):
        """Test AutoParser returns comprehensive format information"""
        auto_parser = AutoParser()
        formats = auto_parser.get_supported_formats()
        
        assert 'extensions' in formats
        assert 'mime_types' in formats
        assert 'parsers' in formats
        
        assert isinstance(formats['extensions'], list)
        assert isinstance(formats['mime_types'], list)
        assert isinstance(formats['parsers'], dict)
        
        # Check individual parsers are included
        assert 'txt' in formats['parsers']
        assert 'pdf' in formats['parsers']
        assert 'docx' in formats['parsers']
        assert 'html' in formats['parsers']
        assert 'markdown' in formats['parsers']
    
    def test_auto_parser_file_analysis(self):
        """Test AutoParser file analysis functionality"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            test_content = "Analysis test content."
            f.write(test_content)
            f.flush()
            
            try:
                auto_parser = AutoParser()
                analysis = auto_parser.analyze_file(Path(f.name))
                
                assert 'file_path' in analysis
                assert 'extension' in analysis
                assert 'mime_type' in analysis
                assert 'suggested_parsers' in analysis
                assert 'parser_compatibility' in analysis
                
                assert analysis['extension'] == '.txt'
                assert 'txt' in analysis['suggested_parsers']
                
            finally:
                os.unlink(f.name)
    
    def test_parser_error_handling(self):
        """Test parser error handling for non-existent files"""
        auto_parser = AutoParser()
        non_existent_path = Path("/non/existent/file.txt")
        
        result = auto_parser.parse(non_existent_path)
        
        assert result.success is False
        assert result.error_message is not None
        assert "auto_parser" in result.parser_name

class TestParserIntegration:
    """Integration tests for parser system"""
    
    def test_multiple_file_types(self):
        """Test parsing multiple file types in sequence"""
        auto_parser = AutoParser()
        
        # Test TXT
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("TXT content")
            f.flush()
            
            try:
                result = auto_parser.parse(Path(f.name))
                assert result.success is True
                assert "TXT content" in result.text
            finally:
                os.unlink(f.name)
        
        # Test CSV (should be handled by TXT parser)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("header1,header2\nvalue1,value2")
            f.flush()
            
            try:
                result = auto_parser.parse(Path(f.name))
                assert result.success is True
                assert "header1,header2" in result.text
            finally:
                os.unlink(f.name)