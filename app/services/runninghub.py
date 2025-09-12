import requests
import json
import uuid
from datetime import datetime
from flask import current_app
from app.models import TaskLog
from app import db

class RunningHubService:
    def __init__(self):
        self.base_url = None
        self.api_key = None
        
    def _ensure_config(self):
        """确保配置已加载"""
        if self.base_url is None:
            self.base_url = current_app.config['RUNNINGHUB_BASE_URL']
            self.api_key = current_app.config['RUNNINGHUB_API_KEY']
    
    def upload_file(self, file_data, filename, task_id=None):
        """上传文件到RunningHub"""
        self._ensure_config()
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
    
    def run_task(self, node_info_list, task_id, workflow_id, is_plus=False):
        """运行任务"""
        self._ensure_config()
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
            
            # 如果是Plus实例，添加instanceType参数
            if is_plus:
                request_data["instanceType"] = "plus"
                self._log(task_id, "⚡ 使用Plus实例 (48G显存机器)")
            
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
        """获取任务状态"""
        self._ensure_config()
        
        self._log(task_id, f"🔍 开始查询任务状态 (远程ID: {runninghub_task_id})")
        
        try:
            request_data = {
                "apiKey": self.api_key,
                "taskId": runninghub_task_id
            }
            
            self._log(task_id, f"📡 发起状态查询请求到: {self.base_url}/status")
            self._log(task_id, f"📋 请求参数: {json.dumps(request_data, ensure_ascii=False)}")
            
            response = requests.post(
                f"{self.base_url}/status",
                json=request_data,
                headers={'Content-Type': 'application/json'}
            )
            
            self._log(task_id, f"📡 状态查询响应码: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    self._log(task_id, f"📊 状态查询响应: {json.dumps(result, ensure_ascii=False)}")
                except Exception as parse_error:
                    self._log(task_id, f"❌ 状态查询响应解析失败: {str(parse_error)}")
                    self._log(task_id, f"📡 原始响应: {response.text}")
                    return None
                
                if result.get('code') == 0:
                    # 处理两种可能的响应格式
                    data = result.get('data', {})
                    
                    # 格式1: data是对象 {"taskStatus": "RUNNING"}
                    if isinstance(data, dict) and 'taskStatus' in data:
                        status = data['taskStatus']
                        self._log(task_id, f"✅ 状态查询成功: {status} (格式1: 对象)")
                        return status
                    # 格式2: data直接是状态字符串 "RUNNING"
                    elif isinstance(data, str):
                        status = data
                        self._log(task_id, f"✅ 状态查询成功: {status} (格式2: 字符串)")
                        return status
                    else:
                        self._log(task_id, f"❌ 状态查询响应格式异常: data={data} (type: {type(data)})")
                        return None
                else:
                    error_code = result.get('code', 'N/A')
                    error_msg = result.get('msg', 'Unknown error')
                    self._log(task_id, f"❌ 状态查询失败 - 错误代码: {error_code}")
                    self._log(task_id, f"❌ 状态查询失败 - 错误信息: {error_msg}")
                    return None
            else:
                self._log(task_id, f"❌ 状态查询HTTP错误: {response.status_code}")
                self._log(task_id, f"❌ HTTP错误详情: {response.text}")
                return None
                
        except Exception as e:
            self._log(task_id, f"❌ 状态查询异常: {str(e)}")
            self._log(task_id, f"❌ 异常类型: {type(e).__name__}")
            import traceback
            self._log(task_id, f"❌ 异常堆栈: {traceback.format_exc()}")
            return None
    
    def get_outputs(self, runninghub_task_id, task_id):
        """获取任务结果"""
        self._ensure_config()
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
    
    def create_task(self, workflow_id, task_data, is_plus=False):
        """创建任务（新接口方法）"""
        self._ensure_config()
        # 转换为旧接口格式
        node_info_list = []
        for data in task_data:
            node_info_list.append({
                'nodeId': data['node_id'],
                'fieldName': data['field_name'],
                'fieldValue': data['field_value']
            })
        
        # 生成临时task_id用于日志
        temp_task_id = str(uuid.uuid4())[:8]
        
        try:
            current_app.logger.info(f"Creating task with workflow_id: {workflow_id}, node_info_list: {node_info_list}")
            runninghub_task_id = self.run_task(node_info_list, temp_task_id, workflow_id, is_plus)
            current_app.logger.info(f"Task created successfully with runninghub_task_id: {runninghub_task_id}")
            return {'taskId': runninghub_task_id}
        except Exception as e:
            error_msg = str(e)
            current_app.logger.error(f"Failed to create task: {error_msg}")
            current_app.logger.error(f"Workflow ID: {workflow_id}, Node info: {node_info_list}")
            
            # 如果是TASK_QUEUE_MAXED错误，需要特殊处理
            if 'TASK_QUEUE_MAXED' in error_msg:
                current_app.logger.info("RunningHub queue is full, task should remain in PENDING status")
            
            # 重新抛出异常以便上层处理
            raise e
            return None
    
    def get_task_status(self, runninghub_task_id):
        """获取任务状态（新接口方法）"""
        self._ensure_config()
        temp_task_id = str(uuid.uuid4())[:8]
        status = self.get_status(runninghub_task_id, temp_task_id)
        if status:
            return {'status': status}
        return None
    
    def get_task_progress(self, runninghub_task_id):
        """获取任务进度"""
        self._ensure_config()
        # RunningHub目前可能不支持进度查询，返回基于状态的简单进度
        status_info = self.get_task_status(runninghub_task_id)
        if status_info:
            status = status_info.get('status', '')
            if status == 'queue':
                return {'progress': 0, 'message': '排队中'}
            elif status == 'running':
                return {'progress': 50, 'message': '执行中'}
            elif status == 'success':
                return {'progress': 100, 'message': '完成'}
            elif status == 'failed':
                return {'progress': 0, 'message': '失败'}
        return None
    
    def get_task_outputs(self, runninghub_task_id):
        """获取任务输出列表"""
        self._ensure_config()
        temp_task_id = str(uuid.uuid4())[:8]
        outputs = self.get_outputs(runninghub_task_id, temp_task_id)
        if outputs:
            # 转换为文件列表格式
            file_list = []
            for output in outputs:
                if isinstance(output, dict) and 'fileUrl' in output:
                    # 从fileUrl中提取文件名
                    file_url = output['fileUrl']
                    file_name = file_url.split('/')[-1] if '/' in file_url else 'output.file'
                    
                    # 从fileType或URL中推断文件类型
                    file_type = output.get('fileType', '')
                    if not file_type and '.' in file_name:
                        file_type = file_name.split('.')[-1]
                    
                    file_list.append({
                        'name': file_name,
                        'url': file_url,
                        'type': file_type,
                        'node_id': output.get('nodeId', '')
                    })
            return file_list
        return []
    
    def download_output_file(self, runninghub_task_id, output_name):
        """下载输出文件"""
        self._ensure_config()
        outputs = self.get_task_outputs(runninghub_task_id)
        for output in outputs:
            if output['name'] == output_name:
                try:
                    response = requests.get(output['url'])
                    if response.status_code == 200:
                        return response.content
                except Exception as e:
                    current_app.logger.error(f"Failed to download file: {e}")
        return None
    
    def cancel_task(self, runninghub_task_id):
        """取消任务"""
        self._ensure_config()
        # RunningHub可能不支持任务取消，返回True表示已处理
        # 实际实现中可以调用相应的API
        return True
    
    def check_account_status(self, task_id=None):
        """检查账号状态，返回当前任务数量"""
        self._ensure_config()
        try:
            # 构建查询账号状态的请求
            response = requests.get(
                f"{self.base_url}/account/status",
                params={"apiKey": self.api_key},
                headers={'Content-Type': 'application/json'}
            )
            
            if task_id:
                self._log(task_id, f"📊 查询账号状态: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    current_task_counts = result.get('data', {}).get('currentTaskCounts', 0)
                    if task_id:
                        self._log(task_id, f"📊 当前任务数量: {current_task_counts}")
                    return current_task_counts
            
            if task_id:
                self._log(task_id, f"❌ 查询账号状态失败: {response.text}")
            return None
            
        except Exception as e:
            if task_id:
                self._log(task_id, f"❌ 查询账号状态异常: {str(e)}")
            return None
    
    def wait_for_available_slot(self, task_id, max_wait_minutes=30):
        """等待可用槽位，每10秒检查一次"""
        import time
        
        self._log(task_id, "⏳ 开始检查RunningHub账号任务状态...")
        
        start_time = time.time()
        max_wait_seconds = max_wait_minutes * 60
        
        while True:
            current_tasks = self.check_account_status(task_id)
            
            if current_tasks is None:
                self._log(task_id, "❌ 无法获取账号状态，继续执行任务")
                return True
            
            if current_tasks == 0:
                self._log(task_id, "✅ 账号无正在执行的任务，可以启动新任务")
                return True
            
            # 检查是否超时
            elapsed = time.time() - start_time
            if elapsed > max_wait_seconds:
                self._log(task_id, f"⏰ 等待超时({max_wait_minutes}分钟)，停止等待")
                return False
            
            self._log(task_id, f"⏳ 账号有{current_tasks}个任务在执行，10秒后重新检查...")
            time.sleep(10)

    def _log(self, task_id, message):
        """记录任务日志"""
        try:
            log = TaskLog(task_id=task_id, message=message)
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            current_app.logger.error(f"Failed to log message: {e}")