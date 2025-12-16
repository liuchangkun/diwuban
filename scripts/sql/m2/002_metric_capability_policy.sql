-- 指标获取/计算能力策略表（依据图片转录，策略元数据存放表）
-- 注意：创建表属于结构变更，请在执行前确认授权与目标环境

CREATE TABLE IF NOT EXISTS public.metric_capability_policy (
    metric_key          text PRIMARY KEY,
    acquisition_status  text NOT NULL CHECK (acquisition_status IN ('不能','可能','可以')),
    compute_flag        text NOT NULL CHECK (compute_flag IN ('需要','不需要')),
    updated_at          timestamptz DEFAULT now(),
    updated_by          text
);

COMMENT ON TABLE public.metric_capability_policy IS '指标获取/计算能力策略表：记录每个 metric_key 的获取情况(不能/可能/可以)与是否需要计算(需要/不需要)';
COMMENT ON COLUMN public.metric_capability_policy.metric_key IS '指标键；与 dim_metric_config.metric_key 一一对应';
COMMENT ON COLUMN public.metric_capability_policy.acquisition_status IS '获取情况：不能/可能/可以；不能=无法直接采集，可能=部分站点可采，
可以=肯定可采';
COMMENT ON COLUMN public.metric_capability_policy.compute_flag IS '是否计算补充：需要=必须通过其他指标计算获得；不需要=不可计算或不需要计算';
COMMENT ON COLUMN public.metric_capability_policy.updated_at IS '策略最后更新时间';
COMMENT ON COLUMN public.metric_capability_policy.updated_by IS '最后更新人（可填 sys/脚本名）';

