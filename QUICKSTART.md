# RAG v3-improved 快速入门指南

## 1. 创建和激活虚拟环境

### Windows (PowerShell)
```powershell
# 进入项目目录
cd d:\python\RAG\rag_test_v3

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 如果遇到执行策略错误,运行:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Windows (CMD)
```cmd
cd d:\python\RAG\rag_test_v3
python -m venv venv
venv\Scripts\activate.bat
```

### Linux/Mac
```bash
cd /path/to/RAG/rag_test_v3
python -m venv venv
source venv/bin/activate
```

## 2. 安装依赖

```bash
# 确保虚拟环境已激活(提示符前有 (venv))
pip install -r requirements_v3_improved.txt
```

安装时间约2-5分钟,主要包括:
- LangChain框架
- PyMuPDF (PDF处理)
- Pillow (图像处理)
- ChromaDB (向量数据库)
- Google Gemini SDK

## 3. 配置环境变量

在项目根目录创建 `.env` 文件:

```env
# Qwen Embedding配置(用于文本向量化)
EMBEDDING_API_KEY=your_qwen_api_key_here
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v2

# Gemini多模态模型配置(用于理解图片和文本)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash-exp

# v3向量库配置
V3_CHROMA_PERSIST_DIR=./data_base_v3/chroma
V3_COLLECTION_NAME=rag_v3_improved
V3_PAGE_IMAGE_DIR=./data_base_v3/page_images

# 文档配置
DOCUMENTS_DIR=./documents
CHUNK_SIZE=500
CHUNK_OVERLAP=50
```

### 获取API Key

**Qwen Embedding**:
1. 访问: https://dashscope.aliyun.com/
2. 注册/登录阿里云账号
3. 开通DashScope服务
4. 创建API Key

**Gemini**:
1. 访问: https://aistudio.google.com/app/apikey
2. 登录Google账号
3. 创建API Key

## 4. 准备文档

将PDF教材/论文放入 `documents` 目录:

```
rag_test_v3/
├── documents/
│   ├── analog_circuits.pdf
│   ├── power_management.pdf
│   └── ...
```

## 5. 测试组件

```bash
# 测试各个组件是否正常工作
python test_components.py
```

预期输出:
```
测试 FigureExtractor
✓ 成功提取 X 个图片

测试 FormulaExtractor
✓ 成功提取 X 个公式

测试 MultimodalIndex
✓ 索引和关联功能正常

测试 ContentLinker
✓ 内容关联功能正常

总计: 4/4 通过
🎉 所有测试通过!
```

## 6. 启动系统

```bash
# 启动交互式对话
python -m rag_test_v3.start_v3_improved
```

或者使用Python API:

```python
from rag_test_v3.rag_agent_v3_improved import RAGAgentV3Improved

# 初始化智能体
agent = RAGAgentV3Improved()

# 重建知识库(首次使用)
agent.rebuild_knowledge_base()

# 开始对话
response = agent.chat("Buck变换器的输出纹波公式是什么?")
print(response)
```

## 7. 交互式命令

启动后可用命令:

```
您: /rebuild
# 重建知识库(提取图片和公式,建立索引)

您: /search Buck变换器
# 搜索知识库

您: /stats
# 显示索引统计信息

您: /rag off
# 关闭RAG模式(纯LLM对话)

您: /rag on
# 开启RAG模式

您: /quit
# 退出程序
```

## 8. 首次使用流程

```bash
# 1. 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 2. 启动系统
python -m rag_test_v3.start_v3_improved

# 3. 重建知识库
您: /rebuild

# 等待提取完成...
# [步骤 1/4] 提取图片和公式...
# [步骤 2/4] 构建文本向量库...
# [步骤 3/4] 关联文本与图片/公式...
# [步骤 4/4] 保存索引...
# ✓ 知识库重建完成!

# 4. 开始提问
您: Buck变换器的输出纹波电压公式是什么?如何推导?

# 智能体会返回包含公式图片和电路图的详细回答
```

## 9. 常见问题

### Q: 虚拟环境激活失败?
```powershell
# 运行此命令允许执行脚本
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Q: 依赖安装失败?
```bash
# 升级pip
python -m pip install --upgrade pip

# 重新安装
pip install -r requirements_v3_improved.txt
```

### Q: 找不到模块错误?
```bash
# 确保在正确的目录
cd d:\python\RAG\rag_test_v3

# 确保虚拟环境已激活
.\venv\Scripts\Activate.ps1
```

### Q: API调用失败?
- 检查 `.env` 文件中的API Key是否正确
- 确认网络连接正常
- 检查API配额是否用尽

## 10. 退出虚拟环境

```bash
# 完成工作后退出虚拟环境
deactivate
```

## 下次使用

```bash
# 1. 进入目录
cd d:\python\RAG\rag_test_v3

# 2. 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 3. 启动系统
python -m rag_test_v3.start_v3_improved

# 4. 直接开始对话(知识库已存在,无需重建)
您: 你的问题...
```

## 性能优化建议

### 加速知识库重建
- 首次重建可能需要5-10分钟(取决于PDF数量)
- 后续使用无需重建,直接对话

### 降低成本
- 使用 `/rag off` 进行简单对话(不消耗向量检索)
- 调整 `max_images` 参数减少图片数量

### 提升效果
- 调整公式识别规则(`formula_extractor.py`)
- 优化图片过滤阈值(`figure_extractor.py`)
- 定制Prompt(`rag_agent_v3_improved.py`)

---

祝使用愉快! 🚀
