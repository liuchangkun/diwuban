// 泵特性曲线查询功能模块

// 泵查询相关变量
let pumpQueryModule;
let selectedPumpId = null;
let selectedCurveType = null;

// 初始化泵查询模块
function initializePumpQueryModule() {
    if (typeof PumpCurveQueryModule === 'undefined') {
        console.error('泵查询模块未加载');
        return;
    }

    pumpQueryModule = new PumpCurveQueryModule();
    loadPumpList();
    loadCurveTypes();
}

// 加载泵列表
function loadPumpList() {
    const container = document.getElementById('pumpListContainer');
    if (!container) return;

    const pumps = pumpQueryModule.getPumpList();

    container.innerHTML = pumps.map(pump => `
        <div class="pump-item" onclick="selectPump('${pump.id}')" data-pump-id="${pump.id}">
            <div class="pump-info">
                <div class="pump-name">${pump.name}</div>
                <div class="pump-details">${pump.station} | ${pump.type} | 最后校准: ${pump.lastCalibration}</div>
            </div>
            <div class="pump-status status-${pump.status}">
                ${pump.status === 'running' ? '运行中' :
            pump.status === 'standby' ? '备用' : '维护中'}
            </div>
        </div>
    `).join('');
}

// 加载曲线类型
function loadCurveTypes() {
    const container = document.getElementById('curveTypeContainer');
    if (!container) return;

    const curveTypes = pumpQueryModule.curveTypes;

    container.innerHTML = curveTypes.map(curve => `
        <div class="curve-type-card" onclick="selectCurveType('${curve.id}')" data-curve-id="${curve.id}">
            <div class="curve-type-info">
                <span class="curve-icon">${curve.icon}</span>
                <span class="curve-name">${curve.name}</span>
            </div>
            <div class="curve-accuracy accuracy-good">90%+</div>
        </div>
    `).join('');
}

// 选择泵
function selectPump(pumpId) {
    // 更新选中状态
    document.querySelectorAll('.pump-item').forEach(item => {
        item.classList.remove('selected');
    });
    const selectedElement = document.querySelector(`[data-pump-id="${pumpId}"]`);
    if (selectedElement) {
        selectedElement.classList.add('selected');
    }

    selectedPumpId = pumpId;
    console.log(`选择泵: ${pumpId}`);

    // 如果也选了曲线类型，则显示查询结果
    if (selectedCurveType) {
        showQueryResults();
    }
}

// 选择曲线类型
function selectCurveType(curveType) {
    // 更新选中状态
    document.querySelectorAll('.curve-type-card').forEach(card => {
        card.classList.remove('selected');
    });
    const selectedElement = document.querySelector(`[data-curve-id="${curveType}"]`);
    if (selectedElement) {
        selectedElement.classList.add('selected');
    }

    selectedCurveType = curveType;
    console.log(`选择曲线类型: ${curveType}`);

    // 如果也选了泵，则显示查询结果
    if (selectedPumpId) {
        showQueryResults();
    }
}

// 显示查询结果
function showQueryResults() {
    if (!selectedPumpId || !selectedCurveType) return;

    const resultsPanel = document.getElementById('queryResultsPanel');
    if (resultsPanel) {
        resultsPanel.classList.add('active');
    }

    // 初始化详细分析功能
    loadDetailedAnalysis();

    // 加载综合分析
    loadComprehensiveAnalysis();

    // 加载默认标签页（优化历史）
    loadOptimizationHistory();

    console.log(`显示查询结果: 泵=${selectedPumpId}, 曲线=${selectedCurveType}`);
}

// 切换查询结果标签页
function switchQueryTab(tabName) {
    // 更新按钮状态
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });

    // 查找当前被点击的按钮
    const clickedButton = Array.from(document.querySelectorAll('.tab-button'))
        .find(btn => btn.onclick && btn.onclick.toString().includes(tabName));
    if (clickedButton) {
        clickedButton.classList.add('active');
    }

    // 更新内容区域
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    const targetTab = document.getElementById(`${tabName}-tab`);
    if (targetTab) {
        targetTab.classList.add('active');
    }

    // 加载对应数据
    switch (tabName) {
        case 'optimization-history':
            loadOptimizationHistory();
            break;
        case 'algorithm-comparison':
            loadAlgorithmComparison();
            break;
        case 'process-details':
            loadProcessDetails();
            break;
        case 'quality-metrics':
            loadQualityMetrics();
            break;
        case 'detailed-analysis':
            loadDetailedAnalysisContent();
            break;
    }
}

