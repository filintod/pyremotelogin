import collections
import json
import logging
import os
import yaml
from .vars import _resolve_variables, _replace_variables_in_settings

log = logging.getLogger(__name__)

environment_settings = {}
registered_settings = {}
cli_settings = {}


def parse_config(default_config_path=None, environment_var=None, environment_settings_config=False,
                 load_test_envi_key_as_environment=True):
    """ loads yaml config file and return dictionary with parameters parsed.
        If config data has a key called "run_envi" and load_test_envi_key_as_environment is True
        then we will also update run_envi global environment_settings data

    Args:
        environment_var (str): environment variable name to use as path to config file to substitute default. This
                               takes precedence over default_config_path
        default_config_path (str): filepath of default settings file. it should be located on same folder as
                                        module __file__ calling this function
        environment_settings_config (bool): flag to indicate that this data is to set the default run_envi configuration
        load_test_envi_key_as_environment (bool): flag to indicate that if run_envi is found set it as global environment
                                                  variable environment_settings

    Returns:
        dict

    """
    if not environment_var and not default_config_path:
        return

    if environment_var and os.environ.get(environment_var, None):
        test_envi_settings_path = os.environ.get(environment_var)
        found = 'environment variable {} with value'.format(environment_var)

    elif default_config_path:
        test_envi_settings_path = default_config_path
        found = 'file path '

    else:
        return

    found += test_envi_settings_path

    _, ext = os.path.splitext(test_envi_settings_path)
    loader = _get_settings_loaded_and_check_settings_exists(ext, found, test_envi_settings_path)

    with open(test_envi_settings_path) as f:
        new_environment_settings = loader(f)
        variables = _resolve_variables(new_environment_settings.pop('vars', {}))
        _replace_variables_in_settings(new_environment_settings, variables)

    new_environment_settings.pop('vars', None)

    global environment_settings

    if environment_settings_config:
        environment_settings.update(new_environment_settings)
        ret = environment_settings
    else:
        if 'run_envi' in new_environment_settings and load_test_envi_key_as_environment:
            environment_settings.update(new_environment_settings.pop('run_envi'))
        ret = new_environment_settings

    for section, values in registered_settings.items():
        update_settings_with_user_settings(values['local_vars'], section, paths_vars=values['paths_vars'])
        if values['after_update']:
            values['after_update']()

    return ret


def _get_settings_loaded_and_check_settings_exists(ext, found, test_envi_settings_path):
    if ext == '.json':
        loader = json.load
    elif ext in ('.yaml', '.yml'):
        loader = yaml.load
    else:
        raise ValueError("This settings file ({}) has an extension that we don't know how to parse.\n"
                         "The only extensions we can handle are (.json, .yaml and .yml"
                         "".format(test_envi_settings_path))
    if not os.path.exists(test_envi_settings_path):
        print('#' * 80)
        print('The settings file defined in ({}) was not found.'.format(found))
        print('#' * 80)
        raise Exception('Problems finding settings file')
    return loader


def load_config(config_file_path):
    return parse_config(config_file_path, environment_settings_config=True)


def load_default():
    return parse_config(environment_var='TEST_ENVI_SETTINGS', environment_settings_config=True)


def update_settings_with_user_settings(local_vars, section, settings=None, paths_vars=()):
    """ updates run_envi default settings with environment settings given by user
        the keys are case independent to allow the settings file to be written as lower case but still set the proper
        key in the settings.py file that is calling this method

    Args:
        local_vars (dict): dictionary from locals() from file calling this method
        section (str): section to apply config values from in the yaml file.
        settings (dict): if given we would use this settings as the default ones instead of the environment settings
        paths_vars (list): list of variables that are a file/dir path and that we want to normalize to avoid issues
                           with back/forward slashes on windows/unix systems

    Returns:

    """
    settings = settings or environment_settings
    settings_section = settings.get(section, {})

    if settings_section:

        settings_section_keys_lower = [k.lower() for k in settings_section.keys()]
        local_vars_lower = {l.lower(): l for l in local_vars}

        # settings take precendence over OS environment variable
        # augment settings with OS environment variables if settings does not already include a key for that variable
        if 'ENV_TO_VARS' in local_vars and local_vars['ENV_TO_VARS']:
            env_vars_lower = {e.lower(): e for e in local_vars['ENV_TO_VARS']}
            for v in (e for e in env_vars_lower if e not in settings_section_keys_lower
                                                   and os.environ.get(local_vars['ENV_TO_VARS'])):
                settings_section[local_vars[env_vars_lower[v]]] = os.environ.get(local_vars['ENV_TO_VARS'])

        for key, value in [(k, v) for (k, v) in settings_section.items() if k.lower() in local_vars_lower]:
            key = local_vars_lower[key.lower()]
            local_vars[key] = value
            if value and paths_vars and key in paths_vars:
                local_vars[key] = os.path.normpath(value)


