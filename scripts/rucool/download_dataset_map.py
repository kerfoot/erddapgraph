#!/usr/bin/env python

import argparse
import logging
import os
from erddapgraph.tabledap import TabledapPlotter
from erddapgraph import plot_options
import sys
import yaml
import datetime
from dateutil import parser


def main(args):
    """Download the full track map for the specified ERDDAP dataset id"""

    # Set up logger
    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(asctime)s:%(module)s:%(levelname)s:%(message)s [line %(lineno)d]'
    logging.basicConfig(format=log_format, level=log_level)

#    plotting_defaults_file = args.defaults
    dataset_id = args.dataset_id
    x_variable = args.xvar
    x_ascending = True
    y_variable = args.yvar
    y_ascending = False
    color_variable = args.color
    cmin = args.cmin
    cmax = args.cmax
#    config_file = args.config_file
    start_time = args.start_time
    end_time = args.end_time
    hours = args.hours
    output_dir = args.outputdir
    image_type = args.image_type
    marker_size = args.markersize
    marker_type = args.markertype
    marker_color = args.markercolor
    line_style = args.graphtype
    color_bar = args.colorbar
#    background_color = args.background_color
    erddap_url = args.url
    debug = args.debug
    clobber = args.clobber

    if not os.path.isdir(output_dir):
        logging.error('Invalid image destination: {:}'.format(output_dir))
        return 1
    logging.info('Image destination: {:}'.format(os.path.realpath(output_dir)))

    # Create the plotter, set constraints, set plotting options
    plotter = TabledapPlotter(erddap_url)

    # Make sure the dataset ID is valid
    if dataset_id not in plotter.datasets.index.to_list():
        logging.error('Invalid dataset specified: {:}'.format(dataset_id))
        return 1

    # Set the datasetID
    plotter.dataset_id = dataset_id

    # Validate x variable exists in the data set
    if x_variable not in plotter.dataset_variables:
        logging.error('X-axis variable {:} not found in the dataset'.format(x_variable))
        return 1

    # Validate y variable exists in the data set
    if y_variable not in plotter.dataset_variables:
        logging.error('Y-axis variable {:} not found in the dataset'.format(y_variable))
        return 1

    # Validate color variable exists in the data set
    if color_variable and color_variable not in plotter.dataset_variables:
        logging.error('Color variable {:} not found in the dataset'.format(color_variable))
        return 1

    logging.info('X-Axis variable is {:}'.format(x_variable))
    logging.info('Y-Axis variable is {:}'.format(y_variable))
    logging.info('Color variable is {:}'.format(color_variable))

    # Make sure no requested variables have duplicates
    plot_vars_size = len({x_variable, y_variable, color_variable})
    if plot_vars_size != 3:
        logging.error('One or more duplicate variable requested')
        return 1

    # Handle time constraints
    ts0 = None
    ts1 = None
    if hours > 0:
        logging.info('Plotting profiles less than {:} hours from the max time'.format(hours))
        plotter.add_constraint('time', '>=', 'max(time)-{:}hours'.format(hours))
    else:
        if start_time:
            try:
                dt0 = parser.parse(start_time)
                ts0 = dt0.strftime('%Y%m%dT%H%M%S')
                logging.info('Adding time constraint: >={:}'.format(ts0))
                plotter.add_constraint('time', '>=', ts0)
            except ValueError as e:
                logging.error('Error parsing start_time {:}: {:}'.format(start_time, e))

        if end_time:
            try:
                dt1 = parser.parse(end_time)
                ts1 = dt1.strftime('%Y%m%dT%H%M%S')
                logging.info('Adding time constraint: <={:}'.format(ts1))
                plotter.add_constraint('time', '<=', ts1)
            except ValueError as e:
                logging.error('Error parsing start_time {:}: {:}'.format(end_time, e))

    # Set the image destination directory
    plotter.image_path = os.path.realpath(output_dir)

    # Set the line style
    plotter.set_line_style(line_style)

    # Set the marker
    plotter.set_marker_style(marker_type, marker_size)

    # Set the marker color
    plotter.set_marker_color(marker_color)

    # Set the image type
    plotter.image_type = image_type

    # Y and X axis direction
    plotter.set_y_range(ascending=y_ascending)
    plotter.set_x_range(ascending=x_ascending)

    # Set the color bar
    if color_bar:
        plotter.set_color_bar(color_bar, min_value=cmin, max_value=cmax)

    # Add constraint to NOT plot NaN values
    plotter.add_constraint(color_variable, '!=', 'NaN')

    logging.info('Creating url...')
    plotter.build_image_request(x_variable, y_variable, color_variable)
    # Print the url but do not send the request
    if debug:
        logging.info('URL: {:}'.format(plotter.image_url))
        logging.info('Skipping request (-x)')
        return 0

    # Download the image
    image_name = '{:}_track_map_{:}.png'.format(dataset_id, image_type)
    it0 = datetime.datetime.now()
    image_path = plotter.download_image(image_name, clobber=clobber)
    it1 = datetime.datetime.now()
    i_delta = it1 - it0
    logging.info('Map image downloaded in {:0.1f} seconds'.format(i_delta.total_seconds()))
    if image_path:
        logging.info('Image written: {:}'.format(image_path))


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description=main.__doc__,
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    arg_parser.add_argument('dataset_id',
                            help='Dataset ID string to search for')

    arg_parser.add_argument('--xvar',
                            type=str,
                            default='longitude',
                            help='Longitude variable to use for x-axis')

    arg_parser.add_argument('--yvar',
                            type=str,
                            default='latitude',
                            help='Latitude variable to use for y-axis')

    arg_parser.add_argument('-c', '--color',
                            type=str,
                            help='Color the markers using the specified variable. If not specified, the default '
                                 'markercolor is used')

    arg_parser.add_argument('--cmin',
                            help='Minimum color bar value')

    arg_parser.add_argument('--cmax',
                            help='Maximum color bar value')

    arg_parser.add_argument('--start',
                            help='Start date/time string [YYYY-mm-ddTHH:MM]',
                            dest='start_time')

    arg_parser.add_argument('--end',
                            help='End date/time string [YYYY-mm-ddTHH:MM]',
                            dest='end_time')

    arg_parser.add_argument('--lasthrs',
                            help='Number of previous hours to plot from max time',
                            dest='hours',
                            type=int,
                            default=0)

    arg_parser.add_argument('-o', '--outputdir',
                            type=str,
                            help='Write location',
                            default='.')

    arg_parser.add_argument('--clobber',
                            action='store_true',
                            help='Clobber existing image if the file already exists')

    arg_parser.add_argument('-i', '--image_type',
                            type=str,
                            choices=plot_options['image_types'],
                            default='largePng',
                            help='Image type')

    arg_parser.add_argument('-s', '--markersize',
                            type=int,
                            help='Marker size',
                            default=7)

    arg_parser.add_argument('-m', '--markercolor',
                            type=str,
                            help='Marker color',
                            choices=plot_options['colors'].keys(),
                            default='black')

    arg_parser.add_argument('-t', '--markertype',
                            type=str,
                            help='Marker type from ERDDAP graph marker pulldown. Enclose in single quotes if marker type'
                                 ' contains whitespace.',
                            choices=plot_options['marker_types'],
                            default='Circle')

    arg_parser.add_argument('-g', '--graphtype',
                            type=str,
                            help='Line style from ERDDAP graph marker pulldown',
                            choices=plot_options['line_styles'],
                            default='markers')

    arg_parser.add_argument('--colorbar',
                            type=str,
                            help='Colorbar name',
                            choices=plot_options['color_bars'],
                            default='Rainbow2')

    arg_parser.add_argument('-u', '--url',
                            help='ERDDAP server base url',
                            default='https://slocum-data.marine.rutgers.edu/erddap')

    arg_parser.add_argument('-x', '--debug',
                            help='Print image request URL but do not send the request',
                            action='store_true')

    arg_parser.add_argument('-l', '--loglevel',
                            help='Verbosity level <Default=info>',
                            type=str,
                            choices=['debug', 'info', 'warning', 'error', 'critical'],
                            default='info')

    parsed_args = arg_parser.parse_args()

#    print(parsed_args)
#    sys.exit(0)

    sys.exit(main(parsed_args))
