"""Admin-Oberfläche unter /admin – nur lesend, vorerst ohne Login."""

from typing import ClassVar

from fastapi import FastAPI
from sqladmin import Admin, ModelView
from sqlalchemy.engine import Engine

from models import Account, Emission, Redemption


class AccountAdmin(ModelView, model=Account):
    name_plural = "Accounts"
    column_list = (
        Account.username,
        Account.balance,
        Account.u,
        Account.wallet_id,
        Account.created_at,
        Account.account_id,
    )
    column_searchable_list = (Account.username,)
    column_sortable_list = (Account.username, Account.balance, Account.created_at)
    column_default_sort = (Account.created_at, True)
    column_formatters: ClassVar = {
        Account.u: lambda account, _: account.u.hex(),
        Account.wallet_id: lambda account, _: account.wallet_id.hex(),
    }
    column_formatters_detail = column_formatters
    can_create = can_edit = can_delete = False


class EmissionAdmin(ModelView, model=Emission):
    name_plural = "Emissions"
    column_list = (Emission.id,)
    can_create = can_edit = can_delete = False


class RedemptionAdmin(ModelView, model=Redemption):
    name_plural = "Redemptions"
    column_list = (Redemption.id,)
    can_create = can_edit = can_delete = False


def setup_admin(app: FastAPI, engine: Engine) -> None:
    admin = Admin(app, engine)
    admin.add_view(AccountAdmin)
    admin.add_view(EmissionAdmin)
    admin.add_view(RedemptionAdmin)
