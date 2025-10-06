/**
 * 视频首帧坐标修正工具
 * 解决视频自动提取首帧与手动截取首帧的坐标偏移问题
 */

class VideoFrameFix {
  constructor() {
    this.videoMetadata = null;
    this.debugMode = false;
  }

  /**
   * 增强的视频首帧提取，保留原始视频尺寸信息
   * @param {File} file - 视频文件
   * @param {Object} targetResolution - 目标分辨率 {width: number, height: number}
   */
  async extractFirstFrameWithMetadata(file, targetResolution = null) {
    return new Promise((resolve, reject) => {
      const url = URL.createObjectURL(file);
      const video = document.createElement('video');
      let cleaned = false;
      
      const cleanup = () => {
        if (cleaned) return;
        cleaned = true;
        try { URL.revokeObjectURL(url); } catch {}
        video.src = '';
      };

      video.preload = 'auto';
      video.src = url;
      video.muted = true;
      video.playsInline = true;

      const onError = (e) => {
        cleanup();
        reject(e?.error || e || new Error('视频解码错误'));
      };

      const draw = () => {
        try {
          const vw = video.videoWidth;
          const vh = video.videoHeight;
          
          if (!vw || !vh) return false;

          // 保存原始视频元数据
          this.videoMetadata = {
            originalVideoWidth: vw,
            originalVideoHeight: vh,
            videoFile: file.name,
            extractTime: new Date().toISOString(),
            targetResolution: targetResolution
          };

          // 创建Canvas并绘制首帧
          const off = document.createElement('canvas');
          // 使用目标分辨率或原始尺寸
          const canvasWidth = targetResolution ? targetResolution.width : vw;
          const canvasHeight = targetResolution ? targetResolution.height : vh;
          off.width = canvasWidth;
          off.height = canvasHeight;
          const ctx = off.getContext('2d');
          ctx.drawImage(video, 0, 0, canvasWidth, canvasHeight);
          
          // 生成图片数据
          const dataUrl = off.toDataURL('image/png');
          
          if (this.debugMode) {
            console.log('视频首帧提取信息:', {
              videoWidth: vw,
              videoHeight: vh,
              canvasWidth: off.width,
              canvasHeight: off.height,
              fileName: file.name
            });
          }

          cleanup();
          resolve({
            dataUrl,
            metadata: this.videoMetadata
          });
          return true;
        } catch (err) {
          cleanup();
          reject(err);
          return false;
        }
      };

      video.addEventListener('error', onError, { once: true });
      video.addEventListener('loadedmetadata', () => {
        const attempt = () => {
          if (video.readyState >= 2) {
            if (!draw()) {
              setTimeout(attempt, 100);
            }
          } else {
            const onceDraw = () => { draw() || setTimeout(attempt, 100); };
            video.addEventListener('loadeddata', onceDraw, { once: true });
            video.addEventListener('canplay', onceDraw, { once: true });
          }
        };
        try { video.currentTime = 0; } catch {}
        attempt();
      }, { once: true });
    });
  }

  /**
   * 修正点编辑器的图片加载，保持视频原始尺寸
   * @param {Object} editor - 编辑器实例
   * @param {File} file - 视频文件
   * @param {Object} targetResolution - 目标分辨率 {width: number, height: number}
   */
  async loadVideoFrameWithCorrectDimensions(editor, file, targetResolution = null) {
    try {
      const result = await this.extractFirstFrameWithMetadata(file, targetResolution);
      
      // 先正常加载图片
      await editor.loadImage(result.dataUrl);
      
      // 然后修正尺寸信息
      if (this.videoMetadata) {
        const originalImageWidth = editor.imageWidth;
        const originalImageHeight = editor.imageHeight;
        
        // 使用目标分辨率或视频原始尺寸作为坐标基准
        if (targetResolution) {
          editor.imageWidth = targetResolution.width;
          editor.imageHeight = targetResolution.height;
        } else {
          editor.imageWidth = this.videoMetadata.originalVideoWidth;
          editor.imageHeight = this.videoMetadata.originalVideoHeight;
        }
        
        // 记录尺寸修正信息
        editor._videoFrameCorrection = {
          originalVideoWidth: this.videoMetadata.originalVideoWidth,
          originalVideoHeight: this.videoMetadata.originalVideoHeight,
          extractedImageWidth: originalImageWidth,
          extractedImageHeight: originalImageHeight,
          targetWidth: targetResolution ? targetResolution.width : this.videoMetadata.originalVideoWidth,
          targetHeight: targetResolution ? targetResolution.height : this.videoMetadata.originalVideoHeight,
          correctionApplied: true
        };

        if (this.debugMode) {
          console.log('视频首帧尺寸修正:', {
            '原始视频尺寸': `${this.videoMetadata.originalVideoWidth}x${this.videoMetadata.originalVideoHeight}`,
            '提取图片尺寸': `${originalImageWidth}x${originalImageHeight}`,
            '目标分辨率': targetResolution ? `${targetResolution.width}x${targetResolution.height}` : '未指定',
            '修正后基准': `${editor.imageWidth}x${editor.imageHeight}`,
            '是否需要修正': originalImageWidth !== editor.imageWidth || 
                           originalImageHeight !== editor.imageHeight
          });
        }

        // 重新适配视图
        editor.fitToView();
      }

      return result;
    } catch (error) {
      console.error('视频首帧加载失败:', error);
      throw error;
    }
  }

