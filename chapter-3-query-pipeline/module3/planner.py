from module3.schemas import QueryConfig

class RuleBasedPlanner:
    """
    Phân tích intent, lọc metadata (hiện hành/văn bản cũ), quyết định chạy Graph hay HyDE.
    """
    def plan(self, query: str) -> QueryConfig:
        config = QueryConfig()
        query_lower = query.lower()
        
        # Nếu nhắc đến điều khoản/mã văn bản cụ thể thì tắt HyDE để lấy chính xác
        if "điều" in query_lower or "khoản" in query_lower or "nghị định" in query_lower or "luật" in query_lower:
            config.use_hyde = False
        else:
            config.use_hyde = True
            
        # Nếu hỏi đa bước / so sánh thì bật Graph (nếu có)
        if "so sánh" in query_lower or "thay đổi" in query_lower:
            config.use_graph = True
            config.is_multi_hop = True
            
        # Nếu nhắc "hiện hành", "mới nhất" -> filter trạng thái
        if "hiện hành" in query_lower or "mới nhất" in query_lower:
            config.filters["trang_thai"] = "effective"
            
        # Nếu nói rõ "luật cũ" -> filter hết hiệu lực (giả lập)
        if "cũ" in query_lower or "hết hiệu lực" in query_lower:
            config.filters["trang_thai"] = "hết_hiệu_lực"
            
        # Default policy: Lọc bỏ hết hiệu lực nếu không nói gì
        if "trang_thai" not in config.filters:
            # We want to exclude "hết_hiệu_lực". In Qdrant, we might use a negative filter.
            # Here we just pass a simple flag or value to mock retriever.
            config.filters["exclude_trang_thai"] = "hết_hiệu_lực"
            
        return config
