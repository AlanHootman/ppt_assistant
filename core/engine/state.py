"""
工作流状态管理模块
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import uuid
import json
from pathlib import Path
import logging

from config.settings import settings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentState(BaseModel):
    """工作流状态模型"""
    
    # 会话标识
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # 原始输入
    raw_md: Optional[str] = None
    ppt_template_path: Optional[str] = None
    
    # 处理结果 - 使用显式字典类型
    content_structure: Optional[Dict[str, Any]] = None
    layout_features: Optional[Dict[str, Any]] = None
    decision_result: Optional[Dict[str, Any]] = None
    ppt_file_path: Optional[str] = None
    
    # 运行状态
    current_node: Optional[str] = None
    failures: List[str] = Field(default_factory=list)  # 使用default_factory
    checkpoints: List[str] = Field(default_factory=list)  # 使用default_factory
    validation_attempts: int = 0
    
    def add_checkpoint(self, name: str) -> None:
        """添加检查点标记"""
        if self.checkpoints is None:
            self.checkpoints = []
        self.checkpoints.append(name)
        logger.info(f"Session {self.session_id}: Added checkpoint '{name}'")
    
    def record_failure(self, error: str) -> None:
        """记录失败信息"""
        if self.failures is None:
            self.failures = []
        self.failures.append(error)
        logger.error(f"Session {self.session_id}: Failure '{error}'")
    
    def save(self) -> None:
        """保存当前状态到文件系统"""
        session_dir = settings.SESSION_DIR / self.session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        state_file = session_dir / "state.json"
        with open(state_file, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))
        
        logger.info(f"Session {self.session_id}: State saved to {state_file}")
    
    @classmethod
    def load(cls, session_id: str) -> "AgentState":
        """从文件系统加载状态"""
        state_file = settings.SESSION_DIR / session_id / "state.json"
        
        if not state_file.exists():
            logger.warning(f"Session {session_id}: State file not found")
            return cls(session_id=session_id)
        
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        logger.info(f"Session {session_id}: State loaded from {state_file}")
        return cls(**data) 