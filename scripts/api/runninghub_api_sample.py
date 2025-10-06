#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立脚本：上传图片 → 创建任务 → 查询状态 → 获取结果
- 仅依赖 requests（如未安装：pip install requests）
- 使用官方API文档格式，只传递图片路径参数
"""
import os
import time
import json
import typing as t
import requests

# === 必填配置 ===
RUNNINGHUB_BASE_URL = "https://www.runninghub.cn/task/openapi"
RUNNINGHUB_API_KEY = "d4b17e6ea9474695965f3f3c9dd53c1d"
WORKFLOW_ID = "1956307610033160194"

# 示例输入（来自仓库）
PRODUCT_IMAGE_PATH = "archive_for_cleanup/产品图.png"
MODEL_IMAGE_PATH = "archive_for_cleanup/模特图.png"

# 节点映射（来自工作流导出）
NODES = [
    {"node_id": "156", "field_name": "image", "path": PRODUCT_IMAGE_PATH, "description": "产品图"},
    {"node_id": "145", "field_name": "image", "path": MODEL_IMAGE_PATH, "description": "模特图"},
]

# === HTTP helpers ===
DEFAULT_TIMEOUT = 60  # 增加超时时间到60秒
HEADERS_JSON = {"Content-Type": "application/json"}
MAX_RETRIES = 3  # 最大重试次数

class RHClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def upload_file(self, file_path: str, filename: t.Optional[str] = None) -> str:
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        fname = filename or os.path.basename(file_path)
        
        # 重试机制
        for attempt in range(MAX_RETRIES):
            try:
                with open(file_path, "rb") as f:
                    files = {"file": (fname, f)}
                    data = {"apiKey": self.api_key}
                    print(f"    尝试上传 {fname} (第 {attempt + 1}/{MAX_RETRIES} 次)...")
                    resp = requests.post(f"{self.base_url}/upload", data=data, files=files, timeout=DEFAULT_TIMEOUT)
                
                if resp.status_code != 200:
                    raise RuntimeError(f"Upload HTTP {resp.status_code}: {resp.text}")
                body = resp.json()
                if body.get("code") != 0:
                    raise RuntimeError(f"Upload failed: {body.get('msg')}")
                return body["data"]["fileName"]
                
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                if attempt < MAX_RETRIES - 1:
                    wait_time = (attempt + 1) * 5  # 递增等待时间
                    print(f"    网络超时，{wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    raise RuntimeError(f"上传失败，已重试 {MAX_RETRIES} 次: {str(e)}")
            except Exception as e:
                raise RuntimeError(f"上传出错: {str(e)}")

    def create_task(self, workflow_id: str, node_info_list: list) -> str:
        payload = {
            "apiKey": self.api_key,
            "workflowId": workflow_id,
            "nodeInfoList": node_info_list
        }
        
        # 打印API参数
        print("=== API 参数 ===")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print("================")
        
        # 重试机制
        for attempt in range(MAX_RETRIES):
            try:
                print(f"    尝试创建任务 (第 {attempt + 1}/{MAX_RETRIES} 次)...")
                resp = requests.post(f"{self.base_url}/create", json=payload, headers=HEADERS_JSON, timeout=DEFAULT_TIMEOUT)
                if resp.status_code != 200:
                    raise RuntimeError(f"Create HTTP {resp.status_code}: {resp.text}")
                body = resp.json()
                if body.get("code") != 0:
                    raise RuntimeError(f"Create failed: {body.get('msg')}")
                return body["data"]["taskId"]
                
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                if attempt < MAX_RETRIES - 1:
                    wait_time = (attempt + 1) * 5
                    print(f"    网络超时，{wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    raise RuntimeError(f"创建任务失败，已重试 {MAX_RETRIES} 次: {str(e)}")
            except Exception as e:
                raise RuntimeError(f"创建任务出错: {str(e)}")

    def get_status(self, task_id: str) -> dict:
        payload = {"apiKey": self.api_key, "taskId": task_id}
        resp = requests.post(f"{self.base_url}/status", json=payload, headers=HEADERS_JSON, timeout=DEFAULT_TIMEOUT)
        if resp.status_code != 200:
            raise RuntimeError(f"Status HTTP {resp.status_code}: {resp.text}")
        return resp.json()

    def get_outputs(self, task_id: str) -> dict:
        payload = {"apiKey": self.api_key, "taskId": task_id}
        resp = requests.post(f"{self.base_url}/outputs", json=payload, headers=HEADERS_JSON, timeout=DEFAULT_TIMEOUT)
        if resp.status_code != 200:
            raise RuntimeError(f"Outputs HTTP {resp.status_code}: {resp.text}")
        return resp.json()


def main():
    client = RHClient(RUNNINGHUB_BASE_URL, RUNNINGHUB_API_KEY)

    print("[1/3] 上传图片到 RunningHub...")
    uploaded_map = {}
    for node in NODES:
        file_path = node["path"]
        file_name = client.upload_file(file_path)
        uploaded_map[node["node_id"]] = file_name
        print(f"  - {node['description']} → fileName={file_name}")

    print("[2/3] 准备节点信息列表...")
    
    # 构建nodeInfoList，只传递图片路径参数
    node_info_list = []
    for node in NODES:
        filename = uploaded_map[node["node_id"]]
        # 保留完整的fileName，包括api/前缀
        
        node_info = {
            "nodeId": node["node_id"],
            "fieldName": node["field_name"],
            "fieldValue": filename
        }
        node_info_list.append(node_info)
        print(f"  - 节点 {node['node_id']} ({node['description']}): {node['field_name']} = {filename}")

    print("[3/3] 创建任务...")
    task_id = client.create_task(WORKFLOW_ID, node_info_list)
    print(f"  → 远程 taskId: {task_id}")

    print("[4/4] 轮询任务状态...")
    start = time.time()
    max_wait_sec = 1800  # 最多等待 30 分钟
    interval_sec = 5
    last_status = None
    while True:
        status_body = client.get_status(task_id)
        if status_body.get("code") != 0:
            raise RuntimeError(f"Status failed: {status_body.get('msg')}")
        data = status_body.get("data", {})
        
        # 处理 data 可能是字符串的情况
        if isinstance(data, str):
            status = data  # 如果 data 本身就是状态字符串
        elif isinstance(data, dict):
            status = data.get("status")
        else:
            status = str(data)  # 其他情况转为字符串
            
        if status != last_status:
            status_display = {
                "RUNNING": "🔄 运行中",
                "SUCCESS": "✅ 成功",
                "FAILED": "❌ 失败",
                "PENDING": "⏳ 等待中"
            }.get(status, f"📊 {status}")
            print(f"  - {status_display}")
            last_status = status
            
        if status in ("success", "failed", "SUCCESS", "FAILED", "completed", "error"):
            break
        if time.time() - start > max_wait_sec:
            raise TimeoutError("等待任务结果超时")
        time.sleep(interval_sec)

    print("[4/4] 获取任务结果...")
    
    outputs_body = client.get_outputs(task_id)
    
    if outputs_body.get("code") != 0:
        error_msg = outputs_body.get('msg', 'Unknown error')
        print(f"  ❌ 获取输出失败: {error_msg}")
        
        # 如果有详细错误信息，显示给用户
        if outputs_body.get("data") and isinstance(outputs_body["data"], dict):
            failed_reason = outputs_body["data"].get("failedReason", {})
            if failed_reason:
                print(f"  📋 错误详情:")
                print(f"    - 节点: {failed_reason.get('node_name', 'Unknown')}")
                print(f"    - 错误类型: {failed_reason.get('exception_type', 'Unknown')}")
                print(f"    - 错误信息: {failed_reason.get('exception_message', 'No details')}")
        return
    
    outputs = outputs_body.get("data", [])
    if outputs:
        print("  ✅ 成功获取任务结果:")
        print(json.dumps(outputs, ensure_ascii=False, indent=2))
    else:
        print("  ⚠️ 任务完成但没有输出结果")

    # 可选：下载所有结果到本地
    out_dir = "outputs_download"
    os.makedirs(out_dir, exist_ok=True)
    for i, item in enumerate(outputs):
        if isinstance(item, dict) and item.get("fileUrl"):
            url = item["fileUrl"]
            try:
                r = requests.get(url, timeout=DEFAULT_TIMEOUT)
                if r.status_code == 200:
                    # 从 URL 推断文件名
                    name = url.split("/")[-1] or f"output_{i}.bin"
                    save_path = os.path.join(out_dir, name)
                    with open(save_path, "wb") as f:
                        f.write(r.content)
                    print(f"  - 已下载: {save_path}")
                else:
                    print(f"  - 下载失败 HTTP {r.status_code}: {url}")
            except Exception as e:
                print(f"  - 下载异常: {e}")

if __name__ == "__main__":
    main()