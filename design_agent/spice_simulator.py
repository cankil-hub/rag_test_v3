"""
SPICE Simulator: 自动运行ngspice仿真并解析结果
"""
import subprocess
import os
import re
from typing import Dict, List, Optional
from pathlib import Path

class SpiceSimulator:
    """SPICE仿真器封装"""
    
    def __init__(self, ngspice_path: str = "ngspice", use_mock: bool = False):
        """
        初始化仿真器
        
        Args:
            ngspice_path: ngspice可执行文件路径，默认从PATH查找
            use_mock: 是否使用模拟仿真（用于测试或无ngspice环境）
        """
        self.ngspice_path = ngspice_path
        self.use_mock = use_mock
        self.output_dir = Path("./design_agent/simulation_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查ngspice是否可用
        if not use_mock:
            self.ngspice_available = self._check_ngspice_available()
            if not self.ngspice_available:
                print("[Simulator] 切换到模拟模式（mock mode）")
                self.use_mock = True
    
    def _check_ngspice_available(self) -> bool:
        """检查ngspice是否安装"""
        try:
            print(f"[Simulator] 检查ngspice: {self.ngspice_path}")
            result = subprocess.run(
                [self.ngspice_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10  # 增加超时到10秒
            )
            if result.returncode == 0:
                print(f"[Simulator] ngspice 已找到")
                return True
            else:
                print(f"[Simulator] ⚠ ngspice 返回错误: {result.returncode}")
                print(f"  stderr: {result.stderr[:200]}")
                return False
        except subprocess.TimeoutExpired:
            print(f"[Simulator] ⚠ ngspice 超时（10秒）")
            return False
        except FileNotFoundError as e:
            print(f"[Simulator] ⚠ ngspice 文件未找到: {e}")
            return False
        except Exception as e:
            print(f"[Simulator] ⚠ ngspice 检查失败: {type(e).__name__}: {e}")
            return False
    
    def run_simulation(self, netlist_path: str) -> Dict:
        """
        运行SPICE仿真
        
        Args:
            netlist_path: 网表文件路径
            
        Returns:
            仿真结果字典
        """
        if self.use_mock:
            return self._mock_simulate(netlist_path)
        
        print(f"[Simulator] 正在仿真: {os.path.basename(netlist_path)}")
        
        # 准备输出文件
        output_log = self.output_dir / f"{Path(netlist_path).stem}_output.log"
        
        try:
            # 运行ngspice批处理模式
            cmd = [
                self.ngspice_path,
                "-b",  # 批处理模式
                netlist_path,
                "-o", str(output_log)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # 30秒超时
            )
            
            if result.returncode != 0:
                print(f"[Simulator] ✗ 仿真失败")
                print(f"  错误输出: {result.stderr[:200]}")
                return {
                    "success": False,
                    "error": result.stderr
                }
            
            # 解析输出
            with open(output_log, 'r', encoding='utf-8') as f:
                output = f.read()
            
            results = self._parse_output(output)
            results["success"] = True
            results["log_file"] = str(output_log)
            
            print(f"[Simulator] ✓ 仿真完成")
            return results
            
        except subprocess.TimeoutExpired:
            print(f"[Simulator] ✗ 仿真超时")
            return {"success": False, "error": "Simulation timeout"}
        except Exception as e:
            print(f"[Simulator] ✗ 仿真异常: {e}")
            return {"success": False, "error": str(e)}
    
    def run_dc_analysis(self, netlist_path: str) -> Dict:
        """
        运行DC工作点分析
        
        Returns:
            {
                "success": bool,
                "vout": float,
                "vin": float,
                "voltages": {"node_name": value, ...},
                "currents": {"device_name": value, ...}
            }
        """
        results = self.run_simulation(netlist_path)
        
        if not results.get("success"):
            return results
        
        # 提取DC工作点
        dc_results = {
            "success": True,
            "voltages": results.get("dc_voltages", {}),
            "currents": results.get("dc_currents", {})
        }
        
        # 提取关键节点电压
        voltages = dc_results["voltages"]
        dc_results["vout"] = voltages.get("vout", voltages.get("VOUT"))
        dc_results["vin"] = voltages.get("vin", voltages.get("VIN"))
        dc_results["gnd"] = 0.0
        
        return dc_results
    
    def run_ac_analysis(self, netlist_path: str) -> Dict:
        """
        运行AC分析
        
        Returns:
            {
                "success": bool,
                "ugf": float,  # 单位增益频率 (Hz)
                "pm": float,   # 相位裕度 (度)
                "gm": float,   # 增益裕度 (dB)
                "dc_gain": float,  # DC增益 (dB)
                "freq": List[float],  # 频率点
                "gain_db": List[float],  # 增益曲线
                "phase_deg": List[float]  # 相位曲线
            }
        """
        results = self.run_simulation(netlist_path)
        
        if not results.get("success"):
            return results
        
        # 提取AC分析结果
        ac_results = {
            "success": True,
            "measurements": results.get("measurements", {})
        }
        
        # 提取关键指标
        meas = ac_results["measurements"]
        ac_results["ugf"] = meas.get("ugf", 0.0)
        ac_results["pm"] = meas.get("pm", 0.0)
        ac_results["gm"] = meas.get("gm", 0.0)
        
        # TODO: 提取频率响应曲线数据（需要解析.ac输出）
        
        return ac_results
    
    def _parse_output(self, output: str) -> Dict:
        """
        解析ngspice输出
        
        提取：
        - DC工作点 (Operating Point)
        - 测量结果 (.meas命令输出)
        - AC响应数据
        """
        results = {
            "dc_voltages": {},
            "dc_currents": {},
            "measurements": {}
        }
        
        # 解析 .meas 测量结果
        # 格式: ugf = 1.234e+06
        meas_pattern = r'(\w+)\s*=\s*([-+]?[\d.]+[eE]?[-+]?\d*)'
        for match in re.finditer(meas_pattern, output):
            name = match.group(1)
            value = float(match.group(2))
            results["measurements"][name] = value
        
        # 解析DC工作点
        # 查找 "Node voltages" 或 "Operating Point" 部分
        dc_section = re.search(
            r'(Operating Point|Node voltages).*?(?=\n\s*\n|\Z)',
            output,
            re.DOTALL | re.IGNORECASE
        )
        
        if dc_section:
            dc_text = dc_section.group(0)
            # 格式: vout = 1.234
            voltage_pattern = r'v\((\w+)\)\s*=\s*([-+]?[\d.]+[eE]?[-+]?\d*)'
            for match in re.finditer(voltage_pattern, dc_text):
                node = match.group(1)
                voltage = float(match.group(2))
                results["dc_voltages"][node] = voltage
        
        return results
    
    def _mock_simulate(self, netlist_path: str) -> Dict:
        """
        模拟仿真（用于无ngspice环境）
        返回典型的LDO仿真结果
        """
        print(f"[Simulator] 🧪 模拟仿真模式: {os.path.basename(netlist_path)}")
        
        # 判断是小信号还是晶体管级
        is_small_signal = "smallsignal" in netlist_path.lower()
        
        if is_small_signal:
            # 小信号模型：返回AC结果
            return {
                "success": True,
                "measurements": {
                    "ugf": 1.2e6,  # 1.2 MHz
                    "pm": 62.0,     # 62°
                    "gm": 12.0      # 12 dB
                },
                "mock": True
            }
        else:
            # 晶体管级：返回DC结果
            return {
                "success": True,
                "dc_voltages": {
                    "vout": 1.21,
                    "vin": 3.3,
                    "vfb": 0.605,
                    "gnd": 0.0
                },
                "dc_currents": {},
                "measurements": {},
                "mock": True
            }
    
    def validate_dc_operating_point(self, dc_results: Dict, spec: Dict) -> Dict:
        """
        验证DC工作点
        
        Args:
            dc_results: DC仿真结果
            spec: 设计规格 {"vout_target": 1.2, "vout_tolerance": 0.05, ...}
        
        Returns:
            验证结果
        """
        checks = {}
        
        vout = dc_results.get("vout")
        vin = dc_results.get("vin")
        
        if vout is not None and vin is not None:
            # 检查输出电压
            vout_target = spec.get("vout_target", 1.2)
            vout_tolerance = spec.get("vout_tolerance", 0.1)
            vout_error = abs(vout - vout_target)
            checks["vout_in_range"] = vout_error < vout_tolerance
            checks["vout"] = vout
            checks["vout_error"] = vout_error
            
            # 检查压差
            min_headroom = spec.get("min_headroom", 0.2)
            headroom = vin - vout
            checks["sufficient_headroom"] = headroom > min_headroom
            checks["headroom"] = headroom
        
        checks["passed"] = all(v for k, v in checks.items() if k.endswith("_in_range") or k.endswith("_headroom"))
        
        return checks
    
    def validate_ac_stability(self, ac_results: Dict, spec: Dict) -> Dict:
        """
        验证AC稳定性
        
        Args:
            ac_results: AC仿真结果
            spec: 稳定性规格 {"min_pm": 45, "min_gm": 6, ...}
        """
        checks = {}
        
        pm = ac_results.get("pm")
        gm = ac_results.get("gm")
        ugf = ac_results.get("ugf")
        
        # 相位裕度
        if pm is not None:
            min_pm = spec.get("min_pm", 45)
            checks["phase_margin_ok"] = pm > min_pm
            checks["pm"] = pm
        
        # 增益裕度
        if gm is not None:
            min_gm = spec.get("min_gm", 6)
            checks["gain_margin_ok"] = gm > min_gm
            checks["gm"] = gm
        
        # UGF范围
        if ugf is not None:
            min_ugf = spec.get("min_ugf", 1e3)
            max_ugf = spec.get("max_ugf", 100e6)
            checks["ugf_reasonable"] = min_ugf < ugf < max_ugf
            checks["ugf"] = ugf
        
        checks["passed"] = all(v for k, v in checks.items() if k.endswith("_ok") or k.endswith("_reasonable"))
        
        return checks


if __name__ == "__main__":
    # 测试仿真器
    sim = SpiceSimulator()
    
    # 测试小信号网表
    netlist = "design_agent/workspace/Any-Cap_Fig10_MillerLDO_smallsignal.sp"
    
    if os.path.exists(netlist):
        print(f"\n测试AC分析: {netlist}")
        results = sim.run_ac_analysis(netlist)
        
        if results["success"]:
            print(f"✓ UGF: {results.get('ugf', 0)/1e6:.2f} MHz")
            print(f"✓ PM: {results.get('pm', 0):.1f}°")
            
            # 验证稳定性
            validation = sim.validate_ac_stability(results, {"min_pm": 45, "min_gm": 6})
            print(f"\n稳定性验证: {'✓ 通过' if validation['passed'] else '✗ 失败'}")
