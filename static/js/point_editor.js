// Reusable Point Editor - Canvas based, ComfyUI-compatible pixel coordinates
// No external dependencies; supports mouse, keyboard, and touch gestures.

class PointEditor {
  constructor(canvas, { onChange } = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.onChange = onChange || (() => {});

    // Data space: image pixel coordinates (immutable base)
    this.image = new Image();
    this.imageWidth = 0;
    this.imageHeight = 0;

    // View transformation: display space
    this.scale = 1; // pixels on screen per pixel in image
    this.minScale = 0.05;
    this.maxScale = 20;
    this.offsetX = 0; // image(0,0) maps to screen(offsetX, offsetY)
    this.offsetY = 0;

    // Points: {id, x, y, type: 'positive' | 'negative'} in image pixel space
    this.points = [];
    this.nextId = 1;
    this.activeType = 'positive';

    // Interaction state
    this.draggingId = null;
    this.dragStart = null;
    this.mode = 'add'; // 'add' | 'pan'
    this.hoverId = null;

    // History (undo/redo)
    this.history = [];
    this.future = [];

    // Bind events
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(canvas);
    window.addEventListener('resize', () => this.resize());

    this.initEvents();
    this.resize();
    this.draw();
  }

  // -------- Public API --------
  async loadImage(src) {
    if (!src) return;
    await new Promise((resolve, reject) => {
      this.image.onload = () => {
        this.imageWidth = this.image.naturalWidth;
        this.imageHeight = this.image.naturalHeight;
        this.fitToView();
        this.clearDataOnly();
        this.pushHistory();
        resolve();
      };
      this.image.onerror = reject;
      this.image.src = src;
    });
  }

  async loadImageFile(file) {
    if (!file) return;
    // Only allow JPG/PNG
    const isValid = /^image\/(png|jpe?g)$/i.test(file.type);
    if (!isValid) throw new Error('Unsupported image type');
    const url = URL.createObjectURL(file);
    if (this._currentObjectURL) {
      try { URL.revokeObjectURL(this._currentObjectURL); } catch {}
    }
    this._currentObjectURL = url;
    await this.loadImage(url);
  }

  setActiveType(type) {
    if (type === 'positive' || type === 'negative') {
      this.activeType = type;
      this.draw();
    }
  }

  toJSON({ normalized = false } = {}) {
    const w = this.imageWidth || 1;
    const h = this.imageHeight || 1;
    const convert = (p) => ({
      x: normalized ? Number((p.x / w).toFixed(12)) : p.x,
      y: normalized ? Number((p.y / h).toFixed(12)) : p.y,
      id: p.id
    });
    return {
      positive: this.points.filter(p => p.type === 'positive').map(convert),
      negative: this.points.filter(p => p.type === 'negative').map(convert)
    };
  }

  fromJSON(data, { normalized = false, useCoordinateFix = false } = {}) {
    if (!data) return;
    
    let processedData = data;
    
    // 如果启用坐标修复，尝试修复ComfyUI坐标
    if (useCoordinateFix && window.CoordinateFix) {
      try {
        const coordinateFix = new window.CoordinateFix(this);
        processedData = coordinateFix.fixComfyUICoordinates(data);
        console.log('坐标修复结果:', {
          original: data,
          fixed: processedData,
          imageSize: { width: this.imageWidth, height: this.imageHeight }
        });
      } catch (error) {
        console.warn('坐标修复失败，使用原始数据:', error);
        processedData = data;
      }
    }
    
    const w = this.imageWidth || 1;
    const h = this.imageHeight || 1;
    const parse = (arr, type) => (arr || []).map((p, idx) => ({
      id: p.id ?? this.nextId + idx,
      x: normalized ? (p.x * w) : p.x,
      y: normalized ? (p.y * h) : p.y,
      type
    }));
    const pos = parse(processedData.positive, 'positive');
    const neg = parse(processedData.negative, 'negative');
    this.points = [...pos, ...neg];
    this.nextId = (this.points.reduce((m, p) => Math.max(m, p.id), 0) || 0) + 1;
    this.pushHistory();
    this.draw();
    this.emitChange();
  }

