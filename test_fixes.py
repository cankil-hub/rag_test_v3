# 测试修复后的图片检索和网表生成

from design_agent.circuit_prototype_generator import CircuitPrototypeGenerator

print("="*60)
print("测试修复后的功能")
print("="*60)

generator = CircuitPrototypeGenerator()

requirement = "我需要一个超低功耗的LDO，静态电流要求小于1uA"

print(f"\n需求: {requirement}\n")

result = generator.generate_prototype(requirement)

if result["success"]:
    print(f"\n✓ 成功生成网表!")
    print(f"  架构: {result['architecture']}")
    print(f"  来源: {result['source']}")
    print(f"  网表: {result['netlist_path']}")
else:
    print(f"\n✗ 失败: {result.get('error')}")
