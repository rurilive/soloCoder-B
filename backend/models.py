from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid


@dataclass
class Position:
    x: float = 0.0
    y: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y}

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "Position":
        return cls(x=data.get("x", 0.0), y=data.get("y", 0.0))


@dataclass
class NodeConfig:
    code: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "params": self.params,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NodeConfig":
        return cls(
            code=data.get("code", ""),
            inputs=data.get("inputs", {}),
            outputs=data.get("outputs", {}),
            params=data.get("params", {}),
        )


@dataclass
class Node:
    id: str
    type: str
    position: Position
    config: NodeConfig
    label: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "position": self.position.to_dict(),
            "config": self.config.to_dict(),
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Node":
        return cls(
            id=data["id"],
            type=data["type"],
            position=Position.from_dict(data.get("position", {})),
            config=NodeConfig.from_dict(data.get("config", {})),
            label=data.get("label"),
        )

    @classmethod
    def create(
        cls,
        node_type: str,
        position: Position,
        config: Optional[NodeConfig] = None,
        node_id: Optional[str] = None,
        label: Optional[str] = None,
    ) -> "Node":
        return cls(
            id=node_id or str(uuid.uuid4()),
            type=node_type,
            position=position,
            config=config or NodeConfig(),
            label=label,
        )


@dataclass
class Edge:
    id: str
    source: str
    target: str
    source_handle: Optional[str] = None
    target_handle: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "source_handle": self.source_handle,
            "target_handle": self.target_handle,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Edge":
        return cls(
            id=data["id"],
            source=data["source"],
            target=data["target"],
            source_handle=data.get("source_handle"),
            target_handle=data.get("target_handle"),
        )

    @classmethod
    def create(
        cls,
        source: str,
        target: str,
        source_handle: Optional[str] = None,
        target_handle: Optional[str] = None,
        edge_id: Optional[str] = None,
    ) -> "Edge":
        return cls(
            id=edge_id or str(uuid.uuid4()),
            source=source,
            target=target,
            source_handle=source_handle,
            target_handle=target_handle,
        )


@dataclass
class Workflow:
    id: str
    name: str
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Workflow":
        nodes = [Node.from_dict(n) for n in data.get("nodes", [])]
        edges = [Edge.from_dict(e) for e in data.get("edges", [])]
        return cls(
            id=data["id"],
            name=data.get("name", "Untitled Workflow"),
            nodes=nodes,
            edges=edges,
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )

    @classmethod
    def create(
        cls,
        name: str,
        workflow_id: Optional[str] = None,
    ) -> "Workflow":
        return cls(
            id=workflow_id or str(uuid.uuid4()),
            name=name,
            nodes=[],
            edges=[],
        )

    def update_timestamp(self):
        self.updated_at = datetime.now().isoformat()
