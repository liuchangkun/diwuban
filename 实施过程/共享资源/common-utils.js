/**
 * 泵站数据处理系统 - 公共JavaScript工具库
 * 提供统一的工具函数、数据处理、图表管理等功能
 */

// 全局命名空间
window.PumpSystem = window.PumpSystem || {};

// 工具函数库
PumpSystem.Utils = {

    /**
     * 格式化时间戳
     * @param {Date|string|number} timestamp - 时间戳
     * @param {string} format - 格式化模式
     * @returns {string} 格式化后的时间字符串
     */
    formatTime(timestamp, format = 'YYYY-MM-DD HH:mm:ss') {
        const date = new Date(timestamp);
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');

        return format
            .replace('YYYY', year)
            .replace('MM', month)
            .replace('DD', day)
            .replace('HH', hours)
            .replace('mm', minutes)
            .replace('ss', seconds);
    },

    /**
     * 格式化数值
     * @param {number} value - 数值
     * @param {number} decimals - 小数位数
     * @param {string} suffix - 后缀单位
     * @returns {string} 格式化后的数值字符串
     */
    formatNumber(value, decimals = 2, suffix = '') {
        if (typeof value !== 'number' || isNaN(value)) return '--';
        return value.toFixed(decimals) + suffix;
    },

    /**
     * 防抖函数
     * @param {Function} func - 要防抖的函数
     * @param {number} wait - 等待时间（毫秒）
     * @returns {Function} 防抖后的函数
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func.apply(this, args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * 节流函数
     * @param {Function} func - 要节流的函数
     * @param {number} limit - 限制时间（毫秒）
     * @returns {Function} 节流后的函数
     */
    throttle(func, limit) {
        let inThrottle;
        return function executedFunction(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    /**
     * 生成唯一ID
     * @param {string} prefix - 前缀
     * @returns {string} 唯一ID
     */
    generateId(prefix = 'id') {
        return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    },

    /**
     * 深拷贝对象
     * @param {*} obj - 要拷贝的对象
     * @returns {*} 拷贝后的对象
     */
    deepClone(obj) {
        if (obj === null || typeof obj !== 'object') return obj;
        if (obj instanceof Date) return new Date(obj);
        if (obj instanceof Array) return obj.map(item => this.deepClone(item));
        if (typeof obj === 'object') {
            const clonedObj = {};
            for (let key in obj) {
                if (obj.hasOwnProperty(key)) {
                    clonedObj[key] = this.deepClone(obj[key]);
                }
            }
            return clonedObj;
        }
    }
};

// 通知系统
PumpSystem.Notification = {

    /**
     * 显示通知
     * @param {string} message - 通知消息
     * @param {string} type - 通知类型 (success, error, warning, info)
     * @param {number} duration - 显示时长（毫秒）
     */
    show(message, type = 'info', duration = 3000) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;

        document.body.appendChild(notification);

        // 触发显示动画
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);

        // 自动隐藏
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                if (document.body.contains(notification)) {
                    document.body.removeChild(notification);
                }
            }, 300);
        }, duration);
    },

    success(message, duration) { this.show(message, 'success', duration); },
    error(message, duration) { this.show(message, 'error', duration); },
    warning(message, duration) { this.show(message, 'warning', duration); },
    info(message, duration) { this.show(message, 'info', duration); }
};

