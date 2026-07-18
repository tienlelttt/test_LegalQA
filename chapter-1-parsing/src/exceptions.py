class LegalParsingError(Exception):
    """Lỗi xảy ra trong quá trình Parse cấu trúc văn bản."""
    pass

class LegalChunkingError(Exception):
    """Lỗi xảy ra trong quá trình Chunking."""
    pass

class MetadataExtractionError(Exception):
    """Lỗi xảy ra trong quá trình trích xuất metadata."""
    pass
