"""
2023-01-12: kerfoot@marine.rutgers.edu - init

download_timeseries.py - download a time series of time (x) vs depth (y) with markers color coded by temperature
Steps:
1. Create the plotter instance and connect to the ERDDAP server
2. View available data sets
3. Configure the plot paramters
    - set line style to 'markers'
    - set marker to 'dot'
    - set color bar to 'KT_thermal' for plotting temperature
4. Add any optional constraints
5. build the image request
6. download the requested image
"""
import logging
import os
from pprint import pprint as pp
from erddapgraph.tabledap import TabledapPlotter

# Set up logger
log_level = 'INFO'
log_format = '%(asctime)s:%(module)s:%(levelname)s:%(message)s [line %(lineno)d]'
logging.basicConfig(format=log_format, level=log_level)

# ERDDAP Server
erddap_url = 'https://gliders.ioos.us/erddap'

# Create the plotter instance and connect to the erddap_url server
plotter = TabledapPlotter(erddap_url)

# Set image path. This is the destination path for all downloaded images.
plotter.image_path = '/Users/kerfoot/code/erddapgraph/img'

# Find data sets in which the datasetID begins with ru29
target_string = '^ru29'
datasets = plotter.search_datasets('^ru29')
logging.info('Found {:} data sets containing the target string {:}'.format(datasets.shape[0], target_string))
# Print the list of data set IDs
pp(datasets.index.values.tolist())

# set the target data set id
plotter.dataset_id = datasets.index.values.tolist()[-1]

# show the data set time interval
plotter.dataset_time_range

# Display the default plotting parameters
logging.info('Default plotting parameters:')
pp(plotter.plot_parameters)

# Set the plotting paramters (Make A Graph API graphics commands)
# Available linestyles
logging.info('Available line styles:')
pp(plotter.line_styles)
# Set the line style
plotter.set_line_style = 'markers'

# Available marker types
logging.info('Available markers:')
pp(plotter.marker_types)
# Set the marker type and size
plotter.set_marker_style('Dot', marker_size=5)

# X-Axis settings
# The default x axis parameters show the min and max x values, axis direction=Ascending and scale=Linear. This is what
# we want for the x axis, so no need to call plotter.set_x_range()

# Y-Axis setting
# The default y axis parameters show the min and max y values, axis direction=Descending and scale=Linear. This is what
# we want for the y axis, so no need to call plotter.set_y_range()

# Colorbar
# We're going to plot temperture, so we need to set the color bar to 'KT_thermal'. The plotter.set_color_bar parameters
# are: set_color_bar(color_bar, continuous='C', scale='Linear', min_value=None, max_value=None, num_sections=None) for
# a linearly scaled colorbar, scale to the c variable min and max values with predetermined number of sections. This is
# what we want, so no need to update these paramters
logging.info('Setting color bar to KT_thermal')
plotter.set_color_bar('KT_thermal')

# Show updated plotting parameters
logging.info('Updated plotting parameters:')
pp(plotter.plot_parameters)

# Show the data set variables
logging.info('Variables in {:} data set'.format(plotter.dataset_id))
pp(plotter.dataset_variables)

# Set the x, y and c variables and build the resulting image request
image_url = plotter.build_image_request('time', 'depth', 'temperature')

# Download the image and write to the qualified image name. The path to the image must exist
status = plotter.download_image('temperature_section.png')

# Now that we have the entire temperature section, let's create a new section that just contains the last 72hrs of data
# by adding a constraint
plotter.add_constraint('time', '>=', 'max(time)-72hours')
# View updated constraints
plotter.constraints

# Build the updated image request url
image_url = plotter.build_image_request('time', 'depth', 'temperature')

# Send the request and download the image to plotter.image_path
plotter.download_image('temperature_section_last72hours.png')