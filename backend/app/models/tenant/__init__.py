"""Tenant schema models package — imported to register all models on TenantBase"""

from app.models.tenant.user import User
from app.models.tenant.otp_cache import OTPCache
from app.models.tenant.user_session import UserSession
from app.models.tenant.plant import Plant
from app.models.tenant.plant_membership import PlantMembership
from app.models.tenant.offsite_access_grant import OffsiteAccessGrant
from app.models.tenant.geofence_check import GeofenceCheck
from app.models.tenant.department import Department
from app.models.tenant.production_line import ProductionLine
from app.models.tenant.product_model import ProductModel
from app.models.tenant.station import Station
from app.models.tenant.station_employee import StationEmployee
from app.models.tenant.characteristic import Characteristic
from app.models.tenant.sampling_instruction import SamplingInstruction
from app.models.tenant.sample import Sample
from app.models.tenant.measurement import Measurement
from app.models.tenant.spc_calculation import SPCCalculation
from app.models.tenant.violation import Violation
from app.models.tenant.alert import Alert
from app.models.tenant.knowledge_document import KnowledgeDocument
from app.models.tenant.document_chunk import DocumentChunk
from app.models.tenant.ai_conversation import AIConversation
from app.models.tenant.ai_message import AIMessage
from app.models.tenant.plant_subscription import PlantSubscription
from app.models.tenant.subscription_webhook import SubscriptionWebhook
from app.models.tenant.billing_history import BillingHistory
from app.models.tenant.station_metric import StationMetric
from app.models.tenant.company_usage import CompanyUsage
from app.models.tenant.audit_log import AuditLog

__all__ = [
    "User",
    "OTPCache",
    "UserSession",
    "Plant",
    "PlantMembership",
    "OffsiteAccessGrant",
    "GeofenceCheck",
    "Department",
    "ProductionLine",
    "ProductModel",
    "Station",
    "StationEmployee",
    "Characteristic",
    "SamplingInstruction",
    "Sample",
    "Measurement",
    "SPCCalculation",
    "Violation",
    "Alert",
    "KnowledgeDocument",
    "DocumentChunk",
    "AIConversation",
    "AIMessage",
    "PlantSubscription",
    "SubscriptionWebhook",
    "BillingHistory",
    "StationMetric",
    "CompanyUsage",
    "AuditLog",
]
