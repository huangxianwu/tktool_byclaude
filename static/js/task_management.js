/**
 * 任务管理页面JavaScript逻辑
 */

class TaskManager {
    constructor() {
        this.tasks = [];
        this.filteredTasks = [];
        this.selectedTasks = new Set();
        this.autoRefreshInterval = null;
        this.currentPage = 1;
        this.pageSize = 20;
        this.totalTasks = 0;
        this.batchOperation = null;
        this.workflows = [];
        this.filters = {
            status: '',
            workflow: '',
            timeRange: '',
            search: '',
            sort: 'created_at_desc',
            startDate: '',
            endDate: ''
        };
        
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
        
        // 绑定筛选事件
        this.bindFilterEvents();
    }
    
    bindFilterEvents() {
        // 状态筛选
        document.getElementById('status-filter').addEventListener('change', (e) => {
            this.filters.status = e.target.value;
            this.loadTasks();
        });
        
        // 工作流筛选
        document.getElementById('workflow-filter').addEventListener('change', (e) => {
            this.filters.workflow = e.target.value;
            this.loadTasks();
        });
        
        // 时间范围筛选
        document.getElementById('time-filter').addEventListener('change', (e) => {
            this.filters.timeRange = e.target.value;
            this.toggleCustomDateRange(e.target.value === 'custom');
            this.handleTimeRangeFilter();
        });
        
        // 排序
        document.getElementById('sort-filter').addEventListener('change', (e) => {
            this.filters.sort = e.target.value;
            this.loadTasks();
        });
        
        // 搜索
        let searchTimeout;
        document.getElementById('search-input').addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                this.filters.search = e.target.value.trim();
                this.loadTasks();
            }, 300);
        });
        
        // 自定义时间范围
        document.getElementById('start-date').addEventListener('change', (e) => {
            this.filters.startDate = e.target.value;
            if (this.filters.timeRange === 'custom') {
                this.loadTasks();
            }
        });
        
        document.getElementById('end-date').addEventListener('change', (e) => {
            this.filters.endDate = e.target.value;
            if (this.filters.timeRange === 'custom') {
                this.loadTasks();
            }
        });
        
        // 重置筛选
        document.getElementById('reset-filters').addEventListener('click', () => {
            this.resetFilters();
        });
    }
    
    async loadTasks() {
        this.showLoading(true);
        
        try {
            // 构建查询参数
            const params = new URLSearchParams();
            
            if (this.filters.status) {
                params.append('status', this.filters.status);
            }
            if (this.filters.workflow) {
                params.append('workflow_id', this.filters.workflow);
            }
            if (this.filters.search) {
                params.append('search', this.filters.search);
            }
            if (this.filters.startDate) {
                params.append('start_date', this.filters.startDate);
            }
            if (this.filters.endDate) {
                params.append('end_date', this.filters.endDate);
            }
            
            // 处理排序参数
            const [sortBy, sortOrder] = this.filters.sort.split('_');
            params.append('sort_by', sortBy);
            params.append('sort_order', sortOrder);
            
            const url = `/api/tasks${params.toString() ? '?' + params.toString() : ''}`;
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            this.tasks = await response.json();
            this.filteredTasks = this.tasks; // 直接使用后端筛选的结果
            await this.loadWorkflows();
            this.renderTasks();
            
        } catch (error) {
            console.error('加载任务失败:', error);
            this.showError('加载任务失败: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }
    
    async loadWorkflows() {
        try {
            const response = await fetch('/api/workflows');
            if (response.ok) {
                this.workflows = await response.json();
                this.populateWorkflowFilter();
            }
        } catch (error) {
            console.error('加载工作流失败:', error);
        }
    }
    
    populateWorkflowFilter() {
        const workflowSelect = document.getElementById('workflow-filter');
        // 保存当前选中的值
        const currentValue = workflowSelect.value;
        
        // 清除现有选项（保留第一个"全部工作流"选项）
        while (workflowSelect.children.length > 1) {
            workflowSelect.removeChild(workflowSelect.lastChild);
        }
        
        // 添加工作流选项
        this.workflows.forEach(workflow => {
            const option = document.createElement('option');
            option.value = workflow.id;
            option.textContent = workflow.name || `工作流 ${workflow.id}`;
            workflowSelect.appendChild(option);
        });
        
        // 恢复之前选中的值
        if (currentValue && this.workflows.some(w => w.id == currentValue)) {
            workflowSelect.value = currentValue;
        }
    }
    
    applyFilters() {
        let filtered = [...this.tasks];
        
        // 状态筛选
        if (this.filters.status) {
            filtered = filtered.filter(task => task.status.toLowerCase() === this.filters.status);
        }
        
        // 工作流筛选
        if (this.filters.workflow) {
            filtered = filtered.filter(task => task.workflow_id == this.filters.workflow);
        }
        
        // 搜索筛选
        if (this.filters.search) {
            const searchLower = this.filters.search.toLowerCase();
            filtered = filtered.filter(task => 
                (task.description && task.description.toLowerCase().includes(searchLower)) ||
                (task.local_task_id && task.local_task_id.toString().includes(searchLower))
            );
        }
        
        // 时间范围筛选
        filtered = this.applyTimeFilter(filtered);
        
        // 排序
        filtered = this.applySorting(filtered);
        
        this.filteredTasks = filtered;
        this.currentPage = 1; // 重置到第一页
        this.renderTasks();
    }
    
    applyTimeFilter(tasks) {
        if (!this.filters.timeRange) return tasks;
        
        const now = new Date();
        let startDate, endDate;
        
        switch (this.filters.timeRange) {
            case 'today':
                startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
                endDate = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
                break;
            case 'week':
                const weekStart = new Date(now);
                weekStart.setDate(now.getDate() - now.getDay());
                weekStart.setHours(0, 0, 0, 0);
                startDate = weekStart;
                endDate = new Date(weekStart);
                endDate.setDate(weekStart.getDate() + 7);
                break;
            case 'month':
                startDate = new Date(now.getFullYear(), now.getMonth(), 1);
                endDate = new Date(now.getFullYear(), now.getMonth() + 1, 1);
                break;
            case 'custom':
                if (this.filters.startDate) {
                    startDate = new Date(this.filters.startDate);
                }
                if (this.filters.endDate) {
                    endDate = new Date(this.filters.endDate);
                }
                break;
            default:
                return tasks;
        }
        
        return tasks.filter(task => {
            const taskDate = new Date(task.created_at);
            const afterStart = !startDate || taskDate >= startDate;
            const beforeEnd = !endDate || taskDate < endDate;
            return afterStart && beforeEnd;
        });
    }
    
    applySorting(tasks) {
        const [field, direction] = this.filters.sort.split('_');
        const isDesc = direction === 'desc';
        
        return tasks.sort((a, b) => {
            let aValue, bValue;
            
            switch (field) {
                case 'created':
                    aValue = new Date(a.created_at);
                    bValue = new Date(b.created_at);
                    break;
                case 'updated':
                    aValue = new Date(a.updated_at || a.created_at);
                    bValue = new Date(b.updated_at || b.created_at);
                    break;
                case 'status':
                    aValue = a.status;
                    bValue = b.status;
                    break;
                default:
                    return 0;
            }
            
            if (aValue < bValue) return isDesc ? 1 : -1;
            if (aValue > bValue) return isDesc ? -1 : 1;
            return 0;
        });
    }
    
    toggleCustomDateRange(show) {
        const customDateRange = document.getElementById('custom-date-range');
        if (show) {
            customDateRange.classList.remove('hidden');
        } else {
            customDateRange.classList.add('hidden');
        }
    }
    
    handleTimeRangeFilter() {
        const timeRange = this.filters.timeRange;
        const now = new Date();
        
        switch (timeRange) {
            case 'today':
                this.filters.startDate = now.toISOString().split('T')[0];
                this.filters.endDate = now.toISOString().split('T')[0];
                break;
            case 'week':
                const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                this.filters.startDate = weekAgo.toISOString().split('T')[0];
                this.filters.endDate = now.toISOString().split('T')[0];
                break;
            case 'month':
                const monthAgo = new Date(now.getFullYear(), now.getMonth() - 1, now.getDate());
                this.filters.startDate = monthAgo.toISOString().split('T')[0];
                this.filters.endDate = now.toISOString().split('T')[0];
                break;
            case 'custom':
                // 自定义时间范围，不自动设置日期
                return;
            default:
                this.filters.startDate = '';
                this.filters.endDate = '';
                break;
        }
        
        this.loadTasks();
    }
    
    resetFilters() {
        // 保存当前的工作流筛选状态
        const currentWorkflow = this.filters.workflow;
        
        // 重置筛选条件，但保持工作流筛选
        this.filters = {
            status: '',
            workflow: currentWorkflow, // 保持工作流筛选状态
            timeRange: '',
            search: '',
            sort: 'created_at_desc',
            startDate: '',
            endDate: ''
        };
        
        // 重置表单元素，但保持工作流筛选器的值
        document.getElementById('status-filter').value = '';
        // 不重置工作流筛选器的值
        // document.getElementById('workflow-filter').value = '';
        document.getElementById('time-filter').value = '';
        document.getElementById('search-input').value = '';
        document.getElementById('sort-filter').value = 'created_at_desc';
        document.getElementById('start-date').value = '';
        document.getElementById('end-date').value = '';
        
        // 隐藏自定义时间范围
        this.toggleCustomDateRange(false);
        
        // 重新加载任务
        this.loadTasks();
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
        const tbody = document.getElementById('taskTableBody');
        const emptyState = document.getElementById('empty-state');
        
        // 使用筛选后的任务数据
        const tasksToRender = this.filteredTasks || this.tasks || [];
        
        if (tasksToRender.length === 0) {
            tbody.innerHTML = '';
            emptyState.style.display = 'block';
            return;
        }
        
        emptyState.style.display = 'none';
        
        const startIndex = (this.currentPage - 1) * this.pageSize;
        const endIndex = startIndex + this.pageSize;
        const paginatedTasks = tasksToRender.slice(startIndex, endIndex);
        
        tbody.innerHTML = paginatedTasks.map(task => this.renderTaskRow(task)).join('');
        
        // 更新分页信息
        this.updatePagination();
        
        this.updateSelectionState();
    }
    
    renderTaskRow(task) {
        const statusClass = `status-${task.status.toLowerCase()}`;
        const statusText = this.getStatusText(task.status);
        const createdAt = new Date(task.created_at).toLocaleString();
        const canStart = ['READY', 'FAILED', 'STOPPED', 'CANCELLED'].includes(task.status);
        const canStop = ['PENDING', 'QUEUED', 'RUNNING'].includes(task.status);
        
        return `
            <tr data-task-id="${task.task_id}">
                <td>
                    <input type="checkbox" class="task-checkbox" value="${task.task_id}" 
                           onchange="taskManager.toggleTaskSelection('${task.task_id}')">
                </td>
                <td>
                    <code class="task-id" ondblclick="copyToClipboard('${task.task_id}')" title="双击复制完整ID">${task.task_id.substring(0, 8)}...</code>
                </td>
                <td class="task-description-cell">
                    <span class="task-description" title="${task.task_description || ''}">
                        ${task.task_description || '无描述'}
                    </span>
                </td>
                <td class="workflow-name-cell" title="${task.workflow_name || 'Unknown'}">
                    ${task.workflow_name || 'Unknown'}
                </td>
                <td>
                    <code class="task-id" ondblclick="copyToClipboard('${task.runninghub_task_id || ''}')" title="双击复制完整ID">${task.runninghub_task_id || '未分配'}</code>
                </td>
                <td style="padding: 0 8px;">
                    ${task.is_plus ? '<span class="plus-badge">PLUS</span>' : '否'}
                </td>
                <td>
                    <span class="datetime">${createdAt}</span>
                </td>
                <td>
                    <span class="duration">${this.calculateDuration(task)}</span>
                </td>
                <td>
                    <span class="status-badge ${statusClass}">${statusText}</span>
                </td>
                <td>
                    <div class=\"task-actions\">
                        ${canStart ? `<button class=\"btn btn-success\" onclick=\"taskManager.startTask('${task.task_id}')\">启动</button>` : ''}
                        ${canStop ? `<button class=\"btn btn-warning\" onclick=\"taskManager.stopTask('${task.task_id}')\">停止</button>` : ''}
                        <button class=\"btn btn-secondary\" onclick=\"taskManager.showTaskDetail('${task.task_id}')\">详情</button>
                        <a class=\"btn btn-secondary\" href=\"/tasks/create/${task.workflow_id}?copyFrom=${task.task_id}\">复制</a>
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

    calculateDuration(task) {
        if (!task.started_at) {
            return '-';
        }
        
        const startTime = new Date(task.started_at);
        const endTime = task.completed_at ? new Date(task.completed_at) : new Date();
        const duration = endTime - startTime;
        
        if (duration < 0) {
            return '-';
        }
        
        const totalSeconds = Math.floor(duration / 1000);
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;
        
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
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
    
    updatePagination() {
        const tasksToRender = this.filteredTasks || this.tasks || [];
        const totalTasks = tasksToRender.length;
        const totalPages = Math.ceil(totalTasks / this.pageSize);
        const startIndex = (this.currentPage - 1) * this.pageSize + 1;
        const endIndex = Math.min(this.currentPage * this.pageSize, totalTasks);
        
        document.getElementById('page-start').textContent = totalTasks > 0 ? startIndex : 0;
        document.getElementById('page-end').textContent = endIndex;
        document.getElementById('total-count').textContent = totalTasks;
        
        document.getElementById('prev-page').disabled = this.currentPage <= 1;
        document.getElementById('next-page').disabled = this.currentPage >= totalPages;
        
        this.renderPageNumbers(totalPages);
    }

    renderPageNumbers(totalPages) {
        const pageNumbers = document.getElementById('page-numbers');
        let html = '';
        
        for (let i = 1; i <= totalPages; i++) {
            if (i === this.currentPage) {
                html += `<button class="px-3 py-2 text-sm bg-primary text-white rounded-lg">${i}</button>`;
            } else {
                html += `<button onclick="taskManager.goToPage(${i})" class="px-3 py-2 text-sm bg-white border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors">${i}</button>`;
            }
        }
        
        pageNumbers.innerHTML = html;
    }

    previousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.renderTasks();
        }
    }

    nextPage() {
        const totalPages = Math.ceil(this.tasks.length / this.pageSize);
        if (this.currentPage < totalPages) {
            this.currentPage++;
            this.renderTasks();
        }
    }

    goToPage(page) {
        this.currentPage = page;
        this.renderTasks();
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
    
    async updateTaskStatus(taskId) {
        try {
            console.log('开始更新任务状态:', taskId);
            const task = this.tasks.find(t => t.task_id === taskId);
            if (!task || !task.runninghub_task_id) {
                this.showError('任务不存在或缺少远程任务ID');
                return;
            }
            
            console.log('发送更新请求，远程任务ID:', task.runninghub_task_id);
            const response = await fetch(`/api/tasks/${taskId}/update-status`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    remote_task_id: task.runninghub_task_id
                })
            });
            
            console.log('响应状态码:', response.status);
            const result = await response.json();
            console.log('响应结果:', result);
            
            if (response.ok) {
                if (result.success) {
                    this.showSuccess(`状态更新成功: ${result.old_status} → ${result.new_status}`);
                } else {
                    this.showSuccess(result.message || '状态更新完成');
                }
                this.loadTasks();
                this.loadQueueStatus();
            } else {
                this.showError(result.error || '更新失败');
            }
        } catch (error) {
            console.error('更新任务状态异常:', error);
            this.showError('更新任务状态失败: ' + error.message);
        }
    }
    
    async showTaskDetail(taskId) {
        // 跳转到独立的任务详情页面
        window.location.href = `/task_detail/${taskId}`;
    }
    
    // renderTaskDetail方法已移除，现在使用独立的任务详情页面
    
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
                        // 使用统一的时间字段名和格式化函数
                        const timestamp = this.formatTimestamp(log.timestamp || log.created_at);
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
                        <a href="${output.file_url || output.url}" download="${output.name || 'file'}" class="btn btn-download">
                            💾 下载
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
        const drawer = document.getElementById('taskDrawer');
        drawer.classList.add('hidden');
    }
    
    closeTaskDrawer() {
        this.closeTaskDetail();
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
    
    // 格式化时间戳
    formatTimestamp(timestamp) {
        if (!timestamp) {
            return '时间未知';
        }
        
        try {
            const date = new Date(timestamp);
            if (isNaN(date.getTime())) {
                return '时间格式错误';
            }
            return date.toLocaleTimeString('zh-CN', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        } catch (error) {
            console.warn('时间格式化失败:', error);
            return '时间解析失败';
        }
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

function closeTaskDrawer() {
    taskManager.closeTaskDrawer();
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        taskManager.showSuccess('ID已复制到剪贴板');
    }).catch(err => {
        console.error('复制失败:', err);
        taskManager.showError('复制失败');
    });
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