"""A bokeh app for visualizing the calibration progress."""
import numpy as np
from _redis_tools import array_from_redis, redis
from bokeh.io import curdoc
from bokeh.layouts import column, gridplot
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure

# this is the data source we will stream to
s11_source = ColumnDataSource(
    data=dict(
        re_begin=[],
        re_mid=[],
        re_end=[],
        im_begin=[],
        im_mid=[],
        im_end=[],
        re_rms=[],
        im_rms=[],
        iter=[],
    )
)

temp_source = ColumnDataSource(data=dict(temps=[], iter=[]))

n_data = {name: 0 for name in s11_source.column_names + temp_source.column_names}

fig_begin = figure(title="S11 [40MHz]")
fig_mid = figure(title="S11 [120MHz]")
fig_end = figure(title="S11 [200MHz]")
fig_rms = figure(title="S11 RMS")
fig_temp = figure(title="Thermistor Temp")


grid = gridplot(
    [[fig_begin, fig_mid, fig_end], [fig_rms, fig_temp, None]],
    plot_width=500,
    plot_height=300,
)

fig_begin.line(x="iter", y="re_begin", source=s11_source, legend_label="Real")
fig_begin.line(
    x="iter", y="im_begin", source=s11_source, color="orange", legend_label="Imaginary"
)

fig_mid.line(x="iter", y="re_mid", source=s11_source)
fig_mid.line(x="iter", y="im_mid", source=s11_source, color="orange")

fig_end.line(x="iter", y="re_end", source=s11_source)
fig_end.line(x="iter", y="im_end", source=s11_source, color="orange")

fig_rms.line(x="iter", y="re_rms", source=s11_source)
fig_rms.line(x="iter", y="im_rms", source=s11_source, color="orange")

fig_temp.line(x="iter", y="temps", source=temp_source)


def update():
    """Update all the sources from new data in redis."""
    for source in [s11_source, temp_source]:
        new_data = {}

        for clm in source.column_names:
            if clm == "iter":
                continue

            try:
                data = array_from_redis(redis, clm)
            except KeyError as e:
                print(str(e))
                new_data = {}
                break

            new_data[clm] = data[n_data[clm] :]
            new_data["iter"] = np.arange(n_data[clm], len(data))
            n_data[clm] = len(data)

        if new_data:
            source.stream(new_data)


# create a layout for everything
layout = column(grid)


curdoc().add_periodic_callback(update, 1000)

# add the layout to curdoc
curdoc().add_root(layout)
