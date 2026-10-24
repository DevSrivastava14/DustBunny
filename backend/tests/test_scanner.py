import pytest
from pathlib import Path
import tempfile
import os
from app.scanner import scan_folder, validate_folder_path, extract_text, FileScanError
from app.models import FileStatus


class TestValidateFolderPath:
    def test_valid_directory(self, tmp_path):
        result = validate_folder_path(str(tmp_path))
        assert result == tmp_path.resolve()
    
    def test_nonexistent_path(self):
        with pytest.raises(FileScanError) as exc:
            validate_folder_path("/nonexistent/path")
        assert exc.value.status == FileStatus.ERROR
        assert "does not exist" in exc.value.message
    
    def test_file_instead_of_directory(self, tmp_path):
        file_path = tmp_path / "test.txt"
        file_path.write_text("test")
        with pytest.raises(FileScanError) as exc:
            validate_folder_path(str(file_path))
        assert exc.value.status == FileStatus.ERROR
        assert "not a directory" in exc.value.message


class TestScanFolderPathTraversal:
    def test_symlink_outside_root_handled(self, tmp_path):
        target_dir = tmp_path / "outside"
        target_dir.mkdir()
        (target_dir / "secret.txt").write_text("secret")
        
        scan_dir = tmp_path / "scan"
        scan_dir.mkdir()
        try:
            link = scan_dir / "link.txt"
            link.symlink_to(target_dir / "secret.txt")
            results = scan_folder(str(scan_dir))
            assert len(results) == 0
        except (OSError, NotImplementedError):
            pytest.skip("Symlinks not supported on this platform")

    def test_relative_path_escape_handled(self, tmp_path, monkeypatch):
        scan_dir = tmp_path / "scan"
        scan_dir.mkdir()
        (scan_dir / "normal.txt").write_text("content")
        
        original_rglob = Path.rglob
        
        def mock_rglob(self, pattern):
            for item in original_rglob(self, pattern):
                yield item
            escape_file = tmp_path / "escape.txt"
            escape_file.write_text("escaped")
            yield escape_file
        
        monkeypatch.setattr(Path, "rglob", mock_rglob)
        
        results = scan_folder(str(scan_dir))
        filenames = {r["filename"] for r in results}
        assert "normal.txt" in filenames
        escaped = [r for r in results if r["filename"] == "escape.txt"]
        assert len(escaped) == 1
        assert escaped[0]["status"] == FileStatus.ERROR
        assert "escaped" in escaped[0]["error_message"].lower()


class TestScanFolder:
    def test_scan_empty_directory(self, tmp_path):
        results = scan_folder(str(tmp_path))
        assert results == []
    
    def test_scan_txt_file(self, tmp_path):
        (tmp_path / "test.txt").write_text("Hello world")
        results = scan_folder(str(tmp_path))
        assert len(results) == 1
        assert results[0]["filename"] == "test.txt"
        assert results[0]["status"] == FileStatus.SUCCESS
        assert results[0]["text"] == "Hello world"
    
    def test_scan_md_file(self, tmp_path):
        (tmp_path / "notes.md").write_text("# Title\n\nContent")
        results = scan_folder(str(tmp_path))
        assert len(results) == 1
        assert results[0]["filename"] == "notes.md"
        assert results[0]["status"] == FileStatus.SUCCESS
        assert "# Title" in results[0]["text"]
    
    def test_scan_pdf_file(self, tmp_path):
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "PDF content here")
        pdf_path = tmp_path / "doc.pdf"
        doc.save(str(pdf_path))
        doc.close()
        
        results = scan_folder(str(tmp_path))
        assert len(results) == 1
        assert results[0]["filename"] == "doc.pdf"
        assert results[0]["status"] == FileStatus.SUCCESS
        assert "PDF content" in results[0]["text"]
    
    def test_skip_unsupported_file(self, tmp_path):
        (tmp_path / "image.jpg").write_bytes(b"fake image")
        results = scan_folder(str(tmp_path))
        assert len(results) == 1
        assert results[0]["status"] == FileStatus.SKIPPED_UNSUPPORTED
        assert "Unsupported" in results[0]["error_message"]
    
    def test_skip_empty_file(self, tmp_path):
        (tmp_path / "empty.txt").write_text("")
        results = scan_folder(str(tmp_path))
        assert len(results) == 1
        assert results[0]["status"] == FileStatus.SKIPPED_EMPTY
    
    def test_skip_oversized_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MAX_FILE_SIZE_MB", "1")
        from app.config import get_settings
        get_settings.cache_clear()
        
        large_file = tmp_path / "large.txt"
        large_file.write_text("x" * (2 * 1024 * 1024))
        
        results = scan_folder(str(tmp_path))
        assert len(results) == 1
        assert results[0]["status"] == FileStatus.SKIPPED_OVERSIZED
        get_settings.cache_clear()
    
    def test_skip_symlink(self, tmp_path):
        target = tmp_path / "target.txt"
        target.write_text("content")
        link = tmp_path / "link.txt"
        try:
            link.symlink_to(target)
            results = scan_folder(str(tmp_path))
            assert len(results) == 1
            assert results[0]["filename"] == "target.txt"
        except (OSError, NotImplementedError):
            pytest.skip("Symlinks not supported on this platform")
    
    def test_subdirectory_recursion(self, tmp_path):
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("nested content")
        (tmp_path / "root.txt").write_text("root content")
        
        results = scan_folder(str(tmp_path))
        filenames = {r["filename"].replace("\\", "/") for r in results}
        assert "root.txt" in filenames
        assert "subdir/nested.txt" in filenames


class TestExtractText:
    def test_extract_txt(self, tmp_path):
        file_path = tmp_path / "test.txt"
        file_path.write_text("Test content")
        text = extract_text(file_path)
        assert text == "Test content"
    
    def test_extract_md(self, tmp_path):
        file_path = tmp_path / "test.md"
        file_path.write_text("# Header\n\nBody")
        text = extract_text(file_path)
        assert "# Header" in text
    
    def test_unsupported_extension_raises(self, tmp_path):
        file_path = tmp_path / "test.xyz"
        file_path.write_text("content")
        with pytest.raises(FileScanError) as exc:
            extract_text(file_path)
        assert exc.value.status == FileStatus.SKIPPED_UNSUPPORTED