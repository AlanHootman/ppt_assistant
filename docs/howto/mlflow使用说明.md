# 使用MLflow跟踪LangGraph工作流

本文档提供了如何使用MLflow来跟踪和可视化PPT Assistant工作流的执行过程。

## 1. 安装MLflow

首先，确保已经安装了MLflow：

```bash
pip install mlflow
```

## 2. 启用工作流跟踪

在运行工作流时，添加`--trace`参数即可启用MLflow跟踪：

```bash
python run_workflow.py --md_file your_file.md --ppt_template your_template.pptx --trace
```

这将记录工作流的执行过程，包括每个节点的状态变化、处理时间、生成的内容等信息。

## 3. 查看工作流可视化

### 3.1 启动MLflow UI

可以通过以下方式之一启动MLflow UI：

1. 在运行工作流的同时启动UI：

   ```bash
   python run_workflow.py --md_file your_file.md --ppt_template your_template.pptx --trace --ui
   ```

2. 或者单独启动UI查看历史记录：

   ```bash
   python start_mlflow_ui.py
   ```

默认情况下，MLflow UI将在`http://localhost:5000`启动。可以通过`--port`参数修改端口号。

### 3.2 查看实验和运行

在MLflow UI中：

1. 左侧面板显示所有实验，默认创建名为"ppt_generation"的实验。
2. 中间面板显示该实验的所有运行记录，按时间排序。
3. 点击一个运行记录，右侧将显示详细信息。

### 3.3 关键指标和参数

每次工作流运行会记录以下信息：

- **参数**：记录每个节点的执行时间、处理文件信息等。
- **指标**：记录每个节点的执行次数、处理内容大小等。
- **工件**：保存生成的内容结构、决策结果和最终PPT文件等。

## 4. 故障排除

如果遇到问题，检查以下几点：

1. 确保已经正确安装MLflow：`pip install mlflow`
2. 检查`mlruns`目录是否存在并有写入权限
3. 确保端口号没有被其他应用占用
4. 查看控制台的错误日志以获取详细信息

## 5. 配置MLflow跟踪服务器

可以通过环境变量来配置MLflow跟踪服务器的URI：

1. 在项目根目录创建或编辑`.env`文件，添加以下配置：

   ```
   MLFLOW_TRACKING_URI=http://your-mlflow-server:port
   ```

2. 如果未指定，系统将默认使用`http://127.0.0.1:5000`作为跟踪服务器地址。

3. 也可以在代码中直接指定：

   ```python
   from core.monitoring.mlflow_tracker import MLflowTracker
   
   # 使用自定义跟踪服务器
   tracker = MLflowTracker(tracking_uri="http://your-custom-server:port")
   
   # 或使用环境变量中的跟踪服务器（推荐）
   tracker = MLflowTracker()
   ```

这种配置方式便于在不同环境（开发、测试、生产）之间切换MLflow服务器。