  // -------- Internal utilities --------
  resize() {
    const rect = this.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = Math.max(2, Math.floor(rect.width * dpr));
    this.canvas.height = Math.max(2, Math.floor(rect.height * dpr));
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.draw();
  }

  fitToView() {
    const rect = this.canvas.getBoundingClientRect();
    if (!this.imageWidth || !this.imageHeight || rect.width === 0 || rect.height === 0) return;
    const scale = Math.min((rect.width - 20) / this.imageWidth, (rect.height - 20) / this.imageHeight);
    this.scale = Math.max(this.minScale, Math.min(this.maxScale, scale));
    this.offsetX = (rect.width - this.imageWidth * this.scale) / 2;
    this.offsetY = (rect.height - this.imageHeight * this.scale) / 2;
    this.draw();
  }

  clearDataOnly() {
    this.points = [];
    this.nextId = 1;
    this.history = [];
    this.future = [];
  }

  pushHistory() {
    const snapshot = JSON.stringify({
      points: this.points,
      scale: this.scale,
      offsetX: this.offsetX,
      offsetY: this.offsetY,
      activeType: this.activeType
    });
    this.history.push(snapshot);
    if (this.history.length > 200) this.history.shift();
    this.future = [];
  }

  undo() {
    if (this.history.length <= 1) return;
    const current = this.history.pop();
    this.future.push(current);
    const prev = JSON.parse(this.history[this.history.length - 1]);
    this.points = JSON.parse(JSON.stringify(prev.points));
    this.scale = prev.scale;
    this.offsetX = prev.offsetX;
    this.offsetY = prev.offsetY;
    this.activeType = prev.activeType;
    this.draw();
    this.emitChange();
  }

  redo() {
    if (this.future.length === 0) return;
    const next = JSON.parse(this.future.pop());
    this.history.push(JSON.stringify(next));
    this.points = JSON.parse(JSON.stringify(next.points));
    this.scale = next.scale;
    this.offsetX = next.offsetX;
    this.offsetY = next.offsetY;
    this.activeType = next.activeType;
    this.draw();
    this.emitChange();
  }

  // coord transforms
  screenToImage(x, y) {
    return { x: (x - this.offsetX) / this.scale, y: (y - this.offsetY) / this.scale };
  }
  imageToScreen(x, y) {
    return { x: this.offsetX + x * this.scale, y: this.offsetY + y * this.scale };
  }

