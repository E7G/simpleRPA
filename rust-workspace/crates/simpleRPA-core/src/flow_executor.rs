use crate::flow::{FlowDiagram, FlowNode, NodeType};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

pub struct FlowExecutionContext {
    pub variables: HashMap<String, String>,
    pub script_results: HashMap<String, bool>,
    pub current_node_id: Option<String>,
    pub execution_path: Vec<String>,
    pub loop_counters: HashMap<String, i32>,
}

impl FlowExecutionContext {
    pub fn new() -> Self {
        Self {
            variables: HashMap::new(),
            script_results: HashMap::new(),
            current_node_id: None,
            execution_path: Vec::new(),
            loop_counters: HashMap::new(),
        }
    }

    pub fn set_variable(&mut self, name: &str, value: &str) {
        self.variables.insert(name.to_string(), value.to_string());
    }

    pub fn get_variable(&self, name: &str) -> Option<&str> {
        self.variables.get(name).map(|s| s.as_str())
    }

    pub fn set_script_result(&mut self, node_id: &str, result: bool) {
        self.script_results.insert(node_id.to_string(), result);
    }
}

pub struct FlowExecutor {
    flow: FlowDiagram,
    context: FlowExecutionContext,
    stop_flag: Arc<Mutex<bool>>,
    pause_flag: Arc<Mutex<bool>>,

    on_node_start: Option<Box<dyn Fn(&FlowNode) + Send>>,
    on_node_end: Option<Box<dyn Fn(&FlowNode, bool) + Send>>,
    on_flow_start: Option<Box<dyn Fn(&FlowDiagram) + Send>>,
    on_flow_end: Option<Box<dyn Fn(bool, &str) + Send>>,
    on_error: Option<Box<dyn Fn(Option<&FlowNode>, &str) + Send>>,
}

impl FlowExecutor {
    pub fn new(flow: FlowDiagram) -> Self {
        let mut context = FlowExecutionContext::new();
        for (name, var) in &flow.variables {
            context.set_variable(name, &var.value.to_string());
        }

        Self {
            flow,
            context,
            stop_flag: Arc::new(Mutex::new(false)),
            pause_flag: Arc::new(Mutex::new(false)),
            on_node_start: None,
            on_node_end: None,
            on_flow_start: None,
            on_flow_end: None,
            on_error: None,
        }
    }

