\encoding UTF8
SET client_encoding = 'UTF8';

-- 为 device_running_thresholds 添加表与字段注释（中文，避免使用特殊字符）

COMMENT ON TABLE public.device_running_thresholds IS
'设备秒级运行判断的集中阈值配置表。用于统一管理每台设备启用的信号、开关滞回阈值、缺报延续与防抖参数。';

COMMENT ON COLUMN public.device_running_thresholds.device_id IS '设备ID，对应 dim_devices.id，用于唯一定位设备';
COMMENT ON COLUMN public.device_running_thresholds.enable_i IS '是否启用电流信号参与判断；电流取三相电流中的最大值';
COMMENT ON COLUMN public.device_running_thresholds.enable_p IS '是否启用有功功率信号参与判断';
COMMENT ON COLUMN public.device_running_thresholds.enable_f IS '是否启用频率信号参与判断；软启泵通常为 false';

COMMENT ON COLUMN public.device_running_thresholds.i_on  IS '电流开启阈值，用于判定运行；建议高于停机残余电流';
COMMENT ON COLUMN public.device_running_thresholds.i_off IS '电流关闭阈值，用于判定关机；建议略高于残余电流';
COMMENT ON COLUMN public.device_running_thresholds.p_on  IS '有功功率开启阈值；例如停机残余约為 10，可将 p_on 设为 30';
COMMENT ON COLUMN public.device_running_thresholds.p_off IS '有功功率关闭阈值；例如可将 p_off 设为 15';
COMMENT ON COLUMN public.device_running_thresholds.f_on  IS '频率开启阈值；例如停机残余约為 1-3，可将 f_on 设为 6';
COMMENT ON COLUMN public.device_running_thresholds.f_off IS '频率关闭阈值；例如可将 f_off 设为 3';

COMMENT ON COLUMN public.device_running_thresholds.grace_hold_secs IS '当秒所有启用信号都缺报时，沿用上一秒状态的最长秒数；0 表示不延续';
COMMENT ON COLUMN public.device_running_thresholds.min_run_secs    IS '段落化防抖时的最短运行段长度；逐秒输出不受影响';
COMMENT ON COLUMN public.device_running_thresholds.min_stop_secs   IS '段落化防抖时的最短停机段长度；逐秒输出不受影响';
COMMENT ON COLUMN public.device_running_thresholds.smoothing_secs  IS '可选的平滑窗口秒数；0 表示不平滑';

COMMENT ON COLUMN public.device_running_thresholds.updated_at IS '配置更新时间';
COMMENT ON COLUMN public.device_running_thresholds.updated_by IS '配置变更人或来源备注';