// 加载优化历史
function loadOptimizationHistory() {
    if (!selectedPumpId || !selectedCurveType) return;

    const container = document.getElementById('optimizationHistoryContainer');
    if (!container) return;

    const history = pumpQueryModule.getCurveOptimizationHistory(selectedPumpId, selectedCurveType);

    if (!history || history.length === 0) {
        container.innerHTML = '<p>暂无优化历史记录</p>';
        return;
    }

    const tableHTML = `
        <table class="optimization-history-table">
            <thead>
                <tr>
                    <th>时间</th>
                    <th>优化原因</th>
                    <th>算法变化</th>
                    <th>精度变化</th>
                    <th>数据质量</th>
                    <th>处理时间</th>
                    <th>备注</th>
                </tr>
            </thead>
            <tbody>
                ${history.map(record => `
                    <tr>
                        <td>${new Date(record.timestamp).toLocaleString()}</td>
                        <td><span class="reason-badge reason-${record.reason}">${record.reasonDesc}</span></td>
                        <td>${record.beforeAlgorithm} → ${record.afterAlgorithm}</td>
                        <td>
                            <span style="color: #e74c3c;">${(record.beforeAccuracy * 100).toFixed(1)}%</span>
                            →
                            <span style="color: #27ae60;">${(record.afterAccuracy * 100).toFixed(1)}%</span>
                            <small>(+${((record.afterAccuracy - record.beforeAccuracy) * 100).toFixed(1)}%)</small>
                        </td>
                        <td>${(record.dataQuality * 100).toFixed(1)}%</td>
                        <td>${record.processingTime.toFixed(1)}s</td>
                        <td><small>${record.notes}</small></td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    container.innerHTML = tableHTML;
}

// 加载算法对比
function loadAlgorithmComparison() {
    if (!selectedPumpId || !selectedCurveType) return;

    const container = document.getElementById('algorithmComparisonContainer');
    if (!container) return;

    const comparison = pumpQueryModule.getAlgorithmComparison(selectedPumpId, selectedCurveType);

    if (!comparison || comparison.length === 0) {
        container.innerHTML = '<p>暂无算法对比数据</p>';
        return;
    }

    const cardsHTML = `
        <div class="algorithm-comparison-grid">
            ${comparison.map(algo => `
                <div class="algorithm-comparison-card ${algo.recommended ? 'recommended' : ''}">
                    <div class="algorithm-header">
                        <div class="algorithm-title">${algo.algorithmName}</div>
                        ${algo.recommended ? '<span class="recommended-badge">推荐</span>' : ''}
                    </div>
                    <div class="algorithm-metrics-grid">
                        <div class="metric-row">
                            <span class="metric-label">精度:</span>
                            <span class="metric-value">${(algo.accuracy * 100).toFixed(1)}%</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">训练时间:</span>
                            <span class="metric-value">${algo.trainingTime.toFixed(1)}s</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">收敛性:</span>
                            <span class="metric-value">${(algo.convergence * 100).toFixed(1)}%</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">鲁棒性:</span>
                            <span class="metric-value">${(algo.robustness * 100).toFixed(1)}%</span>
                        </div>
                    </div>
                    <div style="margin-top: 10px; font-size: 0.85rem; color: #666; line-height: 1.4;">
                        ${algo.notes}
                    </div>
                </div>
            `).join('')}
        </div>
    `;

    container.innerHTML = cardsHTML;
}

