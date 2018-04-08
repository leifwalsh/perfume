# -*- coding: utf-8 -*-

""":mod:`perfume.analyze` contains transformation and analysis tools.

These functions mostly take as input the samples collected by
:func:`perfume.bench`.
"""

import bokeh.io as bi
import bokeh.models as bm
import bokeh.plotting as bp
import numpy as np
import pandas as pd
from scipy import stats

from perfume import colors


def timings(samples):
    """Converts samples to sample times per observation."""
    groups = samples.groupby(axis=1, level=0)
    return groups.apply(lambda group: group.iloc[:, 1] - group.iloc[:, 0])


def _remove_other_timings(group):
    other_timings = (
        (group.iloc[:, 0] - group.iloc[:, 1].shift(1)).fillna(0).cumsum()
    )
    ret = group.groupby(axis=1, level=1).apply(
        lambda x: x.iloc[:, 0] - other_timings
    )
    ret.columns = group.columns
    return ret


def isolate(samples):
    """For each function, isolates its begin and end times.

    Within each function's begins and ends, each begin will be equal
    to the previous end.  This gives a sequence of begins and ends as
    if each function were run in isolation with no benchmarking
    overhead.
    """
    zeroed = samples.groupby(axis=1, level=0).apply(
        lambda group: group - group.iloc[0, 0]
    )
    return zeroed.groupby(axis=1, level=0).apply(_remove_other_timings)


def _timing_in_context(group):
    time_col = pd.DataFrame(data=group.iloc[:, 1].values, columns=["time"])
    values = pd.DataFrame(data=timings(group), columns=[group.columns[0][0]])
    time_col = pd.to_timedelta(time_col["time"], unit="s")
    values = values.assign(time=time_col)
    return values.set_index("time")


def timings_in_context(samples):
    """Returns a sparse dataframe with a time index, with timings.

    Each cell contains the timing observed, at the time when it was
    observed.  Therefore, each row will have NaNs except for the
    function whose sample completed at that time.
    """
    iso = isolate(samples)
    t = iso.groupby(axis=1, level=0).apply(_timing_in_context)
    t.columns = t.columns.droplevel(0)
    return t


def bucket_resample_timings(
    samples, sample_size=10, agg=np.mean, sample_count=1000
):

    def _meat_axe(s):
        return pd.Series(
            [
                agg(np.random.choice(s.values, size=sample_size, replace=True))
                for _ in range(sample_count)
            ]
        )

    return timings(samples).apply(_meat_axe)


def _ks_Z(a, b):
    result = stats.ks_2samp(a, b)
    n = len(a)
    m = len(b)
    return result.statistic / np.sqrt((n + m) / (n * m))


def ks_test(t):
    """Runs the Kolmogorov-Smirnov test across functions.

    Returns a DataFrame containing all pairwise K-S test results.

    The standard K-S test computes :math:`D`, which is the maximum
    difference between the empirical CDFs.

    The result value we return is the :math:`Z` value, defined as

    .. math::

       Z = D / \\sqrt{(n + m) / nm}

    where :math:`n` and :math:`m` are the respective sample sizes.

    :math:`Z` is typically interpreted using a lookup table, i.e. for
    confidence level :math:`\\alpha`, we want to see a :math:`Z`
    greater than :math:`c(\\alpha)`:

    +--------------------+------+------+-------+------+-------+-------+
    | :math:`\\alpha`     | 0.10 | 0.05 | 0.025 | 0.01 | 0.005 | 0.001 |
    +--------------------+------+------+-------+------+-------+-------+
    | :math:`c(\\alpha)`  | 1.22 | 1.36 | 1.48  | 1.63 | 1.73  | 1.95  |
    +--------------------+------+------+-------+------+-------+-------+
    """
    data = {
        name: (
            [
                _ks_Z(t[name].values, t[t.columns[j]].values)
                for j in range(i + 1)
            ]
            + ([np.nan] * (len(t.columns) - 2 - i))
        )
        for i, name in enumerate(t.columns[1:])
    }
    idx = pd.Index(t.columns[:-1], name="K-S test Z")
    return pd.DataFrame(data, index=idx)


def _cumulative_quantiles(group, rng):
    group = isolate(group)
    t = timings(group)
    ret = pd.concat(
        [
            t.iloc[:(i + 1), :].describe().T[
                ["min", "25%", "50%", "75%", "max"]
            ]
            for i in rng
        ]
    )
    ret = ret.set_index(group.iloc[slice(rng.start, rng.stop), 1])
    ret.index.name = "time"
    return ret


def cumulative_quantiles(samples, rng=None):
    """Computes "cumulative quantiles" for each function.

    That is, for each time, what are the extremes, median, and
    25th/75th percentiles for all observations up until that point.
    """
    if rng is None:
        rng = range(len(samples.index))
    groups = samples.groupby(axis=1, level=0)
    df = groups.apply(lambda group: _cumulative_quantiles(group, rng))
    return df


def cumulative_quantiles_plot(
    samples, plot_width=960, plot_height=480, show_samples=True
):
    """Plots the cumulative quantiles along with a scatter plot of
    observations."""
    plot = bp.figure(plot_width=960, plot_height=480)

    names = samples.columns.levels[0]
    _colors = {
        name: color for name, color in zip(names, colors.colors(len(names)))
    }

    def draw(group):
        name = group.columns[0][0]
        color = _colors[name]
        group.columns = group.columns.droplevel(0)
        group = group.dropna()
        quantile_source = bm.ColumnDataSource(
            pd.DataFrame(
                data={"lower": group["25%"], "upper": group["75%"]},
                index=group.index,
            ).dropna().reset_index()
        )
        extreme_source = bm.ColumnDataSource(
            pd.DataFrame(
                data={"lower": group["min"], "upper": group["max"]},
                index=group.index,
            ).dropna().reset_index()
        )
        plot.line(group.index, group["50%"], line_color=color, legend=name)
        plot.add_layout(
            bm.Band(
                base="time",
                lower="lower",
                upper="upper",
                source=quantile_source,
                fill_color=color,
                fill_alpha=0.2,
            )
        )
        plot.add_layout(
            bm.Band(
                base="time",
                lower="lower",
                upper="upper",
                source=extreme_source,
                fill_color=color,
                fill_alpha=0.025,
            )
        )
        plot.line(
            "time", "lower", line_color=color, alpha=0.5, source=extreme_source
        )
        plot.line(
            "time", "upper", line_color=color, alpha=0.5, source=extreme_source
        )

    cumulative_quantiles(samples).groupby(axis=1, level=0).apply(draw)

    if show_samples:

        def scatter(group):
            name = group.columns[0][0]
            color = _colors[name]
            group = isolate(group)
            t = timings(group).set_index(group.iloc[:, 1])
            t.index.name = "time"
            t.columns = ["value"]
            source = bm.ColumnDataSource(t.reset_index())
            plot.circle(
                x="time",
                y="value",
                source=source,
                color=color,
                size=1,
                alpha=0.5,
            )

        samples.groupby(axis=1, level=0).apply(scatter)

    bi.show(plot)
