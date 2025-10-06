// 坐标修复和增强转换系统
class CoordinateFix {
    constructor() {
        this.debugMode = true;
        this.coordinateHistory = [];
    }

    // 增强的坐标检测和转换
    enhancedCoordinateDetection(data, imageWidth, imageHeight) {
        const allPoints = [...(data.positive || []), ...(data.negative || [])];
        
        if (allPoints.length === 0) {
            return { type: 'pixel', confidence: 0 };
        }

        // 多种检测策略
        const detectionResults = {
            normalized: this.checkNormalizedCoordinates(allPoints),
            pixel: this.checkPixelCoordinates(allPoints, imageWidth, imageHeight),
            scaled: this.checkScaledCoordinates(allPoints, imageWidth, imageHeight)
        };

        // 选择最可能的类型
        const bestMatch = Object.entries(detectionResults)
            .sort((a, b) => b[1].confidence - a[1].confidence)[0];

        this.log(`坐标检测结果:`, detectionResults);
        this.log(`最佳匹配: ${bestMatch[0]} (置信度: ${bestMatch[1].confidence.toFixed(2)})`);

        return {
            type: bestMatch[0],
            confidence: bestMatch[1].confidence,
            allResults: detectionResults
        };
    }

    checkNormalizedCoordinates(points) {
        const inRange = points.filter(p => p.x >= 0 && p.x <= 1 && p.y >= 0 && p.y <= 1);
        const confidence = inRange.length / points.length;
        
        return {
            confidence,
            inRange: inRange.length,
            total: points.length,
            description: '归一化坐标 (0-1范围)'
        };
    }

    checkPixelCoordinates(points, imageWidth, imageHeight) {
        if (!imageWidth || !imageHeight) {
            return { confidence: 0.5, description: '无法验证像素坐标（缺少图片尺寸）' };
        }

        const inRange = points.filter(p => 
            p.x >= 0 && p.x <= imageWidth && 
            p.y >= 0 && p.y <= imageHeight
        );
        
        const nearRange = points.filter(p => 
            p.x >= -imageWidth * 0.1 && p.x <= imageWidth * 1.1 && 
            p.y >= -imageHeight * 0.1 && p.y <= imageHeight * 1.1
        );

        const confidence = (inRange.length * 1.0 + nearRange.length * 0.5) / points.length;
        
        return {
            confidence: Math.min(confidence, 1.0),
            inRange: inRange.length,
            nearRange: nearRange.length,
            total: points.length,
            description: `像素坐标 (${imageWidth}x${imageHeight})`
        };
    }

    checkScaledCoordinates(points, imageWidth, imageHeight) {
        if (!imageWidth || !imageHeight) {
            return { confidence: 0, description: '无法检测缩放坐标（缺少图片尺寸）' };
        }

        // 检查常见的缩放比例
        const scaleFactors = [0.5, 2.0, 0.25, 4.0, 0.75, 1.5];
        let bestScale = 1.0;
        let bestConfidence = 0;

        scaleFactors.forEach(scale => {
            const scaledWidth = imageWidth * scale;
            const scaledHeight = imageHeight * scale;
            
            const inRange = points.filter(p => 
                p.x >= 0 && p.x <= scaledWidth && 
                p.y >= 0 && p.y <= scaledHeight
            );
            
            const confidence = inRange.length / points.length;
            if (confidence > bestConfidence) {
                bestConfidence = confidence;
                bestScale = scale;
            }
        });

        return {
            confidence: bestConfidence,
            scale: bestScale,
            description: `缩放坐标 (比例: ${bestScale})`
        };
    }

