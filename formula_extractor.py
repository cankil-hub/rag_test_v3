"""
PDF公式提取器
识别和提取数学公式,并渲染为高清图像
"""
import fitz  # PyMuPDF
from typing import List, Dict, Optional
import os
import re


class FormulaExtractor:
    """PDF公式提取器"""
    
    def __init__(self, output_dir: str = "./data_base_v3/formulas"):
        """
        初始化公式提取器
        
        Args:
            output_dir: 公式图片输出目录
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        print(f"[FormulaExtractor] 初始化完成, 输出目录: {output_dir}")
    
    def extract_formulas(self, pdf_path: str) -> List[Dict]:
        """
        提取PDF中的公式
        
        策略:
        1. 基于文本特征识别公式区域(包含=, ∫, Σ等符号)
        2. 渲染该区域为高清图像
        3. 保存公式文本和上下文
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            公式元数据列表:
            {
                'formula_id': 'doc1_eq_p10_b5',
                'page': 10,
                'bbox': [x0, y0, x1, y1],
                'image_path': '/path/to/doc1_eq_p10_b5.png',
                'text': 'V_ripple = I_out / (8*f*C)',
                'context': '输出纹波电压可表示为:',
                'source': '/path/to/doc1.pdf'
            }
        """
        if not os.path.exists(pdf_path):
            print(f"[FormulaExtractor] PDF文件不存在: {pdf_path}")
            return []
        
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            print(f"[FormulaExtractor] 打开PDF失败: {pdf_path}, 错误: {e}")
            return []
        
        formulas = []
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        
        print(f"[FormulaExtractor] 开始提取: {pdf_path} (共{len(doc)}页)")
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # 获取页面文本块
            try:
                blocks = page.get_text("dict")["blocks"]
            except Exception as e:
                print(f"[FormulaExtractor] 获取文本块失败 (页{page_num}): {e}")
                continue
            
            for block_idx, block in enumerate(blocks):
                # 跳过图像块
                if block.get("type") != 0:
                    continue
                
                # 提取文本
                text = self._extract_block_text(block)
                
                # 判断是否为公式
                if not text or not self._is_formula(text):
                    continue
                
                # 获取边界框
                bbox = block.get("bbox")
                if not bbox:
                    continue
                
                # 生成公式ID
                formula_id = f"{base_name}_eq_p{page_num}_b{block_idx}"
                
                # 渲染公式区域为图像
                image_path = self._render_formula_region(page, bbox, formula_id)
                
                if not image_path:
                    continue
                
                # 提取上下文(前一个文本块)
                context = self._extract_context(blocks, block_idx)
                
                formulas.append({
                    'formula_id': formula_id,
                    'page': page_num,
                    'bbox': list(bbox),
                    'image_path': image_path,
                    'text': text.strip(),
                    'context': context,
                    'source': pdf_path
                })
        
        doc.close()
        print(f"[FormulaExtractor] 提取完成: {len(formulas)} 个公式")
        return formulas
    
    def _extract_block_text(self, block: Dict) -> str:
        """从文本块中提取文本"""
        text = ""
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text += span.get("text", "") + " "
        return text.strip()
    
    def _is_formula(self, text: str) -> bool:
        """
        判断文本块是否为公式
        
        使用多种启发式规则:
        1. 包含等号且较短
        2. 包含数学符号
        3. 包含分数形式
        4. 包含上下标标记
        """
        # 规则1: 包含等号且长度适中(避免普通句子)
        if '=' in text and 10 < len(text) < 200:
            # 检查是否有数学特征
            # 包含变量(单个大写字母或带下标)
            if re.search(r'\b[A-Z]\b|[A-Za-z]_[A-Za-z0-9]', text):
                return True
        
        # 规则2: 包含数学符号
        math_symbols = ['∫', '∑', '∏', '√', '∂', '∇', '≈', '≤', '≥', '±', '×', '÷', '∞', 'π', 'Δ', 'α', 'β', 'γ', 'θ', 'ω']
        if any(sym in text for sym in math_symbols):
            return True
        
        # 规则3: 包含分数形式(如"V/R", "1/2C")
        if re.search(r'[A-Za-z0-9]+\s*/\s*[A-Za-z0-9]+', text):
            # 排除日期(如"2024/12/08")
            if not re.search(r'\d{4}/\d{1,2}/\d{1,2}', text):
                return True
        
        # 规则4: 包含上下标标记(如"V_out", "x^2")
        if re.search(r'[A-Za-z]_[A-Za-z0-9]|[A-Za-z]\^[0-9]', text):
            return True
        
        # 规则5: 包含括号且有数学运算符
        if '(' in text and ')' in text:
            if any(op in text for op in ['+', '-', '*', '/', '=']):
                # 检查是否有变量
                if re.search(r'\b[A-Z]\b', text):
                    return True
        
        # 规则6: 短文本且包含多个数学运算符
        if len(text) < 100:
            op_count = sum(text.count(op) for op in ['+', '-', '*', '/', '='])
            if op_count >= 2:
                return True
        
        return False
    
    def _render_formula_region(
        self, 
        page, 
        bbox: tuple, 
        formula_id: str
    ) -> Optional[str]:
        """
        渲染公式区域为高清图像
        
        Args:
            page: PyMuPDF页面对象
            bbox: 边界框 (x0, y0, x1, y1)
            formula_id: 公式ID
            
        Returns:
            图片路径或None
        """
        try:
            # 扩展边界框(增加15%边距,确保公式完整)
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
            
            # 高分辨率渲染(300 DPI,确保公式清晰)
            mat = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=mat, clip=clip_rect)
            
            # 保存图像
            image_path = os.path.join(self.output_dir, f"{formula_id}.png")
            pix.save(image_path)
            
            return image_path
            
        except Exception as e:
            print(f"[FormulaExtractor] 渲染公式失败 ({formula_id}): {e}")
            return None
    
    def _extract_context(self, blocks: List[Dict], current_idx: int) -> str:
        """
        提取公式的上下文(前一个文本块)
        
        Args:
            blocks: 所有文本块
            current_idx: 当前公式块索引
            
        Returns:
            上下文文本
        """
        # 尝试获取前一个文本块
        if current_idx > 0:
            prev_block = blocks[current_idx - 1]
            if prev_block.get("type") == 0:  # 文本块
                text = self._extract_block_text(prev_block)
                # 取最后一句作为上下文
                sentences = text.split('。')
                if sentences:
                    return sentences[-1].strip()[:100]
        
        # 尝试获取后一个文本块
        if current_idx + 1 < len(blocks):
            next_block = blocks[current_idx + 1]
            if next_block.get("type") == 0:
                text = self._extract_block_text(next_block)
                sentences = text.split('。')
                if sentences:
                    return sentences[0].strip()[:100]
        
        return ""
    
    def extract_formulas_batch(self, pdf_dir: str) -> Dict[str, List[Dict]]:
        """
        批量提取目录下所有PDF的公式
        
        Args:
            pdf_dir: PDF文件目录
            
        Returns:
            {pdf_path: [formulas]}
        """
        results = {}
        
        for root, _, files in os.walk(pdf_dir):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_path = os.path.join(root, file)
                    formulas = self.extract_formulas(pdf_path)
                    results[pdf_path] = formulas
        
        total_formulas = sum(len(eqs) for eqs in results.values())
        print(f"[FormulaExtractor] 批量提取完成: {len(results)} 个PDF, 共 {total_formulas} 个公式")
        
        return results


if __name__ == "__main__":
    # 测试代码
    extractor = FormulaExtractor()
    
    # 测试单个PDF
    test_pdf = "./documents/test.pdf"  # 替换为实际路径
    if os.path.exists(test_pdf):
        formulas = extractor.extract_formulas(test_pdf)
        print(f"\n提取结果:")
        for eq in formulas:
            print(f"  - {eq['formula_id']}:")
            print(f"    文本: {eq['text'][:80]}...")
            print(f"    上下文: {eq['context'][:60]}...")
    else:
        print(f"测试PDF不存在: {test_pdf}")
        print("请将PDF文件放在 ./documents/ 目录下进行测试")
