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
    """Create ERDDAP image request urls and download the time series images data set with the specified dataset ID"""

    # Set up logger
    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(asctime)s:%(module)s:%(levelname)s:%(message)s [line %(lineno)d]'
    logging.basicConfig(format=log_format, level=log_level)

    plotting_defaults_file = args.defaults
    dataset_id = args.dataset_id
    x_variable = args.xvar
    x_ascending = True
    y_variable = args.yvar
    y_ascending = False
    config_file = args.config_file
    start_time = args.start_time
    end_time = args.end_time
    hours = args.hours
    output_dir = args.outputdir
    image_type = args.image_type
    marker_size = args.markersize
    marker_type = args.markertype
    marker_color = args.markercolor
    line_style = args.graphtype
    erddap_url = args.url
    debug = args.debug
    clobber = args.clobber
    default_colorbar = 'Rainbow2'

    # Validate default plotting parameters file
    if not os.path.isfile(plotting_defaults_file):
        logging.error('Invalid plotting defaults file: {:}'.format(plotting_defaults_file))
        return 1
    try:
        with open(plotting_defaults_file, 'r') as fid:
            plot_variables = yaml.safe_load(fid)
    except Exception as e:
        logging.error('Default plotting parameters file: {:} ({:})'.format(plotting_defaults_file, e))
        return 1

    if not os.path.isdir(output_dir):
        logging.error('Invalid image destination: {:}'.format(output_dir))
        return 1
    logging.info('Image destination: {:}'.format(os.path.realpath(output_dir)))

    # Load the deployment specific plot parameters if specified in config_file
    plot_configs = None
    if config_file:
        if not os.path.isfile(config_file):
            logging.error('Plotting configuration file does not exist: {:}'.format(config_file))
            return 1

        try:
            with open(config_file, 'r') as fid:
                plot_configs = yaml.safe_load(fid)
        except (OSError, ValueError) as e:
            logging.error('Error parsing configuration file {:}: {:}'.format(config_file, e))
            return 1

    if plot_configs:
        logging.info('Updating default plotting variables and parameters')
        for plot_variable in plot_configs.keys():
            if plot_variable not in plot_variables:
                logging.info('Creating new plot variable: {:}'.format(plot_variable))
                plot_variables[plot_variable] = plot_variable[plot_variable]
            else:
                logging.info('Updating existing plot variable parameters: {:}'.format(plot_variable))
                plot_variables[plot_variable].update(plot_configs[plot_variable])

    # Create the plotter, set constraints, set plotting options
    plotter = TabledapPlotter(erddap_url)

    # Set the image destination directory
    plotter.image_path = output_dir

    # Make sure the dataset ID is valid
    if dataset_id not in plotter.datasets.index.to_list():
        logging.error('Invalid dataset specified: {:}'.format(dataset_id))
        return 1

    # Set the datasetID
    plotter.dataset_id = dataset_id

    if y_variable not in plotter.dataset_variables:
        logging.error('Y-axis variable {:} not found in the dataset'.format(y_variable))
        return 1
    logging.info('Y-Axis variable is {:}'.format(y_variable))
    if x_variable not in plotter.dataset_variables:
        logging.error('X-axis variable {:} not found in the dataset'.format(x_variable))
        return 1
    logging.info('X-Axis variable is {:}'.format(x_variable))

    # Handle time constraints
    ts0 = None
    ts1 = None
    if hours:
        logging.info('Plotting profiles less than {:} hours from the max time'.format(hours))
    #        plotter.add_constraint('time', '>=', 'max(time)-{:}hours'.format(hours))
    else:
        if start_time:
            try:
                dt0 = parser.parse(start_time)
                ts0 = dt0.strftime('%Y%m%dT%H%M%S')
                logging.info('Adding time constraint: >={:}'.format(ts0))
            #                plotter.add_constraint('time', '>=', ts0)
            except ValueError as e:
                logging.error('Error parsing start_time {:}: {:}'.format(start_time, e))

        if end_time:
            try:
                dt1 = parser.parse(end_time)
                ts1 = dt1.strftime('%Y%m%dT%H%M%S')
                logging.info('Adding time constraint: <={:}'.format(ts1))
            #                plotter.add_constraint('time', '>=', ts1)
            except ValueError as e:
                logging.error('Error parsing start_time {:}: {:}'.format(end_time, e))

    # Set the line style
    plotter.set_line_style(line_style)

    # Set the marker
    plotter.set_marker_style(marker_type, marker_size)

    # Set the marker color
    plotter.set_marker_color(marker_color)

    # Set the image type
    plotter.image_type = image_type

    for plot_var in plot_variables:

        # Clear previous constraints
        plotter.clear_constraints()

        # Add time constraints if there are any
        if hours:
            plotter.add_constraint('time', '>=', 'max(time)-{:}hours'.format(hours))
        else:
            if ts0:
                plotter.add_constraint('time', '>=', ts0)
            if ts1:
                plotter.add_constraint('time', '<=', ts1)

        if plot_var not in plotter.dataset_variables:
            logging.debug('Variable {:} not found in ERDDAP data set: {:}'.format(plot_var, dataset_id))
            continue

        # Fill in and add plot_variables[plot_var]['min'] and plot_variables[plot_var]['max'] from the variable's
        # 'actual_range' attribute if not specified in either the plotting_defaults_file or config_file
        if 'min' not in plot_variables[plot_var]:
            logging.info('No minimum value set for {:}'.format(plot_var))
            var_atts = plotter.get_variable_attributes(plot_var)
            if not var_atts.empty:
                # See if the variable contains an 'actual_range' attribute
                range_attr = var_atts[var_atts.attribute_name == 'actual_range']
                if not range_attr.empty:
                    min_value = float(range_attr.iloc[0]['value'].split(',')[0])
                    logging.info(
                        'Setting {:} min parameter to value in {:}:actual_range attribute: {:}'.format(plot_var,
                                                                                                       plot_var,
                                                                                                       min_value))
                    plot_variables[plot_var]['min'] = min_value
        if 'max' not in plot_variables[plot_var]:
            logging.info('No maximum value set for {:}'.format(plot_var))
            var_atts = plotter.get_variable_attributes(plot_var)
            if not var_atts.empty:
                # See if the variable contains an 'actual_range' attribute
                range_attr = var_atts[var_atts.attribute_name == 'actual_range']
                if not range_attr.empty:
                    max_value = float(range_attr.iloc[0]['value'].split(',')[1])
                    logging.info(
                        'Updating {:} max parameter to value in {:}:actual_range attribute: {:}'.format(plot_var,
                                                                                                        plot_var,
                                                                                                        max_value))
                    plot_variables[plot_var]['max'] = max_value

        cmin = None
        cmax = None
        if 'min' in plot_variables[plot_var]:
            logging.info('Setting {:} minimum value constraint: {:}'.format(plot_var, plot_variables[plot_var]['min']))
            plotter.add_constraint(plot_var, '>=', plot_variables[plot_var]['min'])
            cmin = plot_variables[plot_var]['min']
        if 'max' in plot_variables[plot_var]:
            logging.info('Setting {:} maximum value constraint: {:}'.format(plot_var, plot_variables[plot_var]['max']))
            plotter.add_constraint(plot_var, '<=', plot_variables[plot_var]['max'])
            cmax = plot_variables[plot_var]['max']

        if 'zmin' in plot_variables[plot_var]:
            logging.info('Setting {:} minimum value constraint: {:}'.format(plot_var, plot_variables[plot_var]['zmin']))
            plotter.add_constraint(plot_var, '>=', plot_variables[plot_var]['min'])
        if 'zmax' in plot_variables[plot_var]:
            logging.info('Setting {:} maximum value constraint: {:}'.format(plot_var, plot_variables[plot_var]['zmax']))
            plotter.add_constraint(plot_var, '<=', plot_variables[plot_var]['max'])

        # Set the x-axis direction
        plotter.set_x_range(ascending=x_ascending)

        # Set the y-axis direction
        plotter.set_y_range(ascending=y_ascending)

        # Set the color bar with color bar name, min and max values
        plot_var_colorbar = plot_variables[plot_var].get('colorbar', default_colorbar)
        plotter.set_color_bar(plot_var_colorbar, min_value=cmin, max_value=cmax)

        # Add constraint to NOT plot NaN values
        plotter.add_constraint(plot_var, '!=', 'NaN')

        logging.info('Creating url...')
        it0 = datetime.datetime.now()
        plotter.build_image_request(x_variable, y_variable, plot_var)
        it1 = datetime.datetime.now()
        i_delta = it1 - it0
        logging.info('{:} profiles image downloaded in {:0.1f} seconds'.format(plot_var, i_delta.total_seconds()))
        # Print the url but do not send the request
        if debug:
            logging.info('URL: {:}'.format(plotter.image_url))
            logging.info('Skipping request (-x)')
            continue

        # Download the image
        image_name = '{:}_{:}_ts_{:}.png'.format(dataset_id, plot_var, image_type)
        image_path = plotter.download_image(image_name, clobber=clobber)
        if image_path:
            logging.info('Image written: {:}'.format(image_path))


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description=main.__doc__,
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    arg_parser.add_argument('dataset_id',
                            help='Dataset ID string to search for')

    arg_parser.add_argument('-x', '--xvar',
                            type=str,
                            default='time',
                            help='X-axis variable for plotting')

    arg_parser.add_argument('-y', '--yvar',
                            type=str,
                            default='depth',
                            help='Y-axis variable for plotting')

    arg_parser.add_argument('--cmin',
                            help='Minimum color bar value')

    arg_parser.add_argument('--cmax',
                            help='Maximum color bar value')

    arg_parser.add_argument('--config_file',
                            help='YAML file containing variables and min/max limits for plotting')

    arg_parser.add_argument('--start',
                            help='Start date/time string [YYYY-mm-ddTHH:MM]',
                            dest='start_time')

    arg_parser.add_argument('--end',
                            help='End date/time string [YYYY-mm-ddTHH:MM]',
                            dest='end_time')

    arg_parser.add_argument('--lasthrs',
                            help='Number of previous hours to plot from max time',
                            dest='hours',
                            type=int)

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
                            default=5)

    arg_parser.add_argument('-m', '--markercolor',
                            type=str,
                            help='Marker color',
                            choices=plot_options['colors'].keys(),
                            default='black')

    arg_parser.add_argument('-t', '--markertype',
                            type=str,
                            help='Marker type from ERDDAP graph marker pulldown',
                            choices=plot_options['marker_types'],
                            default='Borderless Filled Circle')

    arg_parser.add_argument('-g', '--graphtype',
                            type=str,
                            help='Line style from ERDDAP graph marker pulldown',
                            choices=plot_options['line_styles'],
                            default='markers')

    arg_parser.add_argument('--colorbar',
                            type=str,
                            help='Name of default color bar to use if not specified in the config file(s)',
                            dest='default_colorbar',
                            choices=plot_options['color_bars'],
                            default='Rainbow2')

    arg_parser.add_argument('-u', '--url',
                            help='ERDDAP server base url',
                            default='http://slocum-data.marine.rutgers.edu/erddap')

    arg_parser.add_argument('-d', '--defaults',
                            help='YAML sensors and plotting defaults',
                            default=os.path.realpath(os.path.join(os.path.dirname(__file__),
                                                                  '..',
                                                                  '..',
                                                                  'config',
                                                                  'erddap_plot_vars.yml')))

    arg_parser.add_argument('--debug',
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