  // event setup
  initEvents() {
    // Mouse
    this.canvas.addEventListener('mousedown', (e) => {
      const { left, top } = this.canvas.getBoundingClientRect();
      const x = e.clientX - left, y = e.clientY - top;
      if (e.button === 1 || (e.button === 0 && this.mode === 'pan')) {
        this.mode = 'pan';
        this.dragStart = { x, y, startOffsetX: this.offsetX, startOffsetY: this.offsetY };
        return;
      }
      const hit = this.pickPoint(x, y);
      if (hit) {
        this.draggingId = hit.id;
        this.dragStart = { x, y, point: { ...hit } };
      } else if (e.button === 0) {
        // add point
        const { x: ix, y: iy } = this.screenToImage(x, y);
        const clamped = { x: Math.max(0, Math.min(this.imageWidth, ix)), y: Math.max(0, Math.min(this.imageHeight, iy)) };
        const p = { id: this.nextId++, x: clamped.x, y: clamped.y, type: this.activeType };
        this.points.push(p);
        this.pushHistory();
        this.draw();
        this.emitChange();
      }
    });

    window.addEventListener('mousemove', (e) => {
      const { left, top } = this.canvas.getBoundingClientRect();
      const x = e.clientX - left, y = e.clientY - top;
      if (this.dragStart && this.mode === 'pan') {
        this.offsetX = this.dragStart.startOffsetX + (x - this.dragStart.x);
        this.offsetY = this.dragStart.startOffsetY + (y - this.dragStart.y);
        this.draw();
        return;
      }
      if (this.draggingId) {
        const idx = this.points.findIndex(p => p.id === this.draggingId);
        if (idx >= 0) {
          const { x: ix, y: iy } = this.screenToImage(x, y);
          this.points[idx].x = Math.max(0, Math.min(this.imageWidth, ix));
          this.points[idx].y = Math.max(0, Math.min(this.imageHeight, iy));
          this.draw();
        }
      } else {
        const hit = this.pickPoint(x, y);
        this.hoverId = hit ? hit.id : null;
        this.canvas.style.cursor = hit ? 'move' : (this.mode === 'pan' ? 'grab' : 'crosshair');
      }
    });

    window.addEventListener('mouseup', (e) => {
      if (this.dragStart && this.mode === 'pan') {
        this.dragStart = null;
        this.mode = 'add';
        this.pushHistory();
      }
      if (this.draggingId) {
        this.draggingId = null;
        this.dragStart = null;
        this.pushHistory();
        this.emitChange();
      }
    });

    // Wheel zoom
    this.canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const delta = -e.deltaY;
      const zoomFactor = Math.exp(delta * 0.0015);
      const { left, top } = this.canvas.getBoundingClientRect();
      const mx = e.clientX - left, my = e.clientY - top;
      this.zoomAt(mx, my, zoomFactor);
    }, { passive: false });

    // Keyboard shortcuts
    window.addEventListener('keydown', (e) => {
      if (e.code === 'Space') {
        this.mode = 'pan';
        this.canvas.style.cursor = 'grab';
        e.preventDefault();
      }
      if ((e.metaKey || e.ctrlKey) && !e.shiftKey && e.key.toLowerCase() === 'z') { this.undo(); e.preventDefault(); }
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 'z') { this.redo(); e.preventDefault(); }
      if (e.key.toLowerCase() === 'p') { this.setActiveType('positive'); }
      if (e.key.toLowerCase() === 'n') { this.setActiveType('negative'); }
      if (e.key.toLowerCase() === 'f') { this.fitToView(); }
      if (e.key === 'Delete' && (e.shiftKey || !this.draggingId)) {
        this.deleteSelectedOrLast();
      }
    });
    window.addEventListener('keyup', (e) => { if (e.code === 'Space') { this.mode = 'add'; this.canvas.style.cursor = 'crosshair'; }});

    // Touch
    let lastTouchDist = 0; let isTouchPanning = false; let lastTouchCenter = null;
    this.canvas.addEventListener('touchstart', (e) => {
      if (e.touches.length === 1) {
        isTouchPanning = true; this.dragStart = { x: e.touches[0].clientX, y: e.touches[0].clientY, startOffsetX: this.offsetX, startOffsetY: this.offsetY };
      } else if (e.touches.length === 2) {
        isTouchPanning = false; lastTouchDist = this._touchDistance(e); lastTouchCenter = this._touchCenter(e);
      }
    }, { passive: true });
    this.canvas.addEventListener('touchmove', (e) => {
      if (e.touches.length === 1 && isTouchPanning && this.dragStart) {
        const dx = e.touches[0].clientX - this.dragStart.x; const dy = e.touches[0].clientY - this.dragStart.y;
        this.offsetX = this.dragStart.startOffsetX + dx; this.offsetY = this.dragStart.startOffsetY + dy; this.draw();
      } else if (e.touches.length === 2) {
        const dist = this._touchDistance(e); const center = this._touchCenter(e);
        const zoomFactor = dist / (lastTouchDist || dist);
        this.zoomAt(center.x - this.canvas.getBoundingClientRect().left, center.y - this.canvas.getBoundingClientRect().top, zoomFactor);
        lastTouchDist = dist; lastTouchCenter = center;
      }
    }, { passive: false });
    this.canvas.addEventListener('touchend', () => { isTouchPanning = false; this.dragStart = null; });

    // Delete with double-click on a point
    this.canvas.addEventListener('dblclick', (e) => {
      const { left, top } = this.canvas.getBoundingClientRect();
      const hit = this.pickPoint(e.clientX - left, e.clientY - top);
      if (hit) {
        this.points = this.points.filter(p => p.id !== hit.id);
        this.pushHistory();
        this.draw();
        this.emitChange();
      }
    });
  }

  deleteSelectedOrLast() {
    if (this.hoverId != null) {
      this.points = this.points.filter(p => p.id !== this.hoverId);
    } else {
      this.points.pop();
    }
    this.pushHistory();
    this.draw();
    this.emitChange();
  }

  zoomAt(mx, my, zoomFactor) {
    const prevScale = this.scale;
    let nextScale = prevScale * zoomFactor;
    nextScale = Math.max(this.minScale, Math.min(this.maxScale, nextScale));
    const { x: ix, y: iy } = this.screenToImage(mx, my);
    this.scale = nextScale;
    const { x: sx, y: sy } = this.imageToScreen(ix, iy);
    // Keep mouse point stable
    this.offsetX += mx - sx;
    this.offsetY += my - sy;
    this.draw();
  }

  pickPoint(sx, sy) {
    // hit test in screen space within radius
    const r = Math.max(6, 6 * window.devicePixelRatio);
    for (let i = this.points.length - 1; i >= 0; i--) {
      const p = this.points[i];
      const sp = this.imageToScreen(p.x, p.y);
      const dx = sp.x - sx, dy = sp.y - sy;
      if (dx * dx + dy * dy <= r * r) return p;
    }
    return null;
  }

  draw() {
    const { ctx, canvas } = this;
    const w = canvas.clientWidth, h = canvas.clientHeight;
    ctx.clearRect(0, 0, w, h);

    // Background
    ctx.fillStyle = '#f3f4f6';
    ctx.fillRect(0, 0, w, h);

    // Image
    if (this.imageWidth && this.imageHeight) {
      ctx.imageSmoothingEnabled = true;
      ctx.drawImage(this.image, this.offsetX, this.offsetY, this.imageWidth * this.scale, this.imageHeight * this.scale);
      // Grid crosshair for visual aid
      this._drawChecker();
    }

    // Points
    const fontSize = 12;
    ctx.font = `${fontSize}px ui-monospace, SFMono-Regular, Menlo, monospace`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    this.points.forEach((p, idx) => {
      const { x, y } = this.imageToScreen(p.x, p.y);
      const radius = 6;
      ctx.lineWidth = 2;
      ctx.strokeStyle = p.type === 'positive' ? '#10b981' : '#ef4444';
      ctx.fillStyle = 'rgba(255,255,255,0.9)';
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      // index number
      ctx.fillStyle = '#111827';
      ctx.fillText(String(idx + 1), x, y - 16);
    });

    // HUD
    const zoomPct = Math.round(this.scale * 100);
    this._setMeta(`meta-zoom`, `${zoomPct}%`);
    this._setMeta(`meta-origin`, `(${this.offsetX.toFixed(0)}, ${this.offsetY.toFixed(0)})`);
    this._setMeta(`meta-size`, this.imageWidth && this.imageHeight ? `${this.imageWidth}×${this.imageHeight}` : '-');
  }

  _setMeta(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  _drawChecker() {
    const { ctx, offsetX, offsetY, scale } = this;
    const step = 50 * scale; // 50px grid in image space
    ctx.save();
    ctx.strokeStyle = 'rgba(0,0,0,0.06)';
    ctx.lineWidth = 1;
    // vertical lines
    for (let x = offsetX % step; x < this.canvas.clientWidth; x += step) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, this.canvas.clientHeight); ctx.stroke();
    }
    // horizontal lines
    for (let y = offsetY % step; y < this.canvas.clientHeight; y += step) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(this.canvas.clientWidth, y); ctx.stroke();
    }
    ctx.restore();
  }

  emitChange() { this.onChange(this.toJSON()); }

  // util
  _touchDistance(e) {
    const [a, b] = e.touches; const dx = a.clientX - b.clientX; const dy = a.clientY - b.clientY; return Math.hypot(dx, dy);
  }
  _touchCenter(e) {
    const [a, b] = e.touches; return { x: (a.clientX + b.clientX) / 2, y: (a.clientY + b.clientY) / 2 };
  }
}

