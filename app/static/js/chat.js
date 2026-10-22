/* =========================================================================
   客服问答页逻辑：会话列表、多轮问答、来源标签、点赞点踩
   ========================================================================= */

const ChatPage = {
  conversations: [],
  activeId: null,
  sending: false,

  async init() {
    const user = await requireLogin();
    if (!user) return;

    this.listEl = document.getElementById('convList');
    this.scrollEl = document.getElementById('chatScroll');
    this.titleEl = document.getElementById('chatTitle');
    this.metaEl = document.getElementById('chatMeta');
    this.countEl = document.getElementById('msgCount');
    this.inputEl = document.getElementById('questionInput');
    this.sendBtn = document.getElementById('sendBtn');

    document.getElementById('newConvBtn').addEventListener('click', () => this.createConversation());
    document.getElementById('refreshBtn').addEventListener('click', () => this.loadConversations());
    this.sendBtn.addEventListener('click', () => this.send());
    this.inputEl.addEventListener('input', () => this.autoSize());
    this.inputEl.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        this.send();
      }
    });
    document.querySelectorAll('.hint-card').forEach((btn) => {
      btn.addEventListener('click', () => {
        this.inputEl.value = btn.textContent.trim();
        this.inputEl.focus();
      });
    });

    await this.loadConversations();

    const target = new URLSearchParams(location.search).get('cid');
    if (target) {
      const found = this.conversations.find((item) => String(item.id) === String(target));
      if (found) await this.selectConversation(found.id);
    }
  },

  autoSize() {
    this.inputEl.style.height = 'auto';
    this.inputEl.style.height = `${Math.min(this.inputEl.scrollHeight, 140)}px`;
  },

  async loadConversations() {
    this.listEl.innerHTML = '<div class="loading"><span class="spinner-border spinner-border-sm text-primary"></span>加载中…</div>';
    try {
      this.conversations = (await authFetch('/api/conversations')) || [];
    } catch (err) {
      this.listEl.innerHTML = `<div class="empty-state"><i class="bi bi-exclamation-circle"></i><p>${escapeHtml(err.message)}</p>
        <button class="btn btn-outline-secondary btn-sm" onclick="ChatPage.loadConversations()">重试</button></div>`;
      return;
    }

    if (!this.conversations.length) {
      this.listEl.innerHTML = '<div class="empty-state" style="padding:28px 12px"><i class="bi bi-inbox"></i><p>还没有会话，点击「新会话」开始提问</p></div>';
      return;
    }
    this.renderConversations();
  },

  renderConversations() {
    this.listEl.innerHTML = this.conversations
      .map((item) => {
        const active = String(item.id) === String(this.activeId) ? 'active' : '';
        return `<div class="conversation-item ${active}" data-id="${item.id}">
          <i class="bi bi-chat-left-text" style="font-size:13px;opacity:.65"></i>
          <span class="title" title="${escapeHtml(item.title)}">${escapeHtml(item.title)}</span>
          <button class="del" type="button" data-del="${item.id}" title="删除会话"><i class="bi bi-x-lg" style="font-size:11px"></i></button>
        </div>`;
      })
      .join('');

    this.listEl.querySelectorAll('.conversation-item').forEach((el) => {
      el.addEventListener('click', (event) => {
        if (event.target.closest('[data-del]')) return;
        this.selectConversation(Number(el.dataset.id));
      });
    });
    this.listEl.querySelectorAll('[data-del]').forEach((btn) => {
      btn.addEventListener('click', (event) => {
        event.stopPropagation();
        this.deleteConversation(Number(btn.dataset.del));
      });
    });
  },

  async createConversation() {
    try {
      const conversation = await authFetch('/api/conversations', { method: 'POST', body: {} });
      this.conversations.unshift(conversation);
      this.activeId = conversation.id;
      this.renderConversations();
      this.resetChatArea(conversation.title);
      this.inputEl.focus();
    } catch (err) {
      showToast(err.message, 'error');
    }
  },

  async selectConversation(id) {
    this.activeId = id;
    this.renderConversations();
    const conversation = this.conversations.find((item) => item.id === id);
    this.titleEl.textContent = conversation ? conversation.title : '客服问答';
    this.metaEl.textContent = '基于企业知识库回答，回答末尾附参考来源';
    this.scrollEl.innerHTML = '<div class="loading"><span class="spinner-border spinner-border-sm text-primary"></span>加载消息…</div>';

    try {
      const messages = (await authFetch(`/api/conversations/${id}/messages`)) || [];
      this.renderMessages(messages);
    } catch (err) {
      this.scrollEl.innerHTML = `<div class="empty-state"><i class="bi bi-exclamation-circle"></i><p>${escapeHtml(err.message)}</p>
        <button class="btn btn-outline-secondary btn-sm" onclick="ChatPage.selectConversation(${id})">重试</button></div>`;
    }
  },

  resetChatArea(title) {
    this.titleEl.textContent = title || '客服问答';
    this.countEl.textContent = '0 条消息';
    this.scrollEl.innerHTML = `<div class="chat-empty">
      <i class="bi bi-chat-square-text" style="font-size:30px;color:var(--fg-subtle)"></i>
      <div style="font-size:13.5px;color:var(--fg-muted)">会话已创建，输入问题开始咨询</div>
    </div>`;
  },

  renderMessages(messages) {
    if (!messages.length) {
      this.resetChatArea(this.titleEl.textContent);
      return;
    }
    this.scrollEl.innerHTML = '';
    messages.forEach((message) => this.appendMessage(message));
    this.countEl.textContent = `${messages.length} 条消息`;
    this.scrollToBottom();
  },

  /** 去掉后端附加的「参考来源」文本，避免与来源标签重复展示 */
  stripSourceText(content, sources) {
    if (!sources || !sources.length) return content;
    return content.replace(/\n*参考来源：[\s\S]*$/, '').trim();
  },

  appendMessage(message) {
    const wrapper = document.createElement('div');
    const isUser = message.role === 'user';
    wrapper.className = `msg ${isUser ? 'user' : 'assistant'}`;
    wrapper.dataset.id = message.id;

    const content = isUser ? message.content : this.stripSourceText(message.content, message.sources);
    const sourceHtml = (!isUser && message.sources && message.sources.length)
      ? `<div class="msg-meta">参考来源</div>${message.sources
          .map((name) => `<span class="src-chip"><i class="bi bi-file-earmark-text me-1"></i>${escapeHtml(name)}</span>`)
          .join('')}`
      : '';

    const actionHtml = isUser
      ? `<div class="msg-meta">${formatTime(message.created_at)}</div>`
      : `<div class="msg-meta">
           ${formatTime(message.created_at)}
           <span class="ms-2">
             <button class="fb-btn ${message.feedback === 'up' ? 'active' : ''}" data-fb="up" data-msg="${message.id}"><i class="bi bi-hand-thumbs-up"></i> 有帮助</button>
             <button class="fb-btn ${message.feedback === 'down' ? 'active' : ''}" data-fb="down" data-msg="${message.id}"><i class="bi bi-hand-thumbs-down"></i> 没帮助</button>
           </span>
         </div>`;

    wrapper.innerHTML = `<div><div class="bubble">${escapeHtml(content)}</div>${sourceHtml}${actionHtml}</div>`;
    this.scrollEl.appendChild(wrapper);

    wrapper.querySelectorAll('[data-fb]').forEach((btn) => {
      btn.addEventListener('click', () => this.sendFeedback(Number(btn.dataset.msg), btn.dataset.fb, btn));
    });
  },

  appendTyping() {
    const wrapper = document.createElement('div');
    wrapper.className = 'msg assistant';
    wrapper.id = 'typingMsg';
    wrapper.innerHTML = `<div><div class="bubble"><span class="typing"><span></span><span></span><span></span></span></div></div>`;
    this.scrollEl.appendChild(wrapper);
    this.scrollToBottom();
  },

  removeTyping() {
    const el = document.getElementById('typingMsg');
    if (el) el.remove();
  },

  scrollToBottom() {
    this.scrollEl.scrollTop = this.scrollEl.scrollHeight;
  },

  async send() {
    if (this.sending) return;
    const question = this.inputEl.value.trim();
    if (!question) {
      showToast('请输入问题内容', 'warning');
      return;
    }

    this.sending = true;
    this.sendBtn.disabled = true;
    this.sendBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>回答中';

    try {
      if (!this.activeId) {
        const conversation = await authFetch('/api/conversations', { method: 'POST', body: {} });
        this.conversations.unshift(conversation);
        this.activeId = conversation.id;
        this.renderConversations();
        this.scrollEl.innerHTML = '';
      }

      const emptyEl = document.getElementById('chatEmpty');
      if (emptyEl) emptyEl.remove();

      // 乐观渲染用户消息
      this.appendMessage({
        id: `temp-${Date.now()}`,
        role: 'user',
        content: question,
        sources: [],
        created_at: new Date().toISOString(),
      });
      this.inputEl.value = '';
      this.autoSize();
      this.appendTyping();

      const data = await authFetch(`/api/conversations/${this.activeId}/chat`, {
        method: 'POST',
        body: { question },
      });

      this.removeTyping();
      this.appendMessage({
        id: data.message_id,
        role: 'assistant',
        content: data.answer,
        sources: data.sources || [],
        created_at: new Date().toISOString(),
      });

      // 同步标题与消息数
      const conversation = this.conversations.find((item) => item.id === this.activeId);
      if (conversation) {
        conversation.title = data.title;
        conversation.message_count = (conversation.message_count || 0) + 2;
        this.titleEl.textContent = data.title;
        this.renderConversations();
      }
      const bubbles = this.scrollEl.querySelectorAll('.msg').length;
      this.countEl.textContent = `${bubbles} 条消息`;
      this.scrollToBottom();
    } catch (err) {
      this.removeTyping();
      showToast(err.message, 'error');
      this.appendMessage({
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: `回答失败：${err.message}`,
        sources: [],
        created_at: new Date().toISOString(),
      });
    } finally {
      this.sending = false;
      this.sendBtn.disabled = false;
      this.sendBtn.textContent = '发送';
      this.inputEl.focus();
    }
  },

  async sendFeedback(messageId, rating, btn) {
    try {
      await authFetch(`/api/messages/${messageId}/feedback`, { method: 'POST', body: { rating } });
      const group = btn.parentElement.querySelectorAll('[data-fb]');
      group.forEach((item) => item.classList.remove('active'));
      btn.classList.add('active');
      showToast('感谢您的反馈', 'success');
    } catch (err) {
      showToast(err.message, 'error');
    }
  },

  async deleteConversation(id) {
    if (!window.confirm('确定删除该会话吗？删除后消息无法恢复。')) return;
    try {
      await authFetch(`/api/conversations/${id}`, { method: 'DELETE' });
      this.conversations = this.conversations.filter((item) => item.id !== id);
      if (this.activeId === id) {
        this.activeId = null;
        this.titleEl.textContent = '客服问答';
        this.countEl.textContent = '0 条消息';
        this.resetChatArea('客服问答');
      }
      this.renderConversations();
      if (!this.conversations.length) {
        this.listEl.innerHTML = '<div class="empty-state" style="padding:28px 12px"><i class="bi bi-inbox"></i><p>还没有会话，点击「新会话」开始提问</p></div>';
      }
      showToast('会话已删除', 'success');
    } catch (err) {
      showToast(err.message, 'error');
    }
  },
};

document.addEventListener('DOMContentLoaded', () => ChatPage.init());
