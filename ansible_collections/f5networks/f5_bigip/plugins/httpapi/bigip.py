#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright: (c) 2020, F5 Networks Inc.
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
---
author: Wojciech Wypior <w.wypior@f5.com>
httpapi: bigip
short_description: HttpApi Plugin for BIG-IP devices
description:
  - This HttpApi plugin provides methods to connect to BIG-IP
    devices over a HTTP(S)-based api.
options:
  provider:
    description:
    - The login provider used in communicating with BIG-IP devices when the API connection
      is first established.
    - If the provider is not specified, the default C(tmos) value is assumed.
    ini:
    - section: defaults
      key: f5_provider
    env:
    - name: F5_PROVIDER
    vars:
    - name: f5_provider
  send_telemetry:
    description:
      - If C(yes) anonymous telemetry data is sent to F5
    default: True
    ini:
    - section: defaults
      key: f5_telemetry
    env:
      - name: F5_TELEMETRY
    vars:
      - name: f5_telemetry
version_added: "1.0"
"""
import re
from ansible.module_utils.basic import to_text
from ansible.plugins.httpapi import HttpApiBase
from ansible.module_utils.six.moves.urllib.error import HTTPError
from ansible.errors import AnsibleConnectionFailure

from ansible_collections.f5networks.f5_bigip.plugins.module_utils.constants import (
    LOGIN, LOGOUT, BASE_HEADERS
)

try:
    import json
except ImportError:
    import simplejson as json


class HttpApi(HttpApiBase):
    def __init__(self, connection):
        super(HttpApi, self).__init__(connection)
        self.connection = connection
        self.access_token = None

    def login(self, username, password):
        provider = self.get_option("provider")

        if username and password:
            payload = {
                'username': username,
                'password': password,
                'loginProviderName': provider if provider else 'tmos'
            }

            response = self.send_request(LOGIN, method='POST', data=payload, headers=BASE_HEADERS)
        else:
            raise AnsibleConnectionFailure('Username and password are required for login.')

        if response['code'] == 200 and 'token' in response['contents']:
            self.access_token = response['contents']['token'].get('token', None)
            if self.access_token:
                self.connection._auth = {'X-F5-Auth-Token': self.access_token}
            else:
                raise AnsibleConnectionFailure('Server returned invalid response during connection authentication.')
        else:
            raise AnsibleConnectionFailure('Authentication process failed, server returned: {0}'.format(
                response['contents'])
            )

    def logout(self):
        if not self.connection._auth:
            return
        token = self.connection._auth.get('X-F5-Auth-Token', None)
        logout_uri = '{0}{1}'.format(LOGOUT, token)
        self.send_request(logout_uri, method='DELETE')

    def handle_httperror(self, exc):
        err_5xx = r'^5\d{2}$'
        # We raise AnsibleConnectionFailure without passing to the module, as 50x type errors indicate a problem
        # with BigIP. If we need to handle 50x upstream for say modules that loop and reconnect after performing
        # operation on device i.e. software install we will remove this and do the handling in the module.

        handled_error = re.search(err_5xx, str(exc.code))
        if handled_error:
            raise AnsibleConnectionFailure('Could not connect to {0}: {1}'.format(self.connection._url, exc.reason))
        return False

    def send_request(self, url, method=None, **kwargs):
        body = kwargs.pop('data', None)
        data = json.dumps(body) if body else None

        try:
            self._display_request(method, url)
            response, response_data = self.connection.send(url, data, method=method, **kwargs)
            response_value = self._get_response_value(response_data)
            return dict(
                code=response.getcode(),
                contents=self._response_to_json(response_value),
                headers=response.headers
            )

        except HTTPError as e:
            return dict(code=e.code, contents=json.loads(e.read()))

    def _display_request(self, method, data):
        self._display_message(
            'BIG-IP API Call: {0} {1} with data {2}'.format(method, self.connection._url, data)
        )

    def _display_message(self, msg):
        self.connection._log_messages(msg)

    def _get_response_value(self, response_data):
        return to_text(response_data.getvalue())

    def _response_to_json(self, response_text):
        try:
            return json.loads(response_text) if response_text else {}
        # JSONDecodeError only available on Python 3.5+
        except ValueError:
            raise ConnectionError('Invalid JSON response: %s' % response_text)

    def _telemetry(self):
        return self.get_option('telemetry')

    def _network_os(self):
        return self.connection._network_os
