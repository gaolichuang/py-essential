# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Red Hat, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

r"""
Configuration options which may be set on the command line or in config files.

The schema for each option is defined using the Opt sub-classes, e.g.:

::

    common_opts = [
        cfg.StrOpt('bind_host',
                   default='0.0.0.0',
                   help='IP address to listen on'),
        cfg.IntOpt('bind_port',
                   default=9292,
                   help='Port number to listen on')
    ]

Options can be strings, integers, floats, booleans, lists, or 'multi strings'
or 'key/value pairs' (dictionary) ::

    enabled_apis_opt = cfg.ListOpt('enabled_apis',
                                   default=['ec2', 'osapi_compute'],
                                   help='List of APIs to enable by default')

    DEFAULT_EXTENSIONS = [
        'nova.api.openstack.compute.contrib.standard_extensions'
    ]
    osapi_compute_extension_opt = cfg.MultiStrOpt('osapi_compute_extension',
                                                  default=DEFAULT_EXTENSIONS)

Option schemas are registered with the config manager at runtime, but before
the option is referenced::

    class ExtensionManager(object):

        enabled_apis_opt = cfg.ListOpt(...)

        def __init__(self, conf):
            self.conf = conf
            self.conf.register_opt(enabled_apis_opt)
            ...

        def _load_extensions(self):
            for ext_factory in self.conf.osapi_compute_extension:
                ....

A common usage pattern is for each option schema to be defined in the module or
class which uses the option::

    opts = ...

    def add_common_opts(conf):
        conf.register_opts(opts)

    def get_bind_host(conf):
        return conf.bind_host

    def get_bind_port(conf):
        return conf.bind_port

An option may optionally be made available via the command line. Such options
must be registered with the config manager before the command line is parsed
(for the purposes of --help and CLI arg validation)::

    cli_opts = [
        cfg.BoolOpt('verbose',
                    short='v',
                    default=False,
                    help='Print more verbose output'),
        cfg.BoolOpt('debug',
                    short='d',
                    default=False,
                    help='Print debugging output'),
    ]

    def add_common_opts(conf):
        conf.register_cli_opts(cli_opts)

The config manager has two CLI options defined by default, --config-file
and --config-dir::

    class ConfigOpts(object):

        def __call__(self, ...):

            opts = [
                MultiStrOpt('config-file',
                        ...),
                StrOpt('config-dir',
                       ...),
            ]

            self.register_cli_opts(opts)

Option values are parsed from any supplied config files using
essential.config.iniparser. If none are specified, a default set is used
e.g. glance-api.conf and glance-common.conf::

    glance-api.conf:
      [DEFAULT]
      bind_port = 9292

    glance-common.conf:
      [DEFAULT]
      bind_host = 0.0.0.0

Option values in config files override those on the command line. Config files
are parsed in order, with values in later files overriding those in earlier
files.

The parsing of CLI args and config files is initiated by invoking the config
manager e.g.::

    conf = ConfigOpts()
    conf.register_opt(BoolOpt('verbose', ...))
    conf(sys.argv[1:])
    if conf.verbose:
        ...

Options can be registered as belonging to a group::

    rabbit_group = cfg.OptGroup(name='rabbit',
                                title='RabbitMQ options')

    rabbit_host_opt = cfg.StrOpt('host',
                                 default='localhost',
                                 help='IP/hostname to listen on'),
    rabbit_port_opt = cfg.IntOpt('port',
                                 default=5672,
                                 help='Port number to listen on')

    def register_rabbit_opts(conf):
        conf.register_group(rabbit_group)
        # options can be registered under a group in either of these ways:
        conf.register_opt(rabbit_host_opt, group=rabbit_group)
        conf.register_opt(rabbit_port_opt, group='rabbit')

If no group attributes are required other than the group name, the group
need not be explicitly registered e.g.

    def register_rabbit_opts(conf):
        # The group will automatically be created, equivalent calling::
        #   conf.register_group(OptGroup(name='rabbit'))
        conf.register_opt(rabbit_port_opt, group='rabbit')

If no group is specified, options belong to the 'DEFAULT' section of config
files::

    glance-api.conf:
      [DEFAULT]
      bind_port = 9292
      ...

      [rabbit]
      host = localhost
      port = 5672
      use_ssl = False
      userid = guest
      password = guest
      virtual_host = /

Command-line options in a group are automatically prefixed with the
group name::

    --rabbit-host localhost --rabbit-port 9999

Option values in the default group are referenced as attributes/properties on
the config manager; groups are also attributes on the config manager, with
attributes for each of the options associated with the group::

    server.start(app, conf.bind_port, conf.bind_host, conf)

    self.connection = kombu.connection.BrokerConnection(
        hostname=conf.rabbit.host,
        port=conf.rabbit.port,
        ...)

Option values may reference other values using PEP 292 string substitution::

    opts = [
        cfg.StrOpt('state_path',
                   default=os.path.join(os.path.dirname(__file__), '../'),
                   help='Top-level directory for maintaining nova state'),
        cfg.StrOpt('sqlite_db',
                   default='nova.sqlite',
                   help='file name for sqlite'),
        cfg.StrOpt('sql_connection',
                   default='sqlite:///$state_path/$sqlite_db',
                   help='connection string for sql database'),
    ]

Note that interpolation can be avoided by using '$$'.

Options may be declared as required so that an error is raised if the user
does not supply a value for the option.

Options may be declared as secret so that their values are not leaked into
log files::

     opts = [
        cfg.StrOpt('s3_store_access_key', secret=True),
        cfg.StrOpt('s3_store_secret_key', secret=True),
        ...
     ]

This module also contains a global instance of the ConfigOpts class
in order to support a common usage pattern in OpenStack::

    from essential.config import cfg

    opts = [
        cfg.StrOpt('bind_host', default='0.0.0.0'),
        cfg.IntOpt('bind_port', default=9292),
    ]

    CONF = cfg.CONF
    CONF.register_opts(opts)

    def start(server, app):
        server.start(app, CONF.bind_port, CONF.bind_host)

Positional command line arguments are supported via a 'positional' Opt
constructor argument::

    >>> conf = ConfigOpts()
    >>> conf.register_cli_opt(MultiStrOpt('bar', positional=True))
    True
    >>> conf(['a', 'b'])
    >>> conf.bar
    ['a', 'b']

It is also possible to use argparse "sub-parsers" to parse additional
command line arguments using the SubCommandOpt class:

    >>> def add_parsers(subparsers):
    ...     list_action = subparsers.add_parser('list')
    ...     list_action.add_argument('id')
    ...
    >>> conf = ConfigOpts()
    >>> conf.register_cli_opt(SubCommandOpt('action', handler=add_parsers))
    True
    >>> conf(args=['list', '10'])
    >>> conf.action.name, conf.action.id
    ('list', '10')

"""

import argparse
import collections
import copy
import functools
import glob
import itertools
import os
import six
import string
import sys

from essential.config import iniparser
from six import moves


class Error(Exception):
    """Base class for cfg exceptions."""

    def __init__(self, msg=None):
        self.msg = msg

    def __str__(self):
        return self.msg


class ArgsAlreadyParsedError(Error):
    """Raised if a CLI opt is registered after parsing."""

    def __str__(self):
        ret = "arguments already parsed"
        if self.msg:
            ret += ": " + self.msg
        return ret