  /**
   * 获取当前视频元数据
   */
  getVideoMetadata() {
    return this.videoMetadata;
  }

  /**
   * 启用/禁用调试模式
   */
  setDebugMode(enabled) {
    this.debugMode = enabled;
  }

  /**
   * 检查是否应用了视频帧修正
   */
  isVideoCorrectionApplied(editor) {
    return editor._videoFrameCorrection && editor._videoFrameCorrection.correctionApplied;
  }

  /**
   * 获取视频帧修正信息
   */
  getVideoCorrectionInfo(editor) {
    return editor._videoFrameCorrection || null;
  }

  /**
   * 清除视频帧修正信息
   */
  clearVideoCorrection(editor) {
    if (editor._videoFrameCorrection) {
      delete editor._videoFrameCorrection;
    }
    this.videoMetadata = null;
  }

  /**
   * 修正编辑器坐标基准
   * @param {Object} editor - 编辑器实例
   * @param {Object} metadata - 视频元数据
   * @param {Object} targetResolution - 目标分辨率
   */
  static correctEditorDimensions(editor, metadata, targetResolution = null) {
    if (!editor || !metadata) return;
    
    console.log('VideoFrameFix: 坐标修复 - 设置编辑器尺寸');
    
    // 使用目标分辨率或原始视频尺寸作为坐标基准
    if (targetResolution) {
      editor.imageWidth = targetResolution.width;
      editor.imageHeight = targetResolution.height;
      console.log(`VideoFrameFix: 使用目标分辨率 ${targetResolution.width}x${targetResolution.height}`);
    } else {
      editor.imageWidth = metadata.originalVideoWidth;
      editor.imageHeight = metadata.originalVideoHeight;
      console.log(`VideoFrameFix: 使用原始视频尺寸 ${metadata.originalVideoWidth}x${metadata.originalVideoHeight}`);
    }
    
    // 更新界面显示
    if (typeof updateMetaDisplay === 'function') {
      updateMetaDisplay();
    }
  }

  /**
   * 输出调试信息
   * @param {Object} metadata - 视频元数据
   * @param {Object} editor - 编辑器实例
   * @param {Object} targetResolution - 目标分辨率
   */
  static logDimensionInfo(metadata, editor, targetResolution = null) {
    if (!this.debugMode) return;
    
    console.log('VideoFrameFix: 尺寸信息对比', {
      '原始视频尺寸': `${metadata.originalVideoWidth}x${metadata.originalVideoHeight}`,
      'Canvas绘制尺寸': `${metadata.canvasWidth}x${metadata.canvasHeight}`,
      '目标分辨率': targetResolution ? `${targetResolution.width}x${targetResolution.height}` : '未指定',
      '编辑器坐标基准': `${editor.imageWidth}x${editor.imageHeight}`,
      '视频文件': metadata.videoFile,
      '提取时间': metadata.extractTime,
      '分辨率转换': targetResolution ? '已启用' : '未启用'
    });
  }
}

// 全局实例
window.VideoFrameFix = new VideoFrameFix();