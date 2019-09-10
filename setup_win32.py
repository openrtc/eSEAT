#!/usr/bin/env python

'''setup script for SEAT and SAT

Copyright (C) 2009-2010
    Yosuke Matsusaka and Isao Hara
    Intelligent Systems Research Institute,
    National Institute of Advanced Industrial Science and Technology (AIST),
    Japan
    All rights reserved.
Licensed under the Eclipse Public License -v 1.0 (EPL)
http://www.opensource.org/licenses/eclipse-1.0.txt
'''

from setuptools import setup, find_packages
from setuptools.command.build_ext import build_ext
import sys, os
#from seatsat.__init__ import __version__

cmd_classes = {}
try:
    from DistUtilsExtra.command import *
    cmd_classes.update({"build": build_extra.build_extra,
                        "build_i18n" :  build_i18n.build_i18n})
except ImportError:
    pass

try:
    import py2exe
except ImportError:
    pass

if sys.platform == "win32":
    # py2exe options
    extra = {
        "console": [
                    "eSEAT.py",
                    ],
        "options": {
            "py2exe": {
                "includes": "xml.etree.ElementTree, lxml._elementpath, bs4, OpenRTM_aist, RTC, gzip, multiprocessing, eSEAT_Core, SeatmlParser, SocketAdaptor, utils, WebAdaptor",
#                "bundle_files": 1,
                "dll_excludes": [ 
                    "MSVCP90.dll",
                    "api-ms-win-core-processthreads-l1-1-2.dll",
                    "api-ms-win-core-sysinfo-l1-2-1.dll",
                    "api-ms-win-core-errorhandling-l1-1-1.dll",
                    "api-ms-win-core-profile-l1-1-0.dll",
                    "api-ms-win-core-libraryloader-l1-2-0.dll",
                ],
            }
        }
    }
else:
    extra = {}

setup(name='seatsat',
      cmdclass=cmd_classes,
      version= '0.1',
      description="Simple dialogue manager component for OpenRTM (part of OpenHRI softwares)",
      long_description="""Simple dialogue manager component for OpenRTM (part of OpenHRI softwares).""",
      classifiers=[],
      keywords='',
      author='Yosuke Matsusaka, Isao Hara',
      author_email='isao-hara@aist.go.jp',
      url='http://openrtc.org/openrtc',
      license='EPL',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      package_data={'seatsat': ['*.xsd',]},
      zip_safe=False,
      install_requires=[
        # -*- Extra requirements: -*-
        ],
      entry_points="""
      [console_scripts]
      seat = seatsat.SEAT:main
      validateseatml = seatsat.validateseatml:main
      seateditor = seatsat.seateditor:main
      seatmltographviz = seatsat.seatmltographviz:main
      seatmltosrgs = seatsat.seatmltosrgs:main
      soarrtc = seatsat.SoarRTC:main
      """,
      **extra
      )
