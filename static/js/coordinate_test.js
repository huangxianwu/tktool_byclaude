// 坐标测试用例
class CoordinateTest {
    constructor() {
        this.testResults = [];
    }

    // 测试ComfyUI坐标格式的导入
    testComfyUIImport(editor) {
        console.log('开始测试ComfyUI坐标导入...');
        
        // 模拟ComfyUI的坐标数据（基于你提供的图片分析）
        const comfyUIData = {
            positive: [
                { x: 512, y: 384 },  // 图片中心附近的点
                { x: 256, y: 192 },  // 左上区域的点
                { x: 768, y: 576 }   // 右下区域的点
            ],
            negative: [
                { x: 128, y: 128 },  // 左上角附近
                { x: 896, y: 640 }   // 右下角附近
            ]
        };

        // 假设图片尺寸为1024x768（常见尺寸）
        const testImageWidth = 1024;
        const testImageHeight = 768;

        console.log('测试数据:', comfyUIData);
        console.log('假设图片尺寸:', testImageWidth, 'x', testImageHeight);

        // 测试不同的导入方式
        this.testImportMethod(editor, comfyUIData, false, '像素坐标导入');
        this.testImportMethod(editor, comfyUIData, true, '归一化坐标导入');

        // 测试坐标转换的一致性
        this.testCoordinateConsistency(editor, comfyUIData, testImageWidth, testImageHeight);
    }

    testImportMethod(editor, data, normalized, methodName) {
        console.log(`\n=== ${methodName} ===`);
        
        try {
            // 清空现有数据
            editor.clearDataOnly();
            
            // 导入数据
            editor.fromJSON(data, { normalized });
            
            // 获取导入后的数据
            const exportedData = editor.toJSON({ normalized: false });
            
            console.log('导入后的数据:', exportedData);
            
            // 验证数据完整性
            const posCount = exportedData.positive ? exportedData.positive.length : 0;
            const negCount = exportedData.negative ? exportedData.negative.length : 0;
            const originalPosCount = data.positive ? data.positive.length : 0;
            const originalNegCount = data.negative ? data.negative.length : 0;
            
            const success = posCount === originalPosCount && negCount === originalNegCount;
            
            this.testResults.push({
                method: methodName,
                success,
                originalData: data,
                importedData: exportedData,
                posCount,
                negCount
            });
            
            console.log(`结果: ${success ? '✅ 成功' : '❌ 失败'}`);
            console.log(`正向点: ${originalPosCount} -> ${posCount}`);
            console.log(`负向点: ${originalNegCount} -> ${negCount}`);
            
        } catch (error) {
            console.error(`${methodName} 失败:`, error);
            this.testResults.push({
                method: methodName,
                success: false,
                error: error.message
            });
        }
    }

    testCoordinateConsistency(editor, originalData, imageWidth, imageHeight) {
        console.log('\n=== 坐标一致性测试 ===');
        
        // 设置编辑器的图片尺寸（模拟）
        editor.imageWidth = imageWidth;
        editor.imageHeight = imageHeight;
        
        // 测试像素坐标 -> 归一化 -> 像素坐标的往返转换
        originalData.positive.forEach((point, index) => {
            console.log(`\n测试正向点 ${index + 1}:`);
            this.testRoundTripConversion(point, imageWidth, imageHeight);
        });
        
        if (originalData.negative) {
            originalData.negative.forEach((point, index) => {
                console.log(`\n测试负向点 ${index + 1}:`);
                this.testRoundTripConversion(point, imageWidth, imageHeight);
            });
        }
    }

