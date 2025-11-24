"""
特性曲线拟合方法 - 模拟数据测试脚本

用于验证已实现的物理模型和数学方法的拟合效果。
"""

import numpy as np
import sys
sys.path.insert(0, '.')

# 设置随机种子以确保可重复性
np.random.seed(42)

print('='*60)
print('特性曲线拟合方法 - 模拟数据测试')
print('='*60)

# ==================== 1. 生成模拟泵特性数据 ====================
print('\n📊 1. 生成模拟泵特性数据')
print('-'*40)

# 真实泵参数（模拟）
H0_true = 52.0  # 零流量扬程 (m)
K_true = 0.0045  # 阻力系数
P0_true = 8.5   # 空载功率 (kW)
K_power_true = 0.12  # 功率系数
n_power_true = 1.2   # 功率指数

# 生成流量数据 (m³/h)
Q = np.linspace(0, 100, 20)

# 生成Q-H数据（带噪声）
H_true = H0_true - K_true * Q**2
H_noise = H_true + np.random.normal(0, 0.5, len(Q))

# 生成Q-P数据（带噪声）
P_true = P0_true + K_power_true * Q**n_power_true
P_noise = P_true + np.random.normal(0, 0.3, len(Q))

# 生成Q-η数据（效率曲线，高斯型）
eta_max = 0.82
Q_bep = 65  # 最高效率点流量
sigma = 25
eta_true = eta_max * np.exp(-((Q - Q_bep)**2) / (2 * sigma**2))
eta_noise = eta_true + np.random.normal(0, 0.02, len(Q))
eta_noise = np.clip(eta_noise, 0, 1)

print(f'流量范围: {Q.min():.1f} - {Q.max():.1f} m³/h')
print(f'扬程范围: {H_noise.min():.2f} - {H_noise.max():.2f} m')
print(f'功率范围: {P_noise.min():.2f} - {P_noise.max():.2f} kW')
print(f'效率范围: {eta_noise.min():.3f} - {eta_noise.max():.3f}')

# ==================== 2. 测试物理模型方法 ====================
print('\n📊 2. 测试物理模型方法')
print('-'*40)

from app.services.characteristic_curves.methods.physics import (
    PhysicsPumpCharMethod,
    PhysicsPowerEqMethod,
)

# 2.1 泵特性方程测试
print('\n🔹 泵特性方程 (physics_pump_char)')
pump_method = PhysicsPumpCharMethod()
result_pump = pump_method.fit(Q, H_noise)

H0_fit = result_pump.coefficients["H0"]
K_fit = result_pump.coefficients["K"]
print(f'  真实参数: H0={H0_true}, K={K_true}')
print(f'  拟合参数: H0={H0_fit:.4f}, K={K_fit:.6f}')
print(f'  参数误差: H0误差={abs(H0_fit-H0_true):.4f}, K误差={abs(K_fit-K_true):.6f}')
print(f'  R² = {result_pump.r_squared:.6f}')
print(f'  RMSE = {result_pump.rmse:.4f}')
print(f'  公式: {result_pump.formula}')
print(f'  物理有效: {result_pump.metadata.get("physics_valid", False)}')

# 2.2 功率方程测试
print('\n🔹 功率方程 (physics_power_eq)')
power_method = PhysicsPowerEqMethod()
result_power = power_method.fit(Q, P_noise)

P0_fit = result_power.coefficients["P0"]
K_p_fit = result_power.coefficients["K"]
n_fit = result_power.coefficients["n"]
print(f'  真实参数: P0={P0_true}, K={K_power_true}, n={n_power_true}')
print(f'  拟合参数: P0={P0_fit:.4f}, K={K_p_fit:.6f}, n={n_fit:.4f}')
print(f'  R² = {result_power.r_squared:.6f}')
print(f'  RMSE = {result_power.rmse:.4f}')
print(f'  公式: {result_power.formula}')
print(f'  物理有效: {result_power.metadata.get("physics_valid", False)}')

