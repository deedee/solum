# Copyright 2014 - Rackspace Hosting
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""Solum Deployer Heat handler."""

import os
import time
import yaml

from oslo.config import cfg
from solum.common import clients
from solum import objects
from solum.openstack.common.gettextutils import _
from solum.openstack.common import log as logging


LOG = logging.getLogger(__name__)

STATES = (PENDING, BUILDING, ERROR, READY, ERROR_STACK_CREATE_FAILED) = (
    'PENDING', 'BUILDING', 'ERROR', 'READY', 'ERROR_STACK_CREATE_FAILED')

OPT_GROUP = cfg.OptGroup(name='deployer',
                         title='Options for the solum-deployer service')
SERVICE_OPTS = [
    cfg.IntOpt('max_attempts',
               default=2000,
               help=('Number of attempts to query the Heat stack for '
                     'finding out the status of the created stack and '
                     'getting url of the DU created in the stack')),
    cfg.IntOpt('wait_interval',
               default=1,
               help=('Sleep time interval between two attempts of querying '
                     'the Heat stack. This interval is in seconds.')),
    cfg.FloatOpt('growth_factor',
                 default=1.1,
                 help=('Factor by which sleep time interval increases. '
                       'This value should be >= 1.0')),
]

cfg.CONF.register_group(OPT_GROUP)
cfg.CONF.register_opts(SERVICE_OPTS, OPT_GROUP)


class Handler(object):
    def __init__(self):
        super(Handler, self).__init__()
        objects.load()

    def echo(self, ctxt, message):
        LOG.debug(_("%s") % message)

    def _get_template(self, template_flavor):
        proj_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..')
        templ = os.path.join(proj_dir, 'etc', 'solum', 'templates',
                             '%s.yaml' % template_flavor)
        with open(templ) as templ_file:
            template = templ_file.read()
        return template

    def deploy(self, ctxt, assembly_id, image_id):
        # TODO(asalkeld) support template flavors (maybe an autoscaling one)
        #                this could also be stored in glance.
        template_flavor = 'basic'
        template = self._get_template(template_flavor)

        osc = clients.OpenStackClients(ctxt)

        assem = objects.registry.Assembly.get_by_id(ctxt,
                                                    assembly_id)

        parameters = {'app_name': assem.name,
                      'image': image_id}
        created_stack = osc.heat().stacks.create(stack_name=assem.name,
                                                 template=template,
                                                 parameters=parameters)

        assem.status = BUILDING
        assem.save(ctxt)
        stack_id = created_stack['stack']['id']

        comp_description = 'Heat Stack %s' % (
            yaml.load(template).get('description'))
        objects.registry.Component.assign_and_create(ctxt, assem,
                                                     'Heat Stack',
                                                     comp_description,
                                                     created_stack['stack']
                                                     ['links'][0]['href'])

        self._update_assembly_status(ctxt, assem, osc, stack_id)

    def _update_assembly_status(self, ctxt, assem, osc, stack_id):

        wait_interval = cfg.CONF.deployer.wait_interval
        growth_factor = cfg.CONF.deployer.growth_factor
        got_stack_status = False

        for count in range(cfg.CONF.deployer.max_attempts):
            stack = osc.heat().stacks.get(stack_id)
            if stack.status == 'COMPLETE':
                host_url = self._parse_server_url(stack)
                if host_url is not None:
                    assem.status = READY
                    assem.application_uri = host_url
                    assem.save(ctxt)
                    got_stack_status = True
                    break
            elif stack.status == 'FAILED':
                assem.status = ERROR
                assem.save(ctxt)
                got_stack_status = True
                break

            time.sleep(wait_interval)
            wait_interval *= growth_factor

        if not got_stack_status:
            assem.status = ERROR_STACK_CREATE_FAILED
            assem.save(ctxt)

    def _parse_server_url(self, heat_output):
        """Parse server url from heat-stack-show output."""
        if 'outputs' in heat_output._info:
            return heat_output._info['outputs'][1]['output_value']
        return None