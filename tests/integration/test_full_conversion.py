"""Integration test for full EPUB conversion workflow."""

import os
import subprocess
import tempfile
import zipfile
import pytest


@pytest.mark.integration
def test_msk_guide_conversion_with_epubcheck():
    """
    Integration test that generates an EPUB from AWS MSK documentation
    and validates it using epubcheck.
    """
    # Create temporary directory for output
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "msk_developer_guide-test.epub")

        # Build the conversion command (run current dev code, not installed version)
        cmd = [
            "python3", "-m", "aws_docs_to_epub.cli",
            "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html",
            "-o", output_file,
            "-c",
            "https://cdn.prod.website-files.com/5f05d5858fab461d0d08eaeb/6351097781715e11162b7f19_msk_light.svg",
            "--max-pages", "10"
        ]

        # Run the conversion from the repository root
        repo_root = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            check=False,
            cwd=repo_root,
            env={**os.environ, "PYTHONPATH": os.path.join(repo_root, "src")}
        )

        # Check conversion succeeded
        assert result.returncode == 0, (
            f"Conversion failed with return code {result.returncode}\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )

        # Verify EPUB file was created
        assert os.path.exists(
            output_file), f"Output file not created: {output_file}"

        # Verify file is not empty
        file_size = os.path.getsize(output_file)
        assert file_size > 0, f"Output file is empty: {output_file}"

        # Check if epubcheck is available
        epubcheck_result = subprocess.run(
            ["which", "epubcheck"],
            capture_output=True,
            text=True,
            check=False
        )

        if epubcheck_result.returncode != 0:
            pytest.skip("epubcheck not installed - skipping validation")

        # Run epubcheck validation
        epubcheck_cmd = ["epubcheck", output_file]
        validation_result = subprocess.run(
            epubcheck_cmd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False
        )

        # Check for errors or warnings
        output = validation_result.stdout + validation_result.stderr

        # epubcheck returns 0 for no errors/warnings, 1 for warnings, 2+ for errors
        assert validation_result.returncode == 0, (
            f"epubcheck validation failed with return code {validation_result.returncode}\n"
            f"Output: {output}"
        )

        # Additional check for "No errors or warnings detected" message
        assert "No errors or warnings detected" in output or validation_result.returncode == 0, (
            f"EPUB validation did not pass cleanly:\n{output}"
        )

        print(f"✓ EPUB created successfully: {file_size} bytes")
        print("✓ EPUB validation passed with no errors or warnings")


@pytest.mark.integration
def test_msk_guide_conversion_basic():
    """
    Basic integration test that verifies EPUB generation works
    without requiring epubcheck.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "msk_test.epub")

        # Run current dev code, not installed version
        cmd = [
            "python3", "-m", "aws_docs_to_epub.cli",
            "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html",
            "-o", output_file,
            "-c",
            "https://cdn.prod.website-files.com/5f05d5858fab461d0d08eaeb/6351097781715e11162b7f19_msk_light.svg",
            "--max-pages", "10"
        ]

        repo_root = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
            cwd=repo_root,
            env={**os.environ, "PYTHONPATH": os.path.join(repo_root, "src")}
        )

        assert result.returncode == 0, (
            f"Conversion failed:\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )

        assert os.path.exists(output_file)
        assert os.path.getsize(output_file) > 1000  # At least 1KB

        # Verify it's a valid ZIP file (EPUB is a ZIP)

        assert zipfile.is_zipfile(
            output_file), "Generated file is not a valid ZIP/EPUB"

        # Verify basic EPUB structure
        with zipfile.ZipFile(output_file, 'r') as epub_zip:
            files = epub_zip.namelist()

            # Check for required EPUB files
            assert 'mimetype' in files, "Missing mimetype file"
            assert any(
                'META-INF' in f for f in files), "Missing META-INF directory"

            # Verify mimetype content
            mimetype = epub_zip.read('mimetype').decode('utf-8')
            assert mimetype == 'application/epub+zip', f"Invalid mimetype: {mimetype}"

        print("✓ EPUB structure validated successfully")
