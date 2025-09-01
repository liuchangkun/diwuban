/**
 * 83种特性曲线拟合展示系统 - 核心JavaScript逻辑
 * 基于共享资源库PumpSystem，提供曲线展示和多算法对比分析功能
 */

// 曲线展示系统命名空间
window.CurvesShowcase = {
    // 配置和状态
    config: {
        curveCount: 83,
        algorithmTypes: ['neural_network', 'random_forest', 'gaussian_process', 'polynomial'],
        accuracyLevels: ['excellent', 'good', 'average'],
        viewModes: ['overview', 'comparison', 'analysis', 'performance'],
        refreshInterval: 3000,
        maxDataPoints: 100
    },

    // 数据状态
    state: {
        currentViewMode: 'overview',
        selectedCurves: [],
        selectedAlgorithm: 'all',
        selectedAccuracy: 'all',
        selectedCategory: 'all',
        isMonitoring: true,
        currentCurveType: 'hq'
    },

    // 图表实例
    charts: {},

    // 曲线数据
    curvesData: {},

    // 初始化系统
    init() {
        console.log('初始化83种特性曲线拟合展示系统...');
        this.initializeData();
        this.initializeCharts();
        this.initializeEventListeners();
        this.loadInitialView();
        this.startRealTimeUpdates();
        console.log('曲线展示系统初始化完成');
    },

    // 初始化数据
    initializeData() {
        // 生成83种曲线的模拟数据
        this.curvesData = this.generateCurvesData();
        this.updatePerformanceGrid();
        this.updateCurveTree();
    },

    // 生成曲线数据
    generateCurvesData() {
        const categories = {
            basic: ['H-Q曲线', '效率-Q曲线', '功率-Q曲线', 'NPSH-Q曲线'],
            electrical: ['电机功率曲线', '电流-Q曲线', '功率因数曲线'],
            coordination: ['泵组协调曲线', '变频调速曲线', '并联运行曲线'],
            temperature: ['温度-效率曲线', '粘度-性能曲线'],
            vibration: ['振动-频率曲线', '噪音-流量曲线']
        };

        const curves = {};
        let curveId = 1;

        Object.entries(categories).forEach(([category, curveTypes]) => {
            curveTypes.forEach(curveType => {
                for (let i = 1; i <= Math.ceil(83 / Object.values(categories).flat().length); i++) {
                    if (curveId > 83) return;

                    const curve = {
                        id: `curve_${curveId}`,
                        name: `${curveType}_${i}`,
                        category: category,
                        type: curveType,
                        algorithm: this.config.algorithmTypes[Math.floor(Math.random() * this.config.algorithmTypes.length)],
                        accuracy: Math.random() * 0.3 + 0.7, // 0.7-1.0
                        r2Score: Math.random() * 0.3 + 0.7,
                        rmse: Math.random() * 2 + 0.5,
                        trainingTime: Math.random() * 1000 + 100,
                        dataPoints: Math.floor(Math.random() * 500 + 100),
                        physicsConstraints: {
                            monotonicity: Math.random() > 0.1,
                            efficiencyRange: Math.random() > 0.05,
                            energyBalance: Math.random() > 0.08,
                            similarityLaw: Math.random() > 0.15
                        }
                    };

                    // 生成曲线数据点
                    curve.dataPoints = this.generateCurvePoints(curve.type);
                    curves[curve.id] = curve;
                    curveId++;
                }
            });
        });

        return curves;
    },

    // 生成曲线数据点
    generateCurvePoints(curveType) {
        const points = [];
        const numPoints = 50;

        for (let i = 0; i <= numPoints; i++) {
            const x = i / numPoints;
            let y;

            switch (curveType.toLowerCase()) {
                case 'h-q曲线':
                    y = 1 - 0.8 * Math.pow(x, 2); // 扬程-流量关系
                    break;
                case '效率-q曲线':
                    y = 4 * x * (1 - x); // 效率曲线
                    break;
                case '功率-q曲线':
                    y = x + 0.5 * Math.pow(x, 2); // 功率曲线
                    break;
                default:
                    y = Math.sin(Math.PI * x); // 默认正弦曲线
            }

            // 添加噪声
            y += (Math.random() - 0.5) * 0.1;
            points.push({ x: x * 100, y: Math.max(0, y) });
        }

        return points;
    },

    // 初始化图表
    initializeCharts() {
        this.initMainComparisonChart();
        this.initAlgorithmComparisonChart();
        this.initAccuracyDistributionChart();
        this.initRealtimeMonitorChart();
    },

    // 初始化主对比图表
    initMainComparisonChart() {
        const ctx = document.getElementById('mainComparisonChart');
        if (!ctx) return;

        this.charts.mainComparison = PumpSystem.ChartManager.createChart(ctx, {
            type: 'line',
            data: {
                datasets: []
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: '曲线对比分析' },
                    legend: { position: 'top' }
                },
                scales: {
                    x: { title: { display: true, text: '流量 (m³/h)' } },
                    y: { title: { display: true, text: '扬程 (m)' } }
                }
            }
        });

        this.updateMainChart();
    },

    // 初始化算法对比图表
    initAlgorithmComparisonChart() {
        const ctx = document.getElementById('algorithmComparisonChart');
        if (!ctx) return;

        const algorithmData = {
            labels: ['神经网络', '随机森林', '高斯过程', '多项式', 'SVM', 'XGBoost', '集成算法'],
            datasets: [{
                label: 'R²评分',
                data: [0.943, 0.891, 0.876, 0.823, 0.845, 0.902, 0.925],
                backgroundColor: [
                    '#4caf50', '#2196f3', '#ff9800', '#9c27b0',
                    '#f44336', '#00bcd4', '#795548'
                ],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        };

        this.charts.algorithmComparison = PumpSystem.ChartManager.createChart(ctx, {
            type: 'doughnut',
            data: algorithmData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: '算法性能对比' },
                    legend: { position: 'bottom' }
                }
            }
        });
    },

    // 初始化精度分布图表
    initAccuracyDistributionChart() {
        const ctx = document.getElementById('accuracyDistributionChart');
        if (!ctx) return;

        const accuracyData = this.calculateAccuracyDistribution();

        this.charts.accuracyDistribution = PumpSystem.ChartManager.createChart(ctx, {
            type: 'histogram',
            data: {
                labels: ['0.7-0.75', '0.75-0.8', '0.8-0.85', '0.85-0.9', '0.9-0.95', '0.95-1.0'],
                datasets: [{
                    label: '曲线数量',
                    data: accuracyData,
                    backgroundColor: 'rgba(33, 150, 243, 0.7)',
                    borderColor: '#2196f3',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: '精度分布直方图' }
                },
                scales: {
                    x: { title: { display: true, text: 'R²精度范围' } },
                    y: { title: { display: true, text: '曲线数量' } }
                }
            }
        });
    },

    // 初始化实时监控图表
    initRealtimeMonitorChart() {
        const ctx = document.getElementById('realtimeMonitorChart');
        if (!ctx) return;

        this.charts.realtimeMonitor = PumpSystem.ChartManager.createChart(ctx, {
            type: 'line',
            data: {
                labels: this.generateTimeLabels(20, 'second'),
                datasets: [
                    {
                        label: '拟合速度',
                        data: this.generateMockData(20, 2.0, 2.8),
                        borderColor: '#4caf50',
                        backgroundColor: 'rgba(76, 175, 80, 0.1)',
                        fill: true
                    },
                    {
                        label: 'CPU使用率',
                        data: this.generateMockData(20, 60, 75),
                        borderColor: '#ff9800',
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: '系统实时监控' }
                },
                scales: {
                    y: { title: { display: true, text: '拟合速度 (曲线/秒)' } },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: { display: true, text: 'CPU使用率 (%)' },
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });
    },

    // 初始化事件监听器
    initializeEventListeners() {
        // 视图模式切换
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const mode = e.target.dataset.mode;
                if (mode) this.switchViewMode(mode);
            });
        });

        // 算法筛选
        document.querySelectorAll('.algorithm-tag').forEach(tag => {
            tag.addEventListener('click', (e) => {
                this.selectAlgorithm(e.target.dataset.algorithm);
            });
        });

        // 精度筛选
        document.querySelectorAll('.accuracy-tag').forEach(tag => {
            tag.addEventListener('click', (e) => {
                this.selectAccuracy(e.target.dataset.accuracy);
            });
        });

        // 搜索输入
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterCurves(e.target.value);
            });
        }

        // 分类筛选
        const categoryFilter = document.getElementById('categoryFilter');
        if (categoryFilter) {
            categoryFilter.addEventListener('change', (e) => {
                this.filterByCategory(e.target.value);
            });
        }
    },

    // 加载初始视图
    loadInitialView() {
        this.updateStatistics();
        this.updateCurveMetrics();
        this.updatePerformanceView();
    },

    // 开始实时更新
    startRealTimeUpdates() {
        setInterval(() => {
            if (this.state.isMonitoring) {
                this.updateRealtimeData();
                this.updateCharts();
            }
        }, this.config.refreshInterval);
    },

    // 更新实时数据
    updateRealtimeData() {
        // 模拟系统监控数据变化
        const newSpeed = 2.0 + Math.random() * 0.8;
        const newCpu = 60 + Math.random() * 15;

        if (this.charts.realtimeMonitor) {
            PumpSystem.ChartManager.addDataPoint(this.charts.realtimeMonitor, [newSpeed, newCpu], 20);
        }
    },

    // 切换视图模式
    switchViewMode(mode) {
        this.state.currentViewMode = mode;

        // 更新按钮状态
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-mode="${mode}"]`)?.classList.add('active');

        // 根据模式更新视图
        this.updateViewByMode(mode);
        PumpSystem.Utils.showToast(`切换到${this.getModeDisplayName(mode)}模式`, 'info');
    },

    // 获取模式显示名称
    getModeDisplayName(mode) {
        const modeNames = {
            overview: '概览',
            comparison: '对比',
            analysis: '分析',
            performance: '性能'
        };
        return modeNames[mode] || mode;
    },

    // 根据模式更新视图
    updateViewByMode(mode) {
        switch (mode) {
            case 'overview':
                this.showOverviewMode();
                break;
            case 'comparison':
                this.showComparisonMode();
                break;
            case 'analysis':
                this.showAnalysisMode();
                break;
            case 'performance':
                this.showPerformanceMode();
                break;
        }
    },

    // 显示概览模式
    showOverviewMode() {
        document.getElementById('mainTitle').textContent = '📊 曲线拟合概览';
        this.updateMainChart();
        this.updateStatistics();
    },

    // 显示对比模式
    showComparisonMode() {
        document.getElementById('mainTitle').textContent = '🔀 多算法对比分析';
        this.updateComparisonChart();
    },

    // 显示分析模式
    showAnalysisMode() {
        document.getElementById('mainTitle').textContent = '🔍 深度分析报告';
        this.updateAnalysisView();
    },

    // 显示性能模式
    showPerformanceMode() {
        document.getElementById('mainTitle').textContent = '🏆 性能评估报告';
        this.updatePerformanceView();
    },

    // 更新主图表
    updateMainChart() {
        if (!this.charts.mainComparison) return;

        const selectedCurves = this.getFilteredCurves();
        const datasets = [];

        selectedCurves.slice(0, 5).forEach((curve, index) => {
            const colors = ['#2196f3', '#4caf50', '#ff9800', '#9c27b0', '#f44336'];
            datasets.push({
                label: curve.name,
                data: curve.dataPoints,
                borderColor: colors[index],
                backgroundColor: colors[index] + '20',
                fill: false,
                tension: 0.4
            });
        });

        this.charts.mainComparison.data.datasets = datasets;
        this.charts.mainComparison.update();
    },

    // 获取筛选后的曲线
    getFilteredCurves() {
        return Object.values(this.curvesData).filter(curve => {
            // 算法筛选
            if (this.state.selectedAlgorithm !== 'all' && curve.algorithm !== this.state.selectedAlgorithm) {
                return false;
            }

            // 精度筛选
            if (this.state.selectedAccuracy !== 'all') {
                const accuracy = curve.r2Score;
                switch (this.state.selectedAccuracy) {
                    case 'excellent':
                        if (accuracy < 0.9) return false;
                        break;
                    case 'good':
                        if (accuracy < 0.8 || accuracy >= 0.9) return false;
                        break;
                    case 'average':
                        if (accuracy >= 0.8) return false;
                        break;
                }
            }

            // 分类筛选
            if (this.state.selectedCategory !== 'all' && curve.category !== this.state.selectedCategory) {
                return false;
            }

            return true;
        });
    },

    // 选择算法
    selectAlgorithm(algorithm) {
        this.state.selectedAlgorithm = algorithm;

        // 更新标签状态
        document.querySelectorAll('.algorithm-tag').forEach(tag => {
            tag.classList.remove('active');
        });
        document.querySelector(`[data-algorithm="${algorithm}"]`)?.classList.add('active');

        this.updateMainChart();
        this.updateStatistics();
    },

    // 选择精度
    selectAccuracy(accuracy) {
        this.state.selectedAccuracy = accuracy;

        // 更新标签状态
        document.querySelectorAll('.accuracy-tag').forEach(tag => {
            tag.classList.remove('active');
        });
        document.querySelector(`[data-accuracy="${accuracy}"]`)?.classList.add('active');

        this.updateMainChart();
        this.updateStatistics();
    },

    // 更新统计数据
    updateStatistics() {
        const filteredCurves = this.getFilteredCurves();
        const totalCurves = filteredCurves.length;
        const avgAccuracy = filteredCurves.reduce((sum, curve) => sum + curve.r2Score, 0) / totalCurves || 0;
        const excellentCurves = filteredCurves.filter(curve => curve.r2Score >= 0.9).length;

        // 更新统计卡片
        this.updateStatCard('.stat-card:nth-child(1) .stat-value', totalCurves.toString());
        this.updateStatCard('.stat-card:nth-child(2) .stat-value', avgAccuracy.toFixed(2));
        this.updateStatCard('.stat-card:nth-child(3) .stat-value', excellentCurves.toString());
    },

    // 更新统计卡片
    updateStatCard(selector, value) {
        const element = document.querySelector(selector);
        if (element) element.textContent = value;
    },

    // 工具函数：生成时间标签
    generateTimeLabels(count, unit = 'hour') {
        const labels = [];
        const now = new Date();

        for (let i = count - 1; i >= 0; i--) {
            const time = new Date(now);
            if (unit === 'second') {
                time.setSeconds(time.getSeconds() - i * 10);
                labels.push(PumpSystem.Utils.formatTime(time, 'mm:ss'));
            } else {
                time.setHours(time.getHours() - i);
                labels.push(PumpSystem.Utils.formatTime(time, 'HH:mm'));
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

    // 计算精度分布
    calculateAccuracyDistribution() {
        const curves = Object.values(this.curvesData);
        const bins = [0, 0, 0, 0, 0, 0]; // 对应6个区间

        curves.forEach(curve => {
            const r2 = curve.r2Score;
            if (r2 < 0.75) bins[0]++;
            else if (r2 < 0.8) bins[1]++;
            else if (r2 < 0.85) bins[2]++;
            else if (r2 < 0.9) bins[3]++;
            else if (r2 < 0.95) bins[4]++;
            else bins[5]++;
        });

        return bins;
    },

    // API方法
    exportReport() {
        const reportData = {
            timestamp: new Date().toISOString(),
            curves_summary: {
                total_curves: this.config.curveCount,
                avg_accuracy: this.calculateAverageAccuracy(),
                excellent_count: this.getExcellentCurveCount(),
                algorithm_distribution: this.getAlgorithmDistribution()
            },
            performance_metrics: this.getPerformanceMetrics(),
            physics_constraints: this.getPhysicsConstraintsResults(),
            current_filters: {
                algorithm: this.state.selectedAlgorithm,
                accuracy: this.state.selectedAccuracy,
                category: this.state.selectedCategory,
                view_mode: this.state.currentViewMode
            }
        };

        PumpSystem.DataExporter.exportJSON(reportData, 'curves_analysis_report');
        PumpSystem.Utils.showToast('曲线分析报告已导出', 'success');
    },

    refreshAnalysis() {
        this.initializeData();
        this.updateMainChart();
        this.updateStatistics();
        PumpSystem.Utils.showToast('分析数据已刷新', 'info');
    },

    // 辅助计算方法
    calculateAverageAccuracy() {
        const curves = Object.values(this.curvesData);
        return curves.reduce((sum, curve) => sum + curve.r2Score, 0) / curves.length;
    },

    getExcellentCurveCount() {
        return Object.values(this.curvesData).filter(curve => curve.r2Score >= 0.9).length;
    },

    getAlgorithmDistribution() {
        const distribution = {};
        Object.values(this.curvesData).forEach(curve => {
            distribution[curve.algorithm] = (distribution[curve.algorithm] || 0) + 1;
        });
        return distribution;
    },

    getPerformanceMetrics() {
        return {
            avg_training_time: Object.values(this.curvesData).reduce((sum, curve) => sum + curve.trainingTime, 0) / this.config.curveCount,
            avg_rmse: Object.values(this.curvesData).reduce((sum, curve) => sum + curve.rmse, 0) / this.config.curveCount,
            system_cpu_usage: 68.5,
            memory_usage: 1.2
        };
    },

    getPhysicsConstraintsResults() {
        const results = { passed: 0, warning: 0, failed: 0 };
        Object.values(this.curvesData).forEach(curve => {
            const constraints = curve.physicsConstraints;
            const passRate = Object.values(constraints).filter(Boolean).length / Object.keys(constraints).length;
            if (passRate >= 0.95) results.passed++;
            else if (passRate >= 0.8) results.warning++;
            else results.failed++;
        });
        return results;
    }
};

// 页面卸载时清理资源
window.addEventListener('beforeunload', function () {
    if (window.CurvesShowcase && window.CurvesShowcase.charts) {
        Object.values(window.CurvesShowcase.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
    }
});
