// api.js - API 调用封装与错误处理（中文注释）
(function () {
  'use strict';

  const DEFAULT_TIMEOUT = 15000; // 15秒超时

  // 简易封装 fetch，统一超时、错误处理
  async function request(url, options = {}) {
    // 附带超时控制
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), options.timeout || DEFAULT_TIMEOUT);

    try {
      const resp = await fetch(url, { ...options, signal: controller.signal });
      if (!resp.ok) {
        let detail = '';
        try { detail = await resp.text(); } catch (_) { /* 忽略 */ }
        throw new Error(`HTTP ${resp.status} ${resp.statusText} - ${detail}`);
      }
      const contentType = resp.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        return await resp.json();
      }
      return await resp.text();
    } catch (err) {
      // 统一错误输出
      console.error('API请求失败:', err);
      throw err;
    } finally {
      clearTimeout(id);
    }
  }

  // 具体 API 封装（原始值查询 + 指标清单）
  const API = {
    // 获取泵站列表
    getStations() { return request('/api/v1/data/stations'); },
    // 获取某泵站的设备列表
    getDevicesByStation(stationId) { return request(`/api/v1/data/stations/${encodeURIComponent(stationId)}/devices`); },

    // 指标清单（固定来源 dim_metric_config）
    getMetrics() { return request('/api/v1/data/metrics'); },

    // 原始数据（泵站/设备）——默认 wide，可切换 long
    getStationRaw(stationId, { start_time, end_time, limit = 1000, format = 'wide' } = {}) {
      const qs = new URLSearchParams({ start_time, end_time, limit, format });
      return request(`/api/v1/data/stations/${encodeURIComponent(stationId)}/raw?${qs.toString()}`);
    },
    getDeviceRaw(deviceId, { start_time, end_time, limit = 1000, format = 'wide' } = {}) {
      const qs = new URLSearchParams({ start_time, end_time, limit, format });
      return request(`/api/v1/data/devices/${encodeURIComponent(deviceId)}/raw?${qs.toString()}`);
    },

    // 日志
    getLogLevels() { return request('/api/v1/logs/levels'); },
    searchLogs(params) {
      const qs = new URLSearchParams(params);
      return request(`/api/v1/logs/search?${qs.toString()}`);
    }
  };

  window.API = API;
})();

