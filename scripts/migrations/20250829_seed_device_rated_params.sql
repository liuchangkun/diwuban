-- 设备额定参数初始化（根据 dim_stations/dim_devices 实际清单生成）
-- 站点：
--   id=1 名称=二期供水泵房（6台变频泵 + 总管）
--   id=2 名称=二期取水泵房（2台变频泵、3台软启泵 + 总管）
-- 注意：执行前请先运行 20250829_add_value_json_to_device_rated_params.sql 迁移，确保 value_json 字段存在。

BEGIN;

-- 为避免重复，使用 UPSERT（device_id, param_key 唯一约束）

-- ============ 站点1：二期供水泵房（设备ID 1..6 为泵，7 为总管）============
-- 默认：VFD 泵 -> 50Hz、p=2、η=0.78、额定流量400 m3/h、额定扬程25 m

-- 通用数值参数（站点1：6台变频泵）
INSERT INTO public.device_rated_params(device_id,param_key,value_numeric,unit,source)
VALUES
  -- 1号泵（变频泵）
  (1,'rated_frequency',50,'Hz','初始化默认值'),(1,'poles_pair',2,NULL,'极对数'),(1,'rated_efficiency',0.78,NULL,'额定效率'),(1,'rated_flow',400,'m3/h','额定流量'),(1,'rated_head',25,'m','额定扬程'),
  (1,'eta_motor',0.93,NULL,'电机效率'),(1,'eta_vfd',0.97,NULL,'变频器效率'),
  -- 2号泵（变频泵）
  (2,'rated_frequency',50,'Hz','初始化默认值'),(2,'poles_pair',2,NULL,'极对数'),(2,'rated_efficiency',0.78,NULL,'额定效率'),(2,'rated_flow',400,'m3/h','额定流量'),(2,'rated_head',25,'m','额定扬程'),
  (2,'eta_motor',0.93,NULL,'电机效率'),(2,'eta_vfd',0.97,NULL,'变频器效率'),
  -- 3号泵（变频泵）
  (3,'rated_frequency',50,'Hz','初始化默认值'),(3,'poles_pair',2,NULL,'极对数'),(3,'rated_efficiency',0.78,NULL,'额定效率'),(3,'rated_flow',400,'m3/h','额定流量'),(3,'rated_head',25,'m','额定扬程'),
  (3,'eta_motor',0.93,NULL,'电机效率'),(3,'eta_vfd',0.97,NULL,'变频器效率'),
  -- 4号泵（变频泵）
  (4,'rated_frequency',50,'Hz','初始化默认值'),(4,'poles_pair',2,NULL,'极对数'),(4,'rated_efficiency',0.78,NULL,'额定效率'),(4,'rated_flow',400,'m3/h','额定流量'),(4,'rated_head',25,'m','额定扬程'),
  (4,'eta_motor',0.93,NULL,'电机效率'),(4,'eta_vfd',0.97,NULL,'变频器效率'),
  -- 5号泵（变频泵）
  (5,'rated_frequency',50,'Hz','初始化默认值'),(5,'poles_pair',2,NULL,'极对数'),(5,'rated_efficiency',0.78,NULL,'额定效率'),(5,'rated_flow',400,'m3/h','额定流量'),(5,'rated_head',25,'m','额定扬程'),
  (5,'eta_motor',0.93,NULL,'电机效率'),(5,'eta_vfd',0.97,NULL,'变频器效率'),
  -- 6号泵（变频泵）
  (6,'rated_frequency',50,'Hz','初始化默认值'),(6,'poles_pair',2,NULL,'极对数'),(6,'rated_efficiency',0.78,NULL,'额定效率'),(6,'rated_flow',400,'m3/h','额定流量'),(6,'rated_head',25,'m','额定扬程'),
  (6,'eta_motor',0.93,NULL,'电机效率'),(6,'eta_vfd',0.97,NULL,'变频器效率')
ON CONFLICT (device_id,param_key) DO UPDATE SET value_numeric=EXCLUDED.value_numeric, unit=EXCLUDED.unit, source=EXCLUDED.source, updated_at=now();


-- ============ 站点2：二期取水泵房（设备ID 8..12 为泵，13 为总管）============
-- 变频泵（9,12）：η=0.76；软启泵（8,10,11）：η=0.74；额定流量350 m3/h、扬程22 m

