/**
 * 特性曲线校准监控 - 核心JavaScript逻辑
 * 负责校准过程管理、实时监控、数据更新等功能
 */

// 校准监控主对象
window.CalibrationMonitor = {
    // 配置选项
    config: {
        updateInterval: 3000,
        maxHistoryEntries: 200,
        calibrationTimeout: 300000
    },

    // 状态管理
    state: {
        isCalibrating: false,
        currentStrategy: 'multi-algorithm',
        currentCurveType: 'hq',
        precisionTimeRange: '1h',
        selectedPumps: [],
        calibrationProgress: 0
    },

    // 数据缓存
    cache: {
        pumps: [],
        curveTypes: [],
        calibrationHistory: [],
        precisionData: {},
        rlsParameters: {},
        realTimeLogs: []
    },

    /**
     * 初始化监控系统
     */
    async init() {
        console.log('🎯 校准监控系统初始化开始...');

        try {
            this.initEventListeners();
            await this.loadInitialData();
            this.initCharts();
            this.initPumpQueryModule();
            this.startRealTimeUpdates();
            this.updateUIState();

            console.log('✅ 校准监控系统初始化完成');
            PumpSystem.Notification.success('校准监控系统已准备就绪');
        } catch (error) {
            console.error('❌ 校准监控初始化失败:', error);
            PumpSystem.Notification.error(`初始化失败: ${error.message}`);
        }
    },

    /**
     * 初始化事件监听器
     */
    initEventListeners() {
        // 校准策略选择
        document.querySelectorAll('.strategy-card').forEach(card => {
            card.addEventListener('click', (e) => {
                this.selectCalibrationStrategy(e.currentTarget.dataset.strategy);
            });
        });

        // 各种选择器事件
        const curveTypeSelect = document.getElementById('curveType');
        if (curveTypeSelect) {
            curveTypeSelect.addEventListener('change', (e) => {
                this.switchCurveType(e.target.value);
            });
        }
    },

    /**
     * 加载初始数据
     */
    async loadInitialData() {
        try {
            this.cache.pumps = await this.loadPumpsData();
            this.cache.curveTypes = await this.loadCurveTypesData();
            this.cache.calibrationHistory = await this.loadCalibrationHistory();
        } catch (error) {
            console.warn('API数据加载失败，使用模拟数据:', error);
            this.loadMockData();
        }
    },

    /**
     * 加载泵数据
     */
    async loadPumpsData() {
        return [
            { id: 'A-01', name: '泵站A-01', station: 'A', status: 'online', efficiency: 87.2 },
            { id: 'A-02', name: '泵站A-02', station: 'A', status: 'calibrating', efficiency: 84.8 },
            { id: 'B-01', name: '泵站B-01', station: 'B', status: 'completed', efficiency: 91.5 },
            { id: 'B-02', name: '泵站B-02', station: 'B', status: 'online', efficiency: 85.1 }
        ];
    },

    /**
     * 加载曲线类型数据
     */
    async loadCurveTypesData() {
        return [
            { id: 'hq', name: 'H-Q 扬程-流量曲线', description: '泵的扬程与流量关系曲线' },
            { id: 'etaq', name: 'η-Q 效率-流量曲线', description: '泵的效率与流量关系曲线' },
            { id: 'nq', name: 'N-Q 功率-流量曲线', description: '泵的功率与流量关系曲线' }
        ];
    },

    /**
     * 加载校准历史
     */
    async loadCalibrationHistory() {
        const now = new Date();
        return [
            {
                id: 1,
                time: new Date(now - 4 * 60 * 1000),
                action: '🎯 效率-流量曲线校准完成',
                details: '算法: 随机森林 | R²: 0.89 → 0.94 | 提升: +58%'
            }
        ];
    },

    /**
     * 加载模拟数据
     */
    loadMockData() {
        this.cache.precisionData = {
            maxR2: 0.943,
            avgR2: 0.897,
            minR2: 0.653,
            improvement: 28
        };

        this.cache.rlsParameters = {
            alpha: { value: 1.02, uncertainty: 0.003, status: 'stable' },
            beta: { value: 0.98, uncertainty: 0.005, status: 'stable' },
            cQ: { value: 1.035, uncertainty: 0.008, status: 'adjusting' },
            bQ: { value: -1.2, uncertainty: 0.4, status: 'stable' }
        };

        this.updatePrecisionDisplay();
        this.updateRLSParametersDisplay();
    },

    /**
     * 初始化图表
     */
    initCharts() {
        this.initCurveComparisonChart();
        this.initPrecisionTrendChart();
        this.initRLSChart();
    },

    /**
     * 初始化曲线对比图表
     */
    initCurveComparisonChart() {
        const canvas = document.getElementById('curveComparisonChart');
        if (!canvas) return;

        const config = {
            type: 'line',
            data: {
                labels: ['0', '200', '400', '600', '800', '1000', '1200'],
                datasets: [{
                    label: '神经网络拟合',
                    data: [45, 42, 38, 33, 27, 20, 12],
                    borderColor: '#e74c3c',
                    backgroundColor: 'rgba(231, 76, 60, 0.1)'
                }, {
                    label: '实测数据点',
                    data: [44.5, 41.2, 37.8, 32.1, 26.3, 19.5, 11.2],
                    borderColor: '#3498db',
                    type: 'scatter',
                    pointRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: 'H-Q曲线算法对比' }
                }
            }
        };

        PumpSystem.ChartManager.createChart('curveComparisonChart', config);
    },

    /**
     * 初始化精度追踪图表
     */
    initPrecisionTrendChart() {
        const canvas = document.getElementById('precisionTrendChart');
        if (!canvas) return;

        const config = {
            type: 'line',
            data: {
                labels: Array.from({ length: 24 }, (_, i) => `${i}:00`),
                datasets: [{
                    label: 'R² 值',
                    data: Array.from({ length: 24 }, () => 0.85 + Math.random() * 0.15),
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: '24小时精度趋势' }
                }
            }
        };

        PumpSystem.ChartManager.createChart('precisionTrendChart', config);
    },

    /**
     * 初始化RLS图表
     */
    initRLSChart() {
        const container = document.getElementById('rlsChart');
        if (!container) return;

        const option = {
            title: { text: 'RLS参数实时变化', left: 'center' },
            tooltip: { trigger: 'axis' },
            legend: { bottom: 0, data: ['α', 'β', 'C_Q'] },
            xAxis: {
                type: 'category',
                data: Array.from({ length: 20 }, (_, i) => `T-${19 - i}`)
            },
            yAxis: { type: 'value', min: 0.95, max: 1.05 },
            series: [{
                name: 'α', type: 'line', smooth: true,
                data: Array.from({ length: 20 }, () => 0.98 + Math.random() * 0.06)
            }, {
                name: 'β', type: 'line', smooth: true,
                data: Array.from({ length: 20 }, () => 0.98 + Math.random() * 0.06)
            }]
        };

        PumpSystem.ChartManager.createEChart('rlsChart', option);
    },

    /**
     * 初始化泵查询模块
     */
    initPumpQueryModule() {
        this.updatePumpList();
        this.updateCurveTypeList();
    },

    /**
     * 更新泵列表
     */
    updatePumpList() {
        const container = document.getElementById('pumpListContainer');
        if (!container) return;

        const pumpsHTML = this.cache.pumps.map(pump => `
            <div class="pump-item" data-pump-id="${pump.id}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-weight: bold; color: #2c3e50;">${pump.name}</div>
                        <div style="font-size: 0.85rem; color: #666;">效率: ${pump.efficiency}%</div>
                    </div>
                    <div class="status-indicator ${pump.status}"></div>
                </div>
            </div>
        `).join('');

        container.innerHTML = pumpsHTML;

        container.querySelectorAll('.pump-item').forEach(item => {
            item.addEventListener('click', (e) => {
                this.selectPump(e.currentTarget.dataset.pumpId);
            });
        });
    },

    /**
     * 更新曲线类型列表
     */
    updateCurveTypeList() {
        const container = document.getElementById('curveTypeContainer');
        if (!container) return;

        const curveTypesHTML = this.cache.curveTypes.map(type => `
            <div class="curve-type-item" data-curve-type="${type.id}">
                <div style="font-weight: bold; color: #2c3e50; margin-bottom: 5px;">${type.name}</div>
                <div style="font-size: 0.8rem; color: #666;">${type.description}</div>
            </div>
        `).join('');

        container.innerHTML = curveTypesHTML;

        container.querySelectorAll('.curve-type-item').forEach(item => {
            item.addEventListener('click', (e) => {
                this.selectCurveType(e.currentTarget.dataset.curveType);
            });
        });
    },

    /**
     * 开始实时数据更新
     */
    startRealTimeUpdates() {
        PumpSystem.RealTimeManager.startPolling('calibration-monitor', () => {
            this.updateRealTimeData();
        }, this.config.updateInterval);
    },

    /**
     * 更新实时数据
     */
    updateRealTimeData() {
        this.updatePrecisionMetrics();
        this.updateRLSParameters();
        this.generateRealTimeLog();
    },

    /**
     * 更新精度指标
     */
    updatePrecisionMetrics() {
        const precision = this.cache.precisionData;
        if (precision) {
            precision.maxR2 = Math.min(1.0, precision.maxR2 + (Math.random() - 0.5) * 0.01);
            precision.avgR2 = Math.min(1.0, precision.avgR2 + (Math.random() - 0.5) * 0.005);
            this.updatePrecisionDisplay();
        }
    },

    /**
     * 更新精度显示
     */
    updatePrecisionDisplay() {
        const precision = this.cache.precisionData;
        if (!precision) return;

        const elements = {
            maxR2: document.querySelector('.precision-stat:nth-child(1) .stat-value'),
            avgR2: document.querySelector('.precision-stat:nth-child(2) .stat-value'),
            minR2: document.querySelector('.precision-stat:nth-child(3) .stat-value'),
            improvement: document.querySelector('.precision-stat:nth-child(4) .stat-value')
        };

        if (elements.maxR2) elements.maxR2.textContent = precision.maxR2.toFixed(3);
        if (elements.avgR2) elements.avgR2.textContent = precision.avgR2.toFixed(3);
        if (elements.minR2) elements.minR2.textContent = precision.minR2.toFixed(3);
        if (elements.improvement) elements.improvement.textContent = `+${precision.improvement}%`;
    },

    /**
     * 更新RLS参数
     */
    updateRLSParameters() {
        const params = this.cache.rlsParameters;
        if (!params) return;

        Object.keys(params).forEach(key => {
            const param = params[key];
            if (param.uncertainty) {
                const change = (Math.random() - 0.5) * param.uncertainty * 0.1;
                param.value += change;
            }
        });

        this.updateRLSParametersDisplay();
    },

    /**
     * 更新RLS参数显示
     */
    updateRLSParametersDisplay() {
        const params = this.cache.rlsParameters;
        if (!params) return;

        const grid = document.querySelector('.parameter-grid');
        if (!grid) return;

        const paramElements = [
            { key: 'alpha', label: '功率分摊指数 α' },
            { key: 'beta', label: '频率分摊指数 β' },
            { key: 'cQ', label: '流量缩放系数 C_Q' },
            { key: 'bQ', label: '流量偏置 b_Q' }
        ];

        paramElements.forEach((param, index) => {
            const element = grid.children[index];
            if (element && params[param.key]) {
                const valueElement = element.querySelector('.param-value');
                if (valueElement) {
                    const value = params[param.key].value.toFixed(3);
                    const uncertainty = params[param.key].uncertainty ?
                        `±${params[param.key].uncertainty.toFixed(3)}` : '';
                    valueElement.textContent = `${value} ${uncertainty}`;
                }
            }
        });
    },

    /**
     * 生成实时日志
     */
    generateRealTimeLog() {
        const messages = [
            '[INFO] 泵站A-02 参数收敛检测，连续15次变化 < 0.01',
            '[SUCCESS] 泵站B-01 RLS校准完成，最终精度: R²=0.94',
            '[INFO] 泵站A-01 校准完成，总精度提升: 68.2%',
            '[WARN] 泵站C-01 数据质量检查发现异常值'
        ];

        const message = messages[Math.floor(Math.random() * messages.length)];
        const logEntry = {
            id: PumpSystem.Utils.generateId('log'),
            timestamp: new Date(),
            message: message,
            level: message.includes('[SUCCESS]') ? 'success' :
                message.includes('[WARN]') ? 'warn' : 'info'
        };

        this.addRealTimeLog(logEntry);
    },

    /**
     * 添加实时日志
     */
    addRealTimeLog(logEntry) {
        const logContainer = document.getElementById('realTimeLogContent');
        if (!logContainer) return;

        const logElement = document.createElement('div');
        logElement.className = 'log-item';
        logElement.innerHTML = `
            <div class="log-time">${PumpSystem.Utils.formatTime(logEntry.timestamp)}</div>
            <div class="log-message">${logEntry.message}</div>
        `;

        logContainer.insertBefore(logElement, logContainer.firstChild);

        const logItems = logContainer.children;
        if (logItems.length > 20) {
            logContainer.removeChild(logItems[logItems.length - 1]);
        }
    },

    /**
     * 启动校准
     */
    async startCalibration() {
        if (this.state.isCalibrating) {
            PumpSystem.Notification.warning('校准已在进行中');
            return;
        }

        this.state.isCalibrating = true;
        PumpSystem.Notification.info('开始校准过程...');

        setTimeout(() => {
            this.state.isCalibrating = false;
            PumpSystem.Notification.success('校准完成！');
        }, 5000);
    },

    /**
     * 选择校准策略
     */
    selectCalibrationStrategy(strategy) {
        this.state.currentStrategy = strategy;

        document.querySelectorAll('.strategy-card').forEach(card => {
            card.classList.toggle('active', card.dataset.strategy === strategy);
        });

        PumpSystem.Notification.info(`已选择校准策略: ${strategy}`);
    },

    /**
     * 切换曲线类型
     */
    switchCurveType(curveType) {
        this.state.currentCurveType = curveType;
    },

    /**
     * 选择泵设备
     */
    selectPump(pumpId) {
        if (!this.state.selectedPumps.includes(pumpId)) {
            this.state.selectedPumps.push(pumpId);
        } else {
            this.state.selectedPumps = this.state.selectedPumps.filter(id => id !== pumpId);
        }

        this.updatePumpSelection();
    },

    /**
     * 更新泵选择状态
     */
    updatePumpSelection() {
        document.querySelectorAll('.pump-item').forEach(item => {
            const isSelected = this.state.selectedPumps.includes(item.dataset.pumpId);
            item.classList.toggle('selected', isSelected);
        });
    },

    /**
     * 更新UI状态
     */
    updateUIState() {
        this.updatePrecisionDisplay();
        this.updateRLSParametersDisplay();
    }
};

// 全局函数供HTML调用
window.startCalibration = () => CalibrationMonitor.startCalibration();
window.pauseCalibration = () => PumpSystem.Notification.info('校准已暂停');
window.stopCalibration = () => PumpSystem.Notification.warning('校准已停止');
window.exportCalibrationReport = () => {
    const reportData = {
        timestamp: new Date().toISOString(),
        calibrationHistory: CalibrationMonitor.cache.calibrationHistory,
        precisionData: CalibrationMonitor.cache.precisionData
    };
    PumpSystem.DataExporter.exportJSON(reportData, 'calibration_report');
    PumpSystem.Notification.success('校准报告导出成功');
};
window.updateCurveComparison = (value) => CalibrationMonitor.switchCurveType(value);
window.filterCalibrationLogs = (filter) => console.log('筛选日志:', filter);
window.switchQueryTab = (tab) => {
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });

    const activeTab = document.getElementById(`${tab}-tab`);
    const activeBtn = document.querySelector(`[onclick="switchQueryTab('${tab}')"]`);

    if (activeTab) activeTab.classList.add('active');
    if (activeBtn) activeBtn.classList.add('active');
};

// 暴露到全局
window.CalibrationMonitor = CalibrationMonitor;
