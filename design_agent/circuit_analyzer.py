"""
Circuit Analyzer: 利用 Vision LLM 自动提取电路拓扑
支持两种模式：
1. Transistor-level: 完整的晶体管级电路
2. Small-signal: 小信号模型（用 VCCS/VCVS 等理想元件）
"""
import json
import re
from pathlib import Path
from typing import Dict, Literal

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gemini_chat_model import GeminiChatModel
from config_v3 import ConfigV3

class CircuitAnalyzer:
    def __init__(self):
        self.config = ConfigV3()
        self.vision_model = GeminiChatModel(self.config)
        self.output_dir = Path("./design_agent/topology_drafts")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def analyze_circuit(
        self, 
        image_path: str, 
        circuit_type: Literal["transistor", "small_signal"] = "transistor",
        figure_info: Dict = None
    ) -> Dict:
        """
        分析电路图，生成拓扑结构
        
        Args:
            image_path: 电路图路径
            circuit_type: "transistor" (晶体管级) 或 "small_signal" (小信号模型)
            figure_info: 可选的图片元信息 {"figure_id": ..., "source": ..., "page": ...}
        
        Returns:
            topology dict
        """
        print(f"[CircuitAnalyzer] 正在分析电路图: {os.path.basename(image_path)}")
        print(f"[CircuitAnalyzer] 电路类型: {circuit_type}")
        
        # 根据类型选择prompt
        if circuit_type == "transistor":
            prompt = self._get_transistor_prompt()
        else:
            prompt = self._get_small_signal_prompt()
        
        # 调用 Vision LLM
        response = self.vision_model.chat_with_images(prompt, [image_path])
        
        # 解析JSON
        topology = self._extract_json_from_response(response)
        
        if topology:
            # 添加元信息
            if figure_info:
                topology.update(figure_info)
            
            print(f"[CircuitAnalyzer] ✓ 识别到 {len(topology.get('devices', []))} 个器件")
            return topology
        else:
            print(f"[CircuitAnalyzer] ✗ JSON解析失败")
            return None
    
    def _get_transistor_prompt(self) -> str:
        return """
你是一个精通模拟电路设计的专家。请**非常仔细**地观察这张LDO电路原理图，完成以下任务：

## 任务1：识别所有器件

对于每个器件，记录：
- **名称**：如 M1, M2, R1, C1, MPASS 等
- **类型**：nmos, pmos, resistor, capacitor, isource（电流源）
- **尺寸**：
  - MOSFET: 从图中读取 W/L 标注（如 "100/2" 表示 W=100μm, L=2μm）
  - 电阻: 从图中读取阻值（如 "50k"）
  - 电容: 从图中读取容值（如 "1u"）

## 任务2：识别连接关系

对于每个MOSFET，记录四个端口连到哪个节点：
- **d** (drain): 漏极连接的节点
- **g** (gate): 栅极连接的节点
- **s** (source): 源极连接的节点
- **b** (bulk/body): 衬底连接的节点（通常PMOS连VDD，NMOS连GND）

对于电阻/电容，记录：
- **pos**: 正极节点
- **neg**: 负极节点

**节点命名规则**：
- 供电：VIN 或 VDD
- 输出：VOUT
- 地：GND 或 0
- 参考：VREF
- 反馈：VFB 或 FB
- 中间节点：n1, n2, n3, ... 或 n_bias, n_ctrl 等有意义的名字

## 任务3：整理所有节点

列出电路中的所有节点名称。

## 输出格式

请严格按照以下JSON格式输出（**只输出JSON，不要其他文字**）：

```json
{
  "circuit_type": "transistor_level",
  "devices": [
    {
      "name": "M1",
      "type": "nmos",
      "size": "100/2",
      "connections": {
        "d": "n1",
        "g": "VREF",
        "s": "n5",
        "b": "GND"
      },
      "comment": "输入差分对左管"
    },
    {
      "name": "R1",
      "type": "resistor",
      "value": "50k",
      "connections": {
        "pos": "VOUT",
        "neg": "VFB"
      }
    }
  ],
  "nets": ["VIN", "VOUT", "GND", "VREF", "VFB", "n1", "n2", ...]
}
```

**重要提示**：
1. 仔细跟踪每条连线，确保连接关系正确
2. 精确读取图中的尺寸标注（W/L值）
3. 如果看不清某个标注，在comment中注明 "尺寸不清晰，需确认"
"""
    
    def _get_small_signal_prompt(self) -> str:
        return """
你是一个精通模拟电路设计的专家。这是一张**小信号等效电路图**（用于AC分析），请识别其拓扑结构。

## 小信号元件类型

识别以下理想元件：
- **gm (跨导源，VCCS)**：电压控制电流源，记录控制电压节点和输出电流节点
  - 例如：gm1 受 v(in) 控制，电流输出到 out 节点
- **ro (输出电阻)**：电阻
- **Cgd, Cgs (寄生电容)**：电容
- **Cc (补偿电容)**：电容  
- **RL, CL (负载)**：电阻、电容

## 输出格式

```json
{
  "circuit_type": "small_signal",
  "devices": [
    {
      "name": "gm1",
      "type": "vccs",
      "value": "gm1",
      "connections": {
        "control_pos": "vin",
        "control_neg": "gnd",
        "out_pos": "n1",
        "out_neg": "gnd"
      },
      "comment": "误差放大器跨导"
    },
    {
      "name": "ro1",
      "type": "resistor",
      "value": "ro1",
      "connections": {
        "pos": "n1",
        "neg": "gnd"
      }
    },
    {
      "name": "Cc",
      "type": "capacitor",
      "value": "Cc",
      "connections": {
        "pos": "n1",
        "neg": "vout"
      },
      "comment": "米勒补偿电容"
    }
  ],
  "nets": ["vin", "vout", "gnd", "n1", "n2", ...]
}
```

**重要**：
1. VCCS的连接需要4个端口（control_pos, control_neg, out_pos, out_neg）
2. 参数值（如 gm1, ro1）保持符号形式，不需要具体数值
3. 注明每个元件的功能（如 "主极点电容"）
"""
    
    def _extract_json_from_response(self, response: str) -> Dict:
        """从LLM响应中提取JSON"""
        # 方法1: 提取 ```json ... ``` 代码块
        match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if match:
            json_str = match.group(1)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"[CircuitAnalyzer] JSON解码错误: {e}")
                # 如果JSON被截断，尝试只取到响应结束
                try:
                    # 查找第一个 {，取到响应末尾
                    start = json_str.find('{')
                    if start != -1:
                        return json.loads(json_str[start:])
                except:
                    pass
        
        # 方法2: 尝试直接解析整个响应
        try:
            return json.loads(response)
        except:
            pass
        
        # 方法3: 查找第一个完整的JSON对象
        try:
            start = response.find('{')
            if start != -1:
                # 简单的括号匹配
                depth = 0
                for i, char in enumerate(response[start:], start):
                    if char == '{':
                        depth += 1
                    elif char == '}':
                        depth -= 1
                        if depth == 0:
                            return json.loads(response[start:i+1])
        except:
            pass
        
        print("[CircuitAnalyzer] 警告: 无法从响应中提取有效JSON")
        print(f"响应内容:\n{response[:1000]}...\n")
        
        # 保存原始响应供调试
        debug_file = self.output_dir / "last_llm_response.txt"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(response)
        print(f"[CircuitAnalyzer] 完整LLM响应已保存到: {debug_file}")
        
        return None
    
    def save_draft(self, topology: Dict, filename: str):
        """保存拓扑草稿"""
        output_path = self.output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(topology, f, ensure_ascii=False, indent=2)
        
        print(f"[CircuitAnalyzer] ✓ 拓扑草稿已保存: {output_path}")
        print(f"[CircuitAnalyzer] 请人工审核并修正后移动到 topology/ 目录")
        return str(output_path)


if __name__ == "__main__":
    # 测试：分析 Figure 10 (小信号模型)
    analyzer = CircuitAnalyzer()
    
    # 示例：分析已有的 Figure 10
    fig10_path = "d:/python/RAG/rag_test_v3/data_base_v3/figures/Any-Cap_Low_Dropout_Voltage_Regulator_fig_p27_i0.png"
    
    if os.path.exists(fig10_path):
        topology = analyzer.analyze_circuit(
            image_path=fig10_path,
            circuit_type="small_signal",  # Figure 10 是框图，可能适合小信号分析
            figure_info={
                "figure_id": "Any-Cap_Fig10_MillerLDO",
                "source": "Any-Cap Low Dropout Voltage Regulator.pdf",
                "page": 27,
                "description": "Block diagram of Miller-Compensated LDO"
            }
        )
        
        if topology:
            analyzer.save_draft(topology, "fig10_anycap_draft.json")
    else:
        print(f"找不到图片: {fig10_path}")
        print("请提供有效的电路图路径进行测试")
