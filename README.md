# AI文件处理助手

基于FastAPI后端和Vue3前端的AI文件网站，支持流式输出、多用户认证和持久化存储。

## 项目结构

```
ai_file_processing_website/
├── backend/
│   ├── api/              # API路由
│   │   ├── auth.py       # 认证相关API
│   │   ├── chat.py       # 聊天相关API
│   │   └── user.py       # 用户相关API
│   ├── core/             # 核心配置
│   │   ├── config.py     # 应用配置
│   │   └── security.py   # JWT认证和安全工具
│   ├── db/               # 数据库
│   │   └── database.py   # 数据库连接
│   ├── models/           # 数据模型
│   │   └── user.py       # User, Conversation, Message模型
│   ├── schemas/          # Pydantic模式
│   │   └── schema.py     # 请求/响应模式
│   ├── services/         # 业务逻辑
│   │   └── anthropic_service.py  # Anthropic API服务
│   ├── main.py           # FastAPI应用入口
│   └── requirements.txt  # Python依赖
│
└── frontend/
    ├── src/
    │   ├── api/          # API调用
    │   │   ├── auth.js   # 认证API
    │   │   └── chat.js   # 聊天API
    │   ├── components/   # Vue组件
    │   ├── router/       # 路由配置
    │   ├── store/        # Pinia状态管理
    │   │   └── auth.js   # 认证状态
    │   ├── views/        # 页面视图
    │   │   ├── Login.vue
    │   │   ├── Register.vue
    │   │   └── Chat.vue
    │   ├── App.vue
    │   └── main.js
    ├── index.html
    ├── package.json
    └── vite.config.js
```

## 后端启动

### 使用 uv（推荐）

```bash
cd ai_file_processing_website/backend

# 安装依赖
uv sync

# 复制环境变量文件并配置
cp .env.example .env
# 编辑.env文件，填入你的ANTHROPIC_API_KEY和SECRET_KEY

# 启动服务器
uv run uvicorn main:app --reload --port 8000
```

### 使用 pip（传统方式）

```bash
cd ai_file_processing_website/backend

# 安装依赖
pip install -r requirements.txt

# 复制环境变量文件并配置
cp .env.example .env
# 编辑.env文件，填入你的ANTHROPIC_API_KEY和SECRET_KEY

# 启动服务器
uvicorn main:app --reload --port 8000
```

### uv 常用命令

| 命令 | 说明 |
|------|------|
| `uv sync` | 同步并安装所有依赖 |
| `uv add package` | 添加新依赖 |
| `uv remove package` | 移除依赖 |
| `uv lock` | 更新锁定文件 |
| `uv run command` | 在虚拟环境中运行命令 |

API文档地址: http://localhost:8000/docs

## 前端启动

```bash
cd ai_file_processing_website/frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问地址: http://localhost:5173

## 功能特性

- ✅ 用户注册和登录
- ✅ JWT令牌认证（Access Token + Refresh Token）
- ✅ 流式AI响应输出
- ✅ 多对话管理
- ✅ 对话历史持久化
- ✅ 用户信息管理
