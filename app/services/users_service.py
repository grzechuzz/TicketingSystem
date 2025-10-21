from sqlalchemy.ext.asyncio import AsyncSession
from app.core.pagination import PageDTO
from app.domain.users.schemas import AdminUsersQueryDTO, PasswordChangeDTO, AdminUserListItemDTO, \
    RoleReadDTO, UserRolesUpdateDTO
from app.domain.users import crud as crud
from app.domain.users.models import User
from app.core.auditing import AuditSpan
from app.core.security import verify_password, hash_password
from app.domain.exceptions import Unauthorized, InvalidInput, NotFound, Forbidden


async def list_users_admin(db: AsyncSession, query: AdminUsersQueryDTO) -> PageDTO[AdminUserListItemDTO]:
    users, total = await crud.list_all_users(
        db,
        page=query.page,
        page_size=query.page_size,
        email=query.email,
        name=query.name,
        role=query.role,
        is_active=query.is_active,
        created_from=query.created_from,
        created_to=query.created_to,
    )

    items = [AdminUserListItemDTO.model_validate(u, from_attributes=True) for u in users]

    return PageDTO[AdminUserListItemDTO](items=items, total=total, page=query.page, page_size=query.page_size)


async def change_password(db: AsyncSession, user: User, schema: PasswordChangeDTO) -> None:
    async with AuditSpan(scope="USERS", action="CHANGE_PASSWORD", object_type="user", object_id=user.id):
        if not verify_password(schema.old_password.get_secret_value(), user.password_hash):
            raise Unauthorized("Old password is incorrect", ctx={"user_id": user.id})
        if verify_password(schema.new_password.get_secret_value(), user.password_hash):
            raise InvalidInput("New password must be different from the current one", ctx={"user_id": user.id})
        user.password_hash = hash_password(schema.new_password.get_secret_value())
        await db.flush()


async def update_user_roles(db: AsyncSession, user_id: int, schema: UserRolesUpdateDTO) -> User:
    async with AuditSpan(
            scope="USERS",
            action="SET_ROLES",
            object_type="user",
            object_id=user_id,
            meta={"requested_roles": schema.roles}
    ):
        user = await crud.get_user_by_id(user_id, db)
        if not user:
            raise NotFound("User not found", ctx={"user_id": user_id})

        current = {r.name for r in user.roles}
        if "ADMIN" in current:
            raise Forbidden("Access denied", ctx={"user_id": user_id})

        target_names = set(schema.roles)
        if not target_names:
            raise InvalidInput("No roles specified", ctx={"user_id": user_id})

        roles = await crud.get_roles_by_names(list(target_names), db)
        found = {r.name for r in roles}
        missing = target_names - found
        if missing:
            raise InvalidInput("Unknown roles requested", ctx={"missing": sorted(missing)})

        user.roles = roles
        await db.flush()
        await db.refresh(user)

        return user
