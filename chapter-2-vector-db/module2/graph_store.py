from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class GraphRepository(ABC):
    @abstractmethod
    def add_node(self, node_id: str, label: str, properties: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def add_edge(self, source_id: str, target_id: str, relationship: str, properties: Optional[Dict[str, Any]] = None) -> None:
        pass

    @abstractmethod
    def get_related_nodes(self, node_id: str, relationship: Optional[str] = None) -> List[Dict[str, Any]]:
        pass

class MemoryGraphRepository(GraphRepository):
    """
    Simulation Layer cho Neo4j.
    Sử dụng dictionary tĩnh trong bộ nhớ để mô phỏng Knowledge Graph.
    Sau này sẽ thay bằng Neo4jRepository.
    """
    def __init__(self):
        self.nodes = {}
        self.edges = []

    def add_node(self, node_id: str, label: str, properties: Dict[str, Any]) -> None:
        self.nodes[node_id] = {"label": label, "properties": properties}
        
    def add_edge(self, source_id: str, target_id: str, relationship: str, properties: Optional[Dict[str, Any]] = None) -> None:
        self.edges.append({
            "source": source_id,
            "target": target_id,
            "relationship": relationship,
            "properties": properties or {}
        })

    def get_related_nodes(self, node_id: str, relationship: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        for edge in self.edges:
            if edge["source"] == node_id and (relationship is None or edge["relationship"] == relationship):
                target_id = edge["target"]
                if target_id in self.nodes:
                    results.append(self.nodes[target_id])
        return results

    def debug_print(self):
        print(f"[GraphStore] Hiện có {len(self.nodes)} nodes và {len(self.edges)} edges.")

class Neo4jRepository(GraphRepository):
    """
    Stub implementation of Neo4jRepository for Architecture Verification.
    Demonstrates Liskov Substitution Principle and Dependency Inversion.
    Uses in-memory store similar to MemoryGraphRepository for testing without a real database.
    """
    def __init__(self, uri: str = "bolt://localhost:7687", user: str = "neo4j", password: str = "password"):
        self.uri = uri
        self.user = user
        self.password = password
        # Internal state for stubbing
        self._nodes = {}
        self._edges = []

    def add_node(self, node_id: str, label: str, properties: Dict[str, Any]) -> None:
        self._nodes[node_id] = {"label": label, "properties": properties}
        
    def add_edge(self, source_id: str, target_id: str, relationship: str, properties: Optional[Dict[str, Any]] = None) -> None:
        self._edges.append({
            "source": source_id,
            "target": target_id,
            "relationship": relationship,
            "properties": properties or {}
        })

    def get_related_nodes(self, node_id: str, relationship: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        for edge in self._edges:
            if edge["source"] == node_id and (relationship is None or edge["relationship"] == relationship):
                target_id = edge["target"]
                if target_id in self._nodes:
                    results.append(self._nodes[target_id])
        return results

    def debug_print(self):
        print(f"[Neo4jStub] Connected to {self.uri}. Currently mocking {len(self._nodes)} nodes and {len(self._edges)} edges.")
