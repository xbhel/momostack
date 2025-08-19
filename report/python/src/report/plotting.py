from abc import ABC, abstractmethod
from typing import Any, ClassVar

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

Number = int | float

_DEFAULT_AXIS_COLOR = "#f4f4f7"
_DEFAULT_FONT_SIZE = 10


class BasePlotter(ABC):
    # Class variable to hold the type of plot.
    plot_type: ClassVar[str]

    __plotters: ClassVar[dict[str, type["BasePlotter"]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not isinstance(cls.plot_type, str):
            raise TypeError(f"{cls.__name__} must define a `plot_type` of type str.")

        cls.__plotters[cls.plot_type] = cls

    def plot(self, dataset: dict[str, Any], **kwargs: Any) -> Figure:
        figsize = kwargs.pop("figsize", (8, 4))
        dataset = kwargs.pop("dataset")
        labels, data = self._get_labels_and_data(dataset)

        title = kwargs.pop("title", "")
        x_axis = kwargs.pop("xaxis", {})
        y_axis = kwargs.pop("yaxis", {})
        series = kwargs.pop("series", [])

        figure, ax = plt.subplots(figsize=figsize)
        self._internal_plot(ax, labels, data, series=series)
        ax.set_title(title)
        self._set_xaxis(ax, x_axis)
        self._set_yaxis(ax, y_axis)
        self._set_item_text(ax, data, series, dataset)

        ax.spines[:].set_color(_DEFAULT_AXIS_COLOR)
        ax.tick_params(axis="both", which="both", color=_DEFAULT_AXIS_COLOR)
        ax.legend(
            loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2, columnspacing=1
        )

        return figure

    @abstractmethod
    def _internal_plot(self, axes: Axes, labels: Any, data: Any, **kwargs: Any) -> None:
        pass

    def _get_labels_and_data(
        self, dataset: dict[str, Any]
    ) -> tuple[list[str], list[list[Number]]]:
        source = dataset["source"]
        dimensions = dataset["dimensions"]
        if len(dimensions) < 2:
            raise ValueError(
                "Dataset must define at least one label and one value field"
            )

        labels = [item.get(dimensions[0], "") for item in source]
        data = [[item.get(field, 0) for item in source] for field in dimensions[1:]]
        return labels, data

    def _set_item_text(
        self,
        axes: Axes,
        data: list[list[Number]],
        series: list[Any],
        dataset: dict[str, Any],
    ) -> None:
        source = dataset["source"]
        transposed = np.array(data).T
        max_values = np.max(transposed, axis=1)

        for pos, values in enumerate(transposed):
            texts = []

            for index, value in enumerate(values):
                series_conf = series[index]
                series_name = series_conf.get('name', '')
                formatter = series_conf.get('formatter')
                text = f"{series_name} {value}"
                if formatter:
                    text = formatter(
                        value,
                        series_index=index,
                        series_name=series_name,
                        param=source[pos],
                    )
                texts.append(text)

            axes.text(
                pos,
                max_values[pos],
                text,
                ha="left",
                va="bottom",
                fontsize=_DEFAULT_FONT_SIZE,
                color="#444444",
            )

    def _set_xaxis(self, axes: Axes, xaxis: dict[str, Any]) -> None:
        axes.set_xlabel(
            xaxis.get("name", ""),
            fontsize=xaxis.get("fontsize", _DEFAULT_FONT_SIZE),
            color=xaxis.get("color", _DEFAULT_AXIS_COLOR),
        )

    def _set_yaxis(self, axes: Axes, yaxis: dict[str, Any]) -> None:
        axes.set_ylabel(
            yaxis.get("name", ""),
            fontsize=yaxis.get("fontsize", _DEFAULT_FONT_SIZE),
            color=yaxis.get("color", _DEFAULT_AXIS_COLOR),
        )


class StickedBarPlotter(BasePlotter):
    plot_type = "stacked_bar"

    def _internal_plot(
        self,
        axes: Axes,
        labels: list[str],
        data: list[list[int | float]],
        **kwargs: Any,
    ) -> None:
        bottom = np.zeros(len(labels))
        series = kwargs.pop('series')

        for index, values in enumerate(data):
            series_conf = series[index]
            color = series_conf.get("color", "blue")
            name = series_conf.get("name", None)
            axes.bar(labels, np.array(values), bottom=bottom, color=color, label=name)
            bottom += np.array(values)
