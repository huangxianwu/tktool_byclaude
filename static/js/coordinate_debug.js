// 坐标调试工具
class CoordinateDebugger {
    constructor() {
        this.debugPanel = null;
        this.createDebugPanel();
    }

    createDebugPanel() {
        // 创建调试面板
        this.debugPanel = document.createElement('div');
        this.debugPanel.id = 'coordinate-debug-panel';
        this.debugPanel.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            width: 300px;
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 12px;
            z-index: 10000;
            max-height: 400px;
            overflow-y: auto;
        `;
        document.body.appendChild(this.debugPanel);
    }

    log(message) {
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.innerHTML = `[${timestamp}] ${message}`;
        logEntry.style.marginBottom = '2px';
        this.debugPanel.appendChild(logEntry);
        
        // 保持最新的日志在顶部
        this.debugPanel.scrollTop = this.debugPanel.scrollHeight;
        
        // 限制日志条数
        const logs = this.debugPanel.children;
        if (logs.length > 50) {
            this.debugPanel.removeChild(logs[0]);
        }
    }

    clear() {
        this.debugPanel.innerHTML = '';
    }

    // 分析坐标转换
    analyzeCoordinateConversion(editor, originalCoords, convertedCoords) {
        this.log('=== 坐标转换分析 ===');
        this.log(`图片尺寸: ${editor.imageWidth} x ${editor.imageHeight}`);
        this.log(`画布尺寸: ${editor.canvas.width} x ${editor.canvas.height}`);
        this.log(`缩放比例: ${editor.scale.toFixed(4)}`);
        this.log(`偏移量: (${editor.offsetX.toFixed(2)}, ${editor.offsetY.toFixed(2)})`);
        
        if (originalCoords && convertedCoords) {
            this.log('--- 坐标对比 ---');
            originalCoords.forEach((coord, index) => {
                const converted = convertedCoords[index];
                if (converted) {
                    this.log(`原始: (${coord.x.toFixed(4)}, ${coord.y.toFixed(4)}) -> 转换: (${converted.x.toFixed(4)}, ${converted.y.toFixed(4)})`);
                }
            });
        }
    }

    // 测试坐标转换的准确性
    testCoordinateAccuracy(editor, testPoints) {
        this.log('=== 坐标精度测试 ===');
        
        testPoints.forEach((point, index) => {
            // 测试归一化坐标转换
            const normalizedX = point.x / editor.imageWidth;
            const normalizedY = point.y / editor.imageHeight;
            
            // 转换为屏幕坐标
            const screenCoord = editor.imageToScreen(point.x, point.y);
            
            // 再转换回图片坐标
            const backToImage = editor.screenToImage(screenCoord.x, screenCoord.y);
            
            // 计算误差
            const errorX = Math.abs(point.x - backToImage.x);
            const errorY = Math.abs(point.y - backToImage.y);
            
            this.log(`测试点${index + 1}:`);
            this.log(`  原始: (${point.x.toFixed(4)}, ${point.y.toFixed(4)})`);
            this.log(`  归一化: (${normalizedX.toFixed(6)}, ${normalizedY.toFixed(6)})`);
            this.log(`  屏幕: (${screenCoord.x.toFixed(2)}, ${screenCoord.y.toFixed(2)})`);
            this.log(`  回转: (${backToImage.x.toFixed(4)}, ${backToImage.y.toFixed(4)})`);
            this.log(`  误差: (${errorX.toFixed(6)}, ${errorY.toFixed(6)})`);
            
            if (errorX > 0.001 || errorY > 0.001) {
                this.log(`  ⚠️ 精度损失较大!`);
            }
        });
    }

    // 比较ComfyUI和当前项目的坐标系统
    compareCoordinateSystems(comfyUICoords, currentCoords, imageWidth, imageHeight) {
        this.log('=== ComfyUI vs 当前项目坐标对比 ===');
        this.log(`图片尺寸: ${imageWidth} x ${imageHeight}`);
        
        comfyUICoords.forEach((comfyCoord, index) => {
            const currentCoord = currentCoords[index];
            if (currentCoord) {
                // 计算相对位置差异
                const comfyRelativeX = comfyCoord.x / imageWidth;
                const comfyRelativeY = comfyCoord.y / imageHeight;
                const currentRelativeX = currentCoord.x / imageWidth;
                const currentRelativeY = currentCoord.y / imageHeight;
                
                const relativeDiffX = Math.abs(comfyRelativeX - currentRelativeX);
                const relativeDiffY = Math.abs(comfyRelativeY - currentRelativeY);
                
                this.log(`坐标${index + 1}:`);
                this.log(`  ComfyUI: (${comfyCoord.x}, ${comfyCoord.y}) 相对:(${comfyRelativeX.toFixed(4)}, ${comfyRelativeY.toFixed(4)})`);
                this.log(`  当前项目: (${currentCoord.x}, ${currentCoord.y}) 相对:(${currentRelativeX.toFixed(4)}, ${currentRelativeY.toFixed(4)})`);
                this.log(`  相对差异: (${relativeDiffX.toFixed(6)}, ${relativeDiffY.toFixed(6)})`);
                
                if (relativeDiffX > 0.01 || relativeDiffY > 0.01) {
                    this.log(`  ❌ 相对位置差异较大!`);
                } else {
                    this.log(`  ✅ 相对位置基本一致`);
                }
            }
        });
    }

    // 检查坐标系统的原点和方向
    checkCoordinateSystem(editor) {
        this.log('=== 坐标系统检查 ===');
        
        // 测试四个角点
        const corners = [
            { name: '左上角', x: 0, y: 0 },
            { name: '右上角', x: editor.imageWidth, y: 0 },
            { name: '左下角', x: 0, y: editor.imageHeight },
            { name: '右下角', x: editor.imageWidth, y: editor.imageHeight }
        ];
        
        corners.forEach(corner => {
            const screenCoord = editor.imageToScreen(corner.x, corner.y);
            const normalizedX = corner.x / editor.imageWidth;
            const normalizedY = corner.y / editor.imageHeight;
            
            this.log(`${corner.name}:`);
            this.log(`  图片坐标: (${corner.x}, ${corner.y})`);
            this.log(`  归一化: (${normalizedX.toFixed(2)}, ${normalizedY.toFixed(2)})`);
            this.log(`  屏幕坐标: (${screenCoord.x.toFixed(2)}, ${screenCoord.y.toFixed(2)})`);
        });
        
        // 检查坐标系方向
        const centerX = editor.imageWidth / 2;
        const centerY = editor.imageHeight / 2;
        const rightPoint = editor.imageToScreen(centerX + 100, centerY);
        const downPoint = editor.imageToScreen(centerX, centerY + 100);
        const centerScreen = editor.imageToScreen(centerX, centerY);
        
        this.log('坐标系方向检查:');
        this.log(`  X轴正方向: ${rightPoint.x > centerScreen.x ? '向右' : '向左'}`);
        this.log(`  Y轴正方向: ${downPoint.y > centerScreen.y ? '向下' : '向上'}`);
    }
}

// 全局调试器实例
window.coordinateDebugger = new CoordinateDebugger();

// 为点编辑器添加调试功能
if (typeof PointEditor !== 'undefined') {
    const originalFromJSON = PointEditor.prototype.fromJSON;
    PointEditor.prototype.fromJSON = function(data, options = {}) {
        // 记录导入前的状态
        window.coordinateDebugger.log('=== 开始导入坐标 ===');
        window.coordinateDebugger.log(`导入选项: normalized=${options.normalized}`);
        
        if (data.positive && data.positive.length > 0) {
            window.coordinateDebugger.log(`正向点数量: ${data.positive.length}`);
            data.positive.forEach((point, index) => {
                window.coordinateDebugger.log(`  正向点${index + 1}: (${point.x}, ${point.y})`);
            });
        }
        
        if (data.negative && data.negative.length > 0) {
            window.coordinateDebugger.log(`负向点数量: ${data.negative.length}`);
            data.negative.forEach((point, index) => {
                window.coordinateDebugger.log(`  负向点${index + 1}: (${point.x}, ${point.y})`);
            });
        }
        
        // 调用原始方法
        const result = originalFromJSON.call(this, data, options);
        
        // 记录导入后的状态
        window.coordinateDebugger.analyzeCoordinateConversion(this);
        window.coordinateDebugger.checkCoordinateSystem(this);
        
        return result;
    };
}