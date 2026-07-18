import pytest
from module3.query_understanding import QueryNormalizer, RuleBasedQueryRewriter

def test_query_normalizer():
    normalizer = QueryNormalizer()
    query = "  Làm  thế NÀO để...   đăng ký?  "
    normalized = normalizer.normalize(query)
    assert normalized == "Làm thế NÀO để... đăng ký?"

def test_rule_based_query_rewriter():
    rewriter = RuleBasedQueryRewriter()
    
    # Test stop words removal
    query1 = "cho tôi hỏi luật pccc áp dụng cho ktx sinh viên"
    rewritten1 = rewriter.rewrite(query1)
    assert "cho tôi hỏi" not in rewritten1
    assert "luật pccc áp dụng cho ktx sinh viên" in rewritten1
