"""
Netlist Generator for LDO Design Agent
Converts circuit topology JSON to SPICE netlist
"""
import json
from pathlib import Path
from typing import Dict, List

class NetlistGenerator:
    def __init__(self):
        self.topology_dir = Path("./design_agent/topology")
        self.template_dir = Path("./design_agent/templates")
        self.workspace_dir = Path("./design_agent/workspace")
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
    def load_topology(self, figure_id: str) -> Dict:
        """Load circuit topology from JSON"""
        # Try to find matching topology file
        for topo_file in self.topology_dir.glob("*.json"):
            with open(topo_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get('figure_id') == figure_id or figure_id in str(topo_file):
                    print(f"[NetlistGen] Loaded topology: {topo_file.name}")
                    return data
        
        raise FileNotFoundError(f"Topology for {figure_id} not found")
    
    def generate_from_topology(self, figure_id: str, output_name: str = None, params: Dict = None) -> str:
        """
        Generate SPICE netlist from topology
        
        Args:
            figure_id: Figure identifier (e.g., "Any-Cap_Fig24_Initial_LDO")
            output_name: Output filename (default: auto-generated)
            params: Optional parameter overrides {"VIN_VAL": "3.3", ...}
            
        Returns:
            Path to generated netlist
        """
        # Load topology
        topo = self.load_topology(figure_id)
        
        # Find corresponding template (simplified: assume same name pattern)
        template_name = "fig24_anycap_ldo.sp"  # Hardcoded for Phase 1
        template_path = self.template_dir / template_name
        
        if not template_path.exists():
            raise FileNotFoundError(f"Template {template_name} not found")
        
        # Read template
        with open(template_path, 'r', encoding='utf-8') as f:
            netlist_content = f.read()
        
        # Apply parameter substitutions
        if params:
            for key, value in params.items():
                placeholder = f"{{{key}}}"
                if placeholder in netlist_content:
                    netlist_content = netlist_content.replace(placeholder, str(value))
        
        # Generate output filename
        if output_name is None:
            output_name = f"{figure_id}_generated.sp"
        
        output_path = self.workspace_dir / output_name
        
        # Write netlist
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(netlist_content)
        
        print(f"[NetlistGen] Generated netlist: {output_path}")
        return str(output_path)
    
    def generate_from_template(self, template_name: str, params: Dict, output_name: str) -> str:
        """
        Simple template-based generation (for quick prototyping)
        """
        template_path = self.template_dir / template_name
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for key, value in params.items():
            content = content.replace(f"{{{key}}}", str(value))
        
        output_path = self.workspace_dir / output_name
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(output_path)
    
    def generate_small_signal_netlist(self, figure_id: str, output_name: str = None) -> str:
        """
        为小信号模型生成SPICE网表
        
        Args:
            figure_id: 电路图ID
            output_name: 输出文件名
        """
        # 加载拓扑
        topo = self.load_topology(figure_id)
        
        if topo.get('circuit_type') != 'small_signal':
            raise ValueError(f"拓扑类型不是 small_signal: {topo.get('circuit_type')}")
        
        # 生成网表内容
        netlist_lines = []
        netlist_lines.append(f"* Small-Signal Model: {figure_id}")
        netlist_lines.append(f"* Source: {topo.get('source', 'Unknown')}")
        netlist_lines.append("")
        netlist_lines.append(f".title {topo.get('description', 'Small-Signal Analysis')}")
        netlist_lines.append("")
        
        # 参数定义（从topology中获取，或使用默认值）
        params = topo.get('parameters', {})
        if params:
            netlist_lines.append("* Circuit parameters")
            for param_name, param_value in params.items():
                netlist_lines.append(f".param {param_name}={param_value}")
            netlist_lines.append("")
        
        # 输入信号
        netlist_lines.append("* Input signal")
        netlist_lines.append("VIN vin 0 AC 1")
        netlist_lines.append("")
        
        # 器件定义
        gm_stages = []
        resistors = []
        capacitors = []
        
        for dev in topo.get('devices', []):
            dev_type = dev.get('type')
            name = dev.get('name')
            value = dev.get('value')
            conn = dev.get('connections', {})
            comment = dev.get('comment', '')
            
            # 从参数表中获取实际值（如果有）
            actual_value = params.get(value, value) if params else value
            
            if dev_type == 'vccs':
                # Voltage-Controlled Current Source
                # Syntax: Gxxx n+ n- nc+ nc- value
                ctrl_pos = conn.get('control_pos', 'gnd')
                ctrl_neg = conn.get('control_neg', 'gnd')
                out_pos = conn.get('out_pos', 'gnd')
                out_neg = conn.get('out_neg', 'gnd')
                # 直接使用数值，不用大括号（某些ngspice版本不支持）
                gm_stages.append(f"G{name} {out_pos} {out_neg} {ctrl_pos} {ctrl_neg} {actual_value}  * {value} - {comment}")
            
            elif dev_type == 'resistor':
                pos = conn.get('pos', 'gnd')
                neg = conn.get('neg', 'gnd')
                resistors.append(f"R{name} {pos} {neg} {actual_value}  * {value} - {comment}")
            
            elif dev_type == 'capacitor':
                pos = conn.get('pos', 'gnd')
                neg = conn.get('neg', 'gnd')
                capacitors.append(f"C{name} {pos} {neg} {actual_value}  * {value} - {comment}")
        
        if gm_stages:
            netlist_lines.append("* Transconductance stages (VCCS)")
            netlist_lines.extend(gm_stages)
            netlist_lines.append("")
        
        if resistors:
            netlist_lines.append("* Resistances")
            netlist_lines.extend(resistors)
            netlist_lines.append("")
        
        if capacitors:
            netlist_lines.append("* Capacitances")
            netlist_lines.extend(capacitors)
            netlist_lines.append("")
        
        # 分析命令
        netlist_lines.append("* AC Analysis")
        netlist_lines.append(".ac dec 100 1 10Meg")
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
        if output_name is None:
            output_name = f"{figure_id}_smallsignal.sp"
        
        output_path = self.workspace_dir / output_name
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(netlist_lines))
        
        print(f"[NetlistGen] 生成小信号网表: {output_path}")
        return str(output_path)


if __name__ == "__main__":
    # Test: Generate Figure 24 netlist
    gen = NetlistGenerator()
    
    try:
        netlist_path = gen.generate_from_topology(
            figure_id="Any-Cap_Fig24_Initial_LDO",
            output_name="fig24_test.sp",
            params={
                "VIN_VAL": "3.3",
                "VREF_VAL": "0.6",
                "CLOAD_VAL": "1u",
                "ILOAD_VAL": "50m"
            }
        )
        
        print(f"\n✓ Netlist generated successfully:")
        print(f"  {netlist_path}")
        print(f"\nTo simulate, run:")
        print(f"  ngspice {netlist_path}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
