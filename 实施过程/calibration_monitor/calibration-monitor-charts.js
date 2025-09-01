// 泵特性曲线校准监控系统 - 图表功能模块

// 图表配置和数据
const chartConfigs = {
    colors: {
        primary: '#3498db',
        success: '#27ae60',
        warning: '#f39c12',
        danger: '#e74c3c',
        info: '#17a2b8',
        secondary: '#95a5a6'
    },
    defaultOptions: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: true,
                position: 'top'
            }
        }
    }
};

// RLS参数变化图表
function initRLSChart() {
    const ctx = document.getElementById('rlsChart');
    if (!ctx) return;

    charts.rls = new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: {
            labels: ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10'],
            datasets: [{
                label: '效率系数',
                data: [0.82, 0.825, 0.83, 0.835, 0.84, 0.843, 0.845, 0.846, 0.847, 0.847, 0.847],
                borderColor: chartConfigs.colors.success,
                backgroundColor: 'rgba(76, 175, 80, 0.1)',
                tension: 0.4
            }, {
                label: '扬程系数',
                data: [1.05, 1.045, 1.04, 1.035, 1.03, 1.028, 1.025, 1.024, 1.023, 1.023, 1.023],
                borderColor: chartConfigs.colors.primary,
                backgroundColor: 'rgba(33, 150, 243, 0.1)',
                tension: 0.4
            }, {
                label: '流量系数',
                data: [0.92, 0.925, 0.93, 0.935, 0.94, 0.945, 0.95, 0.953, 0.955, 0.956, 0.956],
                borderColor: chartConfigs.colors.warning,
                backgroundColor: 'rgba(255, 152, 0, 0.1)',
                tension: 0.4
            }]
        },
        options: {
            ...chartConfigs.defaultOptions,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: '迭代次数'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: '参数值'
                    },
                    min: 0.8,
                    max: 1.1
                }
            },
            plugins: {
                ...chartConfigs.defaultOptions.plugins,
                tooltip: {
                    callbacks: {
                        afterBody: function (context) {
                            const dataIndex = context[0].dataIndex;
                            const convergence = dataIndex > 8 ? '已收敛' : '收敛中';
                            return `状态: ${convergence}`;
                        }
                    }
                }
            }
        }
    });
}

// 算法性能对比雷达图
function initAlgorithmRadarChart() {
    const ctx = document.getElementById('algorithmRadarChart');
    if (!ctx) return;

    charts.algorithmRadar = new Chart(ctx.getContext('2d'), {
        type: 'radar',
        data: {
            labels: ['精度', '速度', '稳定性', '鲁棒性', '资源消耗'],
            datasets: [{
                label: '神经网络',
                data: [95, 70, 85, 80, 60],
                borderColor: chartConfigs.colors.danger,
                backgroundColor: 'rgba(231, 76, 60, 0.2)',
                pointBackgroundColor: chartConfigs.colors.danger
            }, {
                label: '随机森林',
                data: [89, 85, 92, 88, 75],
                borderColor: chartConfigs.colors.primary,
                backgroundColor: 'rgba(52, 152, 235, 0.2)',
                pointBackgroundColor: chartConfigs.colors.primary
            }, {
                label: '高斯过程',
                data: [87, 65, 88, 85, 55],
                borderColor: chartConfigs.colors.success,
                backgroundColor: 'rgba(39, 174, 96, 0.2)',
                pointBackgroundColor: chartConfigs.colors.success
            }]
        },
        options: {
            ...chartConfigs.defaultOptions,
            scales: {
                r: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        stepSize: 20
                    }
                }
            }
        }
    });
}

// 精度提升趋势图
function initAccuracyImprovementChart() {
    const ctx = document.getElementById('accuracyImprovementChart');
    if (!ctx) return;

    charts.accuracyImprovement = new Chart(ctx.getContext('2d'), {
        type: 'bar',
        data: {
            labels: ['H-Q扬程', 'η-Q效率', 'P-Q功率', 'H-f频率', '泵组协调'],
            datasets: [{
                label: '改进前',
                data: [58, 52, 61, 45, 53],
                backgroundColor: 'rgba(149, 165, 166, 0.6)',
                borderColor: chartConfigs.colors.secondary,
                borderWidth: 1
            }, {
                label: '改进后',
                data: [94, 89, 87, 92, 85],
                backgroundColor: 'rgba(39, 174, 96, 0.6)',
                borderColor: chartConfigs.colors.success,
                borderWidth: 1
            }]
        },
        options: {
            ...chartConfigs.defaultOptions,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: '精度 (%)'
                    }
                }
            },
            plugins: {
                ...chartConfigs.defaultOptions.plugins,
                tooltip: {
                    callbacks: {
                        afterLabel: function (context) {
                            if (context.datasetIndex === 1) {
                                const before = context.chart.data.datasets[0].data[context.dataIndex];
                                const after = context.parsed.y;
                                const improvement = ((after - before) / before * 100).toFixed(1);
                                return `提升: +${improvement}%`;
                            }
                            return '';
                        }
                    }
                }
            }
        }
    });
}

