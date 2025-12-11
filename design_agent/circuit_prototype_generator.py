"""
RAG引导的原型电路生成器
核心理念：让LLM基于知识库的专业论文知识生成电路，而非凭空臆想
"""
import json
import os
import sys
from typing import Dict, List, Tuple, Optional
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_agent_v3_improved import RAGAgentV3Improved
from gemini_chat_model import GeminiChatModel
from config_v3 import ConfigV3
from design_agent.netlist_generator import NetlistGenerator


class CircuitPrototypeGenerator:
    """
    RAG引导的原型电路生成器
    
    工作流程:
    1. RAG检索相关论文架构
    2. LLM分析并推荐最佳架构
    3. LLM根据论文知识生成理想电路
    4. 输出SPICE网表
    """
    
    def __init__(self, rag_engine: RAGAgentV3Improved = None):
        """初始化生成器"""
        print("[PrototypeGen] 初始化中...")
        
        # RAG引擎
        if rag_engine is None:
            self.rag = RAGAgentV3Improved()
        else:
            self.rag = rag_engine
        
        # LLM模型
        self.config = ConfigV3()
        self.llm = GeminiChatModel(self.config)
        
        # 网表生成器
        self.netlist_gen = NetlistGenerator()
        
        # 输出目录
        self.output_dir = Path("./design_agent/prototypes")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        print("[PrototypeGen] ✓ 初始化完成")
    
    def generate_prototype(self, requirement: str) -> Dict:
        """
        根据用户需求生成原型电路
        
        Args:
            requirement: 用户需求描述，如"超低功耗LDO，静态电流<1uA"
            
        Returns:
            {
                "success": bool,
                "architecture": "推荐的架构名称",
                "source": "来源论文",
                "rationale": "推荐理由",
                "topology": {...},  # 电路拓扑JSON
                "netlist_path": "xxx.sp",
                "summary": "总结说明"
            }
        """
        print(f"\n[PrototypeGen] 开始处理需求: {requirement[:50]}...")
        
        result = {
            "success": False,
            "requirement": requirement
        }
        
        try:
            # Step 1: RAG检索相关论文内容
            print("[PrototypeGen] Step 1: RAG检索相关架构...")
            context, figures, formulas = self._retrieve_relevant_content(requirement)
            
            if not context:
                result["error"] = "未找到相关论文内容"
                return result
            
            print(f"  ✓ 检索到 {len(context)} 字符的相关内容")
            print(f"  ✓ 找到 {len(figures)} 个相关图片")
            
            # Step 2: LLM分析并推荐架构
            print("[PrototypeGen] Step 2: LLM分析架构...")
            architecture_info = self._analyze_architecture(requirement, context, figures)
            
            if not architecture_info:
                result["error"] = "架构分析失败"
                return result
            
            result["architecture"] = architecture_info.get("architecture_name", "Unknown")
            result["source"] = architecture_info.get("source_paper", "Unknown")
            result["rationale"] = architecture_info.get("rationale", "")
            result["key_parameters"] = architecture_info.get("key_parameters", {})
            
            print(f"  ✓ 推荐架构: {result['architecture']}")
            print(f"  ✓ 来源: {result['source']}")
            
            # Step 3: LLM生成理想电路拓扑
            print("[PrototypeGen] Step 3: LLM生成电路拓扑...")
            topology = self._generate_circuit_topology(
                requirement, 
                architecture_info, 
                context
            )
            
            if not topology:
                result["error"] = "电路拓扑生成失败"
                return result
            
            result["topology"] = topology
            print(f"  ✓ 生成了 {len(topology.get('devices', []))} 个器件")
            
            # Step 4: 生成SPICE网表
            print("[PrototypeGen] Step 4: 生成SPICE网表...")
            netlist_path = self._generate_netlist(topology, requirement)
            
            result["netlist_path"] = netlist_path
            print(f"  ✓ 网表已保存: {netlist_path}")
            
            # 生成总结
            result["summary"] = self._generate_summary(result)
            result["success"] = True
            
            print("\n[PrototypeGen] ✓ 原型电路生成完成!")
            
        except Exception as e:
            result["error"] = str(e)
            print(f"\n[PrototypeGen] ✗ 生成失败: {e}")
            import traceback
            traceback.print_exc()
        
        return result
    
    def _retrieve_relevant_content(self, requirement: str) -> Tuple[str, List, List]:
        """从RAG检索相关论文内容"""
        # 构建检索查询
        search_query = f"LDO {requirement} 架构 设计 电路"
        
        # 调用RAG检索
        context, figures, formulas = self.rag.retrieve_context(
            query=search_query,
            k=10,  # 检索更多内容
            max_images=15  # 增加容量，容纳图片和公式
        )
        
        return context, figures, formulas
    
    def _analyze_architecture(
        self, 
        requirement: str, 
        context: str, 
        figures: List
    ) -> Optional[Dict]:
        """LLM分析检索结果，推荐最佳架构（详细版）"""
        
        prompt = f"""你是模拟电路设计领域的资深专家。基于以下从专业论文中检索的内容，为用户需求推荐最合适的LDO架构。

## 用户需求
{requirement}

## 论文内容（来自知识库）
{context[:10000]}  

## 任务
请进行**详细的架构分析和推荐**，包括：

### 1. 论文中提到的架构梳理
- 列出论文中提到的所有LDO架构
- 简要说明每种架构的特点

### 2. 架构选择分析
针对用户需求，分析各架构的适用性：
- 哪些架构能满足该需求？
- 各架构的优缺点对比
- 为什么最终选择推荐的架构？

### 3. 推荐理由（详细说明）
- 该架构如何满足用户的核心需求？
- 该架构的关键技术特点是什么？
- 论文中是否有具体的性能数据支撑？

### 4. 设计关键点
- 实现该架构时需要注意什么？
- 有哪些设计权衡(tradeoff)？
- 论文中提到的典型参数值

## 输出要求
请输出JSON格式（只输出JSON，不要其他内容）:
{{
  "architecture_name": "推荐的架构名称",
  "source_paper": "来源论文名称",
  
  "architectures_in_papers": [
    {{"name": "架构1", "brief": "简要特点"}},
    {{"name": "架构2", "brief": "简要特点"}}
  ],
  
  "selection_analysis": {{
    "candidates": ["候选架构1", "候选架构2"],
    "comparison": "各架构对比分析（100-200字）",
    "why_selected": "为什么选择推荐的架构（100-200字）"
  }},
  
  "rationale": "详细的推荐理由，包括：该架构如何满足需求、关键技术特点、论文中的性能数据等（300-500字）",
  
  "key_parameters": {{
    "gm_ea": "误差放大器跨导典型值及说明",
    "gm_pass": "调整管跨导典型值及说明",
    "ro_ea": "误差放大器输出阻抗",
    "Cc": "补偿电容",
    "CL": "支持的负载电容范围",
    "Iq": "静态电流"
  }},
  
  "design_considerations": {{
    "key_techniques": ["关键技术1", "关键技术2"],
    "tradeoffs": ["权衡1", "权衡2"],
    "implementation_notes": "实现时需要注意的事项"
  }}
}}
"""
        
        # 调用LLM（带图片如果有的话）
        if figures:
            response = self.llm.chat_with_images(prompt, figures[:3])
        else:
            response = self.llm.chat(prompt)
        
        # 解析JSON
        architecture_info = self._extract_json(response)
        
        # 打印详细分析结果
        if architecture_info:
            self._print_architecture_analysis(architecture_info)
        
        return architecture_info
    
    def _print_architecture_analysis(self, info: Dict):
        """打印详细的架构分析结果"""
        print("\n" + "="*60)
        print("📊 架构分析报告")
        print("="*60)
        
        # 论文中的架构
        archs = info.get("architectures_in_papers", [])
        if archs:
            print("\n📖 论文中提到的架构:")
            for arch in archs:
                print(f"   • {arch.get('name', 'N/A')}: {arch.get('brief', '')}")
        
        # 选择分析
        selection = info.get("selection_analysis", {})
        if selection:
            print(f"\n🔍 候选架构: {', '.join(selection.get('candidates', []))}")
            print(f"\n📋 对比分析:")
            print(f"   {selection.get('comparison', 'N/A')}")
            print(f"\n✅ 选择理由:")
            print(f"   {selection.get('why_selected', 'N/A')}")
        
        # 推荐架构
        print(f"\n🏆 推荐架构: {info.get('architecture_name', 'N/A')}")
        print(f"   来源: {info.get('source_paper', 'N/A')}")
        
        # 详细理由
        rationale = info.get("rationale", "")
        if rationale:
            print(f"\n📝 详细推荐理由:")
            # 分行打印，每行不超过60字符
            for i in range(0, len(rationale), 60):
                print(f"   {rationale[i:i+60]}")
        
        # 设计考量
        considerations = info.get("design_considerations", {})
        if considerations:
            techniques = considerations.get("key_techniques", [])
            if techniques:
                print(f"\n🔧 关键技术: {', '.join(techniques)}")
            
            tradeoffs = considerations.get("tradeoffs", [])
            if tradeoffs:
                print(f"⚖️  设计权衡: {', '.join(tradeoffs)}")
        
        print("\n" + "="*60)
    
    def _generate_circuit_topology(
        self, 
        requirement: str,
        architecture_info: Dict, 
        context: str
    ) -> Optional[Dict]:
        """LLM根据架构信息生成理想电路拓扑"""
        
        arch_name = architecture_info.get("architecture_name", "LDO")
        key_params = architecture_info.get("key_parameters", {})
        
        prompt = f"""你是模拟电路设计专家。根据以下架构信息，生成一个理想单元的小信号等效电路。

## 用户需求
{requirement}

## 推荐架构
{arch_name}

## 关键参数
{json.dumps(key_params, indent=2, ensure_ascii=False)}

## 论文参考
{context[:4000]}

## 任务
生成该架构的**小信号等效电路**，使用以下理想元件：

1. **VCCS (压控电流源)**: 表示跨导级
   - 用于误差放大器、缓冲级、调整管等
   - 格式: {{"name": "gm_ea", "type": "vccs", "value": "100u", ...}}

2. **电阻 R**: 表示输出阻抗
   - 用于各级的输出阻抗
   - 格式: {{"name": "ro_ea", "type": "resistor", "value": "1Meg", ...}}

3. **电容 C**: 表示电容
   - 补偿电容、寄生电容、负载电容
   - 格式: {{"name": "Cc", "type": "capacitor", "value": "10p", ...}}

## 输出要求
输出JSON格式（只输出JSON，不要其他内容）:
{{
  "figure_id": "prototype_{{需求关键词}}",
  "description": "电路描述",
  "circuit_type": "small_signal",
  "devices": [
    {{
      "name": "器件名",
      "type": "vccs/resistor/capacitor",
      "value": "数值+单位",
      "connections": {{...}},
      "comment": "说明"
    }}
  ],
  "parameters": {{
    "参数名": "参数值"
  }}
}}

## 重要提示
1. 确保电路拓扑完整（输入、各级、输出、反馈）
2. 参数值要基于论文内容，给出合理的典型值
3. VCCS的connections需要包含: control_pos, control_neg, out_pos, out_neg
4. 电阻和电容的connections需要包含: pos, neg
5. 所有节点名使用小写
"""
        
        response = self.llm.chat(prompt)
        return self._extract_json(response)
    
    def _generate_netlist(self, topology: Dict, requirement: str) -> str:
        """从拓扑生成SPICE网表"""
        
        # 生成文件名
        # 从需求中提取关键词
        keywords = requirement.replace(" ", "_").replace("，", "_")[:30]
        filename = f"prototype_{keywords}.sp"
        output_path = self.output_dir / filename
        
        # 构建网表内容
        netlist_lines = []
        
        # 标题
        desc = topology.get("description", "Prototype Circuit")
        netlist_lines.append(f"* Prototype: {desc}")
        netlist_lines.append(f"* Requirement: {requirement}")
        netlist_lines.append(f"* Generated by RAG-Guided Circuit Generator")
        netlist_lines.append("")
        netlist_lines.append(f".title {desc}")
        netlist_lines.append("")
        
        # 参数定义
        params = topology.get("parameters", {})
        if params:
            netlist_lines.append("* Circuit parameters")
            for param_name, param_value in params.items():
                netlist_lines.append(f".param {param_name}={param_value}")
            netlist_lines.append("")
        
        # 输入信号
        netlist_lines.append("* Input signal")
        netlist_lines.append("VIN vin 0 DC 0.6 AC 1  * Reference/Input voltage")
        netlist_lines.append("")
        
        # 器件定义
        vccs_list = []
        resistor_list = []
        capacitor_list = []
        
        for dev in topology.get("devices", []):
            dev_type = dev.get("type", "")
            name = dev.get("name", "")
            value = dev.get("value", "1")
            conn = dev.get("connections", {})
            comment = dev.get("comment", "")
            
            if dev_type == "vccs":
                ctrl_pos = conn.get("control_pos", "vin")
                ctrl_neg = conn.get("control_neg", "gnd")
                out_pos = conn.get("out_pos", "out")
                out_neg = conn.get("out_neg", "gnd")
                vccs_list.append(f"G{name} {out_pos} {out_neg} {ctrl_pos} {ctrl_neg} {value}  * {comment}")
            
            elif dev_type == "resistor":
                pos = conn.get("pos", "out")
                neg = conn.get("neg", "gnd")
                resistor_list.append(f"R{name} {pos} {neg} {value}  * {comment}")
            
            elif dev_type == "capacitor":
                pos = conn.get("pos", "out")
                neg = conn.get("neg", "gnd")
                capacitor_list.append(f"C{name} {pos} {neg} {value}  * {comment}")
        
        if vccs_list:
            netlist_lines.append("* Transconductance stages (VCCS)")
            netlist_lines.extend(vccs_list)
            netlist_lines.append("")
        
        if resistor_list:
            netlist_lines.append("* Resistances")
            netlist_lines.extend(resistor_list)
            netlist_lines.append("")
        
        if capacitor_list:
            netlist_lines.append("* Capacitances")
            netlist_lines.extend(capacitor_list)
            netlist_lines.append("")
        
        # AC分析命令
        netlist_lines.append("* AC Analysis")
        netlist_lines.append(".ac dec 100 1 100Meg")
        netlist_lines.append("")
        netlist_lines.append(".control")
        netlist_lines.append("run")
        netlist_lines.append("plot vdb(vout) phase(vout)")
        netlist_lines.append("let gain_db = vdb(vout)")
        netlist_lines.append("let phase_deg = phase(vout) * 180 / pi")
        netlist_lines.append("meas ac ugf when gain_db=0")
        netlist_lines.append("meas ac pm find phase_deg when gain_db=0")
        netlist_lines.append("print ugf pm")
        netlist_lines.append(".endc")
        netlist_lines.append("")
        netlist_lines.append(".end")
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(netlist_lines))
        
        # 同时保存拓扑JSON
        json_path = self.output_dir / f"prototype_{keywords}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(topology, f, indent=2, ensure_ascii=False)
        
        return str(output_path)
    
    def _generate_summary(self, result: Dict) -> str:
        """生成结果总结"""
        summary = f"""
## 原型电路生成完成

### 推荐架构
- **名称**: {result.get('architecture', 'N/A')}
- **来源**: {result.get('source', 'N/A')}

### 推荐理由
{result.get('rationale', 'N/A')}

### 生成的电路
- **类型**: 小信号等效电路
- **器件数**: {len(result.get('topology', {}).get('devices', []))}
- **网表路径**: `{result.get('netlist_path', 'N/A')}`

### 关键参数
"""
        for k, v in result.get('key_parameters', {}).items():
            summary += f"- **{k}**: {v}\n"
        
        return summary
    
    def _extract_json(self, response: str) -> Optional[Dict]:
        """从LLM响应中提取JSON"""
        import re
        
        # 方法1: 尝试提取 ```json ... ``` 代码块
        match = re.search(r'```json\s*\n(.*?)\n```', response, re.DOTALL)
        if match:
            try:
                json_str = match.group(1).strip()
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"[PrototypeGen] JSON解码错误(方法1): {e}")
                # 继续尝试其他方法
        
        # 方法1.5: 尝试提取 ``` ... ``` 代码块（无json标记）
        match = re.search(r'```\s*\n(\{.*?\})\s*\n```', response, re.DOTALL)
        if match:
            try:
                json_str = match.group(1).strip()
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # 方法2: 尝试直接解析
        try:
            return json.loads(response)
        except:
            pass
        
        # 方法3: 查找第一个 { 和最后一个 }
        start = response.find('{')
        end = response.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                json_str = response[start:end+1]
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"[PrototypeGen] JSON解码错误(方法3): {e}")
                # 保存原始响应用于调试
                debug_file = self.output_dir / "last_llm_response_error.txt"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(response)
                print(f"[PrototypeGen] 原始响应已保存到: {debug_file}")
        
        print(f"[PrototypeGen] 警告: 无法解析JSON响应")
        print(f"  响应前200字符: {response[:200]}")
        return None


# 便捷函数
def generate_ldo_prototype(requirement: str) -> Dict:
    """便捷函数：生成LDO原型电路"""
    generator = CircuitPrototypeGenerator()
    return generator.generate_prototype(requirement)


if __name__ == "__main__":
    # 测试
    print("="*60)
    print("RAG引导的原型电路生成器测试")
    print("="*60)
    
    generator = CircuitPrototypeGenerator()
    
    # 测试用例
    test_requirement = "我需要一个超低功耗的LDO，静态电流要求小于1uA，用于IoT设备"
    
    result = generator.generate_prototype(test_requirement)
    
    if result["success"]:
        print("\n" + "="*60)
        print(result["summary"])
    else:
        print(f"\n生成失败: {result.get('error', 'Unknown error')}")
