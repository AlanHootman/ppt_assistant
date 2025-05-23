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

### 安装依赖

```bash
# 创建虚拟环境
conda create -n ppt_gen python=3.12
conda activate ppt_gen

# 安装依赖
pip install -r requirements.txt

cd libs/ppt_manager
pip install -e .
```

### 基本使用

运行示例工作流：

```bash
python run_workflow.py
```

自定义运行参数：

```bash
python run_workflow.py --markdown <md文件路径> --template <ppt模板路径>
```

### 高级用法

```python
from core.engine.workflowEngine import WorkflowEngine

# 初始化工作流引擎
engine = WorkflowEngine()

# 运行工作流
result = await engine.run_async(
    raw_md="# 标题\n## 子标题\n- 要点1\n- 要点2",
    ppt_template_path="templates/default.pptx"
)

# 获取生成的PPT文件路径
ppt_path = result.output_ppt_path
print(f"PPT已生成: {ppt_path}")
```

## 项目结构

```
ppt-assisstant/
├── core/                  # 核心业务
│   ├── agents/            # LangGraph Agent实现
│   ├── workflows/         # 工作流配置
│   └── engine/            # 执行引擎
├── config/                # 配置中心
├── workspace/             # 运行时文件
├── tests/                 # 测试体系
└── docs/                  # 文档中心
```

## 开发进度

- [x] 工作流引擎框架
- [x] 配置加载器
- [x] 状态管理
- [ ] Markdown解析Agent
- [ ] PPT模板分析Agent
- [ ] 布局决策Agent
- [ ] PPT生成Agent

## 许可证

MIT

