# PPT 管理器

这是一个用于加载、解析、编辑和导出PowerPoint (PPTX) 文件的Python库。

## 功能

- PPTX文件管理功能
  - 加载PPTX文件并提取详细信息
  - 将演示文稿转换为JSON结构化数据
  - 获取幻灯片布局(Layout)信息
  - 解析幻灯片元素和元数据
- PPTX文件渲染功能
  - 将幻灯片渲染为高质量图片(PNG、JPG)
  - 支持单页或整份文档渲染
- PPTX文件幻灯片编辑功能
  - 基于布局创建新幻灯片
  - 复制现有幻灯片
  - 删除单个或批量幻灯片
- PPTX文件幻灯片-文本编辑功能
  - 精确定位和修改文本元素
  - 调整文本字体大小
- PPTX文件幻灯片-图片编辑功能
  - 获取幻灯片中的图片元素
  - 替换幻灯片中的图片
  - 为图片添加备注信息

## 快速开始

### 安装依赖

```bash
# 从项目目录安装
pip install -e .
```

安装soffice组件

```bash
# 安装soffice组件
brew install soffice
```

安装pdf2image组件

```bash
# 安装pdf2image组件
pip install pdf2image
```

### 代码实现

PPT管理器提供了以下接口，方便用户快速实现常见功能。

### 1. PPTX文件管理功能
#### 1.1 获取整个演示文稿的JSON结构
将PPTX文件转换为JSON格式，方便进行结构化分析和处理。

```python
from interfaces.ppt_api import PPTManager

# 初始化PPT管理器
ppt_manager = PPTManager()

# 这种方式可以重复使用已加载的演示文稿，而不需要多次读取文件
presentation = ppt_manager.load_presentation("path/to/your/presentation.pptx")
ppt_json = ppt_manager.get_presentation_json(
    presentation=presentation,
    include_details=True  # 是否包含元素详细信息
)

# 输出基本信息
print(f"演示文稿宽度: {ppt_json['width']}, 高度: {ppt_json['height']}")
print(f"幻灯片数量: {ppt_json['slide_count']}")
print(f"元数据-标题: {ppt_json['metadata'].get('title', '无标题')}")
```

#### 1.2 获取指定幻灯片的JSON结构

```python
presentation = ppt_manager.load_presentation("path/to/your/presentation.pptx")
slide_json = ppt_manager.get_slide_json(
    presentation=presentation,
    slide_index=0  # 第一张幻灯片，索引从0开始
)

print(f"幻灯片标题: {slide_json['title']}")
print(f"元素数量: {slide_json['element_count']}")

# 获取所有幻灯片的JSON结构
all_slides_json = ppt_manager.get_slide_json(
    presentation=presentation,
    slide_index=None  # None表示获取所有幻灯片
)

for i, slide in enumerate(all_slides_json):
    print(f"幻灯片 {i+1} 标题: {slide['title']}")
```

#### 1.3 获取PPT中模板中的所有Layout
通过PresentationModel对象，获取PPTX文件中的所有Layout，并输出为JSON格式。
入参：PresentationModel对象
返回：PPTX文件中的所有Layout信息，以Json格式返回

```python
from interfaces.ppt_api import PPTManager

# 初始化PPT管理器
ppt_manager = PPTManager()

presentation = ppt_manager.load_presentation("path/to/your/presentation.pptx")
layouts_json = ppt_manager.get_layouts_json(presentation)
```

#### 1.4 获取指定幻灯片的Layout
入参：slide_id
返回：指定幻灯片的Layout信息，以Json格式返回

```python
from interfaces.ppt_api import PPTManager

# 初始化PPT管理器
ppt_manager = PPTManager()

presentation = ppt_manager.load_presentation("path/to/your/presentation.pptx")

# 获取幻灯片的ID
slide_id = "slide-001"

# 获取指定幻灯片的Layout信息
layout_json = ppt_manager.get_slide_layout_json(presentation, slide_id)

```

### 2. PPTX文件渲染显示功能
#### 2.1 渲染所有幻灯片为图片

