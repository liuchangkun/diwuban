"""
泵组特性曲线拟合与增强数据补齐实现
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from dataclasses import dataclass
from enum import Enum
import asyncio
import logging
from datetime import datetime, timedelta

from app.adapters.db.gateway import DatabaseGateway

logger = logging.getLogger(__name__)

class PumpGroupCurveType(Enum):
    """泵组曲线类型"""
    GROUP_EFFICIENCY_LOAD = "group_efficiency_load"
    GROUP_COORDINATION = "group_coordination"
    GROUP_IMBALANCE = "group_imbalance"
    GROUP_FREQUENCY_DIST = "group_frequency_distribution"

@dataclass
class CurveQuality:
    r2_score: float
    rmse: float
    sample_count: int
    confidence: float

class PumpGroupCurveFitter:
    """泵组特性曲线拟合器"""
    
    def __init__(self, gateway: DatabaseGateway):
        self.gateway = gateway
        
    async def fit_pump_group_curves(self, station_id: str, days: int = 30) -> Dict:
        """拟合泵组特性曲线"""
        
        # 获取泵组数据
        pump_data = await self._get_pump_group_data(station_id, days)
        
        if pump_data.empty:
            logger.warning(f"泵站 {station_id} 缺少泵组数据")
            return {}
        
        results = {}
        
        # 并行拟合多条曲线
        curve_types = [
            PumpGroupCurveType.GROUP_EFFICIENCY_LOAD,
            PumpGroupCurveType.GROUP_COORDINATION,
            PumpGroupCurveType.GROUP_IMBALANCE,
            PumpGroupCurveType.GROUP_FREQUENCY_DIST
        ]
        
        for curve_type in curve_types:
            try:
                result = await self._fit_single_curve(curve_type, pump_data)
                results[curve_type.value] = result
            except Exception as e:
                logger.error(f"拟合曲线 {curve_type.value} 失败: {e}")
                results[curve_type.value] = self._get_default_curve(curve_type)
        
        return results
    
    async def _get_pump_group_data(self, station_id: str, days: int) -> pd.DataFrame:
        """获取泵组数据"""
        
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        sql = """
        SELECT 
            fm.metric_time,
            fm.device_id,
            fm.metric_type,
            fm.metric_value
        FROM fact_measurements fm
        JOIN dim_devices d ON fm.device_id = d.device_id
        WHERE fm.station_id = %s 
            AND fm.metric_time BETWEEN %s AND %s
            AND d.device_type = 'pump'
            AND fm.metric_type IN (
                'pump_flow_rate', 'pump_efficiency', 
                'pump_active_power', 'pump_frequency'
            )
        ORDER BY fm.metric_time, fm.device_id
        """
        
        result = await self.gateway.execute_query(sql, station_id, start_time, end_time)
        
        if not result:
            return pd.DataFrame()
        
        df = pd.DataFrame(result)
        pivot_df = df.pivot_table(
            index=['metric_time', 'device_id'], 
            columns='metric_type', 
            values='metric_value'
        ).reset_index()
        
        return pivot_df
    
    async def _fit_single_curve(self, curve_type: PumpGroupCurveType, data: pd.DataFrame) -> Dict:
        """拟合单条曲线"""
        
        # 预处理数据
        processed_data = await self._preprocess_data(curve_type, data)
        
        if processed_data.empty:
            return self._get_default_curve(curve_type)
        
        # 提取X, Y数据
        x_data, y_data = self._extract_xy_data(curve_type, processed_data)
        
        # 数据筛选（排除补齐数据）
        filtered_x, filtered_y = self._filter_original_data(x_data, y_data)
        
        if len(filtered_x) < 10:
            return self._get_default_curve(curve_type)
        
        # 降级拟合策略
        return await self._fit_with_fallback(filtered_x, filtered_y, curve_type)
    
    async def _preprocess_data(self, curve_type: PumpGroupCurveType, data: pd.DataFrame) -> pd.DataFrame:
        """数据预处理"""
        
        if curve_type == PumpGroupCurveType.GROUP_EFFICIENCY_LOAD:
            return self._calc_efficiency_load(data)
        elif curve_type == PumpGroupCurveType.GROUP_COORDINATION:
            return self._calc_coordination(data)
        elif curve_type == PumpGroupCurveType.GROUP_IMBALANCE:
            return self._calc_imbalance(data)
        elif curve_type == PumpGroupCurveType.GROUP_FREQUENCY_DIST:
            return self._calc_frequency_distribution(data)
        else:
            return data
    
    def _calc_efficiency_load(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算效率-负载率"""
        group_metrics = []
        
        for time_point, group in data.groupby('metric_time'):
            total_flow = group['pump_flow_rate'].sum()
            avg_efficiency = (group['pump_efficiency'] * group['pump_flow_rate']).sum() / total_flow if total_flow > 0 else 0
            load_ratio = (total_flow / 200) * 100  # 假设设计流量200
            
            group_metrics.append({
                'load_ratio': load_ratio,
                'avg_efficiency': avg_efficiency
            })
        
        return pd.DataFrame(group_metrics)
    
    def _calc_coordination(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算协调系数"""
        coordination_metrics = []
        
        for time_point, group in data.groupby('metric_time'):
            pump_count = len(group)
            total_flow = group['pump_flow_rate'].sum()
            group_efficiency = (group['pump_efficiency'] * group['pump_flow_rate']).sum() / total_flow if total_flow > 0 else 0
            single_avg = group['pump_efficiency'].mean()
            coordination = group_efficiency / single_avg if single_avg > 0 else 1.0
            
            coordination_metrics.append({
                'pump_count': pump_count,
                'coordination_coeff': coordination
            })
        
        return pd.DataFrame(coordination_metrics)
    
    def _calc_imbalance(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算不平衡系数"""
        imbalance_metrics = []
        
        for time_point, group in data.groupby('metric_time'):
            flows = group['pump_flow_rate'].dropna()
            if len(flows) < 2:
                continue
                
            flow_ratio = flows.max() / flows.min() if flows.min() > 0 else 1.0
            ideal_eff = group['pump_efficiency'].mean()
            actual_eff = (group['pump_efficiency'] * group['pump_flow_rate']).sum() / flows.sum()
            efficiency_loss = ideal_eff - actual_eff
            
            imbalance_metrics.append({
                'flow_ratio': flow_ratio,
                'efficiency_loss': efficiency_loss
            })
        
        return pd.DataFrame(imbalance_metrics)
    
    def _calc_frequency_distribution(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算频率分布"""
        freq_metrics = []
        
        for time_point, group in data.groupby('metric_time'):
            frequencies = group['pump_frequency'].dropna()
            if len(frequencies) < 2:
                continue
                
            freq_std = frequencies.std()
            total_flow = group['pump_flow_rate'].sum()
            group_eff = (group['pump_efficiency'] * group['pump_flow_rate']).sum() / total_flow if total_flow > 0 else 0
            
            freq_metrics.append({
                'frequency_std': freq_std,
                'group_efficiency': group_eff
            })
        
        return pd.DataFrame(freq_metrics)
    
    def _extract_xy_data(self, curve_type: PumpGroupCurveType, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """提取X, Y数据"""
        
        mapping = {
            PumpGroupCurveType.GROUP_EFFICIENCY_LOAD: ('load_ratio', 'avg_efficiency'),
            PumpGroupCurveType.GROUP_COORDINATION: ('pump_count', 'coordination_coeff'),
            PumpGroupCurveType.GROUP_IMBALANCE: ('flow_ratio', 'efficiency_loss'),
            PumpGroupCurveType.GROUP_FREQUENCY_DIST: ('frequency_std', 'group_efficiency')
        }
        
        x_col, y_col = mapping[curve_type]
        x_data = data[x_col].values
        y_data = data[y_col].values
        
        # 过滤有效数据
        valid_mask = ~(np.isnan(x_data) | np.isnan(y_data))
        return x_data[valid_mask], y_data[valid_mask]
    
    def _filter_original_data(self, x_data: np.ndarray, y_data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """排除补齐数据，只用原始数据"""
        
        # 检测FFILL模式：连续相同值
        ffill_mask = np.ones(len(y_data), dtype=bool)
        for i in range(1, len(y_data)):
            if y_data[i] == y_data[i-1]:
                # 连续相同值，可能是FFILL
                j = i
                while j < len(y_data) and y_data[j] == y_data[i-1]:
                    j += 1
                if j - i + 1 >= 3:  # 连续3个以上相同值
                    ffill_mask[i-1:j] = False
        
        # 检测统计异常的均值填充
        rolling_mean = pd.Series(y_data).rolling(window=5, center=True).mean()
        mean_fill_mask = ~(np.abs(y_data - rolling_mean) < 1e-6)
        
        # 检测过于平滑的REG填充
        if len(y_data) > 5:
            second_diff = np.diff(y_data, n=2)
            smooth_threshold = np.std(second_diff) * 0.1
            smooth_mask = np.ones(len(y_data), dtype=bool)
            smooth_mask[2:] = np.abs(second_diff) >= smooth_threshold
        else:
            smooth_mask = np.ones(len(y_data), dtype=bool)
        
        # 综合筛选
        valid_mask = ffill_mask & mean_fill_mask & smooth_mask
        
        logger.info(f"数据筛选: 原始{len(x_data)}条，保留{np.sum(valid_mask)}条原始数据")
        
        return x_data[valid_mask], y_data[valid_mask]
    
    async def _fit_with_fallback(self, x_data: np.ndarray, y_data: np.ndarray, curve_type: PumpGroupCurveType) -> Dict:
        """降级拟合策略"""
        
        methods = ['polynomial', 'linear', 'default']
        
        for method in methods:
            try:
                result = await self._fit_method(method, x_data, y_data, curve_type)
                quality = self._evaluate_quality(result, x_data, y_data)
                
                if quality.r2_score > 0.6:  # 质量阈值
                    return {
                        'model': result,
                        'method': method,
                        'quality': quality,
                        'curve_type': curve_type.value
                    }
            except Exception as e:
                logger.warning(f"拟合方法 {method} 失败: {e}")
                continue
        
        return self._get_default_curve(curve_type)
    
    async def _fit_method(self, method: str, x_data: np.ndarray, y_data: np.ndarray, curve_type: PumpGroupCurveType) -> Dict:
        """具体拟合方法"""
        
        if method == 'polynomial':
            # 尝试不同阶数
            best_degree = 1
            best_score = -np.inf
            best_coeffs = None
            
            for degree in range(1, min(4, len(x_data)//3)):
                try:
                    coeffs = np.polyfit(x_data, y_data, degree)
                    y_pred = np.polyval(coeffs, x_data)
                    score = 1 - np.sum((y_data - y_pred)**2) / np.sum((y_data - np.mean(y_data))**2)
                    
                    if score > best_score:
                        best_score = score
                        best_degree = degree
                        best_coeffs = coeffs
                except:
                    continue
            
            return {
                'type': 'polynomial',
                'coefficients': best_coeffs,
                'degree': best_degree
            }
        
        elif method == 'linear':
            coeffs = np.polyfit(x_data, y_data, 1)
            return {
                'type': 'linear',
                'coefficients': coeffs
            }
        
        else:
            return self._get_default_curve(curve_type)
    
    def _evaluate_quality(self, model: Dict, x_data: np.ndarray, y_data: np.ndarray) -> CurveQuality:
        """评估拟合质量"""
        
        # 预测
        if model['type'] == 'polynomial':
            y_pred = np.polyval(model['coefficients'], x_data)
        elif model['type'] == 'linear':
            y_pred = model['coefficients'][0] * x_data + model['coefficients'][1]
        else:
            y_pred = np.full_like(y_data, np.mean(y_data))
        
        # 计算指标
        r2 = 1 - np.sum((y_data - y_pred)**2) / np.sum((y_data - np.mean(y_data))**2)
        rmse = np.sqrt(np.mean((y_data - y_pred)**2))
        confidence = min(r2 * (len(x_data) / 50), 1.0)  # 样本数量影响置信度
        
        return CurveQuality(
            r2_score=r2,
            rmse=rmse,
            sample_count=len(x_data),
            confidence=confidence
        )
    
    def _get_default_curve(self, curve_type: PumpGroupCurveType) -> Dict:
        """获取默认曲线"""
        
        defaults = {
            PumpGroupCurveType.GROUP_EFFICIENCY_LOAD: {
                'type': 'polynomial',
                'coefficients': [-0.001, 0.05, 75],  # 效率随负载变化
                'quality': CurveQuality(0.5, 5.0, 0, 0.3)
            },
            PumpGroupCurveType.GROUP_COORDINATION: {
                'type': 'polynomial',
                'coefficients': [-0.02, 0.15, 0.9],  # 协调系数随泵数变化
                'quality': CurveQuality(0.5, 0.1, 0, 0.3)
            },
            PumpGroupCurveType.GROUP_IMBALANCE: {
                'type': 'linear',
                'coefficients': [5, -5],  # 不平衡导致效率损失
                'quality': CurveQuality(0.5, 2.0, 0, 0.3)
            },
            PumpGroupCurveType.GROUP_FREQUENCY_DIST: {
                'type': 'linear',
                'coefficients': [-2, 85],  # 频率分布影响效率
                'quality': CurveQuality(0.5, 3.0, 0, 0.3)
            }
        }
        
        return defaults.get(curve_type, {
            'type': 'linear',
            'coefficients': [0, 50],
            'quality': CurveQuality(0.0, 10.0, 0, 0.1)
        })


class CurveEnhancedCompletion:
    """基于曲线的增强数据补齐"""
    
    def __init__(self, gateway: DatabaseGateway, curve_fitter: PumpGroupCurveFitter):
        self.gateway = gateway
        self.curve_fitter = curve_fitter
    
    async def enhance_data_completion(self, 
                                    station_id: str,
                                    missing_data: Dict,
                                    curve_models: Optional[Dict] = None) -> Dict:
        """使用拟合曲线增强数据补齐"""
        
        if curve_models is None:
            # 获取最新的曲线模型
            curve_models = await self.curve_fitter.fit_pump_group_curves(station_id)
        
        enhanced_data = {}
        
        for metric_type, missing_points in missing_data.items():
            
            # 选择相关曲线
            relevant_curves = self._select_relevant_curves(metric_type, curve_models)
            
            if not relevant_curves:
                # 回退到传统方法
                enhanced_data[metric_type] = await self._traditional_completion(missing_points)
                continue
            
            # 基于曲线的补齐
            completed_points = []
            
            for point in missing_points:
                # 获取同时刻的已知指标
                known_metrics = await self._get_known_metrics(station_id, point['timestamp'])
                
                # 使用曲线预测
                predicted_value = await self._predict_from_curves(
                    metric_type, known_metrics, relevant_curves
                )
                
                # 计算置信度
                confidence = self._calculate_confidence(predicted_value, known_metrics, relevant_curves)
                
                completed_points.append({
                    'timestamp': point['timestamp'],
                    'value': predicted_value,
                    'confidence': confidence,
                    'method': 'curve_enhanced',
                    'curves_used': list(relevant_curves.keys())
                })
            
            enhanced_data[metric_type] = completed_points
        
        return enhanced_data
    
    def _select_relevant_curves(self, metric_type: str, curve_models: Dict) -> Dict:
        """选择与指标相关的曲线"""
        
        relevance_map = {
            'pump_flow_rate': ['group_efficiency_load', 'group_coordination'],
            'pump_efficiency': ['group_efficiency_load', 'group_imbalance'],
            'pump_frequency': ['group_frequency_distribution'],
            'pump_active_power': ['group_efficiency_load', 'group_coordination']
        }
        
        relevant_names = relevance_map.get(metric_type, [])
        return {name: curve_models[name] for name in relevant_names if name in curve_models}
    
    async def _get_known_metrics(self, station_id: str, timestamp: datetime) -> Dict:
        """获取指定时刻的已知指标"""
        
        # 查询前后5分钟的数据
        start_time = timestamp - timedelta(minutes=5)
        end_time = timestamp + timedelta(minutes=5)
        
        sql = """
        SELECT metric_type, AVG(metric_value) as avg_value
        FROM fact_measurements
        WHERE station_id = %s 
            AND metric_time BETWEEN %s AND %s
            AND metric_value IS NOT NULL
        GROUP BY metric_type
        """
        
        result = await self.gateway.execute_query(sql, station_id, start_time, end_time)
        
        return {row['metric_type']: row['avg_value'] for row in result}
    
    async def _predict_from_curves(self, 
                                 target_metric: str,
                                 known_metrics: Dict,
                                 curve_models: Dict) -> float:
        """基于曲线预测缺失值"""
        
        predictions = []
        weights = []
        
        for curve_name, model in curve_models.items():
            try:
                # 根据曲线类型确定输入
                input_value = self._get_curve_input(curve_name, known_metrics)
                
                if input_value is not None:
                    prediction = self._predict_with_model(model, input_value)
                    weight = model.get('quality', CurveQuality(0.5, 5.0, 0, 0.5)).confidence
                    
                    predictions.append(prediction)
                    weights.append(weight)
            except Exception:
                continue
        
        if not predictions:
            return np.mean(list(known_metrics.values())) if known_metrics else 0.0
        
        # 加权平均
        return np.average(predictions, weights=weights)
    
    def _get_curve_input(self, curve_name: str, known_metrics: Dict) -> Optional[float]:
        """获取曲线输入参数"""
        
        input_mapping = {
            'group_efficiency_load': 'total_flow_rate',  # 需要计算总流量
            'group_coordination': 'pump_count',  # 需要计算运行泵数
            'group_frequency_distribution': 'frequency_std'  # 需要计算频率标准差
        }
        
        if curve_name in input_mapping:
            # 这里需要根据已知指标计算输入参数
            # 简化实现，实际需要更复杂的计算
            return known_metrics.get('pump_flow_rate', 50.0)  # 默认值
        
        return None
    
    def _predict_with_model(self, model: Dict, input_value: float) -> float:
        """使用模型预测"""
        
        if model['type'] == 'polynomial':
            return np.polyval(model['coefficients'], input_value)
        elif model['type'] == 'linear':
            return model['coefficients'][0] * input_value + model['coefficients'][1]
        else:
            return 50.0  # 默认值
    
    def _calculate_confidence(self, prediction: float, known_metrics: Dict, curve_models: Dict) -> float:
        """计算预测置信度"""
        
        confidence_factors = []
        
        # 曲线质量因子
        for model in curve_models.values():
            quality = model.get('quality', CurveQuality(0.5, 5.0, 0, 0.5))
            confidence_factors.append(quality.confidence)
        
        # 数据完整性因子
        completeness = min(len(known_metrics) / 5, 1.0)  # 假设需要5个相关指标
        confidence_factors.append(completeness)
        
        # 物理合理性因子
        if 0 <= prediction <= 100:  # 假设大多数指标在0-100范围内合理
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.3)
        
        return np.mean(confidence_factors) if confidence_factors else 0.5
    
    async def _traditional_completion(self, missing_points: List[Dict]) -> List[Dict]:
        """传统补齐方法（FFILL/MEAN/REG）"""
        
        completed_points = []
        
        for point in missing_points:
            completed_points.append({
                'timestamp': point['timestamp'],
                'value': 50.0,  # 简化的默认值
                'confidence': 0.3,
                'method': 'traditional',
                'curves_used': []
            })
        
        return completed_points