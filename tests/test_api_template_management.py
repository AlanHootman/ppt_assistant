#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import argparse
import requests
from pathlib import Path

class TemplateManagerTester:
    """PPT模板管理API测试工具"""
    
    def __init__(self, base_url="http://localhost:8000"):
        """初始化API测试工具
        
        Args:
            base_url: API服务基础URL
        """
        self.base_url = base_url
        self.headers = {
            'Accept': 'application/json',
        }
    
    def upload_template(self, template_path, name=None, description=None, tags=None):
        """上传模板
        
        Args:
            template_path: 模板文件路径
            name: 模板名称
            description: 模板描述
            tags: 模板标签，逗号分隔
            
        Returns:
            响应JSON
        """
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"模板文件不存在: {template_path}")
        
        if name is None:
            name = os.path.basename(template_path).split('.')[0]
        
        if description is None:
            description = f"模板: {name}"
        
        if tags is None:
            tags = "测试,API"
        
        url = f"{self.base_url}/api/templates/upload"
        
        files = {
            'file': open(template_path, 'rb')
        }
        
        data = {
            'name': name,
            'description': description,
            'tags': tags
        }
        
        print(f"上传模板: {name}")
        response = requests.post(url, headers=self.headers, data=data, files=files)
        response.raise_for_status()
        return response.json()
    
    def list_templates(self):
        """获取模板列表
        
        Returns:
            响应JSON
        """
        url = f"{self.base_url}/api/templates"
        print("获取模板列表")
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_template(self, template_id):
        """获取模板详情
        
        Args:
            template_id: 模板ID
            
        Returns:
            响应JSON
        """
        url = f"{self.base_url}/api/templates/{template_id}"
        print(f"获取模板详情: ID={template_id}")
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def update_template(self, template_id, name=None, description=None, tags=None):
        """更新模板信息
        
        Args:
            template_id: 模板ID
            name: 新模板名称
            description: 新模板描述
            tags: 新模板标签
            
        Returns:
            响应JSON
        """
        url = f"{self.base_url}/api/templates/{template_id}"
        
        data = {}
        if name is not None:
            data['name'] = name
        if description is not None:
            data['description'] = description
        if tags is not None:
            data['tags'] = tags
        
        print(f"更新模板: ID={template_id}")
        response = requests.put(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()
    
    def delete_template(self, template_id):
        """删除模板
        
        Args:
            template_id: 模板ID
            
        Returns:
            响应JSON
        """
        url = f"{self.base_url}/api/templates/{template_id}"
        print(f"删除模板: ID={template_id}")
        response = requests.delete(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_template_analysis(self, template_id):
        """获取模板分析结果
        
        Args:
            template_id: 模板ID
            
        Returns:
            响应JSON
        """
        url = f"{self.base_url}/api/templates/{template_id}/analysis"
        print(f"获取模板分析结果: ID={template_id}")
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def request_analysis(self, template_id):
        """请求重新分析模板
        
        Args:
            template_id: 模板ID
            
        Returns:
            响应JSON
        """
        url = f"{self.base_url}/api/templates/{template_id}/analyze"
        print(f"请求重新分析模板: ID={template_id}")
        response = requests.post(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

def run_template_management_test(args):
    """运行模板管理测试"""
    tester = TemplateManagerTester(args.base_url)
    
    if args.action == "upload":
        if not args.template:
            print("错误: 上传模板需要指定--template参数")
            return
            
        if not os.path.exists(args.template):
            print(f"错误: 模板文件不存在: {args.template}")
            return
        
        result = tester.upload_template(
            args.template, 
            name=args.name,
            description=args.description,
            tags=args.tags
        )
        print("\n上传结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    elif args.action == "list":
        result = tester.list_templates()
        print("\n模板列表:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    elif args.action == "get":
        if not args.id:
            print("错误: 获取模板详情需要指定--id参数")
            return
            
        result = tester.get_template(args.id)
        print("\n模板详情:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    elif args.action == "update":
        if not args.id:
            print("错误: 更新模板需要指定--id参数")
            return
            
        result = tester.update_template(
            args.id,
            name=args.name,
            description=args.description,
            tags=args.tags
        )
        print("\n更新结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    elif args.action == "delete":
        if not args.id:
            print("错误: 删除模板需要指定--id参数")
            return
            
        result = tester.delete_template(args.id)
        print("\n删除结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    elif args.action == "analysis":
        if not args.id:
            print("错误: 获取分析结果需要指定--id参数")
            return
            
        result = tester.get_template_analysis(args.id)
        print("\n分析结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    elif args.action == "analyze":
        if not args.id:
            print("错误: 请求分析需要指定--id参数")
            return
            
        result = tester.request_analysis(args.id)
        print("\n请求分析结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    elif args.action == "full-test":
        # 1. 上传模板
        if not args.template:
            print("错误: 完整测试需要指定--template参数")
            return
            
        if not os.path.exists(args.template):
            print(f"错误: 模板文件不存在: {args.template}")
            return
        
        upload_result = tester.upload_template(
            args.template,
            name="API测试模板",
            description="通过API自动化测试上传的模板",
            tags="测试,API,自动化"
        )
        template_id = upload_result['id']
        print(f"\n模板上传成功，ID: {template_id}")
        
        # 2. 获取模板详情
        get_result = tester.get_template(template_id)
        print("\n获取模板详情成功")
        
        # 3. 请求分析模板
        analyze_result = tester.request_analysis(template_id)
        task_id = analyze_result.get('task_id')
        print(f"\n请求分析成功，分析任务ID: {task_id}")
        
        # 4. 更新模板信息
        update_result = tester.update_template(
            template_id,
            name="更新后的API测试模板",
            description="通过API更新的模板描述"
        )
        print("\n模板信息更新成功")
        
        # 5. 列出所有模板
        list_result = tester.list_templates()
        template_count = len(list_result)
        print(f"\n获取模板列表成功，共有{template_count}个模板")
        
        # 6. 删除模板（如果指定了--no-delete则跳过）
        if not args.no_delete:
            delete_result = tester.delete_template(template_id)
            print("\n模板删除成功")
        else:
            print(f"\n保留模板，ID: {template_id}")
        
        print("\n完整测试流程执行完毕!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PPT模板管理API测试工具")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API服务基础URL")
    parser.add_argument("action", choices=[
        "upload", "list", "get", "update", "delete", 
        "analysis", "analyze", "full-test"
    ], help="执行的操作")
    parser.add_argument("--template", help="模板文件路径(用于上传)")
    parser.add_argument("--id", help="模板ID(用于获取、更新、删除等操作)")
    parser.add_argument("--name", help="模板名称(用于上传、更新)")
    parser.add_argument("--description", help="模板描述(用于上传、更新)")
    parser.add_argument("--tags", help="模板标签,逗号分隔(用于上传、更新)")
    parser.add_argument("--no-delete", action="store_true", help="完整测试时不删除创建的模板")
    
    args = parser.parse_args()
    run_template_management_test(args) 