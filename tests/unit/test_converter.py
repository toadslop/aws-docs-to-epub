"""Sample unit test for converter."""

import pytest
from aws_docs_to_epub import AWSDocsToEpub


def test_converter_init_valid_url():
    """Test converter initializes with valid URL."""
    url = "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html"
    converter = AWSDocsToEpub(url)

    assert converter.config.service_name == "msk"
    assert converter.config.version == "latest"
    assert converter.config.guide_type == "developerguide"


def test_converter_init_invalid_url():
    """Test converter raises error with invalid URL."""
    url = "https://docs.aws.amazon.com/invalid"

    with pytest.raises(ValueError):
        AWSDocsToEpub(url)
