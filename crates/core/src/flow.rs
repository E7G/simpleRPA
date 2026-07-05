use std::collections::HashMap;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum NodeType {
    Script,
    Condition,
    Loop,
    Start,
    End,
    Variable,
    Delay,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ConnectionType {
    Flow,
    Data,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Port {
    #[serde(default)]
    pub id: String,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub port_type: String,
    #[serde(default = "default_any")]
    pub data_type: String,
    #[serde(default)]
    pub required: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub default_value: Option<serde_json::Value>,
}

fn default_any() -> String { "any".into() }

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

fn default_flow() -> ConnectionType { ConnectionType::Flow }

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FlowVariable {
    pub name: String,
    pub value: serde_json::Value,
    #[serde(default = "default_auto")]
    pub var_type: String,
    #[serde(default)]
    pub description: String,
}

fn default_auto() -> String { "auto".into() }

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
        let mut diagram = Self {
            id: uuid::Uuid::new_v4().to_string(),
            name: name.to_string(),
            description: String::new(),
            nodes: HashMap::new(),
            connections: HashMap::new(),
            variables: HashMap::new(),
            script_refs: HashMap::new(),
        };
        diagram.create_default_nodes();
        diagram
    }

    fn create_default_nodes(&mut self) {
        self.nodes.insert(
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
                    ..Default::default()
                }],
                ..Default::default()
            },
        );
        self.nodes.insert(
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
                    ..Default::default()
                }],
                ..Default::default()
            },
        );
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
            self.connections.retain(|_, c| {
                c.source_node_id != node_id && c.target_node_id != node_id
            });
            return true;
        }
        false
    }

    pub fn add_connection(
        &mut self,
        source_node_id: &str,
        source_port_id: &str,
        target_node_id: &str,
        target_port_id: &str,
        connection_type: ConnectionType,
    ) -> Option<String> {
        if !self.nodes.contains_key(source_node_id) || !self.nodes.contains_key(target_node_id) {
            return None;
        }
        let id = uuid::Uuid::new_v4().to_string();
        let conn = Connection {
            id: id.clone(),
            source_node_id: source_node_id.to_string(),
            source_port_id: source_port_id.to_string(),
            target_node_id: target_node_id.to_string(),
            target_port_id: target_port_id.to_string(),
            connection_type,
        };
        self.connections.insert(id.clone(), conn);
        Some(id)
    }

    pub fn get_next_nodes(&self, node_id: &str) -> Vec<String> {
        self.connections
            .values()
            .filter(|c| c.source_node_id == node_id && c.connection_type == ConnectionType::Flow)
            .map(|c| c.target_node_id.clone())
            .collect()
    }

    pub fn get_prev_nodes(&self, node_id: &str) -> Vec<String> {
        self.connections
            .values()
            .filter(|c| c.target_node_id == node_id && c.connection_type == ConnectionType::Flow)
            .map(|c| c.source_node_id.clone())
            .collect()
    }

    pub fn to_dict(&self) -> serde_json::Value {
        serde_json::to_value(self).unwrap_or(serde_json::Value::Null)
    }

    pub fn from_dict(data: &serde_json::Value) -> Result<Self, String> {
        serde_json::from_value(data.clone()).map_err(|e| format!("解析流程失败: {}", e))
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
            if node_id != "start" && self.get_prev_nodes(node_id).is_empty() {
                errors.push(format!("节点 '{}' 没有输入连接", node.name));
            }
            if node_id != "end" && self.get_next_nodes(node_id).is_empty() {
                errors.push(format!("节点 '{}' 没有输出连接", node.name));
            }
        }

        if errors.is_empty() {
            Ok(())
        } else {
            Err(errors)
        }
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
