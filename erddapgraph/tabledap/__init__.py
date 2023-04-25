"""Class TabledapPlotter
Class for creating image request URLs from an ERDDAP tabledap data set's Make A Graph API and downloading the image(s).
ERDDAP Make A Graph API Documentation:
    https://gliders.ioos.us/erddap/tabledap/documentation.html#GraphicsCommands
"""
from erddapy import ERDDAP
from erddapy import servers
import pandas as pd
import requests
import logging
import os
import re
import yaml
from urllib.parse import quote
import subprocess
from erddapgraph import plot_options


class TabledapPlotter(object):

    def __init__(self, erddap_url):
        """
        Create a new instance and connect to the specified ERDDAP server
        :param erddap_url: ERDDAP server home page (should begin with 'http' and end with '/erddap'
        """

        self._logger = logging.getLogger(os.path.basename(__file__))
        self._protocol = 'tabledap'
        self._plot_options = None
        self._num_datasets = 0
        self._items_per_page = 1e6
        self._e = ERDDAP(erddap_url, protocol=self._protocol, response='png')
        self._servers = servers
        self._datasets = pd.DataFrame()
        self._dataset_description = pd.DataFrame()

        self._default_plot_parameters = {'.bgColor=': '0xFFCCCCFF',
                                         '.color=': '0x000000',
                                         '.colorBar=': 'Rainbow2|C|Linear|||',
                                         '.draw=': 'markers',
                                         '.legend=': 'Bottom',
                                         '.marker=': '6|5',
                                         '.xRange=': '||true|Linear',
                                         '.yRange=': '||false|Linear'}

        self._dataset_id = None
        self._constraints = {}
        self._plot_parameters = self._default_plot_parameters.copy()
        self._plot_query = None
        self._constraints_query = None
        self._image_url = None
        self._last_request = None
        self._last_request = None
        self._image_app = None
        self._last_image = None
        self._image_path = os.path.realpath(os.path.curdir)

        # Option types that should be found in the self._plot_options_file
        option_types = ['image_types',
                        'legend_options',
                        'line_styles',
                        'marker_types',
                        'colors',
                        'opacities',
                        'continuous_options',
                        'scale_options',
                        'color_bars',
                        'zoom_levels',
                        'operators']

        # Find and load the ERDDAP MakeAGraph plotting options
        self._plot_options = plot_options
        self._plot_options_file = plot_options['options_file']

        # Check to make sure that all option_types are found in self._plot_options_file
        for option_type in option_types:
            if option_type not in self._plot_options:
                self._logger.warning(
                    'Option {:} not found in plot options configuration file: {:}'.format(option_type,
                                                                                          plot_options['options_file']))

        self._fetch_datasets()

        # Set the image display shell utility
        self.image_app = 'open'

        # Regex to match RRGGBB colors
        self._hex_regex = re.compile(r'^[a-z0-9]{6}$', re.IGNORECASE)

    @property
    def image_path(self):
        return self._image_path

    @image_path.setter
    def image_path(self, image_path):
        image_path = os.path.realpath(image_path)
        if os.path.isdir(image_path):
            self._image_path = image_path
            return

        self._logger.error('Invalid image path: {:}'.format(image_path))

    @property
    def background_color(self):
        graphics_command = '.bgColor='
        if graphics_command in self._plot_parameters:
            return self._plot_parameters[graphics_command]

        self._logger.warning('{:} not set'.format(graphics_command))

    @property
    def color_bar(self):
        graphics_command = '.colorBar='
        if graphics_command in self._plot_parameters:
            return self._plot_parameters[graphics_command]

        self._logger.warning('{:} not set'.format(graphics_command))

    @property
    def marker_color(self):
        graphics_command = '.color='
        if graphics_command in self._plot_parameters:
            return self._plot_parameters[graphics_command]

        self._logger.warning('{:} not set'.format(graphics_command))

    @property
    def line_style(self):
        graphics_command = '.draw='
        if graphics_command in self._plot_parameters:
            return self._plot_parameters[graphics_command]

        self._logger.warning('{:} not set'.format(graphics_command))

    @property
    def legend(self):
        graphics_command = '.legend='
        if graphics_command in self._plot_parameters:
            return self._plot_parameters[graphics_command]

        self._logger.warning('{:} not set'.format(graphics_command))

    @property
    def marker(self):
        graphics_command = '.marker='
        if graphics_command in self._plot_parameters:
            return self._plot_parameters[graphics_command]

        self._logger.warning('{:} not set'.format(graphics_command))

    @property
    def x_range(self):
        graphics_command = '.xRange='
        if graphics_command in self._plot_parameters:
            return self._plot_parameters[graphics_command]

        self._logger.warning('{:} not set'.format(graphics_command))

    @property
    def size(self):
        graphics_command = '.size='
        if graphics_command in self._plot_parameters:
            return self._plot_parameters[graphics_command]

        self._logger.warning('{:} not set'.format(graphics_command))

    @property
    def trim(self):
        graphics_command = '.trim='
        if graphics_command in self._plot_parameters:
            return self._plot_parameters[graphics_command]

        self._logger.warning('{:} not set'.format(graphics_command))

    @property
    def y_range(self):
        graphics_command = '.yRange='
        if graphics_command in self._plot_parameters:
            return self._plot_parameters[graphics_command]

    @property
    def zoom(self):
        graphics_command = '.zoom='
        if graphics_command in self._plot_parameters:
            return self._plot_parameters[graphics_command]

    @property
    def servers(self):
        return self._servers

    @property
    def image_app(self):
        return self._image_app

    @image_app.setter
    def image_app(self, image_app):

        if not image_app:
            self._logger.warning('No image viewer specified')
            return

        result = subprocess.run(['which', image_app], stdout=subprocess.PIPE)
        if not result.stdout:
            self._logger.warning('Image app {:} not found'.format(self._image_app))
            return

        self._image_app = result.stdout.decode().strip()

    @property
    def image_type(self):
        return self._e.response

    @image_type.setter
    def image_type(self, image_type):
        if image_type not in self._plot_options['image_types']:
            self._logger.error('Invalid image type specified: {:}'.format(image_type))
            return

        self._e.response = image_type

    @property
    def dataset_id(self):
        return self._dataset_id

    @dataset_id.setter
    def dataset_id(self, dataset_id):
        if dataset_id not in self._datasets.index:
            self._logger.error('Invalid dataset_id: {:}'.format(dataset_id))
            return

        self._logger.info('Selected dataset_id: {:}'.format(dataset_id))
        self._dataset_id = dataset_id

        # Fetch the data set metadata/description
        self.get_dataset_description()

    #        self._get_dataset_variables()

    @property
    def dataset_variables(self):
        #        return self._dataset_variables

        return sorted(
            self._dataset_description[self._dataset_description['row_type'] == 'variable']['variable_name'].tolist())

    @property
    def dataset_description(self):

        return self._dataset_description

    @property
    def plotting_query(self):
        return self._plot_query

    @property
    def constraints_query(self):
        return self._constraints_query

    @property
    def image_url(self):
        return self._image_url

    @property
    def e(self):
        return self._e

    @property
    def server(self):
        return self._e.server

    @server.setter
    def server(self, erddap_url):

        # If erddap_url does not start with http, then assume it is a shortcut name of servers contained in
        # ERDDAP.server
        if not erddap_url.startswith('http'):
            if erddap_url not in self._servers:
                self._logger.error('Server name {:} not found in erddapy.ERDDAP.servers'.format(erddap_url))
                self._logger.error('Please specify a valid ERDDAP server shortcut name or valid server address')
                return
            erddap_url = self._servers[erddap_url].url

        self._logger.info('Connecting to server: {:}'.format(erddap_url))
        self._e.server = erddap_url
        self._logger.info('Fetching data sets...')
        self._fetch_datasets()
        self._logger.info('Clearing existing constraints...')
        self.clear_constraints()
        self._logger.info('Setting plot parameters to defaults...')
        self.reset_plot_parameters()
        self._logger.info(self)

        self._last_request = None
        self._dataset_id = None
        self._plot_query = None
        self._constraints_query = None
        self._image_url = None
        self._last_request = None

    @property
    def datasets(self):
        return self._datasets

    @property
    def last_request(self):
        return self._last_request

    @property
    def plot_parameters(self):
        return self._plot_parameters

    @property
    def image_types(self):
        if 'image_types' not in self._plot_options:
            self._logger.critical(
                'No image types found in plot options configuration file: {:}'.format(self._plot_options_file))
            return []

        return self._plot_options['image_types']

    @property
    def legend_options(self):
        if 'legend_options' not in self._plot_options:
            self._logger.critical(
                'No legend options found in plot options configuration file: {:}'.format(self._plot_options_file))
            return []

        return self._plot_options['legend_options']

    @property
    def line_styles(self):
        if 'line_styles' not in self._plot_options:
            self._logger.critical(
                'No line styles found in plot options configuration file: {:}'.format(self._plot_options_file))
            return []

        return self._plot_options['line_styles']

    @property
    def marker_types(self):
        if 'marker_types' not in self._plot_options:
            self._logger.critical(
                'No marker types found in plot options configuration file: {:}'.format(self._plot_options_file))
            return []

        return self._plot_options['marker_types']

    @property
    def colors(self):
        if 'colors' not in self._plot_options:
            self._logger.critical(
                'No colors found in plot options configuration file: {:}'.format(self._plot_options_file))
            return []

        return self._plot_options['colors'].keys()

    @property
    def opacities(self):
        if 'opacities' not in self._plot_options:
            self._logger.critical(
                'No opacities found in plot options configuration file: {:}'.format(self._plot_options_file))
            return []

        return self._plot_options['opacities']

    @property
    def continuous_options(self):
        if 'continuous_options' not in self._plot_options:
            self._logger.critical(
                'No color bar continuity options found in plot options configuration file: {:}'.format(
                    self._plot_options_file))
            return []

        return self._plot_options['continuous_options']

    @property
    def scale_options(self):
        if 'scale_options' not in self._plot_options:
            self._logger.critical(
                'No scale types found in plot options configuration file: {:}'.format(self._plot_options_file))
            return []

        return self._plot_options['scale_options']

    @property
    def color_bars(self):
        if 'color_bars' not in self._plot_options:
            self._logger.critical(
                'No color bars found in plot options configuration file: {:}'.format(self._plot_options_file))
            return []

        return self._plot_options['color_bars']

    @property
    def zoom_levels(self):
        if 'zoom_levels' not in self._plot_options:
            self._logger.critical(
                'No zoom levels found in plot options configuration file: {:}'.format(self._plot_options_file))
            return []

        return self._plot_options['zoom_levels']

    @property
    def operators(self):
        if 'operators' not in self._plot_options:
            self._logger.critical(
                'No constraint operators found in plot options configuration file: {:}'.format(self._plot_options_file))
            return []

        return self._plot_options['operators']

    @property
    def constraints(self):
        return self._constraints

    @property
    def dataset_time_range(self):
        if not self._dataset_id:
            self._logger.warning('Please specify a dataset id (self.dataset_id)')
            return

        return self._datasets.loc[self._dataset_id, ['minTime', 'maxTime']]

    def set_background_color(self, color, opacity='ff'):
        """
        Set the image background color and (optionally) opacity
        :param color: name of the color, which must be in self.colors
        :param opacity: hexadecimal representation (00-FF) for the opacity. 00 is clear, FF is fully opaque
        :return:
        """

        if color in self.colors:
            rrggbb = self._plot_options['colors'][color]
        else:
            match = self._hex_regex.fullmatch(color)
            if not match:
                self._logger.error('Invalid color specified: {:}'.format(color))
                return
            rrggbb = color

        aa = opacity.upper()
        if opacity not in self.opacities:
            self._logger.error('Invalid opacity specified: {:}'.format(opacity))
            return

        self._plot_parameters.update({'.bgColor=': '0x{:}{:}'.format(aa, rrggbb)})

    def set_color_bar(self, color_bar, continuous='C', scale='Linear', min_value=None, max_value=None,
                      num_sections=None):
        """
        Set the color bar and associated color bar parameters
        :param color_bar: Name of the color bar, which must be in self.color_bars
        :param continuous: C (continuous) or D (discrete)
        :param scale: Linear or Log
        :param min_value: minimum value for the color bar
        :param max_value: maximum value for the color bar
        :param num_sections: preferred number of sections in the color bar
        :return:
        """
        if color_bar not in self._plot_options['color_bars']:
            self._logger.error('Invalid color bar specified: {:}'.format(color_bar))
            self._logger.error('Please specify a valid color bar contained in self.color_bars')
            return

        if continuous not in self._plot_options['continuous_options']:
            self._logger.warning('Invalid continuous option specified: {:}'.format(continuous))
            self._logger.warning('Defaulting to C (continuous)')
            continuous = 'C'

        if scale not in self._plot_options['scale_options']:
            self._logger.warning('Invalid scale option specified: {:}'.format(scale))
            self._logger.warning('Defaulting to Linear')
            scale = 'Linear'

        if min_value is None:
            min_value = ''

        if max_value is None:
            max_value = ''

        if not num_sections:
            num_sections = ''

        self._plot_parameters.update({'.colorBar=': '{:}|{:}|{:}|{:}|{:}|{:}'.format(color_bar,
                                                                                     continuous,
                                                                                     scale,
                                                                                     min_value,
                                                                                     max_value,
                                                                                     num_sections)})

    def set_marker_color(self, color):
        """
        Set the marker color
        :param color: name of the color, which must be in self.colors
        :return:
        """
        if color not in self.colors:
            self._logger.error('Invalid color specified: {:}'.format(color))
            self._logger.error('Please specify a valid color name from self.colors')
            return

        self._plot_parameters.update({'.color=': '0x{:}'.format(self._plot_options['colors'][color])})

    def set_line_style(self, line_style):
        """
        Set the line style for plotting
        :param line_style: lines sytle, which must be in self.line_styles
        :return:
        """
        if line_style not in self._plot_options['line_styles']:
            self._logger.error('Invalid line style specified: {:}'.format(line_style))
            self._logger.error('Please specify a valid line style from self.line_styles')
            return

        self._plot_parameters.update({'.draw=': line_style})

    def set_marker_style(self, marker, marker_size=5):
        """
        Set the marker style for plotting
        :param marker: marker type, which must be in self.marker_types
        :param marker_size: [optional] integer specifying the marker size
        :return:
        """
        if marker not in self._plot_options['marker_types']:
            self._logger.error('Invalid marker specified: {:}'.format(marker))
            self._logger.error('Please specify a valid marker from self.marker_types')
            return

        self._plot_parameters.update(
            {'.marker=': '{:}|{:}'.format(self._plot_options['marker_types'].index(marker), marker_size)})

    def set_legend(self, location):

        if location not in self._plot_options['legend_options']:
            self._logger.error('Invalid legend location specified: {:}'.format(location))
            self._logger.error('Please specify a valid legend location from self.legend_locations')
            return

        self._plot_parameters.update({'.legend=': location})

    def set_x_range(self, min_value=None, max_value=None, ascending=True, scale='Linear'):
        """
        Set the x axis plotting parameters
        :param min_value: minimum x value [default=minimum x value]
        :param max_value: maximum x value [default=maximum x value]
        :param ascending: ascending if True, descending if False [default=True for ascending axis]
        :param scale: Linear or Log [default='Linear']
        :return:
        """

        scale = scale or self._plot_options['scale_options'][0]
        if scale not in self._plot_options['scale_options']:
            self._logger.error('Invalid scale value: {:}'.format(scale))
            self._logger.error('Please select a value from self.scale_options')
            return

        if not isinstance(ascending, bool):
            self._logger.error('Value for ascending must be a boolean')
            return

        if not min_value:
            min_value = ''
        if not max_value:
            max_value = ''

        self._plot_parameters.update({'.xRange=': '{:}|{:}|{:}|{:}'.format(min_value,
                                                                           max_value,
                                                                           str(ascending).lower(),
                                                                           scale)})

    def set_y_range(self, min_value='', max_value='', ascending=False, scale=None):
        """
        Set the y axis plotting parameters
        :param min_value: minimum x value
        :param max_value: maximum x value
        :param ascending: ascending if True, descending if False
        :param scale: Linear or Log
        :return:
        """

        scale = scale or self._plot_options['scale_options'][0]
        if scale not in self._plot_options['scale_options']:
            self._logger.error('Invalid scale value: {:}'.format(scale))
            self._logger.error('Please select a value from self.scale_options')
            return

        if not isinstance(ascending, bool):
            self._logger.error('Value for ascending must be a boolean')
            return

        if not min_value:
            min_value = ''
        if not max_value:
            max_value = ''

        self._plot_parameters.update({'.yRange=': '{:}|{:}|{:}|{:}'.format(min_value,
                                                                           max_value,
                                                                           str(ascending).lower(),
                                                                           scale)})

    def set_zoom_level(self, zoom_level):
        """
        Set image zoom level
        :param zoom_level: zoom level, which must be contained in self.zoom_levels
        :return:
        """
        if zoom_level not in self._plot_options['zoom_levels']:
            self._logger.error('Invalid zoom level specified: {:}'.format(zoom_level))
            self._logger.error('Please specify a zoom level from self.zoom_levels')
            return

        self._plot_parameters.update({'.zoom=': zoom_level})

    def set_trim_pixels(self, num_pixels):
        """
        Remove all whitespace at the bottom of the imager except for num_pixels pixels
        :param num_pixels: integer specifying the number of pixels to keep
        :return:
        """
        if not isinstance(num_pixels, int):
            self._logger.error('Number of pixels to trim must be an integer')
            return

        self._plot_parameters.update({'.trim=': str(num_pixels)})

    def add_constraint(self, variable, operator, value):

        if not self._dataset_id:
            self._logger.warning('No dataset_id specified.  Please specify a valid dataset_id via self.dataset_id '
                                 'before adding constraints')
            return

        if variable not in self.dataset_variables:
            self._logger.error('X variable {:} not found in data set: {:}'.format(variable, self._dataset_id))
            return

        if operator not in self.operators:
            self._logger.error(
                'Invalid operator specified: {:}. Select from available operators in self.operators'.format(operator))
            return

        constraint = '{:}{:}{:}'.format(variable, operator, value)
        self._logger.info('Adding constraint: {:}'.format(constraint))

        self._constraints['{:}{:}'.format(variable, operator)] = str(value)

    def remove_constraint(self, constraint):

        if constraint not in self._constraints:
            self._logger.warning('Constraint {:} has not been set'.format(constraint))
            return

        self._logger.info('Removing constraint: {:}'.format(constraint))
        constraint_value = self._constraints.pop(constraint)
        self._logger.info('Constraint {:}={:} removed'.format(constraint, constraint_value))

    def clear_constraints(self):
        """
        Clears the current plot constraints
        :return:
        """
        self._constraints = {}

    def reset_plot_parameters(self):
        """
        Reset the current plot parameters to the default setting
        :return:
        """
        self._plot_parameters = self._default_plot_parameters.copy()

    def build_image_request(self, x, y, c=None):
        """
        Build the image request url using the parameters in self.plot_parameters and optional constraints contained in
        self.constraints
        :param x: x-axis variable
        :param y: y-axis variable
        :param c: optional variable used to color markers by value
        :return: the ERDDAP MakeAGraph image url
        """

        self._image_url = None

        if not self._dataset_id:
            self._logger.warning('No dataset_id specified.  Please specify a valid dataset_id via self.dataset_id')
            return

        if x not in self.dataset_variables:
            self._logger.error('X variable {:} not found in data set: {:}'.format(x, self._dataset_id))
            return
        if y not in self.dataset_variables:
            self._logger.error('Y variable {:} not found in data set: {:}'.format(y, self._dataset_id))
            return

        variables = [x, y]
        if c:
            if c not in self.dataset_variables:
                self._logger.error('C variable {:} not found in data set: {:}'.format(c, self._dataset_id))
                return
            variables.append(c)

        self._build_plot_query_string()
        self._build_constraints_query_string()

        if self._constraints:
            url = '{:}/{:}/{:}.{:}?{:}&{:}&{:}'.format(self._e.server,
                                                       self._e.protocol,
                                                       self._dataset_id,
                                                       self._e.response,
                                                       ','.join(variables),
                                                       self._constraints_query,
                                                       self._plot_query)
        else:
            url = '{:}/{:}/{:}.{:}?{:}&{:}'.format(self._e.server,
                                                   self._e.protocol,
                                                   self._dataset_id,
                                                   self._e.response,
                                                   ','.join(variables),
                                                   self._plot_query)

        self._image_url = url
        self._logger.debug('Image url: {:}'.format(self._image_url))

        return self._image_url

    def download_image(self, image_name, clobber=False, show=False):
        """
        Send a prepared ERDDAP image request and write the resulting file to self._image_path as image_name
        :param image_name: Name of the file to write the image to
        :param clobber: True to overwrite an existing image file
        :param show: True to try and display the downloaded image. self.image_app must be set to a valid system image
            display utility.
        :return: True on success, False on failure
        """

        if not self._image_path:
            self._logger.error('No image path set')
            return

        if not os.path.isdir(self._image_path):
            self._logger.error('Invalid image path: {:}'.format(self._image_path))
            return

        if not self._image_url:
            self._logger.error('No image request URL found.')
            self._logger.error('Build the image request URL with self.build_image_request() prior to downloading.')
            return

        # Create the fully qualified path to the image to be written
        image_path = os.path.join(self._image_path, image_name)
        if os.path.isfile(image_path):
            if clobber:
                self._logger.warning('Clobbering existing image file: {:}'.format(image_path))
            else:
                self._logger.warning('Skipping existing image file: {:}'.format(image_path))
                return

        self._logger.debug('Sending request: {:}'.format(self._image_url))
        r = requests.get(self._image_url, stream=True)
        # Clear self._image_url
        self._image_url = None
        if r.status_code != 200:
            self._logger.error('{:} (code={:}'.format(r.reason, r.status_code))
            return
        self._logger.info('Writing image to {:}'.format(image_path))
        try:
            with open(image_path, 'wb') as f:
                for chunk in r.iter_content():
                    f.write(chunk)

                self._last_image = os.path.realpath(image_path)

                if show:
                    self.show()

                return self._last_image

        except (OSError, IOError) as e:
            logging.error('Image download error: {:}'.format(e))

    def show(self):
        """
        Try to display the most recently downloaded image using self.image_app, if set.
        :return:
        """

        if not self._image_app:
            self._logger.warning('No image viewer specified. Please set an valid image app via self.image_app')
            return

        if not self._last_image:
            self._logger.warning('No image to display')
            return

        result = subprocess.run([self._image_app, self._last_image], stdout=subprocess.PIPE)
        if result.returncode != 0:
            self._logger.error('Failed to open image {:}: {:}'.format(self._last_image, result.stderr))

    def search_datasets(self, target_string):
        """
        Search the data set IDS in self.datasets that contain target_string
        :param target_string: string or regular expression to search for
        :return: pandas data frame containing the data set metadata for all data set ids that contain target_string
        """

        return self._datasets[self._datasets.index.str.contains(target_string)]

    def get_dataset_description(self):
        """
        Fetch the data set metadata description (datasetID/info.csv) as a pandas DataFrame
        :return: pandas DataFrame
        """

        self._dataset_description = pd.DataFrame()

        if not self._dataset_id:
            self._logger.warning('No dataset_id specified')

        # Get the data set description csv response url
        desc_url = self._e.get_info_url(self._dataset_id, response='csv')

        self._logger.info('Fetching dataset {:} description'.format(self._dataset_id))

        metadata = pd.read_csv(desc_url)
        # Rename the columns to all lower case and replace spaces with underscores
        metadata.rename(columns={s: s.replace(' ', '_').lower() for s in metadata.columns.to_list()}, inplace=True)

        self._dataset_description = metadata

    def get_variable_attributes(self, variable):
        """
        Fetch the attributes of a variable as a pandas DataFrame
        :param variable: data set variable name
        :return: pandas DataFrame
        """
        if not self._dataset_id:
            self._logger.warning('No dataset_id specified')
            return pd.DataFrame()

        if variable not in self.dataset_variables:
            self._logger.warning('Variable {:} not found in dataset {:}'.format(variable, self._dataset_id))
            return pd.DataFrame()

        return self._dataset_description[(self._dataset_description['variable_name'] == variable) & (
                self._dataset_description['row_type'] == 'attribute')]

    def _build_plot_query_string(self):

        self._plot_query = '&'.join(['{:}{:}'.format(k, quote(v)) for k, v in self._plot_parameters.items()])

    def _build_constraints_query_string(self):

        self._constraints_query = '&'.join([quote('{:}{:}'.format(k, v)) for k, v in self._constraints.items()])

    def _fetch_datasets(self):

        try:

            self._logger.info('Fetching available server datasets: {:}'.format(self._e.server))
            url = self._e.get_download_url(dataset_id='allDatasets', response='csv')
            self._last_request = url

            self._logger.debug('Server info: {:}'.format(self._last_request))
            self._datasets = pd.read_csv(url, parse_dates=['minTime', 'maxTime'], skiprows=[1]).set_index('datasetID')

            # Remove useless columns for tabledap datasets
            self._datasets = self._datasets.drop(columns=['griddap', 'wms'])

            self._num_datasets = self._datasets.shape[0]

        except requests.exceptions.HTTPError as e:
            self._logger.error(
                'Failed to fetch/parse ERDDAP server datasets info: {:} ({:})'.format(self._last_request, e))
            return

    def __repr__(self):
        return '<TabledapPlotter(server={:}, image_type={:}, dataset_id={:}, num_datasets={:})>'.format(self._e.server,
                                                                                                        self._e.response,
                                                                                                        self._dataset_id,
                                                                                                        self._num_datasets)
