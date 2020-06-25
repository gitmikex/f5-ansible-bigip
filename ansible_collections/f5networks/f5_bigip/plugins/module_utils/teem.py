# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 F5 Networks Inc.
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


import sys
import uuid
import re

from time import time
from datetime import datetime

from ansible.module_utils.urls import open_url
from ansible.module_utils.six.moves.urllib.error import HTTPError

from .constants import (
    TEEM_ENDPOINT, TEEM_KEY, TEEM_TIMEOUT, TEEM_VERIFY,
    CURRENT_COLL_VERSION, BASE_HEADERS, PLATFORM
)


class TeemClient:
    def __init__(self, f5client, start_time):
        self.f5client = f5client
        self.start_time = start_time

    def prepare_request(self):
        asset_id = str(uuid.uuid4())
        user_agent = 'F5_BIGIP/{0}'.format(CURRENT_COLL_VERSION)
        telemetry = self.build_telemetry()
        url = 'https://%s/ee/v1/telemetry' % TEEM_ENDPOINT
        headers = {
                    'F5-ApiKey': TEEM_KEY,
                    'F5-DigitalAssetId': asset_id,
                    'F5-TraceId': str(uuid.uuid4()),
                    'User-Agent': user_agent
                }
        headers.update(BASE_HEADERS)
        data = {
            'digitalAssetName': 'F5_BIGIP',
            'digitalAssetVersion': CURRENT_COLL_VERSION,
            'digitalAssetId': asset_id,
            'documentType': 'F5_BIGIP Ansible Collection',
            'documentVersion': '1',
            'observationStartTime': self.start_time,
            'observationEndTime': datetime.now().isoformat(),
            'epochTime': time(),
            'telemetryId': str(uuid.uuid4()),
            'telemetryRecords': telemetry
        }
        return url, headers, data

    def send(self):
        url, headers, data = self.prepare_request()
        try:
            self.f5client.plugin._display_message('F5 TEEM phone home with data: {0}'.format(data))
            response = open_url(
                url=url,
                method='POST',
                headers=headers,
                timeout=TEEM_TIMEOUT,
                validate_certs=TEEM_VERIFY,
                data=data
            )
        except HTTPError as e:
            raise
        ok = re.search(r'20[01-4]', str(response.code))
        if ok:
            self.f5client.plugin._display_message('TEEM Data sent successfully.')

    def build_telemetry(self):
        module_name = self.f5client.module_name
        tmp, version = self.f5client.platform
        platform = PLATFORM.get(tmp, '')
        ansible_version = self.f5client.ansible_version
        python_version = sys.version.split(' ')[0]

        return [{
            'CollectionName': 'F5_BIGIP',
            'CollectionVersion': CURRENT_COLL_VERSION,
            'CollectionModuleName': module_name,
            'f5Platform': platform,
            'f5SoftwareVersion': version,
            'ControllerAnsibleVersion': ansible_version,
            'ControllerPythonVersion': python_version
        }]



