// 视频创意策划页面的Alpine.js应用
function videoStrategyApp() {
    return {
        // 状态管理（默认仅显示第二阶段）
        currentPhase: 'phase2',
        data: null,
        loading: false,
        message: '',
        messageType: 'info',
        
        // 搜索功能
        searchQuery: '',
        searchResults: [],
        
        // 统计数据
        stats: {
            totalSequences: 0,
            totalWords: 0,
            estimatedDuration: 0,
            sellingPoints: 0
        },

        // 初始化
        init() {
            this.loadData();
            this.setupEventListeners();
        },

        // 加载数据
        async loadData() {
            this.loading = true;
            try {
                // 首先尝试从URL参数获取数据ID
                const urlParams = new URLSearchParams(window.location.search);
                const dataId = urlParams.get('id');
                
                if (dataId) {
                    // 从数据库加载特定数据
                    const response = await fetch(`/api/auto-editor/video-strategy/${dataId}`);
                    if (response.ok) {
                        this.data = await response.json();
                        this.updateStats();
                    } else {
                        throw new Error('数据加载失败');
                    }
                } else {
                    // 尝试从localStorage获取最新数据
                    const savedData = localStorage.getItem('video_strategy_data');
                    if (savedData) {
                        this.data = JSON.parse(savedData);
                        this.updateStats();
                    }
                }
            } catch (error) {
                console.error('加载数据失败:', error);
                this.showMessage('数据加载失败', 'error');
            } finally {
                this.loading = false;
            }
        },

        // 更新统计数据
        updateStats() {
            if (!this.data || !this.data.phase2_creation_and_delivery) {
                return;
            }

            const phase2 = this.data.phase2_creation_and_delivery;
            let totalSequences = 0;
            let totalWords = 0;
            let estimatedDuration = 0;
            let sellingPoints = 0;

            // 计算视频制作蓝图统计
            if (phase2.videoProductionBlueprint && phase2.videoProductionBlueprint.sequences) {
                totalSequences = phase2.videoProductionBlueprint.sequences.length;
                
                phase2.videoProductionBlueprint.sequences.forEach(seq => {
                    if (seq.content) {
                        totalWords += seq.content.split(' ').length;
                    }
                    if (seq.duration) {
                        estimatedDuration += parseFloat(seq.duration) || 0;
                    }
                });
            }

            // 计算卖点数量
            if (this.data.phase1_analysis_and_strategy && 
                this.data.phase1_analysis_and_strategy.sellingPoints) {
                sellingPoints = this.data.phase1_analysis_and_strategy.sellingPoints.length;
            }

            this.stats = {
                totalSequences,
                totalWords,
                estimatedDuration: Math.round(estimatedDuration),
                sellingPoints
            };
        },

        // 保存数据到数据库
        async saveToDatabase() {
            if (!this.data) {
                this.showMessage('没有可保存的数据', 'error');
                return;
            }

            this.loading = true;
            try {
                const response = await fetch('/api/auto-editor/video-strategy', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        data: this.data,
                        timestamp: new Date().toISOString(),
                        title: this.generateTitle()
                    })
                });

                if (response.ok) {
                    const result = await response.json();
                    this.showMessage('数据保存成功', 'success');
                    
                    // 更新URL以包含数据ID
                    if (result.id) {
                        const newUrl = new URL(window.location);
                        newUrl.searchParams.set('id', result.id);
                        window.history.pushState({}, '', newUrl);
                    }
                } else {
                    throw new Error('保存失败');
                }
            } catch (error) {
                console.error('保存数据失败:', error);
                this.showMessage('数据保存失败', 'error');
            } finally {
                this.loading = false;
            }
        },

        // 导出数据
        exportData() {
            if (!this.data) {
                this.showMessage('没有可导出的数据', 'error');
                return;
            }

            try {
                const dataStr = JSON.stringify(this.data, null, 2);
                const dataBlob = new Blob([dataStr], { type: 'application/json' });
                const url = URL.createObjectURL(dataBlob);
                
                const link = document.createElement('a');
                link.href = url;
                link.download = `video_strategy_${new Date().toISOString().slice(0, 10)}.json`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                URL.revokeObjectURL(url);
                this.showMessage('数据导出成功', 'success');
            } catch (error) {
                console.error('导出数据失败:', error);
                this.showMessage('数据导出失败', 'error');
            }
        },

        // 复制到剪贴板
        async copyToClipboard(text) {
            if (!text) {
                this.showMessage('没有可复制的内容', 'error');
                return;
            }

            try {
                await navigator.clipboard.writeText(text);
                this.showMessage('已复制到剪贴板', 'success');
            } catch (error) {
                console.error('复制失败:', error);
                // 降级方案
                const textArea = document.createElement('textarea');
                textArea.value = text;
                document.body.appendChild(textArea);
                textArea.select();
                try {
                    document.execCommand('copy');
                    this.showMessage('已复制到剪贴板', 'success');
                } catch (fallbackError) {
                    this.showMessage('复制失败', 'error');
                }
                document.body.removeChild(textArea);
            }
        },

        // 生成标题
        generateTitle() {
            if (!this.data) return '视频创意策划';
            
            const timestamp = new Date().toLocaleString('zh-CN');
            const keyPoints = this.data.phase1_analysis_and_strategy?.keySellingPoints;
            
            if (keyPoints && keyPoints.length > 0) {
                const firstPoint = keyPoints[0].substring(0, 20);
                return `${firstPoint}... - ${timestamp}`;
            }
            
            return `视频创意策划 - ${timestamp}`;
        },

        // 显示消息
        showMessage(text, type = 'info') {
            this.message = text;
            this.messageType = type;
            
            // 自动隐藏消息
            setTimeout(() => {
                this.message = '';
            }, type === 'error' ? 5000 : 3000);
        },

        // 设置事件监听器
        setupEventListeners() {
            // 监听来自AI剪辑师页面的数据
            window.addEventListener('message', (event) => {
                if (event.data && event.data.type === 'video_strategy_data') {
                    this.data = event.data.payload;
                    localStorage.setItem('video_strategy_data', JSON.stringify(this.data));
                    this.showMessage('数据已更新', 'success');
                }
            });

            // 监听键盘快捷键
            document.addEventListener('keydown', (event) => {
                if (event.ctrlKey || event.metaKey) {
                    switch (event.key) {
                        case 's':
                            event.preventDefault();
                            this.saveToDatabase();
                            break;
                        case 'e':
                            event.preventDefault();
                            this.exportData();
                            break;
                        case '1':
                            event.preventDefault();
                            this.activePhase = 'phase1';
                            break;
                        case '2':
                            event.preventDefault();
                            this.activePhase = 'phase2';
                            break;
                    }
                }
            });
        },

        // 格式化时间戳
        formatTimestamp(timestamp) {
            if (!timestamp) return '';
            return new Date(timestamp).toLocaleString('zh-CN');
        },

        // 计算词数
        countWords(text) {
            if (!text) return 0;
            return text.trim().split(/\s+/).length;
        },

        // 计算预计时长（基于182 WPM）
        calculateDuration(text) {
            if (!text) return 0;
            const wordCount = this.countWords(text);
            return Math.round((wordCount / 182) * 60);
        },

        // 获取素材类型标签样式
        getClipTypeClass(isLongClip) {
            return isLongClip 
                ? 'bg-orange-100 text-orange-800 border-orange-200' 
                : 'bg-green-100 text-green-800 border-green-200';
        },

        // 获取场景序号样式
        getSequenceClass(sequence) {
            const colors = [
                'bg-blue-600',
                'bg-green-600', 
                'bg-purple-600',
                'bg-red-600',
                'bg-yellow-600',
                'bg-indigo-600',
                'bg-pink-600',
                'bg-gray-600'
            ];
            return colors[(sequence - 1) % colors.length];
        },

        // 验证数据完整性
        validateData() {
            if (!this.data) return false;
            
            const phase1 = this.data.phase1_analysis_and_strategy;
            const phase2 = this.data.phase2_creation_and_delivery;
            
            return !!(
                phase1 && 
                phase1.keySellingPoints && 
                phase1.clipAnalysis &&
                phase2 && 
                phase2.videoProductionBlueprint &&
                phase2.cleanEnglishVoiceoverScript
            );
        },

        // 获取数据统计信息
        getDataStats() {
            if (!this.validateData()) return null;
            
            const phase1 = this.data.phase1_analysis_and_strategy;
            const phase2 = this.data.phase2_creation_and_delivery;
            
            return {
                keyPointsCount: phase1.keySellingPoints?.length || 0,
                clipsCount: phase1.clipAnalysis?.length || 0,
                scenesCount: phase2.videoProductionBlueprint?.length || 0,
                totalWords: this.countWords(phase2.cleanEnglishVoiceoverScript),
                estimatedDuration: this.calculateDuration(phase2.cleanEnglishVoiceoverScript)
            };
        },

        // 搜索功能
        searchInData(query) {
            if (!query || !this.data) return [];
            
            const results = [];
            const searchText = query.toLowerCase();
            
            // 搜索卖点
            this.data.phase1_analysis_and_strategy?.keySellingPoints?.forEach((point, index) => {
                if (point.toLowerCase().includes(searchText)) {
                    results.push({
                        type: 'keyPoint',
                        index,
                        content: point,
                        phase: 'phase1'
                    });
                }
            });
            
            // 搜索场景
            this.data.phase2_creation_and_delivery?.videoProductionBlueprint?.forEach((scene, index) => {
                if (scene.englishVoiceoverScript?.toLowerCase().includes(searchText) ||
                    scene.clipDescription?.toLowerCase().includes(searchText)) {
                    results.push({
                        type: 'scene',
                        index,
                        content: scene,
                        phase: 'phase2'
                    });
                }
            });
            
            return results;
        }
    };
}

// 全局工具函数
window.VideoStrategyUtils = {
    // 从AI剪辑师页面接收数据
    receiveDataFromEditor(data) {
        // 发送消息给视频策划页面
        window.postMessage({
            type: 'video_strategy_data',
            payload: data
        }, '*');
    },

    // 打开视频策划页面
    openStrategyPage(data = null) {
        const url = data 
            ? `/video-strategy?data=${encodeURIComponent(JSON.stringify(data))}`
            : '/video-strategy';
        window.open(url, '_blank');
    }
};