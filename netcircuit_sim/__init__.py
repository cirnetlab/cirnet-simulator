"""Compatibility imports for pre-CIRNET Simulator consumers.

All names resolve to canonical modules, preserving class and pickle identity.
"""
from importlib import import_module as _import_module
import sys as _sys

_canonical = _import_module('cirnet_sim')
for _name in ('logic', 'circuit', 'waveform', 'nets', 'analog', 'engine', 'dispatch', 'backends'):
    _sys.modules[__name__ + '.' + _name] = _import_module('cirnet_sim.' + _name)
_sys.modules[__name__] = _canonical
