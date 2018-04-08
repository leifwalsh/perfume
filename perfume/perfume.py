# -*- coding: utf-8 -*-

"""Main module."""

import collections
import time
import uuid

from bokeh import io as bi
from bokeh import models as bm
import bokeh.palettes
from bokeh import plotting as bp
from IPython import display as ipdisplay
import numpy as np
import pandas as pd

from perfume import analyze
from perfume import colors


class Timer(object):

    def __enter__(self):
        self._begin = time.perf_counter()
        return self

    def __exit__(self, *exc_info):
        self._end = time.perf_counter()

    @property
    def begin(self):
        return self._begin

    @property
    def end(self):
        return self._end

    def elapsed_seconds(self):
        return self.end - self.begin

    @classmethod
    def time(cls, fn, *args, **kwargs):
        with cls() as timer:
            fn(*args, **kwargs)
        return timer.elapsed_seconds()


class Display(object):

    def __init__(self, names, initial_size, width=900, height=480):
        # Call this once to raise an error early if necessary:
        self._colors = colors.colors(len(names))

        self._start = time.perf_counter()
        self._initial_size = initial_size
        self._sources = collections.OrderedDict(
            [
                (
                    name,
                    {
                        "hist": bm.ColumnDataSource(
                            data={"top": [], "left": [], "right": []}
                        ),
                        "pdf": bm.ColumnDataSource(data={"x": [], "y": []}),
                        "stddev": bm.ColumnDataSource(
                            data={"base": [], "lower": [], "upper": []}
                        ),
                        "median": bm.ColumnDataSource(data={"x": [], "y": []}),
                    },
                )
                for name in names
            ]
        )
        self._width = width
        self._height = height
        self._plot = None
        self._elapsed_rendering_seconds = 0.0
        self._describe_widget = ipdisplay.HTML("")
        self._display_id = str(uuid.uuid1())

    def elapsed_rendering_ratio(self):
        elapsed = time.perf_counter() - self._start
        return self._elapsed_rendering_seconds / elapsed

    def initialize_plot(self, title):
        with Timer() as timer:
            plot = bp.figure(
                title=title, plot_width=self._width, plot_height=self._height
            )
            plot.xaxis.axis_label = "millis"
            plot.yaxis.visible = False
            _colors = iter(self._colors)
            for name, sources in self._sources.items():
                color = next(_colors)
                plot.quad(
                    top="top",
                    bottom=0,
                    left="left",
                    right="right",
                    source=sources["hist"],
                    alpha=0.3,
                    fill_color=color,
                    line_color=color,
                )
                plot.line(
                    "x",
                    "y",
                    source=sources["pdf"],
                    legend=name,
                    alpha=0.5,
                    line_color=color,
                    line_width=4,
                )
                stddev = bm.Whisker(
                    base="base",
                    lower="lower",
                    upper="upper",
                    source=sources["stddev"],
                    dimension="width",
                    line_alpha=0.7,
                    line_color=color,
                    line_width=2,
                )
                for head in (stddev.lower_head, stddev.upper_head):
                    head.line_color = color
                    head.line_width = 2
                    head.line_alpha = 0.7
                plot.add_layout(stddev)
                median = bm.Whisker(
                    base="y",
                    lower="x",
                    upper="x",
                    source=sources["median"],
                    dimension="width",
                    line_alpha=0.7,
                    line_color=color,
                    line_width=2,
                )
                for head in (median.lower_head, median.upper_head):
                    head.line_color = color
                    head.line_width = 2
                    head.line_alpha = 0.7
                plot.add_layout(median)

        self._elapsed_rendering_seconds -= timer.elapsed_seconds()
        return plot

    @staticmethod
    def _ks_style(s):
        if np.isnan(s):
            return "visibility: hidden"

        else:
            thresholds = [1.22, 1.36, 1.48, 1.63, 1.73, 1.95]
            cs = list(reversed(bokeh.palettes.RdYlGn[len(thresholds) + 1]))
            color = cs[np.searchsorted(thresholds, s)]
            return "background-color: {}".format(color)

    def update(self, samples):
        # If this is a module-level import, readthedocs fails because
        # this triggers an import of _tkinter, which isn't built in to
        # the python that they use.
        import seaborn as sns

        with Timer() as timer:
            timings = analyze.timings(samples)
            bucketed_timings = analyze.bucket_resample_timings(samples)
            for name, sources in self._sources.items():
                array = timings[name].values
                hist, edges = np.histogram(array, density=True, bins="auto")
                x, y = sns.distributions._statsmodels_univariate_kde(
                    array,
                    "gau",
                    "scott",
                    200,
                    3,
                    (-np.inf, np.inf),
                    cumulative=False,
                )
                whisker_height = np.max(y) / 2
                lower, median, upper = np.percentile(array, [25., 50., 75.])

                sources["hist"].data = {
                    "top": hist, "left": edges[:-1], "right": edges[1:]
                }
                sources["pdf"].data = {"x": x, "y": y}
                sources["stddev"].data = {
                    "base": [whisker_height],
                    "lower": [lower],
                    "upper": [upper],
                }
                sources["median"].data = {"x": [median], "y": [whisker_height]}

            describe_html = (
                timings.describe().style.set_precision(3).set_caption(
                    "Descriptive Timing Statistics"
                ).render()
            )
            if len(self._sources) > 1:
                ks_frame = analyze.ks_test(timings)
                ks_bk_frame = analyze.ks_test(bucketed_timings)
                ks_html = (
                    ks_frame.style.applymap(self._ks_style).set_precision(
                        3
                    ).set_caption(
                        "K-S test"
                    ).render()
                )
                ks_bk_html = (
                    ks_bk_frame.style.applymap(self._ks_style).set_precision(
                        2
                    ).set_caption(
                        "Bucketed K-S test"
                    ).render()
                )
                html = describe_html + ks_html + ks_bk_html
                self._describe_widget.data = html.replace(
                    "table", 'table style="display:inline"'
                )
            else:
                self._describe_widget.data = describe_html

            total_bench_time = timings[self._initial_size:].sum().sum() / 1000.
            elapsed = time.perf_counter() - self._start
            num_samples = len(timings.index)
            title = (
                "{} samples, {:.2f} sec elapsed, {:.2f} samples/sec, "
                "{:.2f}% efficiency"
            ).format(
                num_samples,
                elapsed,
                (num_samples - self._initial_size) / elapsed,
                100. * total_bench_time / elapsed
            )

            if self._plot is None:
                self._plot = self.initialize_plot(title)
                bi.show(self._plot, notebook_handle=True)
                ipdisplay.display(
                    self._describe_widget, display_id=self._display_id
                )
            else:
                self._plot.title.text = title
                bi.push_notebook()
                ipdisplay.update_display(
                    self._describe_widget, display_id=self._display_id
                )
        self._elapsed_rendering_seconds += timer.elapsed_seconds()


