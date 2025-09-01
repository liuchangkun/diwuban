// 泵特性曲线校准监控系统 - 工具函数模块

// 数据格式化工具
const DataFormatter = {
    // 格式化精度值
    formatAccuracy: function (value) {
        if (typeof value !== 'number') return 'N/A';
        return (value * 100).toFixed(1) + '%';
    },

    // 格式化时间
    formatTime: function (timestamp) {
        if (!timestamp) return 'N/A';
        const date = new Date(timestamp);
        return date.toLocaleString('zh-CN');
    },

    // 格式化持续时间
    formatDuration: function (seconds) {
        if (typeof seconds !== 'number') return 'N/A';

        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);

        if (hours > 0) {
            return `${hours}小时${minutes}分${secs}秒`;
        } else if (minutes > 0) {
            return `${minutes}分${secs}秒`;
        } else {
            return `${secs}秒`;
        }
    },

    // 格式化文件大小
    formatFileSize: function (bytes) {
        if (typeof bytes !== 'number') return 'N/A';

        const units = ['B', 'KB', 'MB', 'GB'];
        let size = bytes;
        let unitIndex = 0;

        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }

        return size.toFixed(1) + units[unitIndex];
    },

    // 格式化数值
    formatNumber: function (value, decimals = 2) {
        if (typeof value !== 'number') return 'N/A';
        return value.toFixed(decimals);
    }
};

// 数据验证工具
const DataValidator = {
    // 验证R²值范围
    isValidR2: function (value) {
        return typeof value === 'number' && value >= 0 && value <= 1;
    },

    // 验证精度改善幅度
    isValidImprovement: function (before, after) {
        return this.isValidR2(before) && this.isValidR2(after) && after >= before;
    },

    // 验证时间戳
    isValidTimestamp: function (timestamp) {
        const date = new Date(timestamp);
        return date instanceof Date && !isNaN(date);
    },

    // 验证曲线数据点
    isValidCurveData: function (data) {
        return Array.isArray(data) && data.length > 0 &&
            data.every(point => typeof point.x === 'number' && typeof point.y === 'number');
    }
};

// 算法信息工具
const AlgorithmInfo = {
    algorithms: {
        'neural_network': {
            name: '神经网络',
            icon: '🧠',
            description: '深度学习，适合复杂非线性拟合',
            strengths: ['高精度', '非线性建模', '自适应学习'],
            weaknesses: ['计算复杂', '需要大量数据', '黑盒模型']
        },
        'random_forest': {
            name: '随机森林',
            icon: '🌲',
            description: '集成学习，稳定性好，泛化能力强',
            strengths: ['稳定性好', '抗过拟合', '特征重要性'],
            weaknesses: ['内存消耗大', '预测速度慢', '难以外推']
        },
        'gaussian_process': {
            name: '高斯过程',
            icon: '📊',
            description: '概率建模，提供不确定性估计',
            strengths: ['不确定性量化', '少样本学习', '理论基础好'],
            weaknesses: ['计算复杂度高', '超参数敏感', '扩展性差']
        },
        'polynomial': {
            name: '多项式拟合',
            icon: '📈',
            description: '传统方法，快速简单，兜底方案',
            strengths: ['计算快速', '可解释性强', '数学基础好'],
            weaknesses: ['容易过拟合', '外推性差', '非线性能力有限']
        },
        'spline': {
            name: '样条插值',
            icon: '〰️',
            description: '分段平滑拟合，局部性好',
            strengths: ['局部拟合好', '计算效率高', '平滑性好'],
            weaknesses: ['参数选择复杂', '边界效应', '外推不可靠']
        },
        'linear': {
            name: '线性回归',
            icon: '📏',
            description: '最简单的拟合方法，基础兜底',
            strengths: ['计算简单', '可解释性强', '鲁棒性好'],
            weaknesses: ['只能建模线性关系', '精度有限', '假设严格']
        }
    },

    getAlgorithmInfo: function (algorithmId) {
        return this.algorithms[algorithmId] || {
            name: '未知算法',
            icon: '❓',
            description: '算法信息未定义',
            strengths: [],
            weaknesses: []
        };
    },

    getAllAlgorithms: function () {
        return Object.keys(this.algorithms).map(id => ({
            id,
            ...this.algorithms[id]
        }));
    }
};

