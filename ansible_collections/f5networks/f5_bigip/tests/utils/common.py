# -*- coding: utf-8 -*-
#
# Copyright: (c) 2020, F5 Networks Inc.
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
from unittest.mock import Mock

from ansible.module_utils.six import BytesIO


def connection_response(response, status=200):
    response_mock = Mock()
    response_mock.getcode.return_value = status
    response_text = json.dumps(response) if type(response) is dict else response
    response_data = BytesIO(response_text.encode() if response_text else ''.encode())
    return response_mock, response_data