def _flatten(l):
    return [n for sublist in l for n in sublist]


def bench(*fns, samples=None, efficiency=.9):
    """Benchmarks functions, displaying results in a Jupyter notebook.

    Runs ``fns`` repeatedly, collecting timing information, until
    :exc:`KeyboardInterrupt` is raised, at which point benchmarking
    stops and the results so far are returned.

    Parameters
    ----------
    fns : list of callable
        A list of functions to benchmark and compare
    samples : pandas.DataFrame
        Optionally, pass the results of a previous call to
        :func:`.bench` to continue from its already collected data.
    efficiency : float
        Number between 0 and 1.  Represents the target portion of time
        we aim to spend running the functions under test (so, we spend
        up to :math:`1 - efficiency` time analyzing and rendering
        plots).

    Returns
    -------
    pandas.DataFrame
        A dataframe containing the results so far.  The row index is
        just an autoincrement integer, and the column index is a
        :class:`~pandas.MultiIndex` where the first level is function
        name and the second level is ``begin`` or ``end``.
    """
    if samples is None:
        sample_records = []
    else:
        sample_records = [tuple(r) for r in samples.to_records(index=False)]
    names = [fn.__name__ for fn in fns]
    disp = Display(names, len(sample_records))
    index = pd.MultiIndex(
        levels=[names, ("begin", "end")],
        labels=[
            _flatten([(i, i) for i in range(len(names))]), [0, 1] * len(names)
        ],
        names=("function", "timing"),
    )
    try:
        while True:
            sample = []
            for fn in fns:
                with Timer() as timer:
                    fn()
                sample.extend((timer.begin, timer.end))
            sample_records.append(tuple(t * 1000 for t in sample))

            if (
                len(sample_records) > 10
                and disp.elapsed_rendering_ratio() < (1. - efficiency)
            ):
                samples = pd.DataFrame.from_records(
                    iter(sample_records), columns=index
                )
                disp.update(samples)
    except KeyboardInterrupt:
        return pd.DataFrame.from_records(iter(sample_records), columns=index)
