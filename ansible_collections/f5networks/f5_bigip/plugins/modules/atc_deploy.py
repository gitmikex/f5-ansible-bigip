#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright: (c) 2020, F5 Networks Inc.
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: atc_deploy
short_description: Manages ATC declarations sent to BIG-IP
description:
  - Manages ATC declarations sent to BIG-IP.
version_added: "1.0.0"
options:
  service_type:
    description:
      - Specifies the type of declaration to manage.
    type: str
    required: True
    choices:
      - as3
      - do
      - ts
      - cfe
  content:
    description:
      - Declaration to be configured on the system.
      - This parameter is most often used along with the C(file) or C(template) lookup plugins.
        Refer to the examples section for correct usage.
      - For anything advanced or with formatting consider using the C(template) lookup.
      - This can additionally be used for specifying application service configurations
        directly in YAML, however that is not an encouraged practice and, if used at all,
        should only be used for the absolute smallest of configurations to prevent your
        Playbooks from becoming too large.
      - If you C(content) includes encrypted values (such as ciphertexts, passphrases, etc),
        the returned C(changed) value will always be true.
      - If you are using the C(to_nice_json) filter, it will cause this module to fail because
        the purpose of that filter is to format the JSON to be human-readable and this process
        includes inserting "extra characters that break JSON validators.
    type: raw
  as3_tenant:
    description:
      - An as3_tenant you wish to manage.
      - This parameter is only relevant when C(service_type) is C(as3), it will be ignored otherwise.
      - A value of C(all) or no value when C(state) is C(absent) will remove all as3 declarations from device.
    type: str
  state:
    description:
      - When C(state) is C(present), ensures the declaration is exists.
      - When C(state) is C(absent), ensures that the declaration is removed. The C(absent) state is only used when
        C(service_type) is C(as3), it will be ignored otherwise.
    type: str
    choices:
      - present
      - absent
    default: present
notes:
  - Due to limitations of the ATC packages, the module is not idempotent when C(service_type) is other than C(as3).
author:
  - Wojciech Wypior (@wojtek0806)
'''

EXAMPLES = r'''
- hosts: all
  collections:
    - f5networks.f5_bigip
  connection: httpapi

  vars:
    ansible_host: "lb.mydomain.com"
    ansible_user: "admin"
    ansible_httpapi_password: "secret"
    ansible_network_os: f5networks.f5_bigip.bigip
    ansible_httpapi_use_ssl: yes
    
- name: Declaration with 2 Tenants - AS3
  atc_deploy:
    content: "{{ lookup('file', 'two_tenants.json') }}"
    service_type: "as3"

- name: Remove one tenant - AS3
  atc_deploy:
    service_type: "as3"
    as3_tenant: "Sample_01"
    state: absent
  register: result
'''

RETURN = r'''
service_type:
  description: The type of declaration sent to system.
  returned: changed
  type: str
  sample: as3
content:
  description: The declaration sent to the system.
  returned: changed
  type: raw
  sample: hash/dictionary of values
as3_tenant:
  description: The as3_tenant to be managed.
  returned: changed
  type: str
  sample: foobar1