// 实时数据流监控图
function initRealTimeDataChart() {
    const ctx = document.getElementById('realTimeDataChart');
    if (!ctx) return;

    const initialData = Array.from({ length: 20 }, (_, i) => ({
        x: i,
        y: 85 + Math.random() * 10
    }));

    charts.realTimeData = new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: {
            datasets: [{
                label: '实时精度',
                data: initialData,
                borderColor: chartConfigs.colors.primary,
                backgroundColor: 'rgba(52, 152, 235, 0.1)',
                tension: 0.4,
                fill: true,
                pointRadius: 2
            }]
        },
        options: {
            ...chartConfigs.defaultOptions,
            animation: {
                duration: 0
            },
            scales: {
                x: {
                    type: 'linear',
                    title: {
                        display: true,
                        text: '时间 (秒)'
                    }
                },
                y: {
                    min: 75,
                    max: 100,
                    title: {
                        display: true,
                        text: '精度 (%)'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });

    // 启动实时数据更新
    startRealTimeDataUpdate();
}

// 启动实时数据更新
function startRealTimeDataUpdate() {
    if (!charts.realTimeData) return;

    setInterval(() => {
        const chart = charts.realTimeData;
        const data = chart.data.datasets[0].data;

        // 移除第一个数据点
        data.shift();

        // 添加新的数据点
        const lastPoint = data[data.length - 1];
        const newPoint = {
            x: lastPoint.x + 1,
            y: Math.max(75, Math.min(100, lastPoint.y + (Math.random() - 0.5) * 3))
        };
        data.push(newPoint);

        // 更新X轴范围
        chart.options.scales.x.min = newPoint.x - 19;
        chart.options.scales.x.max = newPoint.x;

        chart.update('none');
    }, 1000);
}

// 曲线拟合过程动画图
function initFittingProcessChart() {
    const ctx = document.getElementById('fittingProcessChart');
    if (!ctx) return;

    // 生成模拟数据点
    const originalData = Array.from({ length: 50 }, (_, i) => ({
        x: i * 2,
        y: 100 - 0.8 * i + Math.random() * 10 - 5
    }));

    const fittedData = Array.from({ length: 50 }, (_, i) => ({
        x: i * 2,
        y: 100 - 0.8 * i
    }));

    charts.fittingProcess = new Chart(ctx.getContext('2d'), {
        type: 'scatter',
        data: {
            datasets: [{
                label: '原始数据',
                data: originalData,
                backgroundColor: 'rgba(149, 165, 166, 0.6)',
                borderColor: chartConfigs.colors.secondary,
                pointRadius: 3
            }, {
                label: '拟合曲线',
                data: fittedData,
                type: 'line',
                borderColor: chartConfigs.colors.danger,
                backgroundColor: 'rgba(231, 76, 60, 0.1)',
                tension: 0.3,
                pointRadius: 0,
                borderWidth: 3
            }]
        },
        options: {
            ...chartConfigs.defaultOptions,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: '流量 (m³/h)'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: '扬程 (m)'
                    }
                }
            },
            plugins: {
                ...chartConfigs.defaultOptions.plugins,
                tooltip: {
                    callbacks: {
                        afterBody: function (context) {
                            if (context[0].datasetIndex === 1) {
                                return 'R² = 0.943\nRMSE = 1.2m';
                            }
                            return '';
                        }
                    }
                }
            }
        }
    });
}

