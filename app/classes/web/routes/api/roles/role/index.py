from jsonschema import ValidationError, validate
import orjson
from peewee import DoesNotExist, IntegrityError
from app.classes.models.crafty_permissions import EnumPermissionsCrafty
from app.classes.web.base_api_handler import BaseApiHandler

modify_role_schema = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1,
            "pattern": r"^[^,\[\]]*$",
        },
        "servers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "minimum": 1,
                    },
                    "permissions": {
                        "type": "string",
                        "pattern": r"^[01]{8}$",  # 8 bits, see EnumPermissionsServer
                    },
                },
                "required": ["server_id", "permissions"],
            },
        },
        "manager": {"type": ["integer", "null"]},
    },
    "additionalProperties": False,
    "minProperties": 1,
}

basic_modify_role_schema = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1,
        },
        "servers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "minimum": 1,
                    },
                    "permissions": {
                        "type": "string",
                        "pattern": "^[01]{8}$",  # 8 bits, see EnumPermissionsServer
                    },
                },
                "required": ["server_id", "permissions"],
            },
        },
    },
    "additionalProperties": False,
    "minProperties": 1,
}


class ApiRolesRoleIndexHandler(BaseApiHandler):
    def get(self, role_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        (
            _,
            exec_user_permissions_crafty,
            _,
            superuser,
            _,
            _,
        ) = auth_data

        if (
            not superuser
            and EnumPermissionsCrafty.ROLES_CONFIG not in exec_user_permissions_crafty
        ):
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        try:
            self.finish_json(
                200,
                {"status": "ok", "data": self.controller.roles.get_role(role_id)},
            )
        except DoesNotExist:
            self.finish_json(404, {"status": "error", "error": "ROLE_NOT_FOUND"})

    def delete(self, role_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        (
            _,
            _,
            _,
            superuser,
            user,
            _,
        ) = auth_data
        role = self.controller.roles.get_role(role_id)
        if (
            str(role.get("manager", "no manager found")) != str(auth_data[4]["user_id"])
            and not superuser
        ):
            return self.finish_json(400, {"status": "error", "error": "NOT_AUTHORIZED"})

        self.controller.roles.remove_role(role_id)

        self.finish_json(
            200,
            {"status": "ok", "data": role_id},
        )

        self.controller.management.add_to_audit_log(
            user["user_id"],
            f"deleted role with ID {role_id}",
            server_id=None,
            source_ip=self.get_remote_ip(),
        )

    def patch(self, role_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return
        (
            _,
            exec_user_permissions_crafty,
            _,
            superuser,
            user,
            _,
        ) = auth_data

        role = self.controller.roles.get_role(role_id)
        if not superuser and (
            user["user_id"] != role["manager"]
            or EnumPermissionsCrafty.ROLES_CONFIG not in exec_user_permissions_crafty
        ):
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "NOT_AUTHORIZED",
                    "error_data": "Not Authorized",
                },
            )

        try:
            data = orjson.loads(self.request.body)
        except orjson.JSONDecodeError as e:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )

        try:
            if auth_data[4]["superuser"]:
                validate(data, modify_role_schema)
            else:
                validate(data, basic_modify_role_schema)
        except ValidationError as e:
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": str(e),
                },
            )

        manager = data.get(
            "manager", self.controller.roles.get_role(role_id)["manager"]
        )
        if manager == self.controller.users.get_id_by_name("system") or manager == 0:
            manager = None

        try:
            self.controller.roles.update_role_advanced(
                role_id,
                data.get("name", None),
                data.get("servers", None),
                manager,
            )
        except DoesNotExist:
            return self.finish_json(404, {"status": "error", "error": "ROLE_NOT_FOUND"})
        except IntegrityError:
            return self.finish_json(
                404, {"status": "error", "error": "ROLE_NAME_EXISTS"}
            )
        self.controller.management.add_to_audit_log(
            user["user_id"],
            f"modified role with ID {role_id}",
            server_id=None,
            source_ip=self.get_remote_ip(),
        )

        self.finish_json(
            200,
            {"status": "ok"},
        )
