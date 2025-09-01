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

            console.log('✅ 图表初始化完成');
        } catch (error) {
            console.error('❌ 图表初始化失败:', error);
            PumpSystem.Notification.error(`图表初始化失败: ${error.message}`);
        }
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
                plugins: {
                    title: {
                        display: true,
                        text: '泵站效率趋势'
                    },
                    legend: {
                        position: 'top'
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
                        max: 95
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
                        borderWidth: 1
                    },
                    {
                        label: '优化后功耗 (kW)',
                        data: [325, 320, 338, 328, 322, 345, 332],
                        backgroundColor: 'rgba(39, 174, 96, 0.7)',
                        borderColor: '#27ae60',
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
                        text: '周能耗对比分析'
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
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '泵特性曲线分析'
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
                    }
                }
            }
        });
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
                    }
                },
                scales: {
                    r: {
                        angleLines: {
                            display: true
                        },
                        suggestedMin: 70,
                        suggestedMax: 100
                    }
                }
            }
        });
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
            chart.data.datasets[0].data = newData;
            chart.update();
        }
    },

    /**
     * 销毁所有图表
     */
    destroyAllCharts() {
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
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