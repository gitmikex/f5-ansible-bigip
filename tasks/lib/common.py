#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 F5 Networks Inc.
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import os


def is_gitlab():
    """
    Determines if the script is executed within Gitlab CI/CD
    :rtype: bool
    """
    return os.environ.get('GITLAB_CI') == 'true'


def get_base_dir():
    if is_gitlab():
        return os.environ.get('CI_PROJECT_DIR')
    else:
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

