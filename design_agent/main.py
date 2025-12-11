
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent dir to path to import RAG components
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_agent_v3_improved import RAGAgentV3Improved
from design_agent.core.planner import LDOPlanner
from design_agent.core.researcher import LDOResearcher
from design_agent.core.engineer import LDOEngineer
from design_agent.circuit_prototype_generator import CircuitPrototypeGenerator

class LDODesignAgent:
    def __init__(self):
        print("[LDO Agent] 初始化中...")
        self.rag_engine = RAGAgentV3Improved()
        self.researcher = LDOResearcher(self.rag_engine)
        self.engineer = LDOEngineer()
        self.planner = LDOPlanner(self.researcher)
        self.prototype_gen = CircuitPrototypeGenerator(self.rag_engine)
        
        # 对话上下文
        self.conversation_history = []
        self.last_analysis = None
        
        # 输出目录
        self.report_dir = Path("./design_agent/reports")
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        print("[LDO Agent] ✓ 初始化完成。我是你的LDO设计助手。")

    def run(self, user_request: str):
        """运行设计任务"""
        print(f"\n[用户指令] {user_request}")
        
        # 检测是否是后续请求（生成网表）
        if self._is_netlist_request(user_request) and self.last_analysis:
            return self._generate_netlist_from_context()
        
        # 1. 规划与思考
        plan = self.planner.analyze_request(user_request)
        
        # 2. 执行计划并获取结构化结果
        print(f"\n[LDO Agent] 正在思考并执行计划...")
        report_data = self.planner.execute_plan(plan)
        
        # 3. 保存到对话历史
        self.last_analysis = {
            "request": user_request,
            "plan": plan,
            "report_data": report_data,
            "timestamp": datetime.now()
        }
        self.conversation_history.append(self.last_analysis)
        
        # 4. 生成Markdown报告（嵌入图片）
        md_report = self._generate_markdown_report(
            report_data["text_report"],
            report_data["figures"]
        )
        
        # 5. 保存并显示报告
        report_path = self._save_report(md_report, user_request)
        
        print("\n" + "="*60)
        print("[设计分析报告]")
        print("="*60)
        print(md_report)
        print("\n" + "="*60)
        print(f"📄 报告已保存: {report_path}")
        
        # 6. 检测是否需要生成网表
        should_gen_netlist = self._should_generate_netlist(user_request, report_data["text_report"])
        
        if should_gen_netlist:
            print("\n🔧 正在生成电路原型...")
            self._generate_netlist_from_context()
        else:
            print("\n💡 提示: 输入 '生成网表' 或 '请给出电路原型' 以创建SPICE网表")
        
        print("="*60)
    
    def _is_netlist_request(self, request: str) -> bool:
        """判断是否是生成网表的请求"""
        keywords = ["生成网表", "网表", "电路原型", "SPICE", "给出电路"]
        return any(kw in request for kw in keywords)
    
    def _should_generate_netlist(self, request: str, report: str) -> bool:
        """判断是否应该自动生成网表"""
        # 用户明确要求
        explicit_keywords = ["请给出电路原型", "生成网表", "输出网表", "SPICE"]
        if any(kw in request for kw in explicit_keywords):
            return True
        
        # 报告中提到了网表但用户没要求，则不自动生成
        return False
    
    def _generate_netlist_from_context(self):
        """基于上一轮分析生成网表"""
        if not self.last_analysis:
            print("⚠ 警告: 没有可用的设计分析上下文")
            return
        
        print(f"\n[LDO Agent] 基于设计分析生成电路原型...")
        
        original_request = self.last_analysis["request"]
        
        result = self.prototype_gen.generate_prototype(original_request)
        
        if result["success"]:
            print(f"\n✓ 网表生成成功!")
            print(f"  推荐架构: {result['architecture']}")
            print(f"  来源: {result['source']}")
            print(f"  网表路径: {result['netlist_path']}")
            print(f"\n下一步: 使用 ngspice 仿真验证")
            print(f"  命令: ngspice -b {result['netlist_path']}")
        else:
            print(f"\n✗ 网表生成失败: {result.get('error', 'Unknown error')}")
    
    def _generate_markdown_report(self, text_report: str, figure_paths: list) -> str:
        """生成Markdown格式报告，嵌入图片"""
        md = "# LDO 设计分析报告\n\n"
        md += f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        md += "---\n\n"
        
        # 主体内容
        md += text_report
        
        # 嵌入图片
        if figure_paths:
            md += "\n\n---\n\n"
            md += "## 📊 检索到的参考图片\n\n"
            for i, fig_path in enumerate(figure_paths[:6], 1):  # 最多6张
                # 获取相对路径（相对于项目根目录）
                try:
                    rel_path = os.path.relpath(fig_path, os.getcwd())
                    # 提取文件名作为标题
                    filename = os.path.basename(fig_path)
                    md += f"### 图 {i}: {filename}\n\n"
                    md += f"![{filename}]({rel_path})\n\n"
                except Exception as e:
                    md += f"### 图 {i}\n\n"
                    md += f"_图片路径错误: {e}_\n\n"
        
        return md
    
    def _save_report(self, md_content: str, user_request: str) -> str:
        """保存Markdown报告到文件"""
        import re
        
        # 生成文件名（基于时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 提取需求关键词作为文件名的一部分，并清理非法字符
        brief = user_request[:20]
        # Windows文件名非法字符: < > : " / \ | ? *
        brief = re.sub(r'[<>:"/\\|?*]', '_', brief)
        brief = brief.replace(" ", "_").replace("\n", "")
        
        filename = f"report_{timestamp}_{brief}.md"
        
        report_path = self.report_dir / filename
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        return str(report_path)

if __name__ == "__main__":
    agent = LDODesignAgent()
    print("\n" + "="*60)
    print("欢迎使用 LDO 设计助手")
    print("="*60)
    print("功能:")
    print("  - 提问LDO设计相关问题，获得基于论文的专业建议")
    print("  - 要求生成电路原型和SPICE网表")
    print("  - 支持多轮对话，保持上下文")
    print("\n提示:")
    print("  - 输入需求后，可以继续输入 '生成网表' 创建SPICE电路")
    print("  - 或在需求中加入 '请给出电路原型' 一次性生成")
    print("="*60 + "\n")
    
    while True:
        try:
            req = input("\n请下达设计指令 (输入 q 退出): ")
            if req.lower() in ['q', 'quit', 'exit']:
                print("\n再见!")
                break
            agent.run(req)
        except KeyboardInterrupt:
            print("\n\n再见!")
            break
        except Exception as e:
            print(f"\n✗ 错误: {e}")
            import traceback
            traceback.print_exc()
