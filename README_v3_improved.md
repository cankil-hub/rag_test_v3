# RAG v3-improved - 多模态智能问答系统

基于选择性提取策略的多模态RAG系统,专为模拟电路设计领域优化。

## 核心特性

### ✨ 与原v3的关键区别

| 特性 | 原v3 (全页渲染) | v3-improved (选择性提取) |
|------|----------------|------------------------|
| **存储策略** | 渲染所有PDF页面 | 仅提取图片和公式 |
| **存储效率** | ~1GB/500页 | ~60MB/500页 (节省94%) |
| **Token消耗** | ~8000/次 | ~2000/次 (节省75%) |
| **检索精准度** | 页面级 | 图片/公式级 |
| **相关性** | 中 | 高 |

### 🎯 主要功能

1. **智能图片提取**: 自动识别PDF中的图片,过滤图标和装饰元素
2. **公式识别**: 基于启发式规则识别数学公式并高清渲染
3. **自动关联**: 基于引用、页码、上下文自动关联文本与图片/公式
4. **多模态检索**: 检索时同时返回相关文本、图片和公式
5. **Gemini集成**: 使用Gemini 2.0 Flash理解文本+图像

## 架构组件

```
rag_test_v3/
├── figure_extractor.py          # 图片提取器
├── formula_extractor.py         # 公式提取器
├── multimodal_index.py          # 多模态索引
├── content_linker.py            # 内容关联器
├── rag_agent_v3_improved.py     # 改进的RAG智能体
├── start_v3_improved.py         # 交互式入口
├── vector_store_v3.py           # 向量库管理
├── gemini_chat_model.py         # Gemini模型封装
└── config_v3.py                 # 配置管理
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements_v3_improved.txt
```

### 2. 配置环境

创建 `.env` 文件:

```env
# Qwen Embedding配置(复用v2)
EMBEDDING_API_KEY=your_qwen_api_key
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v2

# Gemini多模态模型配置
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.0-flash-exp

# v3向量库配置(独立于v2)
V3_CHROMA_PERSIST_DIR=./data_base_v3/chroma
V3_COLLECTION_NAME=rag_v3_improved
V3_PAGE_IMAGE_DIR=./data_base_v3/page_images

# 文档配置
DOCUMENTS_DIR=./documents
CHUNK_SIZE=500
CHUNK_OVERLAP=50
```

### 3. 准备文档

将PDF教材/论文放入 `./documents/` 目录

### 4. 运行

```bash
# 交互式对话
python -m rag_test_v3.start_v3_improved

# 或直接导入使用
python
>>> from rag_test_v3.rag_agent_v3_improved import RAGAgentV3Improved
>>> agent = RAGAgentV3Improved()
>>> agent.rebuild_knowledge_base()  # 首次使用需重建
>>> agent.chat("Buck变换器的输出纹波公式是什么?")
```

## 使用示例

### 重建知识库

```python
from rag_test_v3.rag_agent_v3_improved import RAGAgentV3Improved

agent = RAGAgentV3Improved()

# 重建知识库(提取图片和公式)
agent.rebuild_knowledge_base()
```

输出:
```
开始重建 v3-improved 知识库...
[步骤 1/4] 提取图片和公式...
找到 3 个PDF文件

处理: analog_circuits.pdf
[FigureExtractor] 提取完成: 25 个有效图片
[FormulaExtractor] 提取完成: 48 个公式

✓ 提取完成:
  - 图片: 25 个
  - 公式: 48 个

[步骤 2/4] 构建文本向量库...
[步骤 3/4] 关联文本与图片/公式...
[ContentLinker] 关联完成: 共建立 156 个关联
[步骤 4/4] 保存索引...
✓ 知识库重建完成!
```

### 多模态对话

```python
# 提问包含公式的问题
response = agent.chat("Buck变换器的输出纹波电压公式是什么?如何推导?")
print(response)
```

智能体会:
1. 检索相关文本块
2. 找到关联的公式图片
3. 将文本+公式图片一起发送给Gemini
4. 返回详细的技术回答

### 搜索知识库

