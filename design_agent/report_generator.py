"""
Design Report Generator: 生成包含仿真结果的设计报告
"""
import os
import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime

try:
    import matplotlib
    matplotlib.use('Agg')  # 非交互式后端
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("[ReportGen] ⚠ matplotlib未安装，Bode图生成功能将不可用")

class DesignReportGenerator:
    """设计报告生成器"""
    
    def __init__(self):
        self.report_dir = Path("./design_agent/reports")
        self.report_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_report(
        self,
        figure_id: str,
        circuit_type: str,
        netlist_path: str,
        simulation: Dict,
        validation: Dict,
        topology: Dict = None
    ) -> str:
        """
        生成设计报告
        
        Args:
            figure_id: 电路ID
            circuit_type: "transistor" 或 "small_signal"
            netlist_path: 网表路径
            simulation: 仿真结果
            validation: 验证结果
            topology: 可选的拓扑信息
        
        Returns:
            报告文件路径
        """
        print(f"[ReportGen] 正在生成报告: {figure_id}")
        
        # 准备报告内容
        report_lines = []
        report_lines.append(f"# {figure_id} 设计报告")
        report_lines.append("")
        report_lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"**电路类型**: {circuit_type}")
        report_lines.append("")
        
        # 添加拓扑信息
        if topology:
            report_lines.append("## 电路拓扑")
            report_lines.append("")
            report_lines.append(f"- **来源**: {topology.get('source', 'Unknown')}")
            report_lines.append(f"- **页码**: {topology.get('page', '?')}")
            report_lines.append(f"- **描述**: {topology.get('description', 'N/A')}")
            report_lines.append(f"- **器件数**: {len(topology.get('devices', []))}")
            report_lines.append("")
        
        # 仿真结果
        report_lines.append("## 仿真结果")
        report_lines.append("")
        
        if simulation.get("mock"):
            report_lines.append("> **注意**: 这是模拟仿真结果（Mock Mode）")
            report_lines.append("")
        
        if circuit_type == "small_signal":
            self._add_ac_results(report_lines, simulation)
        else:
            self._add_dc_results(report_lines, simulation)
        
        # 验证结果
        report_lines.append("## 验证结果")
        report_lines.append("")
        
        if validation.get("passed"):
            report_lines.append("### ✓ 验证通过")
        else:
            report_lines.append("### ✗ 验证失败")
        
        report_lines.append("")
        self._add_validation_details(report_lines, validation, circuit_type)
        
        # 网表信息
        report_lines.append("## 网表文件")
        report_lines.append("")
        report_lines.append(f"**路径**: `{netlist_path}`")
        report_lines.append("")
        
        # 绘制Bode图（如果是AC分析）
        if circuit_type == "small_signal" and MATPLOTLIB_AVAILABLE:
            bode_path = self._plot_bode(figure_id, simulation)
            if bode_path:
                report_lines.append("## Bode图")
                report_lines.append("")
                report_lines.append(f"![Bode Plot]({bode_path})")
                report_lines.append("")
        
        # 写入报告文件
        report_filename = f"{figure_id}_report.md"
        report_path = self.report_dir / report_filename
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        print(f"[ReportGen] ✓ 报告已生成: {report_path}")
        return str(report_path)
    
    def _add_ac_results(self, lines: List[str], sim: Dict):
        """添加AC仿真结果"""
        lines.append("### AC性能指标")
        lines.append("")
        lines.append("| 指标 | 值 |")
        lines.append("|------|-----|")
        
        ugf = sim.get("ugf", 0)
        pm = sim.get("pm", 0)
        gm = sim.get("gm", 0)
        
        lines.append(f"| 单位增益频率 (UGF) | {ugf/1e6:.2f} MHz |")
        lines.append(f"| 相位裕度 (PM) | {pm:.1f}° |")
        lines.append(f"| 增益裕度 (GM) | {gm:.1f} dB |")
        lines.append("")
    
    def _add_dc_results(self, lines: List[str], sim: Dict):
        """添加DC仿真结果"""
        lines.append("### DC工作点")
        lines.append("")
        lines.append("| 节点 | 电压 (V) |")
        lines.append("|------|----------|")
        
        voltages = sim.get("voltages", sim.get("dc_voltages", {}))
        for node, voltage in voltages.items():
            lines.append(f"| {node} | {voltage:.3f} |")
        lines.append("")
    
    def _add_validation_details(self, lines: List[str], val: Dict, circuit_type: str):
        """添加验证详情"""
        if circuit_type == "small_signal":
            pm = val.get("pm")
            ugf = val.get("ugf")
            
            if pm is not None:
                status = "✓" if val.get("phase_margin_ok") else "✗"
                lines.append(f"- {status} **相位裕度**: {pm:.1f}° (要求 >45°)")
            
            if ugf is not None:
                lines.append(f"- **UGF**: {ugf/1e6:.2f} MHz")
        
        else:  # transistor
            vout = val.get("vout")
            vout_error = val.get("vout_error")
            headroom = val.get("headroom")
            
            if vout is not None:
                status = "✓" if val.get("vout_in_range") else "✗"
                lines.append(f"- {status} **输出电压**: {vout:.3f} V (误差: {vout_error*1000:.1f} mV)")
            
            if headroom is not None:
                status = "✓" if val.get("sufficient_headroom") else "✗"
                lines.append(f"- {status} **压差 (Headroom)**: {headroom:.2f} V")
        
        lines.append("")
    
    def _plot_bode(self, figure_id: str, sim: Dict) -> str:
        """
        绘制Bode图
        
        Returns:
            图片路径（相对于报告文件）
        """
        if not MATPLOTLIB_AVAILABLE:
            return None
        
        # 目前使用模拟数据，真实数据需要从AC输出解析
        # TODO: 从ngspice .ac输出提取频率响应数据
        
        # 模拟典型的LDO Bode响应
        freq = np.logspace(0, 8, 1000)  # 1 Hz to 100 MHz
        
        ugf = sim.get("ugf", 1e6)
        pm_deg = sim.get("pm", 60)
        
        # 简化的单极点模型
        dc_gain_db = 60  # 典型LDO DC增益
        pole1 = ugf / (10 ** (dc_gain_db / 20))  # 主极点
        
        gain_db = dc_gain_db - 20 * np.log10(1 + freq / pole1)
        phase_deg = -np.arctan(freq / pole1) * 180 / np.pi
        
        # 绘图
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        
        # 增益图
        ax1.semilogx(freq, gain_db, 'b-', linewidth=2)
        ax1.axhline(0, color='r', linestyle='--', alpha=0.5, label='0 dB')
        ax1.axvline(ugf, color='g', linestyle='--', alpha=0.5, label=f'UGF = {ugf/1e6:.2f} MHz')
        ax1.set_ylabel('Gain (dB)', fontsize=12)
        ax1.set_title(f'{figure_id} - Frequency Response', fontsize=14, fontweight='bold')
        ax1.grid(True, which='both', alpha=0.3)
        ax1.legend()
        
        # 相位图
        ax2.semilogx(freq, phase_deg, 'r-', linewidth=2)
        ax2.axhline(-180, color='r', linestyle='--', alpha=0.5, label='-180°')
        ax2.axvline(ugf, color='g', linestyle='--', alpha=0.5)
        ax2.set_xlabel('Frequency (Hz)', fontsize=12)
        ax2.set_ylabel('Phase (degrees)', fontsize=12)
        ax2.grid(True, which='both', alpha=0.3)
        ax2.legend()
        
        # 标注相位裕度
        ax2.text(ugf * 1.5, phase_deg[np.argmin(np.abs(freq - ugf))], 
                 f'PM = {pm_deg:.1f}°', fontsize=10, bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))
        
        plt.tight_layout()
        
        # 保存
        plot_filename = f"{figure_id}_bode.png"
        plot_path = self.report_dir / plot_filename
        plt.savefig(plot_path, dpi=150)
        plt.close()
        
        return plot_filename  # 返回相对路径


if __name__ == "__main__":
    # 测试报告生成
    generator = DesignReportGenerator()
    
    # 模拟AC仿真结果
    sim_ac = {
        "success": True,
        "ugf": 1.2e6,
        "pm": 62.0,
        "gm": 12.0,
        "mock": True
    }
    
    validation_ac = {
        "passed": True,
        "phase_margin_ok": True,
        "pm": 62.0,
        "ugf": 1.2e6
    }
    
    report_path = generator.generate_report(
        figure_id="Any-Cap_Fig10_MillerLDO",
        circuit_type="small_signal",
        netlist_path="design_agent/workspace/fig10.sp",
        simulation=sim_ac,
        validation=validation_ac
    )
    
    print(f"\n✓ 测试报告已生成: {report_path}")