    testRoundTripConversion(point, imageWidth, imageHeight) {
        console.log(`原始坐标: (${point.x}, ${point.y})`);
        
        // 转换为归一化坐标
        const normalizedX = point.x / imageWidth;
        const normalizedY = point.y / imageHeight;
        console.log(`归一化: (${normalizedX.toFixed(6)}, ${normalizedY.toFixed(6)})`);
        
        // 转换回像素坐标
        const backToPixelX = normalizedX * imageWidth;
        const backToPixelY = normalizedY * imageHeight;
        console.log(`回转像素: (${backToPixelX.toFixed(6)}, ${backToPixelY.toFixed(6)})`);
        
        // 计算误差
        const errorX = Math.abs(point.x - backToPixelX);
        const errorY = Math.abs(point.y - backToPixelY);
        console.log(`误差: (${errorX.toFixed(6)}, ${errorY.toFixed(6)})`);
        
        // 检查精度
        const precisionOK = errorX < 0.001 && errorY < 0.001;
        console.log(`精度检查: ${precisionOK ? '✅ 通过' : '❌ 失败'}`);
        
        return precisionOK;
    }

    // 生成测试报告
    generateReport() {
        console.log('\n=== 测试报告 ===');
        
        const successCount = this.testResults.filter(r => r.success).length;
        const totalCount = this.testResults.length;
        
        console.log(`总测试数: ${totalCount}`);
        console.log(`成功数: ${successCount}`);
        console.log(`失败数: ${totalCount - successCount}`);
        console.log(`成功率: ${((successCount / totalCount) * 100).toFixed(1)}%`);
        
        this.testResults.forEach((result, index) => {
            console.log(`\n测试 ${index + 1}: ${result.method}`);
            console.log(`状态: ${result.success ? '✅ 成功' : '❌ 失败'}`);
            if (result.error) {
                console.log(`错误: ${result.error}`);
            }
        });
        
        return this.testResults;
    }

    // 比较两个坐标系统的差异
    compareCoordinateSystems(comfyUICoords, currentProjectCoords, imageWidth, imageHeight) {
        console.log('\n=== 坐标系统对比分析 ===');
        
        const differences = [];
        
        // 比较正向点
        if (comfyUICoords.positive && currentProjectCoords.positive) {
            comfyUICoords.positive.forEach((comfyPoint, index) => {
                const currentPoint = currentProjectCoords.positive[index];
                if (currentPoint) {
                    const diff = this.calculateCoordinateDifference(
                        comfyPoint, currentPoint, imageWidth, imageHeight
                    );
                    differences.push({
                        type: 'positive',
                        index,
                        ...diff
                    });
                }
            });
        }
        
        // 比较负向点
        if (comfyUICoords.negative && currentProjectCoords.negative) {
            comfyUICoords.negative.forEach((comfyPoint, index) => {
                const currentPoint = currentProjectCoords.negative[index];
                if (currentPoint) {
                    const diff = this.calculateCoordinateDifference(
                        comfyPoint, currentPoint, imageWidth, imageHeight
                    );
                    differences.push({
                        type: 'negative',
                        index,
                        ...diff
                    });
                }
            });
        }
        
        // 分析差异模式
        this.analyzeDifferencePatterns(differences);
        
        return differences;
    }

    calculateCoordinateDifference(point1, point2, imageWidth, imageHeight) {
        // 绝对差异
        const absoluteDiffX = Math.abs(point1.x - point2.x);
        const absoluteDiffY = Math.abs(point1.y - point2.y);
        
        // 相对差异（基于图片尺寸）
        const relativeDiffX = absoluteDiffX / imageWidth;
        const relativeDiffY = absoluteDiffY / imageHeight;
        
        // 归一化坐标差异
        const norm1X = point1.x / imageWidth;
        const norm1Y = point1.y / imageHeight;
        const norm2X = point2.x / imageWidth;
        const norm2Y = point2.y / imageHeight;
        
        const normalizedDiffX = Math.abs(norm1X - norm2X);
        const normalizedDiffY = Math.abs(norm1Y - norm2Y);
        
        return {
            point1,
            point2,
            absoluteDiff: { x: absoluteDiffX, y: absoluteDiffY },
            relativeDiff: { x: relativeDiffX, y: relativeDiffY },
            normalizedDiff: { x: normalizedDiffX, y: normalizedDiffY },
            distance: Math.sqrt(absoluteDiffX * absoluteDiffX + absoluteDiffY * absoluteDiffY)
        };
    }