// 状态管理工具
const StatusManager = {
    statuses: {
        'pending': { name: '待处理', icon: '⏸', color: '#6c757d' },
        'running': { name: '运行中', icon: '▶', color: '#007bff' },
        'completed': { name: '已完成', icon: '✓', color: '#28a745' },
        'failed': { name: '失败', icon: '✗', color: '#dc3545' },
        'paused': { name: '已暂停', icon: '⏸', color: '#ffc107' }
    },

    getStatusInfo: function (status) {
        return this.statuses[status] || this.statuses['pending'];
    },

    getStatusBadge: function (status) {
        const info = this.getStatusInfo(status);
        return `<span class="status-badge status-${status}" style="color: ${info.color}">
                    ${info.icon} ${info.name}
                </span>`;
    }
};

// 性能等级工具
const PerformanceGrader = {
    grades: {
        excellent: { name: '优秀', threshold: 0.9, color: '#28a745' },
        good: { name: '良好', threshold: 0.8, color: '#007bff' },
        average: { name: '一般', threshold: 0.7, color: '#ffc107' },
        poor: { name: '较差', threshold: 0.5, color: '#fd7e14' },
        bad: { name: '很差', threshold: 0, color: '#dc3545' }
    },

    getGrade: function (accuracy) {
        if (accuracy >= this.grades.excellent.threshold) return 'excellent';
        if (accuracy >= this.grades.good.threshold) return 'good';
        if (accuracy >= this.grades.average.threshold) return 'average';
        if (accuracy >= this.grades.poor.threshold) return 'poor';
        return 'bad';
    },

    getGradeInfo: function (accuracy) {
        const grade = this.getGrade(accuracy);
        return {
            grade,
            ...this.grades[grade]
        };
    },

    getGradeBadge: function (accuracy) {
        const info = this.getGradeInfo(accuracy);
        return `<span class="grade-badge grade-${info.grade}" style="color: ${info.color}">
                    ${info.name}
                </span>`;
    }
};

// 数据导出工具
const DataExporter = {
    // 导出为JSON
    exportJSON: function (data, filename) {
        const jsonStr = JSON.stringify(data, null, 2);
        this.downloadFile(jsonStr, filename + '.json', 'application/json');
    },

    // 导出为CSV
    exportCSV: function (data, filename) {
        if (!Array.isArray(data) || data.length === 0) {
            console.warn('无效的CSV数据');
            return;
        }

        const headers = Object.keys(data[0]);
        const csvContent = [
            headers.join(','),
            ...data.map(row => headers.map(header =>
                JSON.stringify(row[header] || '')
            ).join(','))
        ].join('\n');

        this.downloadFile(csvContent, filename + '.csv', 'text/csv');
    },

    // 通用文件下载
    downloadFile: function (content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }
};

// 颜色工具
const ColorUtils = {
    // 根据精度获取颜色
    getAccuracyColor: function (accuracy) {
        if (accuracy >= 0.9) return '#28a745'; // 绿色
        if (accuracy >= 0.8) return '#007bff'; // 蓝色
        if (accuracy >= 0.7) return '#ffc107'; // 黄色
        if (accuracy >= 0.5) return '#fd7e14'; // 橙色
        return '#dc3545'; // 红色
    },

    // 生成渐变色
    generateGradient: function (startColor, endColor, steps) {
        const colors = [];
        for (let i = 0; i < steps; i++) {
            const ratio = i / (steps - 1);
            colors.push(this.interpolateColor(startColor, endColor, ratio));
        }
        return colors;
    },

    // 颜色插值
    interpolateColor: function (color1, color2, ratio) {
        const hex = (color) => {
            const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(color);
            return result ? {
                r: parseInt(result[1], 16),
                g: parseInt(result[2], 16),
                b: parseInt(result[3], 16)
            } : null;
        };

        const c1 = hex(color1);
        const c2 = hex(color2);

        if (!c1 || !c2) return color1;

        const r = Math.round(c1.r + (c2.r - c1.r) * ratio);
        const g = Math.round(c1.g + (c2.g - c1.g) * ratio);
        const b = Math.round(c1.b + (c2.b - c1.b) * ratio);

        return `rgb(${r}, ${g}, ${b})`;
    }
};

