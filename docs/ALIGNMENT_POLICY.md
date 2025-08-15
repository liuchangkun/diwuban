# ALIGNMENT_POLICY（时间与网格对齐策略）

## 1. 时区与精度
- 默认 Asia/Shanghai → 入库存 UTC，保留本地时区视图。
- 最小精度：秒（保留更高精度）。

## 2. 网格选择（auto）
- 取站内各 metric 邻近时间差中位数 dt_med；dt* = min(dt_med)；映射至 {1s, 5s, 1min}。
- 最近邻容差 = 0.5 × 网格；超容差置 NULL。

## 3. 插值与阶梯
- 累计量禁插值，仅阶梯保持。
- 瞬时量默认不插值，可按需开启线性插值但需审计。

## 4. 滞后补偿
- 允许对特定 metric 配置固定秒级滞后，提高跨测点对齐一致性。

## 5. 输出要求
- 对齐输出列：station_id, device_id, metric, ts_local, ts_utc, value, grid, version。

