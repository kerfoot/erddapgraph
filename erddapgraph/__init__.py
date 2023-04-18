import os
import logging
import yaml

logging.getLogger(__file__)


def load_plot_options(yaml_options_file=None):
    """
    Load the default ERDDAP Make A Graph plotting options from yaml_options_file
    :param yaml_options_file: YAML file containing the plotting options
    :return: dictionary
    """

    yaml_options_file = yaml_options_file or os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'config', 'tabledap-options.yml'))

    if not os.path.isfile(yaml_options_file):
        logging.error('Plotting options file not found: {:}'.format(yaml_options_file))
        return

    plotting_options = None
    try:
        with open(yaml_options_file, 'r') as fid:
            plotting_options = yaml.safe_load(fid)
    except Exception as e:
        logging.error('Options file load error: {:} ({:})'.format(yaml_options_file, e))
        return

    plotting_options['options_file'] = yaml_options_file

    return plotting_options


plot_options = load_plot_options()