// 图表管理器
PumpSystem.ChartManager = {
    charts: new Map(),

    /**
     * 创建Chart.js图表
     * @param {string} canvasId - 画布ID
     * @param {Object} config - 图表配置
     * @returns {Object} Chart.js实例
     */
    createChart(canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.error(`Canvas with id "${canvasId}" not found`);
            return null;
        }

        // 销毁已存在的图表
        if (this.charts.has(canvasId)) {
            this.charts.get(canvasId).destroy();
        }

        const chart = new Chart(canvas, config);
        this.charts.set(canvasId, chart);
        return chart;
    },

    /**
     * 创建ECharts图表
     * @param {string} containerId - 容器ID
     * @param {Object} option - ECharts配置
     * @returns {Object} ECharts实例
     */
    createEChart(containerId, option) {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`Container with id "${containerId}" not found`);
            return null;
        }

        // 销毁已存在的图表
        if (this.charts.has(containerId)) {
            this.charts.get(containerId).dispose();
        }

        const chart = echarts.init(container);
        chart.setOption(option);
        this.charts.set(containerId, chart);
        return chart;
    },

    /**
     * 更新图表数据
     * @param {string} chartId - 图表ID
     * @param {Object} newData - 新数据
     */
    updateChart(chartId, newData) {
        const chart = this.charts.get(chartId);
        if (!chart) return;

        if (chart.update) {
            // Chart.js
            if (newData.datasets) {
                chart.data.datasets = newData.datasets;
            }
            if (newData.labels) {
                chart.data.labels = newData.labels;
            }
            chart.update();
        } else if (chart.setOption) {
            // ECharts
            chart.setOption(newData);
        }
    },

    /**
     * 销毁图表
     * @param {string} chartId - 图表ID
     */
    destroyChart(chartId) {
        const chart = this.charts.get(chartId);
        if (!chart) return;

        if (chart.destroy) {
            chart.destroy();
        } else if (chart.dispose) {
            chart.dispose();
        }
        this.charts.delete(chartId);
    },

    /**
     * 响应式调整所有图表
     */
    resizeAll() {
        this.charts.forEach(chart => {
            if (chart.resize) {
                chart.resize();
            } else if (chart.update) {
                chart.update();
            }
        });
    }
};

// 数据导出功能
PumpSystem.DataExporter = {

    /**
     * 导出JSON数据
     * @param {Object} data - 要导出的数据
     * @param {string} filename - 文件名
     */
    exportJSON(data, filename = 'pump_data') {
        const jsonStr = JSON.stringify(data, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json' });
        this.downloadBlob(blob, `${filename}.json`);
    },

    /**
     * 导出CSV数据
     * @param {Array} data - 表格数据
     * @param {string} filename - 文件名
     */
    exportCSV(data, filename = 'pump_data') {
        if (!Array.isArray(data) || data.length === 0) return;

        const headers = Object.keys(data[0]);
        const csvContent = [
            headers.join(','),
            ...data.map(row => headers.map(header =>
                `"${String(row[header]).replace(/"/g, '""')}"`)
                .join(','))
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        this.downloadBlob(blob, `${filename}.csv`);
    },

    /**
     * 导出Excel数据
     * @param {Array} data - 表格数据
     * @param {string} filename - 文件名
     */
    exportExcel(data, filename = 'pump_data') {
        // 这里需要引入xlsx库或类似库来生成Excel文件
        // 简化版本，导出为CSV格式
        this.exportCSV(data, filename);
        PumpSystem.Notification.info('Excel导出功能需要额外库支持，当前导出为CSV格式');
    },

    /**
     * 下载Blob文件
     * @param {Blob} blob - 文件数据
     * @param {string} filename - 文件名
     */
    downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    },

    /**
     * 生成完整的数据报告
     * @param {Object} systemData - 系统数据
     * @param {string} format - 导出格式 (json, csv, excel)
     */
    exportReport(systemData, format = 'json') {
        const timestamp = PumpSystem.Utils.formatTime(new Date(), 'YYYY-MM-DD_HH-mm-ss');
        const filename = `pump_system_report_${timestamp}`;

        const reportData = {
            timestamp: new Date().toISOString(),
            system_status: systemData.systemStatus || {},
            devices: systemData.devices || [],
            performance_metrics: systemData.performanceMetrics || {},
            calibration_history: systemData.calibrationHistory || [],
            quality_metrics: systemData.qualityMetrics || {},
            algorithm_performance: systemData.algorithmPerformance || {}
        };

        switch (format.toLowerCase()) {
            case 'json':
                this.exportJSON(reportData, filename);
                break;
            case 'csv':
                // 将复杂对象转换为平铺的CSV格式
                const flatData = this.flattenReportData(reportData);
                this.exportCSV(flatData, filename);
                break;
            case 'excel':
                const flatDataForExcel = this.flattenReportData(reportData);
                this.exportExcel(flatDataForExcel, filename);
                break;
            default:
                console.error('Unsupported export format:', format);
        }
    },

    /**
     * 将复杂报告数据平铺为CSV友好格式
     * @param {Object} reportData - 报告数据
     * @returns {Array} 平铺后的数据数组
     */
    flattenReportData(reportData) {
        const flattened = [];

        // 添加系统状态信息
        if (reportData.system_status) {
            flattened.push({
                category: 'System Status',
                metric: 'Overall Efficiency',
                value: reportData.system_status.efficiency || '--',
                unit: '%',
                timestamp: reportData.timestamp
            });
        }

        // 添加设备信息
        if (reportData.devices && Array.isArray(reportData.devices)) {
            reportData.devices.forEach(device => {
                flattened.push({
                    category: 'Device',
                    metric: `${device.name} Status`,
                    value: device.status || '--',
                    unit: '',
                    timestamp: reportData.timestamp
                });
            });
        }

        return flattened;
    }
};

// API通信管理
PumpSystem.API = {
    baseURL: '/api/v1',

    /**
     * 发送GET请求
     * @param {string} endpoint - API端点
     * @param {Object} params - 查询参数
     * @returns {Promise} API响应
     */
    async get(endpoint, params = {}) {
        const url = new URL(`${this.baseURL}${endpoint}`, window.location.origin);
        Object.keys(params).forEach(key => {
            if (params[key] !== null && params[key] !== undefined) {
                url.searchParams.append(key, params[key]);
            }
        });

        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`API Error: ${response.status} ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API GET Error:', error);
            PumpSystem.Notification.error(`API请求失败: ${error.message}`);
            throw error;
        }
    },

    /**
     * 发送POST请求
     * @param {string} endpoint - API端点
     * @param {Object} data - 请求数据
     * @returns {Promise} API响应
     */
    async post(endpoint, data = {}) {
        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                throw new Error(`API Error: ${response.status} ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API POST Error:', error);
            PumpSystem.Notification.error(`API请求失败: ${error.message}`);
            throw error;
        }
    }
};

