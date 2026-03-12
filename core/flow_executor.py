import json
import os
import time
from typing import Dict, List, Optional, Any, Callable, Tuple
from .flow_diagram import FlowDiagram, FlowNode, NodeType, ConnectionType, Connection
from .actions import Action
from .player import Player, PlayerState
from .exporter import Exporter
from utils.config import Config


class FlowExecutionContext:
    def __init__(self):
        self.variables: Dict[str, Any] = {}
        self.script_results: Dict[str, Any] = {}
        self.current_node_id: Optional[str] = None
        self.execution_path: List[str] = []
        self.loop_counters: Dict[str, int] = {}
    
    def set_variable(self, name: str, value: Any):
        self.variables[name] = value
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        return self.variables.get(name, default)
    
    def set_script_result(self, node_id: str, result: Any):
        self.script_results[node_id] = result
    
    def get_script_result(self, node_id: str) -> Any:
        return self.script_results.get(node_id)


class FlowExecutor:
    def __init__(self, flow: FlowDiagram):
        self._flow = flow
        self._context = FlowExecutionContext()
        self._player: Optional[Player] = None
        self._stop_flag = False
        self._pause_flag = False
        
        self._callbacks: Dict[str, List[Callable]] = {
            'on_node_start': [],
            'on_node_end': [],
            'on_flow_start': [],
            'on_flow_end': [],
            'on_error': [],
            'on_variable_change': [],
        }
        
        for var_name, var in flow.variables.items():
            self._context.set_variable(var_name, var.value)
    
    def add_callback(self, event: str, callback: Callable):
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def _emit(self, event: str, *args, **kwargs):
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                print(f"[FlowExecutor] Callback error: {e}")
    
    def set_player(self, player: Player):
        self._player = player
    
    def stop(self):
        self._stop_flag = True
        if self._player:
            self._player.stop()
    
    def pause(self):
        self._pause_flag = True
        if self._player:
            self._player.toggle_pause()
    
    def resume(self):
        self._pause_flag = False
        if self._player:
            self._player.toggle_pause()
    
    def execute(self) -> Tuple[bool, str]:
        self._stop_flag = False
        self._pause_flag = False
        self._context = FlowExecutionContext()
        
        for var_name, var in self._flow.variables.items():
            self._context.set_variable(var_name, var.value)
        
        self._emit('on_flow_start', self._flow)
        
        valid, errors = self._flow.validate()
        if not valid:
            self._emit('on_error', None, "流程验证失败: " + "; ".join(errors))
            return False, "流程验证失败"
        
        try:
            success = self._execute_from_node("start")
            message = "执行完成" if success else "执行中断"
            self._emit('on_flow_end', success, message)
            return success, message
        except Exception as e:
            self._emit('on_error', None, str(e))
            return False, str(e)
    
    def _execute_from_node(self, node_id: str) -> bool:
        if self._stop_flag:
            return False
        
        while self._pause_flag:
            time.sleep(0.1)
            if self._stop_flag:
                return False
        
        node = self._flow.nodes.get(node_id)
        if not node:
            return False
        
        self._context.current_node_id = node_id
        self._context.execution_path.append(node_id)
        self._emit('on_node_start', node)
        
        success = True
        try:
            if node.node_type == NodeType.START:
                pass
            elif node.node_type == NodeType.END:
                self._emit('on_node_end', node, True)
                return True
            elif node.node_type == NodeType.SCRIPT:
                success = self._execute_script_node(node)
            elif node.node_type == NodeType.CONDITION:
                success = self._execute_condition_node(node)
            elif node.node_type == NodeType.LOOP:
                success = self._execute_loop_node(node)
            elif node.node_type == NodeType.VARIABLE:
                success = self._execute_variable_node(node)
            elif node.node_type == NodeType.DELAY:
                success = self._execute_delay_node(node)
        except Exception as e:
            self._emit('on_error', node, str(e))
            success = False
        
        self._emit('on_node_end', node, success)
        
        if not success:
            return False
        
        next_nodes = self._flow.get_next_nodes(node_id)
        for next_node_id in next_nodes:
            if not self._execute_from_node(next_node_id):
                return False
        
        return True
    
    def _execute_script_node(self, node: FlowNode) -> bool:
        script_path = node.properties.get('script_path', '')
        if not script_path:
            return False
        
        params = node.properties.get('params', {})
        for key, value in params.items():
            if isinstance(value, str) and value.startswith('$'):
                var_name = value[1:]
                params[key] = self._context.get_variable(var_name)
        
        local_group_manager = None
        try:
            from .action_group import LocalActionGroupManager
            local_group_manager = LocalActionGroupManager()
        except:
            pass
        
        result = Exporter.import_from_json(script_path, local_group_manager)
        if result is None:
            return False
        
        actions = result if isinstance(result, list) else result.get('actions', [])
        if not actions:
            return True
        
        for action in actions:
            for key, value in params.items():
                if hasattr(action, 'params') and key in action.params:
                    action.params[key] = value
        
        if self._player is None:
            self._player = Player(tab_key="flow")
        
        self._player.set_actions(actions)
        if local_group_manager:
            self._player.set_local_group_manager(local_group_manager)
        
        self._player.play()
        
        while self._player._state not in [PlayerState.IDLE]:
            if self._stop_flag:
                self._player.stop()
                return False
            time.sleep(0.1)
        
        output_var = node.properties.get('output_variable', '')
        if output_var:
            self._context.set_variable(output_var, True)
            self._emit('on_variable_change', output_var, True)
        
        return True
    
    def _execute_condition_node(self, node: FlowNode) -> bool:
        condition_type = node.properties.get('condition_type', 'variable')
        
        if condition_type == 'variable':
            var_name = node.properties.get('variable_name', '')
            operator = node.properties.get('operator', '==')
            compare_value = node.properties.get('compare_value', '')
            
            var_value = self._context.get_variable(var_name)
            
            if operator == '==':
                result = str(var_value) == str(compare_value)
            elif operator == '!=':
                result = str(var_value) != str(compare_value)
            elif operator == '>':
                try:
                    result = float(var_value) > float(compare_value)
                except:
                    result = False
            elif operator == '<':
                try:
                    result = float(var_value) < float(compare_value)
                except:
                    result = False
            elif operator == '>=':
                try:
                    result = float(var_value) >= float(compare_value)
                except:
                    result = False
            elif operator == '<=':
                try:
                    result = float(var_value) <= float(compare_value)
                except:
                    result = False
            elif operator == 'contains':
                result = str(compare_value) in str(var_value)
            elif operator == 'exists':
                result = var_value is not None
            else:
                result = False
            
            self._context.set_variable('_condition_result', result)
            
        elif condition_type == 'script_result':
            script_node_id = node.properties.get('script_node_id', '')
            result = self._context.get_script_result(script_node_id)
            self._context.set_variable('_condition_result', result is not None and result)
        
        else:
            self._context.set_variable('_condition_result', False)
        
        return True
    
    def _execute_loop_node(self, node: FlowNode) -> bool:
        loop_type = node.properties.get('loop_type', 'count')
        max_iterations = node.properties.get('max_iterations', 10)
        
        loop_id = node.id
        self._context.loop_counters[loop_id] = 0
        
        if loop_type == 'count':
            iterations = 0
            while iterations < max_iterations and not self._stop_flag:
                self._context.loop_counters[loop_id] = iterations + 1
                self._context.set_variable('_loop_index', iterations)
                
                loop_body_start = self._find_loop_body_start(node.id)
                if loop_body_start:
                    if not self._execute_from_node(loop_body_start):
                        return False
                
                iterations += 1
        
        elif loop_type == 'condition':
            while not self._stop_flag:
                condition_var = node.properties.get('condition_variable', '')
                condition_value = node.properties.get('condition_value', True)
                
                current_value = self._context.get_variable(condition_var)
                if current_value != condition_value:
                    break
                
                self._context.loop_counters[loop_id] = self._context.loop_counters.get(loop_id, 0) + 1
                
                loop_body_start = self._find_loop_body_start(node.id)
                if loop_body_start:
                    if not self._execute_from_node(loop_body_start):
                        return False
        
        return True
    
    def _find_loop_body_start(self, loop_node_id: str) -> Optional[str]:
        next_nodes = self._flow.get_next_nodes(loop_node_id)
        return next_nodes[0] if next_nodes else None
    
    def _execute_variable_node(self, node: FlowNode) -> bool:
        var_name = node.properties.get('variable_name', '')
        operation = node.properties.get('operation', 'set')
        value = node.properties.get('value', '')
        
        if operation == 'set':
            if isinstance(value, str) and value.startswith('$'):
                source_var = value[1:]
                value = self._context.get_variable(source_var)
            self._context.set_variable(var_name, value)
        
        elif operation == 'increment':
            current = self._context.get_variable(var_name, 0)
            try:
                self._context.set_variable(var_name, current + 1)
            except:
                pass
        
        elif operation == 'decrement':
            current = self._context.get_variable(var_name, 0)
            try:
                self._context.set_variable(var_name, current - 1)
            except:
                pass
        
        elif operation == 'append':
            current = self._context.get_variable(var_name, [])
            if not isinstance(current, list):
                current = [current]
            current.append(value)
            self._context.set_variable(var_name, current)
        
        self._emit('on_variable_change', var_name, self._context.get_variable(var_name))
        return True
    
    def _execute_delay_node(self, node: FlowNode) -> bool:
        duration = node.properties.get('duration', 1.0)
        start_time = time.time()
        
        while (time.time() - start_time) < duration:
            if self._stop_flag:
                return False
            while self._pause_flag:
                time.sleep(0.1)
                if self._stop_flag:
                    return False
            time.sleep(0.05)
        
        return True
    
    def get_context(self) -> FlowExecutionContext:
        return self._context
