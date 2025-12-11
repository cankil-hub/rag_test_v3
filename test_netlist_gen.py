# 测试简化后的网表生成

from design_agent.circuit_prototype_generator import CircuitPrototypeGenerator

print("="*60)
print("测试简化JSON后的网表生成")
print("="*60)

generator = CircuitPrototypeGenerator()

# 使用简单的需求避免超长输入
requirement = "超低功耗LDO，静态电流<1uA，用于IoT设备"

print(f"\n需求: {requirement}\n")

result = generator.generate_prototype(requirement)

if result["success"]:
    print(f"\n✓ 网表生成成功!")
    print(f"  架构: {result['architecture']}")
    print(f"  来源: {result['source']}")
    print(f"  推荐理由: {result.get('rationale', 'N/A')[:100]}...")
    print(f"  网表路径: {result['netlist_path']}")
else:
    print(f"\n✗ 生成失败: {result.get('error')}")
    
print("\n" + "="*60)
