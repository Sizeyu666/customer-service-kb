/* =========================================================================
   历史记录页逻辑：本人会话列表、关键字搜索、删除
   ========================================================================= */

const HistoryPage = {
  conversations: [],
  keyword: '',

  async init() {
    const user = await requireLogin();
    if (!user) return;

    this.tbody = document.getElementById('historyBody');
    this.stateEl = document.getElementById('historyState');
    document.getElementById('refreshBtn').addEventListener('click', () => this.load());
    document.getElementById('searchInput').addEventListener('input', (event) => {
      this.keyword = event.target.value.trim();
      this.render();
    });

    await this.load();
  },

  async load() {
    this.stateEl.innerHTML = '<div class="loading"><span class="spinner-border spinner-border-sm text-primary"></span>加载中…</div>';
    this.tbody.innerHTML = '';
    try {
      this.conversations = (await authFetch('/api/conversations')) || [];
      this.render();
    } catch (err) {
      this.stateEl.innerHTML = `<div class="empty-state"><i class="bi bi-exclamation-circle"></i>
        <p>${escapeHtml(err.message)}</p>
        <button class="btn btn-outline-secondary btn-sm" onclick="HistoryPage.load()">重试</button></div>`;
    }
  },

  render() {
    const rows = this.keyword
      ? this.conversations.filter((item) => (item.title || '').includes(this.keyword))
      : this.conversations;

    if (!this.conversations.length) {
      this.tbody.innerHTML = '';
      this.stateEl.innerHTML = `<div class="empty-state">
        <i class="bi bi-clock-history"></i>
        <p>还没有历史会话</p>
        <a class="btn btn-primary btn-sm" href="/chat">去提问</a></div>`;
      return;
    }

    if (!rows.length) {
      this.tbody.innerHTML = '';
      this.stateEl.innerHTML = `<div class="empty-state"><i class="bi bi-search"></i>
        <p>没有匹配「${escapeHtml(this.keyword)}」的会话</p></div>`;
      return;
    }

    this.stateEl.innerHTML = '';
    this.tbody.innerHTML = rows
      .map(
        (item) => `<tr>
          <td><span title="${escapeHtml(item.title)}">${escapeHtml(item.title)}</span></td>
          <td class="text-sub mono">${item.message_count || 0}</td>
          <td class="text-sub">${formatTime(item.created_at)}</td>
          <td class="text-end nowrap">
            <a class="btn btn-outline-secondary btn-sm me-1" href="/chat?cid=${item.id}">查看</a>
            <button class="btn btn-outline-secondary btn-sm" data-del="${item.id}">删除</button>
          </td>
        </tr>`
      )
      .join('');

    this.tbody.querySelectorAll('[data-del]').forEach((btn) => {
      btn.addEventListener('click', () => this.remove(Number(btn.dataset.del)));
    });
  },

  async remove(id) {
    if (!window.confirm('确定删除该会话吗？删除后消息无法恢复。')) return;
    try {
      await authFetch(`/api/conversations/${id}`, { method: 'DELETE' });
      this.conversations = this.conversations.filter((item) => item.id !== id);
      this.render();
      showToast('会话已删除', 'success');
    } catch (err) {
      showToast(err.message, 'error');
    }
  },
};

document.addEventListener('DOMContentLoaded', () => HistoryPage.init());
