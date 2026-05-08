import os
from sqlalchemy.orm import Session
from models.user import User
from schemas.schema import SafePathCheckResponse
from typing import Dict, Any


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

    def check_safe_path(self, path: str) -> SafePathCheckResponse:
        """
        检查给定路径是否为安全路径（即用户选择的项目目录下的子路径）
        
        Args:
            path: 需要检查的路径
            
        Returns:
            SafePathCheckResponse: 包含是否安全和说明信息
        """
        # 获取用户设置的项目目录
        project_folder = self.user.project_folder if self.user else None
        
        if not project_folder:
            return SafePathCheckResponse(
                is_safe=False,
                message="用户尚未设置项目目录，请先选择项目目录"
            )
        
        # 标准化路径
        try:
            # 获取绝对路径
            abs_path = os.path.abspath(path)
            abs_project_folder = os.path.abspath(project_folder)
            
            # 确保目录路径以分隔符结尾，避免部分匹配问题
            if not abs_project_folder.endswith(os.sep):
                abs_project_folder += os.sep
            
            # 检查路径是否在项目目录下
            if abs_path.startswith(abs_project_folder):
                return SafePathCheckResponse(
                    is_safe=True,
                    message=f"路径安全：{path} 是项目目录 {project_folder} 的子路径"
                )
            else:
                return SafePathCheckResponse(
                    is_safe=False,
                    message=f"路径不安全：{path} 不在项目目录 {project_folder} 下"
                )
        except Exception as e:
            return SafePathCheckResponse(
                is_safe=False,
                message=f"路径检查失败：{str(e)}"
            )

    def get_current_file(self, file_path: str = None) -> Dict[str, Any]:
        """
        获取用户当前选中的目录路径（由前端传入）
        
        Args:
            file_path: 前端传递的目录路径
            
        Returns:
            Dict: 包含路径信息的字典
        """
        if not file_path:
            return {
                "success": False,
                "message": "您当前没有选中任何目录",
                "path": None
            }
        
        return {
            "success": True,
            "message": f"您当前选中的目录是：{file_path}",
            "path": file_path
        }

    def call_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """
        根据工具名称调用相应的工具
        
        Args:
            tool_name: 工具名称
            tool_args: 工具参数
            
        Returns:
            Any: 工具执行结果
        """
        tools = {
            "check_safe_path": self.check_safe_path,
            "get_current_file": self.get_current_file,
        }
        
        if tool_name not in tools:
            return {"error": f"未知工具: {tool_name}"}
        
        try:
            return tools[tool_name](**tool_args)
        except Exception as e:
            return {"error": f"工具调用失败: {str(e)}"}


# LLM 工具定义（用于向LLM描述可用工具）
TOOLS_DEFINITION = [
    {
        "name": "check_safe_path",
        "description": "检查给定路径是否为安全路径（即用户选择的项目目录下的子路径）",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "需要检查的路径"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "get_current_file",
        "description": "获取用户当前选中的目录路径。当用户询问'我选中了哪个目录'、'当前目录是什么'或类似问题时调用此工具。需要前端传入用户选中的目录路径。",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "用户当前选中的目录路径"
                }
            },
            "required": ["file_path"]
        }
    }
]
