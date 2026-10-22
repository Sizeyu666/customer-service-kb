---
name: shadcn-admin-ui
description: "企业客服知识库系统的 shadcn 风格后台 UI 设计系统（Jinja2 + Bootstrap 5）。Invoke when building/editing templates/*.html, static/css/style.css, base layout, navbar, login/register, chat, history, knowledge, admin pages, or any Bootstrap component for this project."
---

# shadcn Admin UI（简洁专业 B 端后台）

> 适用：本项目 `app/templates/`（base/login/register/chat/history/knowledge/admin）与 `app/static/css/style.css`、`static/js/`。
> 技术边界：**只用 Bootstrap 5（CDN）+ 原生 CSS + 原生 fetch，禁止 Node/构建链/Sass**，所有定制通过 CSS 变量和少量覆盖类完成。
> 目标：干净、专业、可信赖的企业级后台，蓝/灰白主色，组件克制、留白充足。

## 一、设计基调

- **关键词**：shadcn 式极简、中性灰阶 + 蓝色强调、清晰层级、柔和描边卡片、低噪音
- **禁止**：渐变背景、玻璃拟态、霓虹高饱和、重阴影、圆角过大、花哨动画、深色主题（本系统固定浅色）
- 中文界面，字体 Inter / 系统无衬线

## 二、设计令牌（写进 style.css 的 `:root`）

```css
:root {
  /* 背景与文字 */
  --bg: #FFFFFF;
  --bg-subtle: #FAFAFA;
  --bg-muted: #F4F4F5;
  --fg: #09090B;            /* 主文字 zinc-950 */
  --fg-muted: #71717A;      /* 次要文字 zinc-500 */
  --fg-subtle: #A1A1AA;
  /* 品牌（蓝，满足蓝/灰白要求） */
  --primary: #2563EB;
  --primary-hover: #1D4ED8;
  --primary-fg: #FFFFFF;
  --primary-soft: #EFF6FF;
  --primary-border: #BFDBFE;
  /* 描边与输入 */
  --border: #E4E4E7;
  --border-strong: #D4D4D8;
  --ring: rgba(37, 99, 235, .35);
  /* 语义色 */
  --success: #16A34A; --success-soft: #F0FDF4; --success-border: #BBF7D0;
  --warning: #D97706; --warning-soft: #FFFBEB; --warning-border: #FDE68A;
  --danger:  #DC2626; --danger-soft:  #FEF2F2; --danger-border:  #FECACA;
  /* 圆角与阴影 */
  --radius: 8px;
  --radius-lg: 12px;
  --shadow-sm: 0 1px 2px rgba(16,24,40,.04);
  --shadow: 0 1px 3px rgba(16,24,40,.06), 0 1px 2px rgba(16,24,40,.04);
  --shadow-lg: 0 8px 24px rgba(16,24,40,.10);
  --font-sans: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI",
    "PingFang SC", "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif;
}
```

## 三、Bootstrap 5 覆盖（在 style.css 中，CDN 之后加载）

