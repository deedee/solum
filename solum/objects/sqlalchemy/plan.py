# Copyright 2014 - Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sqlalchemy

from solum.common import exception
from solum.objects import plan as abstract
from solum.objects.sqlalchemy import models as sql


class Plan(sql.Base, abstract.Plan):
    """Represent a plan in sqlalchemy."""

    __resource__ = 'plans'
    __tablename__ = 'plan'
    __table_args__ = sql.table_args()

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True,
                           autoincrement=True)
    uuid = sqlalchemy.Column(sqlalchemy.String(36))
    project_id = sqlalchemy.Column(sqlalchemy.String(36))
    user_id = sqlalchemy.Column(sqlalchemy.String(36))
    glance_id = sqlalchemy.Column(sqlalchemy.String(36))
    name = sqlalchemy.Column(sqlalchemy.String(255))
    description = sqlalchemy.Column(sqlalchemy.String(255))
    raw_content = sqlalchemy.Column(sqlalchemy.Text)

    @classmethod
    def _raise_duplicate_object(cls, e, self):
        raise exception.ResourceExists(name='plan')


class PlanList(abstract.PlanList):
    """Represent a list of plans in sqlalchemy."""

    @classmethod
    def get_all(cls, context):
        return PlanList(sql.model_query(context, Plan))
