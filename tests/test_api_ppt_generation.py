#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import time
import requests
import argparse
import websocket
import threading
from pathlib import Path

class PPTAssistantAPITester:
    """PPT助手API测试工具"""
    
    def __init__(self, base_url="http://localhost:8000"):
        """初始化API测试工具
        
        Args:
            base_url: API服务基础URL
        """
        self.base_url = base_url
        self.headers = {
            'Accept': 'application/json',
        }
        self.ws = None
        self.ws_running = False
    
    def upload_template(self, template_path, template_name=None):
        """上传PPT模板
        
        Args:
            template_path: 模板文件路径
            template_name: 模板名称，默认使用文件名
            
        Returns:
            响应JSON
        """
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"模板文件不存在: {template_path}")
        
        if template_name is None:
            template_name = os.path.basename(template_path).split('.')[0]
        
        url = f"{self.base_url}/api/v1/templates/"
        
        files = {
            'file': open(template_path, 'rb')
        }
        
        data = {
            'name': template_name,
            'description': f'测试上传的模板: {template_name}',
            'tags': '测试,API'
        }
        
        response = requests.post(url, headers=self.headers, data=data, files=files)
        response.raise_for_status()
        json_data = response.json()
        # 返回data部分数据
        return json_data['data'] if 'data' in json_data else json_data
    
    def list_templates(self):
        """获取模板列表
        
        Returns:
            响应JSON
        """
        url = f"{self.base_url}/api/v1/templates"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        json_data = response.json()
        # 返回templates列表
        return json_data['data']['templates'] if 'data' in json_data and 'templates' in json_data['data'] else json_data
    
    def get_template_details(self, template_id):
        """获取模板详情
        
        Args:
            template_id: 模板ID
            
        Returns:
            响应JSON
        """
        url = f"{self.base_url}/api/v1/templates/{template_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        json_data = response.json()
        # 返回template对象
        return json_data['data']['template'] if 'data' in json_data and 'template' in json_data['data'] else json_data
    
    def generate_ppt(self, template_id, markdown_content):
        """生成PPT
        
        Args:
            template_id: 模板ID
            markdown_content: Markdown内容
            
        Returns:
            响应JSON
        """
        url = f"{self.base_url}/api/v1/ppt/generate"
        
        payload = {
            'template_id': template_id,
            'markdown_content': markdown_content
        }
        
        print(f"发送请求到: {url}")
        print(f"请求载荷: {json.dumps(payload)[:200]}...")
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            print(f"响应状态码: {response.status_code}")
            print(f"响应内容: {response.text[:500]}")
            
            response.raise_for_status()
            json_data = response.json()
            # 返回data部分
            return json_data['data'] if 'data' in json_data else json_data
        except requests.exceptions.HTTPError as e:
            print(f"HTTP错误: {e}")
            if response.content:
                print(f"错误详情: {response.text}")
            raise
        except json.JSONDecodeError:
            print(f"JSON解析错误，响应不是有效的JSON: {response.text}")
            raise
        except Exception as e:
            print(f"生成PPT时发生错误: {str(e)}")
            raise
    
    def get_task_status(self, task_id):
        """获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            响应JSON
        """
        url = f"{self.base_url}/api/v1/ppt/tasks/{task_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        json_data = response.json()
        # 返回data部分
        return json_data['data'] if 'data' in json_data else json_data
    
    def _on_ws_message(self, ws, message):
        """WebSocket消息处理"""
        print(f"收到WebSocket消息: {message[:200]}...")
        try:
            data = json.loads(message)
            progress = data.get('progress', 0)
            status = data.get('status', '')
            step = data.get('current_step', '')
            desc = data.get('step_description', '')
            
            print(f"任务进度: {progress}%, 状态: {status}, 步骤: {step}")
            if desc:
                print(f"描述: {desc}")
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}, 原始消息: {message[:100]}...")
        except Exception as e:
            print(f"处理WebSocket消息时发生错误: {str(e)}")
    
    def _on_ws_error(self, ws, error):
        """WebSocket错误处理"""
        print(f"WebSocket错误: {error}")
    
    def _on_ws_close(self, ws, close_status_code, close_msg):
        """WebSocket关闭处理"""
        print("WebSocket连接已关闭")
        self.ws_running = False
    
    def _on_ws_open(self, ws):
        """WebSocket打开处理"""
        print("WebSocket连接已建立")
        self.ws_running = True
    
    def connect_ws(self, task_id):
        """连接WebSocket获取实时进度
        
        Args:
            task_id: 任务ID
        """
        ws_url = f"ws://localhost:8000/api/v1/ws/tasks/{task_id}"
        print(f"连接到WebSocket: {ws_url}")
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_open=self._on_ws_open,
            on_message=self._on_ws_message,
            on_error=self._on_ws_error,
            on_close=self._on_ws_close,
            on_ping=self._on_ws_ping,
            on_pong=self._on_ws_pong
        )
        
        ws_thread = threading.Thread(
            target=lambda: self.ws.run_forever(
                ping_interval=30,
                ping_timeout=10,
                skip_utf8_validation=True
            )
        )
        ws_thread.daemon = True
        ws_thread.start()
        
        time.sleep(1)
        
        return ws_thread
    
    def disconnect_ws(self):
        """断开WebSocket连接"""
        if self.ws and self.ws_running:
            self.ws.close()
            self.ws_running = False
    
    def _on_ws_ping(self, ws, message):
        """处理收到的ping消息"""
        print("收到服务器ping")
    
    def _on_ws_pong(self, ws, message):
        """处理收到的pong消息"""
        print("收到服务器pong")

