// logs-page.js - 日志查询页面逻辑（中文注释）
(function () {
  'use strict';

  function fmt(ts) { try { return new Date(ts).toLocaleString(); } catch (_) { return ts; } }

  // 将可能包含 \uXXXX 转义序列的字符串解码为可阅读文本（中文注释）
  // - 如果字符串本身是 JSON 字符串字面量（形如 "..."），直接 JSON.parse 还原
  // - 否则将其包裹为 JSON 字符串后再 JSON.parse，实现对 \n/\t/\uXXXX 等转义的统一解码
  // - 失败时原样返回，保证健壮性
  function decodeUnicode(s) {
    if (typeof s !== 'string') return s;
    try {
      const trimmed = s.trim();
      // 情况1：本身是合法的 JSON 字符串字面量
      if (trimmed.startsWith('"') && trimmed.endsWith('"')) {
        const once = JSON.parse(trimmed);
        if (typeof once === 'string' && /\\u[0-9a-fA-F]{4}/.test(once)) {
          // 若仍含有 \uXXXX，再尝试二次解码
          const wrapped2 = '"' + once.replace(/"/g, '\\"') + '"';
          return JSON.parse(wrapped2);
        }
        return once;
      }
      // 情况2：普通字符串，包裹为 JSON 字符串，仅转义双引号，不转义反斜杠，便于 \uXXXX 被解析
      const wrapped = '"' + s.replace(/"/g, '\\"') + '"';
      const once = JSON.parse(wrapped);
      if (typeof once === 'string' && /\\u[0-9a-fA-F]{4}/.test(once)) {
        const wrapped2 = '"' + once.replace(/"/g, '\\"') + '"';
        return JSON.parse(wrapped2);
      }
      return once;
    } catch (_) {
      return s;
    }
  }

  // 尝试把字符串解析为对象（最多两次），用于还原嵌套 JSON 字符串（中文注释）
  function parseJsonDeep(s) {
    if (typeof s !== 'string') return null;
    const looksJson = (x) => typeof x === 'string' && /^(\{|\[)/.test(x.trim());
    try {
      let cur = s;
      if (looksJson(cur)) cur = JSON.parse(cur);
      if (typeof cur === 'string' && looksJson(cur)) cur = JSON.parse(cur);
      return (cur && typeof cur === 'object') ? cur : null;
    } catch (_) { return null; }
  }

  // 将复杂日志内容口语化显示（中文注释）
  function humanizeMsg(raw) {
    const dec = decodeUnicode(raw);
    const obj = parseJsonDeep(dec);
    const round = (n) => (typeof n === 'number' ? Math.round(n * 100) / 100 : n);
    const preview = (txt, n = 160) => String(txt ?? '').replace(/\s+/g, ' ').slice(0, n);

    if (!obj) return dec; // 非 JSON，直接返回解码文本

    const event = obj.event || obj?.extra?.event || '';
    const ext = obj?.extra?.extra || obj?.extra || {};

    const map = {
      'api.request.start': () => `收到 ${ext.method || ''} ${ext.path || ext.url || ''} 请求，来自 ${ext.client_ip || ext.remote_addr || ''}`,
      'api.request.success': () => `请求完成，状态 ${ext.status_code}，用时 ${round(ext.duration_ms)}ms，返回 ${ext.content_type || ''}，长度 ${ext.content_length || ''}`,
      'pool.initialized': () => `连接池初始化完成，最小连接 ${obj.min_size}，最大连接 ${obj.max_size}`,
      'db.init.success': () => `数据库连接池初始化成功（${obj.host || ''}/${obj.database || ''}）`,
      'api.sql.executed': () => `执行 SQL，用时 ${round(ext.duration_ms)}ms${ext.affected_rows != null ? `，影响行数 ${ext.affected_rows}` : ''}\nSQL 预览：${preview(ext.sql)}`,
      'task.begin': () => `任务开始：${preview(obj.message || '')}`,
      // 中文事件名（兼容 startup/health 日志）
      '健康检查完成': () => `健康检查完成：连接池已${obj.db_initialized ? '初始化' : '未初始化'}`,
      '应用初始化完成': () => `应用初始化完成（${preview(JSON.stringify(obj))}）`,
      '日志系统初始化完成': () => `日志系统初始化完成`,
      '数据库连接池初始化完成': () => `数据库连接池初始化完成`,
    };

    if (map[event]) return map[event]();

    // 若没有匹配的事件，尝试 message 字段
    if (obj.message) return decodeUnicode(String(obj.message));

    // 兜底：返回压缩后的对象字符串
    try { return JSON.stringify(obj); } catch (_) { return dec; }
  }

  function bindEvents() {
    const form = document.getElementById('log-query-form');
    form?.addEventListener('submit', async (e) => {
      e.preventDefault();
      await runQuery();
    });
  }
  // 设置默认时间范围：开始 2025-01-01 00:00，结束 2025-09-09 23:59（中文注释）
  function setDefaultRange() {
    const toLocal = (d) => {
      const pad = (n) => String(n).padStart(2, '0');
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    };
    const st = new Date('2025-01-01T00:00:00');
    const et = new Date('2025-09-09T23:59:00');
    const stEl = document.getElementById('start-time');
    const etEl = document.getElementById('end-time');
    if (stEl) stEl.value = toLocal(st);
    if (etEl) etEl.value = toLocal(et);
  }


  async function runQuery() {
    const start = document.getElementById('start-time').value;
    const end = document.getElementById('end-time').value;
    const levels = Array.from(document.querySelectorAll('input[name="level"]:checked')).map(i => i.value);
    const fmtSel = document.querySelector('input[name="fmt"]:checked')?.value || 'json';
    const keyword = document.getElementById('keyword').value || '';

    if (!start || !end) { alert('请选择时间范围'); return; }

    const params = { start_time: new Date(start).toISOString(), end_time: new Date(end).toISOString() };
    if (levels.length) params.levels = levels.join(',');
    if (keyword) params.keyword = keyword;
    if (fmtSel) params.format = fmtSel;

    const data = await API.searchLogs(params);
    renderList(data);
  }

  function renderList(data) {
    const cont = document.getElementById('log-list');
    if (!cont) return;

    // 可选：按 request_id 分组串联
    const groupEnabled = document.getElementById('group-by-request')?.checked;

    // 支持后端 LogsResponse 结构 { logs, total_count, ... }
    const list = Array.isArray(data) ? data : (Array.isArray(data?.logs) ? data.logs : []);
    if (list.length) {
      if (groupEnabled) {
        const groups = {};
        for (const it of list) {
          const rid = it.request_id || '无-request-id';
          (groups[rid] ||= []).push(it);
        }
        const html = Object.entries(groups).map(([rid, items]) => {
          items.sort((a, b) => String(a.timestamp || '').localeCompare(String(b.timestamp || '')));
          const head = `<div class=\"fw-bold mb-1\">请求 ${rid}</div>`;
          const body = items.map(renderItem).join('');
          return `<div class=\"mb-3 p-2 border rounded\">${head}${body}</div>`;
        }).join('');
        cont.innerHTML = html;
      } else {
        cont.innerHTML = list.map(item => renderItem(item)).join('');
      }
      return;
    }

    if (typeof data === 'string') {
      cont.textContent = decodeUnicode(data);
    } else {
      try {
        cont.textContent = JSON.stringify(data, null, 2);
      } catch (_) {
        cont.textContent = String(data);
      }
    }
  }

  function levelText(level) {
    const m = (level || '').toString().toUpperCase();
    return {
      'CRITICAL': '严重错误', 'ERROR': '错误', 'WARN': '警告', 'WARNING': '警告', 'INFO': '提示', 'DEBUG': '调试信息'
    }[m] || m || '日志';
  }

  function renderItem(item) {
    const level = (item.level || item.levelname || 'INFO').toUpperCase();
    const ts = item.timestamp || item.time || item.ts || '';
    const msg = item.message || item.msg || '';

    const icon = { 'CRITICAL': '🚨', 'ERROR': '❌', 'WARN': '⚠️', 'WARNING': '⚠️', 'INFO': 'ℹ️', 'DEBUG': '🐞' }[level] || '📄';
    const color = {
      'CRITICAL': 'text-danger fw-bold', 'ERROR': 'text-danger', 'WARN': 'text-warning', 'WARNING': 'text-warning', 'INFO': 'text-primary', 'DEBUG': 'text-muted'
    }[level] || 'text-body';

    const raw = typeof msg === 'string' ? msg : JSON.stringify(msg);
    const human = humanizeMsg(raw); // 先解码再口语化
    return `
      <div class="border-bottom py-2">
        <div class="${color}">${icon} ${levelText(level)} · ${fmt(ts)}</div>
        <div class="text-body">${escapeHtml(human)}</div>
      </div>
    `;
  }


  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" })[c]);
  }

  document.addEventListener('DOMContentLoaded', () => {
    setDefaultRange();
    bindEvents();
  });
})();
