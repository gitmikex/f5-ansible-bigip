#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 F5 Networks Inc.
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import os

from invoke import task
from .lib.common import get_base_dir

TEST_DIR = get_base_dir() + '/integration'


@task(name='all')
def test_all(c):
    """Runs full test suite."""
    for test in get_all_directories():
        with c.cd(TEST_DIR + '/' + test):
            print("Testing {0} module.".format(test))
            c.run('molecule test')


def get_all_directories():
    """Returns full list of directories for integration tests."""
    output = [d for d in os.listdir(TEST_DIR) if os.path.isdir(os.path.join(TEST_DIR, d)) and d != 'resources']
    return output


def filter_for_changes(c):
    """Placeholder for function that will be entry point to selective testing."""
    pass

