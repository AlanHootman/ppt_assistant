# PPT助手系统API设计

## 1. API概述

PPT助手系统API是一组RESTful接口，用于支持PPT自动生成系统的前端页面和后台管理功能。API主要包含以下几个部分：

- 模板管理API：用于管理PPT模板资源
- 用户认证API：用于后台管理用户的认证
- PPT生成API：用于处理PPT生成请求和查询生成状态
- 文件管理API：用于处理文件上传和下载

## 2. 通用规范

### 2.1 基础URL

```
https://{host}/api/v1
```

### 2.2 请求方法

- GET: 获取资源
- POST: 创建资源
- PUT: 更新资源
- DELETE: 删除资源

### 2.3 状态码

- 200 OK: 请求成功
- 201 Created: 资源创建成功
- 400 Bad Request: 请求参数错误
- 401 Unauthorized: 未认证
- 403 Forbidden: 权限不足
- 404 Not Found: 资源不存在
- 500 Internal Server Error: 服务器内部错误

### 2.4 响应格式

所有API响应均采用JSON格式，基本结构如下：

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {}
}
```

错误响应格式：

```json
{
  "code": 400,
  "message": "请求参数错误",
  "errors": ["参数1不能为空", "参数2格式错误"]
}
```

### 2.5 认证方式

使用JWT (JSON Web Token) 进行API认证。除了登录接口外，其他需要认证的接口均需在请求头中包含：

```
Authorization: Bearer {token}
```

## 3. API详细设计

### 3.1 用户认证API

#### 3.1.1 用户登录

- **接口**: `POST /auth/login`
- **描述**: 管理员登录获取认证令牌
- **请求体**:
  ```json
  {
    "username": "admin",
    "password": "password123"
  }
  ```
- **响应**:
  ```json
  {
    "code": 200,
    "message": "登录成功",
    "data": {
      "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "expires_in": 3600,
      "user": {
        "id": 1,
        "username": "admin",
        "role": "admin"
      }
    }
  }
  ```

#### 3.1.2 验证令牌

- **接口**: `GET /auth/verify`
- **描述**: 验证令牌有效性
- **请求头**: 包含Authorization令牌
- **响应**:
  ```json
  {
    "code": 200,
    "message": "令牌有效",
    "data": {
      "user": {
        "id": 1,
        "username": "admin",
        "role": "admin"
      }
    }
  }
  ```

#### 3.1.3 退出登录

- **接口**: `POST /auth/logout`
- **描述**: 注销用户会话
- **请求头**: 包含Authorization令牌
- **响应**:
  ```json
  {
    "code": 200,
    "message": "已成功退出登录",
    "data": {}
  }
  ```

### 3.2 模板管理API

#### 3.2.1 获取模板列表

- **接口**: `GET /templates`
- **描述**: 获取所有可用的PPT模板列表
- **参数**:
  - `page`: 页码，默认1
  - `limit`: 每页条数，默认10
- **响应**:
  ```json
  {
    "code": 200,
    "message": "获取成功",
    "data": {
      "total": 25,
      "page": 1,
      "limit": 10,
      "templates": [
        {
          "id": 1,
          "name": "商务简约风",
          "preview_url": "/static/templates/1/preview.png",
          "upload_time": "2023-06-15T10:30:00Z",
          "status": "ready",
          "tags": ["商务", "简约", "专业"]
        },
        // 更多模板...
      ]
    }
  }
  ```

#### 3.2.2 获取模板详情

- **接口**: `GET /templates/{template_id}`
- **描述**: 获取特定模板的详细信息
- **响应**:
  ```json
  {
    "code": 200,
    "message": "获取成功",
    "data": {
      "template": {
        "id": 1,
        "name": "商务简约风",
        "file_url": "/static/templates/1/template.pptx",
        "preview_url": "/static/templates/1/preview.png",
        "description": "适用于商务演示的简约风格模板",
        "upload_time": "2023-06-15T10:30:00Z",
        "status": "ready",
        "tags": ["商务", "简约", "专业"],
        "layout_features": {
          // 模板分析结果JSON，包含布局信息等
        }
      }
    }
  }
  ```

#### 3.2.3 上传模板

- **接口**: `POST /templates`
- **描述**: 上传新的PPT模板并进行分析
- **请求头**: 包含Authorization令牌
- **请求体**: 使用FormData格式
  ```
  file: [PPT文件]
  name: "模板名称"
  description: "模板描述"
  tags: ["标签1", "标签2"]
  ```
- **响应**:
  ```json
  {
    "code": 201,
    "message": "模板上传成功，正在进行分析",
    "data": {
      "template_id": 5,
      "name": "教育主题模板",
      "status": "analyzing",
      "task_id": "task-12345"
    }
  }
  ```

#### 3.2.4 更新模板信息

- **接口**: `PUT /templates/{template_id}`
- **描述**: 更新模板的基本信息（不包括文件）
- **请求头**: 包含Authorization令牌
- **请求体**:
  ```json
  {
    "name": "更新后的模板名称",
    "description": "更新后的描述",
    "tags": ["标签1", "标签2", "新标签"]
  }
  ```
- **响应**:
  ```json
  {
    "code": 200,
    "message": "模板信息更新成功",
    "data": {
      "template": {
        "id": 5,
        "name": "更新后的模板名称",
        "description": "更新后的描述",
        "tags": ["标签1", "标签2", "新标签"]
      }
    }
  }
  ```

#### 3.2.5 删除模板

- **接口**: `DELETE /templates/{template_id}`
- **描述**: 删除指定的模板及相关资源
- **请求头**: 包含Authorization令牌
- **响应**:
  ```json
  {
    "code": 200,
    "message": "模板删除成功",
    "data": {}
  }
  ```

#### 3.2.6 获取模板分析状态

- **接口**: `GET /templates/{template_id}/status`
- **描述**: 获取模板分析的当前状态
- **请求头**: 包含Authorization令牌
- **响应**:
  ```json
  {
    "code": 200,
    "message": "获取成功",
    "data": {
      "template_id": 5,
      "status": "analyzing",
      "progress": 60,
      "message": "正在分析布局特征"
    }
  }
  ```

### 3.3 PPT生成API

#### 3.3.1 创建PPT生成任务

- **接口**: `POST /ppt/generate`
- **描述**: 创建一个新的PPT生成任务
- **请求体**:
  ```json
  {
    "template_id": 1,
    "markdown_content": "# 标题\n## 副标题\n内容段落...",
    "callback_url": "https://example.com/callback" // 可选，任务完成后回调通知
  }
  ```
- **响应**:
  ```json
  {
    "code": 201,
    "message": "PPT生成任务已创建",
    "data": {
      "task_id": "task-67890",
      "status": "pending",
      "created_at": "2023-07-10T15:45:30Z"
    }
  }
  ```

#### 3.3.2 获取任务状态

- **接口**: `GET /ppt/tasks/{task_id}`
- **描述**: 获取PPT生成任务的当前状态
- **响应**:
  ```json
  {
    "code": 200,
    "message": "获取成功",
    "data": {
      "task_id": "task-67890",
      "status": "processing", // 可能的状态: pending, processing, completed, failed, cancelled
      "progress": 65,
      "current_step": "slide_generation",
      "step_description": "Agent正在进行PPTX文件的编辑",
      "created_at": "2023-07-10T15:45:30Z",
      "updated_at": "2023-07-10T15:47:45Z",
      "preview_images": [
        {
          "slide_index": 0,
          "preview_url": "/static/output/task-67890/slides/slide_0.png"
        },
        {
          "slide_index": 1,
          "preview_url": "/static/output/task-67890/slides/slide_1.png"
        }
      ],
      "error": {
        "has_error": false,
        "error_code": null,
        "error_message": null,
        "can_retry": false
      }
    }
  }
  ```

- **错误状态示例**:
  ```json
  {
    "code": 200,
    "message": "获取成功",
    "data": {
      "task_id": "task-67890",
      "status": "failed",
      "progress": 35,
      "current_step": "slide_generation",
      "step_description": "Agent生成幻灯片时出现错误",
      "created_at": "2023-07-10T15:45:30Z",
      "updated_at": "2023-07-10T15:47:45Z",
      "preview_images": [
        {
          "slide_index": 0,
          "preview_url": "/static/output/task-67890/slides/slide_0.png"
        }
      ],
      "error": {
        "has_error": true,
        "error_code": "SLIDE_GENERATION_ERROR",
        "error_message": "生成幻灯片时遇到问题：无法处理复杂表格内容",
        "can_retry": true
      }
    }
  }
  ```

#### 3.3.3 重试失败的任务

- **接口**: `POST /ppt/tasks/{task_id}/retry`
- **描述**: 重试之前失败的PPT生成任务
- **响应**:
  ```json
  {
    "code": 200,
    "message": "任务已重新启动",
    "data": {
      "task_id": "task-67890",
      "status": "processing",
      "progress": 35,
      "retry_count": 1,
      "created_at": "2023-07-10T15:45:30Z",
      "updated_at": "2023-07-10T15:55:12Z"
    }
  }
  ```

#### 3.3.4 获取生成结果

- **接口**: `GET /ppt/tasks/{task_id}/result`
- **描述**: 获取已完成的PPT生成任务结果
- **响应**:
  ```json
  {
    "code": 200,
    "message": "获取成功",
    "data": {
      "task_id": "task-67890",
      "status": "completed",
      "file_url": "/static/output/task-67890/presentation.pptx",
      "preview_url": "/static/output/task-67890/preview.png",
      "preview_images": [
        {
          "slide_index": 0,
          "preview_url": "/static/output/task-67890/slides/slide_0.png"
        },
        {
          "slide_index": 1,
          "preview_url": "/static/output/task-67890/slides/slide_1.png"
        },
        // 更多幻灯片预览...
      ],
      "completed_at": "2023-07-10T15:50:12Z",
      "download_expires_at": "2023-07-17T15:50:12Z"
    }
  }
  ```

#### 3.3.5 取消任务

- **接口**: `DELETE /ppt/tasks/{task_id}`
- **描述**: 取消正在进行的PPT生成任务
- **响应**:
  ```json
  {
    "code": 200,
    "message": "任务已取消",
    "data": {
      "task_id": "task-67890",
      "status": "cancelled"
    }
  }
  ```

#### 3.3.6 获取任务生成过程中的幻灯片预览

- **接口**: `GET /ppt/tasks/{task_id}/previews`
- **描述**: 获取PPT生成过程中已生成的幻灯片预览图
- **响应**:
  ```json
  {
    "code": 200,
    "message": "获取成功",
    "data": {
      "task_id": "task-67890",
      "total_slides": 10,
      "generated_slides": 4,
      "previews": [
        {
          "slide_index": 0,
          "preview_url": "/static/output/task-67890/slides/slide_0.png",
          "generated_at": "2023-07-10T15:46:05Z"
        },
        {
          "slide_index": 1,
          "preview_url": "/static/output/task-67890/slides/slide_1.png",
          "generated_at": "2023-07-10T15:46:35Z"
        },
        {
          "slide_index": 2,
          "preview_url": "/static/output/task-67890/slides/slide_2.png",
          "generated_at": "2023-07-10T15:47:02Z"
        },
        {
          "slide_index": 3,
          "preview_url": "/static/output/task-67890/slides/slide_3.png",
          "generated_at": "2023-07-10T15:47:30Z"
        }
      ]
    }
  }
  ```

### 3.4 文件管理API

#### 3.4.1 下载生成的PPT

- **接口**: `GET /files/ppt/{task_id}/download`
- **描述**: 下载指定任务生成的PPT文件
- **响应**: 直接返回文件流，Content-Type为application/vnd.openxmlformats-officedocument.presentationml.presentation

#### 3.4.2 获取模板预览图

- **接口**: `GET /files/templates/{template_id}/preview`
- **描述**: 获取模板的预览图片
- **参数**:
  - `slide_index`: 幻灯片索引，默认0表示首页
- **响应**: 直接返回图片流，Content-Type为image/png或image/jpeg

#### 3.4.3 获取幻灯片预览图

- **接口**: `GET /files/ppt/{task_id}/slides/{slide_index}`
- **描述**: 获取指定任务特定幻灯片的预览图
- **参数**:
  - `task_id`: 任务ID
  - `slide_index`: 幻灯片索引
- **响应**: 直接返回图片流，Content-Type为image/png或image/jpeg

## 4. 实现考虑

### 4.1 异步任务处理

由于PPT生成和模板分析是耗时操作，API设计采用异步任务模式：

1. 客户端发起请求后立即返回任务ID
2. 客户端通过轮询或WebSocket获取任务进度和实时预览
3. 任务完成后通过API获取结果或接收回调通知

### 4.2 错误处理和重试机制

1. 生成过程中发生错误时，系统会记录错误信息和代码
2. API会返回错误详情和是否可重试的标志
3. 前端可据此显示错误信息并提供重试选项
4. 重试API允许从错误点恢复，避免完全重新开始

### 4.3 实时预览功能

1. 每次编辑完PPTX文件进行视觉校验时，系统会生成预览图，并保存到文件系统中
2. 客户端可通过API获取已生成幻灯片的预览图
3. 预览图可用于给用户提供实时反馈，增强用户体验

### 4.4 安全考虑

1. 所有管理API都需要JWT认证
2. 文件上传需要进行类型和大小验证
3. API访问频率限制，防止滥用
4. 敏感操作需记录审计日志

### 4.5 缓存策略

1. 模板预览图和布局分析结果可以缓存，提高访问速度
2. 生成的PPT和预览图可设置过期时间，避免存储空间无限增长

## 5. API变更管理

1. API版本通过URL路径前缀(/api/v1)明确标识
2. 重大变更会发布新版本API，旧版本会有一定的过渡期
3. 非破坏性更新会在现有版本上进行，并向下兼容 