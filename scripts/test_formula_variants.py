"""
测试不同的公式变体，找出正确的公式
"""

import numpy as np

# 测试数据
pool_level = 3.495  # m
flow_rate = 1450  # m³/h
L_offset = 2.5  # m
pipe_diameter = 0.3  # m
K_eq = 10.0
P_atm = 0.101325  # MPa
rho = 1000.0  # kg/m³
g = 9.80665  # m/s²

# 计算流速和损失
pipe_area = np.pi * (pipe_diameter ** 2) / 4
velocity = flow_rate / (3600 * pipe_area)
h_loss = K_eq * (velocity ** 2) / (2 * g)

print("=" * 80)
print("测试不同的公式变体")
print("=" * 80)

print(f"\n📋 输入参数:")
print(f"  - pool_level: {pool_level} m")
print(f"  - flow_rate: {flow_rate} m³/h")
print(f"  - L_offset: {L_offset} m")
print(f"  - pipe_diameter: {pipe_diameter} m")
print(f"  - K_eq: {K_eq}")

print(f"\n📊 中间计算:")
print(f"  - pipe_area: {pipe_area:.4f} m²")
print(f"  - velocity: {velocity:.2f} m/s")
print(f"  - h_loss: {h_loss:.2f} m")

print(f"\n" + "=" * 80)
print("测试不同的 h_static 公式")
print("=" * 80)

# 变体1: h_static = pool_level - L_offset（当前公式）
h_static_1 = pool_level - L_offset
pressure_1 = P_atm + rho * g * (h_static_1 - h_loss) / 1e6
print(f"\n变体1: h_static = pool_level - L_offset")
print(f"  - h_static: {h_static_1:.3f} m")
print(f"  - h_static - h_loss: {h_static_1 - h_loss:.3f} m")
print(f"  - pressure: {pressure_1:.6f} MPa")
print(f"  - 结果: {'✅ 合理' if pressure_1 > 0 else '❌ 负数'}")

# 变体2: h_static = pool_level + L_offset
h_static_2 = pool_level + L_offset
pressure_2 = P_atm + rho * g * (h_static_2 - h_loss) / 1e6
print(f"\n变体2: h_static = pool_level + L_offset")
print(f"  - h_static: {h_static_2:.3f} m")
print(f"  - h_static - h_loss: {h_static_2 - h_loss:.3f} m")
print(f"  - pressure: {pressure_2:.6f} MPa")
print(f"  - 结果: {'✅ 合理' if pressure_2 > 0 else '❌ 负数'}")

# 变体3: h_static = L_offset - pool_level
h_static_3 = L_offset - pool_level
pressure_3 = P_atm + rho * g * (h_static_3 - h_loss) / 1e6
print(f"\n变体3: h_static = L_offset - pool_level")
print(f"  - h_static: {h_static_3:.3f} m")
print(f"  - h_static - h_loss: {h_static_3 - h_loss:.3f} m")
print(f"  - pressure: {pressure_3:.6f} MPa")
print(f"  - 结果: {'✅ 合理' if pressure_3 > 0 else '❌ 负数'}")

print(f"\n" + "=" * 80)
print("测试不同的 K_eq 值（使用变体2）")
print("=" * 80)

for K_eq_test in [1.0, 2.0, 5.0, 10.0, 20.0]:
    h_loss_test = K_eq_test * (velocity ** 2) / (2 * g)
    pressure_test = P_atm + rho * g * (h_static_2 - h_loss_test) / 1e6
    print(f"\nK_eq = {K_eq_test}:")
    print(f"  - h_loss: {h_loss_test:.2f} m")
    print(f"  - pressure: {pressure_test:.6f} MPa")
    print(f"  - 结果: {'✅ 合理' if 0 < pressure_test < 1.0 else '❌ 超出范围'}")

print(f"\n" + "=" * 80)
print("测试不同的 L_offset 值（使用变体1，K_eq=1.0）")
print("=" * 80)

K_eq_test = 1.0
h_loss_test = K_eq_test * (velocity ** 2) / (2 * g)

for L_offset_test in [-2.5, -5.0, -10.0, 10.0, 15.0, 20.0]:
    h_static_test = pool_level - L_offset_test
    pressure_test = P_atm + rho * g * (h_static_test - h_loss_test) / 1e6
    print(f"\nL_offset = {L_offset_test} m:")
    print(f"  - h_static: {h_static_test:.2f} m")
    print(f"  - pressure: {pressure_test:.6f} MPa")
    print(f"  - 结果: {'✅ 合理' if 0 < pressure_test < 1.0 else '❌ 超出范围'}")