// 加载过程详情
function loadProcessDetails() {
    if (!selectedPumpId || !selectedCurveType) return;

    const container = document.getElementById('processDetailsContainer');
    if (!container) return;

    const details = pumpQueryModule.getCurveProcessDetails(selectedPumpId, selectedCurveType);

    if (!details) {
        container.innerHTML = '<p>暂无过程详情数据</p>';
        return;
    }

    const detailsHTML = `
        <div class="process-details-section">
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                <div style="text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                    <div style="font-size: 1.5rem; font-weight: bold; color: #3498db;">${details.totalSteps}</div>
                    <div style="color: #666;">总步骤数</div>
                </div>
                <div style="text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                    <div style="font-size: 1.5rem; font-weight: bold; color: #27ae60;">${details.completedSteps}</div>
                    <div style="color: #666;">已完成</div>
                </div>
                <div style="text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                    <div style="font-size: 1.5rem; font-weight: bold; color: #f39c12;">${details.totalDuration}</div>
                    <div style="color: #666;">总耗时</div>
                </div>
            </div>

            <h5>🔧 过程步骤时间线</h5>
            <div class="process-steps-timeline">
                ${details.steps.map(step => `
                    <div class="process-step">
                        <div class="step-header">
                            <span class="step-name">${step.step}. ${step.name}</span>
                            <span class="step-duration">${step.duration}</span>
                        </div>
                        <div style="font-size: 0.85rem; color: #666;">状态: ${step.status === 'completed' ? '✓ 已完成' : '进行中'}</div>
                    </div>
                `).join('')}
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;">
                <div>
                    <h5>📊 数据选择细节</h5>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                        <div><strong>总数据点:</strong> ${details.dataSelection.totalPoints}个</div>
                        <div><strong>选中数据:</strong> ${details.dataSelection.selectedPoints}个</div>
                        <div><strong>时间范围:</strong> ${details.dataSelection.timeRange}</div>
                        <div><strong>拒绝数据:</strong> ${details.dataSelection.rejectedPoints}个</div>
                        <div style="margin-top: 10px;">
                            <div><strong>质量标准:</strong></div>
                            <ul style="margin: 5px 0; padding-left: 20px; font-size: 0.9rem;">
                                ${details.dataSelection.qualityCriteria.map(criteria => `<li>${criteria}</li>`).join('')}
                            </ul>
                        </div>
                    </div>
                </div>

                <div>
                    <h5>🧠 算法选择原因</h5>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                        <div style="line-height: 1.6;">${details.algorithmReason}</div>
                    </div>

                    <h5 style="margin-top: 15px;">📊 验证结果</h5>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                        <div><strong>交叉验证:</strong> ${details.validationResults.crossValidationFolds}折</div>
                        <div><strong>平均精度:</strong> ${(details.validationResults.averageAccuracy * 100).toFixed(1)}%</div>
                        <div><strong>测试精度:</strong> ${(details.validationResults.testAccuracy * 100).toFixed(1)}%</div>
                        <div><strong>过拟合风险:</strong> ${details.validationResults.holdoutValidation.overfittingRisk === 'low' ? '低' : '中等'}</div>
                    </div>
                </div>
            </div>
        </div>
    `;

    container.innerHTML = detailsHTML;
}