// 多维度性能对比图
function initPerformanceComparisonChart() {
    const ctx = document.getElementById('performanceComparisonChart');
    if (!ctx) return;

    charts.performanceComparison = new Chart(ctx.getContext('2d'), {
        type: 'bar',
        data: {
            labels: ['准确性', '计算速度', '内存占用', '稳定性', '收敛性'],
            datasets: [{
                label: '神经网络',
                data: [94, 70, 60, 85, 88],
                backgroundColor: 'rgba(231, 76, 60, 0.6)',
                borderColor: chartConfigs.colors.danger
            }, {
                label: '随机森林',
                data: [91, 85, 75, 92, 90],
                backgroundColor: 'rgba(52, 152, 235, 0.6)',
                borderColor: chartConfigs.colors.primary
            }, {
                label: '高斯过程',
                data: [90, 65, 55, 88, 85],
                backgroundColor: 'rgba(39, 174, 96, 0.6)',
                borderColor: chartConfigs.colors.success
            }, {
                label: '多项式',
                data: [77, 95, 90, 70, 75],
                backgroundColor: 'rgba(243, 156, 18, 0.6)',
                borderColor: chartConfigs.colors.warning
            }]
        },
        options: {
            ...chartConfigs.defaultOptions,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: '性能指标 (%)'
                    }
                }
            },
            plugins: {
                ...chartConfigs.defaultOptions.plugins,
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// 精度分布直方图
function initAccuracyDistributionChart() {
    const ctx = document.getElementById('accuracyDistributionChart');
    if (!ctx) return;

    charts.accuracyDistribution = new Chart(ctx.getContext('2d'), {
        type: 'bar',
        data: {
            labels: ['0.5-0.6', '0.6-0.7', '0.7-0.8', '0.8-0.9', '0.9-1.0'],
            datasets: [{
                label: '曲线数量',
                data: [2, 8, 15, 35, 23],
                backgroundColor: [
                    'rgba(231, 76, 60, 0.6)',
                    'rgba(243, 156, 18, 0.6)',
                    'rgba(255, 193, 7, 0.6)',
                    'rgba(52, 152, 235, 0.6)',
                    'rgba(39, 174, 96, 0.6)'
                ],
                borderColor: [
                    chartConfigs.colors.danger,
                    chartConfigs.colors.warning,
                    '#ffc107',
                    chartConfigs.colors.primary,
                    chartConfigs.colors.success
                ],
                borderWidth: 1
            }]
        },
        options: {
            ...chartConfigs.defaultOptions,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'R² 精度区间'
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: '曲线数量'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}

// 时间序列预测图
function initTimeSeriesPredictionChart() {
    const ctx = document.getElementById('timeSeriesPredictionChart');
    if (!ctx) return;

    const historicalData = Array.from({ length: 30 }, (_, i) => ({
        x: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000),
        y: 85 + Math.sin(i * 0.1) * 5 + Math.random() * 3
    }));

    const predictionData = Array.from({ length: 10 }, (_, i) => ({
        x: new Date(Date.now() + (i + 1) * 24 * 60 * 60 * 1000),
        y: 90 + Math.sin((30 + i) * 0.1) * 5
    }));

    charts.timeSeriesPrediction = new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: {
            datasets: [{
                label: '历史数据',
                data: historicalData,
                borderColor: chartConfigs.colors.primary,
                backgroundColor: 'rgba(52, 152, 235, 0.1)',
                tension: 0.3
            }, {
                label: '预测数据',
                data: predictionData,
                borderColor: chartConfigs.colors.warning,
                backgroundColor: 'rgba(243, 156, 18, 0.1)',
                borderDash: [5, 5],
                tension: 0.3
            }]
        },
        options: {
            ...chartConfigs.defaultOptions,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'day'
                    },
                    title: {
                        display: true,
                        text: '时间'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: '平均精度 (%)'
                    }
                }
            }
        }
    });
}

// 更新图表数据的辅助函数
function updateChartData(chartName, newData) {
    if (!charts[chartName]) return;

    const chart = charts[chartName];

    if (Array.isArray(newData)) {
        chart.data.datasets[0].data = newData;
    } else if (typeof newData === 'object') {
        Object.keys(newData).forEach(key => {
            if (chart.data[key]) {
                chart.data[key] = newData[key];
            }
        });
    }

    chart.update();
}

// 导出所有图表到PDF
function exportAllChartsToPDF() {
    // 使用 jsPDF 库导出图表
    if (typeof jsPDF === 'undefined') {
        console.warn('jsPDF library not loaded');
        return;
    }

    const pdf = new jsPDF();
    let pageNumber = 1;

    Object.keys(charts).forEach((chartName, index) => {
        if (index > 0) {
            pdf.addPage();
            pageNumber++;
        }

        const chart = charts[chartName];
        const canvas = chart.canvas;
        const imgData = canvas.toDataURL('image/png');

        pdf.text(`图表 ${pageNumber}: ${chartName}`, 20, 20);
        pdf.addImage(imgData, 'PNG', 20, 30, 170, 100);
        pdf.text(`生成时间: ${new Date().toLocaleString()}`, 20, 140);
    });

    pdf.save('calibration-charts-report.pdf');
}

// 初始化所有图表
function initializeAllCharts() {
    try {
        initRLSChart();
        initAlgorithmRadarChart();
        initAccuracyImprovementChart();
        initRealTimeDataChart();
        initFittingProcessChart();
        initPerformanceComparisonChart();
        initAccuracyDistributionChart();
        initTimeSeriesPredictionChart();

        console.log('所有图表初始化完成');
    } catch (error) {
        console.error('图表初始化失败:', error);
    }
}

// 销毁所有图表
function destroyAllCharts() {
    Object.keys(charts).forEach(chartName => {
        if (charts[chartName] && typeof charts[chartName].destroy === 'function') {
            charts[chartName].destroy();
        }
    });
    charts = {};
}

// 导出图表功能
window.CalibrationCharts = {
    initializeAllCharts,
    updateChartData,
    exportAllChartsToPDF,
    destroyAllCharts,
    chartConfigs
};