'''
import time

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection
from ansible.module_utils.six import string_types

from ..module_utils.client import F5Client
from ..module_utils.common import (
    F5ModuleError, AnsibleF5Parameters,
)

try:
    import json
except ImportError:
    import simplejson as json


class Parameters(AnsibleF5Parameters):
    api_map = {}
    api_attributes = []

    returnables = [
        'content',
        'tenant',
        'service_type',
    ]


class ApiParameters(Parameters):
    pass


class ModuleParameters(Parameters):
    @property
    def content(self):
        if self._values['content'] is None:
            return None
        if isinstance(self._values['content'], string_types):
            return json.loads(self._values['content'] or 'null')
        else:
            return self._values['content']

    @property
    def tenant(self):
        if self._values['as3_tenant'] in [None, 'all']:
            return None
        return self._values['as3_tenant']


class Changes(Parameters):
    def to_return(self):
        result = {}
        try:
            for returnable in self.returnables:
                result[returnable] = getattr(self, returnable)
            result = self._filter_params(result)
        except Exception:
            raise
        return result


class UsableChanges(Changes):
    pass


class ReportableChanges(Changes):
    pass


class BaseManager(object):
    def __init__(self, *args, **kwargs):
        self.module = kwargs.get('module', None)
        self.connection = kwargs.get('connection', None)
        self.client = F5Client(module=self.module, client=self.connection)
        self.want = ModuleParameters(params=self.module.params)
        self.changes = UsableChanges()

    def _set_changed_options(self):
        changed = {}
        for key in Parameters.returnables:
            if getattr(self.want, key) is not None:
                changed[key] = getattr(self.want, key)
        if changed:
            self.changes = UsableChanges(params=changed)

    def _announce_deprecations(self, result):
        warnings = result.pop('__warnings', [])
        for warning in warnings:
            self.client.module.deprecate(
                msg=warning['msg'],
                version=warning['version']
            )

    def _check_task_on_device(self, path):
        response = self.client.get(path)
        if response['code'] not in [200, 201, 202]:
            raise F5ModuleError(response['contents'])
        return response['contents']

    def exec_module(self):
        result = dict()

        changed = self.upsert()

        result.update(dict(changed=changed))
        self._announce_deprecations(result)
        return result

    def upsert(self):
        self._set_changed_options()
        if self.module.check_mode:
            return True
        result = self.upsert_on_device()
        return result


class As3Manager(BaseManager):
    def exec_module(self):
        changed = False
        result = dict()
        state = self.want.state

        if state == "present":
            changed = self.present()
        elif state == "absent":
            changed = self.absent()

        result.update(dict(changed=changed))
        return result

    def present(self):
        if self.exists():
            return False
        return self.upsert()

    def absent(self):
        if self.resource_exists():
            return self.remove()
        return False

    def remove(self):
        if self.module.check_mode:
            return True
        result = self.remove_from_device()
        if self.resource_exists():
            raise F5ModuleError("Failed to delete the resource.")
        return result

    def exists(self):
        declaration = {}
        if self.want.content is None:
            raise F5ModuleError(
                "Empty content cannot be specified when 'state' is 'present'."
            )
        try:
            declaration.update(self.want.content)
        except ValueError:
            raise F5ModuleError(
                "The provided 'content' could not be converted into valid json. If you "
                "are using the 'to_nice_json' filter, please remove it."
            )
        declaration['action'] = 'dry-run'

        if self.want.tenant:
            uri = "/mgmt/shared/appsvcs/declare/{0}".format(self.want.tenant)
        else:
            uri = "/mgmt/shared/appsvcs/declare"

        response = self.client.post(uri, data=declaration)

        if response['code'] not in [200, 201, 202, 204, 207]:
            raise F5ModuleError(response['contents'])

        return all([msg.get('message', None) == 'no change' for msg in response['contents']['results']])

    def _get_errors_from_response(self, messages):
        results = []
        if 'results' not in messages:
            if 'message' in messages:
                results.append(messages['message'])
            if 'errors' in messages:
                results += messages['errors']
        else:
            for message in messages['results']:
                if 'message' in message and message['message'] in ['declaration failed', 'declaration is invalid']:
                    results.append(message['message'])
                if 'errors' in message:
                    results += message['errors']
        return results

    def upsert_on_device(self):
        if self.want.tenant:
            uri = "/mgmt/shared/appsvcs/declare/{0}?async=true".format(self.want.tenant)
        else:
            uri = "/mgmt/shared/appsvcs/declare?async=true"

        response = self.client.post(uri, data=self.want.content)

        if response['code'] not in [200, 201, 202, 204, 207]:
            raise F5ModuleError(response['contents'])

        task = self.wait_for_task("/mgmt/shared/appsvcs/task/{0}".format(response['contents']['id']))
        if task:
            return any(msg.get('message', None) != 'no change' for msg in task['results'])

    def wait_for_task(self, path):
        for x in range(0, 900):
            task = self._check_task_on_device(path)
            errors = self._get_errors_from_response(task)
            if errors:
                message = "{0}".format('. '.join(errors))
                raise F5ModuleError(message)
            if any([msg.get('message', None) != 'in progress' for msg in task['results']]):
                return task
            time.sleep(1)
        return False

    def resource_exists(self):
        if self.want.tenant:
            uri = "/mgmt/shared/appsvcs/declare/{0}".format(self.want.tenant)
        else:
            uri = "/mgmt/shared/appsvcs/declare"

        response = self.client.get(uri)

        if response['code'] == 404:
            return False
        if response['code'] == 204:
            return False
        return True

    def remove_from_device(self):
        if self.want.tenant:
            uri = "/mgmt/shared/appsvcs/declare/{0}?async=true".format(self.want.tenant)
        else:
            uri = "/mgmt/shared/appsvcs/declare?async=true"

        response = self.client.delete(uri)

        if response['code'] not in [200, 201, 202, 204, 207]:
            raise F5ModuleError(response['contents'])

        task = self.wait_for_task("/mgmt/shared/appsvcs/task/{0}".format(response['contents']['id']))
        if task:
            return any(msg.get('message', None) != 'no change' for msg in task['results'])


class DoManager(BaseManager):
    def _get_errors_from_response(self, message):
        results = []
        if 'message' in message and message['message'] == 'invalid config - rolling back':
            results.append(message['message'])
        if 'errors' in message:
            results += message['errors']
        return results

    def upsert_on_device(self):
        uri = "/mgmt/shared/declarative-onboarding/declare"
        response = self.client.post(uri, data=self.want.content)

        if response['code'] not in [200, 201, 202, 204, 207]:
            raise F5ModuleError(response['contents'])

        task = self.wait_for_task("/mgmt/shared/declarative-onboarding/task/{0}".format(response['contents']['id']))
        if task:
            if 'message' in task['result'] and task['result']['message'] == 'success':
                return True
            return False

    def wait_for_task(self, path):
        for x in range(0, 200):
            response = self.client.get(path)
            # DO will not be consistent as it will throw: 404, 400, 401 or 503 error codes in no
            # particular order due to services restarting.
            if response['code'] in [400, 401, 404, 503]:
                self.wait_for_device_to_be_ready()
                response = self.client.get(path)
            if response['code'] in [200, 201, 202]:
                errors = self._get_errors_from_response(response['contents'])
                if errors:
                    message = "{0}".format('. '.join(errors))
                    raise F5ModuleError(message)
                if response['contents']['result']['status'] != 'RUNNING':
                    return response['contents']
            time.sleep(15)

    def wait_for_device_to_be_ready(self):
        while True:
            response = self.client.get('/mgmt/shared/declarative-onboarding/available')
            if response['code'] == 200:
                break
            time.sleep(20)


class TsManager(BaseManager):
    def upsert_on_device(self):
        uri = "/mgmt/shared/telemetry/declare"
        response = self.client.post(uri, data=self.want.content)

        if response['code'] not in [200, 201, 202]:
            raise F5ModuleError(response['contents'])

        if response['contents']['message'] == 'success':
            return True
        return False


class FailoverManager(BaseManager):
    def upsert_on_device(self):
        uri = "/mgmt/shared/cloud-failover/declare"
        response = self.client.post(uri, data=self.want.content)

        if response['code'] not in [200, 201, 202]:
            raise F5ModuleError(response['contents'])

        if response['contents']['message'] == 'success':
            return True
        return False


class ModuleManager(object):
    def __init__(self, *args, **kwargs):
        self.module = kwargs.get('module', None)
        self.kwargs = kwargs

    def exec_module(self):
        if self.module.params['service_type'] == 'as3':
            manager = self.get_manager('as3')
        if self.module.params['service_type'] == 'do':
            manager = self.get_manager('do')
        if self.module.params['service_type'] == 'ts':
            manager = self.get_manager('ts')
        if self.module.params['service_type'] == 'cfe':
            manager = self.get_manager('cfe')

        return manager.exec_module()

    def get_manager(self, type):
        if type == 'as3':
            return As3Manager(**self.kwargs)
        if type == 'do':
            return DoManager(**self.kwargs)
        if type == 'ts':
            return TsManager(**self.kwargs)
        if type == 'cfe':
            return FailoverManager(**self.kwargs)


class ArgumentSpec(object):
    def __init__(self):
        self.supports_check_mode = True
        argument_spec = dict(
            service_type=dict(
                required=True,
                choices=['as3', 'do', 'ts', 'cfe']
            ),
            content=dict(type='raw'),
            as3_tenant=dict(),
            state=dict(
                default='present',
                choices=['present', 'absent']
            ),
        )
        self.argument_spec = {}
        self.argument_spec.update(argument_spec)
        self.required_if = [
            ['state', 'present', ['content']]
        ]


def main():
    spec = ArgumentSpec()

    module = AnsibleModule(
        argument_spec=spec.argument_spec,
        supports_check_mode=spec.supports_check_mode,
        required_if=spec.required_if
    )

    try:
        mm = ModuleManager(module=module, connection=Connection(module._socket_path))
        results = mm.exec_module()
        module.exit_json(**results)
    except F5ModuleError as ex:
        module.fail_json(msg=str(ex))


if __name__ == '__main__':
    main()
