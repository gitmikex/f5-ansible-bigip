# -*- coding: utf-8 -*-
#
# Copyright: (c) 2020, F5 Networks Inc.
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
import os

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.f5networks.f5_bigip.plugins.modules.bigip_lx_package import (
    Parameters, ArgumentSpec, ModuleManager
)
from ansible_collections.f5networks.f5_bigip.tests.compat import unittest
from ansible_collections.f5networks.f5_bigip.tests.compat.mock import Mock, patch
from ansible_collections.f5networks.f5_bigip.tests.modules.utils import set_module_args


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


class TestParameters(unittest.TestCase):
    def test_module_parameters(self):
        args = dict(
            package='MyApp-0.1.0-0001.noarch.rpm',
            state='present'
        )
        p = Parameters(params=args)
        assert p.package == 'MyApp-0.1.0-0001.noarch.rpm'


class TestManager(unittest.TestCase):

    def setUp(self):
        self.spec = ArgumentSpec()
        self.patcher1 = patch('time.sleep')
        self.patcher1.start()

    def tearDown(self):
        self.patcher1.stop()

    def test_upload_rpm_package(self, *args):
        package_name = os.path.join(fixture_path, 'MyApp-0.1.0-0001.noarch.rpm')
        # Configure the arguments that would be sent to the Ansible module
        set_module_args(dict(
            package=package_name,
            state='present',
        ))

        module = AnsibleModule(
            argument_spec=self.spec.argument_spec,
            supports_check_mode=self.spec.supports_check_mode,
            required_if=self.spec.required_if
        )
        mm = ModuleManager(module=module)

        # Override methods to force specific logic in the module to happen
        mm.exists = Mock(side_effect=[False, True])
        mm.create_on_device = Mock(return_value=True)
        mm.check_file_exists_on_device = Mock(return_value=False)
        mm.upload_to_device = Mock(return_value=True)
        mm.enable_iapplx_on_device = Mock(return_value=True)
        mm.retain_package_file = Mock(return_value=False)
        mm.remove_package_file_from_device = Mock(return_value=True)

        results = mm.exec_module()

        assert results['changed'] is True
