// 测试JSON解析功能
const fs = require('fs');
const path = require('path');

// 从文本中提取有效的JSON对象
function extractValidJSON(text) {
    // 查找所有可能的JSON对象
    const jsonObjects = [];
    let braceCount = 0;
    let startIndex = -1;
    
    for (let i = 0; i < text.length; i++) {
        const char = text[i];
        
        if (char === '{') {
            if (braceCount === 0) {
                startIndex = i;
            }
            braceCount++;
        } else if (char === '}') {
            braceCount--;
            if (braceCount === 0 && startIndex !== -1) {
                // 找到一个完整的JSON对象
                const jsonStr = text.substring(startIndex, i + 1);
                try {
                    const parsed = JSON.parse(jsonStr);
                    jsonObjects.push(parsed);
                } catch (e) {
                    // 忽略无效的JSON
                }
                startIndex = -1;
            }
        }
    }
    
    // 检查JSON对象是否包含实际数据（而不是占位符）
    function hasRealData(obj) {
        const jsonStr = JSON.stringify(obj);
        // 如果包含太多"..."占位符，认为是模板
        const placeholderCount = (jsonStr.match(/\.\.\./g) || []).length;
        const totalLength = jsonStr.length;
        // 如果占位符比例过高，认为是模板
        return placeholderCount < 5 && totalLength > 1000;
    }
    
    console.log(`找到 ${jsonObjects.length} 个JSON对象`);
    jsonObjects.forEach((obj, index) => {
        const size = JSON.stringify(obj).length;
        const hasReal = hasRealData(obj);
        const hasPhase1 = obj.phase1_analysis_and_strategy || obj.phase1;
        const hasPhase2 = obj.phase2_creation_and_delivery || obj.phase2;
        console.log(`JSON对象 ${index + 1}: 大小=${size}, 有实际数据=${hasReal}, 有Phase1=${!!hasPhase1}, 有Phase2=${!!hasPhase2}`);
    });
    
    // 优先返回包含实际数据的两阶段JSON对象
    for (const obj of jsonObjects) {
        if ((obj.phase1_analysis_and_strategy && obj.phase2_creation_and_delivery) ||
            (obj.phase1 && obj.phase2)) {
            if (hasRealData(obj)) {
                return obj;
            }
        }
    }
    
    // 如果没有找到包含实际数据的两阶段对象，返回最大的包含实际数据的JSON对象
    const realDataObjects = jsonObjects.filter(hasRealData);
    if (realDataObjects.length > 0) {
        return realDataObjects.reduce((largest, current) => {
            const currentSize = JSON.stringify(current).length;
            const largestSize = JSON.stringify(largest).length;
            return currentSize > largestSize ? current : largest;
        });
    }
    
    // 如果没有找到包含实际数据的对象，返回最大的JSON对象
    if (jsonObjects.length > 0) {
        return jsonObjects.reduce((largest, current) => {
            const currentSize = JSON.stringify(current).length;
            const largestSize = JSON.stringify(largest).length;
            return currentSize > largestSize ? current : largest;
        });
    }
    
    throw new Error('未找到有效的JSON对象');
}

// 测试函数
function testJSONParsing() {
  try {
    // 读取AI回复记录文件
    const filePath = path.join(__dirname, 'docs', 'AI回复记录.txt');
    const fileContent = fs.readFileSync(filePath, 'utf8');
    
    console.log('文件内容长度:', fileContent.length);
    console.log('文件前100个字符:', fileContent.substring(0, 100));
    
    // 测试提取JSON
    const extractedJSON = extractValidJSON(fileContent);
    
    console.log('\n=== 提取的JSON结构 ===');
    console.log('包含 phase1_analysis_and_strategy:', !!extractedJSON.phase1_analysis_and_strategy);
    console.log('包含 phase2_creation_and_delivery:', !!extractedJSON.phase2_creation_and_delivery);
    
    if (extractedJSON.phase1_analysis_and_strategy) {
      console.log('Phase1 keySellingPoints 数量:', extractedJSON.phase1_analysis_and_strategy.keySellingPoints?.length || 0);
      console.log('Phase1 clipAnalysis 数量:', extractedJSON.phase1_analysis_and_strategy.clipAnalysis?.length || 0);
    }
    
    if (extractedJSON.phase2_creation_and_delivery) {
      console.log('Phase2 videoProductionBlueprint 数量:', extractedJSON.phase2_creation_and_delivery.videoProductionBlueprint?.length || 0);
    }
    
    console.log('\n=== 测试成功 ===');
    console.log('JSON数据大小:', JSON.stringify(extractedJSON).length, '字符');
    
    // 输出提取的JSON内容（前500字符）
    const jsonStr = JSON.stringify(extractedJSON, null, 2);
    console.log('\n=== 提取的JSON内容（前500字符）===');
    console.log(jsonStr.substring(0, 500));
    
    return extractedJSON;
    
  } catch (error) {
    console.error('测试失败:', error.message);
    return null;
  }
}

// 运行测试
testJSONParsing();