将PPT幻灯片渲染为高质量图片，支持渲染指定页或全部页面。

```python
from interfaces.ppt_api import PPTManager

# 初始化PPT管理器
ppt_manager = PPTManager()

# 方法1: 渲染所有幻灯片 - 从文件路径
image_files = ppt_manager.render_pptx_file(
    pptx_path="path/to/your/presentation.pptx",
    output_dir="output/images",
    format="png"  # 支持"png"、"jpg"、"pdf"
)

print(f"共渲染 {len(image_files)} 张幻灯片图片:")
for img_file in image_files:
    print(f"  - {os.path.basename(img_file)}")

# 方法2: 渲染所有幻灯片 - 从已加载的演示文稿
presentation = ppt_manager.load_presentation("path/to/your/presentation.pptx")
image_files = ppt_manager.render_presentation(
    presentation=presentation,
    output_dir="output/images",
    format="png"  # 支持"png"、"jpg"、"pdf"
)
```

#### 2.2 渲染指定幻灯片为图片

```python
# 方法1: 从文件路径渲染指定幻灯片
image_paths = ppt_manager.render_pptx_file(
    pptx_path="path/to/your/presentation.pptx",
    output_dir="output/images",
    slide_index=2,  # 索引为2的幻灯片（第3张）
    format="png"
)

# 方法2: 从已加载的演示文稿渲染指定幻灯片
presentation = ppt_manager.load_presentation("path/to/your/presentation.pptx")
image_paths = ppt_manager.render_presentation(
    presentation=presentation,
    output_dir="output/images",
    slide_index=2,  # 索引为2的幻灯片（第3张）
    format="png"
)

if image_paths:
    print(f"已渲染指定幻灯片: {os.path.basename(image_paths[0])}")
else:
    print("未成功渲染指定幻灯片")
```

### 3. PPTX文件幻灯片编辑功能
#### 3.1 根据Layout创建新的幻灯片

```python
from interfaces.ppt_api import PPTManager

# 初始化PPT管理器
ppt_manager = PPTManager()

# 首先加载演示文稿
presentation = ppt_manager.load_presentation("path/to/your/presentation.pptx")

# 可选：获取并查看可用的layout
layouts_json = ppt_manager.get_layouts_json(presentation)
print("可用的layout名称：")
for master in layouts_json:
    for layout in master["layouts"]:
        print(f"- {layout['layout_name']}")

# 使用指定layout创建新的幻灯片（添加到末尾）
result = ppt_manager.create_slide_with_layout(
    presentation=presentation,
    layout_name="Title Slide",  # 使用您需要的layout名称
    insert_position=-1  # -1表示添加到末尾
)

if result["success"]:
    print(f"成功创建幻灯片，ID: {result['slide_id']}, 位置: {result['real_index']}")
    # 更新presentation变量为返回的presentation对象
    # 这一步是必须的，确保presentation.slides包含新创建的幻灯片
    presentation = result["presentation"]
else:
    print(f"创建幻灯片失败: {result['message']}")
```

#### 3.2 复制幻灯片

```python
from interfaces.ppt_api import PPTManager

# 初始化PPT管理器
ppt_manager = PPTManager()

# 加载演示文稿
presentation = ppt_manager.load_presentation("path/to/your/presentation.pptx")

# 获取要复制的幻灯片ID（例如第三张幻灯片）
source_slide_id = presentation.slides[2].slide_id

# 复制幻灯片到末尾
duplicate_result = ppt_manager.duplicate_slide_by_id(
    presentation=presentation,
    slide_id=source_slide_id
)

if duplicate_result["success"]:
    print(f"成功复制幻灯片，新ID: {duplicate_result['slide_id']}")
    # 更新presentation对象
    presentation = duplicate_result["presentation"]
    
    # 保存修改后的演示文稿
    ppt_manager.save_presentation(presentation, "output.pptx")
else:
    print(f"复制幻灯片失败: {duplicate_result['message']}")

# 复制幻灯片到指定位置（第2张幻灯片之后）
insert_position = 1  # 索引从0开始，所以这是第2张幻灯片之后
duplicate_result = ppt_manager.duplicate_slide_by_id(
    presentation=presentation,
    slide_id=source_slide_id,
    insert_position=insert_position
)
```

