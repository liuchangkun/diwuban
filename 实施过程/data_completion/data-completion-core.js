/**
 * 数据补充管道监控系统 - 核心JavaScript逻辑
 * 基于共享资源库PumpSystem，提供管道监控和数据分析功能
 */

// 数据补充管道命名空间
window.DataPipeline = {
    // 配置和状态
    config: {
        pipelineSteps: ['ingest', 'validate', 'gate', 'select', 'qcalc', 'hcalc', 'etacalc', 'persist'],
        currentStep: 'gate',
        currentIndex: 2,
        refreshInterval: 5000,
        maxLogEntries: 100
    },

    // 数据状态
    state: {
        totalRecords: 1247,
        processedRecords: 1213,
        errorRecords: 34,
        currentStrategy: 'ffill',
        isMonitoring: true,
        isPipelineRunning: true
    },

    // 图表实例
    charts: {},

    // 初始化系统
    init() {
        console.log('初始化数据补充管道监控系统...');
        this.initializeCharts();
        this.initializeEventListeners();
        this.loadInitialData();
        this.startRealTimeUpdates();
        this.generateInitialLogs();
        console.log('数据补充管道监控系统初始化完成');
    },

    // 初始化图表
    initializeCharts() {
        this.initQualityTrendChart();
        this.initAccuracyTrendChart();
        this.initCalibrationChart();
        this.initResidualChart();
        this.initDataflowChart();
    },

    // 初始化质量趋势图表
    initQualityTrendChart() {
        const ctx = document.querySelector('#qualityTrendChart canvas');
        if (!ctx) return;

        this.charts.qualityTrend = PumpSystem.ChartManager.createChart(ctx, {
            type: 'line',
            data: {
                labels: this.generateTimeLabels(24),
                datasets: [{
                    label: '数据质量评分',
                    data: this.generateMockData(24, 80, 95),
                    borderColor: '#2196f3',
                    backgroundColor: 'rgba(33, 150, 243, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: '24小时质量趋势' }
                },
                scales: {
                    y: { min: 70, max: 100 }
                }
            }
        });
    },

    // 初始化精度趋势图表
    initAccuracyTrendChart() {
        const ctx = document.querySelector('#accuracyTrendChart canvas');
        if (!ctx) return;

        this.charts.accuracyTrend = PumpSystem.ChartManager.createChart(ctx, {
            type: 'line',
            data: {
                labels: this.generateTimeLabels(12),
                datasets: [
                    {
                        label: '扬程RMSE',
                        data: this.generateMockData(12, 1.0, 1.8),
                        borderColor: '#4caf50',
                        yAxisID: 'y'
                    },
                    {
                        label: '效率MAE',
                        data: this.generateMockData(12, 2.0, 4.0),
                        borderColor: '#ff9800',
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { type: 'linear', display: true, position: 'left' },
                    y1: { type: 'linear', display: true, position: 'right', grid: { drawOnChartArea: false } }
                }
            }
        });
    },

    // 初始化校准图表
    initCalibrationChart() {
        const ctx = document.querySelector('#calibrationChart canvas');
        if (!ctx) return;

        this.charts.calibration = PumpSystem.ChartManager.createChart(ctx, {
            type: 'line',
            data: {
                labels: this.generateTimeLabels(20, 'minute'),
                datasets: [
                    {
                        label: '流量系数 C_Q',
                        data: this.generateConvergenceData(20, 1.035, 0.008),
                        borderColor: '#2196f3'
                    },
                    {
                        label: '扬程系数 C_H',
                        data: this.generateConvergenceData(20, 1.023, 0.005),
                        borderColor: '#4caf50'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: '参数收敛过程' }
                }
            }
        });
    },

    // 初始化残差图表
    initResidualChart() {
        const ctx = document.querySelector('#residualChart canvas');
        if (!ctx) return;

        const residualData = this.generateResidualData(100);
        this.charts.residual = PumpSystem.ChartManager.createChart(ctx, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: '残差分布',
                    data: residualData,
                    backgroundColor: residualData.map(d =>
                        Math.abs(d.y) > 2 ? '#f44336' :
                            Math.abs(d.y) > 1 ? '#ff9800' : '#4caf50'
                    ),
                    pointRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: '残差分析 (异常点标红)' }
                }
            }
        });
    },

    // 初始化数据流图表
    initDataflowChart() {
        const ctx = document.querySelector('#dataflowChart canvas');
        if (!ctx) return;

        this.charts.dataflow = PumpSystem.ChartManager.createChart(ctx, {
            type: 'line',
            data: {
                labels: this.generateTimeLabels(10, 'second'),
                datasets: [
                    {
                        label: '输入速率',
                        data: this.generateMockData(10, 240, 250),
                        borderColor: '#2196f3',
                        fill: false
                    },
                    {
                        label: '处理速率',
                        data: this.generateMockData(10, 235, 245),
                        borderColor: '#4caf50',
                        fill: false
                    },
                    {
                        label: '输出速率',
                        data: this.generateMockData(10, 230, 240),
                        borderColor: '#ff9800',
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: '实时数据流监控 (记录/秒)' }
                }
            }
        });
    },

    // 初始化事件监听器
    initializeEventListeners() {
        // 流程步骤点击
        document.querySelectorAll('.flow-step').forEach(step => {
            step.addEventListener('click', () => {
                const stepName = step.dataset.step;
                this.showStepDetails(stepName);
            });
        });

        // 策略选择
        document.querySelectorAll('.strategy-card').forEach(card => {
            card.addEventListener('click', () => {
                if (!card.classList.contains('disabled')) {
                    this.selectStrategy(card.dataset.strategy);
                }
            });
        });

        // 日志过滤
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.filterLogs(btn.dataset.level);
            });
        });
    },

    // 加载初始数据
    loadInitialData() {
        this.updatePipelineStatus();
        this.updateQualityMetrics();
        this.updateAccuracyMetrics();
        this.updateCalibrationProgress();
    },

    // 开始实时更新
    startRealTimeUpdates() {
        setInterval(() => {
            if (this.state.isMonitoring) {
                this.updateRealTimeData();
                this.simulatePipelineProgress();
                this.updateCharts();

                // 随机生成新日志
                if (Math.random() < 0.3) {
                    this.generateRandomLog();
                }
            }
        }, this.config.refreshInterval);
    },

    // 更新实时数据
    updateRealTimeData() {
        // 模拟数据变化
        this.state.processedRecords += Math.floor(Math.random() * 10);
        if (Math.random() < 0.1) {
            this.state.errorRecords += 1;
        }

        // 更新显示
        this.updateDataflowMetrics();
        this.updateQualityScore();
    },

    // 模拟管道进度
    simulatePipelineProgress() {
        if (this.state.isPipelineRunning && Math.random() < 0.1) {
            const currentIndex = this.config.currentIndex;
            if (currentIndex < this.config.pipelineSteps.length - 1) {
                this.config.currentIndex++;
                this.config.currentStep = this.config.pipelineSteps[this.config.currentIndex];
                this.updatePipelineVisuals();
                this.addLogEntry('SUCCESS', `${this.config.currentStep}阶段完成`);
            }
        }
    },

    // 更新管道视觉状态
    updatePipelineVisuals() {
        document.querySelectorAll('.flow-step').forEach((step, index) => {
            step.classList.remove('active', 'completed', 'pending');

            if (index < this.config.currentIndex) {
                step.dataset.status = 'completed';
                step.classList.add('completed');
            } else if (index === this.config.currentIndex) {
                step.dataset.status = 'active';
                step.classList.add('active');
            } else {
                step.dataset.status = 'pending';
                step.classList.add('pending');
            }
        });
    },

    // 选择策略
    selectStrategy(strategy) {
        document.querySelectorAll('.strategy-card').forEach(card => {
            card.classList.remove('active');
        });

        document.querySelector(`[data-strategy="${strategy}"]`).classList.add('active');
        this.state.currentStrategy = strategy;
        this.updateStrategyParameters(strategy);
        this.addLogEntry('INFO', `切换到${strategy.toUpperCase()}策略`);
    },

    // 更新策略参数
    updateStrategyParameters(strategy) {
        const parameters = document.getElementById('strategyParameters');
        const strategyConfig = {
            ffill: { name: 'FFILL策略参数配置', params: ['最大填充间隔', '质量权重', '异常检测阈值'] },
            mean: { name: 'MEAN策略参数配置', params: ['时间窗口', '权重衰减', '置信区间'] },
            reg: { name: 'REG策略参数配置', params: ['模型复杂度', '正则化强度', '验证比例'] },
            curve: { name: 'CURVE策略参数配置', params: ['曲线阶数', '平滑因子', '外推范围'] }
        };

        const config = strategyConfig[strategy];
        if (config && parameters) {
            parameters.querySelector('h4').textContent = `📋 ${config.name}`;
        }
    },

    // 生成初始日志
    generateInitialLogs() {
        const initialLogs = [
            { level: 'INFO', message: '数据补充管道系统启动成功', time: new Date(Date.now() - 300000) },
            { level: 'SUCCESS', message: '数据摄取完成：读取1,247条记录', time: new Date(Date.now() - 240000) },
            { level: 'SUCCESS', message: '数据验证通过：质量评分85.2%', time: new Date(Date.now() - 180000) },
            { level: 'INFO', message: '检测到2.3小时数据缺失，启用FFILL策略', time: new Date(Date.now() - 120000) },
            { level: 'WARN', message: '发现3个异常数据点，已自动标记', time: new Date(Date.now() - 60000) },
            { level: 'INFO', message: '质量门槛评估中，当前策略：FFILL', time: new Date() }
        ];

        initialLogs.forEach(log => {
            this.addLogEntry(log.level, log.message, log.time);
        });
    },

    // 添加日志条目
    addLogEntry(level, message, timestamp = new Date()) {
        const logContainer = document.getElementById('logContainer');
        if (!logContainer) return;

        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry';
        logEntry.innerHTML = `
            <div class="log-timestamp">${PumpSystem.Utils.formatTime(timestamp)}</div>
            <div class="log-level ${level}">${level}</div>
            <div class="log-message">${message}</div>
        `;

        logContainer.insertBefore(logEntry, logContainer.firstChild);

        // 限制日志数量
        const entries = logContainer.querySelectorAll('.log-entry');
        if (entries.length > this.config.maxLogEntries) {
            entries[entries.length - 1].remove();
        }
    },

    // 生成随机日志
    generateRandomLog() {
        const messages = [
            'C_Q参数收敛：当前值1.035±0.008',
            '扬程计算完成：RMSE降至1.2m',
            '效率计算精度提升：MAE=2.8%',
            '数据流处理正常：238记录/秒',
            '异常点检测：发现1个离群值',
            '参数校准进度：C_H收敛度92%'
        ];

        const levels = ['INFO', 'SUCCESS', 'WARN'];
        const level = levels[Math.floor(Math.random() * levels.length)];
        const message = messages[Math.floor(Math.random() * messages.length)];

        this.addLogEntry(level, message);
    },

    // 过滤日志
    filterLogs(level) {
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.remove('active');
        });

        document.querySelector(`[data-level="${level}"]`).classList.add('active');

        const entries = document.querySelectorAll('.log-entry');
        entries.forEach(entry => {
            const entryLevel = entry.querySelector('.log-level').textContent;
            entry.style.display = (level === 'all' || entryLevel === level) ? 'flex' : 'none';
        });
    },

    // 显示步骤详情
    showStepDetails(stepName) {
        const stepDetails = {
            ingest: { title: '数据摄取', desc: '从fact_measurements表读取原始数据，支持增量和全量模式' },
            validate: { title: '数据验证', desc: '执行数据质量检查，包括范围验证、类型检查和异常值检测' },
            gate: { title: '质量门槛', desc: '评估数据缺失程度，选择最适合的补齐策略' },
            select: { title: '数据选择', desc: '基于质量评分筛选高质量数据用于后续计算' },
            qcalc: { title: '流量计算', desc: '使用pump_flow_rate进行流量分摊计算' },
            hcalc: { title: '扬程计算', desc: '基于压差传感器数据和流体密度计算扬程' },
            etacalc: { title: '效率计算', desc: '使用公式η=(ρ·g·Q·H)/(P·1000)计算效率' },
            persist: { title: '数据持久化', desc: '将计算结果保存到compute_runs表' }
        };

        const detail = stepDetails[stepName];
        if (detail) {
            PumpSystem.Utils.showToast(`${detail.title}: ${detail.desc}`, 'info');
        }
    },

    // 工具函数：生成时间标签
    generateTimeLabels(count, unit = 'hour') {
        const labels = [];
        const now = new Date();

        for (let i = count - 1; i >= 0; i--) {
            const time = new Date(now);
            if (unit === 'hour') {
                time.setHours(time.getHours() - i);
                labels.push(PumpSystem.Utils.formatTime(time, 'HH:mm'));
            } else if (unit === 'minute') {
                time.setMinutes(time.getMinutes() - i);
                labels.push(PumpSystem.Utils.formatTime(time, 'mm:ss'));
            } else if (unit === 'second') {
                time.setSeconds(time.getSeconds() - i * 10);
                labels.push(PumpSystem.Utils.formatTime(time, 'ss'));
            }
        }

        return labels;
    },

    // 工具函数：生成模拟数据
    generateMockData(count, min, max) {
        return Array.from({ length: count }, () =>
            min + Math.random() * (max - min)
        );
    },

    // 工具函数：生成收敛数据
    generateConvergenceData(count, target, noise) {
        const data = [];
        for (let i = 0; i < count; i++) {
            const convergence = Math.exp(-i * 0.1);
            const value = target + (Math.random() - 0.5) * noise * convergence;
            data.push(Number(value.toFixed(4)));
        }
        return data;
    },

    // 工具函数：生成残差数据
    generateResidualData(count) {
        return Array.from({ length: count }, (_, i) => ({
            x: i,
            y: (Math.random() - 0.5) * 4 * Math.exp(-i * 0.01)
        }));
    },

    // 更新图表
    updateCharts() {
        // 更新数据流图表
        if (this.charts.dataflow) {
            const newData = [
                this.generateMockData(1, 240, 250)[0],
                this.generateMockData(1, 235, 245)[0],
                this.generateMockData(1, 230, 240)[0]
            ];

            PumpSystem.ChartManager.addDataPoint(this.charts.dataflow, newData, 10);
        }
    },

    // API方法
    startPipeline() {
        this.state.isPipelineRunning = true;
        this.addLogEntry('INFO', '数据补充管道已启动');
        PumpSystem.Utils.showToast('管道已启动', 'success');
    },

    pausePipeline() {
        this.state.isPipelineRunning = false;
        this.addLogEntry('WARN', '数据补充管道已暂停');
        PumpSystem.Utils.showToast('管道已暂停', 'warning');
    },

    resetPipeline() {
        this.config.currentIndex = 0;
        this.config.currentStep = this.config.pipelineSteps[0];
        this.updatePipelineVisuals();
        this.addLogEntry('INFO', '管道已重置到初始状态');
        PumpSystem.Utils.showToast('管道已重置', 'info');
    },

    exportReport() {
        const reportData = {
            timestamp: new Date().toISOString(),
            pipeline_status: {
                current_step: this.config.currentStep,
                total_records: this.state.totalRecords,
                processed_records: this.state.processedRecords,
                error_records: this.state.errorRecords
            },
            quality_metrics: {
                overall_score: 85.2,
                completeness: 96.8,
                accuracy: 89.2,
                consistency: 73.5
            },
            computation_metrics: {
                head_rmse: 1.2,
                efficiency_mae: 2.8,
                flow_error: 3.5,
                overall_accuracy: 94.2
            },
            current_strategy: this.state.currentStrategy
        };

        PumpSystem.DataExporter.exportJSON(reportData, 'data_pipeline_report');
        this.addLogEntry('SUCCESS', '管道监控报告已导出');
    },

    exportLogs() {
        const logs = Array.from(document.querySelectorAll('.log-entry')).map(entry => ({
            timestamp: entry.querySelector('.log-timestamp').textContent,
            level: entry.querySelector('.log-level').textContent,
            message: entry.querySelector('.log-message').textContent
        }));

        PumpSystem.DataExporter.exportJSON({ logs, export_time: new Date().toISOString() }, 'pipeline_logs');
        this.addLogEntry('SUCCESS', '日志数据已导出');
    },

    optimizeStrategy() {
        const strategies = ['ffill', 'mean', 'reg', 'curve'];
        const scores = [0.89, 0.82, 0.95, 0.93];
        const availability = [true, true, false, false];

        let bestStrategy = 'ffill';
        let bestScore = 0;

        strategies.forEach((strategy, index) => {
            if (availability[index] && scores[index] > bestScore) {
                bestScore = scores[index];
                bestStrategy = strategy;
            }
        });

        this.selectStrategy(bestStrategy);
        PumpSystem.Utils.showToast(`推荐策略: ${bestStrategy.toUpperCase()} (评分: ${bestScore})`, 'info');
    }
};

// 页面卸载时清理资源
window.addEventListener('beforeunload', function () {
    if (window.DataPipeline && window.DataPipeline.charts) {
        Object.values(window.DataPipeline.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
    }
});
