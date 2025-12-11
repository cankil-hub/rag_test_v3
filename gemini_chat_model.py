"""
Gemini 多模态聊天模型封装 (v3)
负责与 Gemini-2.x 系列模型进行文本/图像混合对话。
"""
from pathlib import Path
from typing import List, Optional

import google.generativeai as genai  # 需要用户安装 google-generativeai

from config_v3 import ConfigV3


class GeminiChatModel:
    """Gemini 聊天模型封装类（支持多模态输入）"""

    def __init__(self, config: ConfigV3):
        cfg = config.get_gemini_config()
        api_key = cfg["api_key"]
        model_name = cfg["model"]

        if not api_key:
            raise ValueError("GEMINI_API_KEY 未设置")

        genai.configure(api_key=api_key)
        self.model_name = model_name
        
        # 配置生成参数,支持更长的输出
        generation_config = {
            "max_output_tokens": 8192,  # 最大输出token数,适合长文本应用
            "temperature": 0.7,          # 控制随机性
        }
        
        self.model = genai.GenerativeModel(
            model_name,
            generation_config=generation_config
        )

    def chat(self, message: str) -> str:
        """纯文本对话"""
        try:
            resp = self.model.generate_content(message)
            return resp.text or ""
        except Exception as e:
            return f"[Gemini 对话出错]: {e}"

    def chat_with_images(
        self,
        prompt: str,
        image_paths: List[str],
    ) -> str:
        """
        带图片的多模态对话:
        - prompt: 文字指令 + 上下文
        - image_paths: 本地 PNG 图片路径列表
        """
        parts: List = [prompt]

        for p in image_paths:
            try:
                data = Path(p).read_bytes()
            except Exception:
                continue
            parts.append(
                {
                    "mime_type": "image/png",
                    "data": data,
                }
            )

        try:
            resp = self.model.generate_content(parts)
            return resp.text or ""
        except Exception as e:
            return f"[Gemini 多模态对话出错]: {e}"


