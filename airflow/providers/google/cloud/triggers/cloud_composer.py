#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from __future__ import annotations

import asyncio
from typing import Any, Sequence

from airflow.exceptions import AirflowException
from airflow.providers.google.cloud.hooks.cloud_composer import CloudComposerAsyncHook
from airflow.triggers.base import BaseTrigger, TriggerEvent


class CloudComposerExecutionTrigger(BaseTrigger):
    """The trigger handles the async communication with the Google Cloud Composer."""

    def __init__(
        self,
        project_id: str,
        region: str,
        operation_name: str,
        gcp_conn_id: str = "google_cloud_default",
        impersonation_chain: str | Sequence[str] | None = None,
        pooling_period_seconds: int = 30,
    ):
        super().__init__()
        self.project_id = project_id
        self.region = region
        self.operation_name = operation_name
        self.gcp_conn_id = gcp_conn_id
        self.impersonation_chain = impersonation_chain
        self.pooling_period_seconds = pooling_period_seconds

        self.gcp_hook = CloudComposerAsyncHook(
            gcp_conn_id=self.gcp_conn_id,
            impersonation_chain=self.impersonation_chain,
        )

    def serialize(self) -> tuple[str, dict[str, Any]]:
        return (
            "airflow.providers.google.cloud.triggers.cloud_composer.CloudComposerExecutionTrigger",
            {
                "project_id": self.project_id,
                "region": self.region,
                "operation_name": self.operation_name,
                "gcp_conn_id": self.gcp_conn_id,
                "impersonation_chain": self.impersonation_chain,
                "pooling_period_seconds": self.pooling_period_seconds,
            },
        )

    async def run(self):
        while True:
            operation = await self.gcp_hook.get_operation(operation_name=self.operation_name)
            if operation.done:
                break
            elif operation.error.message:
                raise AirflowException(f"Cloud Composer Environment error: {operation.error.message}")
            await asyncio.sleep(self.pooling_period_seconds)
        yield TriggerEvent(
            {
                "operation_name": operation.name,
                "operation_done": operation.done,
            }
        )


class CloudComposerAirflowCLICommandTrigger(BaseTrigger):
    """The trigger wait for the Airflow CLI command result."""

    def __init__(
        self,
        project_id: str,
        region: str,
        environment_id: str,
        execution_cmd_info: dict,
        gcp_conn_id: str = "google_cloud_default",
        impersonation_chain: str | Sequence[str] | None = None,
        poll_interval: int = 10,
    ):
        super().__init__()
        self.project_id = project_id
        self.region = region
        self.environment_id = environment_id
        self.execution_cmd_info = execution_cmd_info
        self.gcp_conn_id = gcp_conn_id
        self.impersonation_chain = impersonation_chain
        self.poll_interval = poll_interval

        self.gcp_hook = CloudComposerAsyncHook(
            gcp_conn_id=self.gcp_conn_id,
            impersonation_chain=self.impersonation_chain,
        )

    def serialize(self) -> tuple[str, dict[str, Any]]:
        return (
            "airflow.providers.google.cloud.triggers.cloud_composer.CloudComposerAirflowCLICommandTrigger",
            {
                "project_id": self.project_id,
                "region": self.region,
                "environment_id": self.environment_id,
                "execution_cmd_info": self.execution_cmd_info,
                "gcp_conn_id": self.gcp_conn_id,
                "impersonation_chain": self.impersonation_chain,
                "poll_interval": self.poll_interval,
            },
        )

    async def run(self):
        try:
            result = await self.gcp_hook.wait_command_execution_result(
                project_id=self.project_id,
                region=self.region,
                environment_id=self.environment_id,
                execution_cmd_info=self.execution_cmd_info,
                poll_interval=self.poll_interval,
            )
        except AirflowException as ex:
            yield TriggerEvent(
                {
                    "status": "error",
                    "message": str(ex),
                }
            )
            return

        yield TriggerEvent(
            {
                "status": "success",
                "result": result,
            }
        )
        return
