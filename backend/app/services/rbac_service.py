from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.models.user_role import UserRole
from app.rbac import ALL_PERMISSION_CODES, PERMISSION_DEFINITIONS, ROLE_ADMIN, ROLE_WRITER, SYSTEM_ROLE_DEFINITIONS


class RBACError(ValueError):
    pass


class RBACService:
    def __init__(self, db: Session):
        self.db = db

    def ensure_permissions(self) -> dict[str, Permission]:
        existing = {item.code: item for item in self.db.query(Permission).all()}
        for definition in PERMISSION_DEFINITIONS:
            row = existing.get(definition["code"])
            if row is None:
                row = Permission(
                    code=definition["code"],
                    name=definition["name"],
                    description=definition.get("description", ""),
                    is_system=True,
                )
                self.db.add(row)
                existing[definition["code"]] = row
            else:
                row.name = definition["name"]
                row.description = definition.get("description", "")
                row.is_system = True
        self.db.flush()
        return existing

    def ensure_account_system_roles(self, account_id: int) -> dict[str, Role]:
        account_id = int(account_id or 1)
        permissions = self.ensure_permissions()
        existing = {
            row.code: row
            for row in self.db.query(Role).filter(Role.account_id == account_id).all()
        }
        role_map: dict[str, Role] = {}
        for definition in SYSTEM_ROLE_DEFINITIONS:
            role = existing.get(definition["code"])
            if role is None:
                role = Role(
                    account_id=account_id,
                    code=definition["code"],
                    name=definition["name"],
                    description=definition.get("description", ""),
                    status="active",
                    is_system=True,
                )
                self.db.add(role)
            else:
                role.name = definition["name"]
                role.description = definition.get("description", "")
                role.status = "active"
                role.is_system = True
            role_map[definition["code"]] = role
        self.db.flush()

        role_ids = [role.id for role in role_map.values()]
        existing_links = defaultdict(set)
        if role_ids:
            rows = self.db.query(RolePermission).filter(RolePermission.role_id.in_(role_ids)).all()
            for row in rows:
                existing_links[int(row.role_id)].add(int(row.permission_id))

        for definition in SYSTEM_ROLE_DEFINITIONS:
            role = role_map[definition["code"]]
            target_ids = {permissions[code].id for code in definition["permissions"] if code in permissions}
            current_ids = existing_links.get(int(role.id), set())
            for perm_id in target_ids - current_ids:
                self.db.add(RolePermission(role_id=role.id, permission_id=perm_id))
            if current_ids - target_ids:
                self.db.query(RolePermission).filter(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id.in_(list(current_ids - target_ids)),
                ).delete(synchronize_session=False)
        self.db.flush()
        return role_map

    def ensure_all_accounts_system_roles(self) -> None:
        account_ids = [account.id for account in self.db.query(Account.id).all()]
        if not account_ids:
            account_ids = [1]
        for account_id in account_ids:
            self.ensure_account_system_roles(int(account_id or 1))
        self.db.flush()

    def backfill_user_roles_from_legacy(self) -> None:
        self.ensure_all_accounts_system_roles()
        existing_user_ids = {user_id for (user_id,) in self.db.query(UserRole.user_id).all()}
        role_rows = self.db.query(Role).all()
        role_map = {(int(role.account_id or 1), role.code): role for role in role_rows}

        for user in self.db.query(User).order_by(User.id.asc()).all():
            if user.id in existing_user_ids:
                continue
            desired_code = (user.role or ROLE_WRITER).strip() or ROLE_WRITER
            role = role_map.get((int(user.account_id or 1), desired_code))
            if role is None:
                role = role_map.get((int(user.account_id or 1), ROLE_WRITER))
            if role is None:
                continue
            self.db.add(UserRole(user_id=user.id, role_id=role.id))
        self.db.flush()

        for user in self.db.query(User).order_by(User.id.asc()).all():
            self.sync_legacy_role_field(user)
        self.db.flush()

    def list_permissions(self) -> list[Permission]:
        self.ensure_permissions()
        self.db.flush()
        return self.db.query(Permission).order_by(Permission.code.asc()).all()

    def list_roles(self, account_id: int) -> list[Role]:
        account_id = int(account_id or 1)
        self.ensure_account_system_roles(account_id)
        self.db.flush()
        return (
            self.db.query(Role)
            .filter(Role.account_id == account_id)
            .order_by(Role.is_system.desc(), Role.created_at.asc(), Role.id.asc())
            .all()
        )

    def role_permission_codes(self, roles: list[Role]) -> dict[int, list[str]]:
        role_ids = [role.id for role in roles]
        mapping: dict[int, list[str]] = {int(role.id): [] for role in roles}
        if not role_ids:
            return mapping
        rows = (
            self.db.query(RolePermission.role_id, Permission.code)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .filter(RolePermission.role_id.in_(role_ids))
            .order_by(Permission.code.asc())
            .all()
        )
        for role_id, code in rows:
            mapping[int(role_id)].append(str(code))
        return mapping

    def serialize_role(self, role: Role, permission_codes: list[str]) -> dict[str, Any]:
        return {
            "id": role.id,
            "account_id": role.account_id,
            "code": role.code,
            "role": role.code,
            "name": role.name,
            "description": role.description or "",
            "status": role.status,
            "is_system": bool(role.is_system),
            "permissions": permission_codes,
        }

    def get_user_roles(self, user: User) -> list[Role]:
        roles = (
            self.db.query(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .filter(
                UserRole.user_id == user.id,
                Role.account_id == user.account_id,
                Role.status == "active",
            )
            .order_by(Role.is_system.desc(), Role.created_at.asc(), Role.id.asc())
            .all()
        )
        if roles:
            return roles
        self.ensure_account_system_roles(int(user.account_id or 1))
        legacy_code = (user.role or ROLE_WRITER).strip() or ROLE_WRITER
        fallback = self.get_role_by_code(int(user.account_id or 1), legacy_code) or self.get_role_by_code(int(user.account_id or 1), ROLE_WRITER)
        if fallback is not None:
            self.db.add(UserRole(user_id=user.id, role_id=fallback.id))
            self.db.flush()
            return [fallback]
        return []

    def get_role_by_code(self, account_id: int, code: str) -> Role | None:
        return (
            self.db.query(Role)
            .filter(
                Role.account_id == int(account_id or 1),
                Role.code == (code or "").strip(),
            )
            .first()
        )

    def get_user_role_codes(self, user: User) -> list[str]:
        return [role.code for role in self.get_user_roles(user)]

    def get_user_permissions(self, user: User) -> list[str]:
        roles = self.get_user_roles(user)
        if not roles:
            return []
        role_ids = [role.id for role in roles]
        rows = (
            self.db.query(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .filter(RolePermission.role_id.in_(role_ids))
            .distinct()
            .order_by(Permission.code.asc())
            .all()
        )
        return [str(code) for (code,) in rows]

    def get_primary_role_code(self, user: User, role_codes: list[str] | None = None) -> str:
        codes = list(role_codes or self.get_user_role_codes(user))
        legacy = (user.role or "").strip()
        if legacy and legacy in codes:
            return legacy
        if ROLE_ADMIN in codes:
            return ROLE_ADMIN
        if codes:
            return codes[0]
        return legacy or ROLE_WRITER

    def attach_user_access_context(self, user: User) -> User:
        role_codes = self.get_user_role_codes(user)
        permission_codes = self.get_user_permissions(user)
        setattr(user, "_role_codes", role_codes)
        setattr(user, "_permission_codes", permission_codes)
        setattr(user, "_primary_role", self.get_primary_role_code(user, role_codes))
        return user

    def sync_legacy_role_field(self, user: User) -> str:
        primary_role = self.get_primary_role_code(user)
        if user.role != primary_role:
            user.role = primary_role
        return primary_role

    def create_role(
        self,
        *,
        account_id: int,
        code: str,
        name: str,
        description: str,
        permission_codes: list[str],
    ) -> Role:
        cleaned_code = (code or "").strip()
        cleaned_name = (name or "").strip()
        if not cleaned_code:
            raise RBACError("角色编码不能为空")
        if not cleaned_name:
            raise RBACError("角色名称不能为空")
        if self.get_role_by_code(account_id, cleaned_code):
            raise RBACError("角色编码已存在")
        role = Role(
            account_id=int(account_id or 1),
            code=cleaned_code,
            name=cleaned_name,
            description=(description or "").strip(),
            status="active",
            is_system=False,
        )
        self.db.add(role)
        self.db.flush()
        self.set_role_permissions(role, permission_codes)
        self.db.flush()
        return role

    def update_role(
        self,
        role: Role,
        *,
        name: str,
        description: str,
        status: str,
    ) -> Role:
        if role.is_system:
            raise RBACError("系统角色不允许修改基础信息")
        cleaned_name = (name or "").strip()
        if not cleaned_name:
            raise RBACError("角色名称不能为空")
        cleaned_status = (status or "active").strip().lower()
        if cleaned_status not in {"active", "disabled"}:
            raise RBACError("角色状态非法")
        role.name = cleaned_name
        role.description = (description or "").strip()
        role.status = cleaned_status
        self.db.flush()
        return role

    def set_role_permissions(self, role: Role, permission_codes: list[str]) -> None:
        valid_codes = {item.code: item for item in self.list_permissions()}
        cleaned_codes = sorted({(item or "").strip() for item in permission_codes if (item or "").strip()})
        invalid = [code for code in cleaned_codes if code not in valid_codes]
        if invalid:
            raise RBACError(f"存在非法权限: {', '.join(invalid)}")
        target_ids = {valid_codes[code].id for code in cleaned_codes}
        current_rows = self.db.query(RolePermission).filter(RolePermission.role_id == role.id).all()
        current_ids = {int(row.permission_id) for row in current_rows}
        for perm_id in target_ids - current_ids:
            self.db.add(RolePermission(role_id=role.id, permission_id=perm_id))
        if current_ids - target_ids:
            self.db.query(RolePermission).filter(
                RolePermission.role_id == role.id,
                RolePermission.permission_id.in_(list(current_ids - target_ids)),
            ).delete(synchronize_session=False)
        self.db.flush()

    def delete_role(self, role: Role) -> None:
        if role.is_system:
            raise RBACError("系统角色不允许删除")
        user_count = self.db.query(UserRole).filter(UserRole.role_id == role.id).count()
        if user_count > 0:
            raise RBACError("角色仍有绑定用户，无法删除")
        self.db.query(RolePermission).filter(RolePermission.role_id == role.id).delete(synchronize_session=False)
        self.db.delete(role)
        self.db.flush()

    def set_user_roles(self, user: User, role_codes: list[str]) -> list[Role]:
        requested = sorted({(code or "").strip() for code in role_codes if (code or "").strip()})
        if not requested:
            raise RBACError("至少需要分配一个角色")
        roles = (
            self.db.query(Role)
            .filter(
                Role.account_id == user.account_id,
                Role.code.in_(requested),
                Role.status == "active",
            )
            .order_by(Role.is_system.desc(), Role.created_at.asc(), Role.id.asc())
            .all()
        )
        found_codes = {role.code for role in roles}
        missing = [code for code in requested if code not in found_codes]
        if missing:
            raise RBACError(f"角色不存在或已禁用: {', '.join(missing)}")

        self.db.query(UserRole).filter(UserRole.user_id == user.id).delete(synchronize_session=False)
        for role in roles:
            self.db.add(UserRole(user_id=user.id, role_id=role.id))
        self.db.flush()
        self.sync_legacy_role_field(user)
        self.db.flush()
        return roles

    def remap_user_roles_for_account_change(self, user: User, target_account_id: int) -> list[Role]:
        current_codes = self.get_user_role_codes(user)
        self.db.query(UserRole).filter(UserRole.user_id == user.id).delete(synchronize_session=False)
        self.ensure_account_system_roles(target_account_id)
        target_roles = []
        for code in current_codes:
            role = self.get_role_by_code(target_account_id, code)
            if role is not None and role.status == "active":
                target_roles.append(role)
        if not target_roles:
            fallback = self.get_role_by_code(target_account_id, ROLE_WRITER)
            if fallback is not None:
                target_roles.append(fallback)
        for role in target_roles:
            self.db.add(UserRole(user_id=user.id, role_id=role.id))
        self.db.flush()
        self.sync_legacy_role_field(user)
        self.db.flush()
        return target_roles


def user_has_role(user: User, role_code: str) -> bool:
    codes = set(getattr(user, "_role_codes", []) or [])
    if codes:
        return role_code in codes
    legacy = (getattr(user, "role", "") or "").strip()
    return legacy == role_code