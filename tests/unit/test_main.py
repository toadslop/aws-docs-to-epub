"""Additional tests for __main__ and commands modules."""

import sys
import subprocess
import os


def test_main_module_execution() -> None:
    """Test __main__ module can be executed."""
    # Get repository root (3 levels up from this test file)
    repo_root = os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))

    # Test that the module can be run with python -m
    result = subprocess.run(
        [sys.executable, '-m', 'aws_docs_to_epub', '--version'],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False
    )
    # Should exit with 0 for --version
    assert result.returncode == 0


def test_main_module_as_script() -> None:
    """Test __main__ module when run as script."""
    # Get repository root (3 levels up from this test file)
    repo_root = os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))

    result = subprocess.run(
        [sys.executable, 'src/aws_docs_to_epub/__main__.py'],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False
    )
    # Should exit (with error since no args provided)
    assert result.returncode != 0