class NoSuchOptError(Error, AttributeError):
    """Raised if an opt which doesn't exist is referenced."""

    def __init__(self, opt_name, group=None):
        self.opt_name = opt_name
        self.group = group

    def __str__(self):
        if self.group is None:
            return "no such option: %s" % self.opt_name
        else:
            return "no such option in group %s: %s" % (self.group.name,
                                                       self.opt_name)


class NoSuchGroupError(Error):
    """Raised if a group which doesn't exist is referenced."""

    def __init__(self, group_name):
        self.group_name = group_name

    def __str__(self):
        return "no such group: %s" % self.group_name


class DuplicateOptError(Error):
    """Raised if multiple opts with the same name are registered."""

    def __init__(self, opt_name):
        self.opt_name = opt_name

    def __str__(self):
        return "duplicate option: %s" % self.opt_name


class RequiredOptError(Error):
    """Raised if an option is required but no value is supplied by the user."""

    def __init__(self, opt_name, group=None):
        self.opt_name = opt_name
        self.group = group

    def __str__(self):
        if self.group is None:
            return "value required for option: %s" % self.opt_name
        else:
            return "value required for option: %s.%s" % (self.group.name,
                                                         self.opt_name)


class TemplateSubstitutionError(Error):
    """Raised if an error occurs substituting a variable in an opt value."""

    def __str__(self):
        return "template substitution error: %s" % self.msg


class ConfigFilesNotFoundError(Error):
    """Raised if one or more config files are not found."""

    def __init__(self, config_files):
        self.config_files = config_files

    def __str__(self):
        return ('Failed to read some config files: %s' %
                string.join(self.config_files, ','))


class ConfigFileParseError(Error):
    """Raised if there is an error parsing a config file."""

    def __init__(self, config_file, msg):
        self.config_file = config_file
        self.msg = msg

    def __str__(self):
        return 'Failed to parse %s: %s' % (self.config_file, self.msg)


class ConfigFileValueError(Error):
    """Raised if a config file value does not match its opt type."""
    pass


def _fixpath(p):
    """Apply tilde expansion and absolutization to a path."""
    return os.path.abspath(os.path.expanduser(p))


def _get_config_dirs(project=None):
    """Return a list of directors where config files may be located.

    :param project: an optional project name

    If a project is specified, following directories are returned::

      ~/.${project}/
      ~/
      /etc/${project}/
      /etc/

    Otherwise, these directories::

      ~/
      /etc/
    """
    cfg_dirs = [
        _fixpath(os.path.join('~', '.' + project)) if project else None,
        _fixpath('~'),
        os.path.join('/etc', project) if project else None,
        '/etc'
    ]

    return list(moves.filter(bool, cfg_dirs))


def _search_dirs(dirs, basename, extension=""):
    """Search a list of directories for a given filename.

    Iterator over the supplied directories, returning the first file
    found with the supplied name and extension.

    :param dirs: a list of directories
    :param basename: the filename, e.g. 'glance-api'
    :param extension: the file extension, e.g. '.conf'
    :returns: the path to a matching file, or None
    """
    for d in dirs:
        path = os.path.join(d, '%s%s' % (basename, extension))
        if os.path.exists(path):
            return path


def find_config_files(project=None, prog=None, extension='.conf'):
    """Return a list of default configuration files.

    :param project: an optional project name
    :param prog: the program name, defaulting to the basename of sys.argv[0]
    :param extension: the type of the config file

    We default to two config files: [${project}.conf, ${prog}.conf]

    And we look for those config files in the following directories::

      ~/.${project}/
      ~/
      /etc/${project}/
      /etc/

    We return an absolute path for (at most) one of each the default config
    files, for the topmost directory it exists in.

    For example, if project=foo, prog=bar and /etc/foo/foo.conf, /etc/bar.conf
    and ~/.foo/bar.conf all exist, then we return ['/etc/foo/foo.conf',
    '~/.foo/bar.conf']

    If no project name is supplied, we only look for ${prog.conf}.
    """
    if prog is None:
        prog = os.path.basename(sys.argv[0])

    cfg_dirs = _get_config_dirs(project)

    config_files = []
    if project:
        config_files.append(_search_dirs(cfg_dirs, project, extension))
    config_files.append(_search_dirs(cfg_dirs, prog, extension))

    return list(moves.filter(bool, config_files))


def _is_opt_registered(opts, opt):
    """Check whether an opt with the same name is already registered.

    The same opt may be registered multiple times, with only the first
    registration having any effect. However, it is an error to attempt
    to register a different opt with the same name.

    :param opts: the set of opts already registered
    :param opt: the opt to be registered
    :returns: True if the opt was previously registered, False otherwise
    :raises: DuplicateOptError if a naming conflict is detected
    """
    if opt.dest in opts:
        if opts[opt.dest]['opt'] != opt:
            raise DuplicateOptError(opt.name)
        return True
    else:
        return False


def set_defaults(opts, **kwargs):
    for opt in opts:
        if opt.dest in kwargs:
            opt.default = kwargs[opt.dest]


def _normalize_group_name(group_name):
    if group_name == 'DEFAULT':
        return group_name
    return group_name.lower()


