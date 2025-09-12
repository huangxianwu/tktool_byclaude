/**
 * 任务管理页面JavaScript逻辑
 */

class TaskManager {
    constructor() {
        this.tasks = [];
        this.selectedTasks = new Set();
        this.autoRefreshInterval = null;
        this.batchOperation = null;
        
        this.init();
    }
    
    init() {
        this.loadTasks();
        this.loadQueueStatus();
        this.bindEvents();
    }
    
    bindEvents() {
        // 页面卸载时清理定时器
        window.addEventListener('beforeunload', () => {
            if (this.autoRefreshInterval) {
                clearInterval(this.autoRefreshInterval);
            }
        });
    }
    
    async loadTasks() {
        this.showLoading(true);
        
        try {
            const response = await fetch('/api/tasks');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            this.tasks = await response.json();
            this.renderTasks();
            
        } catch (error) {
            console.error('加载任务失败:', error);
            this.showError('加载任务失败: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }
    
    async loadQueueStatus() {
        try {
            const response = await fetch('/api/tasks/queue/status');
            if (response.ok) {
                const status = await response.json();
                this.updateQueueStats(status);
            }
        } catch (error) {
            console.error('加载队列状态失败:', error);
        }
    }
    
    updateQueueStats(status) {
        document.getElementById('pending-count').textContent = status.pending_tasks || 0;
        document.getElementById('running-count').textContent = status.running_tasks || 0;
        document.getElementById('max-concurrent').textContent = status.max_concurrent || 1;
    }
    
    renderTasks() {
        const tbody = document.getElementById('task-list');
        const emptyState = document.getElementById('empty-state');
        
        if (!this.tasks || this.tasks.length === 0) {
            tbody.innerHTML = '';
            emptyState.style.display = 'block';
            return;
        }
        
        emptyState.style.display = 'none';
        
        tbody.innerHTML = this.tasks.map(task => this.renderTaskRow(task)).join('');
        this.updateSelectionState();
    }
    
    renderTaskRow(task) {
        const statusClass = `status-${task.status.toLowerCase()}`;
        const statusText = this.getStatusText(task.status);
        const createdAt = new Date(task.created_at).toLocaleString();
        const canStart = ['READY', 'FAILED', 'STOPPED', 'CANCELLED'].includes(task.status);
        const canStop = ['PENDING', 'QUEUED', 'RUNNING'].includes(task.status);
        
        return `
            <tr data-task-id=\"${task.task_id}\">
                <td>
                    <input type=\"checkbox\" class=\"task-checkbox\" value=\"${task.task_id}\" 
                           onchange=\"taskManager.toggleTaskSelection('${task.task_id}')\">
                </td>
                <td>
                    <strong>${task.workflow_name || 'Unknown'}</strong>
                </td>
                <td>
                    <code class="task-id">${task.task_id.substring(0, 8)}...</code>
                </td>
                <td>
                    <span class="task-description" title="${task.task_description || ''}">
                        ${task.task_description ? (task.task_description.length > 30 ? task.task_description.substring(0, 30) + '...' : task.task_description) : '无描述'}
                    </span>
                </td>
                <td>${task.node_count || 0}</td>
                <td>
                    <span class=\"plus-badge ${task.is_plus ? 'plus-yes' : 'plus-no'}\">${task.is_plus ? '是' : '否'}</span>
                </td>
                <td>
                    <span class=\"status-badge ${statusClass}\">${statusText}</span>
                </td>
                <td>
                    <span class=\"datetime\">${createdAt}</span>
                </td>
                <td>
                    <div class=\"task-actions\">
                        ${canStart ? `<button class=\"btn btn-success\" onclick=\"taskManager.startTask('${task.task_id}')\">启动</button>` : ''}
                        ${canStop ? `<button class=\"btn btn-warning\" onclick=\"taskManager.stopTask('${task.task_id}')\">停止</button>` : ''}
                        <button class=\"btn btn-secondary\" onclick=\"taskManager.showTaskDetail('${task.task_id}')\">详情</button>
                        <button class=\"btn btn-danger\" onclick=\"taskManager.deleteTask('${task.task_id}')\">删除</button>
                    </div>
                </td>
            </tr>
        `;
    }
    
    getStatusText(status) {
        const statusMap = {
            'READY': '就绪',
            'PENDING': '排队',
            'QUEUED': '队列中',
            'RUNNING': '运行中',
            'SUCCESS': '成功',
            'FAILED': '失败',
            'STOPPED': '已停止',
            'CANCELLED': '已取消'
        };
        return statusMap[status] || status;
    }
    
    toggleTaskSelection(taskId) {
        const checkbox = document.querySelector(`input[value=\"${taskId}\"]`);
        
        if (checkbox.checked) {
            this.selectedTasks.add(taskId);
        } else {
            this.selectedTasks.delete(taskId);
        }
        
        this.updateSelectionState();
    }
    
    updateSelectionState() {
        const selectedCount = this.selectedTasks.size;
        const totalCount = this.tasks.length;
        
        // 更新选择计数
        document.getElementById('selected-count').textContent = selectedCount;
        
        // 更新全选复选框状态
        const selectAllCheckbox = document.getElementById('select-all');
        if (selectedCount === 0) {
            selectAllCheckbox.indeterminate = false;
            selectAllCheckbox.checked = false;
        } else if (selectedCount === totalCount) {
            selectAllCheckbox.indeterminate = false;
            selectAllCheckbox.checked = true;
        } else {
            selectAllCheckbox.indeterminate = true;
            selectAllCheckbox.checked = false;
        }
        
        // 更新批量操作按钮状态
        this.updateBatchButtons();
    }
    
    updateBatchButtons() {
        const selectedTaskIds = Array.from(this.selectedTasks);
        const selectedTasks = this.tasks.filter(task => selectedTaskIds.includes(task.task_id));
        
        const startBtn = document.getElementById('batch-start-btn');
        const stopBtn = document.getElementById('batch-stop-btn');
        const deleteBtn = document.getElementById('batch-delete-btn');
        
        // 批量启动：所有选中任务都可以启动
        const canBatchStart = selectedTasks.length > 0 && 
            selectedTasks.every(task => ['READY', 'FAILED', 'STOPPED', 'CANCELLED'].includes(task.status));
        startBtn.disabled = !canBatchStart;
        
        // 批量停止：所有选中任务都可以停止
        const canBatchStop = selectedTasks.length > 0 && 
            selectedTasks.every(task => ['PENDING', 'QUEUED', 'RUNNING'].includes(task.status));
        stopBtn.disabled = !canBatchStop;
        
        // 批量删除：有选中任务即可删除
        deleteBtn.disabled = selectedTasks.length === 0;
    }
    
    async startTask(taskId) {
        try {
            const response = await fetch(`/api/tasks/${taskId}/start`, {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showSuccess(result.message);
                this.loadTasks();
                this.loadQueueStatus();
            } else {
                this.showError(result.error);
            }
        } catch (error) {
            this.showError('启动任务失败: ' + error.message);
        }
    }
    
    async stopTask(taskId) {
        try {
            const response = await fetch(`/api/tasks/${taskId}/stop`, {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showSuccess(result.message);
                this.loadTasks();
                this.loadQueueStatus();
            } else {
                this.showError(result.error);
            }
        } catch (error) {
            this.showError('停止任务失败: ' + error.message);
        }
    }
    
    async deleteTask(taskId) {
        if (!confirm('确定要删除这个任务吗？此操作不可恢复。')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/tasks/${taskId}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showSuccess(result.message);
                this.loadTasks();
                this.loadQueueStatus();
            } else {
                this.showError(result.error);
            }
        } catch (error) {
            this.showError('删除任务失败: ' + error.message);
        }
    }
    
    async showTaskDetail(taskId) {
        try {
            const response = await fetch(`/api/tasks/${taskId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const task = await response.json();
            this.renderTaskDetail(task);
            document.getElementById('task-detail-modal').style.display = 'block';
            
        } catch (error) {
            this.showError('获取任务详情失败: ' + error.message);
        }
    }
    
    renderTaskDetail(task) {
        const content = document.getElementById('task-detail-content');
        const createdAt = new Date(task.created_at).toLocaleString();
        const startedAt = task.started_at ? new Date(task.started_at).toLocaleString() : '未开始';
        const completedAt = task.completed_at ? new Date(task.completed_at).toLocaleString() : '未完成';
        
        content.innerHTML = `
            <div class="task-detail-section">
                <h4>基本信息</h4>
                <div class="detail-grid">
                    <div class="detail-item">
                        <label>任务ID:</label>
                        <span>${task.task_id}</span>
                    </div>
                    <div class="detail-item">
                        <label>工作流名称:</label>
                        <span>${task.workflow_name || 'Unknown'}</span>
                    </div>
                    <div class="detail-item">
                        <label>任务描述:</label>
                        <span>${task.task_description || '无描述'}</span>
                    </div>
                    <div class="detail-item">
                        <label>状态:</label>
                        <span class="status-badge status-${task.status.toLowerCase()}">${this.getStatusText(task.status)}</span>
                    </div>
                    <div class="detail-item">
                        <label>创建时间:</label>
                        <span>${createdAt}</span>
                    </div>
                    <div class="detail-item">
                        <label>开始时间:</label>
                        <span>${startedAt}</span>
                    </div>
                    <div class="detail-item">
                        <label>完成时间:</label>
                        <span>${completedAt}</span>
                    </div>
                    ${task.runninghub_task_id ? `
                    <div class="detail-item">
                        <label>RunningHub任务ID:</label>
                        <span>${task.runninghub_task_id}</span>
                    </div>
                    ` : ''}
                </div>
            </div>
            
            ${task.data && task.data.length > 0 ? `
            <div class="task-detail-section">
                <h4>输入参数</h4>
                <div class="task-data-list">
                    ${task.data.map(data => {
                        let valueDisplay = data.field_value;
                        // 如果是文件类型，显示预览
                        if (data.file_url) {
                            if (data.file_url.match(/\.(jpg|jpeg|png|gif)$/i)) {
                                valueDisplay = `<img src="${data.file_url}" alt="输入图片" style="max-width: 200px; border-radius: 4px;">`;
                            } else if (data.file_url.match(/\.(mp4|avi|mov)$/i)) {
                                valueDisplay = `<video controls style="max-width: 200px;"><source src="${data.file_url}"></video>`;
                            }
                        }
                        return `
                            <div class="task-data-item">
                                <strong>${data.field_name}:</strong>
                                <div class="field-value">${valueDisplay}</div>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
            ` : ''}
            
            <div class="task-detail-section">
                <h4>执行日志</h4>
                <div id="modal-execution-logs" class="log-stream modal-logs">
                    <div class="loading-logs">加载日志中...</div>
                </div>
            </div>
            
            <div class="task-detail-section">
                <div class="section-header">
                    <h4>输出结果</h4>
                    <button id="refresh-files-btn" class="btn btn-sm btn-outline-primary" onclick="taskManager.refreshTaskFiles('${task.task_id}')">
                        <i class="fas fa-sync-alt"></i> 更新文件
                    </button>
                </div>
                <div id="modal-result-preview" class="result-gallery modal-results">
                    <div class="loading-results">加载结果中...</div>
                </div>
            </div>
        `;
        
        // 加载日志和结果
        this.loadModalLogs(task.task_id);
        this.loadModalResults(task.task_id);
        
        // 添加样式
        if (!document.querySelector('#task-detail-styles')) {
            const styles = document.createElement('style');
            styles.id = 'task-detail-styles';
            styles.textContent = `
                .task-detail-section {
                    margin-bottom: 20px;
                }
                .task-detail-section h4 {
                    margin-bottom: 10px;
                    color: #333;
                }
                .section-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 10px;
                }
                .section-header h4 {
                    margin: 0;
                }
                #refresh-files-btn {
                    font-size: 12px;
                    padding: 4px 8px;
                }
                .detail-grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 10px;
                }
                .detail-item {
                    display: flex;
                    flex-direction: column;
                }
                .detail-item label {
                    font-weight: bold;
                    color: #666;
                    margin-bottom: 2px;
                }
                .task-data-item {
                    margin-bottom: 8px;
                    padding: 8px;
                    background: #f8f9fa;
                    border-radius: 4px;
                }
                .field-value {
                    margin-top: 4px;
                }
                .modal-logs {
                    max-height: 200px;
                    overflow-y: auto;
                    background: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    padding: 10px;
                    font-family: monospace;
                    font-size: 12px;
                }
                .modal-results {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                    gap: 15px;
                    max-height: 400px;
                    overflow-y: auto;
                }
                .result-card {
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    overflow: hidden;
                    background: white;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    transition: transform 0.2s, box-shadow 0.2s;
                }
                .result-card:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
                }
                .image-preview, .video-preview, .file-preview {
                    position: relative;
                    height: 150px;
                    overflow: hidden;
                }
                .image-preview img, .video-preview video {
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                    cursor: pointer;
                }
                .image-overlay, .video-overlay {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0,0,0,0.5);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    opacity: 0;
                    transition: opacity 0.2s;
                }
                .image-preview:hover .image-overlay,
                .video-preview:hover .video-overlay {
                    opacity: 1;
                }
                .btn-preview, .btn-play {
                    background: rgba(255,255,255,0.9);
                    border: none;
                    padding: 8px 12px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 14px;
                }
                .file-preview {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    background: #f8f9fa;
                    color: #666;
                }
                .file-icon {
                    font-size: 48px;
                    margin-bottom: 8px;
                }
                .file-name {
                    font-weight: bold;
                    font-size: 14px;
                }
                .card-info {
                    padding: 12px;
                }
                .card-title {
                    font-weight: bold;
                    margin-bottom: 8px;
                    color: #333;
                }
                .card-meta {
                    display: flex;
                    justify-content: space-between;
                    font-size: 12px;
                    color: #666;
                    margin-bottom: 10px;
                }
                .card-actions {
                    display: flex;
                    gap: 8px;
                }
                .btn {
                    padding: 6px 12px;
                    text-decoration: none;
                    border-radius: 4px;
                    font-size: 12px;
                    text-align: center;
                    flex: 1;
                }
                .btn-download {
                    background: #007bff;
                    color: white;
                }
                .btn-external {
                    background: #28a745;
                    color: white;
                }
                .btn:hover {
                    opacity: 0.8;
                }
                .log-entry {
                    margin-bottom: 4px;
                    word-wrap: break-word;
                }
                .log-timestamp {
                    color: #666;
                    margin-right: 8px;
                }
            `;
            document.head.appendChild(styles);
        }
    }
    
    async loadModalLogs(taskId) {
        try {
            const response = await fetch(`/api/tasks/${taskId}/logs/history`);
            if (response.ok) {
                const logs = await response.json();
                const container = document.getElementById('modal-execution-logs');
                
                if (logs.length === 0) {
                    container.innerHTML = '<div class="no-logs">暂无执行日志</div>';
                } else {
                    container.innerHTML = logs.map(log => {
                        const timestamp = new Date(log.created_at).toLocaleTimeString();
                        return `
                            <div class="log-entry">
                                <span class="log-timestamp">[${timestamp}]</span>
                                <span class="log-message">${log.message}</span>
                            </div>
                        `;
                    }).join('');
                    
                    // 滚动到底部
                    container.scrollTop = container.scrollHeight;
                }
            } else {
                document.getElementById('modal-execution-logs').innerHTML = '<div class="error-logs">加载日志失败</div>';
            }
        } catch (error) {
            console.error('加载日志失败:', error);
            document.getElementById('modal-execution-logs').innerHTML = '<div class="error-logs">加载日志失败</div>';
        }
    }
    
    async loadModalResults(taskId) {
        try {
            const response = await fetch(`/api/tasks/${taskId}/outputs`);
            if (response.ok) {
                const outputs = await response.json();
                const container = document.getElementById('modal-result-preview');
                
                if (!outputs || outputs.length === 0) {
                    container.innerHTML = '<div class="no-results">暂无输出结果</div>';
                } else {
                    container.innerHTML = outputs.map(output => this.createModalResultCard(output)).join('');
                    // 设置画廊监听器
                    this.setupModalGalleryListeners();
                }
            } else {
                document.getElementById('modal-result-preview').innerHTML = '<div class="error-results">加载结果失败</div>';
            }
        } catch (error) {
            console.error('加载结果失败:', error);
            document.getElementById('modal-result-preview').innerHTML = '<div class="error-results">加载结果失败</div>';
        }
    }
    
    createModalResultCard(output) {
        const isImage = output.file_type && output.file_type.toLowerCase().match(/^(png|jpg|jpeg|gif|bmp|webp)$/);
        const isVideo = output.file_type && output.file_type.toLowerCase().match(/^(mp4|avi|mov|wmv|flv)$/);
        
        let previewContent = '';
        
        if (isImage) {
            const thumbnailUrl = output.thumbnail_url || output.static_url;
            previewContent = `
                <div class="image-preview">
                    <img src="${thumbnailUrl}" alt="输出图片" loading="lazy" onclick="openImageModal('${output.static_url}')">
                    <div class="image-overlay">
                        <button class="btn-preview" onclick="openImageModal('${output.static_url}')">
                            🔍 预览
                        </button>
                    </div>
                </div>
            `;
        } else if (isVideo) {
            previewContent = `
                <div class="video-preview">
                    <video poster="${output.thumbnail_url || ''}" onclick="this.play()">
                        <source src="${output.static_url}" type="video/${output.file_type}">
                    </video>
                    <div class="video-overlay">
                        <button class="btn-play">
                            ▶️
                        </button>
                    </div>
                </div>
            `;
        } else {
            previewContent = `
                <div class="file-preview">
                    <div class="file-icon">
                        📄
                    </div>
                    <div class="file-name">${output.file_type ? output.file_type.toUpperCase() : 'FILE'}</div>
                </div>
            `;
        }
        
        const fileSize = this.formatFileSize(output.file_size);
        const createdTime = output.created_at ? new Date(output.created_at).toLocaleString() : '未知时间';
        
        return `
            <div class="result-card" data-file-type="${output.file_type || 'unknown'}">
                ${previewContent}
                <div class="card-info">
                    <div class="card-title">节点 ${output.node_id || 'unknown'}</div>
                    <div class="card-meta">
                        <span class="file-size">${fileSize}</span>
                        <span class="created-time">${createdTime}</span>
                    </div>
                    <div class="card-actions">
                        <a href="${output.static_url || output.url}" download class="btn btn-download">
                            ⬇️ 下载
                        </a>
                        <a href="${output.file_url || output.url}" target="_blank" class="btn btn-external">
                            🔗 原始链接
                        </a>
                    </div>
                </div>
            </div>
        `;
    }
    
    formatFileSize(bytes) {
        if (!bytes) return '未知大小';
        
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    }
    
    setupModalGalleryListeners() {
        // 为视频添加播放控制
        document.querySelectorAll('.video-preview video').forEach(video => {
            video.addEventListener('click', function() {
                if (this.paused) {
                    this.play();
                } else {
                    this.pause();
                }
            });
        });
    }
    
    openImageModal(imageSrc, imageTitle) {
        // 创建模态框HTML
        const modalHtml = `
            <div class="modal fade" id="imageModal" tabindex="-1" role="dialog">
                <div class="modal-dialog modal-lg" role="document">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${imageTitle}</h5>
                            <button type="button" class="close" data-dismiss="modal">
                                <span>&times;</span>
                            </button>
                        </div>
                        <div class="modal-body text-center">
                            <img src="${imageSrc}" class="img-fluid" alt="${imageTitle}">
                        </div>
                        <div class="modal-footer">
                            <a href="${imageSrc}" download class="btn btn-primary">下载图片</a>
                            <a href="${imageSrc}" target="_blank" class="btn btn-secondary">原始链接</a>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // 移除已存在的图片模态框
        const existingModal = document.getElementById('imageModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // 添加新的模态框到页面
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // 显示模态框
        $('#imageModal').modal('show');
        
        // 模态框关闭后移除DOM元素
        $('#imageModal').on('hidden.bs.modal', function() {
            this.remove();
        });
    }
    
    async refreshTaskFiles(taskId) {
        const refreshBtn = document.getElementById('refresh-files-btn');
        const originalText = refreshBtn.innerHTML;
        
        try {
            // 显示加载状态
            refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 更新中...';
            refreshBtn.disabled = true;
            
            // 调用后端API更新文件
            const response = await fetch(`/api/tasks/${taskId}/refresh-files`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                this.showSuccess(`成功更新 ${result.updated_count || 0} 个文件`);
                
                // 重新加载输出结果
                this.loadModalResults(taskId);
            } else {
                const error = await response.json();
                this.showError(error.message || '更新文件失败');
            }
        } catch (error) {
            console.error('更新文件失败:', error);
            this.showError('更新文件失败: ' + error.message);
        } finally {
            // 恢复按钮状态
            refreshBtn.innerHTML = originalText;
            refreshBtn.disabled = false;
        }
    }
    
    // 批量操作相关方法
    batchStartTasks() {
        const selectedTaskIds = Array.from(this.selectedTasks);
        this.showBatchConfirm('批量启动任务', `确定要启动选中的 ${selectedTaskIds.length} 个任务吗？`, 'start');
    }
    
    batchStopTasks() {
        const selectedTaskIds = Array.from(this.selectedTasks);
        this.showBatchConfirm('批量停止任务', `确定要停止选中的 ${selectedTaskIds.length} 个任务吗？`, 'stop');
    }
    
    batchDeleteTasks() {
        const selectedTaskIds = Array.from(this.selectedTasks);
        this.showBatchConfirm('批量删除任务', `确定要删除选中的 ${selectedTaskIds.length} 个任务吗？此操作不可恢复。`, 'delete');
    }
    
    showBatchConfirm(title, message, operation) {
        this.batchOperation = operation;
        document.getElementById('batch-confirm-title').textContent = title;
        document.getElementById('batch-confirm-message').textContent = message;
        document.getElementById('batch-confirm-modal').style.display = 'block';
    }
    
    async confirmBatchOperation() {
        const selectedTaskIds = Array.from(this.selectedTasks);
        
        if (selectedTaskIds.length === 0) {
            this.closeBatchConfirm();
            return;
        }
        
        try {
            let url = '';
            let method = '';
            
            switch (this.batchOperation) {
                case 'start':
                    url = '/api/tasks/batch/start';
                    method = 'POST';
                    break;
                case 'stop':
                    url = '/api/tasks/batch/stop';
                    method = 'POST';
                    break;
                case 'delete':
                    url = '/api/tasks/batch/delete';
                    method = 'DELETE';
                    break;
            }
            
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ task_ids: selectedTaskIds })
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showSuccess(result.message);
                this.selectedTasks.clear();
                this.loadTasks();
                this.loadQueueStatus();
            } else {
                this.showError(result.error);
            }
            
        } catch (error) {
            this.showError('批量操作失败: ' + error.message);
        } finally {
            this.closeBatchConfirm();
        }
    }
    
    closeBatchConfirm() {
        document.getElementById('batch-confirm-modal').style.display = 'none';
        this.batchOperation = null;
    }
    
    closeTaskDetail() {
        document.getElementById('task-detail-modal').style.display = 'none';
    }
    
    // 工具方法
    toggleSelectAll() {
        const selectAllCheckbox = document.getElementById('select-all');
        const taskCheckboxes = document.querySelectorAll('.task-checkbox');
        
        taskCheckboxes.forEach(checkbox => {
            checkbox.checked = selectAllCheckbox.checked;
            if (selectAllCheckbox.checked) {
                this.selectedTasks.add(checkbox.value);
            } else {
                this.selectedTasks.delete(checkbox.value);
            }
        });
        
        this.updateSelectionState();
    }
    
    refreshTasks() {
        this.loadTasks();
        this.loadQueueStatus();
    }
    
    toggleAutoRefresh() {
        const autoRefreshCheckbox = document.getElementById('auto-refresh');
        
        if (autoRefreshCheckbox.checked) {
            // 启动自动刷新，每10秒刷新一次
            this.autoRefreshInterval = setInterval(() => {
                this.loadTasks();
                this.loadQueueStatus();
            }, 10000);
        } else {
            // 停止自动刷新
            if (this.autoRefreshInterval) {
                clearInterval(this.autoRefreshInterval);
                this.autoRefreshInterval = null;
            }
        }
    }
    
    showLoading(show) {
        document.getElementById('loading').style.display = show ? 'block' : 'none';
    }
    
    showSuccess(message) {
        this.showMessage(message, 'success');
    }
    
    showError(message) {
        this.showMessage(message, 'error');
    }
    
    showMessage(message, type) {
        // 创建消息提示框
        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${type}`;
        messageDiv.textContent = message;
        
        // 添加样式（如果还没有）
        if (!document.querySelector('#message-styles')) {
            const styles = document.createElement('style');
            styles.id = 'message-styles';
            styles.textContent = `
                .message {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    padding: 12px 20px;
                    border-radius: 4px;
                    z-index: 1001;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                    animation: slideIn 0.3s ease-out;
                }
                .message-success {
                    background: #d4edda;
                    color: #155724;
                    border: 1px solid #c3e6cb;
                }
                .message-error {
                    background: #f8d7da;
                    color: #721c24;
                    border: 1px solid #f5c6cb;
                }
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
            `;
            document.head.appendChild(styles);
        }
        
        document.body.appendChild(messageDiv);
        
        // 3秒后自动移除
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.parentNode.removeChild(messageDiv);
            }
        }, 3000);
    }
}

// 全局变量和函数（供HTML调用）
let taskManager;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    taskManager = new TaskManager();
});

// 全局函数（供HTML模板调用）
function refreshTasks() {
    taskManager.refreshTasks();
}

function toggleAutoRefresh() {
    taskManager.toggleAutoRefresh();
}

function toggleSelectAll() {
    taskManager.toggleSelectAll();
}

function batchStartTasks() {
    taskManager.batchStartTasks();
}

function batchStopTasks() {
    taskManager.batchStopTasks();
}

function batchDeleteTasks() {
    taskManager.batchDeleteTasks();
}

function confirmBatchOperation() {
    taskManager.confirmBatchOperation();
}

function closeBatchConfirm() {
    taskManager.closeBatchConfirm();
}

function closeTaskDetail() {
    taskManager.closeTaskDetail();
}

// 点击模态框外部关闭
window.addEventListener('click', (event) => {
    const batchModal = document.getElementById('batch-confirm-modal');
    const detailModal = document.getElementById('task-detail-modal');
    
    if (event.target === batchModal) {
        taskManager.closeBatchConfirm();
    }
    if (event.target === detailModal) {
        taskManager.closeTaskDetail();
    }
});