/* =========================================================================
   公共脚本：令牌管理、统一请求封装、导航渲染、Toast
   ========================================================================= */

const TOKEN_KEY = 'cs_kb_token';
const USER_KEY = 'cs_kb_user';

const Auth = {
  /** 读取本地令牌 */
  getToken() {
    return localStorage.getItem(TOKEN_KEY) || '';
  },
  /** 写入令牌与用户信息 */
  setSession(token, user) {
    localStorage.setItem(TOKEN_KEY, token || '');
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  /** 清理登录态 */
  clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
  /** 读取缓存的用户信息 */
  cachedUser() {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY) || 'null');
    } catch (err) {
      return null;
    }
  },
};

/** 右上角轻提示 */
function showToast(message, type = 'info') {
  let stack = document.getElementById('toastStack');
  if (!stack) {
    stack = document.createElement('div');
    stack.id = 'toastStack';
    stack.className = 'toast-stack';
    document.body.appendChild(stack);
  }
  const el = document.createElement('div');
  el.className = `app-toast ${type}`;
  el.textContent = message;
  stack.appendChild(el);
  window.setTimeout(() => {
    el.style.opacity = '0';
    el.style.transition = 'opacity .2s';
    window.setTimeout(() => el.remove(), 220);
  }, 3200);
}

/**
 * 统一请求封装：
 * 1. 自动携带 Authorization 头
 * 2. 401 清理令牌并跳转登录页
 * 3. 直接返回后端 data 字段，错误抛出中文 message
 */
async function authFetch(url, options = {}) {
  const opts = { ...options, headers: { ...(options.headers || {}) } };
  const token = Auth.getToken();
  if (token) opts.headers.Authorization = `Bearer ${token}`;

  if (opts.body && !(opts.body instanceof FormData)) {
    opts.headers['Content-Type'] = 'application/json';
    if (typeof opts.body !== 'string') opts.body = JSON.stringify(opts.body);
  }

  let response;
  try {
    response = await fetch(url, opts);
  } catch (err) {
    throw new Error('网络异常，请检查网络后重试');
  }

  let payload = null;
  try {
    payload = await response.json();
  } catch (err) {
    payload = null;
  }

  if (response.status === 401) {
    Auth.clearSession();
    if (!location.pathname.startsWith('/login') && !location.pathname.startsWith('/register')) {
      location.href = '/login';
    }
    throw new Error((payload && payload.message) || '登录已过期，请重新登录');
  }

  if (!response.ok) {
    throw new Error((payload && payload.message) || `请求失败（${response.status}）`);
  }

  return payload ? payload.data : null;
}

/** HTML 转义，防止消息内容破坏结构 */
function escapeHtml(text) {
  return String(text == null ? '' : text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/** ISO 时间转「YYYY-MM-DD HH:mm」 */
function formatTime(value, withSeconds = false) {
  if (!value) return '—';
  const date = new Date(value.endsWith('Z') || value.includes('+') ? value : `${value}Z`);
  if (Number.isNaN(date.getTime())) return value;
  const pad = (n) => String(n).padStart(2, '0');
  const base = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
  return withSeconds ? `${base}:${pad(date.getSeconds())}` : base;
}

/** 渲染顶部导航：按登录态与角色显隐 */
function renderNav(user) {
  document.querySelectorAll('[data-role="admin"]').forEach((el) => {
    el.classList.toggle('hidden', !user || user.role !== 'admin');
  });

  const nameEl = document.getElementById('navUserName');
  if (nameEl) nameEl.textContent = user ? user.username : '';

  const guestEl = document.getElementById('navGuest');
  const userEl = document.getElementById('navUserArea');
  if (guestEl) guestEl.classList.toggle('hidden', !!user);
  if (userEl) userEl.classList.toggle('hidden', !user);

  const page = document.body.dataset.page;
  document.querySelectorAll('.app-navbar .nav-link[data-page]').forEach((link) => {
    link.classList.toggle('active', link.dataset.page === page);
  });
}

/** 绑定退出登录 */
function bindLogout() {
  document.querySelectorAll('[data-action="logout"]').forEach((btn) => {
    btn.addEventListener('click', (event) => {
      event.preventDefault();
      Auth.clearSession();
      location.href = '/login';
    });
  });
}

/**
 * 页面登录校验：无令牌直接跳登录；有令牌则向后端确认真实身份。
 * @returns {Promise<object|null>} 当前用户，未登录返回 null（已跳转）
 */
async function requireLogin() {
  if (!Auth.getToken()) {
    location.href = '/login';
    return null;
  }
  try {
    const user = await authFetch('/api/auth/me');
    Auth.setSession(Auth.getToken(), user);
    renderNav(user);
    return user;
  } catch (err) {
    return null;
  }
}

/** 需要管理员权限的页面校验 */
async function requireAdmin() {
  const user = await requireLogin();
  if (!user) return null;
  if (user.role !== 'admin') {
    document.getElementById('pageBody').innerHTML = `
      <div class="card"><div class="empty-state">
        <i class="bi bi-shield-lock"></i>
        <p>无权限访问该页面，仅管理员可操作。</p>
        <a class="btn btn-primary btn-sm" href="/chat">返回客服问答</a>
      </div></div>`;
    return null;
  }
  return user;
}

document.addEventListener('DOMContentLoaded', () => {
  bindLogout();
  if (document.body.dataset.page === 'login' || document.body.dataset.page === 'register') {
    renderNav(null);
    return;
  }
  const cached = Auth.cachedUser();
  if (cached) renderNav(cached);
});
