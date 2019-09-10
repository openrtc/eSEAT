#!/usr/bin/env python3

from setuptools import setup

setup(name='eSEAT',
      version='2.5',
      install_requires=['bs4', 'lxml', 'PyYAML'],
      description='extended Speech Event Action Transfer(eSEAT)',
      author='Isao Hara and Yosuke Matsusaka, AIST',
      author_email='isao-hara@aist.go.jp',
      url='https://github.com/haraisao/eSEAT/',
      packages=['eSEAT'],
      entry_points="""
      [console_scripts]
      eSEAT3 = eSEAT.main:main
      eSEAT_Node3 = eSEAT.core:main_node
      rtcmd = eSEAT.rtcmd:main
      """,
    ) 