```css
body {
  font-family: var(--font-sans); color: var(--fg); background: var(--bg-muted);
  font-size: 15px; -webkit-font-smoothing: antialiased;
}
a { color: var(--primary); text-decoration: none; }
a:hover { color: var(--primary-hover); }

/* 主按钮：实心蓝 */
.btn-primary {
  --bs-btn-bg: var(--primary); --bs-btn-border-color: var(--primary);
  --bs-btn-hover-bg: var(--primary-hover); --bs-btn-hover-border-color: var(--primary-hover);
  --bs-btn-active-bg: var(--primary-hover); --bs-btn-active-border-color: var(--primary-hover);
  --bs-btn-disabled-bg: var(--primary); --bs-btn-disabled-border-color: var(--primary);
  border-radius: var(--radius); font-weight: 600; padding: .5rem 1rem;
}
.btn-outline-secondary {
  --bs-btn-color: var(--fg); --bs-btn-border-color: var(--border);
  --bs-btn-hover-bg: var(--bg-muted); --bs-btn-hover-color: var(--fg);
  --bs-btn-hover-border-color: var(--border-strong);
  border-radius: var(--radius); font-weight: 500; background:#fff;
}
.btn-danger { --bs-btn-bg: var(--danger); --bs-btn-border-color: var(--danger);
  border-radius: var(--radius); font-weight: 600; }

/* 卡片：白底细描边 */
.card {
  border: 1px solid var(--border); border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm); background: var(--bg);
}
.card-header { background: var(--bg); border-bottom: 1px solid var(--border);
  font-weight: 600; border-radius: var(--radius-lg) var(--radius-lg) 0 0 !important; }

/* 表单 */
.form-control, .form-select {
  border-color: var(--border); border-radius: var(--radius); padding: .55rem .8rem;
}
.form-control:focus, .form-select:focus {
  border-color: var(--primary); box-shadow: 0 0 0 3px var(--ring);
}
.form-label { font-weight: 500; color: var(--fg); font-size: 14px; }

/* 表格 */
.table { --bs-table-bg: transparent; margin-bottom: 0; }
.table thead th {
  background: var(--bg-subtle); color: var(--fg-muted); font-size: 12px;
  text-transform: uppercase; letter-spacing: .03em; font-weight: 600;
  border-bottom: 1px solid var(--border); white-space: nowrap;
}
.table td { border-bottom: 1px solid var(--border); vertical-align: middle; }
.table-hover tbody tr:hover { background: var(--bg-subtle); }

/* 徽章/状态 */
.badge { font-weight: 600; border-radius: 999px; padding: .35em .7em; font-weight: 500; }
.badge.bg-success { background: var(--success-soft) !important; color: #15803D; }
.badge.bg-warning { background: var(--warning-soft) !important; color: #B45309; }
.badge.bg-danger  { background: var(--danger-soft)  !important; color: #B91C1C; }
.badge.bg-secondary { background: var(--bg-muted) !important; color: var(--fg-muted); }

/* 模态框 */
.modal-content { border: 1px solid var(--border); border-radius: var(--radius-lg); box-shadow: var(--shadow-lg); }
```

## 四、通用组件类（自定义，在 style.css 中实现）

- **顶部导航 `.app-navbar`**：白底、底部 1px `--border`、固定顶部、高 56px；品牌名左侧加粗（可用一个简单 SVG/文字 logo，不要彩色图标）；导航项用 `.nav-link`，当前页高亮（蓝色文字 + 底部 2px 蓝条）；右侧用户名 + 退出下拉。
- **页面容器 `.page-wrap`**：`max-width: 1180px; margin: 0 auto; padding: 24px 20px;`；页面标题区 `.page-head`（左：h1 20px + 浅灰副标题；右：操作按钮）。
- **统计卡 `.stat-card`**：白底卡片，上方灰色 13px 标签，中间 28px 加粗数字，下方小号趋势/说明；`display:grid; grid-template-columns: repeat(4,1fr); gap:16px`，窄屏降为 2 列、手机 1 列。
- **空状态 `.empty-state`**：居中、浅灰图标位（用 Bootstrap Icons 单色）、一句说明、一个主按钮。
- **加载态 `.loading`**：Bootstrap spinner-border（primary）+ 中文「加载中…」，骨架屏可选。
- **Toast**：固定右上角，白底卡片细描边，成功/错误用语义色左边框，统一由 `auth.js` 的 `showToast(msg, type)` 弹出。
- **Bootstrap Icons**：CDN 引入 `bootstrap-icons`，仅用单色线性图标。

## 五、各页面布局

