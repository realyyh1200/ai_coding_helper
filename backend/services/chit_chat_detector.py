import re
from core.logger import logger

class ChitChatDetector:
    def __init__(self):
        self.chit_chat_keywords = [
            "你好", "您好", "hello", "hi", "嗨", "早上好", "下午好", "晚上好",
            "在吗", "干嘛呢", "在干嘛", "忙吗", "有空吗",
            "谢谢", "感谢", "多谢", "谢谢了", "感谢你",
            "再见", "拜拜", "bye", "goodbye", "下次见",
            "好的", "收到", "明白了", "知道了", "了解", "嗯", "哦", "好",
            "哈哈哈", "哈哈", "呵呵", "嘻嘻", "厉害", "牛逼", "666",
            "吃饭了吗", "睡了吗", "起床了吗", "今天天气",
            "我是", "介绍一下", "你是谁", "你叫什么",
            "能帮我", "帮我", "请问", "问一下",
            "没问题", "没关系", "抱歉", "对不起",
            "真的假的", "真的吗", "是吗", "对吗",
            "开玩笑", "逗我", "笑死",
            "今天", "昨天", "明天", "周末", "假期",
            "聊聊", "聊天", "说说", "谈谈"
        ]
        
        self.professional_keywords = [
            "什么是", "怎么", "如何", "怎样", "为什么", "原因",
            "请问", "解释", "说明", "介绍", "定义", "概念",
            "代码", "程序", "算法", "函数", "类", "方法",
            "错误", "问题", "bug", "异常", "报错",
            "文档", "文件", "资料", "教程", "指南",
            "学习", "研究", "分析", "探讨", "研究一下",
            "技术", "架构", "设计", "实现", "方案",
            "对比", "比较", "区别", "差异",
            "最佳实践", "优化", "性能", "效率",
            "数据库", "服务器", "网络", "系统",
            "配置", "部署", "安装", "设置"
        ]

    def is_chit_chat(self, message: str) -> bool:
        message_lower = message.lower().strip()
        
        if len(message_lower) <= 3:
            return True
        
        chit_chat_count = 0
        professional_count = 0
        
        for keyword in self.chit_chat_keywords:
            if keyword.lower() in message_lower:
                chit_chat_count += 1
        
        for keyword in self.professional_keywords:
            if keyword.lower() in message_lower:
                professional_count += 1
        
        if professional_count > 0:
            return False
        
        if chit_chat_count > 0:
            logger.info(f"💭 检测到闲聊消息 (关键词: {chit_chat_count}个)")
            return True
        
        question_patterns = [
            r'^(你|您)(好|在吗|忙吗|有空吗|是谁|叫什么)\??$',
            r'^[嗯哦啊哈哇噻耶]+[.!?]*$',
            r'^谢谢?[.!?]*$',
            r'^再见?[.!?]*$',
            r'^拜拜?[.!?]*$',
            r'^好的?[.!?]*$',
            r'^收到?[.!?]*$',
            r'^明白?[.!?]*$',
            r'^知道了?[.!?]*$'
        ]
        
        for pattern in question_patterns:
            if re.match(pattern, message_lower):
                logger.info(f"💭 检测到闲聊消息 (匹配模式)")
                return True
        
        return False