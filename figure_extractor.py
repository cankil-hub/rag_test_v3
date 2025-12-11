"""
PDF图片提取器
从PDF中识别和提取图片对象,并保存图片编号和元数据
"""
import fitz  # PyMuPDF
from typing import List, Dict, Optional
import os
from pathlib import Path
import hashlib


class FigureExtractor:
    """PDF图片提取器"""
    
    def __init__(self, output_dir: str = "./data_base_v3/figures"):
        """
        初始化图片提取器
        
        Args:
            output_dir: 图片输出目录
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        print(f"[FigureExtractor] 初始化完成, 输出目录: {output_dir}")
    
    def extract_figures(self, pdf_path: str) -> List[Dict]:
        """
        提取PDF中的所有图片
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            图片元数据列表, 每个元素包含:
            {
                'figure_id': 'doc1_fig_p5_i0',
                'page': 5,
                'bbox': [x0, y0, x1, y1],
                'image_path': '/path/to/doc1_fig_p5_i0.png',
                'caption': '图1.1 Buck变换器电路',
                'size_kb': 125,
                'source': '/path/to/doc1.pdf'
            }
        """
        if not os.path.exists(pdf_path):
            print(f"[FigureExtractor] PDF文件不存在: {pdf_path}")
            return []
        
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            print(f"[FigureExtractor] 打开PDF失败: {pdf_path}, 错误: {e}")
            return []
        
        figures = []
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        
        print(f"[FigureExtractor] 开始提取: {pdf_path} (共{len(doc)}页)")
        

        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # 1. 尝试提取常规位图图片
            image_list = page.get_images(full=True)
            page_figures = []
            
            for img_index, img_info in enumerate(image_list):
                xref = img_info[0]
                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    if not self._is_valid_figure(image_bytes, image_ext):
                        continue
                    
                    figure_id = f"{base_name}_fig_p{page_num}_i{img_index}"
                    image_path = os.path.join(self.output_dir, f"{figure_id}.{image_ext}")
                    
                    with open(image_path, "wb") as f:
                        f.write(image_bytes)
                    
                    caption, caption_bbox = self._extract_caption_and_bbox(page, page_num)
                    # 简化的bbox逻辑，实际应该匹配图片位置
                    bbox = self._get_image_bbox(page, xref) 
                    
                    # 记录已找到的图片，避免重复
                    page_figures.append({
                        'figure_id': figure_id,
                        'page': page_num,
                        'bbox': bbox,
                        'image_path': image_path,
                        'caption': caption,
                        'size_kb': len(image_bytes) // 1024,
                        'source': pdf_path,
                        'ext': image_ext
                    })
                    
                except Exception as e:
                    print(f"[FigureExtractor] 提取图片失败 (页{page_num}, 索引{img_index}): {e}")
                    continue
            
            # 2. [新增] 矢量图检测与回退捕获
            # 如果页面上有 "Figure X.Y" 但没有提取到对应的位图，尝试截图
            vector_figures = self._extract_vector_figures(page, page_num, base_name, page_figures)
            page_figures.extend(vector_figures)
            
            figures.extend(page_figures)
        
        doc.close()
        print(f"[FigureExtractor] 提取完成: {len(figures)} 个有效图片")
        return figures

    def _extract_vector_figures(self, page, page_num, base_name, existing_figures):
        """试图捕获矢量插图(通过查找图注)"""
        vector_figs = []
        try:
            text_blocks = page.get_text("dict")["blocks"]
            pm = page.get_pixmap() # 用于获取页面尺寸
            page_height = pm.height
             
            # 查找所有可能是图注的块
            for block in text_blocks:
                if block.get("type") != 0: continue
                
                txt = " ".join([s["text"] for l in block["lines"] for s in l["spans"]]).strip()
                
                # 简单正则匹配 "Figure X.Y" 或 "Fig. X.Y" 或 仅仅 "X.Y" (如果它是独立的)
                import re
                # 匹配:
                # 1. (Figure|Fig.) + 数字
                # 2. 纯数字 X.Y (且没有括号包围，避免匹配公式)
                is_caption = False
                # 严格模式: 只匹配 Figure 开头的标注
                # 必须以 Figure 或 Fig 开头
                if re.match(r'^(Figure|Fig\.?)\s+\d+', txt, re.IGNORECASE):
                    # 排除可能是正文句子的误判 (例如 "Figure 1 shows that...")
                    # 简单策略: 如果包含 "shows", "demonstrates" 等动词，且长度超过一定限制，可能不是图注
                    # 但很多图注也包含 these verbs.
                    # 更好的策略: 检查 content 的位置 (通常居中?) 
                    # 暂时保留基础匹配，移除纯数字匹配
                    is_caption = True
                
                if is_caption:
                    # 找到了潜在图注
                    # 检查是否已经覆盖了 (简单的Y轴检查)
                    caption_y = block["bbox"][1]
                    
                    is_covered = False
                    for fig in existing_figures:
                        # 如果已有图片在图注上方不远处(如 50px 内)，认为已覆盖
                        # 300太大了，会导致堆叠的图片被误判
                        if fig['bbox']:
                            fig_y_bottom = fig['bbox'][3]
                            if 0 < (caption_y - fig_y_bottom) < 50:
                                is_covered = True
                                break
                    
                    if not is_covered:
                        # 未覆盖，认为是矢量图，执行区域截图
                        # print(f"[FigureExtractor] 发现潜在矢量图: {txt} (页{page_num})")
                        
                        # 定义捕获区域：图注上方 300pt (或者直到页面顶部/上一个文本块)
                        # 简化策略: 图注上方 10pt 到 300pt 范围，且不超出页面
                        scan_height = 300
                        y1 = max(0, block["bbox"][1] - 5) # 图注上方留点空隙
                        y0 = max(0, y1 - scan_height)
                        x0 = 50 # 假设左边距
                        x1 = page.rect.width - 50 # 假设右边距
                        
                        capture_bbox = (x0, y0, x1, y1)
                        
                        fig_id = f"{base_name}_vec_p{page_num}_{len(existing_figures) + len(vector_figs)}"
                        
                        # 渲染
                        image_path = self._render_region(page, capture_bbox, fig_id)
                        
                        if image_path:
                            vector_figs.append({
                                'figure_id': fig_id,
                                'page': page_num,
                                'bbox': list(capture_bbox),
                                'image_path': image_path,
                                'caption': txt,
                                'size_kb': os.path.getsize(image_path) // 1024,
                                'source': "", # 外部填
                                'ext': "png",
                                'is_vector': True
                            })
        except Exception as e:
            print(f"[FigureExtractor] 矢量图检测失败: {e}")
            
        return vector_figs

    def _render_region(self, page, bbox, fig_id):
        """渲染指定区域"""
        try:
            mat = fitz.Matrix(2.0, 2.0) # 2倍缩放保证清晰度
            clip = fitz.Rect(bbox)
            pix = page.get_pixmap(matrix=mat, clip=clip)
            
            # 过滤空白图
            # if pix.n < 4: ... (简单跳过)
            
            image_path = os.path.join(self.output_dir, f"{fig_id}.png")
            pix.save(image_path)
            return image_path
        except Exception:
            return None

    def _extract_caption_and_bbox(self, page, page_num):
        """保留原 _extract_caption 逻辑，改个名适配调用"""
        return self._extract_caption(page, page_num), None
    
    def _is_valid_figure(self, image_bytes: bytes, image_ext: str) -> bool:
        """
        验证图片是否有效(过滤小图标、低质量图片)
        
        Args:
            image_bytes: 图片字节数据
            image_ext: 图片扩展名
            
        Returns:
            是否为有效图片
        """
        # 过滤1: 文件大小(小于10KB可能是图标)
        size_kb = len(image_bytes) // 1024
        if size_kb < 10:
            return False
        
        # 过滤2: 尝试打开图片检查尺寸
        try:
            from PIL import Image
            import io
            
            img = Image.open(io.BytesIO(image_bytes))
            
            # 过滤3: 尺寸太小(可能是图标)
            if img.width < 100 or img.height < 100:
                return False
            
            # 过滤4: 纵横比异常(可能是装饰线)
            aspect_ratio = img.width / img.height
            if aspect_ratio > 10 or aspect_ratio < 0.1:
                return False
            
            # 过滤5: 信息熵太低(可能是空白或纯色)
            import numpy as np
            arr = np.array(img.convert('L'))  # 转为灰度
            if arr.var() < 100:  # 方差太小说明颜色单一
                return False
            
            return True
            
        except Exception as e:
            # 如果无法用PIL打开,保守起见保留
            print(f"[FigureExtractor] 图片验证警告: {e}")
            return size_kb >= 20  # 至少20KB
    
    def _extract_caption(self, page, page_num: int) -> str:
        """
        提取图注(启发式方法)
        查找包含"图X.X"或"Figure X.X"的文本块
        
        Args:
            page: PyMuPDF页面对象
            page_num: 页码
            
        Returns:
            图注文本
        """
        try:
            text = page.get_text()
            lines = text.split('\n')
            
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                
                # 匹配中文图注: "图1.1", "图 1-1", "图1.1:"
                if '图' in line_stripped:
                    # 检查是否包含数字
                    if any(c.isdigit() for c in line_stripped):
                        # 取当前行+下一行作为完整图注
                        caption = line_stripped
                        if i + 1 < len(lines):
                            next_line = lines[i + 1].strip()
                            # 如果下一行不是新的图注,则合并
                            if next_line and not next_line.startswith('图'):
                                caption += " " + next_line
                        return caption[:200]  # 限制长度
                
                # 匹配英文图注: "Figure 1.1", "Fig. 1-1", "Fig 1.1:"
                if any(keyword in line_stripped for keyword in ['Figure', 'Fig.', 'Fig ']):
                    if any(c.isdigit() for c in line_stripped):
                        caption = line_stripped
                        if i + 1 < len(lines):
                            next_line = lines[i + 1].strip()
                            if next_line and not any(kw in next_line for kw in ['Figure', 'Fig']):
                                caption += " " + next_line
                        return caption[:200]
            
            return ""
            
        except Exception as e:
            print(f"[FigureExtractor] 提取图注失败 (页{page_num}): {e}")
            return ""
    
    def _get_image_bbox(self, page, xref: int) -> Optional[List[float]]:
        """
        获取图片在页面中的边界框
        
        Args:
            page: PyMuPDF页面对象
            xref: 图像引用ID
            
        Returns:
            [x0, y0, x1, y1] 或 None
        """
        try:
            # 获取所有图像位置信息
            image_list = page.get_images(full=True)
            
            for img_info in image_list:
                if img_info[0] == xref:
                    # 尝试获取图像的显示矩形
                    # 注意: PyMuPDF可能不总是能准确获取位置
                    # 这里返回一个占位值,实际应用中可能需要更复杂的逻辑
                    return None  # 暂时返回None,后续可优化
            
            return None
            
        except Exception:
            return None
    
    def extract_figures_batch(self, pdf_dir: str) -> Dict[str, List[Dict]]:
        """
        批量提取目录下所有PDF的图片
        
        Args:
            pdf_dir: PDF文件目录
            
        Returns:
            {pdf_path: [figures]}
        """
        results = {}
        
        for root, _, files in os.walk(pdf_dir):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_path = os.path.join(root, file)
                    figures = self.extract_figures(pdf_path)
                    results[pdf_path] = figures
        
        total_figures = sum(len(figs) for figs in results.values())
        print(f"[FigureExtractor] 批量提取完成: {len(results)} 个PDF, 共 {total_figures} 个图片")
        
        return results


if __name__ == "__main__":
    # 测试代码
    extractor = FigureExtractor()
    
    # 测试单个PDF
    test_pdf = "./documents/test.pdf"  # 替换为实际路径
    if os.path.exists(test_pdf):
        figures = extractor.extract_figures(test_pdf)
        print(f"\n提取结果:")
        for fig in figures:
            print(f"  - {fig['figure_id']}: {fig['caption'][:50]}... ({fig['size_kb']}KB)")
    else:
        print(f"测试PDF不存在: {test_pdf}")
        print("请将PDF文件放在 ./documents/ 目录下进行测试")
