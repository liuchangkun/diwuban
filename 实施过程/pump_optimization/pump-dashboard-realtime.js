/**
 * 泵站优化控制台 - 实时数据处理模块
 * 负责处理实时数据流、WebSocket连接等
 */

// 实时数据处理器
window.PumpDashboardRealtime = {
    // WebSocket连接
    websocket: null,

    // 配置选项
    config: {
        websocketUrl: 'ws://localhost:8080/ws',
        reconnectInterval: 5000,
        maxReconnectAttempts: 5
    },

    // 状态管理
    state: {
        isConnected: false,
        reconnectAttempts: 0,
        isStreaming: true
    },

    // 数据缓存
    cache: {
        latestData: {},
        historicalData: []
    },

    /**
     * 初始化实时数据处理
     */
    init() {
        console.log('📡 初始化实时数据处理...');
        this.connectWebSocket();
        this.startDataSimulation();
    },

    /**
     * 连接WebSocket
     */
    connectWebSocket() {
        try {
            // 注意：在实际部署中需要替换为真实的WebSocket服务器地址
            this.websocket = new WebSocket(this.config.websocketUrl);

            this.websocket.onopen = (event) => {
                console.log('✅ WebSocket连接已建立');
                this.state.isConnected = true;
                this.state.reconnectAttempts = 0;
                PumpSystem.Notification.success('实时数据连接已建立');
            };

            this.websocket.onmessage = (event) => {
                this.handleWebSocketMessage(event.data);
            };

            this.websocket.onclose = (event) => {
                console.log('❌ WebSocket连接已关闭');
                this.state.isConnected = false;
                this.handleWebSocketClose(event);
            };

            this.websocket.onerror = (error) => {
                console.error('❌ WebSocket错误:', error);
                PumpSystem.Notification.error('实时数据连接出错');
            };
        } catch (error) {
            console.error('❌ WebSocket连接失败:', error);
            this.handleConnectionError();
        }
    },

    /**
     * 处理WebSocket消息
     */
    handleWebSocketMessage(data) {
        try {
            const message = JSON.parse(data);

            switch (message.type) {
                case 'performance':
                    this.handlePerformanceData(message.data);
                    break;
                case 'alert':
                    this.handleAlertData(message.data);
                    break;
                case 'diagnostic':
                    this.handleDiagnosticData(message.data);
                    break;
                case 'optimization':
                    this.handleOptimizationData(message.data);
                    break;
                default:
                    console.log('未知消息类型:', message.type);
            }
        } catch (error) {
            console.error('处理WebSocket消息失败:', error);
        }
    },

    /**
     * 处理性能数据
     */
    handlePerformanceData(data) {
        // 更新缓存
        this.cache.latestData.performance = data;

        // 更新UI
        if (this.state.isStreaming) {
            this.updatePerformanceUI(data);
        }
    },

    /**
     * 处理报警数据
     */
    handleAlertData(data) {
        // 更新缓存
        this.cache.latestData.alert = data;

        // 添加到实时数据流
        if (this.state.isStreaming) {
            this.addAlertToStream(data);
        }
    },

    /**
     * 处理诊断数据
     */
    handleDiagnosticData(data) {
        // 更新缓存
        this.cache.latestData.diagnostic = data;

        // 更新诊断面板
        if (this.state.isStreaming) {
            this.updateDiagnosticUI(data);
        }
    },

    /**
     * 处理优化数据
     */
    handleOptimizationData(data) {
        // 更新缓存
        this.cache.latestData.optimization = data;

        // 添加到实时数据流
        if (this.state.isStreaming) {
            this.addOptimizationToStream(data);
        }
    },

    /**
     * 更新性能UI
     */
    updatePerformanceUI(data) {
        // 更新相关指标显示
        if (data.efficiency) {
            document.getElementById('totalEfficiency').textContent = data.efficiency.toFixed(1) + '%';
        }

        if (data.flow) {
            document.getElementById('totalFlow').textContent = data.flow.toFixed(0);
        }

        if (data.power) {
            document.getElementById('totalPower').textContent = data.power.toFixed(1);
        }

        // 更新图表数据
        if (PumpDashboardCharts.charts.stationPerformance) {
            // 这里可以更新图表数据
        }
    },

    /**
     * 添加报警到数据流
     */
    addAlertToStream(data) {
        const stream = document.getElementById('realTimeStream');
        if (!stream) return;

        const item = document.createElement('div');
        item.className = 'stream-item alert';
        item.innerHTML = `
            <div class="stream-timestamp">${new Date().toLocaleTimeString()}</div>
            <div class="stream-content">
                🚨 ${data.message || '系统报警'}
            </div>
            <div class="stream-metrics">
                <span class="metric-item">设备: ${data.device || '未知'}</span>
                <span class="metric-item">级别: ${data.level || '警告'}</span>
            </div>
        `;

        stream.insertBefore(item, stream.firstChild);
        this.limitStreamItems(stream);
    },

    /**
     * 添加优化信息到数据流
     */
    addOptimizationToStream(data) {
        const stream = document.getElementById('realTimeStream');
        if (!stream) return;

        const item = document.createElement('div');
        item.className = 'stream-item optimization';
        item.innerHTML = `
            <div class="stream-timestamp">${new Date().toLocaleTimeString()}</div>
            <div class="stream-content">
                ⚡ ${data.message || '优化建议'}
            </div>
            <div class="stream-metrics">
                <span class="metric-item">预期效果: ${data.expectedBenefit || '显著'}</span>
                <span class="metric-item">实施难度: ${data.implementationDifficulty || '中等'}</span>
            </div>
        `;

        stream.insertBefore(item, stream.firstChild);
        this.limitStreamItems(stream);
    },

    /**
     * 更新诊断UI
     */
    updateDiagnosticUI(data) {
        // 更新诊断面板数据
        if (data.healthScore) {
            document.getElementById('healthScore').textContent = data.healthScore.toFixed(1);
        }

        if (data.riskIndex) {
            document.getElementById('riskIndex').textContent = data.riskIndex.toFixed(1);
        }
    },

    /**
     * 限制数据流项目数量
     */
    limitStreamItems(stream) {
        while (stream.children.length > 100) {
            stream.removeChild(stream.lastChild);
        }
    },

    /**
     * 处理WebSocket关闭
     */
    handleWebSocketClose(event) {
        this.state.isConnected = false;

        if (event.wasClean) {
            console.log(`WebSocket连接已干净关闭: ${event.code} ${event.reason}`);
        } else {
            console.log('WebSocket连接意外中断');
            this.attemptReconnect();
        }
    },

    /**
     * 处理连接错误
     */
    handleConnectionError() {
        PumpSystem.Notification.error('实时数据连接失败，将使用模拟数据');
        this.startDataSimulation();
    },

    /**
     * 尝试重新连接
     */
    attemptReconnect() {
        if (this.state.reconnectAttempts < this.config.maxReconnectAttempts) {
            this.state.reconnectAttempts++;
            console.log(`尝试重新连接 (${this.state.reconnectAttempts}/${this.config.maxReconnectAttempts})...`);

            setTimeout(() => {
                this.connectWebSocket();
            }, this.config.reconnectInterval);
        } else {
            console.log('达到最大重连次数，停止重连');
            PumpSystem.Notification.error('实时数据连接失败，请检查网络设置');
            this.startDataSimulation();
        }
    },

    /**
     * 开始数据模拟（备用方案）
     */
    startDataSimulation() {
        console.log('🔄 启动数据模拟...');

        setInterval(() => {
            if (this.state.isStreaming) {
                this.generateSimulatedData();
            }
        }, 3000);
    },

    /**
     * 生成模拟数据
     */
    generateSimulatedData() {
        // 生成性能数据
        const performanceData = {
            efficiency: 80 + Math.random() * 10,
            flow: 1200 + Math.random() * 200,
            power: 300 + Math.random() * 100,
            timestamp: new Date().toISOString()
        };

        this.handlePerformanceData(performanceData);

        // 随机生成报警或优化信息
        if (Math.random() > 0.7) {
            const eventType = Math.random() > 0.5 ? 'alert' : 'optimization';

            if (eventType === 'alert') {
                const alertData = {
                    message: this.getRandomAlertMessage(),
                    device: this.getRandomDevice(),
                    level: ['警告', '严重'][Math.floor(Math.random() * 2)],
                    timestamp: new Date().toISOString()
                };
                this.handleAlertData(alertData);
            } else {
                const optimizationData = {
                    message: this.getRandomOptimizationMessage(),
                    expectedBenefit: ['显著', '中等', '轻微'][Math.floor(Math.random() * 3)],
                    implementationDifficulty: ['简单', '中等', '复杂'][Math.floor(Math.random() * 3)],
                    timestamp: new Date().toISOString()
                };
                this.handleOptimizationData(optimizationData);
            }
        }
    },

    /**
     * 获取随机报警消息
     */
    getRandomAlertMessage() {
        const messages = [
            '设备温度异常升高',
            '振动值超过阈值',
            '压力波动较大',
            '流量计读数异常',
            '电机电流不稳定',
            '密封件泄漏风险'
        ];
        return messages[Math.floor(Math.random() * messages.length)];
    },

    /**
     * 获取随机优化消息
     */
    getRandomOptimizationMessage() {
        const messages = [
            '建议调整变频器频率',
            '优化泵组运行组合',
            '调整出口阀门开度',
            '清洁叶轮提高效率',
            '校准传感器读数',
            '更新控制策略参数'
        ];
        return messages[Math.floor(Math.random() * messages.length)];
    },

    /**
     * 获取随机设备
     */
    getRandomDevice() {
        const devices = ['泵站A-01', '泵站A-02', '泵站B-01', '泵站B-02', '泵站C-01', '泵站C-02'];
        return devices[Math.floor(Math.random() * devices.length)];
    },

    /**
     * 切换数据流
     */
    toggleStreaming() {
        this.state.isStreaming = !this.state.isStreaming;
        PumpSystem.Notification.info(this.state.isStreaming ? '已开始数据流' : '已暂停数据流');
    },

    /**
     * 发送数据到服务器
     */
    sendData(data) {
        if (this.websocket && this.state.isConnected) {
            try {
                this.websocket.send(JSON.stringify(data));
                return true;
            } catch (error) {
                console.error('发送数据失败:', error);
                return false;
            }
        }
        return false;
    },

    /**
     * 关闭连接
     */
    closeConnection() {
        if (this.websocket) {
            this.websocket.close();
        }
    }
};

// 页面加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        PumpDashboardRealtime.init();
    });
} else {
    PumpDashboardRealtime.init();
}

// 页面卸载时关闭连接
window.addEventListener('beforeunload', function () {
    if (window.PumpDashboardRealtime) {
        window.PumpDashboardRealtime.closeConnection();
    }
});