class Opt(object):

    """Base class for all configuration options.

    An Opt object has no public methods, but has a number of public string
    properties:

      name:
        the name of the option, which may include hyphens
      dest:
        the (hyphen-less) ConfigOpts property which contains the option value
      short:
        a single character CLI option name
      default:
        the default value of the option
      positional:
        True if the option is a positional CLI argument
      metavar:
        the name shown as the argument to a CLI option in --help output
      help:
        an string explaining how the options value is used
    """
    multi = False
    _convert_value = None

    def __init__(self, name, dest=None, short=None, default=None,
                 positional=False, metavar=None, help=None,
                 secret=False, required=False,
                 deprecated_name=None, deprecated_group=None,
                 deprecated_opts=None):
        """Construct an Opt object.

        The only required parameter is the option's name. However, it is
        common to also supply a default and help string for all options.

        :param name: the option's name
        :param dest: the name of the corresponding ConfigOpts property
        :param short: a single character CLI option name
        :param default: the default value of the option
        :param positional: True if the option is a positional CLI argument
        :param metavar: the option argument to show in --help
        :param help: an explanation of how the option is used
        :param secret: true iff the value should be obfuscated in log output
        :param required: true iff a value must be supplied for this option
        :param deprecated_name: deprecated name option.  Acts like an alias
        :param deprecated_group: the group containing a deprecated alias
        :param deprecated_opts: array of DeprecatedOpt(s)
        """
        self.name = name
        if dest is None:
            self.dest = self.name.replace('-', '_')
        else:
            self.dest = dest
        self.short = short
        self.default = default
        self.positional = positional
        self.metavar = metavar
        self.help = help
        self.secret = secret
        self.required = required
        if deprecated_name is not None:
            deprecated_name = deprecated_name.replace('-', '_')

        self.deprecated_opts = copy.deepcopy(deprecated_opts) or []
        self.deprecated_opts.append(DeprecatedOpt(deprecated_name,
                                                  group=deprecated_group))

    def __ne__(self, another):
        return vars(self) != vars(another)

    def _get_from_namespace(self, namespace, group_name):
        """Retrieves the option value from a _Namespace object.

        :param namespace: a _Namespace object
        :param group_name: a group name
        """
        names = [(group_name, self.dest)]

        for opt in self.deprecated_opts:
            dname, dgroup = opt.name, opt.group
            if dname or dgroup:
                names.append((dgroup if dgroup else group_name,
                              dname if dname else self.dest))

        return namespace._get_value(names,
                                    self.multi, self.positional,
                                    self._convert_value)

    def _add_to_cli(self, parser, group=None):
        """Makes the option available in the command line interface.

        This is the method ConfigOpts uses to add the opt to the CLI interface
        as appropriate for the opt type. Some opt types may extend this method,
        others may just extend the helper methods it uses.

        :param parser: the CLI option parser
        :param group: an optional OptGroup object
        """
        container = self._get_argparse_container(parser, group)
        kwargs = self._get_argparse_kwargs(group)
        prefix = self._get_argparse_prefix('', group.name if group else None)
        for opt in self.deprecated_opts:
            deprecated_name = self._get_deprecated_cli_name(opt.name,
                                                            opt.group)
            self._add_to_argparse(parser, container, self.name, self.short,
                                  kwargs, prefix,
                                  self.positional, deprecated_name)

    def _add_to_argparse(self, parser, container, name, short, kwargs,
                         prefix='', positional=False, deprecated_name=None):
        """Add an option to an argparse parser or group.

        :param container: an argparse._ArgumentGroup object
        :param name: the opt name
        :param short: the short opt name
        :param kwargs: the keyword arguments for add_argument()
        :param prefix: an optional prefix to prepend to the opt name
        :param position: whether the optional is a positional CLI argument
        """
        def hyphen(arg):
            return arg if not positional else ''

        args = [hyphen('--') + prefix + name]
        if short:
            args.append(hyphen('-') + short)
        if deprecated_name:
            args.append(hyphen('--') + deprecated_name)

        parser.add_parser_argument(container, *args, **kwargs)

    def _get_argparse_container(self, parser, group):
        """Returns an argparse._ArgumentGroup.

        :param parser: an argparse.ArgumentParser
        :param group: an (optional) OptGroup object
        :returns: an argparse._ArgumentGroup if group is given, else parser
        """
        if group is not None:
            return group._get_argparse_group(parser)
        else:
            return parser

    def _get_argparse_kwargs(self, group, **kwargs):
        """Build a dict of keyword arguments for argparse's add_argument().

        Most opt types extend this method to customize the behaviour of the
        options added to argparse.

        :param group: an optional group
        :param kwargs: optional keyword arguments to add to
        :returns: a dict of keyword arguments
        """
        if not self.positional:
            dest = self.dest
            if group is not None:
                dest = group.name + '_' + dest
            kwargs['dest'] = dest
        else:
            kwargs['nargs'] = '?'
        kwargs.update({'default': None,
                       'metavar': self.metavar,
                       'help': self.help, })
        return kwargs

    def _get_argparse_prefix(self, prefix, group_name):
        """Build a prefix for the CLI option name, if required.

        CLI options in a group are prefixed with the group's name in order
        to avoid conflicts between similarly named options in different
        groups.

        :param prefix: an existing prefix to append to (e.g. 'no' or '')
        :param group_name: an optional group name
        :returns: a CLI option prefix including the group name, if appropriate
        """
        if group_name is not None:
            return group_name + '-' + prefix
        else:
            return prefix

    def _get_deprecated_cli_name(self, dname, dgroup, prefix=''):
        """Build a CLi arg name for deprecated options.

        Either a deprecated name or a deprecated group or both or
        neither can be supplied:

          dname, dgroup -> dgroup + '-' + dname
          dname         -> dname
          dgroup        -> dgroup + '-' + self.name
          neither        -> None

        :param dname: a deprecated name, which can be None
        :param dgroup: a deprecated group, which can be None
        :param prefix: an prefix to append to (e.g. 'no' or '')
        :returns: a CLI argument name
        """
        if dgroup == 'DEFAULT':
            dgroup = None

        if dname is None and dgroup is None:
            return None

        if dname is None:
            dname = self.name

        return self._get_argparse_prefix(prefix, dgroup) + dname


class DeprecatedOpt(object):

    """Represents a Deprecated option. Here's how you can use it

        oldopts = [cfg.DeprecatedOpt('oldfoo', group='oldgroup'),
                   cfg.DeprecatedOpt('oldfoo2', group='oldgroup2')]
        cfg.CONF.register_group(cfg.OptGroup('blaa'))
        cfg.CONF.register_opt(cfg.StrOpt('foo', deprecated_opts=oldopts),
                               group='blaa')
    """

    def __init__(self, name, group=None):
        """Constructs an DeprecatedOpt object.

        :param name: the name of the option
        :param group: the group of the option
        """
        self.name = name
        self.group = group

    def __key(self):
        return (self.name, self.group)

    def __eq__(x, y):
        return x.__key() == y.__key()

    def __hash__(self):
        return hash(self.__key())


class StrOpt(Opt):
    """String options.

    String opts do not have their values transformed and are returned as
    str objects.

    In addition to the parameters in the base class Opt, StrOpt has an
    additional parameter.

    :param choices: Optional sequence of valid values.
    """

    def __init__(self, name, choices=None, **kwargs):
        self.choices = choices
        super(StrOpt, self).__init__(name, **kwargs)

    def _get_argparse_kwargs(self, group, **kwargs):
        """Extends the base argparse keyword dict for choices handling."""
        return super(StrOpt, self)._get_argparse_kwargs(group,
                                                        choices=self.choices,
                                                        **kwargs)

    def _convert_value(self, value):
        """Validate a value, no actual conversion required."""
        if self.choices and value not in self.choices:
            message = ('Invalid value: %r (choose from %s)' %
                       (value, ', '.join(map(repr, self.choices))))
            raise ValueError(message)
        return value


class BoolOpt(Opt):

    """Boolean options.

    Bool opts are set to True or False on the command line using --optname or
    --noopttname respectively.

    In config files, boolean values are case insensitive and can be set using
    1/0, yes/no, true/false or on/off.
    """

    _boolean_states = {'1': True, 'yes': True, 'true': True, 'on': True,
                       '0': False, 'no': False, 'false': False, 'off': False}

    def __init__(self, *args, **kwargs):
        if 'positional' in kwargs:
            raise ValueError('positional boolean args not supported')
        super(BoolOpt, self).__init__(*args, **kwargs)

    @staticmethod
    def _convert_value(value):
        """Convert a string value to a bool."""
        ret = BoolOpt._boolean_states.get(value.lower())
        if ret is None:
            raise ValueError('Unexpected boolean value %r' % value)
        return ret

    def _add_to_cli(self, parser, group=None):
        """Extends the base class method to add the --nooptname option."""
        super(BoolOpt, self)._add_to_cli(parser, group)
        self._add_inverse_to_argparse(parser, group)

    def _add_inverse_to_argparse(self, parser, group):
        """Add the --nooptname option to the option parser."""
        container = self._get_argparse_container(parser, group)
        kwargs = self._get_argparse_kwargs(group, action='store_false')
        prefix = self._get_argparse_prefix('no', group.name if group else None)
        for opt in self.deprecated_opts:
            deprecated_name = self._get_deprecated_cli_name(opt.name,
                                                            opt.group,
                                                            prefix='no')
            kwargs["help"] = "The inverse of --" + self.name
            self._add_to_argparse(parser, container, self.name, None, kwargs,
                                  prefix, self.positional, deprecated_name)

    def _get_argparse_kwargs(self, group, action='store_true', **kwargs):
        """Extends the base argparse keyword dict for boolean options."""

        kwargs = super(BoolOpt, self)._get_argparse_kwargs(group, **kwargs)

        # metavar has no effect for BoolOpt
        if 'metavar' in kwargs:
            del kwargs['metavar']

        kwargs['action'] = action

        return kwargs