def run_generate_ppt_test(args):
    """运行PPT生成测试"""
    tester = PPTAssistantAPITester(args.base_url)
    
    # 获取Markdown文件内容
    markdown_path = args.markdown
    if not os.path.exists(markdown_path):
        print(f"错误: Markdown文件不存在: {markdown_path}")
        return
    
    with open(markdown_path, 'r', encoding='utf-8') as f:
        markdown_content = f.read()
    
    # 处理模板ID或上传模板
    template_id = args.template_id
    if template_id is None:
        # 验证模板文件路径
        template_path = args.template
        if not os.path.exists(template_path):
            print(f"错误: 模板文件不存在: {template_path}")
            return
            
        print("上传模板文件...")
        template_response = tester.upload_template(template_path)
        # 根据API响应格式获取模板ID
        if 'template_id' in template_response:
            template_id = template_response['template_id']
        elif 'id' in template_response:
            template_id = template_response['id']
        else:
            print(f"错误: 无法从响应中获取模板ID: {template_response}")
            return
            
        print(f"模板上传成功，ID: {template_id}")
    else:
        print(f"使用已有模板，ID: {template_id}")
    
    # 请求生成PPT
    print("开始生成PPT...")
    generation_response = tester.generate_ppt(template_id, markdown_content)
    task_id = generation_response['task_id']
    print(f"PPT生成任务已创建，任务ID: {task_id}")
    
    # 连接WebSocket获取实时进度
    if not args.no_websocket:
        print("连接WebSocket获取实时进度...")
        ws_thread = tester.connect_ws(task_id)
        
        # 给WebSocket连接一些时间来建立和接收初始消息
        print(f"等待WebSocket连接建立 ({args.ws_wait}秒)...")
        time.sleep(args.ws_wait)
    
    # 定期轮询任务状态
    max_wait_time = args.timeout  # 最长等待时间(秒)
    wait_time = 0
    interval = 5  # 查询间隔(秒)
    
    while wait_time < max_wait_time:
        time.sleep(interval)
        wait_time += interval
        
        status_response = tester.get_task_status(task_id)
        status = status_response.get('status', '')
        
        if status in ['completed', 'failed']:
            break
    
    # 断开WebSocket连接
    if not args.no_websocket:
        tester.disconnect_ws()
    
    # 输出最终结果
    final_status = tester.get_task_status(task_id)
    print("\n最终任务状态:")
    print(json.dumps(final_status, indent=2, ensure_ascii=False))
    
    if final_status.get('status') == 'completed':
        print(f"\nPPT生成成功! 文件URL: {final_status.get('file_url')}")
        if args.download and 'file_url' in final_status:
            # 下载生成的PPT文件
            file_url = final_status['file_url']
            download_url = f"{args.base_url}{file_url}"
            output_path = args.output or f"./output_{task_id}.pptx"
            
            print(f"下载PPT文件到: {output_path}")
            download_response = requests.get(download_url)
            download_response.raise_for_status()
            
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(download_response.content)
            
            print(f"PPT文件已保存到: {output_path}")
    else:
        print("\nPPT生成失败!")
        if 'error' in final_status:
            print(f"错误信息: {final_status['error'].get('error_message', '未知错误')}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PPT助手API测试工具")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API服务基础URL")
    parser.add_argument("--template", help="PPT模板文件路径")
    parser.add_argument("--markdown", required=True, help="Markdown内容文件路径")
    parser.add_argument("--template-id", help="已有模板ID，指定则不上传新模板")
    parser.add_argument("--timeout", type=int, default=600, help="最长等待时间(秒)")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--download", action="store_true", help="下载生成的PPT文件")
    parser.add_argument("--no-websocket", action="store_true", help="不使用WebSocket获取实时进度")
    parser.add_argument("--debug-websocket", action="store_true", help="启用WebSocket调试日志")
    parser.add_argument("--ws-wait", type=int, default=5, help="WebSocket连接后的初始等待时间(秒)")
    
    args = parser.parse_args()
    
    # 检查参数：如果没有提供template_id，则template是必需的
    if args.template_id is None and args.template is None:
        parser.error("必须提供 --template 或 --template-id 参数")
    
    # 启用WebSocket调试
    if args.debug_websocket:
        import logging
        websocket.enableTrace(True)
        logging.basicConfig(level=logging.DEBUG)
        
    run_generate_ppt_test(args) 