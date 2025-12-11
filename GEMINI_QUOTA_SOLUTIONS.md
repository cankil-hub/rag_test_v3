# Gemini API 配额问题解决方案

## 问题现象

您遇到的错误:
```
429 You exceeded your current quota
Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_input_token_count
```

## 原因分析

Gemini API免费版有严格的速率限制:
- **每分钟请求数**: 15次
- **每天请求数**: 1500次  
- **每分钟输入tokens**: 32,000
- **每分钟输出tokens**: 2,000

## 解决方案

### 方案1: 等待配额重置 (推荐用于测试)

免费配额按分钟和天重置:
- **分钟配额**: 等待60秒后重试
- **天配额**: 等待到第二天

### 方案2: 使用其他Gemini模型

不同模型有独立的配额,可以尝试:

```env
# 在.env文件中修改
GEMINI_MODEL=gemini-1.5-flash
# 或
GEMINI_MODEL=gemini-1.5-pro
```

### 方案3: 升级到付费版 (推荐用于生产)

访问 https://ai.google.dev/pricing 升级到付费版本:
- **Pay-as-you-go**: 按使用量付费
- **更高配额**: 每分钟1000+请求
- **更稳定**: 适合生产环境

### 方案4: 添加重试机制

在代码中添加自动重试:

```python
import time
from google.api_core import retry

@retry.Retry(
    initial=1.0,
    maximum=60.0,
    multiplier=2.0,
    deadline=300.0
)
def call_gemini_with_retry():
    # 您的Gemini调用代码
    pass
```

### 方案5: 实现请求队列

限制请求频率:

```python
import time
from collections import deque

class RateLimiter:
    def __init__(self, max_calls_per_minute=10):
        self.max_calls = max_calls_per_minute
        self.calls = deque()
    
    def wait_if_needed(self):
        now = time.time()
        # 移除1分钟前的记录
        while self.calls and self.calls[0] < now - 60:
            self.calls.popleft()
        
        # 如果达到限制,等待
        if len(self.calls) >= self.max_calls:
            sleep_time = 60 - (now - self.calls[0])
            if sleep_time > 0:
                print(f"速率限制: 等待 {sleep_time:.1f} 秒...")
                time.sleep(sleep_time)
        
        self.calls.append(time.time())

# 使用
limiter = RateLimiter(max_calls_per_minute=10)
limiter.wait_if_needed()
# 调用Gemini API
```

## 当前配置优化

### 1. max_output_tokens 已配置

我已经在 `gemini_chat_model.py` 中添加了配置:

```python
generation_config = {
    "max_output_tokens": 8192,  # 最大输出token数
    "temperature": 0.7,          # 控制随机性
}
```

### 2. 测试工具使用

运行测试工具检查连接:

```bash
python test_gemini_connection.py
```

这个工具会:
- ✅ 测试多个Gemini模型的连通性
- ✅ 检测配额问题
- ✅ 测试多模态功能
- ✅ 推荐可用的模型配置

### 3. 监控配额使用

访问 https://ai.dev/usage 查看:
- 当前配额使用情况
- 剩余配额
- 重置时间

## 推荐配置 (生产环境)

### .env 配置

```env
# Gemini配置
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-1.5-flash  # 或 gemini-2.0-flash-exp

# 如果使用付费版,可以设置更大的值
# MAX_OUTPUT_TOKENS=16384
```

### 代码中配置

在 `gemini_chat_model.py` 中:

```python
generation_config = {
    "max_output_tokens": 8192,      # 根据需要调整
    "temperature": 0.7,              # 0.0-1.0, 越高越随机
    "top_p": 0.95,                   # 核采样
    "top_k": 40,                     # Top-K采样
}
```

## 临时解决方案 (立即可用)

1. **等待60秒**: 让分钟配额重置
2. **切换模型**: 改用 `gemini-1.5-flash`
3. **减少请求**: 降低 `k` 参数(检索文档数量)
4. **批量处理**: 合并多个问题一次提问

## 长期建议

1. **升级付费版**: 用于生产环境
2. **实现缓存**: 缓存常见问题的答案
3. **添加重试**: 自动处理429错误
4. **监控配额**: 设置告警通知

---

**当前状态**: 您的API密钥有效,但遇到免费版配额限制。建议等待或升级到付费版。
