# PPT自动生成系统

基于LangGraph的PPT自动生成系统，可以将Markdown文档自动转换为PPT演示文稿。

## 功能特点

- Markdown解析：自动解析Markdown文档结构
- PPT模板分析：分析PPT模板的布局和风格
- 智能布局决策：匹配内容与合适的PPT布局
- 自动生成PPT：根据解析结果生成最终的PPT文件

## 技术架构

系统基于LangGraph工作流引擎构建，包含以下核心组件：

1. 工作流引擎：协调各模块工作
2. Markdown解析器：解析文档结构
3. PPT分析器：分析模板特性
4. 布局决策器：选择最佳布局
5. PPT生成器：生成最终PPT

## 使用方法

### 方式一：使用Docker部署

```bash
docker-compose -f docker/docker-compose.yml up -d
```

### 方式二：使用本地环境部署

#### 1. 安装依赖

```bash
# 创建虚拟环境
conda create -n ppt_gen python=3.12
conda activate ppt_gen

# 安装依赖
pip install -r requirements.txt

# 初始化子模块
git submodule update --init

# 安装ppt_manager
cd libs/ppt_manager
pip install -e .
```

#### 2. 安装LibreOffice

Mac用户可以通过brew安装LibreOffice

```bash
brew install --cask libreoffice
```

安装之后创建soffice的命令脚本
```bash
# 创建软链接
sudo tee /usr/local/bin/soffice <<EOF
#!/bin/bash
/Applications/LibreOffice.app/Contents/MacOS/soffice "\$@"
EOF

# 赋予执行权限
sudo chmod +x /usr/local/bin/soffice

```

验证安装
```bash
soffice --version
```

#### 3. 运行
##### 3.1 启动redis服务
```bash
docker-compose -f docker/docker-compose-dev.yml up -d
```

##### 3.2 启动后端FastAPI服务
```bash
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

##### 3.3 启动celery服务
```bash
celery -A apps.api.celery_app worker --loglevel=info --concurrency=2 --pool=solo -Q celery,template_analysis,ppt_generation
```
##### 3.4 启动mlflow服务
```bash
python scripts/start_mlflow_ui.py
```

##### 3.5 启动前端Vue服务
```bash
cd apps/web
npm install --legacy-peer-deps
npm run dev
```
访问 http://localhost:5173 即可访问前端页面
访问 http://localhost:5000 即可访问mlflow服务

## 项目结构

```
ppt-assisstant/
├── apps/                  # 应用层
│   ├── api/               # FastAPI接口服务
│   │   ├── routers/       # 接口路由
│   │   │   ├── agent.py   # Agent能力接口
│   │   │   └── file.py    # 文件处理接口
│   │   ├── models/        # 接口数据模型
│   │   ├── dependencies/  # 接口依赖项
│   │   └── main.py        # FastAPI入口
│   │
│   └── web/               # 前端工程
│       ├── public/        # 静态资源
│       ├── src/           # 前端源码
│       └── package.json   # 前端依赖
│
├── core/                  # 核心业务
│   ├── agents/            # LangGraph Agent实现
│   │   ├── markdown_agent.py           # Markdown解析
│   │   ├── ppt_analysis_agent.py       # PPT分析
│   │   ├── content_planning_agent.py   # 内容规划
│   │   ├── slide_generator_agent.py    # 幻灯片生成
│   │   ├── ppt_finalizer_agent.py      # PPT清理与保存
│   │   └── base_agent.py               # 基础Agent
│   │
│   ├── workflows/         # 工作流配置
│   │   ├── ppt_gen.yaml   # 主工作流配置
│   │   └── utils.py       # 工作流工具
│   │
│   └── engine/            # 执行引擎
│       ├── state.py       # 状态管理
│       └── workflow.py    # 工作流引擎
│
├── libs/                  # 第三方库
│   ├── ppt_manager/       # PPT操作库（git子模块）
│   └── ...                # 其他子模块
│
├── workspace/             # 运行时文件
│   ├── sessions/          # 会话数据
│   │   └── {session_id}/  # 按会话隔离
│   ├── logs/              # 系统日志
│   │   └── %Y-%m/         # 按日期分片
│   └── temp/              # 临时文件
│
├── config/                # 配置中心
│   ├── settings.py        # 应用配置
│   ├── model_config.yaml  # 模型配置
│   └── workflow/          # 工作流配置
│
├── docs/                  # 文档中心
│   ├── arch/              # 架构设计
│   └── api/               # API文档
│
├── tests/                 # 测试体系
│   ├── unit/              # 单元测试
│   └── integration/       # 集成测试
│
├── Dockerfile             # 容器化构建
├── docker-compose.yml     # 服务编排
└── requirements.txt       # Python依赖
```

## 🙏 致谢
本项目核心思想来源于[PPTAgent](https://github.com/icip-cas/PPTAgent)提出的**多模态大语言模型+Agent框架**。我们诚挚感谢该项目提供的创新思路，这为本工程的设计和实现奠定了关键基础。

## 📚 引用声明
如果您在研究中使用了本项目，请引用启发我们工作的原始PPTAgent项目：
```bibtex
@article{zheng2025pptagent,
  title={PPTAgent: Generating and Evaluating Presentations Beyond Text-to-Slides},
  author={Zheng, Hao and Guan, Xinyan and Kong, Hao and Zheng, Jia and Zhou, Weixiang and Lin, Hongyu and Lu, Yaojie and He, Ben and Han, Xianpei and Sun, Le},
  journal={arXiv preprint arXiv:2501.03936},
  year={2025}
}
```
