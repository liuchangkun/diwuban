/**
 * 泵站数据处理系统 - 基础系统模块
 * 提供全局命名空间和共享功能
 */

// 全局命名空间
window.PumpSystem = window.PumpSystem || {};

// 页面管理器
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
        window.addEventListener('resize', () => {
            if (window.PumpDashboardCharts) {
                PumpDashboardCharts.resizeAll();
            }
        });

        // 设置页面卸载事件
        window.addEventListener('beforeunload', () => {
            // 清理资源
            if (window.PumpDashboardRealtime) {
                PumpDashboardRealtime.closeConnection();
            }
        });
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

console.log('🚰 泵站系统基础模块已加载');
