Ansible Collection f5_bigip
===========================


A collection focusing on managing F5 BIG-IP/BIG-IQ through declarative APIs such as AS3, DO, TS, and CFE. The collection does includes key imperative modules as well for managing some resources and operational tasks outside of declarative workflows. These would include actions such as saving config, backing up config, uploading secutity policies, uploading crts/keys, gathering info, etc.

|

This collection is not currently published to Galaxy while feedback is collected through issues within this repository. When a 1.0.0 release is ready, the collection will be released into Galaxy and Automation Hub.

|

**Note that this Collection is not currently intended to replace the existing |f5_modules| Collection.**


Install from Github
~~~~~~~~~~~~~~~~~~~

``ansible-galaxy collection install git@https://github.com/f5devcentral/f5_bigip.git``

|repoinstall|


Build and Install
~~~~~~~~~~~~~~~~~

* Clone this repository
* Change to the collection directory ``ansible_collections/f5networks/f5_bigip``
* Build the collection ``ansible-galaxy collection build``
* Copy the collection file created to your ansible working directory.
* Install the collection using the command below:

.. code:: shell

    ansible-galaxy collection install <collection name> -p ./collections
    e.g.
    ansible-galaxy collection install f5networks-f5_modules-devel.tar.gz -p ./collections

.. note::

   "-p" is the location in which the collection will be installed. This location should be defined in the path for
   ansible to search for collections. An example of this would be adding ``collections_paths = ./collections``
   to your **ansible.cfg**

Tips
~~~~

* You can leverage both this collection (f5_bigip) and the previous imperative collection (f5_modules) at the same time.
* If you are migrating from the imperative collection, you can leave the provider variables and reference them from the new httpapi connection variables:

.. code:: shell

   ansible_host: "{{ provider.server }}"
   ansible_user: "{{ provider.user }}"
   ansible_httpapi_password: "{{ provider.password }}"
   ansible_httpapi_port: "{{ provider.server_port }}"
   ansible_network_os: f5networks.f5_bigip.bigip
   ansible_httpapi_use_ssl: yes
   ansible_httpapi_validate_certs: "{{ provider.validate_certs }}"


.. |repoinstall| raw:: html

   <a href="https://docs.ansible.com/ansible/latest/user_guide/collections_using.html#installing-a-collection-from-a-git-repository" target="_blank">Git Install Docs</a>

.. |f5_modules| raw:: html

   <a href="https://galaxy.ansible.com/f5networks/f5_modules" target="_blank">f5_modules</a>