// 本地存储工具
const StorageUtils = {
    // 保存数据到localStorage
    save: function (key, data) {
        try {
            localStorage.setItem(key, JSON.stringify(data));
            return true;
        } catch (error) {
            console.error('保存数据失败:', error);
            return false;
        }
    },

    // 从localStorage读取数据
    load: function (key, defaultValue = null) {
        try {
            const data = localStorage.getItem(key);
            return data ? JSON.parse(data) : defaultValue;
        } catch (error) {
            console.error('读取数据失败:', error);
            return defaultValue;
        }
    },

    // 删除数据
    remove: function (key) {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (error) {
            console.error('删除数据失败:', error);
            return false;
        }
    },

    // 清空所有数据
    clear: function () {
        try {
            localStorage.clear();
            return true;
        } catch (error) {
            console.error('清空数据失败:', error);
            return false;
        }
    }
};

// 事件发射器
class EventEmitter {
    constructor() {
        this.events = {};
    }

    on(event, callback) {
        if (!this.events[event]) {
            this.events[event] = [];
        }
        this.events[event].push(callback);
    }

    off(event, callback) {
        if (!this.events[event]) return;
        this.events[event] = this.events[event].filter(cb => cb !== callback);
    }

    emit(event, ...args) {
        if (!this.events[event]) return;
        this.events[event].forEach(callback => {
            try {
                callback(...args);
            } catch (error) {
                console.error('事件处理错误:', error);
            }
        });
    }
}

// 创建全局事件发射器实例
const globalEventEmitter = new EventEmitter();

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 节流函数
function throttle(func, limit) {
    let inThrottle;
    return function (...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// 深度复制
function deepClone(obj) {
    if (obj === null || typeof obj !== 'object') return obj;
    if (obj instanceof Date) return new Date(obj);
    if (obj instanceof Array) return obj.map(item => deepClone(item));
    if (typeof obj === 'object') {
        const clonedObj = {};
        for (const key in obj) {
            if (obj.hasOwnProperty(key)) {
                clonedObj[key] = deepClone(obj[key]);
            }
        }
        return clonedObj;
    }
}

// 生成唯一ID
function generateUniqueId() {
    return 'id_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
}

// 休眠函数
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// 异步重试机制
async function retryAsync(fn, maxRetries = 3, delay = 1000) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            return await fn();
        } catch (error) {
            if (i === maxRetries - 1) throw error;
            await sleep(delay * Math.pow(2, i)); // 指数退避
        }
    }
}

// 错误处理工具
const ErrorHandler = {
    log: function (error, context = '') {
        const timestamp = new Date().toISOString();
        const errorInfo = {
            timestamp,
            context,
            message: error.message,
            stack: error.stack,
            name: error.name
        };

        console.error('应用错误:', errorInfo);

        // 这里可以添加错误上报逻辑
        this.reportError(errorInfo);
    },

    reportError: function (errorInfo) {
        // 模拟错误上报
        StorageUtils.save('last_error', errorInfo);
    },

    getLastError: function () {
        return StorageUtils.load('last_error');
    }
};

// 导出所有工具函数
window.CalibrationUtils = {
    DataFormatter,
    DataValidator,
    AlgorithmInfo,
    StatusManager,
    PerformanceGrader,
    DataExporter,
    ColorUtils,
    StorageUtils,
    EventEmitter,
    globalEventEmitter,
    debounce,
    throttle,
    deepClone,
    generateUniqueId,
    sleep,
    retryAsync,
    ErrorHandler
};
