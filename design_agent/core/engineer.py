"""
Engineer: 网表生成与电路设计
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from design_agent.netlist_generator import NetlistGenerator
from design_agent.spice_simulator import SpiceSimulator
from design_agent.report_generator import DesignReportGenerator

class LDOEngineer:
    """
    工程师：负责将电路拓扑转换为SPICE网表并进行仿真验证
    """
    def __init__(self):
        self.netlist_gen = NetlistGenerator()
        # 使用完整路径
        ngspice_path = r"D:\Program Files\ngspice-44.2_64\Spice64\bin\ngspice.exe"
        self.simulator = SpiceSimulator(ngspice_path=ngspice_path, use_mock=False)
        self.report_gen = DesignReportGenerator()
    
    def replicate_circuit(self, figure_id: str, params: dict = None) -> dict:
        """
        复刻指定电路，生成SPICE网表
        
        Args:
            figure_id: 电路图ID (如 "Any-Cap_Fig24_Initial_LDO")
            params: 参数覆盖 (如 {"VIN_VAL": "3.3", "ILOAD_VAL": "50m"})
            
        Returns:
            结果字典 {"success": bool, "netlist_path": str, "message": str}
        """
        print(f"  [Engineer] 正在复刻电路: '{figure_id}'")
        
        try:
            # 生成网表
            netlist_path = self.netlist_gen.generate_from_topology(
                figure_id=figure_id,
                output_name=f"{figure_id}_replica.sp",
                params=params or {}
            )
            
            print(f"  [Engineer] ✓ 网表生成成功!")
            
            return {
                "success": True,
                "netlist_path": netlist_path,
                "message": f"成功生成网表: {os.path.basename(netlist_path)}"
            }
            
        except FileNotFoundError as e:
            print(f"  [Engineer] ✗ 错误: {e}")
            return {
                "success": False,
                "netlist_path": None,
                "message": f"电路拓扑未找到: {str(e)}"
            }
        except Exception as e:
            print(f"  [Engineer] ✗ 生成失败: {e}")
            return {
                "success": False,
                "netlist_path": None,
                "message": f"网表生成失败: {str(e)}"
            }
    
    def replicate_small_signal_circuit(self, figure_id: str) -> dict:
        """
        复刻小信号模型电路
        
        Args:
            figure_id: 电路图ID (如 "Any-Cap_Fig10_MillerLDO")
        """
        print(f"  [Engineer] 正在复刻小信号模型: '{figure_id}'")
        
        try:
            # 生成小信号网表
            netlist_path = self.netlist_gen.generate_small_signal_netlist(
                figure_id=figure_id,
                output_name=f"{figure_id}_smallsignal.sp"
            )
            
            print(f"  [Engineer] ✓ 小信号网表生成成功!")
            
            return {
                "success": True,
                "netlist_path": netlist_path,
                "message": f"成功生成小信号网表: {os.path.basename(netlist_path)}"
            }
            
        except FileNotFoundError as e:
            print(f"  [Engineer] ✗ 错误: {e}")
            return {
                "success": False,
                "netlist_path": None,
                "message": f"电路拓扑未找到: {str(e)}"
            }
        except Exception as e:
            print(f"  [Engineer] ✗ 生成失败: {e}")
            return {
                "success": False,
                "netlist_path": None,
                "message": f"网表生成失败: {str(e)}"
            }
    
    def replicate_and_simulate(
        self, 
        figure_id: str, 
        circuit_type: str = "transistor",
        params: dict = None,
        generate_report: bool = True
    ) -> dict:
        """
        复刻电路并运行仿真验证
        
        Args:
            figure_id: 电路ID
            circuit_type: "transistor" 或 "small_signal"
            params: 参数（仅晶体管级需要）
            generate_report: 是否生成设计报告
        """
        print(f"  [Engineer] 复刻并验证: '{figure_id}'")
        
        # Step 1: 生成网表
        if circuit_type == "small_signal":
            netlist_result = self.replicate_small_signal_circuit(figure_id)
        else:
            netlist_result = self.replicate_circuit(figure_id, params)
        
        if not netlist_result["success"]:
            return netlist_result
        
        netlist_path = netlist_result["netlist_path"]
        
        # Step 2: 运行仿真
        print(f"  [Engineer] 正在仿真验证...")
        
        if circuit_type == "small_signal":
            sim_results = self.simulator.run_ac_analysis(netlist_path)
            
            if sim_results.get("success"):
                # 验证AC稳定性
                validation = self.simulator.validate_ac_stability(
                    sim_results,
                    {"min_pm": 45, "min_gm": 6}
                )
                
                result = {
                    "success": True,
                    "netlist_path": netlist_path,
                    "simulation": sim_results,
                    "validation": validation,
                    "message": "仿真验证完成"
                }
                
                # Step 3: 生成报告
                if generate_report:
                    try:
                        # 尝试加载拓扑信息
                        topology = self.netlist_gen.load_topology(figure_id)
                    except:
                        topology = None
                    
                    report_path = self.report_gen.generate_report(
                        figure_id=figure_id,
                        circuit_type=circuit_type,
                        netlist_path=netlist_path,
                        simulation=sim_results,
                        validation=validation,
                        topology=topology
                    )
                    result["report_path"] = report_path
                
                return result
            else:
                return {
                    "success": False,
                    "netlist_path": netlist_path,
                    "message": f"仿真失败: {sim_results.get('error', 'Unknown error')}"
                }
        
        else:  # transistor level
            sim_results = self.simulator.run_dc_analysis(netlist_path)
            
            if sim_results.get("success"):
                # 验证DC工作点
                validation = self.simulator.validate_dc_operating_point(
                    sim_results,
                    {"vout_target": params.get("VOUT_TARGET", 1.2), "vout_tolerance": 0.1}
                    if params else {}
                )
                
                result = {
                    "success": True,
                    "netlist_path": netlist_path,
                    "simulation": sim_results,
                    "validation": validation,
                    "message": "仿真验证完成"
                }
                
                # Step 3: 生成报告
                if generate_report:
                    try:
                        topology = self.netlist_gen.load_topology(figure_id)
                    except:
                        topology = None
                    
                    report_path = self.report_gen.generate_report(
                        figure_id=figure_id,
                        circuit_type=circuit_type,
                        netlist_path=netlist_path,
                        simulation=sim_results,
                        validation=validation,
                        topology=topology
                    )
                    result["report_path"] = report_path
                
                return result
            else:
                return {
                    "success": False,
                    "netlist_path": netlist_path,
                    "message": f"仿真失败: {sim_results.get('error', 'Unknown error')}"
                }
