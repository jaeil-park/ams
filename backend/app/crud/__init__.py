# app/crud/__init__.py
# CRUD 인스턴스들을 모아서 한곳에서 import할 수 있게 합니다.

from app.crud.base import CRUDBase
from app.models.user import User
from app.models.customer import Customer
from app.models.project import Project
from app.models.server_inventory import ServerInventory
from app.models.part_inventory import PartInventory
from app.models.part_usage import PartUsage
from app.models.address import Address
from app.models.warranty import Warranty
from app.models.audit_log import AuditLog
from app.models.approval import Approval

from typing import Any

# 기본 CRUD 인스턴스들
user = CRUDBase[User, Any, Any](User)
customer = CRUDBase[Customer, Any, Any](Customer)
project = CRUDBase[Project, Any, Any](Project)
server_inventory = CRUDBase[ServerInventory, Any, Any](ServerInventory)
part_inventory = CRUDBase[PartInventory, Any, Any](PartInventory)
part_usage = CRUDBase[PartUsage, Any, Any](PartUsage)
address = CRUDBase[Address, Any, Any](Address)
warranty = CRUDBase[Warranty, Any, Any](Warranty)
audit_log = CRUDBase[AuditLog, Any, Any](AuditLog)
approval = CRUDBase[Approval, Any, Any](Approval)
