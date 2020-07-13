#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 F5 Networks Inc.
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import os
import subprocess
import sys
import datetime


# Azure Variables
AZURE_TENANT_ID = 'AZURE_TENANT_ID'
AZURE_CLIENT_ID = 'AZURE_CLIENT_ID'
AZURE_SERVICE_PRINCIPAL = 'AZURE_SERVICE_PRINCIPAL'
AZURE_SUBSCRIPTION_ID = 'AZURE_SUBSCRIPTION_ID'


def main():
    configure_azure()


def configure_azure():
    _print_formatted('configuring Azure')
    tenant_id = os.environ.get(AZURE_TENANT_ID)
    client_id = os.environ.get(AZURE_CLIENT_ID)
    service_principal = os.environ.get(AZURE_SERVICE_PRINCIPAL)

    # Login to Azure CLI 2.0
    _call_subprocess(
        ["az", "login", "--tenant", tenant_id, "-u", client_id, "-p", service_principal, "--service-principal"],
        'Unable to login to Azure CLI 2.0'
    )


def _print_formatted(message):
    timestamp = datetime.datetime.now()
    print(f'{timestamp} - {__file__} - {message}')


def _call_subprocess(command, error_description):
    try:
        call_response = subprocess.call(command)
    except Exception as err:
        _log_and_exit(err, error_description)
    if call_response != 0:
        _log_and_exit(error_description)


def _log_and_exit(message, err=''):
    _print_formatted(message)
    sys.exit(err)


if __name__ == "__main__":
    main()