def register_settings(settings_vars, section, paths_vars=(), after_update=None):
    """ register a settings module into the config registered_settings so if there is any update after we
        can update those settings

        Args:
            settings_vars: the globals() of the settings module calling this function
            section: a namespace defined in the yaml file that will link the parameters in the yaml file to the settings_vars
            paths_vars: a list of variables that are paths so we can reformat them depending on the runtime environment
            after_update: a function that would get called after any update of settings in case we need to update

    """
    update_settings_with_user_settings(settings_vars, section, paths_vars=paths_vars)

    registered_settings[section] = dict(local_vars=settings_vars,  # locals() from the file calling this
                                        paths_vars=paths_vars,  # what variables from locals() are paths to check
                                        after_update=after_update  # function to call if there is any update to settings
                                        )


def get_file_to_open(config_folder, f):
    """ from a filename it tries to find the yaml file if the extension is not provided """
    if not os.path.isabs(f):
        f = os.path.join(config_folder, f)

    path, ext = os.path.splitext(f)
    if not ext:
        try:
            ext = next(ext for ext in (".yaml", ".yml") if os.path.exists(f + ext))
        except StopIteration:
            raise FileNotFoundError(f)
    return f + ext


# TODO: include toml/json file as config file
def parse_yaml(config_file_path, base_name='bases', safe=False, replace_list=True):
    """     recursively retrieves configuration from yaml files

    Args:
        config_file_path: starting yaml config file
        base_name: attribute name to use to find parents
        safe: use yaml.safe_load
        replace_list: if True values that are list are replace if false, values are appended if missing

    Returns:

    """
    config_folder, config_file = os.path.split(config_file_path)

    loader = yaml.safe_load if safe else yaml.load

    def deep_update(source, overrides):
        """Update a nested dictionary or similar mapping.

        Modify ``source`` in place.
        """
        for key, value in overrides.items():
            if value and isinstance(value, collections.Mapping):
                source[key] = deep_update(source.get(key, {}), value)
            elif not replace_list and value and isinstance(value, collections.MutableSequence):
                if key not in source:
                    source[key] = []
                deletions = []
                for v in value:
                    if v.startswith('-'):
                        deletions.append(v[1:])
                    elif v not in source[key]:
                        source[key].append(v)
                source[key] = [s for s in source[key] if s not in deletions]
            else:
                source[key] = value
        return source

    def load_yaml(path):
        with open(path) as f:
            yfile = f.read()

        problems = get_yaml_syntax_error(yfile)
        if problems:
            msg = ('\n' + '#' * 80 + '\n\nYour YAML configuration file {} has problems: \n\n'.format(config_file_path) +
                  problems)
            raise Exception(msg)

        return loader(yfile)

    cfg = load_yaml(config_file_path)

    visited_parents = []
    parents = cfg.pop(base_name, [])

    while parents:
        new_parents = []
        visited_parents.extend(parents)
        for parent in parents:
            parent_config = load_yaml(get_file_to_open(config_folder, parent))
            new_parents.extend(p for p in parent_config.pop(base_name, []) if p not in visited_parents)
            cfg = deep_update(parent_config, cfg)
        parents = new_parents

    return cfg


def get_yaml_syntax_error(buffer):
    try:
        list(yaml.parse(buffer, Loader=yaml.BaseLoader))
    except yaml.error.MarkedYAMLError as e:
        return str(e)

    return ""


def copy_yaml_file_without_keys(filename, yaml_data, *keys):
    """ remove information about specified keys like passwords when copying the config file """
    import copy
    yaml_data = copy.deepcopy(yaml_data)

    def get_parent_child(k):
        *parts, child = k.split('.')
        parent = yaml_data
        for p in parts:
            parent = parent.get(p, None)
            if parent is None:
                break
        return parent if parent is not yaml_data else None, child

    with open(filename, 'w') as f:
        for k in keys:
            parent, child = get_parent_child(k)
            if parent and child in parent:
                to_change = parent
            elif parent is None and child in yaml_data:
                to_change = yaml_data
            else:
                continue
            to_change[child] = 'your <{}>'.format(child)

        yaml.dump(yaml_data, f, default_flow_style=False)
