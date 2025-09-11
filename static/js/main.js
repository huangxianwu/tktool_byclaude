// 全局工具函数

// 显示消息
export function showMessage(message, type = 'info') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${type}`;
    messageDiv.textContent = message;
    messageDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 4px;
        color: white;
        z-index: 10000;
        max-width: 300px;
    `;
    
    if (type === 'success') {
        messageDiv.style.background = '#27ae60';
    } else if (type === 'error') {
        messageDiv.style.background = '#e74c3c';
    } else {
        messageDiv.style.background = '#3498db';
    }
    
    document.body.appendChild(messageDiv);
    
    setTimeout(() => {
        messageDiv.remove();
    }, 3000);
}

// 格式化JSON显示
export function formatJSON(jsonString) {
    try {
        const obj = JSON.parse(jsonString);
        return JSON.stringify(obj, null, 2);
    } catch {
        return jsonString;
    }
}

// 文件上传函数
export async function uploadFile(file, taskId = null) {
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/tasks/upload', {
            method: 'POST',
            body: formData,
            headers: taskId ? {'X-Task-ID': taskId} : {}
        });
        
        if (response.ok) {
            const result = await response.json();
            return result.fileName;
        } else {
            throw new Error('文件上传失败');
        }
    } catch (error) {
        console.error('文件上传错误:', error);
        throw error;
    }
}

// 处理任务创建表单
export async function handleTaskCreation(formData, workflowId) {
    try {
        const taskData = [];
        
        // 处理文件上传
        for (const [nodeId, value] of formData.entries()) {
            if (value instanceof File) {
                // 上传文件并获取fileName
                const fileName = await uploadFile(value);
                taskData.push({
                    node_id: nodeId,
                    field_value: fileName,
                    field_name: value.name
                });
            } else {
                taskData.push({
                    node_id: nodeId,
                    field_value: value,
                    field_name: nodeId
                });
            }
        }
        
        // 创建任务
        const response = await fetch('/api/tasks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                workflow_id: workflowId,
                data: taskData
            })
        });
        
        if (response.ok) {
            const task = await response.json();
            showMessage('任务创建成功！', 'success');
            return task;
        } else {
            throw new Error('创建任务失败');
        }
        
    } catch (error) {
        console.error('任务创建错误:', error);
        showMessage('任务创建失败: ' + error.message, 'error');
        throw error;
    }
}

// 初始化页面
document.addEventListener('DOMContentLoaded', function() {
    // 添加全局错误处理
    window.addEventListener('error', function(e) {
        console.error('全局错误:', e.error);
        showMessage('发生错误: ' + e.error.message, 'error');
    });
    
    // 添加未处理的Promise拒绝处理
    window.addEventListener('unhandledrejection', function(e) {
        console.error('未处理的Promise拒绝:', e.reason);
        showMessage('操作失败: ' + e.reason.message, 'error');
        e.preventDefault();
    });
});

// 导出全局函数
window.showMessage = showMessage;
window.formatJSON = formatJSON;
window.uploadFile = uploadFile;
window.handleTaskCreation = handleTaskCreation;