from __future__ import annotations

import dataclasses
from typing import Callable, Literal

from xarray.core.dataarray import DataArray

from icclim.icclim_exceptions import InvalidIcclimArgumentError
from icclim.models.registry import Registry
from icclim.models.user_index_config import UserIndexConfig
from icclim.user_indices import operators

CalcOperationLiteral = Literal[
    "max",
    "min",
    "sum",
    "mean",
    "nb_events",
    "max_nb_consecutive_events",
    "run_mean",
    "run_sum",
    "anomaly",
]


def compute_user_index(config: UserIndexConfig) -> DataArray:
    operation = CalcOperationRegistry.lookup(config.calc_operation)
    return operation.compute_fun(config)


def anomaly(config: UserIndexConfig):
    if (
        config.climate_variables[0].reference_da is None
        or len(config.climate_variables[0].reference_da) == 0
    ):
        raise InvalidIcclimArgumentError(
            f"You must provide a `ref_time_range` in user_index dictionary to compute"
            f" {CalcOperationRegistry.ANOMALY.value}."
            f" To be valid, it must be within the dataset time range."
        )
    return operators.anomaly(
        da=config.climate_variables[0].studied_data,
        da_ref=config.climate_variables[0].reference_da,
        percent=config.is_percent,
    )


def run_sum(config: UserIndexConfig):
    if config.extreme_mode is None or config.window_width is None:
        raise InvalidIcclimArgumentError(
            "Please provide an extreme_mode and a window_width to user_index."
        )
    return operators.run_sum(
        da=config.climate_variables[0].studied_data,
        extreme_mode=config.extreme_mode,
        window_width=config.window_width,
        coef=config.coef,
        freq=config.freq.pandas_freq,
        date_event=config.date_event,
    )


def run_mean(config: UserIndexConfig):
    if config.extreme_mode is None or config.window_width is None:
        raise InvalidIcclimArgumentError(
            "Please provide a extreme mode and a window width."
        )
    return operators.run_mean(
        da=config.climate_variables[0].studied_data,
        extreme_mode=config.extreme_mode,
        window_width=config.window_width,
        coef=config.coef,
        freq=config.freq.pandas_freq,
        date_event=config.date_event,
    )


def max_consecutive_event_count(config: UserIndexConfig):
    if config.logical_operation is None or config.thresh is None:
        raise InvalidIcclimArgumentError(
            "Please provide a threshold and a logical operation."
        )
    if isinstance(config.thresh, (tuple, list)):
        raise InvalidIcclimArgumentError(
            f"{CalcOperationRegistry.MAX_NUMBER_OF_CONSECUTIVE_EVENTS.value} "
            f"does not support threshold list. Please provide a single threshold."
        )
    # todo fix reference_da
    return operators.max_consecutive_event_count(
        da=config.climate_variables[0].studied_data,
        in_base_da=config.climate_variables[0].reference_da,
        logical_operation=config.logical_operation,
        threshold=config.thresh,
        coef=config.coef,
        freq=config.freq.pandas_freq,
        date_event=config.date_event,
    )


def count_events(config: UserIndexConfig):
    if config.nb_event_config is None:
        raise InvalidIcclimArgumentError(
            f"{CalcOperationRegistry.EVENT_COUNT.value} not properly configure."
            f" Please provide a threshold and a logical operation."
        )
    return operators.count_events(
        das=list(map(lambda x: x.studied_data, config.climate_variables)),
        in_base_das=list(map(lambda x: x.reference_da, config.climate_variables)),
        logical_operation=config.nb_event_config.logical_operation,
        link_logical_operations=config.nb_event_config.link_logical_operations,
        thresholds=config.nb_event_config.thresholds,
        coef=config.coef,
        freq=config.freq.pandas_freq,
        date_event=config.date_event,
    )


def sum(config: UserIndexConfig):
    return operators.sum(
        da=_check_and_get_da(config),
        in_base_da=_check_and_get_in_base_da(config),
        coef=config.coef,
        logical_operation=config.logical_operation,
        threshold=_check_and_get_simple_threshold(config.thresh),
        freq=config.freq.pandas_freq,
    )


def mean(config: UserIndexConfig):
    return operators.mean(
        da=_check_and_get_da(config),
        in_base_da=_check_and_get_in_base_da(config),
        coef=config.coef,
        logical_operation=config.logical_operation,
        threshold=_check_and_get_simple_threshold(config.thresh),
        freq=config.freq.pandas_freq,
    )


def min(config: UserIndexConfig):
    return _simple_reducer(operators.min, config)


def max(config: UserIndexConfig):
    return _simple_reducer(operators.max, config)


def _simple_reducer(op: Callable, config: UserIndexConfig):
    return op(
        da=_check_and_get_da(config),
        in_base_da=_check_and_get_in_base_da(config),
        coef=config.coef,
        logical_operation=config.logical_operation,
        threshold=_check_and_get_simple_threshold(config.thresh),
        freq=config.freq.pandas_freq,
        date_event=config.date_event,
    )


def _check_and_get_simple_threshold(
    thresh: None | str | float | int,
) -> None | str | float | int:
    if (
        thresh is None
        or isinstance(thresh, str)
        or isinstance(thresh, float)
        or isinstance(thresh, int)
    ):
        return thresh
    else:
        raise InvalidIcclimArgumentError(
            "threshold type must be either None, "
            "a string (for percentile) or a number."
        )


def _check_and_get_da(config: UserIndexConfig) -> DataArray:
    if len(config.climate_variables) == 1:
        return config.climate_variables[0].studied_data
    else:
        raise InvalidIcclimArgumentError(
            f"There must be exactly one variable for {config.calc_operation}."
        )


def _check_and_get_in_base_da(config: UserIndexConfig) -> DataArray | None:
    if len(config.climate_variables) == 1:
        return config.climate_variables[0].reference_da
    else:
        raise InvalidIcclimArgumentError(
            f"There must be exactly one variable for {config.calc_operation}"
        )


@dataclasses.dataclass
class CalcOperation:
    name: str
    compute: Callable


class CalcOperationRegistry(Registry):
    _item_class = CalcOperation
    MAX = CalcOperation("max", max)
    MIN = CalcOperation("min", min)
    SUM = CalcOperation("sum", sum)
    MEAN = CalcOperation("mean", mean)
    EVENT_COUNT = CalcOperation("nb_events", count_events)
    MAX_NUMBER_OF_CONSECUTIVE_EVENTS = (
        "max_nb_consecutive_events",
        max_consecutive_event_count,
    )
    RUN_MEAN = CalcOperation("run_mean", run_mean)
    RUN_SUM = CalcOperation("run_sum", run_sum)
    ANOMALY = CalcOperation("anomaly", anomaly)