class IntOpt(Opt):

    """Int opt values are converted to integers using the int() builtin."""

    _convert_value = int

    def _get_argparse_kwargs(self, group, **kwargs):
        """Extends the base argparse keyword dict for integer options."""
        return super(IntOpt,
                     self)._get_argparse_kwargs(group, type=int, **kwargs)


class FloatOpt(Opt):

    """Float opt values are converted to floats using the float() builtin."""

    _convert_value = float

    def _get_argparse_kwargs(self, group, **kwargs):
        """Extends the base argparse keyword dict for float options."""
        return super(FloatOpt, self)._get_argparse_kwargs(group,
                                                          type=float, **kwargs)


class ListOpt(Opt):

    """List Options.

    List opt values are simple string values separated by commas. The opt value
    is a list containing these strings.
    """

    @staticmethod
    def _convert_value(value):
        """Convert a string value to a list."""
        return [a.strip() for a in value.split(',')]

    class _StoreListAction(argparse.Action):
        """An argparse action for parsing an option value into a list."""
        def __call__(self, parser, namespace, values, option_string=None):
            if values is not None:
                values = ListOpt._convert_value(values)
            setattr(namespace, self.dest, values)

    def _get_argparse_kwargs(self, group, **kwargs):
        """Extends the base argparse keyword dict for list options."""
        return Opt._get_argparse_kwargs(self,
                                        group,
                                        action=ListOpt._StoreListAction,
                                        **kwargs)


class DictOpt(Opt):

    """Dictionary options.

    Dictionary opt values are key:value pairs separated by commas. The opt
    value is a dictionary of these key/value pairs
    """

    @staticmethod
    def _convert_value(value):
        """Split a line.

        Split a value into key/value pairs separated by commas, then split
        the each into key and value using colons as separator and then
        stuff the key/value (s) into a dictionary
        """
        return dict([[a.strip() for a in v.split(':')]
                    for v in value.split(',')])

    class _StoreDictAction(argparse.Action):
        """An argparse action for parsing an option value into a dictionary."""
        def __call__(self, parser, namespace, values, option_string=None):
            if values is not None:
                values = DictOpt._convert_value(values)
            setattr(namespace, self.dest, values)

    def _get_argparse_kwargs(self, group, **kwargs):
        """Extends the base argparse keyword dict for dictionary options."""
        return Opt._get_argparse_kwargs(self,
                                        group,
                                        action=DictOpt._StoreDictAction,
                                        **kwargs)


class MultiStrOpt(Opt):

    """Multi-string option.

    Multistr opt values are string opts which may be specified multiple times.
    The opt value is a list containing all the string values specified.
    """
    multi = True

    def _get_argparse_kwargs(self, group, **kwargs):
        """Extends the base argparse keyword dict for multi str options."""
        kwargs = super(MultiStrOpt, self)._get_argparse_kwargs(group)
        if not self.positional:
            kwargs['action'] = 'append'
        else:
            kwargs['nargs'] = '*'
        return kwargs


class SubCommandOpt(Opt):

    """Sub-command options.

    Sub-command options allow argparse sub-parsers to be used to parse
    additional command line arguments.

    The handler argument to the SubCommandOpt contructor is a callable
    which is supplied an argparse subparsers object. Use this handler
    callable to add sub-parsers.

    The opt value is SubCommandAttr object with the name of the chosen
    sub-parser stored in the 'name' attribute and the values of other
    sub-parser arguments available as additional attributes.
    """

    def __init__(self, name, dest=None, handler=None,
                 title=None, description=None, help=None):
        """Construct an sub-command parsing option.

        This behaves similarly to other Opt sub-classes but adds a
        'handler' argument. The handler is a callable which is supplied
        an subparsers object when invoked. The add_parser() method on
        this subparsers object can be used to register parsers for
        sub-commands.

        :param name: the option's name
        :param dest: the name of the corresponding ConfigOpts property
        :param title: title of the sub-commands group in help output
        :param description: description of the group in help output
        :param help: a help string giving an overview of available sub-commands
        """
        super(SubCommandOpt, self).__init__(name, dest=dest, help=help)
        self.handler = handler
        self.title = title
        self.description = description

    def _add_to_cli(self, parser, group=None):
        """Add argparse sub-parsers and invoke the handler method."""
        dest = self.dest
        if group is not None:
            dest = group.name + '_' + dest

        subparsers = parser.add_subparsers(dest=dest,
                                           title=self.title,
                                           description=self.description,
                                           help=self.help)

        if self.handler is not None:
            self.handler(subparsers)


class _ConfigFileOpt(Opt):

    """The --config-file option.

    This is an private option type which handles the special processing
    required for --config-file options.

    As each --config-file option is encountered on the command line, we
    parse the file and store the parsed values in the _Namespace object.
    This allows us to properly handle the precedence of --config-file
    options over previous command line arguments, but not over subsequent
    arguments.
    """

    class ConfigFileAction(argparse.Action):

        """An argparse action for --config-file.

        As each --config-file option is encountered, this action adds the
        value to the config_file attribute on the _Namespace object but also
        parses the configuration file and stores the values found also in
        the _Namespace object.
        """

        def __call__(self, parser, namespace, values, option_string=None):
            """Handle a --config-file command line argument.

            :raises: ConfigFileParseError, ConfigFileValueError
            """
            if getattr(namespace, self.dest, None) is None:
                setattr(namespace, self.dest, [])
            items = getattr(namespace, self.dest)
            items.append(values)

            ConfigParser._parse_file(values, namespace)

    def _get_argparse_kwargs(self, group, **kwargs):
        """Extends the base argparse keyword dict for the config file opt."""
        kwargs = super(_ConfigFileOpt, self)._get_argparse_kwargs(group)
        kwargs['action'] = self.ConfigFileAction
        return kwargs


class _ConfigDirOpt(Opt):

    """The --config-dir option.

    This is an private option type which handles the special processing
    required for --config-dir options.

    As each --config-dir option is encountered on the command line, we
    parse the files in that directory and store the parsed values in the
    _Namespace object. This allows us to properly handle the precedence of
    --config-dir options over previous command line arguments, but not
    over subsequent arguments.
    """

    class ConfigDirAction(argparse.Action):

        """An argparse action for --config-dir.

        As each --config-dir option is encountered, this action sets the
        config_dir attribute on the _Namespace object but also parses the
        configuration files and stores the values found also in the
        _Namespace object.
        """

        def __call__(self, parser, namespace, values, option_string=None):
            """Handle a --config-dir command line argument.

            :raises: ConfigFileParseError, ConfigFileValueError
            """
            setattr(namespace, self.dest, values)

            config_dir_glob = os.path.join(values, '*.conf')

            for config_file in sorted(glob.glob(config_dir_glob)):
                ConfigParser._parse_file(config_file, namespace)

    def _get_argparse_kwargs(self, group, **kwargs):
        """Extends the base argparse keyword dict for the config dir option."""
        kwargs = super(_ConfigDirOpt, self)._get_argparse_kwargs(group)
        kwargs['action'] = self.ConfigDirAction
        return kwargs


