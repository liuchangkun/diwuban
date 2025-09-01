/**
 * 泵站优化控制台 - 核心逻辑模块
 * 负责页面初始化、事件处理、核心功能管理
 */

// 泵站优化控制台主对象
window.PumpDashboard = {
    // 配置选项
    config: {
        updateInterval: 5000,
        maxLogEntries: 1000,
        apiEndpoints: {
            stations: '/api/v1/stations',
            devices: '/api/v1/devices',
            performance: '/api/v1/monitoring/performance',
            logs: '/api/v1/logs/search',
            diagnostics: '/api/v1/diagnostics',
            economics: '/api/v1/economics',
            optimization: '/api/v1/optimization'
        }
    },

    // 状态管理
    state: {
        isRealTimeActive: true,
        currentAnalysisMode: 'realtime',
        currentTimeRange: '1h',
        currentStation: 'A',
        currentProcessTab: 'characteristic',
        currentEconomicTab: 'cost',
        currentView: 'dashboard',
        selectedDevices: ['all'],
        filters: {
            logLevel: 'all',
            deviceFilter: 'all',
            traceType: 'performance'
        }
    },

    // 数据缓存
    cache: {
        stations: [],
        devices: [],
        performanceData: {},
        logs: [],
        realTimeData: [],
        diagnostics: {},
        economics: {}
    },

    /**
     * 初始化控制台
     */
    async init() {
        console.log('🚰 泵站优化控制台初始化开始...');

        try {
            // 显示加载指示器
            this.showLoading('初始化系统...');

            // 初始化事件监听器
            this.initEventListeners();

            // 加载基础数据
            await this.loadInitialData();

            // 初始化图表
            if (window.PumpDashboardCharts) {
                PumpDashboardCharts.initAllCharts();
            }

            // 初始化实时数据
            if (window.PumpDashboardRealtime) {
                PumpDashboardRealtime.init();
            }

            // 初始化UI状态
            this.updateUIState();

            // 开始实时数据更新
            this.startRealTimeUpdates();

            // 隐藏加载指示器
            this.hideLoading();

            console.log('✅ 泵站优化控制台初始化完成');
            PumpSystem.Notification.success('系统初始化完成');

            // 更新最后更新时间
            document.getElementById('lastUpdateTime').textContent = '最后更新: ' + new Date().toLocaleTimeString();
        } catch (error) {
            console.error('❌ 初始化失败:', error);
            this.hideLoading();
            PumpSystem.Notification.error(`初始化失败: ${error.message}`);

            // 显示错误恢复选项
            this.showErrorRecoveryOptions(error);
        }
    },

    /**
     * 初始化事件监听器
     */
    initEventListeners() {
        // 分析模式切换
        document.querySelectorAll('.mode-options .option-tag').forEach(tag => {
            tag.addEventListener('click', (e) => {
                this.switchAnalysisMode(e.target.dataset.mode);
            });
        });

        // 时间范围切换
        document.querySelectorAll('.time-controls .option-tag').forEach(tag => {
            tag.addEventListener('click', (e) => {
                this.switchTimeRange(e.target.dataset.range);
            });
        });

        // 设备筛选
        document.querySelectorAll('.filter-options .option-tag').forEach(tag => {
            tag.addEventListener('click', (e) => {
                this.switchDeviceFilter(e.target.dataset.filter);
            });
        });

        // 高级功能
        document.querySelectorAll('.advanced-options .option-tag').forEach(tag => {
            tag.addEventListener('click', (e) => {
                this.toggleAdvancedFeature(e.target.dataset.feature);
            });
        });

        // 实时数据流筛选
        document.querySelectorAll('.filter-tabs .tab-button').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchRealTimeFilter(e.target.dataset.type);
            });
        });

        // 日志级别筛选
        const logLevelFilter = document.getElementById('logLevelFilter');
        if (logLevelFilter) {
            logLevelFilter.addEventListener('change', (e) => {
                this.filterLogs(e.target.value);
            });
        }

        // 自定义时间范围
        const customTimeStart = document.getElementById('customTimeStart');
        const customTimeEnd = document.getElementById('customTimeEnd');
        if (customTimeStart && customTimeEnd) {
            customTimeStart.addEventListener('change', () => {
                if (customTimeEnd.value) {
                    this.setCustomTimeRange(customTimeStart.value, customTimeEnd.value);
                }
            });

            customTimeEnd.addEventListener('change', () => {
                if (customTimeStart.value) {
                    this.setCustomTimeRange(customTimeStart.value, customTimeEnd.value);
                }
            });
        }

        // 键盘快捷键
        document.addEventListener('keydown', (e) => {
            this.handleKeyboardShortcuts(e);
        });
    },

    /**
     * 设置自定义时间范围
     */
    setCustomTimeRange(startTime, endTime) {
        // 移除其他时间范围的激活状态
        document.querySelectorAll('.time-controls .option-tag').forEach(tag => {
            tag.classList.remove('active');
        });

        this.state.currentTimeRange = 'custom';
        this.state.customTimeRange = {
            start: new Date(startTime),
            end: new Date(endTime)
        };

        PumpSystem.Notification.info('已设置自定义时间范围');
        this.refreshData();
    },

    /**
     * 显示错误恢复选项
     */
    showErrorRecoveryOptions(error) {
        const errorContainer = document.createElement('div');
        errorContainer.className = 'error-recovery-container';
        errorContainer.innerHTML = `
            <div class="error-recovery-header">
                <h3>系统初始化失败</h3>
                <p>${error.message}</p>
            </div>
            <div class="error-recovery-options">
                <button class="btn btn-primary" id="retry-init-btn">重试初始化</button>
                <button class="btn btn-secondary" id="use-mock-data-btn">使用模拟数据</button>
                <button class="btn btn-warning" id="offline-mode-btn">离线模式</button>
            </div>
        `;

        document.body.appendChild(errorContainer);

        // 添加事件监听器
        document.getElementById('retry-init-btn').addEventListener('click', () => {
            document.body.removeChild(errorContainer);
            this.init();
        });

        document.getElementById('use-mock-data-btn').addEventListener('click', () => {
            document.body.removeChild(errorContainer);
            this.loadMockData();
        });

        document.getElementById('offline-mode-btn').addEventListener('click', () => {
            document.body.removeChild(errorContainer);
            this.enableOfflineMode();
        });
    },

    /**
     * 启用离线模式
     */
    enableOfflineMode() {
        PumpSystem.Notification.info('已启用离线模式');
        this.state.isOfflineMode = true;
        this.loadMockData();

        // 显示离线模式指示器
        const header = document.querySelector('.header h1');
        const offlineIndicator = document.createElement('span');
        offlineIndicator.className = 'status-badge status-error';
        offlineIndicator.textContent = '● 离线模式';
        header.appendChild(offlineIndicator);
    },

    /**
     * 加载初始数据
     */
    async loadInitialData() {
        try {
            // 并行加载基础数据
            const [stationsData, devicesData, performanceData] = await Promise.all([
                PumpSystem.API.get('/stations'),
                PumpSystem.API.get('/devices'),
                PumpSystem.API.get('/monitoring/performance')
            ]);

            this.cache.stations = stationsData.data || [];
            this.cache.devices = devicesData.data || [];
            this.cache.performanceData = performanceData.data || {};

            // 更新UI
            this.updateStationTabs();
            this.updateDeviceList();
            this.updatePerformanceMetrics();

        } catch (error) {
            console.error('数据加载失败:', error);
            // 使用模拟数据作为备选
            this.loadMockData();
        }
    },

    /**
     * 加载模拟数据（备选方案）
     */
    loadMockData() {
        console.log('🔄 使用模拟数据...');

        this.cache.stations = [
            { id: 'A', name: '泵站A', status: 'online', efficiency: 85.6 },
            { id: 'B', name: '泵站B', status: 'online', efficiency: 82.3 },
            { id: 'C', name: '泵站C', status: 'warning', efficiency: 78.9 }
        ];

        this.cache.devices = [
            { id: 'A-01', name: '泵站A-01', station: 'A', status: 'healthy', efficiency: 87.2 },
            { id: 'A-02', name: '泵站A-02', station: 'A', status: 'healthy', efficiency: 84.8 },
            { id: 'B-01', name: '泵站B-01', station: 'B', status: 'warning', efficiency: 79.5 },
            { id: 'B-02', name: '泵站B-02', station: 'B', status: 'healthy', efficiency: 85.1 },
            { id: 'C-01', name: '泵站C-01', station: 'C', status: 'healthy', efficiency: 81.7 },
            { id: 'C-02', name: '泵站C-02', station: 'C', status: 'critical', efficiency: 76.2 }
        ];

        this.updateUI();
        PumpSystem.Notification.info('已加载模拟数据');
    },

    /**
     * 切换分析模式
     */
    switchAnalysisMode(mode) {
        this.state.currentAnalysisMode = mode;

        // 更新UI
        document.querySelectorAll('.mode-options .option-tag').forEach(tag => {
            tag.classList.remove('active');
        });
        document.querySelector(`[data-mode="${mode}"]`)?.classList.add('active');

        PumpSystem.Notification.info(`切换到${this.getModeDisplayName(mode)}模式`);
        this.refreshData();
    },

    /**
     * 获取模式显示名称
     */
    getModeDisplayName(mode) {
        const modeNames = {
            'realtime': '实时分析',
            'historical': '历史分析',
            'predictive': '预测分析',
            'tracing': '追溯分析',
            'diagnostic': '诊断分析',
            'optimization': '优化分析'
        };
        return modeNames[mode] || mode;
    },

    /**
     * 切换时间范围
     */
    switchTimeRange(range) {
        this.state.currentTimeRange = range;

        // 更新UI
        document.querySelectorAll('.time-controls .option-tag').forEach(tag => {
            tag.classList.remove('active');
        });
        document.querySelector(`[data-range="${range}"]`)?.classList.add('active');

        PumpSystem.Notification.info(`时间范围切换到${range}`);
        this.refreshData();
    },

    /**
     * 切换设备筛选
     */
    switchDeviceFilter(filter) {
        this.state.filters.deviceFilter = filter;

        // 更新UI
        document.querySelectorAll('.filter-options .option-tag').forEach(tag => {
            tag.classList.remove('active');
        });
        document.querySelector(`[data-filter="${filter}"]`)?.classList.add('active');

        PumpSystem.Notification.info(`设备筛选切换到${filter}`);
        this.refreshData();
    },

    /**
     * 切换高级功能
     */
    toggleAdvancedFeature(feature) {
        // 切换功能状态
        const tag = document.querySelector(`[data-feature="${feature}"]`);
        if (tag) {
            tag.classList.toggle('active');
        }

        PumpSystem.Notification.info(`切换${feature}功能`);
        this.refreshData();
    },

    /**
     * 切换实时数据流筛选
     */
    switchRealTimeFilter(type) {
        // 更新UI
        document.querySelectorAll('.filter-tabs .tab-button').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-type="${type}"]`)?.classList.add('active');

        PumpSystem.Notification.info(`实时数据流筛选切换到${type}`);
        this.refreshRealTimeData();
    },

    /**
     * 刷新实时数据
     */
    refreshRealTimeData() {
        if (window.PumpDashboardRealtime) {
            PumpDashboardRealtime.refreshData();
        }
    },

    /**
     * 切换站点
     */
    switchStation(stationId) {
        this.state.currentStation = stationId;

        // 更新UI
        document.querySelectorAll('.station-tabs .tab-button').forEach(tab => {
            tab.classList.remove('active');
        });
        event.target.classList.add('active');

        PumpSystem.Notification.info(`切换到${stationId === 'all' ? '全部泵站' : '泵站' + stationId}`);
        this.refreshStationData();
    },

    /**
     * 处理键盘快捷键
     */
    handleKeyboardShortcuts(event) {
        // Ctrl+R 刷新数据
        if (event.ctrlKey && event.key === 'r') {
            event.preventDefault();
            this.refreshData();
        }

        // Ctrl+E 导出数据
        if (event.ctrlKey && event.key === 'e') {
            event.preventDefault();
            this.exportData('excel');
        }
    },

    /**
     * 切换实时数据更新
     */
    toggleRealTime() {
        this.state.isRealTimeActive = !this.state.isRealTimeActive;
        const toggleBtn = document.getElementById('realTimeToggle');
        if (toggleBtn) {
            toggleBtn.textContent = this.state.isRealTimeActive ? '⏸ 暂停' : '▶ 继续';
        }
        PumpSystem.Notification.info(this.state.isRealTimeActive ? '已开始实时更新' : '已暂停实时更新');
    },

    /**
     * 开始实时数据更新
     */
    startRealTimeUpdates() {
        setInterval(() => {
            if (this.state.isRealTimeActive) {
                this.updateRealTimeData();
            }
        }, this.config.updateInterval);
    },

    /**
     * 更新实时数据
     */
    updateRealTimeData() {
        // 模拟实时数据更新
        this.updatePerformanceMetrics();
        this.updateDeviceHealth();

        // 更新最后更新时间
        document.getElementById('lastUpdateTime').textContent = '最后更新: ' + new Date().toLocaleTimeString();

        // 通过实时数据模块添加数据流项目
        if (window.PumpDashboardRealtime) {
            PumpDashboardRealtime.addRandomStreamItem();
        }
    },

    /**
     * 更新性能指标
     */
    updatePerformanceMetrics() {
        // 更新现有指标
        document.getElementById('totalEfficiency').textContent = (85 + Math.random() * 5).toFixed(1) + '%';
        document.getElementById('totalFlow').textContent = (1200 + Math.random() * 100).toFixed(0);
        document.getElementById('totalPower').textContent = (340 + Math.random() * 20).toFixed(1);
        document.getElementById('alertCount').textContent = Math.floor(Math.random() * 3);

        // 更新新增指标
        document.getElementById('vibrationLevel').textContent = (2 + Math.random() * 1).toFixed(1);
        document.getElementById('temperatureStatus').textContent = (70 + Math.random() * 5).toFixed(1) + '°C';
        document.getElementById('sealCondition').textContent = (90 + Math.random() * 8).toFixed(1) + '%';
        document.getElementById('bearingWear').textContent = (10 + Math.random() * 5).toFixed(1) + '%';
    },

    /**
     * 更新设备健康状态
     */
    updateDeviceHealth() {
        document.getElementById('healthyDevices').textContent = Math.floor(5 + Math.random() * 3);
        document.getElementById('warningDevices').textContent = Math.floor(1 + Math.random() * 2);
        document.getElementById('criticalDevices').textContent = Math.floor(Math.random() * 2);
        document.getElementById('maintenanceDevices').textContent = Math.floor(1 + Math.random() * 2);
    },

    /**
     * 更新设备列表
     */
    updateDeviceList() {
        const deviceList = document.getElementById('deviceList');
        if (!deviceList) return;

        deviceList.innerHTML = '';
        this.cache.devices.forEach(device => {
            const deviceElement = document.createElement('div');
            deviceElement.className = 'device-item';
            deviceElement.innerHTML = `
                <div class="device-name">${device.name}</div>
                <div class="device-status ${device.status}">${this.getDeviceStatusText(device.status)}</div>
                <div class="device-efficiency">${device.efficiency}%</div>
            `;
            deviceList.appendChild(deviceElement);
        });
    },

    /**
     * 获取设备状态文本
     */
    getDeviceStatusText(status) {
        const statusTexts = {
            'healthy': '健康',
            'warning': '警告',
            'critical': '严重',
            'offline': '离线',
            'maintenance': '维护中'
        };
        return statusTexts[status] || status;
    },

    /**
     * 刷新数据
     */
    async refreshData() {
        this.showLoading('刷新数据中...');
        try {
            await this.loadInitialData();
            this.updateUI();
            PumpSystem.Notification.success('数据刷新完成');
        } catch (error) {
            PumpSystem.Notification.error(`刷新失败: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    },

    /**
     * 更新UI
     */
    updateUI() {
        this.updatePerformanceMetrics();
        this.updateDeviceHealth();
        this.updateDeviceList();
        this.updateStationTabs();

        // 更新最后更新时间
        document.getElementById('lastUpdateTime').textContent = '最后更新: ' + new Date().toLocaleTimeString();
    },

    /**
     * 更新UI状态
     */
    updateUIState() {
        // 根据当前视图调整面板显示
        this.updateViewLayout();
    },

    /**
     * 更新视图布局
     */
    updateViewLayout() {
        // 根据当前视图调整面板显示
        const panels = document.querySelectorAll('.panel');
        panels.forEach(panel => {
            // 默认显示所有面板
            panel.style.display = 'block';

            // 根据视图类型调整显示
            switch (this.state.currentView) {
                case 'dashboard':
                    // 仪表盘视图显示所有面板
                    break;
                case 'analysis':
                    // 分析视图隐藏部分面板
                    if (panel.classList.contains('quality-overview-panel') ||
                        panel.classList.contains('status-overview-panel')) {
                        panel.style.display = 'none';
                    }
                    break;
                case 'comparison':
                    // 对比视图只显示对比相关面板
                    if (!panel.classList.contains('comparison-panel') &&
                        !panel.classList.contains('traceability-panel')) {
                        panel.style.display = 'none';
                    }
                    break;
            }
        });
    },

    /**
     * 更新站点标签页
     */
    updateStationTabs() {
        // 这里可以动态生成站点标签
    },

    /**
     * 刷新站点数据
     */
    refreshStationData() {
        // 刷新站点相关数据
        // 示例代码，根据实际情况调整
    },

    /**
     * 显示加载指示器
     */
    showLoading(message) {
        const indicator = document.getElementById('loadingIndicator');
        if (indicator) {
            const loadingText = indicator.querySelector('.loading-text');
            if (loadingText) {
                loadingText.textContent = message || '数据加载中...';
            }
            indicator.style.display = 'flex';
        }
    },

    /**
     * 隐藏加载指示器
     */
    hideLoading() {
        const indicator = document.getElementById('loadingIndicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    },

    /**
     * 导出数据
     */
    exportData(format) {
        PumpSystem.Notification.info(`正在导出${format.toUpperCase()}格式数据...`);

        // 模拟导出过程
        setTimeout(() => {
            switch (format) {
                case 'excel':
                    PumpSystem.DataExporter.exportExcel(this.getExportData(), '泵站优化数据');
                    break;
                case 'pdf':
                    this.exportPDF(this.getExportData(), '泵站优化数据报告');
                    break;
                case 'json':
                    PumpSystem.DataExporter.exportJSON(this.getExportData(), 'pump_optimization_data');
                    break;
            }
            PumpSystem.Notification.success(`${format.toUpperCase()}数据导出完成`);
        }, 1000);
    },

    /**
     * 导出PDF
     */
    exportPDF(data, filename) {
        // 由于PDF生成需要额外库，这里只是模拟
        PumpSystem.Notification.info('PDF导出功能需要额外库支持，请稍后查看');

        // 模拟转换为JSON
        PumpSystem.DataExporter.exportJSON(data, filename.replace('.pdf', '.json'));
    },

    /**
     * 获取导出数据
     */
    getExportData() {
        return {
            timestamp: new Date().toISOString(),
            stations: this.cache.stations,
            devices: this.cache.devices,
            performance: this.cache.performanceData,
            summary: {
                totalEfficiency: document.getElementById('totalEfficiency').textContent,
                totalFlow: document.getElementById('totalFlow').textContent,
                totalPower: document.getElementById('totalPower').textContent,
                energySavings: document.getElementById('energySavings').textContent
            }
        };
    },

    /**
     * 清空日志
     */
    clearLogs() {
        const logViewer = document.getElementById('logViewer');
        if (logViewer) {
            logViewer.innerHTML = '';
        }
        PumpSystem.Notification.success('日志已清空');
    },

    /**
     * 导出日志
     */
    exportLogs() {
        PumpSystem.Notification.info('正在导出日志...');
        // 模拟导出过程
        setTimeout(() => {
            const mockLogContent = '系统日志内容...\n时间戳: ' + new Date().toISOString();
            const blob = new Blob([mockLogContent], { type: 'text/plain' });
            PumpSystem.DataExporter.downloadBlob(blob, 'system_logs.txt');
            PumpSystem.Notification.success('日志导出完成');
        }, 500);
    }
};

console.log('🚰 泵站仪表盘核心模块已加载');
