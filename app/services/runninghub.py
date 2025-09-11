import requests
import json
from datetime import datetime
from flask import current_app
from app.models import TaskLog
from app import db

class RunningHubService:
    def __init__(self):
        self.base_url = current_app.config['RUNNINGHUB_BASE_URL']
        self.api_key = current_app.config['RUNNINGHUB_API_KEY']
    
    def upload_file(self, file_data, filename, task_id=None):
        """上传文件到RunningHub"""
        try:
            files = {'file': (filename, file_data)}
            data = {'apiKey': self.api_key}
            
            # 记录上传请求详情
            if task_id:
                self._log(task_id, f"📤 准备上传文件: {filename}, 大小: {len(file_data)} bytes")
                self._log(task_id, f"📤 上传到: {self.base_url}/upload")
            
            response = requests.post(f"{self.base_url}/upload", data=data, files=files)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    file_name = result['data']['fileName']
                    
                    # 记录上传成功日志
                    if task_id:
                        self._log(task_id, f"📤 文件上传成功 → fileName={file_name}")
                    
                    return file_name
                else:
                    error_msg = result.get('msg', 'Unknown error')
                    if task_id:
                        self._log(task_id, f"❌ 文件上传失败: {error_msg}")
                    raise Exception(f"Upload failed: {error_msg}")
            else:
                if task_id:
                    self._log(task_id, f"❌ 文件上传HTTP错误: {response.status_code}")
                raise Exception(f"HTTP error: {response.status_code}")
                
        except Exception as e:
            if task_id:
                self._log(task_id, f"❌ 文件上传异常: {str(e)}")
            raise
    
    def run_task(self, node_info_list, task_id, workflow_id):
        """发起AI任务"""
        try:
            # 详细记录配置信息
            self._log(task_id, f"🔧 配置信息 - apiKey: {self.api_key[:8]}...{self.api_key[-4:]}")
            self._log(task_id, f"🔧 配置信息 - baseUrl: {self.base_url}")
            
            # 详细记录节点信息
            self._log(task_id, f"📋 节点信息总数: {len(node_info_list)}")
            for i, node in enumerate(node_info_list):
                self._log(task_id, f"📋 节点[{i}] - nodeId: {node.get('nodeId', 'N/A')}")
                self._log(task_id, f"📋 节点[{i}] - fieldName: {node.get('fieldName', 'N/A')}")
                field_value = node.get('fieldValue', 'N/A')
                if len(str(field_value)) > 100:
                    self._log(task_id, f"📋 节点[{i}] - fieldValue: {str(field_value)[:100]}...(截断)")
                else:
                    self._log(task_id, f"📋 节点[{i}] - fieldValue: {field_value}")
            
            # 构建请求参数
            request_data = {
                "workflowId": workflow_id,
                "apiKey": self.api_key,
                "nodeInfoList": node_info_list
            }
            
            self._log(task_id, "🚀 准备调用 create，完整请求参数：")
            self._log(task_id, json.dumps(request_data, ensure_ascii=False, indent=2))
            
            # 发起API请求 - 使用创建任务接口
            self._log(task_id, f"📡 发起POST请求到: `{self.base_url}/create`")
            response = requests.post(
                f"{self.base_url}/create",
                json=request_data,
                headers={'Content-Type': 'application/json'}
            )
            
            # 详细记录响应信息
            self._log(task_id, f"📡 响应状态码: {response.status_code}")
            self._log(task_id, f"📡 响应头: {dict(response.headers)}")
            
            try:
                response_text = response.text
                self._log(task_id, f"📡 响应原始内容: {response_text}")
                result = response.json()
                self._log(task_id, f"📡 响应JSON解析: {json.dumps(result, ensure_ascii=False, indent=2)}")
            except Exception as parse_error:
                self._log(task_id, f"❌ 响应JSON解析失败: {str(parse_error)}")
                self._log(task_id, f"📡 响应原始文本: {response.text}")
                raise Exception(f"Response parsing failed: {str(parse_error)}")
            
            if response.status_code == 200:
                if result.get('code') == 0:
                    runninghub_task_id = result['data']['taskId']
                    self._log(task_id, f"✅ 任务发起成功，taskId={runninghub_task_id}")
                    return runninghub_task_id
                else:
                    error_code = result.get('code', 'N/A')
                    error_msg = result.get('msg', 'Unknown error')
                    self._log(task_id, f"❌ 任务发起失败 - 错误代码: {error_code}")
                    self._log(task_id, f"❌ 任务发起失败 - 错误信息: {error_msg}")
                    
                    # 特殊处理APIKEY_INVALID_NODE_INFO错误
                    if 'APIKEY_INVALID_NODE_INFO' in str(error_msg):
                        self._log(task_id, "🔍 APIKEY_INVALID_NODE_INFO错误分析:")
                        self._log(task_id, "   - 可能原因1: nodeId不存在于工作流中")
                        self._log(task_id, "   - 可能原因2: fieldName与节点定义不匹配")
                        self._log(task_id, "   - 可能原因3: fieldValue格式不正确")
                        self._log(task_id, "   - 可能原因4: API密钥权限不足")
                    
                    raise Exception(f"Run task failed: {error_msg}")
            else:
                self._log(task_id, f"❌ 任务发起HTTP错误: {response.status_code}")
                self._log(task_id, f"❌ HTTP错误详情: {response.text}")
                raise Exception(f"HTTP error: {response.status_code}")
                
        except Exception as e:
            self._log(task_id, f"❌ 任务发起异常: {str(e)}")
            self._log(task_id, f"❌ 异常类型: {type(e).__name__}")
            import traceback
            self._log(task_id, f"❌ 异常堆栈: {traceback.format_exc()}")
            raise
    
    def get_status(self, runninghub_task_id, task_id):
        """查询任务状态"""
        try:
            request_data = {
                "apiKey": self.api_key,
                "taskId": runninghub_task_id
            }
            
            response = requests.post(
                f"{self.base_url}/status",
                json=request_data,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    # 处理两种可能的响应格式
                    data = result.get('data', {})
                    
                    # 格式1: data是对象 {"taskStatus": "RUNNING"}
                    if isinstance(data, dict) and 'taskStatus' in data:
                        status = data['taskStatus']
                        self._log(task_id, f"🔄 任务状态: {status}")
                        return status
                    # 格式2: data直接是状态字符串 "RUNNING"
                    elif isinstance(data, str):
                        status = data
                        self._log(task_id, f"🔄 任务状态: {status}")
                        return status
                    else:
                        self._log(task_id, f"❌ 状态查询响应格式异常: data={data} (type: {type(data)})")
                        return None
                else:
                    error_msg = result.get('msg', 'Unknown error')
                    self._log(task_id, f"❌ 状态查询失败: {error_msg}")
                    return None
            else:
                self._log(task_id, f"❌ 状态查询HTTP错误: {response.status_code}")
                return None
                
        except Exception as e:
            self._log(task_id, f"❌ 状态查询异常: {str(e)}")
            return None
    
    def get_outputs(self, runninghub_task_id, task_id):
        """获取任务结果"""
        try:
            request_data = {
                "apiKey": self.api_key,
                "taskId": runninghub_task_id
            }
            
            response = requests.post(
                f"{self.base_url}/outputs",
                json=request_data,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    # 安全检查：确保data是列表类型
                    data = result.get('data', [])
                    if isinstance(data, list):
                        outputs = data
                        for output in outputs:
                            if isinstance(output, dict) and 'fileUrl' in output:
                                file_url = output['fileUrl']
                                self._log(task_id, f"✅ 结果获取成功，fileUrl={file_url}")
                        return outputs
                    else:
                        self._log(task_id, f"❌ 结果获取响应格式异常: data={data}")
                        return None
                else:
                    error_msg = result.get('msg', 'Unknown error')
                    self._log(task_id, f"❌ 结果获取失败: {error_msg}")
                    return None
            else:
                self._log(task_id, f"❌ 结果获取HTTP错误: {response.status_code}")
                return None
                
        except Exception as e:
            self._log(task_id, f"❌ 结果获取异常: {str(e)}")
            return None
    
    def _log(self, task_id, message):
        """记录任务日志"""
        try:
            log = TaskLog(task_id=task_id, message=message)
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            current_app.logger.error(f"Failed to log message: {e}")