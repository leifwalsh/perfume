#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `perfume` package.

perfume is fairly visualization-heavy and deals with stochastic
events, so end-to-end testing isn't really aimed for here.  But we can
test the transformations in analyze somewhat.
"""


import unittest

import numpy as np
import numpy.testing as npt
import pandas as pd
import pandas.util.testing as pdt

from perfume import analyze


class TestAnalyze(unittest.TestCase):
    """Tests for `perfume.analyze` module."""

    def setUp(self):
        samples = []
        t = 1.0
        for i in range(20):
            sample = []
            sample.append(t)
            t += 1.1
            sample.append(t)
            t += 0.2
            sample.append(t)
            t += 1.5
            sample.append(t)
            t += 0.1
            samples.append(sample)
        self.samples = pd.DataFrame(
            data=samples,
            columns=pd.MultiIndex(
                levels=[["fn1", "fn2"], ["begin", "end"]],
                labels=[[0, 0, 1, 1], [0, 1, 0, 1]],
            ),
        )

    def tearDown(self):
        del self.samples

    def test_timings(self):
        """Test that timings gives us the right results."""
        timings = analyze.timings(self.samples)
        pdt.assert_index_equal(timings.index, self.samples.index)
        self.assertSetEqual(
            set(timings.columns), set(self.samples.columns.get_level_values(0))
        )
        self.assertEqual(len(timings.columns), len(self.samples.columns) / 2)
        npt.assert_array_almost_equal(timings["fn1"], 1.1)
        npt.assert_array_almost_equal(timings["fn2"], 1.5)

    def test_isolate(self):
        """Test that isolate gives us the right results."""
        isolated = analyze.isolate(self.samples)
        pdt.assert_index_equal(isolated.index, self.samples.index)
        pdt.assert_index_equal(isolated.columns, self.samples.columns)
        pdt.assert_frame_equal(
            analyze.timings(isolated), analyze.timings(self.samples)
        )
        npt.assert_array_almost_equal(
            isolated["fn1"]["begin"], np.arange(20) * 1.1
        )
        npt.assert_array_almost_equal(
            isolated["fn1"]["end"], 1.1 + (np.arange(20) * 1.1)
        )
        npt.assert_array_almost_equal(
            isolated["fn2"]["begin"], np.arange(20) * 1.5
        )
        npt.assert_array_almost_equal(
            isolated["fn2"]["end"], 1.5 + (np.arange(20) * 1.5)
        )

    def test_timings_in_context(self):
        """Test that timings_in_context gives us the right results."""
        in_context = analyze.timings_in_context(self.samples)
        # Since each "function" has a fixed frequency, we can create
        # two series with TimedeltaIndexes and align them into the
        # same DataFrame, which should be what timings_in_context
        # gives us.
        fn1_expected = pd.Series(
            1.1,
            index=pd.TimedeltaIndex(
                freq=pd.Timedelta("1.1s"),
                start="1.1s",
                periods=20,
                name="time",
            ),
        )
        fn2_expected = pd.Series(
            1.5,
            index=pd.TimedeltaIndex(
                freq=pd.Timedelta("1.5s"),
                start="1.5s",
                periods=20,
                name="time",
            ),
        )
        expected = pd.DataFrame({"fn1": fn1_expected, "fn2": fn2_expected})
        pdt.assert_frame_equal(in_context, expected)