#### 3.3 删除单个幻灯片

```python
from interfaces.ppt_api import PPTManager

# 初始化PPT管理器
ppt_manager = PPTManager()

# 加载演示文稿
presentation = ppt_manager.load_presentation("path/to/your/presentation.pptx")

# 获取要删除的幻灯片ID（例如第三张幻灯片）
slide_to_delete_id = presentation.slides[2].slide_id

# 删除幻灯片
delete_result = ppt_manager.delete_slide_by_id(
    presentation=presentation,
    slide_id=slide_to_delete_id
)

if delete_result["success"]:
    print(f"成功删除幻灯片，ID: {delete_result['deleted_slide_id']}")
    # 保存修改后的演示文稿
    ppt_manager.save_presentation(presentation, "output.pptx")
else:
    print(f"删除幻灯片失败: {delete_result['message']}")
```

#### 3.4 批量删除幻灯片

```python
from interfaces.ppt_api import PPTManager

# 初始化PPT管理器
ppt_manager = PPTManager()

# 加载演示文稿
presentation = ppt_manager.load_presentation("path/to/your/presentation.pptx")

# 方法1: 通过ID列表删除多个幻灯片
slide_ids_to_delete = [presentation.slides[1].slide_id, presentation.slides[3].slide_id]
delete_result = ppt_manager.delete_slides(
    presentation=presentation,
    slide_ids=slide_ids_to_delete
)

# 方法2: 通过索引范围删除多个幻灯片（删除第2-4张幻灯片）
delete_result = ppt_manager.delete_slides(
    presentation=presentation,
    start_index=1,  # 从0开始计数
    end_index=3
)

if delete_result["success"]:
    print(f"成功删除 {delete_result['deleted_count']} 张幻灯片")
    # 保存修改后的演示文稿
    ppt_manager.save_presentation(presentation, "output.pptx")
else:
    print(f"批量删除幻灯片失败: {delete_result['message']}")
```

### 4. PPTX文件幻灯片-文本编辑功能
#### 4.1 编辑幻灯片中的文本元素

```python
from interfaces.ppt_api import PPTManager

# 初始化PPT管理器
ppt_manager = PPTManager()

# 加载演示文稿
presentation = ppt_manager.load_presentation("path/to/your/presentation.pptx")

# 获取幻灯片和元素ID
slide_id = presentation.slides[0].slide_id  # 第一张幻灯片
# 假设我们要编辑标题元素
title_element = None
for element in presentation.slides[0].elements:
    if hasattr(element, "metadata") and element.metadata.get("shape_name", "").lower().startswith("title"):
        title_element = element
        break

if title_element:
    element_id = title_element.element_id
    # 编辑文本内容
    new_text = "这是新的标题文本"
    edit_result = ppt_manager.edit_text_element_by_id(
        presentation=presentation,
        slide_id=slide_id,
        element_id=element_id,
        new_text=new_text
    )
    
    if edit_result["success"]:
        print(f"成功编辑文本元素")
        # 保存修改后的演示文稿
        ppt_manager.save_presentation(presentation, "output.pptx")
    else:
        print(f"编辑文本元素失败: {edit_result['message']}")
```

#### 4.2 调整文本元素字体大小

