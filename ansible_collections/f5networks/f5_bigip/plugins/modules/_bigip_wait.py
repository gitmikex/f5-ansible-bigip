#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright: (c) 2017, F5 Networks Inc.
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: bigip_wait
short_description: Wait for a BIG-IP condition before continuing
description:
  - You can wait for BIG-IP to be "ready". By "ready", we mean that BIG-IP is ready
    to accept configuration.
  - This module can take into account situations where the device is in the middle
    of rebooting due to a configuration change.
version_added: "1.0.0"
options:
  type:
    description:
      - The type of the BIG-IP.
      - Defaults to C(standard), the other choice is C(vcmp).
      - The choice made defines what module or service Ansible will look for to establish
        that the device has recovered, so please ensure the correct choice is
        specified, specially when running this against VCMP.
    type: str
    default: standard
    choices:
      - standard
      - vcmp
  timeout:
    description:
      - Maximum number of seconds to wait for.
      - When used without other conditions it is equivalent of just sleeping.
      - The default timeout is deliberately set to 2 hours because no individual
        REST API.
    type: int
    default: 7200
  delay:
    description:
      - Number of seconds to wait before starting to poll.
    type: int
    default: 0
  sleep:
    description:
      - Number of seconds to sleep between checks, before this was hardcoded to 1 second.
    type: int
    default: 1
  msg:
    description:
      - This overrides the normal error message from a failure to meet the required conditions.
    type: str
  use_ssh:
    description:
      - Determines if C(network_cli) is to be used as a method of connection.
      - Default connection is always C(httpapi).
    type: bool
    default: no
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

  tasks:
    - name: Wait for BIG-IP to be ready - REST
      bigip_wait:
        timeout: 10
        delay: 10
        sleep: 5


- hosts: all
  collections:
    - f5networks.f5_bigip
  connection: network_cli

  vars:
    ansible_host: "lb.mydomain.com"
    ansible_user: "admin"
    ansible_ssh_password: "secret"
    ansible_network_os: "f5networks.f5_bigip.bigip"
    ansible_port: "22"

  tasks:
    - name: Wait for BIG-IP to be ready - SSH u/p
      bigip_wait:
        use_ssh: yes
        timeout: 10
        delay: 10
        sleep: 5

- hosts: all
  collections:
    - f5networks.f5_bigip
  connection: network_cli

  vars:
    ansible_host: "lb.mydomain.com"
    ansible_user: "admin"
    ansible_private_key_file: "mykeyfile.key"
    ansible_network_os: "f5networks.f5_bigip.bigip"
    ansible_port: "22"

  tasks:
    - name: Wait for BIG-IP to be ready - SSH cert
      bigip_wait:
        use_ssh: yes
        timeout: 10
        delay: 10
        sleep: 5

