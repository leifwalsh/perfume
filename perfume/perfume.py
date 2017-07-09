# -*- coding: utf-8 -*-

'''Main module.'''

import time

from bokeh import io as bi
from bokeh import models as bm
from bokeh import palettes
from bokeh import plotting as bp
from IPython import display
import ipywidgets as widgets
import numpy as np
import pandas as pd
import seaborn as sns


class Timer(object):
    def __enter__(self):
        self._begin = time.perf_counter()
        return self

    def __exit__(self, *exc_info):
        self._end = time.perf_counter()

    def elapsed_seconds(self):
        return self._end - self._begin

    @classmethod
    def time(cls, fn):
        with cls() as timer:
            fn()
        return timer.elapsed_seconds()


def bench(*fns, samples=None, efficiency=.9):
    '''Benchmarks functions, displaying results in a Jupyter notebook.

    TODO: more
    '''
    if samples is None:
        data = []
    else:
        data = [tuple(r) for r in samples.to_records(index=False)]
    start = time.perf_counter()
    initial_size = len(data)
    times = None
    if len(fns) < 3:
        colors = palettes.Set1[3][:len(fns)]
    else:
        colors = palettes.Set1[len(fns)]
    hist_datas = [bm.ColumnDataSource(data={'top': [], 'left': [], 'right': []}) for _ in fns]
    pdfs = [bm.ColumnDataSource(data={'x': [], 'y': []}) for _ in fns]
    whiskers = [bm.ColumnDataSource(data={'25': [], 'base': [], '75': []}) for _ in fns]
    medians = [bm.ColumnDataSource(data={'x': [], 'y': []}) for _ in fns]
    title = bm.Title(text='Distribution')
    p = bp.figure(title=title, plot_width=900, plot_height=480)
    p.xaxis.axis_label = 'millis'
    p.yaxis.visible = False
    first = True
    elapsed_rendering = 0.0
    describe_widget = None
    try:
        while True:
            data.append(tuple(Timer.time(fn) * 1000. for fn in fns))
            if (len(data) < 10
                    or (elapsed_rendering / (time.perf_counter() - start)) > (1. - efficiency)):
                continue
            with Timer() as timer:
                times = pd.DataFrame.from_records(iter(data), columns=[fn.__name__ for fn in fns])
                total_bench_time = times[initial_size:].sum().sum() / 1000.
                elapsed = time.perf_counter() - start
                title.text = (
                    'Distribution ('
                    '{} samples, '
                    '{:.2f} sec elapsed, '
                    '{:.2f} samples/sec, '
                    '{:.2f}% efficiency)').format(
                    len(times.index),
                    elapsed,
                    (len(times.index) - initial_size) / elapsed,
                    100. * total_bench_time / elapsed)
                for fn, hist_data, pdf, whisker, median, color in zip(fns, hist_datas, pdfs, whiskers, medians, colors):
                    time_array = times[fn.__name__].values
                    hist, edges = np.histogram(time_array, density=True, bins='auto')
                    hist_data.data = {'top': hist, 'left': edges[:-1], 'right': edges[1:]}
                    x, y = sns.distributions._statsmodels_univariate_kde(
                        time_array, 'gau', 'scott', 200, 3, (-np.inf, np.inf), cumulative=False)
                    pdf.data = {'x': x, 'y': y}
                    mid_height = np.max(y) / 2.
                    whisker.data = {'25': [np.percentile(time_array, 25.)],
                                    'base': [mid_height],
                                    '75': [np.percentile(time_array, 75.)]}
                    median.data = {'x': [np.percentile(time_array, 50.)],
                                   'y': [mid_height]}

                if first:
                    for fn, hist_data, pdf, whisker, median, color in zip(fns, hist_datas, pdfs, whiskers, medians, colors):
                        p.quad(top='top', bottom=0, left='left', right='right', source=hist_data, alpha=0.3,
                               fill_color=color, line_color=color)
                        p.line('x', 'y', source=pdf, legend=fn.__name__, line_color=color, line_width=4, alpha=0.5)
                        wsk = bm.Whisker(source=whisker, base='base', lower='25', upper='75',
                                         dimension='width', line_color=color, line_width=2, line_alpha=0.7)
                        wsk.lower_head.line_color = color
                        wsk.lower_head.line_width = 2
                        wsk.lower_head.line_alpha = 0.7
                        wsk.upper_head.line_color = color
                        wsk.upper_head.line_width = 2
                        wsk.upper_head.line_alpha = 0.7
                        p.add_layout(wsk)
                        wsk = bm.Whisker(source=median, base='y', lower='x', upper='x',
                                         dimension='width', line_color=color, line_width=2, line_alpha=0.7)
                        wsk.lower_head.line_color = color
                        wsk.lower_head.line_width = 2
                        wsk.lower_head.line_alpha = 0.7
                        wsk.upper_head.line_color = color
                        wsk.upper_head.line_width = 2
                        wsk.upper_head.line_alpha = 0.7
                        p.add_layout(wsk)
                    handle = bi.show(p, notebook_handle=True)
                    first = False
                    describe_widget = display.HTML(times.describe().to_html())
                    display.display(describe_widget, display_id='describe')
                else:
                    bi.push_notebook()
                    describe_widget.data = times.describe().to_html()
                    display.update_display(describe_widget, display_id='describe')
            elapsed_rendering += timer.elapsed_seconds()
    except KeyboardInterrupt:
        return times
