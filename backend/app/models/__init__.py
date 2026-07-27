# app/models/__init__.py
# 모든 모델들을 이곳에 명시적으로 노출시켜 Alembic이 이들을 인지하여 autogenerate할 수 있도록 합니다.

from app.db.base import Base  # Base 클래스 포함
from app.models.user import User
from app.models.customer import Customer
from app.models.customer_contact import CustomerContact
from app.models.address import Address
from app.models.project import Project
from app.models.server_inventory import ServerInventory
from app.models.part_inventory import PartInventory
from app.models.part_usage import PartUsage
from app.models.warranty import Warranty
from app.models.audit_log import AuditLog
from app.models.approval import Approval
