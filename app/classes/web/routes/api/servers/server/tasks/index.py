# TODO: create and read

import json
import logging

from croniter import croniter
from jsonschema import ValidationError, validate
from app.classes.models.server_permissions import EnumPermissionsServer
from app.classes.web.base_api_handler import BaseApiHandler


logger = logging.getLogger(__name__)
new_task_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "enabled": {
            "type": "boolean",
            "default": True,
        },
        "action": {
            "type": "string",
        },
        "action_id": {
            "type": "string",
        },
        "interval": {"type": "integer"},
        "interval_type": {
            "type": "string",
            "enum": [
                # Basic tasks
                "hours",
                "minutes",
                "days",
                # Chain reaction tasks:
                "reaction",
                # CRON tasks:
                "",
            ],
        },
        "start_time": {"type": "string", "pattern": r"\d{1,2}:\d{1,2}"},
        "command": {"type": ["string", "null"]},
        "one_time": {"type": "boolean", "default": False},
        "cron_string": {"type": "string", "default": ""},
        "parent": {"type": ["integer", "null"]},
        "delay": {"type": "integer", "default": 0},
    },
    "additionalProperties": False,
    "minProperties": 1,
}


class ApiServersServerTasksIndexHandler(BaseApiHandler):
    def get(self, server_id: str, task_id: str):
        pass

    def post(self, server_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        try:
            data = json.loads(self.request.body)
        except json.decoder.JSONDecodeError as e:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )

        try:
            validate(data, new_task_schema)
        except ValidationError as e:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )

        if server_id not in [str(x["server_id"]) for x in auth_data[0]]:
            # if the user doesn't have access to the server, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})
        mask = self.controller.server_perms.get_lowest_api_perm_mask(
            self.controller.server_perms.get_user_permissions_mask(
                auth_data[4]["user_id"], server_id
            ),
            auth_data[5],
        )
        server_permissions = self.controller.server_perms.get_permissions(mask)
        if EnumPermissionsServer.SCHEDULE not in server_permissions:
            # if the user doesn't have Schedule permission, return an error
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})
        data["server_id"] = server_id
        if not data.get("start_time"):
            data["start_time"] = "00:00"

        # validate cron string
        if "cron_string" in data:
            if data["cron_string"] != "" and not croniter.is_valid(data["cron_string"]):
                return self.finish_json(
                    405,
                    {
                        "status": "error",
                        "error": self.helper.translation.translate(
                            "error",
                            "cronFormat",
                            self.controller.users.get_user_lang_by_id(
                                auth_data[4]["user_id"]
                            ),
                        ),
                    },
                )
        if "parent" not in data:
            data["parent"] = None
        if data.get("action_id"):
            backup_config = self.controller.management.get_backup_config(
                data["action_id"]
            )
            if backup_config["server_id"]["server_id"] != server_id:
                return self.finish_json(
                    405,
                    {
                        "status": "error",
                        "error": "Server ID Mismatch",
                    },
                )
        task_id = self.tasks_manager.schedule_job(data)

        self.controller.management.add_to_audit_log(
            auth_data[4]["user_id"],
            f"Edited server {server_id}: added schedule",
            server_id,
            self.get_remote_ip(),
        )
        self.tasks_manager.reload_schedule_from_db()

        self.finish_json(200, {"status": "ok", "data": {"schedule_id": task_id}})