```python
docs, figures, formulas = agent.search_knowledge_base("Folding-Cascode运放", k=5)

print(f"文本块: {len(docs)}")
print(f"相关图片: {len(figures)}")
print(f"相关公式: {len(formulas)}")

# 查看图片信息
for fig in figures:
    print(f"- {fig['caption']} (页码: {fig['page']})")
```

## 交互式命令

运行 `python -m rag_test_v3.start_v3_improved` 后可用命令:

- **直接输入问题**: 进行多模态对话
- `/rag on/off`: 开启/关闭RAG模式
- `/rebuild`: 重建知识库
- `/search <query>`: 搜索知识库
- `/stats`: 显示索引统计
- `/quit`: 退出

## 技术细节

### 图片提取策略

1. **过滤规则**:
   - 文件大小 < 10KB → 跳过(可能是图标)
   - 尺寸 < 100x100 → 跳过
   - 纵横比 > 10 或 < 0.1 → 跳过(装饰线)
   - 信息熵太低 → 跳过(空白页)

2. **图注提取**:
   - 匹配"图X.X"、"Figure X.X"等模式
   - 合并多行图注

### 公式识别规则

1. 包含等号且长度适中
2. 包含数学符号(∫, ∑, √, ∂等)
3. 包含分数形式(V/R)
4. 包含上下标(V_out, x^2)
5. 包含括号和运算符

### 关联策略

1. **基于引用**: 文本中提到"图1.1"则关联对应图片
2. **基于页码**: 同一页的内容自动关联
3. **基于上下文**: 公式与前后文本块关联
4. **基于关键词**: "如图所示"等关键词触发关联

## 性能优化建议

### 1. 图片压缩

如果存储空间有限,可以降低图片质量:

```python
# 在 figure_extractor.py 中
# 添加图片压缩逻辑
from PIL import Image

img = Image.open(image_path)
img = img.resize((img.width // 2, img.height // 2))  # 缩小50%
img.save(image_path, quality=85)  # JPEG质量85
```

### 2. 缓存LLM响应

对于常见问题,缓存响应以节省成本:

```python
import hashlib
import json

cache_file = "./data_base_v3/response_cache.json"

def get_cached_response(query):
    query_hash = hashlib.md5(query.encode()).hexdigest()
    # 从cache_file读取
    ...
```

### 3. 批量处理

大量PDF时使用多进程:

```python
from multiprocessing import Pool

def process_pdf(pdf_path):
    extractor = FigureExtractor()
    return extractor.extract_figures(pdf_path)

with Pool(4) as p:
    results = p.map(process_pdf, pdf_files)
```

## 常见问题

### Q: 公式识别不准确怎么办?

A: 调整 `formula_extractor.py` 中的 `_is_formula()` 规则,或集成Mathpix OCR:

```python
# 安装: pip install mathpix
import mathpix

def ocr_formula(image_path):
    return mathpix.latex(image_path)
```

### Q: 图片关联错误怎么办?

A: 检查 `content_linker.py` 的关联逻辑,可以手动调整:

```python
# 手动关联
index.link_text_to_figure(chunk_id, figure_id)
```

### Q: 如何处理表格?

A: 添加 `TableExtractor`:

```python
import camelot

class TableExtractor:
    def extract_tables(self, pdf_path):
        tables = camelot.read_pdf(pdf_path, pages='all')
        # 渲染为图片或转为结构化数据
```

## 与v2对比

| 维度 | v2 | v3-improved |
|------|----|-----------| 
| **公式识别** | ❌ | ✅ |
| **图片理解** | ❌ | ✅ |
| **存储效率** | 高(仅文本) | 中(文本+图片/公式) |
| **Token消耗** | 低 | 中 |
| **回答质量** | 中 | 高(多模态) |
| **成本** | 低 | 中 |

## 下一步计划

- [ ] 集成Mathpix OCR提升公式识别
- [ ] 添加表格提取支持
- [ ] 实现响应缓存
- [ ] 支持跨页图表合并
- [ ] 添加评估数据集

## 许可证

MIT License

## 致谢

- LangChain - LLM应用框架
- PyMuPDF - PDF处理
- Google Gemini - 多模态理解
- Chroma - 向量数据库