class OptGroup(object):

    """Represents a group of opts.

    CLI opts in the group are automatically prefixed with the group name.

    Each group corresponds to a section in config files.

    An OptGroup object has no public methods, but has a number of public string
    properties:

      name:
        the name of the group
      title:
        the group title as displayed in --help
      help:
        the group description as displayed in --help
    """

    def __init__(self, name, title=None, help=None):
        """Constructs an OptGroup object.

        :param name: the group name
        :param title: the group title for --help
        :param help: the group description for --help
        """
        self.name = name
        self.title = "%s options" % name if title is None else title
        self.help = help

        self._opts = {}  # dict of dicts of (opt:, override:, default:)
        self._argparse_group = None

    def _register_opt(self, opt, cli=False):
        """Add an opt to this group.

        :param opt: an Opt object
        :param cli: whether this is a CLI option
        :returns: False if previously registered, True otherwise
        :raises: DuplicateOptError if a naming conflict is detected
        """
        if _is_opt_registered(self._opts, opt):
            return False

        self._opts[opt.dest] = {'opt': opt, 'cli': cli}

        return True

    def _unregister_opt(self, opt):
        """Remove an opt from this group.

        :param opt: an Opt object
        """
        if opt.dest in self._opts:
            del self._opts[opt.dest]

    def _get_argparse_group(self, parser):
        if self._argparse_group is None:
            """Build an argparse._ArgumentGroup for this group."""
            self._argparse_group = parser.add_argument_group(self.title,
                                                             self.help)
        return self._argparse_group

    def _clear(self):
        """Clear this group's option parsing state."""
        self._argparse_group = None


class ParseError(iniparser.ParseError):
    def __init__(self, msg, lineno, line, filename):
        super(ParseError, self).__init__(msg, lineno, line)
        self.filename = filename

    def __str__(self):
        return 'at %s:%d, %s: %r' % (self.filename, self.lineno,
                                     self.msg, self.line)


class ConfigParser(iniparser.BaseParser):
    def __init__(self, filename, sections):
        super(ConfigParser, self).__init__()
        self.filename = filename
        self.sections = sections
        self._normalized = None
        self.section = None

    def _add_normalized(self, normalized):
        self._normalized = normalized

    def parse(self):
        with open(self.filename) as f:
            return super(ConfigParser, self).parse(f)

    def new_section(self, section):
        self.section = section
        self.sections.setdefault(self.section, {})

        if self._normalized is not None:
            self._normalized.setdefault(_normalize_group_name(self.section),
                                        {})

    def assignment(self, key, value):
        if not self.section:
            raise self.error_no_section()

        value = '\n'.join(value)

        def append(sections, section):
            sections[section].setdefault(key, [])
            sections[section][key].append(value)

        append(self.sections, self.section)
        if self._normalized is not None:
            append(self._normalized, _normalize_group_name(self.section))

    def parse_exc(self, msg, lineno, line=None):
        return ParseError(msg, lineno, line, self.filename)

    def error_no_section(self):
        return self.parse_exc('Section must be started before assignment',
                              self.lineno)

    @classmethod
    def _parse_file(cls, config_file, namespace):
        """Parse a config file and store any values in the namespace.

        :raises: ConfigFileParseError, ConfigFileValueError
        """
        config_file = _fixpath(config_file)

        sections = {}
        normalized = {}
        parser = cls(config_file, sections)
        parser._add_normalized(normalized)

        try:
            parser.parse()
        except iniparser.ParseError as pe:
            raise ConfigFileParseError(pe.filename, str(pe))
        except IOError:
            namespace._file_not_found(config_file)
            return

        namespace.add_parsed_config_file(sections, normalized)


class MultiConfigParser(object):
    def __init__(self):
        self.parsed = []
        self._normalized = []

    def read(self, config_files):
        read_ok = []

        for filename in config_files:
            sections = {}
            normalized = {}
            parser = ConfigParser(filename, sections)
            parser._add_normalized(normalized)

            try:
                parser.parse()
            except IOError:
                continue
            self._add_parsed_config_file(sections, normalized)
            read_ok.append(filename)

        return read_ok

    def _add_parsed_config_file(self, sections, normalized):
        """Add a parsed config file to the list of parsed files.

        :param sections: a mapping of section name to dicts of config values
        :param normalized: sections mapping with section names normalized
        :raises: ConfigFileValueError
        """
        self.parsed.insert(0, sections)
        self._normalized.insert(0, normalized)

    def get(self, names, multi=False):
        return self._get(names, multi=multi)

    def _get(self, names, multi=False, normalized=False, convert_value=None):
        """Fetch a config file value from the parsed files.

        :param names: a list of (section, name) tuples
        :param multi: a boolean indicating whether to return multiple values
        :param normalized: whether to normalize group names to lowercase
        :param convert_value: callable to convert a string into the proper type
        """
        rvalue = []

        def normalize(name):
            return _normalize_group_name(section) if normalized else name

        def convert(value):
            return value if convert_value is None else convert_value(value)

        names = [(normalize(section), name) for section, name in names]

        for sections in (self._normalized if normalized else self.parsed):
            for section, name in names:
                if section not in sections:
                    continue
                if name in sections[section]:
                    val = [convert(v) for v in sections[section][name]]
                    if multi:
                        rvalue = val + rvalue
                    else:
                        return val
        if multi and rvalue != []:
            return rvalue
        raise KeyError


class _Namespace(argparse.Namespace):

    """An argparse namespace which also stores config file values.

    As we parse command line arguments, the values get set as attributes
    on a namespace object. However, we also want to parse config files as
    they are specified on the command line and collect the values alongside
    the option values parsed from the command line.

    Note, we don't actually assign values from config files as attributes
    on the namespace because config file options be registered after the
    command line has been parsed, so we may not know how to properly parse
    or convert a config file value at this point.
    """

    def __init__(self, conf):
        self.conf = conf
        self.parser = MultiConfigParser()
        self.files_not_found = []

    def _parse_cli_opts_from_config_file(self, sections, normalized):
        """Parse CLI options from a config file.

        CLI options are special - we require they be registered before the
        command line is parsed. This means that as we parse config files, we
        can go ahead and apply the appropriate option-type specific conversion
        to the values in config files for CLI options. We can't do this for
        non-CLI options, because the schema describing those options may not be
        registered until after the config files are parsed.

        This method relies on that invariant in order to enforce proper
        priority of option values - i.e. that the order in which an option
        value is parsed, whether the value comes from the CLI or a config file,
        determines which value specified for a given option wins.

        The way we implement this ordering is that as we parse each config
        file, we look for values in that config file for CLI options only. Any
        values for CLI options found in the config file are treated like they
        had appeared on the command line and set as attributes on the namespace
        objects. Values in later config files or on the command line will
        override values found in this file.
        """
        namespace = _Namespace(self.conf)
        namespace.parser._add_parsed_config_file(sections, normalized)

        for opt, group in sorted(self.conf._all_cli_opts()):
            group_name = group.name if group is not None else None
            try:
                value = opt._get_from_namespace(namespace, group_name)
            except KeyError:
                continue
            except ValueError as ve:
                raise ConfigFileValueError(str(ve))

            if group_name is None:
                dest = opt.dest
            else:
                dest = group_name + '_' + opt.dest

            if opt.multi:
                if getattr(self, dest, None) is None:
                    setattr(self, dest, [])
                values = getattr(self, dest)
                values.extend(value)
            else:
                setattr(self, dest, value)

    def add_parsed_config_file(self, sections, normalized):
        """Add a parsed config file to the list of parsed files.

        :param sections: a mapping of section name to dicts of config values
        :param normalized: sections mapping with section names normalized
        :raises: ConfigFileValueError
        """
        self._parse_cli_opts_from_config_file(sections, normalized)
        self.parser._add_parsed_config_file(sections, normalized)

    def _file_not_found(self, config_file):
        """Record that we were unable to open a config file.

        :param config_file: the path to the failed file
        """
        self.files_not_found.append(config_file)

    def _get_cli_value(self, names, positional):
        """Fetch a CLI option value.

        Look up the value of a CLI option. The value itself may have come from
        parsing the command line or parsing config files specified on the
        command line. Type conversion have already been performed for CLI
        options at this point.

        :param names: a list of (section, name) tuples
        :param multi: a boolean indicating whether to return multiple values
        :param convert_value: callable to convert a string into the proper type
        """
        for group_name, name in names:
            name = name if group_name is None else group_name + '_' + name
            try:
                value = getattr(self, name)
                if value is not None:
                    # argparse ignores default=None for nargs='*'
                    if positional and not value:
                        value = self.default
                    return value
            except AttributeError:
                pass
        raise KeyError

    def _get_value(self, names, multi, positional, convert_value):
        """Fetch a value from config files.

        Multiple names for a given configuration option may be supplied so
        that we can transparently handle files containing deprecated option
        names or groups.

        :param names: a list of (section, name) tuples
        :param multi: a boolean indicating whether to return multiple values
        :param positional: whether this is a positional option
        :param convert_value: callable to convert a string into the proper type
        """
        try:
            return self._get_cli_value(names, positional)
        except KeyError:
            pass

        names = [(g if g is not None else 'DEFAULT', n) for g, n in names]
        values = self.parser._get(names, multi=multi, normalized=True,
                                  convert_value=convert_value)
        return values if multi else values[-1]


