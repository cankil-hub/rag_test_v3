"""
PDF公式提取器 (改进版v2 - 基于编号查找)
先找公式编号,再向左查找公式内容
"""
import fitz  # PyMuPDF
from typing import List, Dict, Optional, Tuple
import os
import re


class FormulaExtractorOCR:
    """PDF公式提取器 - 使用OCR识别公式"""
    
    def __init__(self, output_dir: str = "./data_base_v3/formulas"):
        """
        初始化公式提取器
        
        Args:
            output_dir: 公式图片输出目录
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # 初始化Pix2Text
        self.p2t = None
        self._init_pix2text()
        
        # 初始化缓存
        self.cache_file = os.path.join(output_dir, "ocr_cache.json")
        self.ocr_cache = {}
        self._load_cache()
        
        print(f"[FormulaExtractorOCR] 初始化完成, 输出目录: {output_dir}")
        print(f"[FormulaExtractorOCR] 加载缓存: {len(self.ocr_cache)} 条记录")

    def _load_cache(self):
        """加载OCR缓存"""
        if os.path.exists(self.cache_file):
            try:
                import json
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.ocr_cache = json.load(f)
            except Exception as e:
                print(f"[FormulaExtractorOCR] 加载缓存失败: {e}")
                self.ocr_cache = {}

    def _save_cache(self):
        """保存OCR缓存"""
        try:
            import json
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.ocr_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[FormulaExtractorOCR] 保存缓存失败: {e}")
    
    def _init_pix2text(self):
        """初始化Pix2Text"""
        try:
            from pix2text import Pix2Text
            print("[FormulaExtractorOCR] 加载Pix2Text模型...")
            self.p2t = Pix2Text.from_config()
            print("[FormulaExtractorOCR] ✓ Pix2Text加载成功")
        except ImportError:
            print("[FormulaExtractorOCR] ⚠ Pix2Text未安装,将使用基础文本提取")
            print("  安装命令: pip install pix2text[multilingual]")
            self.p2t = None
        except Exception as e:
            print(f"[FormulaExtractorOCR] ⚠ Pix2Text加载失败: {e}")
            self.p2t = None
    
    def extract_formulas(self, pdf_path: str) -> List[Dict]:
        """
        提取PDF中的公式
        
        新策略:
        1. 查找所有公式编号块 (X.Y)
        2. 向左查找相邻的数学表达式块
        3. 合并公式内容和编号
        4. OCR识别转LaTeX
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            公式元数据列表
        """
        if not os.path.exists(pdf_path):
            print(f"[FormulaExtractorOCR] PDF文件不存在: {pdf_path}")
            return []
        
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            print(f"[FormulaExtractorOCR] 打开PDF失败: {pdf_path}, 错误: {e}")
            return []
        
        formulas = []
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        
        print(f"[FormulaExtractorOCR] 开始提取: {pdf_path} (共{len(doc)}页)")
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_rect = page.rect
            page_width = page_rect.width
            
            # 获取页面文本块
            try:
                blocks = page.get_text("dict")["blocks"]
            except Exception as e:
                print(f"[FormulaExtractorOCR] 获取文本块失败 (页{page_num}): {e}")
                continue
            
            # 策略: 查找公式编号,然后查找相邻的公式内容
            equation_numbers = self._find_equation_numbers(blocks, page_width)
            
            for eq_num_info in equation_numbers:
                eq_num = eq_num_info['number']
                eq_block_idx = eq_num_info['block_idx']
                eq_bbox = eq_num_info['bbox']
                

                # 查找公式内容(向左查找相邻块)
                formula_blocks = self._find_formula_content(
                    blocks, eq_block_idx, eq_bbox, page_width
                )
                
                # [改进] 如果找不到文本块，尝试使用视觉回退策略 (Visual Fallback)
                # 针对如 Page 98 中 3.112 这种纯矢量/图片公式
                using_fallback = False
                if not formula_blocks:
                    fallback_bbox = self._get_fallback_bbox(eq_bbox, page_rect)
                    if fallback_bbox:
                        merged_bbox = fallback_bbox
                        using_fallback = True
                        # print(f"[FormulaExtractorOCR] 使用视觉回退: {eq_num}")
                    else:
                        continue
                else:
                    # 合并bbox
                    merged_bbox = self._merge_bboxes([b['bbox'] for b in formula_blocks] + [eq_bbox])
                
                # 生成公式ID
                formula_id = f"{base_name}_eq_p{page_num}_{eq_num.replace('.', '_')}"
                
                # 渲染公式区域
                image_path = self._render_formula_region(page, merged_bbox, formula_id)
                
                if not image_path:
                    continue
                
                # OCR识别
                if self.p2t:
                    latex = self._ocr_formula(image_path)
                else:
                    latex = ""
                
                # 如果是回退模式且OCR结果太短，可能抓取了空白，丢弃
                if using_fallback and len(latex) < 3:
                     # print(f"[FormulaExtractorOCR] 丢弃无效OCR结果: {formula_id}")
                     if os.path.exists(image_path):
                         os.remove(image_path)
                     continue

                # 提取文本
                if formula_blocks:
                    text_parts = [self._extract_block_text(b) for b in formula_blocks]
                    text = " ".join(text_parts) + f" ({eq_num})"
                else:
                    # 回退模式下没有提取到文本块，使用LaTeX作为文本
                    text = f"{latex} ({eq_num})"
                
                # 提取上下文
                context = self._extract_context(blocks, eq_block_idx) # Use eq block idx for context
                
                formulas.append({
                    'formula_id': formula_id,
                    'page': page_num,
                    'bbox': list(merged_bbox),
                    'image_path': image_path,
                    'text': text.strip(),
                    'latex': latex,
                    'context': context,
                    'source': pdf_path
                })
        
        doc.close()
        self._save_cache() # 保存缓存
        print(f"[FormulaExtractorOCR] 提取完成: {len(formulas)} 个公式")
        return formulas
    
    def _get_fallback_bbox(self, eq_bbox: tuple, page_rect: fitz.Rect) -> Optional[tuple]:
        """
        获取视觉回退边界框
        当找不到文本块时，盲取编号左侧的区域
        """
        eq_x0, eq_y0, eq_x1, eq_y1 = eq_bbox
        
        # 定义搜索区域
        # 高度：稍微上下扩展一点 (如 +/- 10pt)
        # 宽度：从左页边距到编号左侧
        
        page_width = page_rect.width
        
        # 假设左边距 5pt (原来是50pt，太宽导致长公式被截断)
        margin_left = 5
        
        if eq_x0 < margin_left + 10: # 编号太靠左，没空间
            return None
            
        region_x0 = margin_left
        region_x1 = eq_x1 # 包含编号本身
        
        # 高度扩展
        height_padding = 20 # 上下扩展
        region_y0 = max(0, eq_y0 - height_padding)
        region_y1 = min(page_rect.height, eq_y1 + height_padding)
        
        # 如果是两栏布局(page_width > 500?), 可能需要更智能的左边界
        # 简单起见，如果编号在右半边，只取右半边的左边界
        if eq_x0 > page_width / 2:
            region_x0 = max(margin_left, page_width / 2)
            
        return (region_x0, region_y0, region_x1, region_y1)
    
    def _find_equation_numbers(
        self, 
        blocks: List[Dict], 
        page_width: float
    ) -> List[Dict]:
        """
        查找所有公式编号块
        
        Returns:
            [{'number': '3.114', 'block_idx': 16, 'bbox': [...]}]
        """
        equation_numbers = []
        
        for idx, block in enumerate(blocks):
            if block.get("type") != 0:
                continue
            
            text = self._extract_block_text(block)
            bbox = block.get("bbox")
            
            if not text or not bbox:
                continue
            
            # 查找形如 (3.114) 或 (1) 的编号
            # 更新: 支持没有点的纯数字编号，用于处理新文档
            match = re.match(r'^\s*\((\d+(?:\.\d+)?)\)\s*$', text)
            if not match:
                # 尝试 [1] 格式 (有些论文用方括号)
                match = re.match(r'^\s*\[(\d+(?:\.\d+)?)\]\s*$', text)
                if not match:
                    continue
            
            x0 = bbox[0]
            
            # 公式编号通常在右侧
            if page_width > 0 and x0 < page_width * 0.6:
                continue
            
            equation_numbers.append({
                'number': match.group(1),
                'block_idx': idx,
                'bbox': bbox,
                'text': text
            })
        
        return equation_numbers
    
    def _find_formula_content(
        self,
        blocks: List[Dict],
        eq_block_idx: int,
        eq_bbox: tuple,
        page_width: float
    ) -> List[Dict]:
        """
        查找公式编号左侧的公式内容
        
        策略:
        1. 查找与编号在同一行或相邻行的块
        2. 块的x坐标在编号左侧
        3. 包含数学特征
        """
        eq_y0, eq_y1 = eq_bbox[1], eq_bbox[3]
        eq_y_center = (eq_y0 + eq_y1) / 2
        eq_x0 = eq_bbox[0]
        
        formula_blocks = []
        
        for idx, block in enumerate(blocks):
            if block.get("type") != 0:
                continue
            
            if idx >= eq_block_idx:  # 只看编号之前的块
                continue
            
            bbox = block.get("bbox")
            if not bbox:
                continue
            
            x0, y0, x1, y1 = bbox
            y_center = (y0 + y1) / 2
            
            # 检查是否在同一行或相邻行 (放宽条件: y中心距离 < 60)
            y_distance = abs(y_center - eq_y_center)
            if y_distance > 60:
                continue
            
            # 检查是否在编号左侧或略微重叠
            if x0 >= eq_x0:
                continue
            
            text = self._extract_block_text(block)
            
            # 检查数学特征
            if self._has_math_features(text):
                formula_blocks.append({
                    'idx': idx,
                    'bbox': bbox,
                    'text': text,
                    'block': block
                })
        
        # 按x坐标排序(从左到右)
        formula_blocks.sort(key=lambda b: b['bbox'][0])
        
        return formula_blocks
    
    def _has_math_features(self, text: str) -> bool:
        """检查文本是否包含数学特征 (放宽条件)"""
        if not text or len(text) < 2:
            return False
        
        # 排除参考文献
        if re.match(r'^\s*\d+\.\s+[A-Z]', text):
            return False
        
        if any(kw in text for kw in ['IEEE', 'J.', 'Circuits', 'Trans.', 'Proc.', 'pp.', 'vol.']):
            return False
        
        # 数学特征 (放宽)
        math_symbols = ['≈', '×', '÷', '/', '=', '∫', '∑', '±', '→']
        has_symbol = any(s in text for s in math_symbols)
        
        # 下标 (如 R_S1, C_L)
        has_subscript = bool(re.search(r'[A-Z][A-Z_]*\s*[₀₁₂₃₄₅₆₇₈₉]|[A-Z]\s*S\d|[A-Z]_[A-Z0-9]', text))
        
        # 变量模式 (如 "resistors R S1, R S2")
        has_variables = bool(re.search(r'\b[A-Z]\s+[A-Z]?\d+\b', text))
        
        return has_symbol or has_subscript or has_variables
    
    def _merge_bboxes(self, bboxes: List[tuple]) -> tuple:
        """合并多个bbox"""
        if not bboxes:
            return (0, 0, 0, 0)
        
        x0 = min(b[0] for b in bboxes)
        y0 = min(b[1] for b in bboxes)
        x1 = max(b[2] for b in bboxes)
        y1 = max(b[3] for b in bboxes)
        
        return (x0, y0, x1, y1)
    
    def _extract_block_text(self, block: Dict) -> str:
        """从文本块中提取文本"""
        text = ""
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text += span.get("text", "") + " "
        return text.strip()
    
    def _render_formula_region(
        self, 
        page, 
        bbox: tuple, 
        formula_id: str
    ) -> Optional[str]:
        """渲染公式区域为高清图像"""
        try:
            # 扩展边界框
            x0, y0, x1, y1 = bbox
            width = x1 - x0
            height = y1 - y0
            margin = 0.15
            
            clip_rect = fitz.Rect(
                max(0, x0 - width * margin),
                max(0, y0 - height * margin),
                x1 + width * margin,
                y1 + height * margin
            )
            
            # 高分辨率渲染 -> 降低分辨率以提升速度 (300dpi -> ~144dpi)
            # 2.0倍缩放，配合后续的max_dim限制
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat, clip=clip_rect)
            
            # 保存图像
            image_path = os.path.join(self.output_dir, f"{formula_id}.png")
            pix.save(image_path)
            
            return image_path
            
            return image_path
            
        except Exception as e:
            print(f"[FormulaExtractorOCR] 渲染公式失败 ({formula_id}): {e}")
            return None
    
    def _ocr_formula(self, image_path: str) -> str:
        """使用Pix2Text OCR识别公式 (带缓存 + 图像缩放优化)"""
        if not self.p2t:
            return ""
        
        filename = os.path.basename(image_path)
        if filename in self.ocr_cache:
            return self.ocr_cache[filename]
        
        try:
            # 性能优化: 如果图片过大，先缩小
            # Pix2Text在处理大图时极其缓慢(尤其是CPU模式)
            from PIL import Image
            
            with Image.open(image_path) as img:
                w, h = img.size
                max_dim = 800 # 限制最大边长为800px (对于公式识别通常足够)
                
                if w > max_dim or h > max_dim:
                    scale = max_dim / max(w, h)
                    new_w = int(w * scale)
                    new_h = int(h * scale)
                    # print(f"[FormulaExtractorOCR] 缩放过大图片: {w}x{h} -> {new_w}x{new_h}")
                    img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    result = self.p2t.recognize_formula(img_resized)
                else:
                    result = self.p2t.recognize_formula(img)
            
            if isinstance(result, dict):
                latex = result.get('text', result.get('latex', ''))
            else:
                latex = str(result)
            
            clean_latex = latex.strip()
            # 更新缓存
            self.ocr_cache[filename] = clean_latex
            return clean_latex
            
        except Exception as e:
            print(f"[FormulaExtractorOCR] OCR识别失败 ({os.path.basename(image_path)}): {e}")
            return ""
    
    def _extract_context(self, blocks: List[Dict], current_idx: int) -> str:
        """提取公式的上下文"""
        if current_idx > 0:
            prev_block = blocks[current_idx - 1]
            if prev_block.get("type") == 0:
                text = self._extract_block_text(prev_block)
                sentences = text.split('。')
                if sentences:
                    return sentences[-1].strip()[:100]
        
        if current_idx + 1 < len(blocks):
            next_block = blocks[current_idx + 1]
            if next_block.get("type") == 0:
                text = self._extract_block_text(next_block)
                sentences = text.split('。')
                if sentences:
                    return sentences[0].strip()[:100]
        
        return ""


if __name__ == "__main__":
    # 测试代码
    extractor = FormulaExtractorOCR()
    
    test_pdf = "./documents/LDO.pdf"
    if os.path.exists(test_pdf):
        formulas = extractor.extract_formulas(test_pdf)
        print(f"\n提取结果 (前10个):")
        for eq in formulas[:10]:
            print(f"\n  - {eq['formula_id']}:")
            print(f"    文本: {eq['text'][:60]}...")
            print(f"    LaTeX: {eq['latex'][:80]}...")
    else:
        print(f"测试PDF不存在: {test_pdf}")
