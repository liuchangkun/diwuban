-- 目的：在维表中注册新指标 device_phase（运行相位：0停止/1稳态运行/2启动中/3停止中）

BEGIN;

-- 若 dim_metric_config 中不存在，则插入
INSERT INTO public.dim_metric_config(metric_key, unit, unit_display, value_type, valid_min, valid_max, created_at, updated_at)
SELECT 'device_phase','', '运行相位','int', 0, 3, now(), now()
WHERE NOT EXISTS (
  SELECT 1 FROM public.dim_metric_config WHERE metric_key='device_phase'
);

COMMENT ON TABLE public.dim_metric_config IS '指标配置维表：包含指标键、单位、取值范围等。';
-- 单列注释省略，如需全表每列注释可在初始化脚本中补充

COMMIT;

