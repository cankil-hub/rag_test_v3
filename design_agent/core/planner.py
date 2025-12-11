
from typing import Dict, List
from .researcher import LDOResearcher

class LDOPlanner:
    """
    规划器：负责思考、拆解任务和整合结果
    """
    def __init__(self, researcher: LDOResearcher):
        self.researcher = researcher
        self.chat_model = researcher.rag.chat_model

    def analyze_request(self, user_request: str) -> Dict:
        """
        分析用户请求，生成行动计划
        (目前使用简化逻辑，未来可以使用 LLM 生成 JSON 计划)
        """
        plan = {
            "original_request": user_request,
            "intent": "unknown",
            "search_queries": []
        }
        
        # 简单的意图识别
        plan["search_queries"] = [user_request] # 保留原始查询
        plan["source_filter"] = None # 文档过滤器
        
        # 增强: 如果包含 Figure/Fig 关键词，增加专用检索
        import re
        fig_match = re.search(r'(Figure|Fig\.?)\s*(\d+)', user_request, re.IGNORECASE)
        if fig_match:
            fig_key = f"{fig_match.group(1)} {fig_match.group(2)}" # e.g. "Figure 10"
            plan["search_queries"].append(fig_key) # 增加精准检索 "Figure 10"
        
        # 增强: 提取文档名 (e.g., "Any-Cap...pdf" or "LDO.pdf")
        # 匹配 .pdf 结尾的文件名
        doc_match = re.search(r'([A-Za-z0-9\-_\s]+\.pdf)', user_request, re.IGNORECASE)
        if doc_match:
            # 提取核心部分用于 contains 匹配
            doc_name = doc_match.group(1).strip()
            # 尝试提取一个更短的唯一关键词 (如 "Any-Cap")
            short_match = re.match(r'^([A-Za-z0-9\-]+)', doc_name)
            if short_match:
                plan["source_filter"] = short_match.group(1)
            else:
                plan["source_filter"] = doc_name
            
        if "复刻" in user_request or "simulate" in user_request or "impl" in user_request.lower():
            plan["intent"] = "reproduce_topology"
        else:
            plan["intent"] = "general_design"
            
        return plan

    def execute_plan(self, plan: Dict) -> Dict:
        """执行计划，返回结构化结果"""
        intent = plan["intent"]
        queries = plan["search_queries"]
        source_filter = plan.get("source_filter")
        
        if source_filter:
            print(f"  [Planner] 文档过滤器: '{source_filter}'")
        
        collected_info = ""
        all_figure_paths = []
        all_formula_paths = []
        
        # 1. 思考与检索循环（使用原始查询，不精炼）
        for q in queries:
            print(f"  [Planner] 步骤: 检索 '{q}'")
            context, fig_paths, formula_paths = self.researcher.search_topology(q, source_filter=source_filter)
            collected_info += f"\n--- Search Result for '{q}' ---\n{context}\n"
            all_figure_paths.extend(fig_paths)
            all_formula_paths.extend(formula_paths)
        
        # 去重图片路径
        unique_figure_paths = list(dict.fromkeys(all_figure_paths))
        unique_formula_paths = list(dict.fromkeys(all_formula_paths))
        
        print(f"  [Planner] 总共收集到: {len(unique_figure_paths)} 张图片, {len(unique_formula_paths)} 个公式")

        # 2. 深度思考与整合 (LLM Synthesis)
        print("  [Planner] 正在整合信息并生成设计建议...")
        
        system_prompt = """你是一个精通模拟集成电路设计的专家（LDO Design Agent）。
你的任务是根据提供的[RAG检索结果]和相关图片，回答用户的[设计请求]。

要求：
1. **架构分析**：详细分析检索到的电路结构。如果有图片，请参考图片中的电路拓扑，识别关键器件（功率管、误差放大器、补偿电容等）。
2. **可行性评估**：评估该结构是否适合用指定的CMOS工艺实现。
3. **设计建议**：给出初步的设计思路和参数建议。
4. **引用来源**：必须明确引用检索结果中的文档名。如果引用了图片，说明是哪个文档的哪张图。
5. **输出格式**：使用Markdown格式，包含清晰的章节标题。
"""
        user_prompt = f"""
[用户请求]: {plan['original_request']}

[RAG检索结果]:
{collected_info}

请给出你的专业分析报告（Markdown格式）。
"""
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        response = self.chat_model.chat_with_images(
            prompt=full_prompt,
            image_paths=unique_figure_paths[:10]  # 增加到10张图片
        )
        
        # 返回结构化数据
        return {
            "text_report": response,
            "figures": unique_figure_paths,
            "formulas": unique_formula_paths,
            "raw_context": collected_info
        }
