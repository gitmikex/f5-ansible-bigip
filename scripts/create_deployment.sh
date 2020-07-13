#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 F5 Networks Inc.
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

BIGIP_MODULES=',"bigIpModules":{"value":"ltm:nominal"}'
BIGIP_VERSION=',"bigIpVersion":{"value":"15.1.002000"}'
DNS_NAME=',"dnsLabel": {"value":"ansible-test"}'
TEMPLATE_FILE=scripts/azuredeploy.json

# shellcheck disable=SC2089
DEPLOY_PARAMS='{"authenticationType":{"value":"password"},"adminPasswordOrKey":{"value":"C@tr0cks!"},"adminUsername":{"value":"ansible"},"imageName":{"value":"Best200Mbps"},"restrictedSrcAddress":{"value":"*"},"allowUsageAnalytics":{"value":"No"},"allowPhoneHome":{"value":"No"}'${DNS_NAME}''${BIGIP_MODULES}''${BIGIP_VERSION}'}'
DEPLOY_PARAMS_FILE=tmp/deploy_params.json

# save deployment parameters to a file, to avoid weird parameter parsing errors with certain values
# when passing as a variable. I.E. when providing an sshPublicKey
touch ${DEPLOY_PARAMS_FILE}
echo "${DEPLOY_PARAMS}" > ${DEPLOY_PARAMS_FILE}

echo "DEBUG: DEPLOY PARAMS"
echo "${DEPLOY_PARAMS}"

VALIDATE_RESPONSE=$(az group deployment validate --resource-group "ansible-$CI_PIPELINE_ID" --template-file "${TEMPLATE_FILE}" --parameters @${DEPLOY_PARAMS_FILE})
VALIDATION=$(echo "${VALIDATE_RESPONSE}" | jq .properties.provisioningState)
if [[ $VALIDATION == \"Succeeded\" ]]; then
    az group deployment create --verbose --template-file "${TEMPLATE_FILE}" -g "ansible-$CI_PIPELINE_ID" -n "ansible-$CI_PIPELINE_ID" --parameters @${DEPLOY_PARAMS_FILE}
    echo "Template creation succeeded."
else
    echo "Template validation failed: ${VALIDATE_RESPONSE}"
    exit 1
fi