// 加载质量指标
function loadQualityMetrics() {
    if (!selectedPumpId || !selectedCurveType) return;

    const container = document.getElementById('qualityMetricsContainer');
    if (!container) return;

    const pump = pumpQueryModule.getPumpDetails(selectedPumpId);

    if (!pump) {
        container.innerHTML = '<p>暂无质量指标数据</p>';
        return;
    }

    const curve = pump.curves.find(c => c.curveType === selectedCurveType);
    if (!curve) {
        container.innerHTML = '<p>暂无该曲线质量数据</p>';
        return;
    }

    const metrics = curve.qualityMetrics;
    const metricsHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px;">
            <div style="text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #3498db;">
                <div style="font-size: 1.3rem; font-weight: bold; color: #3498db;">${(metrics.r2Score * 100).toFixed(1)}%</div>
                <div style="color: #666;">R² Score</div>
            </div>
            <div style="text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #27ae60;">
                <div style="font-size: 1.3rem; font-weight: bold; color: #27ae60;">${metrics.mse.toFixed(3)}</div>
                <div style="color: #666;">MSE</div>
            </div>
            <div style="text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #f39c12;">
                <div style="font-size: 1.3rem; font-weight: bold; color: #f39c12;">${metrics.mae.toFixed(3)}</div>
                <div style="color: #666;">MAE</div>
            </div>
            <div style="text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #e74c3c;">
                <div style="font-size: 1.3rem; font-weight: bold; color: #e74c3c;">${metrics.maxError.toFixed(3)}</div>
                <div style="color: #666;">最大误差</div>
            </div>
        </div>

        <h5>📈 残差分析</h5>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px;">
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                <div><strong>均值:</strong> ${metrics.residualAnalysis.mean.toFixed(4)}</div>
                <div><strong>标准差:</strong> ${metrics.residualAnalysis.std.toFixed(4)}</div>
            </div>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                <div><strong>偏度:</strong> ${metrics.residualAnalysis.skewness.toFixed(3)}</div>
                <div><strong>峰度:</strong> ${metrics.residualAnalysis.kurtosis.toFixed(3)}</div>
            </div>
        </div>

        <div style="margin-top: 20px; padding: 15px; background: #e8f5e8; border-radius: 8px; border-left: 4px solid #27ae60;">
            <h5 style="color: #2e7d32; margin-bottom: 10px;">📊 综合评价</h5>
            <div style="color: #2e7d32;">
                该曲线的R²得分为${(metrics.r2Score * 100).toFixed(1)}%，
                ${metrics.r2Score > 0.9 ? '精度优秀' : metrics.r2Score > 0.8 ? '精度良好' : '精度一般'}。
                残差分析显示模型${Math.abs(metrics.residualAnalysis.skewness) < 0.5 ? '缺乏偏差' : '存在偏差'}，
                ${Math.abs(metrics.residualAnalysis.kurtosis) < 2 ? '残差分布正常' : '残差分布异常'}。
            </div>
        </div>
    `;

    container.innerHTML = metricsHTML;
}

// 详细分析功能
function loadDetailedAnalysis() {
    if (!selectedPumpId || !selectedCurveType) return;

    const analysis = pumpQueryModule.getDetailedOptimizationAnalysis(selectedPumpId, selectedCurveType);
    if (!analysis) return;

    // 添加详细分析标签页
    const tabsContainer = document.querySelector('.results-tabs');
    if (tabsContainer && !document.querySelector('[onclick*="detailed-analysis"]')) {
        const detailedTab = document.createElement('button');
        detailedTab.className = 'tab-button';
        detailedTab.onclick = () => switchQueryTab('detailed-analysis');
        detailedTab.innerHTML = '🔍 详细分析';
        tabsContainer.appendChild(detailedTab);
    }

    // 创建详细分析内容区域
    const resultsPanel = document.getElementById('queryResultsPanel');
    if (resultsPanel && !document.getElementById('detailed-analysis-tab')) {
        const detailedAnalysisTab = document.createElement('div');
        detailedAnalysisTab.id = 'detailed-analysis-tab';
        detailedAnalysisTab.className = 'tab-content';
        detailedAnalysisTab.innerHTML = `
            <h4>🔍 深度分析报告</h4>
            <div id="detailedAnalysisContainer">
                <!-- 详细分析内容将动态加载 -->
            </div>
        `;
        resultsPanel.appendChild(detailedAnalysisTab);
    }
}

// 加载详细分析内容
function loadDetailedAnalysisContent() {
    if (!selectedPumpId || !selectedCurveType) return;

    const container = document.getElementById('detailedAnalysisContainer');
    if (!container) return;

    const analysis = pumpQueryModule.getDetailedOptimizationAnalysis(selectedPumpId, selectedCurveType);

    if (!analysis) {
        container.innerHTML = '<p>暂无详细分析数据</p>';
        return;
    }

    const detailedHTML = `
        <!-- 性能趋势分析 -->
        <div class="analysis-section">
            <h5>📈 性能趋势分析</h5>
            <div class="performance-trend-chart">
                <canvas id="performanceTrendChart" width="100%" height="200"></canvas>
            </div>
            <div class="trend-summary">
                <div class="trend-stats">
                    <div class="stat-item">
                        <span class="stat-label">当前精度:</span>
                        <span class="stat-value">${(analysis.accuracy * 100).toFixed(1)}%</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">趋势:</span>
                        <span class="stat-value trend-up">上升</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">数据点:</span>
                        <span class="stat-value">${analysis.dataPoints}个</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- 数据质量报告 -->
        <div class="analysis-section">
            <h5>📋 数据质量报告</h5>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;">
                ${Object.entries(analysis.detailedAnalysis.dataQualityReport.categories).map(([key, category]) => `
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #3498db;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                            <span style="font-weight: bold; color: #2c3e50;">${category.description}</span>
                            <span style="padding: 4px 8px; border-radius: 12px; font-size: 0.8rem; font-weight: bold;
                                    background: ${category.score > 0.9 ? '#d4edda' : category.score > 0.8 ? '#cce5ff' : '#fff3cd'};
                                    color: ${category.score > 0.9 ? '#155724' : category.score > 0.8 ? '#004085' : '#856404'};">
                                ${(category.score * 100).toFixed(1)}%
                            </span>
                        </div>
                        <div style="font-size: 0.85rem; color: #666;">
                            ${category.issues.map(issue => `<div style="margin-bottom: 3px;">• ${issue}</div>`).join('')}
                        </div>
                    </div>
                `).join('')}
            </div>
            <div style="background: #e8f5e8; padding: 15px; border-radius: 8px;">
                <h6 style="margin: 0 0 10px 0; color: #2d7d32;">💡 改进建议</h6>
                <ul style="margin: 0; padding-left: 20px;">
                    ${analysis.detailedAnalysis.dataQualityReport.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                </ul>
            </div>
        </div>

        <!-- 优化建议 -->
        <div class="analysis-section">
            <h5>💡 优化建议</h5>
            <div style="display: grid; gap: 10px;">
                ${analysis.detailedAnalysis.optimizationRecommendations.map(rec => `
                    <div style="background: white; padding: 15px; border-radius: 8px;
                                border-left: 4px solid ${rec.priority === 'high' ? '#e74c3c' : rec.priority === 'medium' ? '#f39c12' : '#3498db'};">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span style="font-weight: bold; color: #2c3e50;">${rec.title}</span>
                            <span style="background: #e9ecef; padding: 2px 6px; border-radius: 8px; font-size: 0.8rem;">
                                ${rec.priority === 'high' ? '高' : rec.priority === 'medium' ? '中' : '低'}
                            </span>
                        </div>
                        <div style="color: #666; margin-bottom: 8px;">${rec.description}</div>
                        <div style="color: #3498db; font-weight: bold;">👉 ${rec.action}</div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;

    container.innerHTML = detailedHTML;

    // 绘制性能趋势图
    setTimeout(() => {
        drawPerformanceTrendChart(analysis.detailedAnalysis.performanceTrend);
    }, 100);
}

// 绘制性能趋势图
function drawPerformanceTrendChart(trendData) {
    const canvas = document.getElementById('performanceTrendChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    const padding = 40;

    ctx.clearRect(0, 0, width, height);

    // 绘制背景
    ctx.fillStyle = '#f8f9fa';
    ctx.fillRect(0, 0, width, height);

    // 绘制网格线
    ctx.strokeStyle = '#e0e0e0';
    ctx.lineWidth = 1;

    for (let i = 1; i < 5; i++) {
        const y = padding + (height - 2 * padding) * i / 5;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(width - padding, y);
        ctx.stroke();
    }

    // 绘制数据线
    if (trendData && trendData.length > 1) {
        ctx.strokeStyle = '#3498db';
        ctx.lineWidth = 2;
        ctx.beginPath();

        trendData.forEach((point, index) => {
            const x = padding + (width - 2 * padding) * index / (trendData.length - 1);
            const y = height - padding - (height - 2 * padding) * (point.accuracy - 0.7) / 0.3;

            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });

        ctx.stroke();

        // 绘制数据点
        ctx.fillStyle = '#3498db';
        trendData.forEach((point, index) => {
            const x = padding + (width - 2 * padding) * index / (trendData.length - 1);
            const y = height - padding - (height - 2 * padding) * (point.accuracy - 0.7) / 0.3;

            ctx.beginPath();
            ctx.arc(x, y, 3, 0, 2 * Math.PI);
            ctx.fill();
        });
    }

    // 添加标签
    ctx.fillStyle = '#666';
    ctx.font = '12px Arial';
    ctx.fillText('精度变化趋势', padding, 20);
    ctx.fillText('70%', 10, height - padding);
    ctx.fillText('100%', 10, padding);
}

// 综合分析功能
function loadComprehensiveAnalysis() {
    if (!selectedPumpId) return;

    const analysis = pumpQueryModule.getComprehensiveAnalysis(selectedPumpId);
    if (!analysis) return;

    console.log('加载综合分析:', analysis);
    // 这里可以添加综合分析的UI显示逻辑
}

// 导出泵查询功能
window.PumpQueryModule = {
    initializePumpQueryModule,
    selectPump,
    selectCurveType,
    switchQueryTab,
    loadOptimizationHistory,
    loadAlgorithmComparison,
    loadProcessDetails,
    loadQualityMetrics,
    showQueryResults
};