'''

RETURN = r'''
# only common fields returned
'''


import datetime
import signal
import time

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import (
    exec_command, Connection
)

from ..module_utils.client import F5Client
from ..module_utils.common import (
    F5ModuleError, AnsibleF5Parameters,
)


def hard_timeout(module, want, start):
    elapsed = datetime.datetime.utcnow() - start
    module.fail_json(
        msg=want.msg or "Timeout when waiting for BIG-IP", elapsed=elapsed.seconds
    )


class Parameters(AnsibleF5Parameters):
    returnables = [
        'elapsed'
    ]

    def to_return(self):
        result = {}
        try:
            for returnable in self.returnables:
                result[returnable] = getattr(self, returnable)
            result = self._filter_params(result)
        except Exception:
            raise
        return result

    @property
    def delay(self):
        if self._values['delay'] is None:
            return None
        return int(self._values['delay'])

    @property
    def timeout(self):
        if self._values['timeout'] is None:
            return None
        return int(self._values['timeout'])

    @property
    def sleep(self):
        if self._values['sleep'] is None:
            return None
        return int(self._values['sleep'])


class Changes(Parameters):
    pass


class BaseManager(object):
    def __init__(self, *args, **kwargs):
        self.module = kwargs.get('module', None)
        self.connection = kwargs.get('connection', None)
        self.client = F5Client(module=self.module, client=self.connection)
        self.want = Parameters(params=self.module.params)
        self.changes = Parameters()

    def exec_module(self):
        result = dict()

        changed = self.execute()

        changes = self.changes.to_return()
        result.update(**changes)
        result.update(dict(changed=changed))
        self._announce_deprecations(result)
        return result

    def _announce_deprecations(self, result):
        warnings = result.pop('__warnings', [])
        for warning in warnings:
            self.module.deprecate(
                msg=warning['msg'],
                version=warning['version']
            )

    def execute(self):
        if self.want.delay >= self.want.timeout:
            raise F5ModuleError(
                "The delay should not be greater than or equal to the timeout."
            )
        if self.want.delay + self.want.sleep >= self.want.timeout:
            raise F5ModuleError(
                "The combined delay and sleep should not be greater than or equal to the timeout."
            )
        signal.signal(
            signal.SIGALRM,
            lambda sig, frame: hard_timeout(self.module, self.want, start)
        )

        # setup handler before scheduling signal, to eliminate a race
        signal.alarm(int(self.want.timeout))

        start = datetime.datetime.utcnow()
        if self.want.delay:
            time.sleep(float(self.want.delay))
        end = start + datetime.timedelta(seconds=int(self.want.timeout))

        self.wait_for_device(start, end)

        elapsed = datetime.datetime.utcnow() - start
        self.changes.update({'elapsed': elapsed.seconds})
        return False

    def _wait_for_module_provisioning(self):
        # To prevent things from running forever, the hack is to check
        # for mprov's status twice. If mprov is finished, then in most
        # cases (not ASM) the provisioning is probably ready.
        nops = 0
        # Sleep a little to let provisioning settle and begin properly
        time.sleep(5)
        while nops < 4:
            try:
                if not self._is_mprov_running_on_device():
                    nops += 1
                else:
                    nops = 0
            except Exception:
                # This can be caused by restjavad restarting.
                pass
            time.sleep(10)

    def _wait_for_rest_interface(self):
        nops = 0
        # Sleep a little to let daemons settle and begin checking if REST interface is available.
        time.sleep(5)
        while nops < 4:
            if not self._rest_endpoints_ready():
                nops += 1
            else:
                break
        time.sleep(10)


class V1Manager(BaseManager):
    def wait_for_device(self, start, end):
        while datetime.datetime.utcnow() < end:
            time.sleep(int(self.want.sleep))
            # First we check if SSH connection is ready by repeatedly attempting to run a simple command
            rc, out, err = exec_command(self.module, 'date')
            if rc != 0:
                continue
            if self._device_is_rebooting():
                # Wait for the reboot to happen and then start from the beginning
                # of the waiting.
                continue
            if self.want.type == "standard":
                if self._is_mprov_running_on_device():
                    self._wait_for_module_provisioning()
            elif self.want.type == "vcmp":
                self._is_vcmpd_running_on_device()
            if not self._rest_endpoints_ready():
                self._wait_for_rest_interface()
            break
        else:
            elapsed = datetime.datetime.utcnow() - start
            self.module.fail_json(
                msg=self.want.msg or "Timeout when waiting for BIG-IP", elapsed=elapsed.seconds
            )

    def _is_mprov_running_on_device(self):
        cmd = "ps aux | grep '[m]prov'"
        rc, out, err = exec_command(self.module, cmd)
        if rc != 0:
            raise F5ModuleError(err)
        if out:
            return True
        return False

    def _is_vcmpd_running_on_device(self):
        cmd = "ps aux | grep '[v]cmpd'"
        rc, out, err = exec_command(self.module, cmd)
        if rc != 0:
            raise F5ModuleError(err)
        if out:
            return True
        return False

    def _rest_endpoints_ready(self):
        cmd = "curl -o /dev/null -s -w\'%{http_code}\\n\' -u admin: http://localhost:8100/mgmt/tm/sys/available"
        rc, out, err = exec_command(self.module, cmd)
        if rc != 0:
            raise F5ModuleError(err)
        if out == '200':
            return True
        return False

    def _device_is_rebooting(self):
        cmd = 'runlevel'
        rc, out, err = exec_command(self.module, cmd)
        if rc != 0:
            raise F5ModuleError(err)
        if out.split(' ')[1] == '6':
            return True
        return False


class V2Manager(BaseManager):
    def wait_for_device(self, start, end):
        while datetime.datetime.utcnow() < end:
            time.sleep(int(self.want.sleep))
            try:
                # The first test verifies that the REST API is available; this is done
                # by repeatedly trying to login to it.
                self.client = self._get_client_connection()
                if not self.client:
                    continue

                if self._device_is_rebooting():
                    # Wait for the reboot to happen and then start from the beginning
                    # of the waiting.
                    continue

                if self.want.type == "standard":
                    if self._is_mprov_running_on_device():
                        self._wait_for_module_provisioning()
                elif self.want.type == "vcmp":
                    self._is_vcmpd_running_on_device()
                if not self._rest_endpoints_ready():
                    self._wait_for_rest_interface()
                break
            except Exception as ex:
                if 'Failed to validate the SSL' in str(ex):
                    raise F5ModuleError(str(ex))

                # The types of exception's we're handling here are "REST API is not
                # ready" exceptions.
                #
                # For example,
                #
                # Typically caused by device starting up:
                #
                #   icontrol.exceptions.iControlUnexpectedHTTPError: 404 Unexpected Error:
                #       Not Found for uri: https://localhost:10443/mgmt/tm/sys/
                #   icontrol.exceptions.iControlUnexpectedHTTPError: 503 Unexpected Error:
                #       Service Temporarily Unavailable for uri: https://localhost:10443/mgmt/tm/sys/
                #
                #
                # Typically caused by a device being down
                #
                #   requests.exceptions.SSLError: HTTPSConnectionPool(host='localhost', port=10443):
                #       Max retries exceeded with url: /mgmt/tm/sys/ (Caused by SSLError(
                #       SSLError("bad handshake: SysCallError(-1, 'Unexpected EOF')",),))
                #
                #
                # Typically caused by device still booting
                #
                #   raise SSLError(e, request=request)\nrequests.exceptions.SSLError:
                #   HTTPSConnectionPool(host='localhost', port=10443): Max retries
                #   exceeded with url: /mgmt/shared/authn/login (Caused by
                #   SSLError(SSLError(\"bad handshake: SysCallError(-1, 'Unexpected EOF')\",),)),
                continue
        else:
            elapsed = datetime.datetime.utcnow() - start
            self.module.fail_json(
                msg=self.want.msg or "Timeout when waiting for BIG-IP", elapsed=elapsed.seconds
            )

    def _get_client_connection(self):
        return F5Client(module=self.module, client=self.connection)

    def _device_is_rebooting(self):
        params = {
            "command": "run",
            "utilCmdArgs": '-c "runlevel"'
        }

        response = self.client.post("/mgmt/tm/util/bash", data=params)

        if response['code'] not in [200, 201]:
            raise F5ModuleError(response['contents'])

        if 'commandResult' in response['contents'] and '6' in response['contents']['commandResult']:
            return True
        return False

    def _is_mprov_running_on_device(self):
        params = {
            "command": "run",
            "utilCmdArgs": '-c "ps aux | grep \'[m]prov\'"'
        }

        response = self.client.post("/mgmt/tm/util/bash", data=params)

        if response['code'] not in [200, 201]:
            raise F5ModuleError(response['contents'])

        if 'commandResult' in response['contents']:
            return True
        return False

    def _is_vcmpd_running_on_device(self):
        params = {
            "command": "run",
            "utilCmdArgs": '-c "ps aux | grep \'[v]cmpd\'"'
        }

        response = self.client.post("/mgmt/tm/util/bash", data=params)

        if response['code'] not in [200, 201]:
            raise F5ModuleError(response['contents'])

        if 'commandResult' in response['contents']:
            return True
        return False

    def _rest_endpoints_ready(self):
        response = self.client.get("/mgmt/tm/sys/available")
        if response['code'] in [200, 201]:
            return True
        return False


class ModuleManager(object):
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.module = kwargs.get('module', None)
        self.connection = kwargs.get('connection', None)

    def exec_module(self):
        if self.module.params['use_ssh']:
            manager = self.get_manager('v1')
        else:
            manager = self.get_manager('v2')
        result = manager.exec_module()
        return result

    def get_manager(self, type):
        if type == 'v1':
            return V1Manager(**self.kwargs)
        elif type == 'v2':
            return V2Manager(**self.kwargs)


class ArgumentSpec(object):
    def __init__(self):
        self.supports_check_mode = True
        argument_spec = dict(
            type=dict(
                choices=['standard', 'vcmp'],
                default='standard'
            ),
            use_ssh=dict(
                type='bool',
                default='no'
            ),
            timeout=dict(default=7200, type='int'),
            delay=dict(default=0, type='int'),
            sleep=dict(default=1, type='int'),
            msg=dict(),
        )
        self.argument_spec = {}
        self.argument_spec.update(argument_spec)


def main():
    spec = ArgumentSpec()

    module = AnsibleModule(
        argument_spec=spec.argument_spec,
        supports_check_mode=spec.supports_check_mode
    )

    try:
        mm = ModuleManager(module=module, connection=Connection(module._socket_path))
        results = mm.exec_module()
        module.exit_json(**results)
    except F5ModuleError as ex:
        module.fail_json(msg=str(ex))


if __name__ == '__main__':
    main()