    analyzeDifferencePatterns(differences) {
        console.log('\n=== 差异模式分析 ===');
        
        if (differences.length === 0) {
            console.log('没有发现坐标差异');
            return;
        }
        
        // 计算平均差异
        const avgAbsoluteDiffX = differences.reduce((sum, d) => sum + d.absoluteDiff.x, 0) / differences.length;
        const avgAbsoluteDiffY = differences.reduce((sum, d) => sum + d.absoluteDiff.y, 0) / differences.length;
        
        const avgRelativeDiffX = differences.reduce((sum, d) => sum + d.relativeDiff.x, 0) / differences.length;
        const avgRelativeDiffY = differences.reduce((sum, d) => sum + d.relativeDiff.y, 0) / differences.length;
        
        console.log(`平均绝对差异: (${avgAbsoluteDiffX.toFixed(2)}, ${avgAbsoluteDiffY.toFixed(2)}) 像素`);
        console.log(`平均相对差异: (${(avgRelativeDiffX * 100).toFixed(2)}%, ${(avgRelativeDiffY * 100).toFixed(2)}%)`);
        
        // 检查是否存在系统性偏移
        const allDiffX = differences.map(d => d.point1.x - d.point2.x);
        const allDiffY = differences.map(d => d.point1.y - d.point2.y);
        
        const avgOffsetX = allDiffX.reduce((sum, diff) => sum + diff, 0) / allDiffX.length;
        const avgOffsetY = allDiffY.reduce((sum, diff) => sum + diff, 0) / allDiffY.length;
        
        console.log(`系统性偏移: (${avgOffsetX.toFixed(2)}, ${avgOffsetY.toFixed(2)}) 像素`);
        
        // 检查是否存在缩放差异
        const distances1 = [];
        const distances2 = [];
        
        for (let i = 0; i < differences.length - 1; i++) {
            for (let j = i + 1; j < differences.length; j++) {
                const diff1 = differences[i];
                const diff2 = differences[j];
                
                const dist1 = Math.sqrt(
                    Math.pow(diff1.point1.x - diff2.point1.x, 2) + 
                    Math.pow(diff1.point1.y - diff2.point1.y, 2)
                );
                const dist2 = Math.sqrt(
                    Math.pow(diff1.point2.x - diff2.point2.x, 2) + 
                    Math.pow(diff1.point2.y - diff2.point2.y, 2)
                );
                
                distances1.push(dist1);
                distances2.push(dist2);
            }
        }
        
        if (distances1.length > 0) {
            const avgDist1 = distances1.reduce((sum, d) => sum + d, 0) / distances1.length;
            const avgDist2 = distances2.reduce((sum, d) => sum + d, 0) / distances2.length;
            const scaleRatio = avgDist2 / avgDist1;
            
            console.log(`平均距离比例: ${scaleRatio.toFixed(4)}`);
            
            if (Math.abs(scaleRatio - 1.0) > 0.01) {
                console.log('⚠️ 检测到可能的缩放差异');
            }
        }
        
        // 输出详细差异信息
        differences.forEach((diff, index) => {
            console.log(`\n${diff.type}点 ${diff.index + 1}:`);
            console.log(`  ComfyUI: (${diff.point1.x}, ${diff.point1.y})`);
            console.log(`  当前项目: (${diff.point2.x}, ${diff.point2.y})`);
            console.log(`  差异: (${diff.absoluteDiff.x.toFixed(2)}, ${diff.absoluteDiff.y.toFixed(2)}) 像素`);
            console.log(`  距离: ${diff.distance.toFixed(2)} 像素`);
        });
    }
}

// 全局测试实例
window.coordinateTest = new CoordinateTest();