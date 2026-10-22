/* =========================================================================
   知识库管理页逻辑：上传（拖拽/多选）、列表、删除、全量重建
   ========================================================================= */

const DocumentsPage = {
  documents: [],
  selectedFiles: [],
  uploading: false,

  async init() {
    const user = await requireAdmin();
    if (!user) return;

    this.tbody = document.getElementById('docBody');
    this.stateEl = document.getElementById('docState');
    this.fileInput = document.getElementById('fileInput');
    this.fileListEl = document.getElementById('fileList');
    this.confirmBtn = document.getElementById('confirmUpload');
    this.tipEl = document.getElementById('uploadTip');

    document.getElementById('refreshBtn').addEventListener('click', () => this.load());
    document.getElementById('rebuildBtn').addEventListener('click', () => this.rebuild());

    const dropzone = document.getElementById('dropzone');
    dropzone.addEventListener('click', () => this.fileInput.click());
    dropzone.addEventListener('dragover', (event) => {
      event.preventDefault();
      dropzone.classList.add('dragover');
    });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
    dropzone.addEventListener('drop', (event) => {
      event.preventDefault();
      dropzone.classList.remove('dragover');
      this.pickFiles(Array.from(event.dataTransfer.files || []));
    });
    this.fileInput.addEventListener('change', () => this.pickFiles(Array.from(this.fileInput.files || [])));
    this.confirmBtn.addEventListener('click', () => this.upload());

    await this.load();
  },

  badge(status) {
    const map = {
      ready: '<span class="badge bg-success">可用</span>',
      processing: '<span class="badge bg-warning">处理中</span>',
      failed: '<span class="badge bg-danger">失败</span>',
    };
    return map[status] || `<span class="badge bg-secondary">${escapeHtml(status)}</span>`;
  },

  async load() {
    this.stateEl.innerHTML = '<div class="loading"><span class="spinner-border spinner-border-sm text-primary"></span>加载中…</div>';
    this.tbody.innerHTML = '';
    try {
      this.documents = (await authFetch('/api/documents')) || [];
    } catch (err) {
      this.stateEl.innerHTML = `<div class="empty-state"><i class="bi bi-exclamation-circle"></i>
        <p>${escapeHtml(err.message)}</p>
        <button class="btn btn-outline-secondary btn-sm" onclick="DocumentsPage.load()">重试</button></div>`;
      return;
    }
    this.render();
  },

  render() {
    if (!this.documents.length) {
      this.tbody.innerHTML = '';
      this.stateEl.innerHTML = `<div class="empty-state">
        <i class="bi bi-folder2-open"></i>
        <p>知识库还是空的，先上传一份客服文档吧</p>
        <button class="btn btn-primary btn-sm" data-bs-toggle="modal" data-bs-target="#uploadModal">上传文档</button></div>`;
      return;
    }

    this.stateEl.innerHTML = '';
    this.tbody.innerHTML = this.documents
      .map(
        (doc) => `<tr>
          <td>
            <div style="font-weight:500">${escapeHtml(doc.filename)}</div>
            ${doc.error_msg ? `<div class="text-sub" style="font-size:12.5px;color:var(--danger)">${escapeHtml(doc.error_msg)}</div>` : ''}
          </td>
          <td><span class="badge bg-secondary">${escapeHtml((doc.file_type || '').toUpperCase())}</span></td>
          <td>${this.badge(doc.status)}</td>
          <td class="mono text-sub">${doc.chunk_count || 0}</td>
          <td class="text-sub">${formatTime(doc.created_at)}</td>
          <td class="text-end">
            <button class="btn btn-outline-secondary btn-sm" data-del="${doc.id}">删除</button>
          </td>
        </tr>`
      )
      .join('');

    this.tbody.querySelectorAll('[data-del]').forEach((btn) => {
      btn.addEventListener('click', () => this.remove(Number(btn.dataset.del)));
    });
  },

  pickFiles(files) {
    const allowed = ['.pdf', '.docx', '.txt', '.md'];
    const valid = [];
    const rejected = [];
    files.forEach((file) => {
      const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
      if (!allowed.includes(ext)) {
        rejected.push(`${file.name}（类型不支持）`);
      } else if (file.size > 20 * 1024 * 1024) {
        rejected.push(`${file.name}（超过 20MB）`);
      } else {
        valid.push(file);
      }
    });

    this.selectedFiles = valid;
    this.fileListEl.innerHTML = valid
      .map((file) => `<li><i class="bi bi-file-earmark-text me-1"></i>${escapeHtml(file.name)}
        <span class="text-subtle">（${(file.size / 1024).toFixed(0)} KB）</span></li>`)
      .join('');
    if (rejected.length) {
      this.tipEl.textContent = `已跳过：${rejected.join('、')}`;
      this.tipEl.classList.remove('hidden');
    } else {
      this.tipEl.classList.add('hidden');
    }
  },

  async upload() {
    if (this.uploading) return;
    if (!this.selectedFiles.length) {
      showToast('请先选择要上传的文件', 'warning');
      return;
    }

    this.uploading = true;
    this.confirmBtn.disabled = true;
    this.confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>上传并索引中…';
    this.tipEl.textContent = '正在解析文档并写入向量库，文件较多时可能需要几十秒，请勿关闭页面。';
    this.tipEl.classList.remove('hidden');

    const formData = new FormData();
    this.selectedFiles.forEach((file) => formData.append('files', file));

    try {
      const result = await authFetch('/api/documents', { method: 'POST', body: formData });
      const failed = result.failed || [];
      if (failed.length) {
        this.tipEl.textContent = `部分文件失败：${failed.map((item) => `${item.filename}（${item.reason}）`).join('；')}`;
        showToast(`上传完成，成功 ${result.success.length} 个，失败 ${failed.length} 个`, 'warning');
      } else {
        showToast(`上传成功，共 ${result.success.length} 个文档`, 'success');
        const modalEl = document.getElementById('uploadModal');
        bootstrap.Modal.getInstance(modalEl)?.hide();
        this.resetPicker();
      }
      await this.load();
    } catch (err) {
      this.tipEl.textContent = err.message;
      showToast(err.message, 'error');
    } finally {
      this.uploading = false;
      this.confirmBtn.disabled = false;
      this.confirmBtn.textContent = '开始上传并索引';
    }
  },

  resetPicker() {
    this.selectedFiles = [];
    this.fileListEl.innerHTML = '';
    this.tipEl.classList.add('hidden');
    this.fileInput.value = '';
  },

  async remove(id) {
    const doc = this.documents.find((item) => item.id === id);
    const name = doc ? doc.filename : '该文档';
    if (!window.confirm(`确定删除「${name}」吗？将同时删除磁盘文件与向量库中的索引。`)) return;
    try {
      await authFetch(`/api/documents/${id}`, { method: 'DELETE' });
      showToast('文档已删除', 'success');
      await this.load();
    } catch (err) {
      showToast(err.message, 'error');
    }
  },

  async rebuild() {
    if (!window.confirm('将清空现有向量索引并按磁盘文件全部重建，期间问答可能短暂不可用，确定继续吗？')) return;
    const btn = document.getElementById('rebuildBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>重建中…';
    try {
      const result = await authFetch('/api/documents/rebuild', { method: 'POST' });
      showToast(result.message, result.failed ? 'warning' : 'success');
      await this.load();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-arrow-repeat me-1"></i>全部重建索引';
    }
  },
};

document.addEventListener('DOMContentLoaded', () => DocumentsPage.init());
