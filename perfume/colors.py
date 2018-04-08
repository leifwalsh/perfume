# -*- coding: utf-8 -*-

from bokeh import palettes


def colors(num_colors):
    if num_colors < 3:
        return iter(palettes.Set1[3][:num_colors])

    else:
        try:
            return iter(palettes.Set1[num_colors])

        except KeyError:
            raise Exception(
                "Too many functions to benchmark, we only have colors to "
                "support {}".format(max(palettes.Set1.keys()))
            )
