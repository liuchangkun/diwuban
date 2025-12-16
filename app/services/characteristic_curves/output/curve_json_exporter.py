import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

from app.services.characteristic_curves.core.data_structures import (
    DirectFitResult,
    FitResult,
    GroupFitResult,
)


class CurveJsonExporter:
    SCHEMA_VERSION = "1.0"

    def __init__(self, output_dir: Optional[Path] = None):
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._output_dir = output_dir
        if self._output_dir:
            self._output_dir.mkdir(parents=True, exist_ok=True)

    def export_single_pump(
        self,
        fit_result: FitResult,
        rated_params: Optional[Dict[str, Any]] = None,
        device_info: Optional[Dict[str, Any]] = None,
        save_to_file: bool = False
    ) -> Dict[str, Any]:
        y_name, y_label, y_unit = self._get_y_mapping(fit_result.curve_type)
        model_type, degree = self._infer_model_info(fit_result)
        coeffs, coeff_names = self._process_coefficients(fit_result.coefficients)

        result = {
            "_schema": {
                "version": self.SCHEMA_VERSION,
                "type": "pump_characteristic_curve",
                "generated_at": datetime.now().isoformat(),
            },
            "identity": {
                "device_id": fit_result.device_id,
                "curve_type": fit_result.curve_type,
                "version": fit_result.version,
                "created_at": fit_result.created_at.isoformat() if fit_result.created_at else None,
            },
            "model": {
                "method_id": fit_result.method_id,
                "method_name": fit_result.method_name,
                "type": model_type,
                "degree": degree if model_type == "polynomial" else None,
                "coefficients": coeffs,
                "coefficient_names": coeff_names,
                "formula": fit_result.formula or self._build_formula(model_type, coeffs, y_name),
                "restore_code": self._generate_restore_code(model_type, coeffs),
            },
            "normalization": {
                "enabled": bool(fit_result.normalization_params),
                "method": "min_max" if fit_result.normalization_params else None,
                "x_params": fit_result.normalization_params.get("Q") or fit_result.normalization_params.get("x") if fit_result.normalization_params else None,
                "y_params": fit_result.normalization_params.get(y_name) or fit_result.normalization_params.get("y") if fit_result.normalization_params else None,
            },
            "valid_range": {
                "x": {"name": "Q", "label": "flow", "unit": "m3/h",
                      "min": fit_result.valid_q_range[0] if fit_result.valid_q_range else 0.0,
                      "max": fit_result.valid_q_range[1] if fit_result.valid_q_range else 500.0},
                "y": {"name": y_name, "label": y_label, "unit": y_unit,
                      "min": fit_result.valid_h_range[0] if fit_result.valid_h_range else 0.0,
                      "max": fit_result.valid_h_range[1] if fit_result.valid_h_range else 100.0},
            },
            "metrics": {
                "r_squared": fit_result.r_squared,
                "rmse": fit_result.rmse,
                "mae": fit_result.mae,
                "mape": fit_result.mape,
                "data_points": fit_result.data_points,
            },
            "sample_curve": self._generate_sample_curve(
                model_type, coeffs,
                fit_result.valid_q_range[0] if fit_result.valid_q_range else 0.0,
                fit_result.valid_q_range[1] if fit_result.valid_q_range else 500.0
            ),
            "key_points": self._generate_key_points(model_type, coeffs, rated_params),
        }

        if rated_params:
            result["rated_params"] = rated_params
        if device_info:
            result["device_info"] = device_info
        if save_to_file and self._output_dir:
            self._save_to_file(result, fit_result.device_id, fit_result.curve_type, fit_result.version)
        return result

    def export_pump_group_direct(
        self,
        fit_result: DirectFitResult,
        station_info: Optional[Dict[str, Any]] = None,
        pump_rated_params: Optional[Dict[int, Dict[str, Any]]] = None,
        save_to_file: bool = False
    ) -> Dict[str, Any]:
        y_name, y_label, y_unit = self._get_y_mapping(fit_result.curve_type)
        coeffs = fit_result.coefficients
        coeff_names = [f"a{i}" for i in range(len(coeffs))]
        pump_ids = [int(pid) for pid in fit_result.pump_combination_key.split(",")] if fit_result.pump_combination_key else []

        q_min = fit_result.valid_q_range[0] if fit_result.valid_q_range else 0.0
        q_max = fit_result.valid_q_range[1] if fit_result.valid_q_range else 1000.0
        h_min = fit_result.valid_h_range[0] if fit_result.valid_h_range else 0.0
        h_max = fit_result.valid_h_range[1] if fit_result.valid_h_range else 100.0

        result = {
            "_schema": {"version": self.SCHEMA_VERSION, "type": "pump_group_characteristic_curve", "generated_at": datetime.now().isoformat()},
            "identity": {
                "station_id": fit_result.station_id,
                "curve_type": fit_result.curve_type,
                "pump_combination": pump_ids,
                "pump_combination_key": fit_result.pump_combination_key,
                "n_pumps": fit_result.n_pumps,
                "version": fit_result.fitted_at.strftime("%Y%m%d_%H%M%S") if fit_result.fitted_at else None,
                "created_at": fit_result.fitted_at.isoformat() if fit_result.fitted_at else None,
            },
            "group_info": {"group_type": fit_result.group_type, "fit_method": fit_result.fit_method, "frequency_normalized": fit_result.frequency_normalized},
            "model": {
                "method_id": fit_result.method_id,
                "method_name": fit_result.method_name,
                "type": "polynomial",
                "degree": fit_result.polynomial_degree or (len(coeffs) - 1),
                "coefficients": coeffs,
                "coefficient_names": coeff_names,
                "formula": self._build_formula("polynomial", coeffs, y_name),
                "restore_code": self._generate_restore_code("polynomial", coeffs),
            },
            "valid_range": {
                "x": {"name": "Q_total", "label": "total_flow", "unit": "m3/h", "min": q_min, "max": q_max},
                "y": {"name": y_name, "label": y_label, "unit": y_unit, "min": h_min, "max": h_max},
            },
            "metrics": {"r_squared": fit_result.r_squared, "rmse": fit_result.rmse, "mae": fit_result.mae, "mape": fit_result.mape, "data_points": fit_result.data_points_used},
            "sample_curve": self._generate_sample_curve("polynomial", coeffs, q_min, q_max),
            "key_points": self._generate_group_key_points(coeffs, q_max),
        }

        if station_info:
            result["station_info"] = station_info
        if pump_rated_params:
            result["pump_rated_params"] = {str(pid): params for pid, params in pump_rated_params.items() if pid in pump_ids}
        if save_to_file and self._output_dir:
            version = fit_result.fitted_at.strftime("%Y%m%d_%H%M%S") if fit_result.fitted_at else "latest"
            self._save_to_file(result, f"station_{fit_result.station_id}_group_{fit_result.pump_combination_key}", fit_result.curve_type, version)
        return result

    def export(self, fit_result: Union[FitResult, DirectFitResult, GroupFitResult], **kwargs) -> Dict[str, Any]:
        if isinstance(fit_result, FitResult):
            return self.export_single_pump(fit_result, **kwargs)
        elif isinstance(fit_result, DirectFitResult):
            return self.export_pump_group_direct(fit_result, **kwargs)
        else:
            raise TypeError(f"Unsupported result type: {type(fit_result)}")

    def _get_y_mapping(self, curve_type: str) -> tuple:
        mapping = {"qh": ("H", "head", "m"), "qp": ("P", "power", "kW"), "qeta": ("eta", "efficiency", "%")}
        return mapping.get(curve_type, ("y", "y_value", ""))

    def _infer_model_info(self, fit_result: FitResult) -> tuple:
        model_type = "polynomial"
        degree = 2
        if fit_result.method_id:
            method_id = fit_result.method_id.lower()
            if "poly_2" in method_id or "poly2" in method_id:
                degree = 2
            elif "poly_3" in method_id or "poly3" in method_id:
                degree = 3
            elif "power" in method_id:
                model_type = "power"
        if fit_result.coefficients:
            coeff_count = len(fit_result.coefficients)
            if model_type == "polynomial":
                degree = coeff_count - 1
        return model_type, degree

    def _process_coefficients(self, coefficients: Dict[str, Any]) -> tuple:
        if isinstance(coefficients, dict):
            return list(coefficients.values()), list(coefficients.keys())
        return list(coefficients) if coefficients else [], [f"a{i}" for i in range(len(coefficients) if coefficients else 0)]

    def _build_formula(self, model_type: str, coefficients: List, y_name: str) -> str:
        if not coefficients:
            return f"{y_name} = f(Q)"
        if model_type == "polynomial":
            terms = []
            for i, c in enumerate(coefficients):
                if i == 0:
                    terms.append(f"{c:.4f}")
                elif i == 1:
                    terms.append(f"{c:+.6f}*Q")
                else:
                    terms.append(f"{c:+.8f}*Q^{i}")
            return f"{y_name} = " + " ".join(terms)
        return f"{y_name} = f(Q)"

    def _generate_restore_code(self, model_type: str, coefficients: List) -> Dict[str, str]:
        if not coefficients:
            return {"python": "# no coefficients", "javascript": "// no coefficients", "sql": "NULL"}
        terms_py = " + ".join([f"({c})*Q**{i}" for i, c in enumerate(coefficients)])
        terms_js = " + ".join([f"({c})*Math.pow(Q,{i})" for i, c in enumerate(coefficients)])
        terms_sql = " + ".join([f"({c})*POWER(Q,{i})" for i, c in enumerate(coefficients)])
        return {"python": f"def predict(Q):\n    return {terms_py}", "javascript": f"function predict(Q) {{ return {terms_js}; }}", "sql": terms_sql}

    def _generate_sample_curve(self, model_type: str, coefficients: List, q_min: float, q_max: float, n_points: int = 21) -> Dict[str, Any]:
        if not coefficients:
            return {"count": 0, "x": [], "y": []}
        x_vals = np.linspace(q_min, q_max, n_points)
        y_vals = [sum(c * (q ** i) for i, c in enumerate(coefficients)) for q in x_vals]
        return {"count": n_points, "x": [round(float(x), 2) for x in x_vals], "y": [round(float(y), 2) for y in y_vals]}

    def _generate_key_points(self, model_type: str, coefficients: List, rated_params: Optional[Dict] = None) -> Dict:
        key_points = {}
        if not coefficients:
            return key_points
        y_at_zero = coefficients[0] if coefficients else 0
        key_points["shutoff"] = {"Q": 0.0, "y": round(float(y_at_zero), 2), "description": "shutoff point"}
        if rated_params:
            q_rated = rated_params.get("rated_flow") or rated_params.get("Q_rated")
            if q_rated:
                y_rated = sum(c * (q_rated ** i) for i, c in enumerate(coefficients))
                key_points["rated"] = {"Q": float(q_rated), "y": round(float(y_rated), 2), "description": "rated point"}
        return key_points

    def _generate_group_key_points(self, coefficients: List, q_max: float) -> Dict:
        key_points = {}
        if not coefficients:
            return key_points
        y_at_zero = coefficients[0] if coefficients else 0
        key_points["shutoff"] = {"Q": 0.0, "y": round(float(y_at_zero), 2), "description": "shutoff point"}
        y_at_max = sum(c * (q_max ** i) for i, c in enumerate(coefficients))
        key_points["max_flow"] = {"Q": float(q_max), "y": round(float(y_at_max), 2), "description": "max flow point"}
        return key_points

    def _save_to_file(self, data: Dict, identifier: Any, curve_type: str, version: str) -> Path:
        if not self._output_dir:
            raise ValueError("Output directory not set")
        file_dir = self._output_dir / str(identifier) / curve_type
        file_dir.mkdir(parents=True, exist_ok=True)
        file_path = file_dir / f"{curve_type}_{version}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self._logger.info(f"[JSON Export] Saved: {file_path}")
        return file_path


def export_fit_result_to_json(fit_result: Union[FitResult, DirectFitResult, GroupFitResult], output_path: Optional[Path] = None, **kwargs) -> Dict[str, Any]:
    exporter = CurveJsonExporter(output_dir=output_path.parent if output_path else None)
    result = exporter.export(fit_result, **kwargs)
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    return result
