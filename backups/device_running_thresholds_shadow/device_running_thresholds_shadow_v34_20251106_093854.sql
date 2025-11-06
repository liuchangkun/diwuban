-- 备份表: device_running_thresholds_shadow
-- 时间: 2025-11-06 09:38:54
-- 行数: 3
-- MD5: 64956abfc6b9ea8bab78afb5277408e3

INSERT INTO device_running_thresholds_shadow (device_id, method, version, pf_min, pf_max, computed_at, remark) VALUES (3, 'gmm', 'vB_shadow', 0.98, 0.98, '2025-11-06 09:23:48.331615+08:00', 'fallback_robust(delta=0.321,min_w=0.03,thr=0.664)') ON CONFLICT (device_id, method, version) DO UPDATE SET pf_min = EXCLUDED.pf_min, pf_max = EXCLUDED.pf_max, computed_at = EXCLUDED.computed_at, remark = EXCLUDED.remark;
INSERT INTO device_running_thresholds_shadow (device_id, method, version, pf_min, pf_max, computed_at, remark) VALUES (4, 'gmm', 'vB_shadow', 0.98, 0.99, '2025-11-06 09:23:48.344999+08:00', 'fallback_robust(delta=0.010,min_w=0.07,thr=0.985)') ON CONFLICT (device_id, method, version) DO UPDATE SET pf_min = EXCLUDED.pf_min, pf_max = EXCLUDED.pf_max, computed_at = EXCLUDED.computed_at, remark = EXCLUDED.remark;
INSERT INTO device_running_thresholds_shadow (device_id, method, version, pf_min, pf_max, computed_at, remark) VALUES (5, 'gmm', 'vB_shadow', 0.1005, 0.98, '2025-11-06 09:23:48.354052+08:00', 'fallback_robust(delta=0.583,min_w=0.40,thr=0.954)') ON CONFLICT (device_id, method, version) DO UPDATE SET pf_min = EXCLUDED.pf_min, pf_max = EXCLUDED.pf_max, computed_at = EXCLUDED.computed_at, remark = EXCLUDED.remark;