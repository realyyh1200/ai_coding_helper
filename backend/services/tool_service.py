import os
import traceback
from sqlalchemy.orm import Session
from models.user import User
from schemas.schema import SafePathCheckResponse
from typing import Dict, Any, Optional
from core.logger import logger


class ToolService:
    """工具服务类，提供各种可被LLM调用的工具"""

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self._user = None

    @property
    def user(self):
        if self._user is None:
            self._user = self.db.query(User).filter(User.id == self.user_id).first()
        return self._user

    def _estimate_token_count(self, text: str) -> int:
        """
        估算文本的token数量

        这里采用保守估算：所有字符都按2个字符=1token计算

        Args:
            text: 要估算的文本

        Returns:
            估算的token数量
        """
        return len(text) // 2

    def call_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """
        根据工具名称调用相应的工具

        Args:
            tool_name: 工具名称
            tool_args: 工具参数

        Returns:
            Any: 工具执行结果
        """
        logger.warning(f"❌ call_tool: 未知工具 - {tool_name}")
        return {"error": f"未知工具: {tool_name}"}


TOOLS_DEFINITION = []