class _CachedArgumentParser(argparse.ArgumentParser):

    """class for caching/collecting command line arguments.

    It also sorts the arguments before intializing the ArgumentParser.
    We need to do this since ArgumentParser by default does not sort
    the argument options and the only way to influence the order of
    arguments in '--help' is to ensure they are added in the sorted
    order.
    """

    def __init__(self, prog=None, usage=None):
        super(_CachedArgumentParser, self).__init__(prog, usage)
        self._args_cache = {}

    def add_parser_argument(self, container, *args, **kwargs):
        values = []
        if container in self._args_cache:
            values = self._args_cache[container]
        values.append({'args': args, 'kwargs': kwargs})
        self._args_cache[container] = values

    def initialize_parser_arguments(self):
        for container, values in six.iteritems(self._args_cache):
            values.sort(key=lambda x: x['args'])
            for argument in values:
                try:
                    container.add_argument(*argument['args'],
                                           **argument['kwargs'])
                except argparse.ArgumentError as e:
                    raise DuplicateOptError(e)
        self._args_cache = {}

    def parse_args(self, args=None, namespace=None):
        self.initialize_parser_arguments()
        return super(_CachedArgumentParser, self).parse_args(args, namespace)

    def print_help(self, file=None):
        self.initialize_parser_arguments()
        super(_CachedArgumentParser, self).print_help(file)

    def print_usage(self, file=None):
        self.initialize_parser_arguments()
        super(_CachedArgumentParser, self).print_usage(file)