```python
from interfaces.ppt_api import PPTManager

# 初始化PPT管理器
ppt_manager = PPTManager()

# 加载演示文稿
presentation = ppt_manager.load_presentation("path/to/your/presentation.pptx")

# 获取幻灯片和元素ID
slide_id = presentation.slides[0].slide_id  # 第一张幻灯片
# 假设我们要调整标题元素的字体大小
title_element = None
for element in presentation.slides[0].elements:
    if hasattr(element, "metadata") and element.metadata.get("shape_name", "").lower().startswith("title"):
        title_element = element
        break

if title_element:
    element_id = title_element.element_id
    # 调整字体大小为36磅
    new_font_size = 36
    adjust_result = ppt_manager.adjust_text_font_size(
        presentation=presentation,
        slide_id=slide_id,
        element_id=element_id,
        font_size=new_font_size
    )
    
    if adjust_result["success"]:
        print(f"成功调整文本元素字体大小")
        # 保存修改后的演示文稿
        ppt_manager.save_presentation(presentation, "output.pptx")
    else:
        print(f"调整字体大小失败: {adjust_result['message']}")
```

### 5. PPTX文件幻灯片-图片编辑功能
#### 5.1 获取幻灯片中的图片元素

```python
from interfaces.ppt_api import PPTManager

# 初始化PPT管理器
ppt_manager = PPTManager()

# 加载演示文稿
presentation = ppt_manager.load_presentation("path/to/your/presentation.pptx")

# 获取指定幻灯片ID中的所有图片元素
slide_id = presentation.slides[0].slide_id  # 第一张幻灯片
result = ppt_manager.get_image_elements_by_slide_id(
    presentation=presentation,
    slide_id=slide_id
)

if result["success"]:
    print(f"幻灯片中包含 {result['image_count']} 个图片元素:")
    for image in result["images"]:
        print(f"  - 图片ID: {image['element_id']}")
        print(f"    路径: {image['image_path']}")
        print(f"    位置: 左={image['position']['left']}, 上={image['position']['top']}, 宽={image['position']['width']}, 高={image['position']['height']}")
else:
    print(f"获取图片元素失败: {result['message']}")
```


#### 5.2 添加图片备注

```python
from interfaces.ppt_api import PPTManager

# 初始化PPT管理器
ppt_manager = PPTManager()

# 加载演示文稿
presentation = ppt_manager.load_presentation("path/to/your/presentation.pptx")

# 获取幻灯片ID和图片元素ID
slide_id = presentation.slides[2].slide_id  # 第三张幻灯片
# 假设我们要为第一个图片元素添加备注
image_elements = []
for element in presentation.slides[2].elements:
    if hasattr(element, "element_type") and element.element_type == ElementType.IMAGE:
        image_elements.append(element)

if image_elements:
    element_id = image_elements[0].element_id
    
    # 添加图片备注
    caption = "这是一张iPhone 16 Pro的产品图片"
    result = ppt_manager.add_image_caption(
        presentation=presentation,
        slide_id=slide_id,
        element_id=element_id,
        caption=caption
    )
    
    if result["success"]:
        print("成功添加图片备注")
        # 保存修改后的演示文稿
        ppt_manager.save_presentation(presentation, "output.pptx")
    else:
        print(f"添加图片备注失败: {result['message']}")
```

#### 5.3 替换幻灯片中的图片

```python
from interfaces.ppt_api import PPTManager

# 初始化PPT管理器
ppt_manager = PPTManager()

# 加载演示文稿
presentation = ppt_manager.load_presentation("path/to/your/presentation.pptx")

# 首先获取幻灯片中的图片元素
slide_id = presentation.slides[0].slide_id  # 第一张幻灯片
image_result = ppt_manager.get_image_elements_by_slide_id(
    presentation=presentation,
    slide_id=slide_id
)

if image_result["success"] and image_result["image_count"] > 0:
    # 找到一个图片元素
    element_id = image_result["images"][0]["element_id"]
    
    # 替换图片
    replace_result = ppt_manager.replace_image_by_element_id(
        presentation=presentation,
        slide_id=slide_id,
        element_id=element_id,
        image_path="path/to/new/image.jpg"  # 新图片路径
    )
    
    if replace_result["success"]:
        print(f"成功替换图片元素")
        # 保存修改后的演示文稿
        ppt_manager.save_presentation(presentation, "output.pptx")
    else:
        print(f"替换图片失败: {replace_result['message']}")
else:
    print(f"未找到图片元素")
```
