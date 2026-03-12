from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import uuid
import json


class NodeType(Enum):
    SCRIPT = "script"
    CONDITION = "condition"
    LOOP = "loop"
    START = "start"
    END = "end"
    VARIABLE = "variable"
    DELAY = "delay"


class ConnectionType(Enum):
    FLOW = "flow"
    DATA = "data"


@dataclass
class Port:
    id: str
    name: str
    port_type: str
    data_type: str = "any"
    required: bool = False
    default_value: Any = None


@dataclass
class NodePosition:
    x: float
    y: float


@dataclass
class FlowNode:
    id: str
    node_type: NodeType
    name: str
    position: NodePosition
    input_ports: List[Port] = field(default_factory=list)
    output_ports: List[Port] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'node_type': self.node_type.value,
            'name': self.name,
            'position': {'x': self.position.x, 'y': self.position.y},
            'input_ports': [{'id': p.id, 'name': p.name, 'port_type': p.port_type, 
                            'data_type': p.data_type, 'required': p.required, 
                            'default_value': p.default_value} for p in self.input_ports],
            'output_ports': [{'id': p.id, 'name': p.name, 'port_type': p.port_type,
                             'data_type': p.data_type} for p in self.output_ports],
            'properties': self.properties
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'FlowNode':
        node = cls(
            id=data['id'],
            node_type=NodeType(data['node_type']),
            name=data['name'],
            position=NodePosition(data['position']['x'], data['position']['y']),
            properties=data.get('properties', {})
        )
        node.input_ports = [Port(**p) for p in data.get('input_ports', [])]
        node.output_ports = [Port(**p) for p in data.get('output_ports', [])]
        return node


@dataclass
class Connection:
    id: str
    source_node_id: str
    source_port_id: str
    target_node_id: str
    target_port_id: str
    connection_type: ConnectionType = ConnectionType.FLOW
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'source_node_id': self.source_node_id,
            'source_port_id': self.source_port_id,
            'target_node_id': self.target_node_id,
            'target_port_id': self.target_port_id,
            'connection_type': self.connection_type.value
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Connection':
        return cls(
            id=data['id'],
            source_node_id=data['source_node_id'],
            source_port_id=data['source_port_id'],
            target_node_id=data['target_node_id'],
            target_port_id=data['target_port_id'],
            connection_type=ConnectionType(data.get('connection_type', 'flow'))
        )


@dataclass
class FlowVariable:
    name: str
    value: Any
    var_type: str = "auto"
    description: str = ""


class FlowDiagram:
    def __init__(self, name: str = "新流程"):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.description: str = ""
        self.nodes: Dict[str, FlowNode] = {}
        self.connections: Dict[str, Connection] = {}
        self.variables: Dict[str, FlowVariable] = {}
        self.script_refs: Dict[str, str] = {}
        
        self._create_default_nodes()
    
    def _create_default_nodes(self):
        start_node = FlowNode(
            id="start",
            node_type=NodeType.START,
            name="开始",
            position=NodePosition(100, 300),
            output_ports=[Port(id="out", name="输出", port_type="flow")]
        )
        self.nodes["start"] = start_node
        
        end_node = FlowNode(
            id="end",
            node_type=NodeType.END,
            name="结束",
            position=NodePosition(800, 300),
            input_ports=[Port(id="in", name="输入", port_type="flow")]
        )
        self.nodes["end"] = end_node
    
    def add_node(self, node: FlowNode) -> str:
        if not node.id:
            node.id = str(uuid.uuid4())
        self.nodes[node.id] = node
        return node.id
    
    def remove_node(self, node_id: str):
        if node_id in ["start", "end"]:
            return False
        if node_id in self.nodes:
            del self.nodes[node_id]
            self.connections = {
                k: v for k, v in self.connections.items()
                if v.source_node_id != node_id and v.target_node_id != node_id
            }
            return True
        return False
    
    def add_connection(self, source_node_id: str, source_port_id: str,
                       target_node_id: str, target_port_id: str,
                       connection_type: ConnectionType = ConnectionType.FLOW) -> Optional[str]:
        if source_node_id not in self.nodes or target_node_id not in self.nodes:
            return None
        
        conn_id = str(uuid.uuid4())
        conn = Connection(
            id=conn_id,
            source_node_id=source_node_id,
            source_port_id=source_port_id,
            target_node_id=target_node_id,
            target_port_id=target_port_id,
            connection_type=connection_type
        )
        self.connections[conn_id] = conn
        return conn_id
    
    def remove_connection(self, conn_id: str) -> bool:
        if conn_id in self.connections:
            del self.connections[conn_id]
            return True
        return False
    
    def get_next_nodes(self, node_id: str) -> List[str]:
        next_nodes = []
        for conn in self.connections.values():
            if conn.source_node_id == node_id and conn.connection_type == ConnectionType.FLOW:
                next_nodes.append(conn.target_node_id)
        return next_nodes
    
    def get_prev_nodes(self, node_id: str) -> List[str]:
        prev_nodes = []
        for conn in self.connections.values():
            if conn.target_node_id == node_id and conn.connection_type == ConnectionType.FLOW:
                prev_nodes.append(conn.source_node_id)
        return prev_nodes
    
    def add_variable(self, name: str, value: Any = None, var_type: str = "auto", description: str = ""):
        self.variables[name] = FlowVariable(name, value, var_type, description)
    
    def remove_variable(self, name: str):
        if name in self.variables:
            del self.variables[name]
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'nodes': [n.to_dict() for n in self.nodes.values()],
            'connections': [c.to_dict() for c in self.connections.values()],
            'variables': {k: {'name': v.name, 'value': v.value, 
                             'var_type': v.var_type, 'description': v.description}
                         for k, v in self.variables.items()},
            'script_refs': self.script_refs
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'FlowDiagram':
        diagram = cls.__new__(cls)
        diagram.id = data.get('id', str(uuid.uuid4()))
        diagram.name = data.get('name', '未命名流程')
        diagram.description = data.get('description', '')
        diagram.nodes = {}
        diagram.connections = {}
        diagram.variables = {}
        diagram.script_refs = data.get('script_refs', {})
        
        for node_data in data.get('nodes', []):
            node = FlowNode.from_dict(node_data)
            diagram.nodes[node.id] = node
        
        for conn_data in data.get('connections', []):
            conn = Connection.from_dict(conn_data)
            diagram.connections[conn.id] = conn
        
        for var_name, var_data in data.get('variables', {}).items():
            diagram.variables[var_name] = FlowVariable(
                name=var_data['name'],
                value=var_data['value'],
                var_type=var_data.get('var_type', 'auto'),
                description=var_data.get('description', '')
            )
        
        return diagram
    
    def validate(self) -> Tuple[bool, List[str]]:
        errors = []
        
        if "start" not in self.nodes:
            errors.append("缺少开始节点")
        if "end" not in self.nodes:
            errors.append("缺少结束节点")
        
        for node_id, node in self.nodes.items():
            if node_id not in ["start"]:
                prev_nodes = self.get_prev_nodes(node_id)
                if not prev_nodes:
                    errors.append(f"节点 '{node.name}' 没有输入连接")
            
            if node_id not in ["end"]:
                next_nodes = self.get_next_nodes(node_id)
                if not next_nodes:
                    errors.append(f"节点 '{node.name}' 没有输出连接")
        
        for node_id, node in self.nodes.items():
            if node.node_type == NodeType.SCRIPT:
                script_path = node.properties.get('script_path', '')
                if not script_path:
                    errors.append(f"脚本节点 '{node.name}' 未指定脚本文件")
        
        return len(errors) == 0, errors
