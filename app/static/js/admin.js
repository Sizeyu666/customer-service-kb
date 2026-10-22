/* =========================================================================
   用户管理页逻辑：数据看板 + 用户列表 + 角色调整
   ========================================================================= */

const AdminPage = {
  users: [],

  async init() {
    const user = await requireAdmin();
    if (!user) return;
    this.me = user;

    this.tbody = document.getElementById('userBody');
    this.stateEl = document.getElementById('userState');
    document.getElementById('refreshBtn').addEventListener('click', () => this.load());

    await this.load();
  },

  async load() {
    this.stateEl.innerHTML = '<div class="loading"><span class="spinner-border spinner-border-sm text-primary"></span>加载中…</div>';
    this.tbody.innerHTML = '';

    try {
      const [stats, users] = await Promise.all([
        authFetch('/api/admin/stats'),
        authFetch('/api/admin/users'),
      ]);
      this.users = users || [];
      document.getElementById('statUsers').textContent = stats.users;
      document.getElementById('statDocs').textContent = stats.documents;
      document.getElementById('statConvs').textContent = stats.conversations;
      document.getElementById('statMsgs').textContent = stats.messages;
      this.render();
    } catch (err) {
      this.stateEl.innerHTML = `<div class="empty-state"><i class="bi bi-exclamation-circle"></i>
        <p>${escapeHtml(err.message)}</p>
        <button class="btn btn-outline-secondary btn-sm" onclick="AdminPage.load()">重试</button></div>`;
    }
  },

  render() {
    if (!this.users.length) {
      this.stateEl.innerHTML = '<div class="empty-state"><i class="bi bi-people"></i><p>暂无用户</p></div>';
      return;
    }
    this.stateEl.innerHTML = '';
    this.tbody.innerHTML = this.users
      .map((user) => {
        const isAdmin = user.role === 'admin';
        const isMe = this.me && user.id === this.me.id;
        return `<tr>
          <td>
            <div style="font-weight:500">${escapeHtml(user.username)}${isMe ? ' <span class="text-subtle" style="font-size:12px">（我）</span>' : ''}</div>
          </td>
          <td>${isAdmin ? '<span class="badge bg-primary">管理员</span>' : '<span class="badge bg-secondary">普通用户</span>'}</td>
          <td class="text-sub">${formatTime(user.created_at)}</td>
          <td class="text-end">
            <select class="form-select form-select-sm d-inline-block" style="width:130px" data-user="${user.id}" ${isMe ? 'disabled' : ''}>
              <option value="user" ${isAdmin ? '' : 'selected'}>普通用户</option>
              <option value="admin" ${isAdmin ? 'selected' : ''}>管理员</option>
            </select>
          </td>
        </tr>`;
      })
      .join('');

    this.tbody.querySelectorAll('[data-user]').forEach((select) => {
      select.addEventListener('change', () => this.changeRole(Number(select.dataset.user), select));
    });
  },

  async changeRole(userId, select) {
    const target = this.users.find((item) => item.id === userId);
    const previous = target ? target.role : 'user';
    const next = select.value;
    select.disabled = true;
    try {
      const updated = await authFetch(`/api/admin/users/${userId}/role`, {
        method: 'PUT',
        body: { role: next },
      });
      if (target) target.role = updated.role;
      showToast('角色已更新', 'success');
      await this.load();
    } catch (err) {
      select.value = previous;
      showToast(err.message, 'error');
    } finally {
      select.disabled = false;
    }
  },
};

document.addEventListener('DOMContentLoaded', () => AdminPage.init());