1. **base.html**：引入 Bootstrap 5 + bootstrap-icons + `style.css`（顺序：Bootstrap CSS → icons → style.css）；`.app-navbar` 导航按登录态/角色显隐（`/api/auth/me`）；`{% block content %}`；底部引入 `auth.js` 与各页脚本。
2. **login.html / register.html**：整页居中（`min-height:100vh; display:grid; place-items:center; background: var(--bg-muted)`），一张 400px 宽 `.card`，内：品牌名 + 标题 + 副标题 + 表单 + 主按钮（通栏）+ 底部切换链接；fetch 提交，错误用内联中文红字或 toast；登录成功 token 存 localStorage 跳 `/chat`。
3. **chat.html（客服问答）**：左右两栏卡片化布局：
   - 左栏（约 280px，`.conversation-list`）：「新会话」按钮 + 会话列表（标题、时间、激活态高亮）；窄屏折叠为顶部下拉。
   - 右栏（flex 填充）：顶部当前会话标题；中部 `.chat-scroll` 消息区（用户气泡右靠浅蓝/白底蓝字、客服气泡左靠白底卡片）；底部固定输入区（文本框 + 发送按钮）。
   - 客服回答末尾渲染「参考来源」：胶囊标签（文档名 + 页码），点击可高亮；无结果时显示系统固定话术，不编造。
   - 流式/等待：发送后客服气泡显示三点 typing 动画。
4. **history.html**：会话列表表格或卡片（标题、消息数、时间、操作：查看/删除），分页；空状态引导去提问。
5. **knowledge.html（管理员）**：页头「上传文档」按钮（模态框：拖拽上传 + 类型提示 PDF/Word/MD）；文档表格（文件名、类型徽章、上传时间、文本块数、状态徽章 ready/processing/failed、删除）；上传后轮询状态并 toast 提示。
6. **admin.html（管理员）**：顶部 4 个 `.stat-card`（用户数/文档数/会话数/消息数）；下方用户表格（用户名、角色徽章、注册时间、角色切换下拉、保存）；非管理员 403 页面。

## 六、聊天气泡规范（style.css）

```css
.chat-wrap { display:flex; flex-direction:column; height: calc(100vh - 56px - 48px); }
.chat-scroll { flex:1; overflow-y:auto; padding: 20px; background: var(--bg-muted); }
.msg { display:flex; margin-bottom: 14px; }
.msg.user { justify-content: flex-end; }
.bubble { max-width: 72%; padding: 10px 14px; border-radius: 12px; line-height: 1.7;
  font-size: 15px; white-space: pre-wrap; word-break: break-word; }
.msg.user .bubble { background: var(--primary); color: #fff; border-bottom-right-radius: 4px; }
.msg.assistant .bubble { background: #fff; border: 1px solid var(--border);
  color: var(--fg); border-bottom-left-radius: 4px; box-shadow: var(--shadow-sm); }
.src-chip { display:inline-block; font-size:12px; color:#1D4ED8; background:var(--primary-soft);
  border:1px solid var(--primary-border); border-radius:999px; padding:2px 10px; margin:6px 6px 0 0; }
.chat-input { border-top:1px solid var(--border); background:#fff; padding:12px 16px; }
```

## 七、状态处理（每页都要有）

- 加载中：spinner + 中文文案；空数据：`.empty-state`；失败：toast + 「重试」按钮。
- 未登录：前端检查 token，无则跳 `/login`；`authFetch` 遇 401 清 token 并跳转；403 显示无权限提示。
- 所有接口错误信息以中文呈现，不把堆栈/英文异常直接暴露。

## 八、不要做

- 不引入 Node、webpack、Sass、React/Vue；不使用 shadcn 原版 React 组件（只取其设计语言，用 Bootstrap + CSS 实现）。
- 不做多套主题/深色切换；不用渐变、玻璃拟态、重阴影。
- 不改变后端接口与业务逻辑，只做模板与静态资源。
- 页面宽度统一、卡片对齐；不要每页一套配色。

## 九、交付前 QA 清单

- [ ] 未登录访问受保护页面跳登录；登录态刷新保持；403 有提示
- [ ] 登录/注册为居中卡片，错误中文提示，按钮 loading 防重复提交
- [ ] 顶栏导航按角色显隐，当前页高亮
- [ ] 对话页双栏：新建/切换/删除会话、多轮问答、用户/客服气泡、来源胶囊、typing、窄屏可用
- [ ] 知识库上传模态、状态徽章、ready 块数、删除后来源失效
- [ ] admin 4 个统计卡与用户表格、角色切换生效
- [ ] 表格、表单、模态、toast、徽章在各页风格一致
- [ ] 每页都有加载/空/失败三种状态；移动端不横向溢出