// Page binding
(function init() {
  const canvas = document.getElementById('point-canvas');
  if (!canvas) return;
  
  // 检测是否为嵌入模式
  const urlParams = new URLSearchParams(window.location.search);
  const isEmbedded = urlParams.get('embedded') === 'true';
  const nodeId = urlParams.get('nodeId');
  
  // 如果是嵌入模式，显示保存按钮并隐藏部分功能
  if (isEmbedded) {
    const saveBtn = document.getElementById('tool-save');
    if (saveBtn) {
      saveBtn.classList.remove('hidden');
    }
    
    // 可以选择隐藏一些不必要的按钮
    const exportBtn = document.getElementById('tool-export');
    const importBtn = document.getElementById('tool-import');
    if (exportBtn) exportBtn.style.display = 'none';
    if (importBtn) importBtn.style.display = 'none';
  }
  
  const editor = new PointEditor(canvas, {
    onChange: (data) => {
      const normalized = document.getElementById('normalize-toggle') && document.getElementById('normalize-toggle').checked;
      const out = editor.toJSON({ normalized });
      const ta = document.getElementById('json-output');
      if (ta) ta.value = JSON.stringify(out);
    }
  });

  // 文件选择导入图片（JPG/PNG）
  const imgFileInput = document.getElementById('image-file');
  const loadBtn = document.getElementById('tool-load-image');
  if (loadBtn && imgFileInput) {
    loadBtn.onclick = () => imgFileInput.click();
    imgFileInput.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      try {
        await editor.loadImageFile(file);
        showToast('图片加载成功', 'success');
      } catch {
        showToast('仅支持 JPG/PNG 图片', 'error');
      }
      imgFileInput.value = '';
    });
  }

  // 选择视频并截取首帧作为底图
  const videoFileInput = document.getElementById('fileVideo');
  const btnLoadVideo = document.getElementById('tool-load-video');
  if (btnLoadVideo && videoFileInput) {
    btnLoadVideo.onclick = () => videoFileInput.click();
    videoFileInput.addEventListener('change', async (e) => {
      const file = e.target.files && e.target.files[0];
      if (!file) return;

      try {
        // 使用增强的视频首帧提取功能
        if (window.VideoFrameFix) {
          // 启用调试模式以便观察修正过程
          window.VideoFrameFix.setDebugMode(true);
          
          // 获取用户设置的目标分辨率
          let targetResolution = null;
          const enableResolutionFix = document.getElementById('enable-resolution-fix');
          const targetWidth = document.getElementById('target-width');
          const targetHeight = document.getElementById('target-height');
          
          if (enableResolutionFix && enableResolutionFix.checked && 
              targetWidth && targetHeight && 
              targetWidth.value && targetHeight.value) {
            targetResolution = {
              width: parseInt(targetWidth.value),
              height: parseInt(targetHeight.value)
            };
            console.log('VideoFrameFix: 使用目标分辨率', targetResolution);
          }
          
          await window.VideoFrameFix.loadVideoFrameWithCorrectDimensions(editor, file, targetResolution);
          showToast('已截取首帧作为底图（已修正坐标）', 'success');
        } else {
          // 回退到原始方法
          const extractFirstFrame = (file) => new Promise((resolve, reject) => {
            const url = URL.createObjectURL(file);
            const video = document.createElement('video');
            let cleaned = false;
            const cleanup = () => { if (cleaned) return; cleaned = true; try { URL.revokeObjectURL(url); } catch {} video.src = ''; };
            video.preload = 'auto';
            video.src = url;
            video.muted = true;
            video.playsInline = true;

            const onError = (e) => { cleanup(); reject(e?.error || e || new Error('视频解码错误')); };
            const draw = () => {
              try {
                const vw = video.videoWidth, vh = video.videoHeight;
                if (!vw || !vh) return false;
                const off = document.createElement('canvas');
                off.width = vw; off.height = vh;
                const ctx = off.getContext('2d');
                ctx.drawImage(video, 0, 0, vw, vh);
                const dataUrl = off.toDataURL('image/png');
                cleanup();
                resolve(dataUrl);
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

          const dataUrl = await extractFirstFrame(file);
          await editor.loadImage(dataUrl);
          showToast('已截取首帧作为底图', 'success');
        }
      } catch (err) {
        console.error('提取视频首帧失败:', err);
        showToast('视频加载失败，请重试', 'error');
      }
      e.target.value = '';
    });
  }

  // 支持拖拽图片到画布容器
  const container = document.getElementById('canvas-container');
  if (container) {
    const dragRingClasses = ['ring-2', 'ring-primary'];
    container.addEventListener('dragover', (e) => {
      e.preventDefault();
      container.classList.add(...dragRingClasses);
    });
    container.addEventListener('dragleave', () => {
      container.classList.remove(...dragRingClasses);
    });
    container.addEventListener('drop', async (e) => {
      e.preventDefault();
      container.classList.remove(...dragRingClasses);
      const file = e.dataTransfer.files && e.dataTransfer.files[0];
      if (!file) return;
      try {
        await editor.loadImageFile(file);
        showToast('图片加载成功', 'success');
      } catch {
        showToast('仅支持拖拽 JPG/PNG 图片', 'error');
      }
    });
  }

  // 工具栏按钮
  document.getElementById('tool-positive').onclick = () => editor.setActiveType('positive');
  document.getElementById('tool-negative').onclick = () => editor.setActiveType('negative');
  document.getElementById('tool-move').onclick = () => { editor.mode = 'pan'; };
  document.getElementById('tool-zoomfit').onclick = () => editor.fitToView();
  document.getElementById('tool-clear').onclick = () => { editor.clearDataOnly(); editor.draw(); editor.emitChange(); };
  document.getElementById('tool-undo').onclick = () => editor.undo();
  document.getElementById('tool-redo').onclick = () => editor.redo();

  document.getElementById('normalize-toggle').addEventListener('change', () => editor.emitChange());

  // 导出
  document.getElementById('tool-export').onclick = () => {
    const normalized = document.getElementById('normalize-toggle').checked;
    const json = JSON.stringify(editor.toJSON({ normalized }), null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'points.json'; a.click();
    URL.revokeObjectURL(url);
  };

  // 复制到剪贴板
  const btnCopy = document.getElementById('btn-copy');
  if (btnCopy) {
    btnCopy.onclick = async () => {
      try {
        const ta = document.getElementById('json-output');
        await navigator.clipboard.writeText(ta.value || '');
        showToast('已复制到剪贴板', 'success');
      } catch {
        showToast('复制失败', 'error');
      }
    };
  }

  // 保存按钮（嵌入模式）
  const btnSave = document.getElementById('tool-save');
  if (btnSave && isEmbedded) {
    btnSave.onclick = async () => {
      try {
        // 获取当前坐标数据
        const normalized = document.getElementById('normalize-toggle') && document.getElementById('normalize-toggle').checked;
        const coordinates = editor.toJSON({ normalized });
        
        // 生成标注图片
        let annotatedImage = null;
        if (editor.image && editor.image.src) {
          annotatedImage = await generateAnnotatedImage(editor);
        }
        
        // 准备要传递的数据
        const saveData = {
          coordinates: coordinates,
          annotatedImage: annotatedImage,
          nodeId: nodeId,
          timestamp: new Date().toISOString()
        };
        
        // 向父窗口发送消息
        if (window.parent && window.parent !== window) {
          window.parent.postMessage({
            type: 'pointEditorSave',
            data: saveData
          }, window.location.origin);
        }
        
        showToast('数据已保存', 'success');
      } catch (error) {
        console.error('保存失败:', error);
        showToast('保存失败', 'error');
      }
    };
  }

  // 生成标注图片的函数
  async function generateAnnotatedImage(editor) {
    try {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      
      // 设置画布尺寸为图片原始尺寸
      canvas.width = editor.imageWidth;
      canvas.height = editor.imageHeight;
      
      // 绘制原始图片
      ctx.drawImage(editor.image, 0, 0, editor.imageWidth, editor.imageHeight);
      
      // 绘制坐标点
      const points = editor.points;
      points.forEach(point => {
        ctx.save();
        
        // 设置点的样式
        const isPositive = point.type === 'positive';
        ctx.fillStyle = isPositive ? '#22c55e' : '#ef4444';
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        
        // 绘制圆点
        ctx.beginPath();
        ctx.arc(point.x, point.y, 8, 0, 2 * Math.PI);
        ctx.fill();
        ctx.stroke();
        
        // 绘制标签
        ctx.fillStyle = '#ffffff';
        ctx.font = '12px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(isPositive ? '+' : '-', point.x, point.y + 4);
        
        ctx.restore();
      });
      
      // 返回base64图片数据
      return canvas.toDataURL('image/png');
    } catch (error) {
      console.error('生成标注图片失败:', error);
      return null;
    }
  }

  // 导入点数据
  const fileInput = document.getElementById('file-import');
  document.getElementById('tool-import').onclick = () => fileInput.click();
  fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0]; if (!file) return;
    const text = await file.text();
    try {
      const data = JSON.parse(text);
      const normalized = !!data.normalized || allInUnitRange(data);
      editor.fromJSON(data, { normalized });
      showToast('导入成功', 'success');
    } catch {
      showToast('导入失败：JSON格式错误', 'error');
    }
    fileInput.value = '';
  });

  function allInUnitRange(data) {
    const arr = [...(data.positive||[]), ...(data.negative||[])];
    return arr.every(p => p.x >= 0 && p.x <= 1 && p.y >= 0 && p.y <= 1);
  }

  function detectCoordinateType(data, imageWidth, imageHeight) {
    const arr = [...(data.positive||[]), ...(data.negative||[])];
    if (arr.length === 0) return 'pixel';
    
    // 检查是否所有坐标都在0-1范围内
    const allInUnit = arr.every(p => p.x >= 0 && p.x <= 1 && p.y >= 0 && p.y <= 1);
    if (allInUnit) return 'normalized';
    
    // 检查是否坐标值合理（不超过图片尺寸太多）
    const maxX = Math.max(...arr.map(p => p.x));
    const maxY = Math.max(...arr.map(p => p.y));
    
    if (imageWidth && imageHeight) {
      // 如果坐标值接近图片尺寸，认为是像素坐标
      if (maxX <= imageWidth * 1.2 && maxY <= imageHeight * 1.2) {
        return 'pixel';
      }
    }
    
    // 默认返回像素坐标
    return 'pixel';
  }

  // 粘贴坐标功能
  const pasteModal = document.getElementById('paste-coords-modal');
  const coordsInput = document.getElementById('coords-input');
  const btnPasteCoords = document.getElementById('tool-paste-coords');
  const btnCancelPaste = document.getElementById('cancel-paste');
  const btnConfirmPaste = document.getElementById('confirm-paste');

  if (btnPasteCoords && pasteModal) {
    // 显示模态框
    btnPasteCoords.onclick = () => {
      pasteModal.classList.remove('hidden');
      coordsInput.focus();
      coordsInput.select();
    };

    // 取消按钮
    btnCancelPaste.onclick = () => {
      pasteModal.classList.add('hidden');
      coordsInput.value = '';
    };

    // 点击背景关闭模态框
    pasteModal.onclick = (e) => {
      if (e.target === pasteModal) {
        pasteModal.classList.add('hidden');
        coordsInput.value = '';
      }
    };

    // 确认导入
    btnConfirmPaste.onclick = () => {
      const text = coordsInput.value.trim();
      if (!text) {
        showToast('请输入坐标数据', 'error');
        return;
      }

      try {
        const data = JSON.parse(text);
        
        // 验证数据格式
        if (!data || typeof data !== 'object') {
          throw new Error('数据格式错误');
        }
        
        if (!data.positive && !data.negative) {
          throw new Error('未找到positive或negative坐标数据');
        }

        // 验证坐标数组格式
        const validateCoords = (coords, type) => {
          if (!Array.isArray(coords)) return;
          coords.forEach((coord, idx) => {
            if (typeof coord.x !== 'number' || typeof coord.y !== 'number') {
              throw new Error(`${type}坐标第${idx + 1}项格式错误：需要x和y数值`);
            }
          });
        };

        if (data.positive) validateCoords(data.positive, 'positive');
        if (data.negative) validateCoords(data.negative, 'negative');

        // 获取用户选择的坐标类型
        const coordTypeRadio = document.querySelector('input[name="coord-type"]:checked');
        const userChoice = coordTypeRadio ? coordTypeRadio.value : 'auto';
        
        let normalized = false;
        let coordType = 'pixel';
        
        if (userChoice === 'auto') {
          // 自动检测坐标类型
          coordType = detectCoordinateType(data, editor.imageWidth, editor.imageHeight);
          normalized = (coordType === 'normalized');
        } else if (userChoice === 'normalized') {
          normalized = true;
          coordType = 'normalized';
        } else {
          normalized = false;
          coordType = 'pixel';
        }
        
        // 检查是否启用坐标修复
        const enableFix = document.getElementById('enable-coordinate-fix')?.checked;
        
        // 记录导入信息到调试面板
        console.log('坐标导入信息:', {
          userChoice,
          detectedType: coordType,
          normalized,
          enableFix,
          imageSize: { width: editor.imageWidth, height: editor.imageHeight },
          pointCount: (data.positive?.length || 0) + (data.negative?.length || 0)
        });
        
        // 导入数据（启用或禁用坐标修复）
        editor.fromJSON(data, { normalized, useCoordinateFix: enableFix });
        
        // 更新调试面板
        updateDebugPanel();
        
        // 关闭模态框并清空输入
        pasteModal.classList.add('hidden');
        coordsInput.value = '';
        
        const totalPoints = (data.positive?.length || 0) + (data.negative?.length || 0);
        const typeText = userChoice === 'auto' ? `自动检测为${coordType}坐标` : `${coordType}坐标`;
        showToast(`成功导入 ${totalPoints} 个坐标点（${typeText}）`, 'success');
        
      } catch (error) {
        console.error('导入坐标失败:', error);
        showToast(`导入失败：${error.message}`, 'error');
      }
    };

    // 支持Ctrl+Enter快捷键确认
    coordsInput.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        btnConfirmPaste.click();
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        btnCancelPaste.click();
      }
    });
  }

  // 调试面板功能
  const debugPanel = document.getElementById('debug-panel');
  const debugToggle = document.getElementById('toggle-debug');
  const toolDebug = document.getElementById('tool-debug');

  function updateDebugPanel() {
    if (!debugPanel || debugPanel.classList.contains('hidden')) return;
    
    // 更新图片信息
    const imageSizeEl = document.getElementById('debug-image-size');
    const imageScaleEl = document.getElementById('debug-image-scale');
    
    if (imageSizeEl) {
      if (editor.imageWidth && editor.imageHeight) {
        imageSizeEl.textContent = `${editor.imageWidth} × ${editor.imageHeight}`;
      } else {
        imageSizeEl.textContent = '未加载';
      }
    }
    
    if (imageScaleEl) {
      imageScaleEl.textContent = editor.scale.toFixed(2);
    }
    
    // 更新坐标列表
    const coordsListEl = document.getElementById('debug-coords-list');
    if (coordsListEl) {
      if (editor.points.length === 0) {
        coordsListEl.innerHTML = '<div class="text-gray-400">暂无坐标点</div>';
      } else {
        const coordsHtml = editor.points.map(point => {
          const screenCoord = editor.imageToScreen(point.x, point.y);
          const typeColor = point.type === 'positive' ? 'text-green-600' : 'text-red-600';
          return `
            <div class="mb-1 p-1 bg-gray-50 rounded text-xs">
              <div class="${typeColor} font-medium">ID${point.id} (${point.type})</div>
              <div>原始: (${point.x.toFixed(1)}, ${point.y.toFixed(1)})</div>
              <div>屏幕: (${screenCoord.x.toFixed(1)}, ${screenCoord.y.toFixed(1)})</div>
            </div>
          `;
        }).join('');
        coordsListEl.innerHTML = coordsHtml;
      }
    }
  }

  // 调试面板切换
  if (toolDebug && debugPanel) {
    toolDebug.onclick = () => {
      debugPanel.classList.toggle('hidden');
      updateDebugPanel();
    };
  }

  if (debugToggle && debugPanel) {
    debugToggle.onclick = () => {
      debugPanel.classList.add('hidden');
    };
  }

  // 监听编辑器变化，更新调试面板
  if (editor.onChange) {
    const originalOnChange = editor.onChange;
    editor.onChange = (data) => {
      originalOnChange(data);
      updateDebugPanel();
    };
  } else {
    editor.onChange = updateDebugPanel;
  }

  // 监听图片加载，更新调试面板
  const originalLoadImage = editor.loadImage;
  editor.loadImage = async function(src) {
    const result = await originalLoadImage.call(this, src);
    updateDebugPanel();
    return result;
  };

  // Expose for debugging
  window.__pointEditor = editor;
  window.__updateDebugPanel = updateDebugPanel;
})();