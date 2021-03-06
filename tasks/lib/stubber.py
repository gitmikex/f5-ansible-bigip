#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2017 F5 Networks Inc.
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import os
import shutil

from .common import BASE_DIR

try:
    from jinja2 import Environment
    from jinja2 import FileSystemLoader
    HAS_JINJA = True
except ImportError:
    HAS_JINJA = False

if HAS_JINJA:
    JINJA_ENV = Environment(
        loader=FileSystemLoader(BASE_DIR + '/devtools/stubs')
    )


def module_file_present(module):
    module_file = '{0}/ansible_collections/f5networks/f5_bigip/plugins/modules/{1}.py'.format(BASE_DIR, module)
    if os.path.exists(module_file):
        print('Module file "{0}" exists'.format(module_file))
        return True
    return False


def module_file_absent(module):
    result = module_file_present(module)
    return not result


def stub_roles_dirs(module):
    # Create role containing all of your future functional tests
    for d in ['defaults', 'tasks', 'meta']:
        directory = '{0}/integration/targets/{1}/{2}'.format(BASE_DIR, module, d)
        if not os.path.exists(directory):
            os.makedirs(directory)


def stub_roles_yaml_files(module):
    # Create default vars to contain any playbook variables
    for d in ['defaults', 'tasks']:
        defaults_file = '{0}/integration/targets/{1}/{2}/main.yaml'.format(
            BASE_DIR, module, d
        )
        touch(defaults_file)
    for f in ['setup.yaml', 'teardown.yaml']:
        defaults_file = '{0}/integration/targets/{1}/tasks/{2}'.format(BASE_DIR, module, f)
        touch(defaults_file)
    main_tests = '{0}/integration/targets/{1}/tasks/main.yaml'.format(BASE_DIR, module)

    template = JINJA_ENV.get_template('test_integration_targets_main.yaml')
    content = template.render()

    with open(main_tests, 'w') as fh:
        fh.write(content)

    stub_meta_main_file(module)


def stub_meta_main_file(module):
    touch('{0}/integration/targets/{1}/meta/main.yml'.format(BASE_DIR, module))
    main_meta = '{0}/integration/targets/{1}/meta/main.yml'.format(BASE_DIR, module)
    template = JINJA_ENV.get_template('test_meta_main.yml')
    content = template.render()

    with open(main_meta, 'w') as fh:
        fh.write(content)


def stub_playbook_file(module):
    # Stub out the test playbook
    playbook_file = '{0}/integration/{1}.yaml'.format(BASE_DIR, module)

    template = JINJA_ENV.get_template('playbooks_module.yaml')
    content = template.render(module=module)

    fh = open(playbook_file, 'w')
    fh.write(content)
    fh.close()


def stub_library_file(module, extension, version):
    # Create your new module python file
    library_file = '{0}/ansible_collections/f5networks/f5_bigip/plugins/modules/{1}{2}'.format(
        BASE_DIR, module, extension
    )

    template = JINJA_ENV.get_template('library_module.py')
    content = template.render(module=module, version=version)

    fh = open(library_file, 'w')
    fh.write(content)
    fh.close()


def touch(name, times=None):
    with open(name, 'a'):
        os.utime(name, times)


def stub_unit_test_file(module, extension):
    test_dir_path = '{0}/ansible_collections/f5networks/f5_bigip/tests/modules/network/f5/'.format(BASE_DIR)
    if not os.path.exists(test_dir_path):
        os.makedirs(test_dir_path)
    test_file = '{0}/ansible_collections/f5networks/f5_bigip/tests/modules/network/f5/test_{1}{2}'.format(
        BASE_DIR, module, extension
    )

    template = JINJA_ENV.get_template('tests_unit_module.py')
    content = template.render(module=module)

    fh = open(test_file, 'w')
    fh.write(content)
    fh.close()


def unstub_meta_yml_files(module):
    main_meta = '{0}/integration/targets/{1}/meta/main.yml'.format(BASE_DIR, module)
    if os.path.exists(main_meta):
        os.remove(main_meta)


def unstub_roles_yaml_files(module):
    for d in ['defaults', 'tasks']:
        defaults_file = '{0}/integration/targets/{1}/{2}/main.yaml'.format(
            BASE_DIR, module, d
        )
    if os.path.exists(defaults_file):
        os.remove(defaults_file)

    unstub_meta_yml_files(module)

    for f in ['setup.yaml', 'teardown.yaml']:
        set_teardown_file = '{0}/integration/targets/{1}/tasks/{2}'.format(BASE_DIR, module, f)
    if os.path.exists(set_teardown_file):
        os.remove(set_teardown_file)
    main_tests = '{0}/integration/targets/{1}/tasks/main.yaml'.format(BASE_DIR, module)
    if os.path.exists(main_tests):
        os.remove(main_tests)


def unstub_roles_dirs(module):
    for d in ['defaults', 'tasks', 'meta']:
        directory = '{0}/integration/targets/{1}/{2}'.format(BASE_DIR, module, d)
        if os.path.exists(directory):
            shutil.rmtree(directory)
    main_dir = '{0}/integration/targets/{1}'.format(BASE_DIR, module)
    if os.path.exists(main_dir):
        os.rmdir(main_dir)


def unstub_playbook_file(module):
    playbook_file = '{0}/integration/{1}.yaml'.format(BASE_DIR, module)
    if os.path.exists(playbook_file):
        os.remove(playbook_file)


def unstub_library_file(module, extension):
    library_file = '{0}/ansible_collections/f5networks/f5_bigip/plugins/modules/{1}{2}'.format(BASE_DIR, module, extension)
    if os.path.exists(library_file):
        os.remove(library_file)


def unstub_unit_test_file(module, extension):
    test_dir_path = '{0}/ansible_collections/f5networks/f5_bigip/tests/modules/network/f5/'.format(BASE_DIR)
    if not os.path.exists(test_dir_path):
        os.makedirs(test_dir_path)
    test_file = '{0}/ansible_collections/f5networks/f5_bigip/tests/modules/network/f5/test_{1}{2}'.format(
        BASE_DIR, module, extension
    )
    if os.path.exists(test_file):
        os.remove(test_file)
