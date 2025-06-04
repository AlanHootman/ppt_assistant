#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2024 deadwalk
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Agent基类模块

定义所有Agent的共同接口和基本功能。
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, TYPE_CHECKING

# 使用TYPE_CHECKING避免循环导入
if TYPE_CHECKING:
    from core.engine.state import AgentState

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Agent基类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化Agent
        
        Args:
            config: Agent配置
        """
        self.config = config
        self.name = self.__class__.__name__
        logger.info(f"初始化Agent: {self.name}")
    
    @abstractmethod
    async def run(self, state: "AgentState") -> "AgentState":
        """
        执行Agent的主要逻辑
        
        Args:
            state: 当前工作流状态
            
        Returns:
            更新后的状态
        """
        pass
    
    def add_checkpoint(self, state: "AgentState", checkpoint_name: Optional[str] = None) -> None:
        """
        添加检查点，标记Agent执行完成
        
        Args:
            state: 当前工作流状态
            checkpoint_name: 检查点名称，默认为{agent名称}_completed
        """
        name = checkpoint_name or f"{self.name}_completed"
        state.add_checkpoint(name)
        logger.debug(f"添加检查点: {name}")
    
    def record_failure(self, state: "AgentState", error_message: str) -> None:
        """
        记录执行失败信息
        
        Args:
            state: 当前工作流状态
            error_message: 错误信息
        """
        state.record_failure(f"{self.name}: {error_message}")
        logger.error(f"Agent执行失败: {self.name} - {error_message}") 