    // 智能坐标转换
    smartCoordinateConversion(data, targetType, imageWidth, imageHeight, sourceType = null) {
        if (!sourceType) {
            const detection = this.enhancedCoordinateDetection(data, imageWidth, imageHeight);
            sourceType = detection.type;
        }

        this.log(`坐标转换: ${sourceType} -> ${targetType}`);

        const convertedData = {
            positive: data.positive ? this.convertPointArray(data.positive, sourceType, targetType, imageWidth, imageHeight) : [],
            negative: data.negative ? this.convertPointArray(data.negative, sourceType, targetType, imageWidth, imageHeight) : []
        };

        // 记录转换历史
        this.coordinateHistory.push({
            timestamp: Date.now(),
            sourceType,
            targetType,
            imageSize: { width: imageWidth, height: imageHeight },
            originalData: JSON.parse(JSON.stringify(data)),
            convertedData: JSON.parse(JSON.stringify(convertedData))
        });

        return convertedData;
    }

    convertPointArray(points, sourceType, targetType, imageWidth, imageHeight) {
        return points.map(point => this.convertPoint(point, sourceType, targetType, imageWidth, imageHeight));
    }

    convertPoint(point, sourceType, targetType, imageWidth, imageHeight) {
        let x = point.x;
        let y = point.y;

        // 首先转换为标准像素坐标
        switch (sourceType) {
            case 'normalized':
                x = x * imageWidth;
                y = y * imageHeight;
                break;
            case 'scaled':
                // 这里需要根据检测到的缩放比例进行转换
                const detection = this.checkScaledCoordinates([point], imageWidth, imageHeight);
                if (detection.scale && detection.scale !== 1.0) {
                    x = x / detection.scale;
                    y = y / detection.scale;
                }
                break;
            case 'pixel':
            default:
                // 已经是像素坐标，无需转换
                break;
        }

        // 然后转换为目标类型
        switch (targetType) {
            case 'normalized':
                return {
                    x: x / imageWidth,
                    y: y / imageHeight
                };
            case 'pixel':
            default:
                return { x, y };
        }
    }

    // ComfyUI兼容性修复
    fixComfyUICoordinates(data, imageWidth, imageHeight) {
        this.log('开始ComfyUI坐标兼容性修复...');
        
        // 检测坐标类型
        const detection = this.enhancedCoordinateDetection(data, imageWidth, imageHeight);
        
        // 如果检测为像素坐标但置信度不高，尝试其他可能性
        if (detection.type === 'pixel' && detection.confidence < 0.8) {
            this.log('像素坐标置信度较低，尝试其他转换方式...');
            
            // 尝试不同的图片尺寸基准
            const alternativeSizes = this.generateAlternativeImageSizes(imageWidth, imageHeight);
            
            for (const altSize of alternativeSizes) {
                const altDetection = this.enhancedCoordinateDetection(data, altSize.width, altSize.height);
                this.log(`尝试尺寸 ${altSize.width}x${altSize.height}: ${altDetection.type} (置信度: ${altDetection.confidence.toFixed(2)})`);
                
                if (altDetection.confidence > detection.confidence) {
                    this.log(`找到更好的匹配: ${altSize.description}`);
                    return this.smartCoordinateConversion(data, 'pixel', altSize.width, altSize.height, altDetection.type);
                }
            }
        }

        // 使用检测到的类型进行转换
        return this.smartCoordinateConversion(data, 'pixel', imageWidth, imageHeight, detection.type);
    }

    generateAlternativeImageSizes(baseWidth, baseHeight) {
        const alternatives = [];
        
        // 常见的显示尺寸比例
        const ratios = [
            { scale: 0.5, desc: '50%显示尺寸' },
            { scale: 0.75, desc: '75%显示尺寸' },
            { scale: 1.25, desc: '125%显示尺寸' },
            { scale: 1.5, desc: '150%显示尺寸' },
            { scale: 2.0, desc: '200%显示尺寸' }
        ];

        ratios.forEach(ratio => {
            alternatives.push({
                width: Math.round(baseWidth * ratio.scale),
                height: Math.round(baseHeight * ratio.scale),
                description: ratio.desc
            });
        });

        // 常见的标准尺寸
        const standardSizes = [
            { width: 512, height: 512, description: '标准512x512' },
            { width: 1024, height: 1024, description: '标准1024x1024' },
            { width: 768, height: 768, description: '标准768x768' },
            { width: 512, height: 768, description: '标准512x768' },
            { width: 768, height: 512, description: '标准768x512' }
        ];

        alternatives.push(...standardSizes);

        return alternatives;
    }