-- 数值参数（站点2：2台变频泵 + 3台软启泵）
INSERT INTO public.device_rated_params(device_id,param_key,value_numeric,unit,source)
VALUES
  -- 1号泵（软启泵）
  (8,'rated_frequency',50,'Hz','初始化默认值'),(8,'poles_pair',2,NULL,'极对数'),(8,'rated_efficiency',0.74,NULL,'额定效率'),(8,'rated_flow',350,'m3/h','额定流量'),(8,'rated_head',22,'m','额定扬程'),
  (8,'eta_motor',0.90,NULL,'电机效率'),(8,'eta_vfd',1.00,NULL,'软启动无变频损耗'),
  -- 2号泵（变频泵）
  (9,'rated_frequency',50,'Hz','初始化默认值'),(9,'poles_pair',2,NULL,'极对数'),(9,'rated_efficiency',0.76,NULL,'额定效率'),(9,'rated_flow',350,'m3/h','额定流量'),(9,'rated_head',22,'m','额定扬程'),
  (9,'eta_motor',0.92,NULL,'电机效率'),(9,'eta_vfd',0.97,NULL,'变频器效率'),
  -- 3号泵（软启泵）
  (10,'rated_frequency',50,'Hz','初始化默认值'),(10,'poles_pair',2,NULL,'极对数'),(10,'rated_efficiency',0.74,NULL,'额定效率'),(10,'rated_flow',350,'m3/h','额定流量'),(10,'rated_head',22,'m','额定扬程'),
  (10,'eta_motor',0.90,NULL,'电机效率'),(10,'eta_vfd',1.00,NULL,'软启动无变频损耗'),
  -- 4号泵（软启泵）
  (11,'rated_frequency',50,'Hz','初始化默认值'),(11,'poles_pair',2,NULL,'极对数'),(11,'rated_efficiency',0.74,NULL,'额定效率'),(11,'rated_flow',350,'m3/h','额定流量'),(11,'rated_head',22,'m','额定扬程'),
  (11,'eta_motor',0.90,NULL,'电机效率'),(11,'eta_vfd',1.00,NULL,'软启动无变频损耗'),
  -- 5号泵（变频泵）
  (12,'rated_frequency',50,'Hz','初始化默认值'),(12,'poles_pair',2,NULL,'极对数'),(12,'rated_efficiency',0.76,NULL,'额定效率'),(12,'rated_flow',350,'m3/h','额定流量'),(12,'rated_head',22,'m','额定扬程'),
  (12,'eta_motor',0.92,NULL,'电机效率'),(12,'eta_vfd',0.97,NULL,'变频器效率')
ON CONFLICT (device_id,param_key) DO UPDATE SET value_numeric=EXCLUDED.value_numeric, unit=EXCLUDED.unit, source=EXCLUDED.source, updated_at=now();


-- ============ 总管（main_pipeline）默认管网参数（含中文说明） ============
-- 站点1：设备ID 7
INSERT INTO public.device_rated_params(device_id,param_key,value_numeric,unit,source)
VALUES
  (7,'pipe_diameter',0.40,'m','主管内径（米，默认值，可调整）'),
  (7,'pipe_length',150.0,'m','代表性管段长度（米，默认值，可调整）'),
  (7,'roughness_rel',0.0005,NULL,'相对粗糙度 ε/D（无量纲，默认值）'),
  (7,'C_hazen',120,NULL,'海泽-威廉系数（经验值，默认120）')
ON CONFLICT (device_id,param_key) DO UPDATE SET value_numeric=EXCLUDED.value_numeric, unit=EXCLUDED.unit, source=EXCLUDED.source, updated_at=now();

-- 站点2：设备ID 13
INSERT INTO public.device_rated_params(device_id,param_key,value_numeric,unit,source)
VALUES
  (13,'pipe_diameter',0.50,'m','主管内径（米，默认值，可调整）'),
  (13,'pipe_length',200.0,'m','代表性管段长度（米，默认值，可调整）'),
  (13,'roughness_rel',0.0005,NULL,'相对粗糙度 ε/D（无量纲，默认值）'),
  (13,'C_hazen',120,NULL,'海泽-威廉系数（经验值，默认120）')
ON CONFLICT (device_id,param_key) DO UPDATE SET value_numeric=EXCLUDED.value_numeric, unit=EXCLUDED.unit, source=EXCLUDED.source, updated_at=now();

COMMIT;

