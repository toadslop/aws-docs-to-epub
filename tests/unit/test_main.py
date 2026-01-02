"""Additional tests for __main__ and commands modules."""

import sys
import subprocess


def test_main_module_execution() -> None:
    """Test __main__ module can be executed."""
    # Test that the module can be run with python -m
    result = subprocess.run(
        [sys.executable, '-m', 'aws_docs_to_epub', '--version'],
        cwd='/home/brian-heise/code/convert2',
        capture_output=True,
        text=True,
        check=False
    )
    # Should exit with 0 for --version
    assert result.returncode == 0


def test_main_module_as_script() -> None:
    """Test __main__ module when run as script."""
    result = subprocess.run(
        [sys.executable, 'src/aws_docs_to_epub/__main__.py'],
        cwd='/home/brian-heise/code/convert2',
        capture_output=True,
        text=True,
        check=False
    )
    # Should exit (with error since no args provided)
    assert result.returncode != 0