    pub fn set_on_node_start<F: Fn(&FlowNode) + Send + 'static>(&mut self, f: F) {
        self.on_node_start = Some(Box::new(f));
    }

    pub fn set_on_node_end<F: Fn(&FlowNode, bool) + Send + 'static>(&mut self, f: F) {
        self.on_node_end = Some(Box::new(f));
    }

    pub fn set_on_flow_start<F: Fn(&FlowDiagram) + Send + 'static>(&mut self, f: F) {
        self.on_flow_start = Some(Box::new(f));
    }

    pub fn set_on_flow_end<F: Fn(bool, &str) + Send + 'static>(&mut self, f: F) {
        self.on_flow_end = Some(Box::new(f));
    }

    pub fn set_on_error<F: Fn(Option<&FlowNode>, &str) + Send + 'static>(&mut self, f: F) {
        self.on_error = Some(Box::new(f));
    }

    pub fn stop(&self) {
        *self.stop_flag.lock().unwrap() = true;
    }

    pub fn pause(&self) {
        *self.pause_flag.lock().unwrap() = true;
    }

    pub fn resume(&self) {
        *self.pause_flag.lock().unwrap() = false;
    }

    pub fn execute(&mut self) -> Result<(), String> {
        *self.stop_flag.lock().unwrap() = false;
        *self.pause_flag.lock().unwrap() = false;
        self.context = FlowExecutionContext::new();

        for (name, var) in &self.flow.variables {
            self.context.set_variable(name, &var.value.to_string());
        }

        if let Some(ref f) = self.on_flow_start {
            f(&self.flow);
        }

        if let Err(errors) = self.flow.validate() {
            let msg = format!("流程验证失败: {}", errors.join("; "));
            if let Some(ref f) = self.on_error {
                f(None, &msg);
            }
            return Err(msg);
        }

        let success = self.execute_from_node("start").unwrap_or(false);
        let message = if success {
            "执行完成".to_string()
        } else {
            "执行中断".to_string()
        };

        if let Some(ref f) = self.on_flow_end {
            f(success, &message);
        }

        if success {
            Ok(())
        } else {
            Err(message)
        }
    }

    fn execute_from_node(&mut self, node_id: &str) -> Result<bool, String> {
        if *self.stop_flag.lock().unwrap() {
            return Ok(false);
        }

        while *self.pause_flag.lock().unwrap() {
            std::thread::sleep(Duration::from_millis(50));
            if *self.stop_flag.lock().unwrap() {
                return Ok(false);
            }
        }

        let node = match self.flow.nodes.get(node_id) {
            Some(n) => n.clone(),
            None => return Ok(false),
        };

        self.context.current_node_id = Some(node_id.to_string());
        self.context.execution_path.push(node_id.to_string());

        if let Some(ref f) = self.on_node_start {
            f(&node);
        }

        let success = match node.node_type {
            NodeType::Start => true,
            NodeType::End => {
                if let Some(ref f) = self.on_node_end {
                    f(&node, true);
                }
                return Ok(true);
            }
            NodeType::Delay => {
                let duration = node
                    .properties
                    .get("duration")
                    .and_then(|v| v.as_f64())
                    .unwrap_or(1.0);
                let end = Instant::now() + Duration::from_secs_f64(duration);
                while Instant::now() < end {
                    if *self.stop_flag.lock().unwrap() {
                        return Ok(false);
                    }
                    std::thread::sleep(Duration::from_millis(50));
                }
                true
            }
            NodeType::Variable => {
                let var_name = node
                    .properties
                    .get("variable_name")
                    .and_then(|v| v.as_str())
                    .unwrap_or("");
                let operation = node
                    .properties
                    .get("operation")
                    .and_then(|v| v.as_str())
                    .unwrap_or("set");
                let value = node
                    .properties
                    .get("value")
                    .and_then(|v| v.as_str())
                    .unwrap_or("");

                match operation {
                    "set" => {
                        self.context.set_variable(var_name, value);
                    }
                    "increment" => {
                        let current = self
                            .context
                            .get_variable(var_name)
                            .and_then(|v| v.parse::<i32>().ok())
                            .unwrap_or(0);
                        self.context
                            .set_variable(var_name, &(current + 1).to_string());
                    }
                    "decrement" => {
                        let current = self
                            .context
                            .get_variable(var_name)
                            .and_then(|v| v.parse::<i32>().ok())
                            .unwrap_or(0);
                        self.context
                            .set_variable(var_name, &(current - 1).to_string());
                    }
                    _ => {}
                }
                true
            }
            NodeType::Condition => {
                let var_name = node
                    .properties
                    .get("variable_name")
                    .and_then(|v| v.as_str())
                    .unwrap_or("");
                let operator = node
                    .properties
                    .get("operator")
                    .and_then(|v| v.as_str())
                    .unwrap_or("==");
                let compare_value = node
                    .properties
                    .get("compare_value")
                    .and_then(|v| v.as_str())
                    .unwrap_or("");

                let var_value = self.context.get_variable(var_name).unwrap_or("");

                let result = match operator {
                    "==" => var_value == compare_value,
                    "!=" => var_value != compare_value,
                    ">" => {
                        var_value.parse::<f64>().unwrap_or(0.0)
                            > compare_value.parse::<f64>().unwrap_or(0.0)
                    }
                    "<" => {
                        var_value.parse::<f64>().unwrap_or(0.0)
                            < compare_value.parse::<f64>().unwrap_or(0.0)
                    }
                    ">=" => {
                        var_value.parse::<f64>().unwrap_or(0.0)
                            >= compare_value.parse::<f64>().unwrap_or(0.0)
                    }
                    "<=" => {
                        var_value.parse::<f64>().unwrap_or(0.0)
                            <= compare_value.parse::<f64>().unwrap_or(0.0)
                    }
                    "contains" => var_value.contains(compare_value),
                    "exists" => !var_value.is_empty(),
                    _ => false,
                };

                self.context
                    .set_variable("_condition_result", &result.to_string());
                true
            }
            NodeType::Loop => {
                let max_iterations = node
                    .properties
                    .get("max_iterations")
                    .and_then(|v| v.as_i64())
                    .unwrap_or(10) as i32;

                let loop_id = node.id.clone();
                self.context.loop_counters.insert(loop_id.clone(), 0);

                let next_nodes = self.flow.get_next_nodes(&node.id);
                let loop_body_start = next_nodes.first().cloned();

                for i in 0..max_iterations {
                    if *self.stop_flag.lock().unwrap() {
                        return Ok(false);
                    }

                    self.context.loop_counters.insert(loop_id.clone(), i + 1);
                    self.context.set_variable("_loop_index", &i.to_string());

                    if let Some(ref body_start) = loop_body_start {
                        if !self.execute_from_node(body_start)? {
                            return Ok(false);
                        }
                    }
                }
                true
            }
            NodeType::Script => {
                let script_path = node
                    .properties
                    .get("script_path")
                    .and_then(|v| v.as_str())
                    .unwrap_or("");
                let _ = script_path;
                true
            }
        };

        if let Some(ref f) = self.on_node_end {
            f(&node, success);
        }

        if !success {
            return Ok(false);
        }

        let next_nodes = self.flow.get_next_nodes(node_id);
        for next_id in next_nodes {
            if !self.execute_from_node(&next_id)? {
                return Ok(false);
            }
        }

        Ok(true)
    }

    pub fn get_context(&self) -> &FlowExecutionContext {
        &self.context
    }
}