    // 验证坐标转换的准确性
    validateConversion(originalData, convertedData, imageWidth, imageHeight) {
        this.log('验证坐标转换准确性...');
        
        const results = {
            positive: this.validatePointArray(originalData.positive, convertedData.positive, imageWidth, imageHeight),
            negative: this.validatePointArray(originalData.negative, convertedData.negative, imageWidth, imageHeight)
        };

        const overallAccuracy = (
            (results.positive.accuracy * results.positive.count + 
             results.negative.accuracy * results.negative.count) /
            (results.positive.count + results.negative.count)
        ) || 0;

        this.log(`转换验证结果: 总体准确度 ${(overallAccuracy * 100).toFixed(1)}%`);
        
        return {
            overallAccuracy,
            details: results
        };
    }

    validatePointArray(original, converted, imageWidth, imageHeight) {
        if (!original || !converted || original.length !== converted.length) {
            return { accuracy: 0, count: 0, errors: ['数组长度不匹配'] };
        }

        let accurateCount = 0;
        const errors = [];

        original.forEach((origPoint, index) => {
            const convPoint = converted[index];
            
            // 检查坐标是否在合理范围内
            const inBounds = convPoint.x >= 0 && convPoint.x <= imageWidth && 
                           convPoint.y >= 0 && convPoint.y <= imageHeight;
            
            if (inBounds) {
                accurateCount++;
            } else {
                errors.push(`点${index + 1}: (${convPoint.x.toFixed(2)}, ${convPoint.y.toFixed(2)}) 超出边界`);
            }
        });

        return {
            accuracy: accurateCount / original.length,
            count: original.length,
            errors
        };
    }

    // 调试日志
    log(message, data = null) {
        if (this.debugMode) {
            console.log(`[CoordinateFix] ${message}`, data || '');
            
            // 同时输出到调试面板
            if (window.coordinateDebugger) {
                window.coordinateDebugger.log(`[修复] ${message}`);
                if (data) {
                    window.coordinateDebugger.log(`  数据: ${JSON.stringify(data)}`);
                }
            }
        }
    }

    // 获取转换历史
    getConversionHistory() {
        return this.coordinateHistory;
    }

    // 清除历史记录
    clearHistory() {
        this.coordinateHistory = [];
    }
}

// 全局坐标修复实例
window.coordinateFix = new CoordinateFix();

// 增强PointEditor的fromJSON方法
if (typeof PointEditor !== 'undefined') {
    const originalFromJSON = PointEditor.prototype.fromJSON;
    
    PointEditor.prototype.fromJSON = function(data, options = {}) {
        // 如果启用了坐标修复
        if (options.useCoordinateFix !== false) {
            console.log('使用增强坐标修复...');
            
            // 使用修复后的坐标数据
            const fixedData = window.coordinateFix.fixComfyUICoordinates(
                data, 
                this.imageWidth, 
                this.imageHeight
            );
            
            // 验证修复结果
            const validation = window.coordinateFix.validateConversion(
                data, 
                fixedData, 
                this.imageWidth, 
                this.imageHeight
            );
            
            console.log('坐标修复验证结果:', validation);
            
            // 如果修复效果好，使用修复后的数据
            if (validation.overallAccuracy > 0.8) {
                console.log('使用修复后的坐标数据');
                return originalFromJSON.call(this, fixedData, { ...options, normalized: false });
            } else {
                console.log('修复效果不佳，使用原始数据');
            }
        }
        
        // 使用原始方法
        return originalFromJSON.call(this, data, options);
    };
}