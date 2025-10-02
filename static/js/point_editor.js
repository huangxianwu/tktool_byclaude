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

  fromJSON(data, { normalized = false } = {}) {
    if (!data) return;
    const w = this.imageWidth || 1;
    const h = this.imageHeight || 1;
    const parse = (arr, type) => (arr || []).map((p, idx) => ({
      id: p.id ?? this.nextId + idx,
      x: normalized ? (p.x * w) : p.x,
      y: normalized ? (p.y * h) : p.y,
      type
    }));
    const pos = parse(data.positive, 'positive');
    const neg = parse(data.negative, 'negative');
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
  const editor = new PointEditor(canvas, {
    onChange: (data) => {
      const normalized = document.getElementById('normalize-toggle').checked;
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

  // Expose for debugging
  window.__pointEditor = editor;
})();