import os
import shutil
import uuid
from pathlib import Path
from typing import Optional, Dict
from fastapi import UploadFile
from apps.api.config import settings

class FileService:
    """文件管理服务，处理模板文件和生成的PPT文件"""
    
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        self.static_dir = settings.STATIC_DIR
        self.templates_dir = self.static_dir / "templates"
        self.outputs_dir = self.static_dir / "output"
        
        # 确保目录存在
        for dir_path in [self.upload_dir, self.templates_dir, self.outputs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    async def save_template_file(self, file: UploadFile, template_id: int) -> Dict[str, str]:
        """保存模板文件
        
        Args:
            file: 上传的模板文件
            template_id: 模板ID
            
        Returns:
            包含文件路径和目录路径的字典
        """
        # 创建模板目录
        template_dir = self.templates_dir / str(template_id)
        template_dir.mkdir(exist_ok=True)
        
        # 保存原始文件
        file_path = template_dir / "template.pptx"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "file_path": str(file_path),
            "template_dir": str(template_dir)
        }
    
    def delete_template_files(self, template_id: int) -> bool:
        """删除模板相关文件
        
        Args:
            template_id: 模板ID
            
        Returns:
            是否成功删除
        """
        template_dir = self.templates_dir / str(template_id)
        if template_dir.exists():
            shutil.rmtree(template_dir)
            return True
        return False
    
    def get_template_file_path(self, template_id: int) -> Optional[str]:
        """获取模板文件路径
        
        Args:
            template_id: 模板ID
            
        Returns:
            模板文件路径，如果不存在则返回None
        """
        file_path = self.templates_dir / str(template_id) / "template.pptx"
        return str(file_path) if file_path.exists() else None
    
    def get_template_preview_path(self, template_id: int, slide_index: int = 0) -> Optional[str]:
        """获取模板预览图路径
        
        Args:
            template_id: 模板ID
            slide_index: 幻灯片索引
            
        Returns:
            预览图路径，如果不存在则返回None
        """
        preview_path = self.templates_dir / str(template_id) / f"preview_{slide_index}.png"
        return str(preview_path) if preview_path.exists() else None
    
    def create_task_output_dir(self, task_id: str) -> str:
        """创建任务输出目录
        
        Args:
            task_id: 任务ID
            
        Returns:
            输出目录路径
        """
        output_dir = self.outputs_dir / task_id
        output_dir.mkdir(parents=True, exist_ok=True)
        return str(output_dir)
    
    def get_task_file_path(self, task_id: str, filename: str) -> Optional[str]:
        """获取任务文件路径
        
        Args:
            task_id: 任务ID
            filename: 文件名
            
        Returns:
            文件路径，如果不存在则返回None
        """
        file_path = self.outputs_dir / task_id / filename
        return str(file_path) if file_path.exists() else None
    
    def get_task_preview_images(self, task_id: str) -> list:
        """获取任务预览图列表
        
        Args:
            task_id: 任务ID
            
        Returns:
            预览图URL列表
        """
        output_dir = self.outputs_dir / task_id
        if not output_dir.exists():
            return []
        
        preview_images = []
        for file in output_dir.glob("preview_*.png"):
            # 将文件路径转换为URL路径
            url_path = f"/static/output/{task_id}/{file.name}"
            preview_images.append(url_path)
        
        # 按照幻灯片索引排序
        preview_images.sort(key=lambda x: int(x.split("preview_")[1].split(".")[0]))
        return preview_images 