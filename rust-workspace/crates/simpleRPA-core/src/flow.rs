use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum NodeType {
    Script,
    Condition,
    Loop,
    Start,
    End,
    Variable,
    Delay,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ConnectionType {
    Flow,
    Data,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Port {
    pub id: String,
    pub name: String,
    pub port_type: String,
    #[serde(default)]
    pub data_type: String,
    #[serde(default)]
    pub required: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodePosition {
    pub x: f64,
    pub y: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FlowNode {
    pub id: String,
    pub node_type: NodeType,
    pub name: String,
    pub position: NodePosition,
    #[serde(default)]
    pub input_ports: Vec<Port>,
    #[serde(default)]
    pub output_ports: Vec<Port>,
    #[serde(default)]
    pub properties: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Connection {
    pub id: String,
    pub source_node_id: String,
    pub source_port_id: String,
    pub target_node_id: String,
    pub target_port_id: String,
    #[serde(default = "default_flow")]
    pub connection_type: ConnectionType,
}

fn default_flow() -> ConnectionType {
    ConnectionType::Flow
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FlowVariable {
    pub name: String,
    pub value: serde_json::Value,
    #[serde(default)]
    pub var_type: String,
    #[serde(default)]
    pub description: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FlowDiagram {
    pub id: String,
    pub name: String,
    #[serde(default)]
    pub description: String,
    pub nodes: HashMap<String, FlowNode>,
    pub connections: HashMap<String, Connection>,
    #[serde(default)]
    pub variables: HashMap<String, FlowVariable>,
    #[serde(default)]
    pub script_refs: HashMap<String, String>,
}

impl FlowDiagram {
    pub fn new(name: &str) -> Self {
        let id = uuid::Uuid::new_v4().to_string();
        let mut diagram = Self {
            id: id.clone(),
            name: name.to_string(),
            description: String::new(),
            nodes: HashMap::new(),
            connections: HashMap::new(),
            variables: HashMap::new(),
            script_refs: HashMap::new(),
        };

        diagram.nodes.insert(
            "start".into(),
            FlowNode {
                id: "start".into(),
                node_type: NodeType::Start,
                name: "开始".into(),
                position: NodePosition { x: 100.0, y: 300.0 },
                output_ports: vec![Port {
                    id: "out".into(),
                    name: "输出".into(),
                    port_type: "flow".into(),
                    data_type: "any".into(),
                    required: false,
                }],
                ..Default::default()
            },
        );

        diagram.nodes.insert(
            "end".into(),
            FlowNode {
                id: "end".into(),
                node_type: NodeType::End,
                name: "结束".into(),
                position: NodePosition { x: 800.0, y: 300.0 },
                input_ports: vec![Port {
                    id: "in".into(),
                    name: "输入".into(),
                    port_type: "flow".into(),
                    data_type: "any".into(),
                    required: false,
                }],
                ..Default::default()
            },
        );

        diagram
    }

    pub fn add_node(&mut self, mut node: FlowNode) -> String {
        if node.id.is_empty() {
            node.id = uuid::Uuid::new_v4().to_string();
        }
        let id = node.id.clone();
        self.nodes.insert(id.clone(), node);
        id
    }

    pub fn remove_node(&mut self, node_id: &str) -> bool {
        if node_id == "start" || node_id == "end" {
            return false;
        }
        if self.nodes.remove(node_id).is_some() {
            self.connections
                .retain(|_, c| c.source_node_id != node_id && c.target_node_id != node_id);
            true
        } else {
            false
        }
    }

    pub fn add_connection(
        &mut self,
        source_node_id: &str,
        source_port_id: &str,
        target_node_id: &str,
        target_port_id: &str,
    ) -> Option<String> {
        if !self.nodes.contains_key(source_node_id) || !self.nodes.contains_key(target_node_id) {
            return None;
        }

        let conn_id = uuid::Uuid::new_v4().to_string();
        let conn = Connection {
            id: conn_id.clone(),
            source_node_id: source_node_id.into(),
            source_port_id: source_port_id.into(),
            target_node_id: target_node_id.into(),
            target_port_id: target_port_id.into(),
            connection_type: ConnectionType::Flow,
        };
        self.connections.insert(conn_id.clone(), conn);
        Some(conn_id)
    }

    pub fn get_next_nodes(&self, node_id: &str) -> Vec<String> {
        self.connections
            .values()
            .filter(|c| {
                c.source_node_id == node_id && matches!(c.connection_type, ConnectionType::Flow)
            })
            .map(|c| c.target_node_id.clone())
            .collect()
    }

    pub fn add_variable(
        &mut self,
        name: &str,
        value: serde_json::Value,
        var_type: &str,
        description: &str,
    ) {
        self.variables.insert(
            name.into(),
            FlowVariable {
                name: name.into(),
                value,
                var_type: var_type.into(),
                description: description.into(),
            },
        );
    }

    pub fn to_dict(&self) -> serde_json::Value {
        serde_json::json!({
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "nodes": self.nodes.values().map(|n| n.clone()).collect::<Vec<_>>(),
            "connections": self.connections.values().map(|c| c.clone()).collect::<Vec<_>>(),
            "variables": self.variables,
            "script_refs": self.script_refs,
        })
    }

    pub fn from_dict(data: &serde_json::Value) -> Option<Self> {
        let id = data.get("id")?.as_str()?.to_string();
        let name = data
            .get("name")
            .and_then(|v| v.as_str())
            .unwrap_or("未命名流程")
            .to_string();
        let description = data
            .get("description")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();

        let nodes: HashMap<String, FlowNode> = data
            .get("nodes")
            .and_then(|v| v.as_array())
            .map(|arr| {
                arr.iter()
                    .filter_map(|n| {
                        let node: FlowNode = serde_json::from_value(n.clone()).ok()?;
                        Some((node.id.clone(), node))
                    })
                    .collect()
            })
            .unwrap_or_default();

        let connections: HashMap<String, Connection> = data
            .get("connections")
            .and_then(|v| v.as_array())
            .map(|arr| {
                arr.iter()
                    .filter_map(|c| {
                        let conn: Connection = serde_json::from_value(c.clone()).ok()?;
                        Some((conn.id.clone(), conn))
                    })
                    .collect()
            })
            .unwrap_or_default();

        let variables: HashMap<String, FlowVariable> = data
            .get("variables")
            .and_then(|v| serde_json::from_value(v.clone()).ok())
            .unwrap_or_default();

        let script_refs: HashMap<String, String> = data
            .get("script_refs")
            .and_then(|v| serde_json::from_value(v.clone()).ok())
            .unwrap_or_default();

        Some(Self {
            id,
            name,
            description,
            nodes,
            connections,
            variables,
            script_refs,
        })
    }

    pub fn validate(&self) -> Result<(), Vec<String>> {
        let mut errors = Vec::new();

        if !self.nodes.contains_key("start") {
            errors.push("缺少开始节点".into());
        }
        if !self.nodes.contains_key("end") {
            errors.push("缺少结束节点".into());
        }

        for (node_id, node) in &self.nodes {
            if node_id != "start" {
                let prev = self.get_prev_nodes(node_id);
                if prev.is_empty() {
                    errors.push(format!("节点 '{}' 没有输入连接", node.name));
                }
            }
            if node_id != "end" {
                let next = self.get_next_nodes(node_id);
                if next.is_empty() {
                    errors.push(format!("节点 '{}' 没有输出连接", node.name));
                }
            }
        }

        if errors.is_empty() {
            Ok(())
        } else {
            Err(errors)
        }
    }

    fn get_prev_nodes(&self, node_id: &str) -> Vec<String> {
        self.connections
            .values()
            .filter(|c| {
                c.target_node_id == node_id && matches!(c.connection_type, ConnectionType::Flow)
            })
            .map(|c| c.source_node_id.clone())
            .collect()
    }
}

impl Default for FlowNode {
    fn default() -> Self {
        Self {
            id: String::new(),
            node_type: NodeType::Script,
            name: String::new(),
            position: NodePosition { x: 0.0, y: 0.0 },
            input_ports: Vec::new(),
            output_ports: Vec::new(),
            properties: HashMap::new(),
        }
    }
}
