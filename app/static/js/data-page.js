// data-page.js - 数据展示页面逻辑（中文注释，原始值 + wide/long + 指标多选 + Tabulator 表格 + 导出）
(function () {
  'use strict';

  // 全局状态（前端局部缓存）
  let metricsCatalog = [];      // 指标清单（来自 /api/v1/data/metrics）
  let metricsUnitMap = {};      // metric_key -> unit 映射
  let normalizedRows = [];      // 归一化后的 long 形态数据 [{ts, metric, value, device_name?}]

  // 渲染控制相关的全局状态（用于表格 wide/long 切换）
  let currentFormat = 'wide';           // 当前返回格式（wide|long）
  let currentWideRows = [];             // 原始 wide 数据（仅在 format=wide 时保存，用于横向表格）
  let currentSelectedMetrics = [];      // 当前选中的指标（用于列构建）
  let currentDeviceName = '';           // 当前设备名称（若选择了具体设备）

  // 图表实例缓存与自适应
  let chartInstance = null;
  let chartResizeBound = false;
  // 新表格实例（Tabulator）
  // 工具：获取/创建 Tabulator 容器
  // ResizeObserver（容器尺寸变化监听）
  let chartRO = null; // 观察图表容器
  let tableRO = null; // 观察表格容器

  // 安全暴露给 window，供视图切换按钮调用
  function exposeGlobals() {
    if (chartInstance) window.chartInstance = chartInstance;
    if (tableInst) window.tableInst = tableInst;
  }

  function ensureChartObserver() {
    try {
      if (typeof ResizeObserver === 'undefined') return;
      if (!chartRO) {
        chartRO = new ResizeObserver(() => { if (chartInstance) { chartInstance.resize(); } });
        const targets = [
          document.getElementById('chart'),
          document.getElementById('chart-view'),
          document.querySelector('main.container-narrow')
        ].filter(Boolean);
        targets.forEach(t => chartRO.observe(t));
      }
    } catch (e) { console.warn('ensureChartObserver error', e); }
  }

  // 表格构建完成标志，避免初始化前 redraw 警告（中文注释）
  let tableReady = false;

  function ensureTableObserver() {
    try {
      if (typeof ResizeObserver === 'undefined') return;
      if (!tableRO) {
        tableRO = new ResizeObserver(() => {
          if (tableReady && tableInst) {
            try { tableInst.redraw(true); } catch (_) { }
          }
        });
        const el = document.getElementById('grid-table');
        if (el) tableRO.observe(el);
        // 额外监听多个父级容器，增强布局变化感知
        const extraTargets = [
          document.querySelector('#table-view .table-wrapper'),
          document.getElementById('table-view'),
          document.querySelector('main.container-narrow')
        ].filter(Boolean);
        extraTargets.forEach(t => tableRO.observe(t));

        // 根据可视空间动态更新表格高度
        function updateTableHeight() {
          if (!tableInst) return;
          try {
            const container = document.getElementById('grid-table');
            const h = computeTableHeight(container);
            tableInst.setHeight(h);
          } catch (e) { console.warn('updateTableHeight error', e); }
        }

      }
    } catch (e) { console.warn('ensureTableObserver error', e); }
  }

  let tableInst = null;

  function getGridContainer() {
    let el = document.getElementById('grid-table');
    if (!el) {
      const holder = document.querySelector('#table-view .table-wrapper') || document.getElementById('table-view') || document.body;
      el = document.createElement('div');
      el.id = 'grid-table';
      holder.appendChild(el);
    }
    return el;
  }

  // 工具：格式化时间（本地时区显示）
  function fmtTs(ts) {
    try { return new Date(ts).toLocaleString(); } catch (_) { return ts; }
  }

  // 表头菜单：列显示/隐藏（Tabulator 列菜单）
  function buildHeaderMenu() {
    return [
      { label: '隐藏此列', action: (_e, col) => col.hide() },
      { label: '显示全部列', action: (_e, col) => { const t = col.getTable(); t.getColumns().forEach(c => c.show()); } }
    ];
  }

  // 工具：采样（超过 20000 点时，步进抽样至 ~5000 点）
  function sampleEveryN(arr, target = 5000) {
    const n = arr.length;
    if (n <= 20000) return arr;
    const step = Math.ceil(n / target);
    const out = [];
    for (let i = 0; i < n; i += step) { out.push(arr[i]); }
    return out;
  }

  // 工具：将 wide 记录扁平化为 long 记录
  function flattenWide(wideRows, whitelist) {
    const out = [];
    for (const r of wideRows) {
      const ts = r.record_timestamp || r.timestamp || r.ts;
      const bag = r.metrics_data || {}; // {metric_key: value}
      for (const [k, v] of Object.entries(bag)) {
        if (whitelist && whitelist.length && !whitelist.includes(k)) continue;
        out.push({ ts, metric: k, value: v });
      }
    }
    return out;
  }

  // UI 绑定
  function bindEvents() {
    const form = document.getElementById('query-form');
    if (form) {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        await runQuery();
      });
    }
    document.querySelectorAll('[data-quick-range]')?.forEach(btn => {
      btn.addEventListener('click', () => applyQuickRange(btn.getAttribute('data-quick-range')));
    });

    // 导出按钮（长数据导出）
    document.getElementById('btn-export-csv')?.addEventListener('click', () => exportData('csv'));
    document.getElementById('btn-export-json')?.addEventListener('click', () => exportData('json'));

    // 新表格：搜索与导出（Tabulator）
    document.getElementById('table-search')?.addEventListener('input', (e) => {
      const q = (e.target.value || '').trim();
      if (tableInst) {
        if (!q) { tableInst.clearFilter(); }
        else {
          tableInst.setFilter((data) => {
            try { return JSON.stringify(data).toLowerCase().includes(q.toLowerCase()); } catch (_) { return false; }
          });
        }
      }
    });
    document.getElementById('btn-table-export-csv')?.addEventListener('click', () => {
      if (tableInst) { tableInst.download('csv', `table_${tsNow()}.csv`, { bom: true }); }
    });

    // 级联：泵站->设备
    const stationSelect = document.getElementById('station-select');
    const deviceSelect = document.getElementById('device-select');
    stationSelect?.addEventListener('change', async () => {
      await populateDevices(stationSelect.value, deviceSelect);
    });
  }

  async function populateStations() {
    const stationSelect = document.getElementById('station-select');
    if (!stationSelect) return;
    const stations = await API.getStations();
    stationSelect.innerHTML = '<option value="">选择泵站</option>';
    stations.forEach(s => {
      const opt = document.createElement('option');
      opt.value = s.id || s.station_id || s.stationId;
      opt.textContent = s.name || s.station_name || `站点${opt.value}`;
      stationSelect.appendChild(opt);
    });
  }

  async function populateDevices(stationId, deviceSelect) {
    if (!deviceSelect) return;
    if (!stationId) { deviceSelect.innerHTML = '<option value="">先选择泵站</option>'; return; }
    const list = await API.getDevicesByStation(stationId);
    deviceSelect.innerHTML = '<option value="">全部设备</option>';
    list.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d.id || d.device_id || d.deviceId;
      opt.textContent = d.name || d.device_name || `设备${opt.value}`;
      deviceSelect.appendChild(opt);
    });
  }

  async function populateMetrics() {
    // 从固定清单加载指标
    try {
      metricsCatalog = await API.getMetrics();
      metricsUnitMap = {};
      const metricSelect = document.getElementById('metric-select');
      metricSelect.innerHTML = '';
      metricsCatalog.forEach(m => {
        metricsUnitMap[m.metric_key] = m.unit || '';
        const opt = document.createElement('option');
        opt.value = m.metric_key;
        opt.textContent = m.metric_key + (m.unit ? ` (${m.unit})` : '');
        metricSelect.appendChild(opt);
      });
    } catch (err) {
      console.warn('加载指标清单失败:', err);
    }
  }
  // 固定默认时间范围（用户要求）
  function setDefaultRange() {
    const st = new Date('2025-01-01T01:01:00');
    const et = new Date('2025-05-01T01:01:00');
    const toLocal = (d) => {
      const pad = (n) => String(n).padStart(2, '0');
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    };
    const stEl = document.getElementById('start-time');
    const etEl = document.getElementById('end-time');
    if (stEl && etEl) { stEl.value = toLocal(st); etEl.value = toLocal(et); }
  }

  // 计算表格目标高度：基于视口高度与容器距顶部的可用空间，区间 260~900
  function computeTableHeight(container) {
    const vh = window.innerHeight || document.documentElement.clientHeight || 800;
    let top = 0;
    try { top = (container || document.getElementById('grid-table'))?.getBoundingClientRect()?.top || 0; } catch (_) { top = 0; }
    const padding = 24; // 底部留白
    const raw = vh - top - padding;
    return Math.round(Math.max(260, Math.min(raw, 900)));
  }

  // 自适应布局：根据窗口尺寸动态调整容器宽度、表单布局与图表高度
  function applyResponsiveLayout() {
    try {
      const w = window.innerWidth || document.documentElement.clientWidth;
      const h = window.innerHeight || document.documentElement.clientHeight;
      const main = document.querySelector('main.container-narrow');
      if (main) {
        let maxW = '95vw';
        if (w >= 1920) maxW = '90vw';
        else if (w >= 1200) maxW = '95vw';
        else if (w >= 768) maxW = '98vw';
        else maxW = '100vw';
        main.style.maxWidth = maxW;
        main.style.width = '100%';
      }
      // 小屏表单单列
      const cols = document.querySelectorAll('#query-form .row > div');
      cols.forEach(d => {
        if (w <= 767) d.classList.add('col-12'); else d.classList.remove('col-12');
      });
      // 图表高度 40-60%（取 55%），最小 260 最大 700
      const chartEl = document.getElementById('chart');
      if (chartEl) {
        const target = Math.round(Math.max(260, Math.min(h * 0.55, 700)));
        chartEl.style.height = target + 'px';
        if (chartInstance) chartInstance.resize();
      }
    } catch (e) { console.warn('applyResponsiveLayout 出错', e); }
  }

  function applyQuickRange(type) {
    const end = new Date();

    let start = new Date(end);
    const map = { '1h': 1 / 24, '6h': 6 / 24, '24h': 1, '7d': 7 };
    const days = map[type] ?? 1;
    start.setTime(end.getTime() - days * 24 * 3600 * 1000);
    const toLocal = (d) => {
      const pad = (n) => String(n).padStart(2, '0');
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    };
    document.getElementById('start-time').value = toLocal(start);
    document.getElementById('end-time').value = toLocal(end);
  }

  async function runQuery() {
    const stationId = document.getElementById('station-select').value;
    const deviceSel = document.getElementById('device-select');
    const deviceId = deviceSel.value;
    const deviceName = deviceId ? (deviceSel.selectedOptions?.[0]?.textContent || '') : '';
    const start = document.getElementById('start-time').value;
    const end = document.getElementById('end-time').value;
    const limit = Math.min(Math.max(parseInt(document.getElementById('limit').value || '1000', 10) || 1000, 1), 100000);
    const format = document.querySelector('input[name=\"fmt\"]:checked')?.value || 'wide';

    if (!stationId) { alert('请选择泵站'); return; }
    if (!start || !end) { alert('请选择时间范围'); return; }

    // 指标选择（多选）
    const metricSelect = document.getElementById('metric-select');
    const selectedMetrics = Array.from(metricSelect.selectedOptions || []).map(o => o.value);

    // 暂存全局状态（用于表格渲染分支）
    currentFormat = format;
    currentSelectedMetrics = selectedMetrics;
    currentDeviceName = deviceName;

    // 查询按钮加载态
    const btn = document.querySelector('#query-form button[type="submit"]');
    const btnText = btn ? btn.textContent : '';
    if (btn) { btn.disabled = true; btn.textContent = '查询中…'; }

    try {
      // 请求数据（原始值）
      const params = { start_time: new Date(start).toISOString(), end_time: new Date(end).toISOString(), limit, format };
      let resp = null;
      if (deviceId) {
        resp = await API.getDeviceRaw(deviceId, params);
      } else {
        resp = await API.getStationRaw(stationId, params);
      }

      const rows = Array.isArray(resp?.data) ? resp.data : [];

      // 图表统一使用 long 形态
      let longRows = [];
      if ((format || 'wide') === 'wide') {
        // wide：表格横排，图表需要扁平化后的 long
        currentWideRows = rows;
        longRows = flattenWide(rows, selectedMetrics);
      } else {
        // long：表格竖排，图表直用 long
        currentWideRows = [];
        longRows = rows.map(r => ({ ts: r.ts || r.record_timestamp || r.timestamp, metric: r.metric, value: r.value }));
        if (selectedMetrics && selectedMetrics.length) {
          longRows = longRows.filter(r => selectedMetrics.includes(r.metric));
        }
      }

      // 数据采样（仅用于图表，表格仍可分页完整展示）
      normalizedRows = longRows.map(r => ({ ...r, device_name: deviceName }));

      // 渲染表格（根据返回格式选择渲染方式）
      if ((format || 'wide') === 'wide') {
        renderTableWide(currentWideRows, selectedMetrics, deviceName);
      } else {
        renderTableLong(normalizedRows);
      }

      // 渲染图表（统一 long）
      renderChart(normalizedRows);

      // 更新序列信息与采样提示
      const info = document.getElementById('series-info');
      if (info) {
        const total = normalizedRows.length;
        const uniqMetrics = new Set(normalizedRows.map(r => r.metric)).size;
        const sampled = total > 20000 ? '（图表采样已启用）' : '';
        info.textContent = `点数：${total}，序列：${uniqMetrics}${sampled}`;
      }
    } catch (err) {
      console.error('查询失败', err);
      alert('查询失败：' + (err?.message || err));
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = btnText; }
    }
  }

  function renderTable(rows) {
    // 使用 Tabulator 渲染 long 竖排表格（完全移除 DataTables 回退）
    const columns = [
      { title: '时间戳', field: 'ts', width: 180, frozen: true, headerHozAlign: 'center', hozAlign: 'left', formatter: (cell) => fmtTs(cell.getValue()), headerMenu: buildHeaderMenu },
      { title: '设备', field: 'device_name', width: 140, headerMenu: buildHeaderMenu },
      { title: '指标', field: 'metric', width: 220, headerMenu: buildHeaderMenu },
      { title: '数值', field: 'value', hozAlign: 'right', headerMenu: buildHeaderMenu },
      { title: '单位', field: 'unit', width: 100, headerMenu: buildHeaderMenu }
    ];

    const data = rows.map(r => ({
      ts: r.ts,
      device_name: r.device_name || '',
      metric: r.metric,
      value: r.value ?? '—',
      unit: metricsUnitMap[r.metric] || ''
    }));

    // 若已有旧表格，先销毁，避免残留配置影响新实例
    if (tableInst) { try { tableInst.destroy(); } catch (_) { } tableInst = null; }
    const container = getGridContainer();
    // eslint-disable-next-line no-undef
    tableInst = new Tabulator(container, {
      data,
      columns,
      layout: 'fitDataStretch',
      movableColumns: true,
      height: computeTableHeight(container),
      pagination: true,
      paginationSize: 50,
      responsiveLayout: 'collapse',
      columnDefaults: { minWidth: 120, headerHozAlign: 'center' },
      locale: true,
      langs: { 'zh-cn': { pagination: { page_size: '每页', first: '首页', last: '尾页' } } },
      index: 'ts'
    });
    tableReady = false;
    tableInst.on('tableBuilt', () => { tableReady = true; try { tableInst.redraw(true); } catch (_) { } });
    exposeGlobals();
    ensureTableObserver();
  }

  // 表格渲染：long 竖排（时间戳 | 设备 | 指标 | 数值 | 单位）
  function renderTableLong(rows) {
    renderTable(rows);
  }

  // 表格渲染：wide 横排（时间戳 | 设备? | 指标列横向展开）
  function renderTableWide(wideRows, selectedMetrics, deviceName) {
    // 使用 Tabulator 渲染 wide 横排表格
    const includeDevice = !!deviceName;
    const metrics = (selectedMetrics && selectedMetrics.length)
      ? selectedMetrics
      : Array.from(new Set(wideRows.flatMap(r => Object.keys(r.metrics_data || {}))));

    // 1) 生成列定义
    const columns = [];
    columns.push({ title: '时间戳', field: '__ts', width: 180, frozen: true, headerHozAlign: 'center', formatter: (cell) => fmtTs(cell.getValue()) });
    if (includeDevice) columns.push({ title: '设备', field: '__device', width: 140, headerHozAlign: 'center' });
    for (const m of metrics) {
      const unit = metricsUnitMap[m] || '';
      columns.push({ title: unit ? `${m}(${unit})` : m, field: m, hozAlign: 'right' });
    }

    // 2) 组装数据行
    const data = wideRows.map(r => {
      const row = { __ts: r.record_timestamp || r.ts || r.timestamp };
      if (includeDevice) row.__device = deviceName;
      for (const m of metrics) {
        row[m] = (r.metrics_data ? r.metrics_data[m] : undefined) ?? null;
      }
      return row;
    });

    // 3) 使用 Tabulator 渲染（已移除 DataTables 回退）
    // 若已有旧表格，先销毁
    if (tableInst) { try { tableInst.destroy(); } catch (_) { } tableInst = null; }
    const container = getGridContainer();
    // eslint-disable-next-line no-undef
    tableReady = false;
    tableInst = new Tabulator(container, {
      data,
      columns,
      layout: 'fitDataStretch',
      movableColumns: true,
      height: computeTableHeight(container),
      pagination: true,
      paginationSize: 50,
      rowHeight: 28,
      // 取消宽表的折叠以保持横向滚动为主
      // responsiveLayout: 'collapse',
      columnDefaults: { minWidth: 120, headerHozAlign: 'center' },
      locale: true,
      langs: { 'zh-cn': { pagination: { page_size: '每页', first: '首页', last: '尾页' } } },
      index: '__ts'
    });
    tableInst.on('tableBuilt', () => { tableReady = true; try { tableInst.redraw(true); } catch (_) { } });
    exposeGlobals();
    ensureTableObserver();
  }


  function renderChart(rows) {
    const el = document.getElementById('chart');
    if (!el || !window.echarts) return;

    // 缓存与复用图表实例，避免重复绑定与内存泄露
    if (!chartInstance) {
      chartInstance = window.echarts.init(el);
      if (!chartResizeBound) {
        chartResizeBound = true;
        window.addEventListener('resize', () => chartInstance && chartInstance.resize());
      }
      exposeGlobals();
      ensureChartObserver();
    }

    if (!rows || rows.length === 0) {
      chartInstance.setOption({
        title: { text: '无数据', left: 'center', top: 'middle', textStyle: { color: '#6c757d', fontSize: 14 } },
        xAxis: { type: 'time' },
        yAxis: { type: 'value' },
        series: []
      });
      return;
    }

    // 依据单位进行分组，自动选择最多的两类单位映射到左右Y轴
    const unitBuckets = new Map(); // unit -> { metricKey -> [[ts,value], ...] }
    const unitCounts = new Map();  // unit -> 点数统计
    for (const r of rows) {
      const u = metricsUnitMap[r.metric] || '';
      if (!unitBuckets.has(u)) unitBuckets.set(u, new Map());
      const m = unitBuckets.get(u);
      if (!m.has(r.metric)) m.set(r.metric, []);
      m.get(r.metric).push([r.ts, r.value]);
      unitCounts.set(u, (unitCounts.get(u) || 0) + 1);
    }
    // 选出点数最多的两种单位
    const sortedUnits = Array.from(unitCounts.entries()).sort((a, b) => b[1] - a[1]).map(([u]) => u);
    const keptUnits = sortedUnits.slice(0, 2);
    // 若不足两类，只有一类则只用一个轴
    const unitAxisIndex = new Map();
    keptUnits.forEach((u, idx) => unitAxisIndex.set(u, idx));

    // 构建 series
    const series = [];
    for (const [u, metricMap] of unitBuckets.entries()) {
      const axisIndex = unitAxisIndex.has(u) ? unitAxisIndex.get(u) : 0; // 未入选的单位也映射到0，以免丢失
      for (const [metricKey, arr] of metricMap.entries()) {
        const data = sampleEveryN(arr);
        series.push({ name: metricKey + (u ? ` (${u})` : ''), type: 'line', showSymbol: false, data, yAxisIndex: axisIndex });
      }
    }

    // 构建 yAxis 配置（最多两个）
    const yAxes = keptUnits.length <= 1 ? [
      { type: 'value', name: keptUnits[0] || '', axisLabel: { formatter: '{value}' } }
    ] : [
      { type: 'value', name: keptUnits[0] || '', axisLabel: { formatter: '{value}' } },
      { type: 'value', name: keptUnits[1] || '', axisLabel: { formatter: '{value}' }, position: 'right' }
    ];

    chartInstance.setOption({
      tooltip: { trigger: 'axis' },
      legend: { type: 'scroll' },
      xAxis: { type: 'time' },
      yAxis: yAxes,
      dataZoom: [{ type: 'inside' }, { type: 'slider' }],
      series
    });
  }

  function exportData(kind) {
    // 导出当前过滤结果（不局限 DataTables 当前页）
    const rows = normalizedRows;
    if (kind === 'json') {
      const blob = new Blob([JSON.stringify(rows, null, 2)], { type: 'application/json;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      download(url, `data_${tsNow()}.json`);
    } else {
      // CSV: ts,metric,value
      const header = 'ts,metric,value\n';
      const lines = rows.map(r => `${escapeCsv(r.ts)},${escapeCsv(r.metric)},${escapeCsv(r.value)}`).join('\n');
      const blob = new Blob(["\uFEFF" + header + lines], { type: 'text/csv;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      download(url, `data_${tsNow()}.csv`);
    }
  }

  function tsNow() {
    const d = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
  }
  function escapeCsv(v) {
    const s = v == null ? '' : String(v);
    if (/[",\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
    return s;
  }
  function download(url, filename) {
    const a = document.createElement('a');
    a.href = url; a.download = filename; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  // 初始化
  document.addEventListener('DOMContentLoaded', async () => {
    bindEvents();
    await populateStations();
    await populateMetrics();
    setDefaultRange();
    applyResponsiveLayout();
    window.addEventListener('resize', applyResponsiveLayout);
  });
})();


