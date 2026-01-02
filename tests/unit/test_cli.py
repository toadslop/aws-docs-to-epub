"""Sample unit test for CLI."""

import pytest
from aws_docs_to_epub.cli import main


def test_cli_no_args():
    """Test CLI with no arguments shows help."""
    with pytest.raises(SystemExit):
        main()
