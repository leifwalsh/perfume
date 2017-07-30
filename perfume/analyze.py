# -*- coding: utf-8 -*-

'''Analysis tools.'''

import bokeh.io as bi
import bokeh.models as bm
import bokeh.plotting as bp
import pandas as pd

from perfume import colors


def timings(samples):
    '''Converts samples to sample times per observation.'''
    groups = samples.groupby(axis=1, level=0)
    return groups.apply(lambda group: group.iloc[:,1] - group.iloc[:,0])


def _remove_other_timings(group):
    other_timings = (group.iloc[:,0] - group.iloc[:,1].shift(1)).fillna(0).cumsum()
    ret = group.groupby(axis=1, level=1).apply(lambda x: x.iloc[:,0] - other_timings)
    ret.columns = group.columns
    return ret


def isolate(samples):
    '''For each function, isolates its begin and end times.

    Within each function's begins and ends, each begin will be equal
    to the previous end.  This gives a sequence of begins and ends as
    if each function were run in isolation with no benchmarking
    overhead.
    '''
    zeroed = samples.groupby(axis=1, level=0).apply(lambda group: group - group.iloc[0,0])
    return zeroed.groupby(axis=1, level=0).apply(_remove_other_timings)


def _timing_in_context(group):
    time_col = pd.DataFrame(data=group.iloc[:,1].values, columns=['time'])
    values = pd.DataFrame(data=timings(group),
                          columns=[group.columns[0][0]])
    time_col = pd.to_timedelta(time_col['time'], unit='s')
    values = values.assign(time=time_col)
    return values.set_index('time')


def timings_in_context(samples):
    '''Returns a sparse dataframe with a time index, with timings.

    Each cell contains the timing observed, at the time when it was
    observed.  Therefore, each row will have NaNs except for the
    function whose sample completed at that time.
    '''
    iso = isolate(samples)
    t = iso.groupby(axis=1, level=0).apply(_timing_in_context)
    t.columns = t.columns.droplevel(0)
    return t


def _cumulative_quantiles(group, rng):
    group = isolate(group)
    t = timings(group)
    ret = pd.concat(
        [t.iloc[:(i+1),:].describe().T[['min', '25%', '50%', '75%', 'max']]
         for i in rng])
    ret = ret.set_index(group.iloc[slice(rng.start, rng.stop), 1])
    ret.index.name = 'time'
    return ret


def cumulative_quantiles(samples, rng=None):
    '''Computes "cumulative quantiles" for each function.

    That is, for each time, what are the extremes, median, and
    25th/75th percentiles for all observations up until that point.
    '''
    if rng is None:
        rng = range(len(samples.index))
    groups = samples.groupby(axis=1, level=0)
    df = groups.apply(lambda group: _cumulative_quantiles(group, rng))
    return df


def cumulative_quantiles_plot(samples):
    '''Plots the cumulative quantiles along with a scatter plot of
    observations.'''
    plot = bp.figure(plot_width=960, plot_height=480)

    names = samples.columns.levels[0]
    _colors = {name: color for name, color in zip(names, colors.colors(len(names)))}

    def draw(group):
        name = group.columns[0][0]
        color = _colors[name]
        group.columns = group.columns.droplevel(0)
        group = group.dropna()
        quantile_source = bm.ColumnDataSource(
            pd.DataFrame(
                data={'lower': group['25%'], 'upper': group['75%']},
                index=group.index).dropna().reset_index())
        extreme_source = bm.ColumnDataSource(
            pd.DataFrame(
                data={'lower': group['min'], 'upper': group['max']},
                index=group.index).dropna().reset_index())
        plot.line(group.index, group['50%'], line_color=color, legend=name)
        plot.add_layout(bm.Band(base='time',
                                lower='lower',
                                upper='upper',
                                source=quantile_source,
                                fill_color=color, fill_alpha=0.2))
        plot.add_layout(bm.Band(base='time',
                                lower='lower',
                                upper='upper',
                                source=extreme_source,
                                fill_color=color, fill_alpha=0.025))
        plot.line('time', 'lower', line_color=color, alpha=0.5,
                  source=extreme_source)
        plot.line('time', 'upper', line_color=color, alpha=0.5,
                  source=extreme_source)
    cumulative_quantiles(samples).groupby(axis=1, level=0).apply(draw)

    def scatter(group):
        name = group.columns[0][0]
        color = _colors[name]
        group = isolate(group)
        t = timings(group).set_index(group.iloc[:, 1])
        t.index.name = 'time'
        t.columns = ['value']
        source = bm.ColumnDataSource(t.reset_index())
        plot.circle(x='time', y='value', source=source, color=color, size=1, alpha=0.5)
    samples.groupby(axis=1, level=0).apply(scatter)

    bi.show(plot)
