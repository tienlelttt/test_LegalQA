from typing import List
from module3.schemas import QueryConfig

class LLMQueryExpander:
    """
    Sinh câu hỏi phụ (Multi-query) hoặc văn bản giả định (HyDE) trước khi gọi DB.
    """
    def expand(self, query: str, config: QueryConfig) -> List[str]:
        expanded_queries = [query]
        
        if config.use_hyde:
            # Mô phỏng gọi LLM để sinh HyDE document
            hyde_doc = query + " giả định: Theo quy định của pháp luật, vấn đề này được xử lý như sau..."
            expanded_queries.append(hyde_doc)
            
        if config.is_multi_hop:
            # Mô phỏng Multi-query
            expanded_queries.append("Khía cạnh 1 của " + query)
            expanded_queries.append("Khía cạnh 2 của " + query)
            
        return expanded_queries