// 实时数据管理
PumpSystem.RealTimeManager = {
    intervals: new Map(),
    websockets: new Map(),

    /**
     * 启动数据轮询
     * @param {string} key - 轮询标识
     * @param {Function} callback - 回调函数
     * @param {number} interval - 轮询间隔（毫秒）
     */
    startPolling(key, callback, interval = 5000) {
        if (this.intervals.has(key)) {
            clearInterval(this.intervals.get(key));
        }

        const intervalId = setInterval(callback, interval);
        this.intervals.set(key, intervalId);

        // 立即执行一次
        callback();
    },

    /**
     * 停止数据轮询
     * @param {string} key - 轮询标识
     */
    stopPolling(key) {
        if (this.intervals.has(key)) {
            clearInterval(this.intervals.get(key));
            this.intervals.delete(key);
        }
    },

    /**
     * 停止所有轮询
     */
    stopAllPolling() {
        this.intervals.forEach(intervalId => clearInterval(intervalId));
        this.intervals.clear();
    }
};

// 页面生命周期管理
PumpSystem.PageManager = {
    initialized: false,

    /**
     * 初始化页面
     * @param {Function} initCallback - 初始化回调函数
     */
    init(initCallback) {
        if (this.initialized) return;

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.initialized = true;
                initCallback();
            });
        } else {
            this.initialized = true;
            initCallback();
        }

        // 设置窗口调整大小事件
        window.addEventListener('resize', PumpSystem.Utils.throttle(() => {
            PumpSystem.ChartManager.resizeAll();
        }, 250));

        // 设置页面卸载事件
        window.addEventListener('beforeunload', () => {
            PumpSystem.RealTimeManager.stopAllPolling();
        });
    }
};

// 全局初始化
PumpSystem.init = function (config = {}) {
    console.log('🚰 泵站数据处理系统已启动');

    // 设置默认配置
    if (config.apiBaseURL) {
        PumpSystem.API.baseURL = config.apiBaseURL;
    }

    return PumpSystem;
};

// 导出到全局
window.PumpSystem = PumpSystem;
