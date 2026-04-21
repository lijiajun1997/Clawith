"""
Style-related functions for Word Document Server.
"""
from docx.shared import Pt
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn


def set_chinese_font(run, english_font="Arial", chinese_font="微软雅黑"):
    """
    为文本运行设置中英文字体。

    Args:
        run: 文本运行对象
        english_font: 英文字体名称
        chinese_font: 中文字体名称
    """
    # 设置西文字体
    run.font.name = english_font

    # 设置中文字体（东亚字体）
    run._element.rPr.rFonts.set(qn('w:eastAsia'), chinese_font)


def ensure_normal_style(doc):
    """
    确保 Normal 样式存在并设置合理的中英文字体。

    Args:
        doc: Document 对象
    """
    try:
        style = doc.styles['Normal']
        # 设置字体
        style.font.name = 'Arial'
        style.font.size = Pt(11)

        # 设置中文字体
        try:
            rPr = style._element.get_or_add_rPr()
            rFonts = rPr.get_or_add_rFonts()
            rFonts.set(qn('w:eastAsia'), '微软雅黑')
            rFonts.set(qn('w:ascii'), 'Arial')
            rFonts.set(qn('w:hAnsi'), 'Arial')
        except Exception:
            pass  # 如果设置失败，使用默认字体

    except KeyError:
        pass


def ensure_heading_style(doc):
    """
    Ensure Heading styles exist in the document with Chinese font support.

    Args:
        doc: Document object
    """
    # 字体大小映射
    font_sizes = {
        1: 18,
        2: 16,
        3: 14,
        4: 13,
        5: 12,
        6: 11,
        7: 11,
        8: 10,
        9: 10
    }

    for i in range(1, 10):  # Create Heading 1 through Heading 9
        style_name = f'Heading {i}'
        try:
            # Try to access the style to see if it exists
            style = doc.styles[style_name]

            # 更新现有样式的字体设置
            try:
                style.font.size = Pt(font_sizes[i])
                style.font.bold = True

                # 设置中英文字体
                rPr = style._element.get_or_add_rPr()
                rFonts = rPr.get_or_add_rFonts()
                rFonts.set(qn('w:eastAsia'), '微软雅黑')
                rFonts.set(qn('w:ascii'), 'Arial')
                rFonts.set(qn('w:hAnsi'), 'Arial')
            except Exception:
                pass

        except KeyError:
            # Create the style if it doesn't exist
            try:
                style = doc.styles.add_style(style_name, WD_STYLE_TYPE.PARAGRAPH)
                style.font.size = Pt(font_sizes[i])
                style.font.bold = True

                # 设置中英文字体
                try:
                    rPr = style._element.get_or_add_rPr()
                    rFonts = rPr.get_or_add_rFonts()
                    rFonts.set(qn('w:eastAsia'), '微软雅黑')
                    rFonts.set(qn('w:ascii'), 'Arial')
                    rFonts.set(qn('w:hAnsi'), 'Arial')
                except Exception:
                    pass

            except Exception:
                # If style creation fails, we'll just use default formatting
                pass


def ensure_table_style(doc):
    """
    Ensure Table Grid style exists in the document.
    
    Args:
        doc: Document object
    """
    try:
        # Try to access the style to see if it exists
        style = doc.styles['Table Grid']
    except KeyError:
        # If style doesn't exist, we'll handle it at usage time
        pass


def create_style(doc, style_name, style_type, base_style=None, font_properties=None, paragraph_properties=None):
    """
    Create a new style in the document.
    
    Args:
        doc: Document object
        style_name: Name for the new style
        style_type: Type of style (WD_STYLE_TYPE)
        base_style: Optional base style to inherit from
        font_properties: Dictionary of font properties (bold, italic, size, name, color)
        paragraph_properties: Dictionary of paragraph properties (alignment, spacing)
        
    Returns:
        The created style
    """
    from docx.shared import Pt
    
    try:
        # Check if style already exists
        style = doc.styles.get_by_id(style_name, WD_STYLE_TYPE.PARAGRAPH)
        return style
    except:
        # Create new style
        new_style = doc.styles.add_style(style_name, style_type)
        
        # Set base style if specified
        if base_style:
            new_style.base_style = doc.styles[base_style]
        
        # Set font properties
        if font_properties:
            font = new_style.font
            if 'bold' in font_properties:
                font.bold = font_properties['bold']
            if 'italic' in font_properties:
                font.italic = font_properties['italic']
            if 'size' in font_properties:
                font.size = Pt(font_properties['size'])
            if 'name' in font_properties:
                font.name = font_properties['name']
            if 'color' in font_properties:
                from docx.shared import RGBColor
                
                # Define common RGB colors
                color_map = {
                    'red': RGBColor(255, 0, 0),
                    'blue': RGBColor(0, 0, 255),
                    'green': RGBColor(0, 128, 0),
                    'yellow': RGBColor(255, 255, 0),
                    'black': RGBColor(0, 0, 0),
                    'gray': RGBColor(128, 128, 128),
                    'white': RGBColor(255, 255, 255),
                    'purple': RGBColor(128, 0, 128),
                    'orange': RGBColor(255, 165, 0)
                }
                
                color_value = font_properties['color']
                try:
                    # Handle string color names
                    if isinstance(color_value, str) and color_value.lower() in color_map:
                        font.color.rgb = color_map[color_value.lower()]
                    # Handle RGBColor objects
                    elif hasattr(color_value, 'rgb'):
                        font.color.rgb = color_value
                    # Try to parse as RGB string
                    elif isinstance(color_value, str):
                        font.color.rgb = RGBColor.from_string(color_value)
                    # Use directly if it's already an RGB value
                    else:
                        font.color.rgb = color_value
                except Exception as e:
                    # Fallback to black if all else fails
                    font.color.rgb = RGBColor(0, 0, 0)
        
        # Set paragraph properties
        if paragraph_properties:
            if 'alignment' in paragraph_properties:
                new_style.paragraph_format.alignment = paragraph_properties['alignment']
            if 'spacing' in paragraph_properties:
                new_style.paragraph_format.line_spacing = paragraph_properties['spacing']
        
        return new_style
