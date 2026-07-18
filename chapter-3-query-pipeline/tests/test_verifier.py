import pytest
from shared.models.schemas import Chunk, Metadata
from module3.schemas import AnswerResult, QueryContext
from module3.verifier import CitationVerifier, MockGroundednessVerifier, HallucinationDetectionVerifier, ConfidenceScoringVerifier, RuleBasedScoringStrategy, VerificationPipeline

def test_citation_verifier_missing():
    verifier = CitationVerifier()
    
    # Missing citation
    result = AnswerResult(answer="Đây là câu trả lời.", query="Hỏi gì?")
    context = QueryContext(chunks=[])
    
    verified_result = verifier.verify(result, context)
    assert len(verified_result.warnings) > 0
    assert "Missing citation" in verified_result.warnings[0]

def test_citation_verifier_mismatch():
    verifier = CitationVerifier()
    
    # Mismatch citation (Cite Điều 2 nhưng context chỉ có Điều 1)
    result = AnswerResult(answer="Đây là câu trả lời. [Điều 2 — Luật XYZ, 123]", query="Hỏi gì?")
    
    meta = {"document_id": "doc1", "dieu_so": "1", "ten_van_ban": "Luật XYZ", "so_hieu": "123", "trang_thai": "effective"}
    context = QueryContext(chunks=[Chunk(chunk_id="1", content="Nội dung", metadata=meta, parent_id="", chunk_type="DIEU")])
    
    verified_result = verifier.verify(result, context)
    assert any("mismatch" in w.lower() for w in verified_result.warnings)
    
def test_mock_groundedness_verifier():
    verifier = MockGroundednessVerifier()
    
    # Hallucination test
    result = AnswerResult(answer="Đây là ảo giác.", query="Hỏi gì?")
    context = QueryContext(chunks=[])
    
    verified = verifier.verify(result, context)
    assert not verified.is_grounded

def test_hallucination_and_confidence():
    # Setup pipeline with the 4 steps
    verifiers = [
        MockGroundednessVerifier(),
        CitationVerifier(),
        HallucinationDetectionVerifier(),
        ConfidenceScoringVerifier(RuleBasedScoringStrategy())
    ]
    pipeline = VerificationPipeline(verifiers)
    
    # Bad answer
    result = AnswerResult(answer="Đây là ảo giác và bịa đặt. [Điều 99 — Luật Không Có Thật, 999]", query="Hỏi gì?")
    meta = {"document_id": "doc1", "dieu_so": "1", "ten_van_ban": "Luật XYZ", "so_hieu": "123", "trang_thai": "effective"}
    context = QueryContext(chunks=[Chunk(chunk_id="1", content="Nội dung", metadata=meta, parent_id="", chunk_type="DIEU")])
    
    final_result = pipeline.run(result, context)
    
    assert final_result.hallucination_risk == "high"
    assert final_result.confidence_score == 0.1
    assert "không tìm đủ căn cứ rõ ràng" in final_result.answer.lower()
