// AI剪辑师页面 - 新布局实现
(function(){
  // DOM元素引用
  const elPrompt = document.getElementById('ae-prompt');
  // 新的两类上传控件
  const elRefFile = document.getElementById('ae-ref-file');
  const elAddRefFile = document.getElementById('ae-add-ref-file');
  const elRefFileList = document.getElementById('ae-ref-file-list');
  const elClips = document.getElementById('ae-clips');
  const elAddClips = document.getElementById('ae-add-clips');
  const elClipsList = document.getElementById('ae-clips-list');
  const elModel = document.getElementById('ae-model');
  const elTemplate = document.getElementById('ae-template');
  const elOutputFormat = document.getElementById('ae-output-format');
  const elSend = document.getElementById('ae-send');
  const elStop = document.getElementById('ae-stop');
  const elStatus = document.getElementById('ae-status');
  const elProgress = document.getElementById('ae-progress');
  const elProgressText = document.getElementById('ae-progress-text');
  const elSubProgress = document.getElementById('ae-sub-progress');
  const elLog = document.getElementById('ae-log');
  
  // 新增元素
  const elRawResponse = document.getElementById('ae-raw-response');
  const elCopyRawResponse = document.getElementById('ae-copy-raw-response');
  const elRawText = document.getElementById('ae-raw-text');
  const elCopyRaw = document.getElementById('ae-copy-raw');
  const elUpdateTable = document.getElementById('ae-update-table');
  const elTableContainer = document.getElementById('ae-table-container');
  const elSaveTable = document.getElementById('ae-save-table');
  const elOpenStrategy = document.getElementById('ae-open-strategy');

  // 停止控制：支持中断上传与聊天请求
  let currentChatAbortController = null;
  const currentXHRs = [];
  let currentJsonData = null; // 存储当前的JSON数据
  // 文件选择状态（新）
  const referenceFiles = []; // [{ file }]
  const clipFiles = []; // [{ file }]

  // 提示词框自动扩展功能
  if (elPrompt) {
    // 记录原始高度
    const originalHeight = '8rem'; // h-32 对应 8rem
    const expandedHeight = '16rem'; // 扩展后的高度
    
    // 获得焦点时扩展
    elPrompt.addEventListener('focus', function() {
      this.style.height = expandedHeight;
      this.style.transition = 'height 0.3s ease';
    });
    
    // 失去焦点时收缩（如果内容不多的话）
    elPrompt.addEventListener('blur', function() {
      // 检查内容长度，如果内容较少则收缩
      const lineCount = this.value.split('\n').length;
      const charCount = this.value.length;
      
      // 如果内容较少（少于3行或少于100个字符），则收缩回原始高度
      if (lineCount <= 3 && charCount <= 100) {
        this.style.height = originalHeight;
      }
      // 否则保持扩展状态
    });
    
    // 输入时动态调整高度
    elPrompt.addEventListener('input', function() {
      // 重置高度以获取正确的scrollHeight
      this.style.height = 'auto';
      // 设置为内容高度，但不小于扩展高度
      const newHeight = Math.max(this.scrollHeight, 256); // 256px = 16rem
      this.style.height = newHeight + 'px';
    });
  }

  // 工具函数
  function setStatus(msg){ if(elStatus) elStatus.textContent = msg || ''; }
  function setProgress(pct, text){
    if(elProgress) elProgress.style.width = `${Math.max(0, Math.min(100, pct))}%`;
    if(elProgressText) elProgressText.textContent = text || '';
  }
  function setSubProgress(text){ if(elSubProgress) elSubProgress.textContent = text || ''; }
  function appendLogLine(line){
    if(!elLog) return;
    const now = new Date();
    const t = now.toLocaleTimeString();
    elLog.textContent += `[${t}] ${line}\n`;
    elLog.scrollTop = elLog.scrollHeight;
  }

  // 渲染参考视频文件列表
  function renderRefFileList(){
    if(!elRefFileList) return;
    elRefFileList.innerHTML = '';
    
    if(referenceFiles.length === 0) {
      elRefFileList.innerHTML = '<p class="text-gray-500 text-sm">暂无选择的参考视频</p>';
      return;
    }
    
    referenceFiles.forEach((item, idx) => {
      const f = item.file;
      const div = document.createElement('div');
      div.className = 'flex items-center justify-between bg-gray-50 border border-gray-200 rounded-lg p-2 mb-2';
      
      const meta = document.createElement('div');
      meta.className = 'text-sm text-gray-700 flex-1';
      meta.textContent = `${f.name} (${(f.size/1024/1024).toFixed(2)}MB)`;
      
      const btn = document.createElement('button');
      btn.className = 'text-xs px-2 py-1 bg-red-600 text-white rounded hover:bg-red-700 transition-colors ml-2';
      btn.textContent = '删除';
      btn.onclick = () => { 
        referenceFiles.splice(idx, 1); 
        renderRefFileList(); 
        setStatus(`已删除参考视频: ${f.name}`);
        appendLogLine(`删除参考视频: ${f.name}`);
      };
      
      div.appendChild(meta);
      div.appendChild(btn);
      elRefFileList.appendChild(div);
    });
  }

  // 渲染剪辑视频文件列表
  function renderClipsList(){
    if(!elClipsList) return;
    elClipsList.innerHTML = '';
    
    if(clipFiles.length === 0) {
      elClipsList.innerHTML = '<p class="text-gray-500 text-sm">暂无选择的剪辑视频</p>';
      return;
    }
    
    clipFiles.forEach((item, idx) => {
      const f = item.file;
      const div = document.createElement('div');
      div.className = 'flex items-center justify-between bg-gray-50 border border-gray-200 rounded-lg p-2 mb-2';
      
      const meta = document.createElement('div');
      meta.className = 'text-sm text-gray-700 flex-1';
      meta.textContent = `${f.name} (${(f.size/1024/1024).toFixed(2)}MB)`;
      
      const btn = document.createElement('button');
      btn.className = 'text-xs px-2 py-1 bg-red-600 text-white rounded hover:bg-red-700 transition-colors ml-2';
      btn.textContent = '删除';
      btn.onclick = () => { 
        clipFiles.splice(idx, 1); 
        renderClipsList(); 
        setStatus(`已删除剪辑视频: ${f.name}`);
        appendLogLine(`删除剪辑视频: ${f.name}`);
      };
      
      div.appendChild(meta);
      div.appendChild(btn);
      elClipsList.appendChild(div);
    });
  }

  // 参考视频文件选择事件
  elRefFile?.addEventListener('change', (e) => {
    const files = Array.from(e.target.files || []);
    let addedCount = 0;
    
    for(const f of files) {
      // 检查是否为视频文件
      if(!f.type.startsWith('video/')) {
        appendLogLine(`跳过非视频文件: ${f.name}`);
        continue;
      }
      
      referenceFiles.push({ file: f });
      addedCount++;
      appendLogLine(`添加参考视频: ${f.name}`);
    }
    
    if(addedCount > 0) {
      renderRefFileList();
      setStatus(`已添加 ${addedCount} 个参考视频文件`);
    }
    
    // 清空input值，允许重复选择同一文件
    e.target.value = '';
  });

  // 剪辑视频文件选择事件
  elClips?.addEventListener('change', (e) => {
    const files = Array.from(e.target.files || []);
    let addedCount = 0;
    
    for(const f of files) {
      // 检查是否为视频文件
      if(!f.type.startsWith('video/')) {
        appendLogLine(`跳过非视频文件: ${f.name}`);
        continue;
      }
      
      clipFiles.push({ file: f });
      addedCount++;
      appendLogLine(`添加剪辑视频: ${f.name}`);
    }
    
    if(addedCount > 0) {
      renderClipsList();
      setStatus(`已添加 ${addedCount} 个剪辑视频文件`);
    }
    
    // 清空input值，允许重复选择同一文件
    e.target.value = '';
  });

  // 发送请求
  elSend?.addEventListener('click', async ()=>{
    try{
      // 初始化停止控制器
      currentChatAbortController = new AbortController();
      let waitingTimer = null;
      let waitingSeconds = 0;
      setStatus('正在发送到 Gemini...');
      setProgress(10, '准备请求');
      setSubProgress('整理素材…');
      if(elLog) elLog.textContent = '';
      appendLogLine('开始请求');

      // 校验数量上限
      if(clipFiles.length > 10){
        setStatus('最多只能选择10个文件');
        return;
      }

      // 构建两类素材的负载：参考视频与剪辑素材
      // 剪辑素材：处理图片为Base64；视频走上传接口
      const clipPayloads = [];
      const clipImages = clipFiles.filter(x => x.file.type.startsWith('image/'));
      const clipVideos = clipFiles.filter(x => x.file.type.startsWith('video/'));

      for(const item of clipImages){
        const f = item.file;
        setProgress(15, `处理图片 ${f.name}`);
        setSubProgress('读取图片为Base64…');
        const b64 = await fileToBase64(f);
        clipPayloads.push({ kind: 'image', mimeType: f.type, data: b64, name: f.name });
        appendLogLine(`图片内联：${f.name}`);
      }

      for(let i=0;i<clipVideos.length;i++){
        const f = clipVideos[i].file;
        const sizeMB = (f.size/1024/1024).toFixed(2);
        setProgress(20 + Math.floor((i/clipVideos.length)*20), `上传视频 ${f.name}`);
        setSubProgress('准备上传…');
        appendLogLine(`开始上传视频：${f.name} · 大小 ${sizeMB}MB`);
        const form = new FormData();
        form.append('files', f);
        const { uploadedInfo } = await xhrUpload('/api/auto-editor/upload', form, (loaded, total) => {
          const pct = total ? Math.round((loaded/total)*100) : 0;
          setSubProgress(`上传进度：${pct}%`);
        });
        if(uploadedInfo && uploadedInfo.length){
          const info = uploadedInfo[0];
          clipPayloads.push({ kind: 'video', mimeType: info.mimeType, name: info.name, id: info.id, path: info.path });
          appendLogLine(`上传完成：${info.name} → ${info.path}`);
        } else {
          appendLogLine(`上传失败：${f.name}`);
        }
      }

      setProgress(50, '素材就绪');
      setSubProgress('');

      // 每次发送都生成新的conversation_id，实现独立会话，避免历史对话影响当前对话
      const conversationId = crypto.randomUUID ? crypto.randomUUID() : String(Date.now() + Math.random());
      const outputFormat = elOutputFormat?.value || 'markdown';
      const template = elTemplate?.value || 'custom';
      // 参考视频：支持多选，逐个上传后作为数组发送
      const referencePayloads = [];
      const refVideos = referenceFiles.filter(x => x.file.type.startsWith('video/'));
      for(let i=0;i<refVideos.length;i++){
        const f = refVideos[i].file;
        const sizeMB = (f.size/1024/1024).toFixed(2);
        appendLogLine(`准备参考视频：${f.name} · 大小 ${sizeMB}MB`);
        const form = new FormData();
        form.append('files', f);
        const { uploadedInfo } = await xhrUpload('/api/auto-editor/upload', form, (loaded, total) => {
          const pct = total ? Math.round((loaded/total)*100) : 0;
          setSubProgress(`参考视频上传进度：${pct}%`);
        });
        if(uploadedInfo && uploadedInfo.length){
          const info = uploadedInfo[0];
          referencePayloads.push({ kind: 'video', mimeType: info.mimeType, name: info.name, id: info.id, path: info.path });
          appendLogLine(`参考视频上传完成：${info.name} → ${info.path}`);
        } else {
          appendLogLine(`参考视频上传失败：${f.name}`);
        }
      }

      const body = {
        model: elModel?.value || 'gemini-2.5-pro',
        text: elPrompt?.value || '',
        reference_files: referencePayloads,
        clip_files: clipPayloads,
        conversation_id: conversationId,
        output_format: outputFormat,
        template: template
      };

      appendLogLine('发送请求到后端');
      setProgress(70, '请求API');
      setSubProgress('合成请求并携带会话ID…');
      const resp = await fetch('/api/auto-editor/chat',{
        method:'POST',
        headers:{ 'Content-Type':'application/json' },
        body: JSON.stringify(body),
        signal: currentChatAbortController.signal
      });
      
      // 启动等待中的心跳提示
      waitingTimer = setInterval(()=>{
        waitingSeconds += 1;
        setSubProgress(`等待模型响应… ${waitingSeconds}s`);
        if(waitingSeconds % 5 === 0) appendLogLine(`仍在等待模型响应… ${waitingSeconds}s`);
      }, 1000);
      
      setProgress(80, '等待响应');
      const json = await resp.json();
      if(waitingTimer){ clearInterval(waitingTimer); waitingTimer = null; }
      
      if(!resp.ok){
        setStatus(`错误：${json.error || resp.status}`);
        appendLogLine(`错误：${JSON.stringify(json.error || resp.status)}`);
        const serverLog = json.log || [];
        for(const item of serverLog){
          const msg = `${item.stage || 'stage'}: ${item.message || ''}`;
          appendLogLine(msg);
        }
        return;
      }
      
      setStatus('完成');
      setProgress(100, '完成');
      setSubProgress('');

      // 处理响应数据
      const responseText = json.text || JSON.stringify(json.jsonData || json, null, 2);
      
      // 更新回复原文本区域（显示AI的完整原始回复）
      if (elRawResponse) {
        // 显示完整的原始回复，包括文字描述等所有内容
        const fullRawResponse = json.raw_response || json.original_response || json.full_text || JSON.stringify(json, null, 2);
        elRawResponse.textContent = fullRawResponse;
      }
      
      // 更新原文区域
      if (elRawText) {
        elRawText.value = responseText;
      }

      // 后端日志
      const serverLog = json.log || [];
      for(const item of serverLog){
        const msg = `${item.stage || 'stage'}: ${item.message || ''}`;
        appendLogLine(msg);
      }
      if(json.conversation_id){
        appendLogLine(`会话ID：${json.conversation_id}`);
      }
      
    } catch(e){
      console.error(e);
      setStatus('发送失败');
      appendLogLine(`异常：${String(e)}`);
      setProgress(0, '失败');
      setSubProgress('');
    }
  });

  // 停止按钮：中断所有上传与聊天
  elStop?.addEventListener('click', ()=>{
    try{
      // 取消聊天fetch
      if(currentChatAbortController){
        currentChatAbortController.abort();
        currentChatAbortController = null;
      }
      // 取消上传XHR
      for(const xhr of currentXHRs){
        try{ xhr.abort(); }catch(err){}
      }
      currentXHRs.length = 0;
      setStatus('已停止');
      setProgress(0, '已停止');
      setSubProgress('');
      appendLogLine('操作已停止');
    }catch(err){
      appendLogLine(`停止异常：${String(err)}`);
    }
  });

  // 确认更新表格按钮事件
  console.log('elUpdateTable element:', elUpdateTable);
  elUpdateTable?.addEventListener('click', () => {
    console.log('确认更新表格按钮被点击');
    appendLogLine('确认更新表格按钮被点击');
    
    try {
      let rawText = elRawText?.value || '';
      console.log('原始文本内容:', rawText);
      
      if (!rawText.trim()) {
        setStatus('请先输入或获取JSON原文');
        appendLogLine('错误：原文为空');
        return;
      }

      // 清理markdown代码块标记
      rawText = cleanJsonText(rawText);
      console.log('清理后的文本内容:', rawText);
      appendLogLine('已清理markdown代码块标记');

      appendLogLine('开始解析JSON并更新表格');
      const jsonData = JSON.parse(rawText);
      console.log('解析的JSON数据:', jsonData);
      appendLogLine(`JSON解析成功，数据类型: ${typeof jsonData}`);
      currentJsonData = jsonData;
      
      const tableHtml = renderTable(jsonData);
      console.log('生成的表格HTML长度:', tableHtml.length);
      appendLogLine(`表格HTML生成完成，长度: ${tableHtml.length}`);
      
      if (elTableContainer) {
        elTableContainer.innerHTML = tableHtml;
        appendLogLine('表格更新完成');
        setStatus('表格已更新');
        
        // 显示保存和打开策划页按钮
        if (elSaveTable) elSaveTable.classList.remove('hidden');
        if (elOpenStrategy) elOpenStrategy.classList.remove('hidden');
      } else {
        appendLogLine('错误：表格容器元素未找到');
        console.error('elTableContainer not found');
      }
    } catch (error) {
      console.error('JSON解析错误:', error);
      appendLogLine(`JSON解析错误: ${error.message}`);
      setStatus('JSON解析失败，请检查格式');
    }
  });

  // 表格渲染函数
  function renderTable(data) {
    try {
      console.log('renderTable called with data:', data);
      console.log('数据类型:', typeof data);
      console.log('数据键:', Object.keys(data || {}));
      
      // 优先检查Phase2数据
      let phase2Data = null;
      
      if (data && data.phase2_creation_and_delivery) {
        phase2Data = data.phase2_creation_and_delivery;
        console.log('找到 phase2_creation_and_delivery 数据:', phase2Data);
      } else if (data && data.phase2) {
        phase2Data = data.phase2;
        console.log('找到 phase2 数据:', phase2Data);
      } else if (data && data.videoProductionBlueprint) {
        phase2Data = { videoProductionBlueprint: data.videoProductionBlueprint };
        console.log('找到 videoProductionBlueprint 数据:', phase2Data);
      }
      
      // 检查phase2Data是否有videoProductionBlueprint
      if (phase2Data && phase2Data.videoProductionBlueprint) {
        console.log('phase2Data.videoProductionBlueprint:', phase2Data.videoProductionBlueprint);
        console.log('videoProductionBlueprint 数组长度:', phase2Data.videoProductionBlueprint.length);
      }
      
      // 如果找到Phase2数据，优先渲染
      if (phase2Data && phase2Data.videoProductionBlueprint && Array.isArray(phase2Data.videoProductionBlueprint) && phase2Data.videoProductionBlueprint.length > 0) {
        console.log('渲染Phase2表格，数据项数量:', phase2Data.videoProductionBlueprint.length);
        return renderPhase2OnlyTable(phase2Data);
      }
      
      // 检查是否有完整的两阶段数据
      const hasNewTwoPhase = data && 
        ((data.phase1 && data.phase2) || 
         (data.phase1_analysis_and_strategy && data.phase2_creation_and_delivery));
      
      if (hasNewTwoPhase) {
        console.log('渲染两阶段表格');
        const normalizedData = {
          phase1: data.phase1 || data.phase1_analysis_and_strategy,
          phase2: data.phase2 || data.phase2_creation_and_delivery
        };
        return renderTwoPhaseTable(normalizedData);
      }
      
      console.log('数据格式不支持，返回错误信息');
      return '<div class="text-center text-gray-500 py-8"><p>数据格式不支持，请检查JSON结构</p><p>支持的格式：phase2_creation_and_delivery.videoProductionBlueprint 或 phase1+phase2</p></div>';
      
    } catch (error) {
      console.error('表格渲染错误:', error);
      return `<div class="text-center text-red-500 py-8"><p>表格渲染错误: ${error.message}</p></div>`;
    }
  }

  // 渲染Phase2表格 - 根据文档字段映射要求
  function renderPhase2OnlyTable(data) {
    try {
      console.log('renderPhase2OnlyTable called with:', data);
      
      const blueprint = data.videoProductionBlueprint || [];
      console.log('视频数据数组:', blueprint);
      console.log('视频数据数量:', blueprint.length);
      
      if (!Array.isArray(blueprint) || blueprint.length === 0) {
        return '<div class="text-center text-gray-500 py-8"><p>没有找到视频制作蓝图数据</p></div>';
      }
      
      let html = `
        <div class="bg-white rounded-lg shadow-lg overflow-hidden">
          <div class="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-4">
            <h2 class="text-xl font-bold">Phase 2: 视频制作蓝图</h2>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">序列编号</th>
                  <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">视频来源</th>
                  <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">起始时间</th>
                  <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">截止时间</th>
                  <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">画面描述</th>
                  <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">口播文案</th>
                  <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">导演备注</th>
                  <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
      `;
      
      blueprint.forEach((item, index) => {
        console.log(`处理第${index + 1}个视频:`, item);
        
        // 支持样例JSON的字段名
        const sequenceNumber = item.sequence || item.sequenceNumber || (index + 1);
        const clipSource = item.clipSource || item.videoName || item.video_name || '';
        const startTime = normalizeTime(item.clipSourceStartTime || item.startTime || item.start_time || '');
        const endTime = normalizeTime(item.clipSourceEndTime || item.endTime || item.end_time || '');
        const clipDescription = item.clipDescription || item.sceneDescription || item.scene_description || '';
        const voiceover = item.englishVoiceoverScript || item.voiceover || item.voiceover_script || '';
        const directorNotes = item.directorsNotes || item.directorNotes || item.director_notes || '';
        
        console.log(`渲染数据: 序号=${sequenceNumber}, 来源=${clipSource}, 开始=${startTime}, 结束=${endTime}`);
        
        html += `
          <tr class="hover:bg-gray-50">
            <td class="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${sequenceNumber}</td>
            <td class="px-4 py-4 text-sm text-gray-900 max-w-xs truncate" title="${clipSource}">${clipSource}</td>
            <td class="px-4 py-4 whitespace-nowrap text-sm text-gray-900">${startTime}</td>
            <td class="px-4 py-4 whitespace-nowrap text-sm text-gray-900">${endTime}</td>
            <td class="px-4 py-4 text-sm text-gray-900 max-w-xs truncate" title="${clipDescription}">${clipDescription}</td>
            <td class="px-4 py-4 text-sm text-gray-900 max-w-xs truncate" title="${voiceover}">${voiceover}</td>
            <td class="px-4 py-4 text-sm text-gray-900 max-w-xs truncate" title="${directorNotes}">${directorNotes}</td>
            <td class="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
              <button class="text-blue-600 hover:text-blue-900">编辑</button>
            </td>
          </tr>
        `;
      });
      
      html += `
              </tbody>
            </table>
          </div>
        </div>
      `;
      
      console.log('表格HTML生成完成，长度:', html.length);
      return html;
      
    } catch (error) {
      console.error('Phase2表格渲染错误:', error);
      return `<div class="text-center text-red-500 py-8"><p>Phase2表格渲染错误: ${error.message}</p></div>`;
    }
  }

  // JSON文本清理函数
  function cleanJsonText(text) {
    if (!text) return text;
    
    // 去除markdown代码块标记
    text = text.replace(/^```json\s*/i, '').replace(/^```\s*/, '').replace(/\s*```\s*$/g, '');
    
    // 去除可能的其他markdown标记
    text = text.replace(/^`+\s*/, '').replace(/\s*`+\s*$/g, '');
    
    // 去除首尾空白字符
    text = text.trim();
    
    return text;
  }

  // 时间格式规范化函数
  function normalizeTime(timeStr) {
    if (!timeStr) return '';
    
    // 如果已经是 mm:ss 格式，直接返回
    if (/^\d{1,2}:\d{2}$/.test(timeStr)) {
      return timeStr;
    }
    
    // 尝试从各种格式中提取时间
    const timeMatch = timeStr.match(/(\d+):(\d+)/);
    if (timeMatch) {
      const minutes = parseInt(timeMatch[1]);
      const seconds = parseInt(timeMatch[2]);
      return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    
    // 如果包含秒数，尝试转换
    const secondsMatch = timeStr.match(/(\d+)s/);
    if (secondsMatch) {
      const totalSeconds = parseInt(secondsMatch[1]);
      const minutes = Math.floor(totalSeconds / 60);
      const seconds = totalSeconds % 60;
      return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    
    return timeStr; // 无法解析时返回原始字符串
  }

  // 渲染两阶段表格
  function renderTwoPhaseTable(data) {
    let html = '<div class="space-y-6">';
    html += '<h3 class="text-lg font-semibold text-gray-900">两阶段视频制作蓝图</h3>';
    
    // Phase 1: 分析与策略
    if (data.phase1) {
      html += '<div class="bg-blue-50 p-4 rounded-lg">';
      html += '<h4 class="text-md font-semibold text-blue-900 mb-3">Phase 1: 分析与策略</h4>';
      
      // 关键卖点
      if (data.phase1.keySellingPoints && Array.isArray(data.phase1.keySellingPoints)) {
        html += '<div class="mb-4">';
        html += '<h5 class="text-sm font-medium text-gray-700 mb-2">关键卖点</h5>';
        html += '<div class="overflow-x-auto">';
        html += '<table class="min-w-full bg-white border border-gray-200 rounded">';
        html += '<thead class="bg-gray-50"><tr><th class="px-3 py-2 text-left text-xs font-medium text-gray-500">序号</th><th class="px-3 py-2 text-left text-xs font-medium text-gray-500">卖点</th></tr></thead><tbody>';
        data.phase1.keySellingPoints.forEach((point, index) => {
          html += `<tr class="border-t"><td class="px-3 py-2 text-sm">${index + 1}</td><td class="px-3 py-2 text-sm">${point}</td></tr>`;
        });
        html += '</tbody></table></div></div>';
      }
      
      html += '</div>';
    }
    
    // Phase 2: 创作与交付
    if (data.phase2 && data.phase2.videoProductionBlueprint) {
      html += '<div class="bg-green-50 p-4 rounded-lg">';
      html += '<h4 class="text-md font-semibold text-green-900 mb-3">Phase 2: 创作与交付</h4>';
      html += renderPhase2OnlyTable(data.phase2).replace('<div class="space-y-4">', '').replace('</div>', '');
      html += '</div>';
    }
    
    html += '</div>';
    return html;
  }

  // 辅助函数
  function fileToBase64(file){
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve((reader.result || '').toString().split(',')[1] || '');
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  function xhrUpload(url, formData, onProgress){
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', url);
      xhr.responseType = 'json';
      xhr.upload.onprogress = (e) => {
        if(onProgress) onProgress(e.loaded, e.total);
      };
      // 纳入可停止的集合
      currentXHRs.push(xhr);
      xhr.onload = () => {
        try{
          const res = xhr.response || {};
          const files = res.files || [];
          // 完成后移除
          const idx = currentXHRs.indexOf(xhr);
          if(idx >= 0) currentXHRs.splice(idx,1);
          resolve({ uploadedInfo: files });
        }catch(err){ reject(err); }
      };
      xhr.onerror = () => reject(new Error('上传失败'));
      xhr.send(formData);
    });
  }

  // 初始化文件显示
  function initializeFileDisplays() {
    renderRefFileList();
    renderClipsList();
    appendLogLine('页面初始化完成');
  }

  // 页面加载完成后初始化
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeFileDisplays);
  } else {
    initializeFileDisplays();
  }

})();