# ==================== 3. 测试数学方法 ====================
print('\n📊 3. 测试数学方法')
print('-'*40)

from app.services.characteristic_curves.methods.math import (
    MathPoly2Method,
    MathPoly3Method,
    MathStatGaussianMethod,
    MathSplineCubicMethod,
)

# 3.1 多项式方法 - Q-H曲线
print('\n🔹 2次多项式 (math_poly_2) - Q-H曲线')
poly2 = MathPoly2Method()
result_poly2 = poly2.fit(Q, H_noise)
print(f'  R² = {result_poly2.r_squared:.6f}')
print(f'  RMSE = {result_poly2.rmse:.4f}')
print(f'  公式: {result_poly2.formula}')

print('\n🔹 3次多项式 (math_poly_3) - Q-H曲线')
poly3 = MathPoly3Method()
result_poly3 = poly3.fit(Q, H_noise)
print(f'  R² = {result_poly3.r_squared:.6f}')
print(f'  RMSE = {result_poly3.rmse:.4f}')
print(f'  公式: {result_poly3.formula}')

# 3.2 高斯方法 - Q-η曲线
print('\n🔹 高斯函数 (math_stat_gaussian) - Q-η曲线')
gaussian = MathStatGaussianMethod()
result_gaussian = gaussian.fit(Q, eta_noise)
A_fit = result_gaussian.coefficients.get("A", 0)
mu_fit = result_gaussian.coefficients.get("mu", 0)
sigma_fit = result_gaussian.coefficients.get("sigma", 0)
print(f'  真实参数: A={eta_max}, mu={Q_bep}, sigma={sigma}')
print(f'  拟合参数: A={A_fit:.4f}, mu={mu_fit:.2f}, sigma={sigma_fit:.2f}')
print(f'  R² = {result_gaussian.r_squared:.6f}')
print(f'  RMSE = {result_gaussian.rmse:.4f}')

# 3.3 样条方法 - Q-H曲线
print('\n🔹 三次样条 (math_spline_cubic) - Q-H曲线')
spline = MathSplineCubicMethod()
result_spline = spline.fit(Q, H_noise)
print(f'  R² = {result_spline.r_squared:.6f}')
print(f'  RMSE = {result_spline.rmse:.4f}')




# ==================== 4. 方法对比 ====================
print('\n📊 4. Q-H曲线拟合方法对比')
print('-'*40)
print(f"{'方法':<25} {'R²':>10} {'RMSE':>10}")
print('-'*45)
results = [
    ('physics_pump_char', result_pump),
    ('math_poly_2', result_poly2),
    ('math_poly_3', result_poly3),
    ('math_spline_cubic', result_spline),
]
for name, r in results:
    print(f'{name:<25} {r.r_squared:>10.6f} {r.rmse:>10.4f}')

# ==================== 5. 预测验证 ====================
print('\n📊 5. 预测验证')
print('-'*40)

# 在新点上预测
Q_test = np.array([25, 50, 75])
print(f'测试流量点: {Q_test}')

# 真实值
H_test_true = H0_true - K_true * Q_test**2
print(f'真实扬程: {H_test_true}')

# 各方法预测
if result_pump.predict_func:
    H_pred_pump = result_pump.predict_func(Q_test)
    print(f'物理模型预测: {H_pred_pump}')
    err_pump = np.abs(H_pred_pump - H_test_true)
    print(f'物理模型误差: {err_pump} (平均: {err_pump.mean():.4f})')

if result_poly2.predict_func:
    H_pred_poly2 = result_poly2.predict_func(Q_test)
    print(f'2次多项式预测: {H_pred_poly2}')
    err_poly2 = np.abs(H_pred_poly2 - H_test_true)
    print(f'2次多项式误差: {err_poly2} (平均: {err_poly2.mean():.4f})')

print('\n' + '='*60)
print('✅ 模拟数据测试完成')
print('='*60)
