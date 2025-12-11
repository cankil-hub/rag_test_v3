# LDO RAG 系统使用指南

> 一个基于RAG（检索增强生成）的LDO电路设计智能助手

## 目录

1. [快速开始](#快速开始)
2. [核心功能](#核心功能)
3. [使用示例](#使用示例)
4. [API参考](#api参考)
5. [目录结构](#目录结构)

---

## 快速开始

### 环境要求

- Python 3.8+
- 已配置 Gemini API Key（在 `.env` 文件中）

### 安装依赖

```bash
pip install -r requirements_v3_improved.txt
```

---

## ⭐ 两个核心命令

### 1️⃣ 构建/更新RAG知识库

**程序**: `start.py`

将PDF论文放入 `papers/` 目录后，运行：

```bash
python start.py
```

该程序会：
- 扫描 `papers/` 目录下的PDF文件
- 提取文本、图片和公式
- 构建向量索引
- 保存到 `vector_store/` 和 `image_store/`

**增量更新**: 只需添加新PDF到 `papers/` 目录，再次运行 `start.py` 即可。

---

### 2️⃣ 使用RAG进行LDO设计

**程序**: `design_agent/circuit_prototype_generator.py`

```bash
python -c "
from design_agent.circuit_prototype_generator import generate_ldo_prototype

# 输入你的设计需求
result = generate_ldo_prototype('我需要一个超低功耗的LDO，静态电流小于1uA')

if result['success']:
    print(f'推荐架构: {result[\"architecture\"]}')
    print(f'网表路径: {result[\"netlist_path\"]}')
"
```

**或者交互式使用**:

```python
# 启动Python交互环境
python

>>> from design_agent.circuit_prototype_generator import CircuitPrototypeGenerator
>>> generator = CircuitPrototypeGenerator()
>>> result = generator.generate_prototype("我需要一个高PSRR的LDO")
>>> print(result['architecture'])
>>> print(result['rationale'])
```

---

## 核心功能

### 1. 设计咨询 (`RAGAgentV3Improved.chat`)

向系统提问LDO设计相关问题，获得基于论文的专业回答。

```python
from rag_agent_v3_improved import RAGAgentV3Improved

rag = RAGAgentV3Improved()
answer = rag.chat("如何提高LDO的PSRR？")
print(answer)
```

### 2. 原型电路生成 (`CircuitPrototypeGenerator`)

根据设计需求，自动推荐架构并生成可仿真的SPICE网表。

```python
from design_agent.circuit_prototype_generator import CircuitPrototypeGenerator

generator = CircuitPrototypeGenerator()
result = generator.generate_prototype("我需要一个高PSRR的LDO")

# 结果包含：
# - architecture: 推荐的架构名称
# - source: 来源论文
# - rationale: 详细推荐理由
# - netlist_path: 生成的SPICE网表路径
```

### 3. 知识库检索 (`RAGAgentV3Improved.retrieve_context`)

直接检索论文内容、图片和公式。

```python
rag = RAGAgentV3Improved()
context, figures, formulas = rag.retrieve_context(
    query="Miller补偿 LDO 稳定性",
    k=10,
    max_images=6
)
```

---

## 使用示例

### 示例1: 超低功耗LDO设计

**需求**: 静态电流<1uA，用于IoT设备

```python
result = generator.generate_prototype(
    "我需要一个超低功耗的LDO，静态电流要求小于1uA，用于IoT设备"
)
```

**输出**:
- 推荐架构: Any-Load Stable LDO (Vadim Ivanov方法)
- 静态电流: 300nA
- 关键技术: 亚阈值工作、高阻抗反馈网络

### 示例2: 高PSRR LDO设计

**需求**: 为RF前端供电，100kHz PSRR > 60dB

```python
result = generator.generate_prototype(
    "我需要设计一个高PSRR的LDO，用于为敏感的RF前端电路供电"
)
```

**可能推荐**:
- Cascode LDO架构
- 前馈纹波消除 (FFRC)
- OPD LDO

### 示例3: Digital LDO设计

**需求**: 先进工艺节点，快速瞬态响应

```python
result = generator.generate_prototype(
    "我想设计一个Digital LDO，用于先进工艺节点下的数字负载供电"
)
```

**输出**:
- 推荐架构: Coarse-Fine Dual-Loop Digital LDO
- 电流效率: 99.94%
- 面积: 0.021 mm²

---

## API参考

### CircuitPrototypeGenerator

```python
class CircuitPrototypeGenerator:
    def __init__(self, rag_engine=None):
        """初始化生成器"""
    
    def generate_prototype(self, requirement: str) -> dict:
        """
        根据需求生成原型电路
        
        Args:
            requirement: 用户需求描述
            
        Returns:
            {
                "success": bool,
                "architecture": str,      # 推荐架构
                "source": str,            # 来源论文
                "rationale": str,         # 推荐理由
                "key_parameters": dict,   # 关键参数
                "topology": dict,         # 电路拓扑
                "netlist_path": str       # 网表路径
            }
        """
```

### RAGAgentV3Improved

```python
class RAGAgentV3Improved:
    def __init__(self, config_path=".env"):
        """初始化RAG引擎"""
    
    def chat(self, message: str, use_rag=True) -> str:
        """多模态对话接口"""
    
    def retrieve_context(self, query: str, k=10) -> tuple:
        """检索上下文: (context, figures, formulas)"""
    
    def rebuild_knowledge_base(self, target_filename=None):
        """重建知识库"""
```

---

## 目录结构

```
rag_test_v3/
├── start.py                    # ⭐ 构建RAG知识库
├── rag_agent_v3_improved.py    # RAG核心引擎
├── config_v3.py                # 配置管理
├── gemini_chat_model.py        # LLM封装
├── design_agent/               # 设计代理模块
│   ├── main.py                 # ⭐ 交互式设计代理入口
│   ├── circuit_prototype_generator.py  # 原型电路生成器
│   ├── circuit_analyzer.py     # 电路分析器
│   ├── netlist_generator.py    # 网表生成器
│   ├── core/                   # 核心组件
│   │   ├── engineer.py         # 工程师角色
│   │   ├── planner.py          # 规划器
│   │   └── researcher.py       # 研究员
│   ├── prototypes/             # 生成的原型电路
│   └── topology/               # 电路拓扑JSON
├── documents/                  # ⭐ PDF论文库（放这里）
├── vector_store/               # 向量数据库
└── image_store/                # 提取的图片
```

---

## 添加新论文

1. 将PDF文件放入 `documents/` 目录
2. 运行：

```bash
python start.py
```

或在交互模式中使用：
```
您: /sync
```

---

## 常见问题

### Q: 生成的网表如何仿真？

使用ngspice：
```bash
ngspice -b prototype_xxx.sp
```

### Q: 如何提高架构推荐的准确性？

1. 在知识库中添加更多相关论文
2. 需求描述尽量详细和具体

### Q: 支持哪些电路类型？

当前主要支持LDO相关电路的小信号模型，包括：
- 传统模拟LDO
- Digital LDO
- 高PSRR LDO
- 超低功耗LDO

---

## 版本历史

- **v3.0**: 增加RAG引导的原型电路生成功能
- **v2.0**: 多模态RAG支持（图片+公式）
- **v1.0**: 基础文本检索功能
