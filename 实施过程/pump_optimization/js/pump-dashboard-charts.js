/**
 * 泵站优化控制台 - 图表管理模块
 * 负责初始化和管理所有图表组件
 */

// 图表管理器
window.PumpDashboardCharts = {
    // 图表实例存储
    charts: {},

    /**
     * 初始化所有图表
     */
    initAllCharts() {
        console.log('📈 初始化所有图表...');

        try {
            this.initStationPerformanceChart();
            this.initEnergyTrendChart();
            this.initHealthTrendChart();
            this.initProcessAnalysisChart();
            this.initEconomicAnalysisChart();
            this.initDiagnosticRadarChart();
            this.initNewPerformanceCharts();

            console.log('✅ 图表初始化完成');
        } catch (error) {
            console.error('❌ 图表初始化失败:', error);
            PumpSystem.Notification.error(`图表初始化失败: ${error.message}`);
        }
    },

    /**
     * 初始化新增性能图表
     */
    initNewPerformanceCharts() {
        // 在这里添加新的图表初始化
        this.initEfficiencyHistoryChart();
        this.initPowerConsumptionChart();
        this.initPumpLoadDistributionChart();
        this.initCorrelationMatrixChart();
    },

    /**
     * 初始化站点性能图表
     */
    initStationPerformanceChart() {
        const ctx = document.getElementById('stationPerformanceChart');
        if (!ctx) return;

        this.charts.stationPerformance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: this.generateTimeLabels(24, 'hour'),
                datasets: [
                    {
                        label: '泵站A效率',
                        data: this.generateMockData(24, 80, 90),
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: '泵站B效率',
                        data: this.generateMockData(24, 75, 85),
                        borderColor: '#27ae60',
                        backgroundColor: 'rgba(39, 174, 96, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: '泵站C效率',
                        data: this.generateMockData(24, 70, 80),
                        borderColor: '#f39c12',
                        backgroundColor: 'rgba(243, 156, 18, 0.1)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    title: {
                        display: true,
                        text: '泵站效率趋势'
                    },
                    legend: {
                        position: 'top'
                    },
                    tooltip: {
                        usePointStyle: true,
                        callbacks: {
                            footer: (tooltipItems) => {
                                const index = tooltipItems[0].dataIndex;
                                return '参考值: 85%';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: '时间'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: '效率 (%)'
                        },
                        min: 70,
                        max: 95,
                        ticks: {
                            callback: (value) => value + '%'
                        }
                    }
                }
            }
        });
    },

    /**
     * 初始化能耗趋势图表
     */
    initEnergyTrendChart() {
        const ctx = document.getElementById('energyTrendChart');
        if (!ctx) return;

        this.charts.energyTrend = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
                datasets: [
                    {
                        label: '实际功耗 (kW)',
                        data: [342, 338, 356, 345, 339, 362, 348],
                        backgroundColor: 'rgba(243, 156, 18, 0.7)',
                        borderColor: '#f39c12',
                        borderWidth: 1,
                        order: 2
                    },
                    {
                        label: '优化后功耗 (kW)',
                        data: [325, 320, 338, 328, 322, 345, 332],
                        backgroundColor: 'rgba(39, 174, 96, 0.7)',
                        borderColor: '#27ae60',
                        borderWidth: 1,
                        order: 1
                    },
                    {
                        label: '节能量 (kW)',
                        data: [17, 18, 18, 17, 17, 17, 16],
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.7)',
                        type: 'line',
                        borderWidth: 2,
                        order: 0
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '周能耗对比分析'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        title: {
                            display: true,
                            text: '功耗 (kW)'
                        }
                    }
                }
            }
        });
    },

    /**
     * 初始化健康趋势图表
     */
    initHealthTrendChart() {
        const ctx = document.getElementById('healthTrendChart');
        if (!ctx) return;

        this.charts.healthTrend = new Chart(ctx, {
            type: 'line',
            data: {
                labels: this.generateTimeLabels(30, 'day'),
                datasets: [
                    {
                        label: '设备健康指数',
                        data: this.generateMockData(30, 85, 95),
                        borderColor: '#9b59b6',
                        backgroundColor: 'rgba(155, 89, 182, 0.1)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '设备健康趋势'
                    },
                    annotation: {
                        annotations: {
                            line1: {
                                type: 'line',
                                yMin: 90,
                                yMax: 90,
                                borderColor: 'rgb(75, 192, 192)',
                                borderWidth: 2,
                                borderDash: [5, 5],
                                label: {
                                    content: '健康阈值',
                                    enabled: true,
                                    position: 'end'
                                }
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        min: 80,
                        max: 100,
                        title: {
                            display: true,
                            text: '健康指数'
                        }
                    }
                }
            }
        });
    },

    /**
     * 初始化工艺分析图表
     */
    initProcessAnalysisChart() {
        const ctx = document.getElementById('processAnalysisChart');
        if (!ctx) return;

        // 生成特性曲线数据
        const flowData = [];
        const headData = [];
        const efficiencyData = [];
        const operatingPoint = { x: 60, y: 32, efficiency: 84 }; // 当前运行点

        for (let i = 0; i <= 100; i += 5) {
            const flow = i;
            // 扬程曲线：H = 40 - 0.003*Q^2
            const head = 40 - 0.003 * Math.pow(flow, 2);
            // 效率曲线：η = -0.0002*Q^2 + 0.04*Q + 70
            const efficiency = Math.max(0, -0.0002 * Math.pow(flow, 2) + 0.04 * flow + 70);

            flowData.push(flow);
            headData.push(head);
            efficiencyData.push(efficiency);
        }

        this.charts.processAnalysis = new Chart(ctx, {
            type: 'line',
            data: {
                labels: flowData,
                datasets: [
                    {
                        label: '扬程 (m)',
                        data: headData,
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        yAxisID: 'y',
                        tension: 0.4
                    },
                    {
                        label: '效率 (%)',
                        data: efficiencyData,
                        borderColor: '#27ae60',
                        backgroundColor: 'rgba(39, 174, 96, 0.1)',
                        yAxisID: 'y1',
                        tension: 0.4
                    },
                    {
                        label: '当前运行点',
                        data: [{ x: operatingPoint.x, y: operatingPoint.y }],
                        backgroundColor: 'red',
                        borderColor: 'red',
                        pointRadius: 8,
                        pointHoverRadius: 10,
                        showLine: false,
                        yAxisID: 'y'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    title: {
                        display: true,
                        text: '泵特性曲线分析'
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                if (context.dataset.label === '当前运行点') {
                                    return [
                                        `流量: ${operatingPoint.x} m³/h`,
                                        `扬程: ${operatingPoint.y} m`,
                                        `效率: ${operatingPoint.efficiency}%`
                                    ];
                                }
                                return context.dataset.label + ': ' + context.parsed.y;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: '流量 (m³/h)'
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: '扬程 (m)'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: '效率 (%)'
                        },
                        grid: {
                            drawOnChartArea: false
                        }
                    }
                }
            }
        });
    },

    /**
     * 初始化经济分析图表
     */
    initEconomicAnalysisChart() {
        const ctx = document.getElementById('economicAnalysisChart');
        if (!ctx) return;

        this.charts.economicAnalysis = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['电费', '维护费', '人工费', '设备折旧', '其他'],
                datasets: [{
                    data: [45, 25, 15, 10, 5],
                    backgroundColor: [
                        '#f39c12',
                        '#3498db',
                        '#9b59b6',
                        '#27ae60',
                        '#e74c3c'
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '运营成本构成分析'
                    },
                    legend: {
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${label}: ${percentage}% (¥${this.formatCurrency(value * 1000)})`;
                            }
                        }
                    }
                }
            }
        });
    },

    /**
     * 格式化货币
     */
    formatCurrency(value) {
        return new Intl.NumberFormat('zh-CN', {
            maximumFractionDigits: 0
        }).format(value);
    },

    /**
     * 初始化诊断雷达图
     */
    initDiagnosticRadarChart() {
        const ctx = document.getElementById('diagnosticRadarChart');
        if (!ctx) return;

        this.charts.diagnosticRadar = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['效率', '振动', '温度', '密封', '轴承', '能耗', '稳定性'],
                datasets: [{
                    label: '当前状态',
                    data: [85, 92, 88, 94, 87, 89, 91],
                    backgroundColor: 'rgba(155, 89, 182, 0.2)',
                    borderColor: '#9b59b6',
                    pointBackgroundColor: '#9b59b6'
                }, {
                    label: '标准值',
                    data: [90, 90, 90, 90, 90, 90, 90],
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    borderColor: '#3498db',
                    pointBackgroundColor: '#3498db'
                }, {
                    label: '上次检修后',
                    data: [80, 85, 83, 90, 82, 86, 85],
                    backgroundColor: 'rgba(243, 156, 18, 0.1)',
                    borderColor: '#f39c12',
                    pointBackgroundColor: '#f39c12'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '设备健康多维度诊断'
                    },
                    legend: {
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const value = context.parsed.r;
                                let status = '正常';
                                let color = 'green';

                                if (value < 80) {
                                    status = '警告';
                                    color = 'orange';
                                } else if (value < 70) {
                                    status = '严重';
                                    color = 'red';
                                }

                                return `${context.dataset.label}: ${value}% - ${status}`;
                            }
                        }
                    }
                },
                scales: {
                    r: {
                        angleLines: {
                            display: true
                        },
                        suggestedMin: 70,
                        suggestedMax: 100,
                        ticks: {
                            callback: (value) => value + '%'
                        }
                    }
                }
            }
        });
    },

    /**
     * 初始化效率历史图表
     */
    initEfficiencyHistoryChart() {
        const ctx = document.getElementById('efficiencyHistoryChart');
        if (!ctx) return;

        // 生成效率历史数据
        const months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月'];
        const currentEfficiency = this.generateMockData(9, 83, 87);
        const previousEfficiency = this.generateMockData(9, 80, 84);
        const targetEfficiency = Array(9).fill(88);

        this.charts.efficiencyHistory = new Chart(ctx, {
            type: 'line',
            data: {
                labels: months,
                datasets: [
                    {
                        label: '当年效率',
                        data: currentEfficiency,
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: '去年同期',
                        data: previousEfficiency,
                        borderColor: '#f39c12',
                        backgroundColor: 'rgba(243, 156, 18, 0.1)',
                        tension: 0.4,
                        borderDash: [5, 5],
                        fill: false
                    },
                    {
                        label: '目标效率',
                        data: targetEfficiency,
                        borderColor: '#27ae60',
                        backgroundColor: 'rgba(39, 174, 96, 0.1)',
                        tension: 0.0,
                        borderDash: [10, 5],
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '泵站效率历史趋势'
                    }
                },
                scales: {
                    y: {
                        title: {
                            display: true,
                            text: '效率 (%)'
                        },
                        min: 75,
                        max: 95,
                        ticks: {
                            callback: (value) => value + '%'
                        }
                    }
                }
            }
        });
    },

    /**
     * 初始化功耗图表
     */
    initPowerConsumptionChart() {
        const ctx = document.getElementById('powerConsumptionChart');
        if (!ctx) return;

        // 生成功耗数据
        const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`);
        const powerData = this.generateMockData(24, 300, 400);
        const flowData = this.generateMockData(24, 1100, 1300);

        this.charts.powerConsumption = new Chart(ctx, {
            type: 'line',
            data: {
                labels: hours,
                datasets: [
                    {
                        label: '功耗 (kW)',
                        data: powerData,
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        tension: 0.4,
                        yAxisID: 'y',
                        fill: true
                    },
                    {
                        label: '流量 (m³/h)',
                        data: flowData,
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        tension: 0.4,
                        yAxisID: 'y1',
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    title: {
                        display: true,
                        text: '功耗与流量关系'
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: '功耗 (kW)'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: '流量 (m³/h)'
                        },
                        grid: {
                            drawOnChartArea: false
                        }
                    }
                }
            }
        });
    },

    /**
     * 初始化泵负载分布图表
     */
    initPumpLoadDistributionChart() {
        const ctx = document.getElementById('pumpLoadDistributionChart');
        if (!ctx) return;

        this.charts.pumpLoadDistribution = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['泵01', '泵02', '泵03', '泵04', '泵05', '泵06', '泵07', '泵08'],
                datasets: [
                    {
                        label: '运行时间占比',
                        data: [75, 82, 65, 95, 60, 85, 70, 55],
                        backgroundColor: 'rgba(52, 152, 219, 0.7)',
                        borderColor: '#3498db',
                        borderWidth: 1
                    },
                    {
                        label: '平均负载率',
                        data: [85, 80, 90, 75, 95, 70, 85, 88],
                        backgroundColor: 'rgba(243, 156, 18, 0.7)',
                        borderColor: '#f39c12',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '泵负载分布'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: '百分比 (%)'
                        },
                        ticks: {
                            callback: (value) => value + '%'
                        }
                    }
                }
            }
        });
    },

    /**
     * 初始化相关性矩阵图表
     */
    initCorrelationMatrixChart() {
        const ctx = document.getElementById('correlationMatrixChart');
        if (!ctx) return;

        // 使用 ECharts 创建相关性矩阵热力图
        if (typeof echarts !== 'undefined') {
            const chart = echarts.init(ctx);

            const data = [
                [0.95, 0.85, 0.65, 0.55, 0.25],
                [0.85, 1.00, 0.75, 0.60, 0.30],
                [0.65, 0.75, 1.00, 0.80, 0.40],
                [0.55, 0.60, 0.80, 1.00, 0.65],
                [0.25, 0.30, 0.40, 0.65, 1.00]
            ];

            const labels = ['流量', '功耗', '效率', '压力', '温度'];

            const option = {
                tooltip: {
                    position: 'top',
                    formatter: (params) => {
                        return `${labels[params.value[0]]} 与 ${labels[params.value[1]]} 的相关性: ${params.value[2].toFixed(2)}`;
                    }
                },
                grid: {
                    top: '15%',
                    bottom: '15%',
                    left: '15%',
                    right: '15%'
                },
                xAxis: {
                    type: 'category',
                    data: labels,
                    splitArea: {
                        show: true
                    }
                },
                yAxis: {
                    type: 'category',
                    data: labels,
                    splitArea: {
                        show: true
                    }
                },
                visualMap: {
                    min: 0,
                    max: 1,
                    calculable: true,
                    orient: 'horizontal',
                    left: 'center',
                    bottom: '0%',
                    text: ['高相关', '低相关'],
                    color: ['#d94e5d', '#eac736', '#50a3ba']
                },
                series: [{
                    name: '相关性',
                    type: 'heatmap',
                    data: data.reduce((result, row, i) => {
                        row.forEach((value, j) => {
                            result.push([i, j, value]);
                        });
                        return result;
                    }, []),
                    label: {
                        show: true,
                        formatter: (params) => params.value[2].toFixed(2)
                    },
                    emphasis: {
                        itemStyle: {
                            shadowBlur: 10,
                            shadowColor: 'rgba(0, 0, 0, 0.5)'
                        }
                    }
                }]
            };

            chart.setOption(option);
            this.charts.correlationMatrix = chart;
        }
    },

    /**
     * 生成时间标签
     */
    generateTimeLabels(count, unit = 'hour') {
        const labels = [];
        const now = new Date();

        for (let i = count - 1; i >= 0; i--) {
            const time = new Date(now);
            switch (unit) {
                case 'hour':
                    time.setHours(time.getHours() - i);
                    labels.push(time.getHours() + ':00');
                    break;
                case 'day':
                    time.setDate(time.getDate() - i);
                    labels.push(`${time.getMonth() + 1}/${time.getDate()}`);
                    break;
                case 'week':
                    time.setDate(time.getDate() - i * 7);
                    labels.push(`第${Math.ceil((time.getDate() + 7) / 7)}周`);
                    break;
                default:
                    labels.push(i);
            }
        }

        return labels;
    },

    /**
     * 生成模拟数据
     */
    generateMockData(count, min, max) {
        return Array.from({ length: count }, () =>
            Math.random() * (max - min) + min
        );
    },

    /**
     * 更新图表数据
     */
    updateChartData(chartName, newData) {
        const chart = this.charts[chartName];
        if (chart && newData) {
            if (chart.data && chart.data.datasets) {
                chart.data.datasets[0].data = newData;
                chart.update();
            } else if (chart.setOption) {
                // ECharts更新
                chart.setOption({
                    series: [{
                        data: newData
                    }]
                });
            }
        }
    },

    /**
     * 更新所有图表尺寸
     */
    resizeAll() {
        Object.values(this.charts).forEach(chart => {
            if (chart) {
                if (chart.resize) {
                    // ECharts
                    chart.resize();
                } else if (chart.update) {
                    // Chart.js
                    chart.update();
                }
            }
        });
    },

    /**
     * 销毁所有图表
     */
    destroyAllCharts() {
        Object.values(this.charts).forEach(chart => {
            if (chart) {
                if (chart.destroy) {
                    // Chart.js
                    chart.destroy();
                } else if (chart.dispose) {
                    // ECharts
                    chart.dispose();
                }
            }
        });
        this.charts = {};
    }
};

// 页面卸载时销毁图表
window.addEventListener('beforeunload', function () {
    if (window.PumpDashboardCharts) {
        window.PumpDashboardCharts.destroyAllCharts();
    }
});

console.log('📊 泵站图表管理模块已加载');