class ConfigOpts(collections.Mapping):

    """Config options which may be set on the command line or in config files.

    ConfigOpts is a configuration option manager with APIs for registering
    option schemas, grouping options, parsing option values and retrieving
    the values of options.
    """

    def __init__(self):
        """Construct a ConfigOpts object."""
        self._opts = {}  # dict of dicts of (opt:, override:, default:)
        self._groups = {}

        self._args = None

        self._oparser = None
        self._namespace = None
        self.__cache = {}
        self._config_opts = []

    def _pre_setup(self, project, prog, version, usage, default_config_files):
        """Initialize a ConfigCliParser object for option parsing."""

        if prog is None:
            prog = os.path.basename(sys.argv[0])

        if default_config_files is None:
            default_config_files = find_config_files(project, prog)

        self._oparser = _CachedArgumentParser(prog=prog, usage=usage)
        self._oparser.add_parser_argument(self._oparser,
                                          '--version',
                                          action='version',
                                          version=version)

        return prog, default_config_files

    def _setup(self, project, prog, version, usage, default_config_files):
        """Initialize a ConfigOpts object for option parsing."""

        self._config_opts = [
            _ConfigFileOpt('config-file',
                           default=default_config_files,
                           metavar='PATH',
                           help=('Path to a config file to use. Multiple '
                                 'config files can be specified, with values '
                                 'in later files taking precedence. The '
                                 'default files used are: %(default)s')),
            _ConfigDirOpt('config-dir',
                          metavar='DIR',
                          help='Path to a config directory to pull *.conf '
                               'files from. This file set is sorted, so as to '
                               'provide a predictable parse order if '
                               'individual options are over-ridden. The set '
                               'is parsed after the file(s) specified via '
                               'previous --config-file, arguments hence '
                               'over-ridden options in the directory take '
                               'precedence.'),
        ]
        self.register_cli_opts(self._config_opts)

        self.project = project
        self.prog = prog
        self.version = version
        self.usage = usage
        self.default_config_files = default_config_files

    def __clear_cache(f):
        @functools.wraps(f)
        def __inner(self, *args, **kwargs):
            if kwargs.pop('clear_cache', True):
                self.__cache.clear()
            return f(self, *args, **kwargs)

        return __inner

    def __call__(self,
                 args=None,
                 project=None,
                 prog=None,
                 version=None,
                 usage=None,
                 default_config_files=None):
        """Parse command line arguments and config files.

        Calling a ConfigOpts object causes the supplied command line arguments
        and config files to be parsed, causing opt values to be made available
        as attributes of the object.

        The object may be called multiple times, each time causing the previous
        set of values to be overwritten.

        Automatically registers the --config-file option with either a supplied
        list of default config files, or a list from find_config_files().

        If the --config-dir option is set, any *.conf files from this
        directory are pulled in, after all the file(s) specified by the
        --config-file option.

        :param args: command line arguments (defaults to sys.argv[1:])
        :param project: the toplevel project name, used to locate config files
        :param prog: the name of the program (defaults to sys.argv[0] basename)
        :param version: the program version (for --version)
        :param usage: a usage string (%prog will be expanded)
        :param default_config_files: config files to use by default
        :returns: the list of arguments left over after parsing options
        :raises: SystemExit, ConfigFilesNotFoundError, ConfigFileParseError,
                 RequiredOptError, DuplicateOptError
        """

        self.clear()

        prog, default_config_files = self._pre_setup(project,
                                                     prog,
                                                     version,
                                                     usage,
                                                     default_config_files)

        self._setup(project, prog, version, usage, default_config_files)

        self._namespace = self._parse_cli_opts(args if args is not None
                                               else sys.argv[1:])
        if self._namespace.files_not_found:
            raise ConfigFilesNotFoundError(self._namespace.files_not_found)

        self._check_required_opts()

    def __getattr__(self, name):
        """Look up an option value and perform string substitution.

        :param name: the opt name (or 'dest', more precisely)
        :returns: the option value (after string subsititution) or a GroupAttr
        :raises: NoSuchOptError,ConfigFileValueError,TemplateSubstitutionError
        """
        return self._get(name)

    def __getitem__(self, key):
        """Look up an option value and perform string substitution."""
        return self.__getattr__(key)

    def __contains__(self, key):
        """Return True if key is the name of a registered opt or group."""
        return key in self._opts or key in self._groups

    def __iter__(self):
        """Iterate over all registered opt and group names."""
        for key in itertools.chain(self._opts.keys(), self._groups.keys()):
            yield key

    def __len__(self):
        """Return the number of options and option groups."""
        return len(self._opts) + len(self._groups)

    def reset(self):
        """Clear the object state and unset overrides and defaults."""
        self._unset_defaults_and_overrides()
        self.clear()

    @__clear_cache
    def clear(self):
        """Clear the state of the object to before it was called.

        Any subparsers added using the add_cli_subparsers() will also be
        removed as a side-effect of this method.
        """
        self._args = None
        self._oparser = argparse.ArgumentParser()
        self._namespace = None
        self.unregister_opts(self._config_opts)
        for group in self._groups.values():
            group._clear()

    @__clear_cache
    def register_opt(self, opt, group=None, cli=False):
        """Register an option schema.

        Registering an option schema makes any option value which is previously
        or subsequently parsed from the command line or config files available
        as an attribute of this object.

        :param opt: an instance of an Opt sub-class
        :param cli: whether this is a CLI option
        :param group: an optional OptGroup object or group name
        :return: False if the opt was already registered, True otherwise
        :raises: DuplicateOptError
        """
        if group is not None:
            group = self._get_group(group, autocreate=True)
            return group._register_opt(opt, cli)

        if _is_opt_registered(self._opts, opt):
            return False

        self._opts[opt.dest] = {'opt': opt, 'cli': cli}

        return True

    @__clear_cache
    def register_opts(self, opts, group=None):
        """Register multiple option schemas at once."""
        for opt in opts:
            self.register_opt(opt, group, clear_cache=False)

    @__clear_cache
    def register_cli_opt(self, opt, group=None):
        """Register a CLI option schema.

        CLI option schemas must be registered before the command line and
        config files are parsed. This is to ensure that all CLI options are
        shown in --help and option validation works as expected.

        :param opt: an instance of an Opt sub-class
        :param group: an optional OptGroup object or group name
        :return: False if the opt was already registered, True otherwise
        :raises: DuplicateOptError, ArgsAlreadyParsedError
        """
        if self._args is not None:
            raise ArgsAlreadyParsedError("cannot register CLI option")

        return self.register_opt(opt, group, cli=True, clear_cache=False)

    @__clear_cache
    def register_cli_opts(self, opts, group=None):
        """Register multiple CLI option schemas at once."""
        for opt in opts:
            self.register_cli_opt(opt, group, clear_cache=False)

    def register_group(self, group):
        """Register an option group.

        An option group must be registered before options can be registered
        with the group.

        :param group: an OptGroup object
        """
        if group.name in self._groups:
            return

        self._groups[group.name] = copy.copy(group)

    @__clear_cache
    def unregister_opt(self, opt, group=None):
        """Unregister an option.

        :param opt: an Opt object
        :param group: an optional OptGroup object or group name
        :raises: ArgsAlreadyParsedError, NoSuchGroupError
        """
        if self._args is not None:
            raise ArgsAlreadyParsedError("reset before unregistering options")

        if group is not None:
            self._get_group(group)._unregister_opt(opt)
        elif opt.dest in self._opts:
            del self._opts[opt.dest]

    @__clear_cache
    def unregister_opts(self, opts, group=None):
        """Unregister multiple CLI option schemas at once."""
        for opt in opts:
            self.unregister_opt(opt, group, clear_cache=False)

    def import_opt(self, name, module_str, group=None):
        """Import an option definition from a module.

        Import a module and check that a given option is registered.

        This is intended for use with global configuration objects
        like cfg.CONF where modules commonly register options with
        CONF at module load time. If one module requires an option
        defined by another module it can use this method to explicitly
        declare the dependency.

        :param name: the name/dest of the opt
        :param module_str: the name of a module to import
        :param group: an option OptGroup object or group name
        :raises: NoSuchOptError, NoSuchGroupError
        """
        __import__(module_str)
        self._get_opt_info(name, group)

    def import_group(self, group, module_str):
        """Import an option group from a module.

        Import a module and check that a given option group is registered.

        This is intended for use with global configuration objects
        like cfg.CONF where modules commonly register options with
        CONF at module load time. If one module requires an option group
        defined by another module it can use this method to explicitly
        declare the dependency.

        :param group: an option OptGroup object or group name
        :param module_str: the name of a module to import
        :raises: ImportError, NoSuchGroupError
        """
        __import__(module_str)
        self._get_group(group)

    @__clear_cache
    def set_override(self, name, override, group=None):
        """Override an opt value.

        Override the command line, config file and default values of a
        given option.

        :param name: the name/dest of the opt
        :param override: the override value
        :param group: an option OptGroup object or group name
        :raises: NoSuchOptError, NoSuchGroupError
        """
        opt_info = self._get_opt_info(name, group)
        opt_info['override'] = override

    @__clear_cache
    def set_default(self, name, default, group=None):
        """Override an opt's default value.

        Override the default value of given option. A command line or
        config file value will still take precedence over this default.

        :param name: the name/dest of the opt
        :param default: the default value
        :param group: an option OptGroup object or group name
        :raises: NoSuchOptError, NoSuchGroupError
        """
        opt_info = self._get_opt_info(name, group)
        opt_info['default'] = default

    @__clear_cache
    def clear_override(self, name, group=None):
        """Clear an override an opt value.

        Clear a previously set override of the command line, config file
        and default values of a given option.

        :param name: the name/dest of the opt
        :param group: an option OptGroup object or group name
        :raises: NoSuchOptError, NoSuchGroupError
        """
        opt_info = self._get_opt_info(name, group)
        opt_info.pop('override', None)

    @__clear_cache
    def clear_default(self, name, group=None):
        """Clear an override an opt's default value.

        Clear a previously set override of the default value of given option.

        :param name: the name/dest of the opt
        :param group: an option OptGroup object or group name
        :raises: NoSuchOptError, NoSuchGroupError
        """
        opt_info = self._get_opt_info(name, group)
        opt_info.pop('default', None)

    def _all_opt_infos(self):
        """A generator function for iteration opt infos."""
        for info in self._opts.values():
            yield info, None
        for group in self._groups.values():
            for info in group._opts.values():
                yield info, group

    def _all_cli_opts(self):
        """A generator function for iterating CLI opts."""
        for info, group in self._all_opt_infos():
            if info['cli']:
                yield info['opt'], group

    def _unset_defaults_and_overrides(self):
        """Unset any default or override on all options."""
        for info, group in self._all_opt_infos():
            info.pop('default', None)
            info.pop('override', None)

    def find_file(self, name):
        """Locate a file located alongside the config files.

        Search for a file with the supplied basename in the directories
        which we have already loaded config files from and other known
        configuration directories.

        The directory, if any, supplied by the config_dir option is
        searched first. Then the config_file option is iterated over
        and each of the base directories of the config_files values
        are searched. Failing both of these, the standard directories
        searched by the module level find_config_files() function is
        used. The first matching file is returned.

        :param basename: the filename, e.g. 'policy.json'
        :returns: the path to a matching file, or None
        """
        dirs = []
        if self.config_dir:
            dirs.append(_fixpath(self.config_dir))

        for cf in reversed(self.config_file):
            dirs.append(os.path.dirname(_fixpath(cf)))

        dirs.extend(_get_config_dirs(self.project))

        return _search_dirs(dirs, name)

    def log_opt_values(self, logger, lvl):
        """Log the value of all registered opts.

        It's often useful for an app to log its configuration to a log file at
        startup for debugging. This method dumps to the entire config state to
        the supplied logger at a given log level.

        :param logger: a logging.Logger object
        :param lvl: the log level (e.g. logging.DEBUG) arg to logger.log()
        """
        logger.log(lvl, "*" * 80)
        logger.log(lvl, "Configuration options gathered from:")
        logger.log(lvl, "command line args: %s", self._args)
        logger.log(lvl, "config files: %s", self.config_file)
        logger.log(lvl, "=" * 80)

        def _sanitize(opt, value):
            """Obfuscate values of options declared secret."""
            return value if not opt.secret else '*' * len(str(value))

        for opt_name in sorted(self._opts):
            opt = self._get_opt_info(opt_name)['opt']
            logger.log(lvl, "%-30s = %s", opt_name,
                       _sanitize(opt, getattr(self, opt_name)))

        for group_name in self._groups:
            group_attr = self.GroupAttr(self, self._get_group(group_name))
            for opt_name in sorted(self._groups[group_name]._opts):
                opt = self._get_opt_info(opt_name, group_name)['opt']
                logger.log(lvl, "%-30s = %s",
                           "%s.%s" % (group_name, opt_name),
                           _sanitize(opt, getattr(group_attr, opt_name)))

        logger.log(lvl, "*" * 80)

    def print_usage(self, file=None):
        """Print the usage message for the current program."""
        self._oparser.print_usage(file)

    def print_help(self, file=None):
        """Print the help message for the current program."""
        self._oparser.print_help(file)

    def _get(self, name, group=None):
        if isinstance(group, OptGroup):
            key = (group.name, name)
        else:
            key = (group, name)
        try:
            return self.__cache[key]
        except KeyError:
            value = self._substitute(self._do_get(name, group))
            self.__cache[key] = value
            return value

    def _do_get(self, name, group=None):
        """Look up an option value.

        :param name: the opt name (or 'dest', more precisely)
        :param group: an OptGroup
        :returns: the option value, or a GroupAttr object
        :raises: NoSuchOptError, NoSuchGroupError, ConfigFileValueError,
                 TemplateSubstitutionError
        """
        if group is None and name in self._groups:
            return self.GroupAttr(self, self._get_group(name))

        info = self._get_opt_info(name, group)
        opt = info['opt']

        if isinstance(opt, SubCommandOpt):
            return self.SubCommandAttr(self, group, opt.dest)

        if 'override' in info:
            return info['override']

        if self._namespace is not None:
            group_name = group.name if group is not None else None
            try:
                return opt._get_from_namespace(self._namespace, group_name)
            except KeyError:
                pass
            except ValueError as ve:
                raise ConfigFileValueError(str(ve))

        if 'default' in info:
            return info['default']

        return opt.default

    def _substitute(self, value):
        """Perform string template substitution.

        Substitute any template variables (e.g. $foo, ${bar}) in the supplied
        string value(s) with opt values.

        :param value: the string value, or list of string values
        :returns: the substituted string(s)
        """
        if isinstance(value, list):
            return [self._substitute(i) for i in value]
        elif isinstance(value, str):
            tmpl = string.Template(value)
            return tmpl.safe_substitute(self.StrSubWrapper(self))
        else:
            return value

    def _get_group(self, group_or_name, autocreate=False):
        """Looks up a OptGroup object.

        Helper function to return an OptGroup given a parameter which can
        either be the group's name or an OptGroup object.

        The OptGroup object returned is from the internal dict of OptGroup
        objects, which will be a copy of any OptGroup object that users of
        the API have access to.

        :param group_or_name: the group's name or the OptGroup object itself
        :param autocreate: whether to auto-create the group if it's not found
        :raises: NoSuchGroupError
        """
        group = group_or_name if isinstance(group_or_name, OptGroup) else None
        group_name = group.name if group else group_or_name

        if group_name not in self._groups:
            if group is not None or not autocreate:
                raise NoSuchGroupError(group_name)

            self.register_group(OptGroup(name=group_name))

        return self._groups[group_name]

    def _get_opt_info(self, opt_name, group=None):
        """Return the (opt, override, default) dict for an opt.

        :param opt_name: an opt name/dest
        :param group: an optional group name or OptGroup object
        :raises: NoSuchOptError, NoSuchGroupError
        """
        if group is None:
            opts = self._opts
        else:
            group = self._get_group(group)
            opts = group._opts

        if opt_name not in opts:
            raise NoSuchOptError(opt_name, group)

        return opts[opt_name]

    def _check_required_opts(self):
        """Check that all opts marked as required have values specified.

        :raises: RequiredOptError
        """
        for info, group in self._all_opt_infos():
            opt = info['opt']

            if opt.required:
                if 'default' in info or 'override' in info:
                    continue

                if self._get(opt.dest, group) is None:
                    raise RequiredOptError(opt.name, group)

    def _parse_cli_opts(self, args):
        """Parse command line options.

        Initializes the command line option parser and parses the supplied
        command line arguments.

        :param args: the command line arguments
        :returns: a _Namespace object containing the parsed option values
        :raises: SystemExit, DuplicateOptError
                 ConfigFileParseError, ConfigFileValueError

        """
        self._args = args

        for opt, group in sorted(self._all_cli_opts(),
                                 key=lambda x: x[0].name):
            opt._add_to_cli(self._oparser, group)

        namespace = _Namespace(self)

        for arg in args:
            if arg == '--config-file' or arg.startswith('--config-file='):
                break
        else:
            for config_file in self.default_config_files:
                ConfigParser._parse_file(config_file, namespace)

        return self._oparser.parse_args(args, namespace)

    class GroupAttr(collections.Mapping):

        """Helper class.

        Represents the option values of a group as a mapping and attributes.
        """

        def __init__(self, conf, group):
            """Construct a GroupAttr object.

            :param conf: a ConfigOpts object
            :param group: an OptGroup object
            """
            self._conf = conf
            self._group = group

        def __getattr__(self, name):
            """Look up an option value and perform template substitution."""
            return self._conf._get(name, self._group)

        def __getitem__(self, key):
            """Look up an option value and perform string substitution."""
            return self.__getattr__(key)

        def __contains__(self, key):
            """Return True if key is the name of a registered opt or group."""
            return key in self._group._opts

        def __iter__(self):
            """Iterate over all registered opt and group names."""
            for key in self._group._opts.keys():
                yield key

        def __len__(self):
            """Return the number of options and option groups."""
            return len(self._group._opts)

    class SubCommandAttr(object):

        """Helper class.

        Represents the name and arguments of an argparse sub-parser.
        """

        def __init__(self, conf, group, dest):
            """Construct a SubCommandAttr object.

            :param conf: a ConfigOpts object
            :param group: an OptGroup object
            :param dest: the name of the sub-parser
            """
            self._conf = conf
            self._group = group
            self._dest = dest

        def __getattr__(self, name):
            """Look up a sub-parser name or argument value."""
            if name == 'name':
                name = self._dest
                if self._group is not None:
                    name = self._group.name + '_' + name
                return getattr(self._conf._namespace, name)

            if name in self._conf:
                raise DuplicateOptError(name)

            try:
                return getattr(self._conf._namespace, name)
            except AttributeError:
                raise NoSuchOptError(name)

    class StrSubWrapper(object):

        """Helper class.

        Exposes opt values as a dict for string substitution.
        """

        def __init__(self, conf):
            """Construct a StrSubWrapper object.

            :param conf: a ConfigOpts object
            """
            self.conf = conf

        def __getitem__(self, key):
            """Look up an opt value from the ConfigOpts object.

            :param key: an opt name
            :returns: an opt value
            :raises: TemplateSubstitutionError if attribute is a group
            """
            value = getattr(self.conf, key)
            if isinstance(value, self.conf.GroupAttr):
                raise TemplateSubstitutionError(
                    'substituting group %s not supported' % key)
            return value


CONF = ConfigOpts()
