# -*- coding: utf-8 -*-
#
# Copyright: (c) 2020, F5 Networks Inc.
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
import os
from unittest.mock import MagicMock, Mock
from unittest import TestCase

from ansible.errors import AnsibleConnectionFailure
from ansible.module_utils.six.moves.urllib.error import HTTPError
from ansible.module_utils.six import StringIO
from ansible.playbook.play_context import PlayContext
from ansible.plugins.loader import connection_loader

from ansible_collections.f5networks.f5_bigip.tests.utils.common import connection_response

fixture_path = os.path.join(os.path.dirname(__file__), 'fixtures')
fixture_data = {}


def load_fixture(name):
    path = os.path.join(fixture_path, name)

    if path in fixture_data:
        return fixture_data[path]

    with open(path) as f:
        data = f.read()

    try:
        data = json.loads(data)
    except Exception:
        pass

    fixture_data[path] = data
    return data


class TestBigIPHttpapi(TestCase):
    def setUp(self):
        self.pc = PlayContext()
        self.pc.network_os = "f5networks.f5_bigip.bigiq"
        self.connection = connection_loader.get("httpapi", self.pc, "/dev/null")
        self.mock_send = MagicMock()
        self.connection.send = self.mock_send

    def test_login_raises_exception_when_username_and_password_are_not_provided(self):
        with self.assertRaises(AnsibleConnectionFailure) as res:
            self.connection.httpapi.login(None, None)
        assert 'Username and password are required for login.' in str(res.exception)

    def test_login_raises_exception_when_invalid_token_response(self):
        self.connection.send.return_value = connection_response(
            {'token': {'BAZ': 'BAR'}}
        )
        with self.assertRaises(AnsibleConnectionFailure) as res:
            self.connection.httpapi.login('foo', 'bar')

        assert 'Server returned invalid response during connection authentication.' in str(res.exception)

    def test_send_request_should_return_error_info_when_http_error_raises(self):
        self.connection.send.side_effect = HTTPError(
            'http://bigip.local', 400, '', {}, StringIO('{"errorMessage": "ERROR"}')
        )

        with self.assertRaises(AnsibleConnectionFailure) as res:
            self.connection.httpapi.login('foo', 'bar')

        assert "Authentication process failed, server returned: {'errorMessage': 'ERROR'}" in str(res.exception)

    def test_get_login_ref(self):
        self.connection.send.return_value = connection_response(
            load_fixture('load_provider_list.json')
        )

        expected = {
            'loginReference':
                {'link':
                    'https://localhost/mgmt/cm/system/authn/providers/RadiusServer/'
                    '15633ac8-362c-4b05-b1f9-f77f3cd8921e/login'
                 }
        }

        result = self.connection.httpapi._get_login_ref('RadiusServer')
        assert result == expected

    def test_login_success_local_provider(self):
        self.connection.send.return_value = connection_response(load_fixture('local_auth_response.json'))

        token = "eyJraWQiOiJhZmExZDliOC1jN2NiLTQ2NWMtOTE0Yy00MWNkODgwZjM1YjEiLCJhbGciOiJSUzM4NCJ9.eyJpc3MiOiJCSU" \
                "ctSVEiLCJqdGkiOiJuaGpmanVqRU9FWnZqaWQtR2xUSW1RIiwic3ViIjoiYWRtaW4iLCJhdWQiOiIxNzIuMTguNy41NSIsI" \
                "mlhdCI6MTU5MzE4Nzg3MSwiZXhwIjoxNTkzMTg4MTcxLCJ1c2VyTmFtZSI6ImFkbWluIiwiYXV0aFByb3ZpZGVyTmFtZSI6" \
                "ImxvY2FsIiwidXNlciI6Imh0dHBzOi8vbG9jYWxob3N0L21nbXQvc2hhcmVkL2F1dGh6L3VzZXJzL2FkbWluIiwidHlwZSI" \
                "6IkFDQ0VTUyIsInRpbWVvdXQiOjMwMCwiZ3JvdXBSZWZlcmVuY2VzIjpbXX0.Ob1gwS93X0yE1Q5rKiHEpFl-5dcmFN8dR-" \
                "CLe_ghJaNT4zEWp4r6EdgQ57yrBCHqfoe2JMVJ9UYW7Dn8lJh1buDJLAOJ9l1ifUQo0rSKkSI1UwNyVI5KeHafclngz1MNH" \
                "G8HUB0vRySfDO5FhRjDrNyXL7CeOblog9qgVAsBOW60A9Tgx4vlFgDebzf46Pp_EO9Oes75oIQSkGdARuYbNtM72QwWNUO6" \
                "fiFo_L93-LOrQiWz87PECRkwq5C91sl4uiqdBGN2LRjwHcs3v2vNQbVTlABPnOsGLe14dZE4AZ_peNwIBIGL4JT_55rdohl" \
                "AKqQKCIgEDTB9xvQyOZgX9yO76FfTIpzg2tPLVomiaFHK1joFdzJ-jWWfBUdlKLgYbenwUD9VRyZncv6fTmJug_QSCc1FL8" \
                "4cw8Ab745kBiwOwpr5RwvRqMjDKJfQuyTX_CYQIt9j-RfrGAORqiSvlu7FUykIXdcnpO9WktEr6Y3MZl7Wj__kyngZ3nwM-NOM"

        self.connection.httpapi.login('foo', 'bar')

        assert self.connection.httpapi.access_token == token
        assert self.connection._auth == {'X-F5-Auth-Token': token}

    def test_login_success_radius_provider(self):
        self.connection.send.side_effect = [
            connection_response(load_fixture('load_provider_list.json')),
            connection_response(load_fixture('login_with_non_local_provider.json'))
        ]
        mock_response = MagicMock()
        self.connection.httpapi.get_option = mock_response
        self.connection.httpapi.get_option.return_value = 'RadiusServer'

        self.connection.httpapi.login('baz', 'bar')

        token = "eyJraWQiOiJhZmExZDliOC1jN2NiLTQ2NWMtOTE0Yy00MWNkODgwZjM1YjEiLCJhbGciOiJSUzM4NCJ9.eyJpc3MiOiJCSU" \
                "ctSVEiLCJqdGkiOiJFNkhKdnZOUnpwSnNQenB4MVRYSjN3Iiwic3ViIjoicGF1bGEiLCJhdWQiOiIxNzIuMTguNy41NSIsIm" \
                "lhdCI6MTU5MzE4ODg1MywiZXhwIjoxNTkzMTg5MTUzLCJ1c2VyTmFtZSI6InBhdWxhIiwiYXV0aFByb3ZpZGVyTmFtZSI6Il" \
                "JhZGl1c1NlcnZlciIsInVzZXIiOiJodHRwczovL2xvY2FsaG9zdC9tZ210L2NtL3N5c3RlbS9hdXRobi9wcm92aWRlcnMvcm" \
                "FkaXVzLzE1NjMzYWM4LTM2MmMtNGIwNS1iMWY5LWY3N2YzY2Q4OTIxZS91c2Vycy8xYjIwNzQ2NS1lYWM4LTNiNWQtOGIxMi" \
                "1lMzM1ZmFhMGI1M2EiLCJ0eXBlIjoiQUNDRVNTIiwidGltZW91dCI6MzAwLCJncm91cFJlZmVyZW5jZXMiOltdfQ.IESe2Hp" \
                "LfZOMZJ5dS1U90jAPDB8gvmJXNNVkcYcL0WTFmJ9XdSTnuw7NbGddZPXBwH-VmA7v0lPLymb_RmQqDoSQ1nnD692oSlRVpC9Z" \
                "g3S1zA-6Ela3ChuIpnQU3ZY0XBDhCKGF_L-9ryC5QPrsCcwLYX-1u579yJlUzGPxxRU4CSp7Gz7-HpUqFVvCOzc5_mJbQD_td" \
                "0z2bbOUnl3m7IbTEBrB8q_svvCONleiGk15bTyLyP-KZKblSzF1Ypr73F5EHbJUS75zhLls6Zqm7XKPA_5ZXq9_YO-sXsKYOB" \
                "nGurYieXDF_o0EdmUFqNypUr0bJxlSv4IAbZRJFi-kNKcsRrUm-t5c2UBXITKyQsCx2dsAS6zSAxMGLEF87kahTlQuRZ9NCs3" \
                "bokAz1cmuntWhLq0GxOwcJf45_F70lmu5192DXUlbiz13CLMzWHHA4lpcgwrwrUl1zqnT5arb7vOeAXFUNK1Eiu2OFnbAgItx" \
                "634fj8EJCQWjIelvgm6y"

        assert self.connection.httpapi.access_token == token
        assert self.connection._auth == {'X-F5-Auth-Token': token}

    def test_get_telemetry_network_os(self):
        mock_response = MagicMock()
        self.connection.httpapi.get_option = mock_response
        self.connection.httpapi.get_option.return_value = False

        assert self.connection.httpapi.telemetry() is False
        assert self.connection.httpapi.network_os() == self.pc.network_os
