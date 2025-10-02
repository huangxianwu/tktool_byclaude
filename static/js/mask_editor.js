(() => {
  const fileInput = document.getElementById('file');
  const fileVideoInput = document.getElementById('fileVideo');
  const saveBtn = document.getElementById('save');
  const cancelBtn = document.getElementById('cancel');
  const paintBtn = document.getElementById('paint');
  const eraseBtn = document.getElementById('erase');
  const radiusInput = document.getElementById('radius');
  const rval = document.getElementById('rval');
  const base = document.getElementById('base');
  const mask = document.getElementById('mask');

  const baseCtx = base.getContext('2d');
  const maskCtx = mask.getContext('2d');

  let img = null;
  let drawing = false;
  let mode = 'paint'; // 'paint' | 'erase'
  let radius = parseInt(radiusInput.value, 10) || 20;

  const setEnabled = (enabled) => {
    saveBtn.disabled = !enabled;
    cancelBtn.disabled = !enabled;
  };

  const updateRadiusLabel = () => {
    radius = parseInt(radiusInput.value, 10) || 20;
    rval.textContent = `${radius}px`;
  };

  const clearMask = () => {
    if (!img) return;
    maskCtx.clearRect(0, 0, mask.width, mask.height);
  };

  const drawCircle = (x, y) => {
    if (!img) return;
    maskCtx.beginPath();
    maskCtx.arc(x, y, radius, 0, Math.PI * 2);
    maskCtx.closePath();
    if (mode === 'paint') {
      // 使用半透明高对比颜色，提升可视化效果（导出时仍转白色）
      maskCtx.fillStyle = 'rgba(255, 0, 0, 0.35)';
      maskCtx.globalCompositeOperation = 'source-over';
      maskCtx.fill();
    } else {
      maskCtx.globalCompositeOperation = 'destination-out';
      maskCtx.fillStyle = 'rgba(0,0,0,1)';
      maskCtx.fill();
    }
    maskCtx.globalCompositeOperation = 'source-over';
  };

  const getPos = (e) => {
    const rect = mask.getBoundingClientRect();
    const scaleX = mask.width / rect.width;
    const scaleY = mask.height / rect.height;
    const x = (e.clientX - rect.left) * scaleX;
    const y = (e.clientY - rect.top) * scaleY;
    return { x, y };
  };

  const onPointerDown = (e) => {
    if (!img) return;
    drawing = true;
    const { x, y } = getPos(e);
    drawCircle(x, y);
  };

  const onPointerMove = (e) => {
    if (!img || !drawing) return;
    const { x, y } = getPos(e);
    drawCircle(x, y);
  };

  const onPointerUp = () => {
    drawing = false;
  };

  const renderImage = (image) => {
    // 自适应画布尺寸到图片像素尺寸，确保像素级映射
    base.width = image.naturalWidth;
    base.height = image.naturalHeight;
    mask.width = image.naturalWidth;
    mask.height = image.naturalHeight;

    baseCtx.clearRect(0, 0, base.width, base.height);
    baseCtx.drawImage(image, 0, 0, base.width, base.height);

    clearMask();
    setEnabled(true);
  };

  const renderVideoFrame = (video) => {
    // 使用视频首帧作为底图
    const vw = video.videoWidth;
    const vh = video.videoHeight;
    if (!vw || !vh) return;
    base.width = vw;
    base.height = vh;
    mask.width = vw;
    mask.height = vh;

    baseCtx.clearRect(0, 0, base.width, base.height);
    baseCtx.drawImage(video, 0, 0, base.width, base.height);

    clearMask();
    setEnabled(true);
  };

  const loadFile = (file) => {
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      img = image;
      renderImage(image);
      URL.revokeObjectURL(url);
    };
    image.onerror = () => {
      alert('图片加载失败，请重试');
      URL.revokeObjectURL(url);
    };
    image.src = url;
  };

  const loadVideo = (file) => {
    const url = URL.createObjectURL(file);
    const video = document.createElement('video');
    video.preload = 'metadata';
    video.src = url;
    video.muted = true;
    video.playsInline = true;
    const cleanup = () => URL.revokeObjectURL(url);

    const tryDraw = () => {
      renderVideoFrame(video);
      img = video; // 标记已有底图，允许绘制/导出
      cleanup();
    };

    video.addEventListener('loadedmetadata', () => {
      try { video.currentTime = 0; } catch (e) {}
    });
    video.addEventListener('seeked', tryDraw);
    video.addEventListener('loadeddata', tryDraw); // 兼容部分浏览器
    video.addEventListener('error', () => { alert('视频加载失败，请重试'); cleanup(); });
  };

  const exportMaskPNG = () => {
    if (!img) return;
    // 导出灰度遮罩：白色代表遮罩区域，黑色透明背景
    // 将透明背景转换为黑色，白色保持
    const temp = document.createElement('canvas');
    temp.width = mask.width;
    temp.height = mask.height;
    const tctx = temp.getContext('2d');
    tctx.drawImage(mask, 0, 0);
    const imgData = tctx.getImageData(0, 0, temp.width, temp.height);
    const data = imgData.data;
    for (let i = 0; i < data.length; i += 4) {
      const r = data[i];
      const g = data[i + 1];
      const b = data[i + 2];
      const a = data[i + 3];
      // 透明像素 -> 黑色
      if (a === 0) {
        data[i] = 0; data[i + 1] = 0; data[i + 2] = 0; data[i + 3] = 255;
      } else {
        // 非透明保持白色
        data[i] = 255; data[i + 1] = 255; data[i + 2] = 255; data[i + 3] = 255;
      }
    }
    tctx.putImageData(imgData, 0, 0);
    const link = document.createElement('a');
    link.download = 'mask.png';
    link.href = temp.toDataURL('image/png');
    link.click();
  };

  // 事件绑定
  mask.addEventListener('pointerdown', onPointerDown);
  window.addEventListener('pointermove', onPointerMove);
  window.addEventListener('pointerup', onPointerUp);

  fileInput.addEventListener('change', (e) => {
    const f = e.target.files && e.target.files[0];
    if (f) loadFile(f);
  });

  fileVideoInput.addEventListener('change', (e) => {
    const f = e.target.files && e.target.files[0];
    if (f) loadVideo(f);
  });

  paintBtn.addEventListener('click', () => { mode = 'paint'; paintBtn.classList.add('bg-gray-100'); eraseBtn.classList.remove('bg-gray-100'); });
  eraseBtn.addEventListener('click', () => { mode = 'erase'; eraseBtn.classList.add('bg-gray-100'); paintBtn.classList.remove('bg-gray-100'); });

  radiusInput.addEventListener('input', updateRadiusLabel);
  updateRadiusLabel();

  saveBtn.addEventListener('click', exportMaskPNG);
  cancelBtn.addEventListener('click', () => { clearMask(); });

  // 初始状态
  setEnabled(false);
})();