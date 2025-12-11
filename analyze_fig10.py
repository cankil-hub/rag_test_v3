"""
使用 Vision LLM 分析 Figure 10
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from design_agent.circuit_analyzer import CircuitAnalyzer

# 初始化analyzer
analyzer = CircuitAnalyzer()

# Figure 10 是框图，适合用 small_signal 模式分析
# 如果图片存在则使用本地图片，否则从用户上传的图片中查找备份
fig10_candidates = [
    "d:/python/RAG/rag_test_v3/data_base_v3/figures/Any-Cap_Low_Dropout_Voltage_Regulator_fig_p27_i0.png",
    "C:/Users/jianqiu.chen/.gemini/antigravity/brain/d8421660-3c9d-4e89-9361-de7b650d42cd/uploaded_image_0_1765290068811.png"  # 备份(这是Figure 24)
]

image_path = None
for candidate in fig10_candidates:
    if os.path.exists(candidate):
        image_path = candidate
        print(f"使用图片: {candidate}")
        break

if not image_path:
    print("错误: 找不到 Figure 10 的图片")
    sys.exit(1)

# 分析电路
# Figure 10 是 Block Diagram，可能适合 small_signal 模式
topology = analyzer.analyze_circuit(
    image_path=image_path,
    circuit_type="small_signal",  # 框图通常用小信号模型
    figure_info={
        "figure_id": "Any-Cap_Fig10_MillerLDO",
        "source": "Any-Cap Low Dropout Voltage Regulator.pdf",
        "page": 27,
        "description": "Block Diagram of Miller-Compensated LDO Regulator"
    }
)

if topology:
    # 保存草稿
    draft_path = analyzer.save_draft(topology, "fig10_miller_ldo_draft.json")
    
    print("\n" + "="*60)
    print("分析成功！")
    print("="*60)
    print(f"识别到 {len(topology.get('devices', []))} 个器件")
    print(f"草稿保存在: {draft_path}")
    print("\n请人工审核草稿，确认无误后：")
    print("1. 移动到 topology/ 目录")
    print("2. 重命名为 fig10_miller_ldo.json")
else:
    print("分析失败")
    print("请查看 design_agent/topology_drafts/last_llm_response.txt 了解详情")
