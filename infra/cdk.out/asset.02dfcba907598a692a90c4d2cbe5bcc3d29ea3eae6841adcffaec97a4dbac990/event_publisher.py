"""
CDSS Shared Utilities — EventBridge Publisher
Publishes events for async inter-agent communication.
"""

import json
import logging
from typing import Optional
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

from .config import AWS_REGION, EVENT_BUS_NAME

logger = logging.getLogger(__name__)


class EventPublisher:
    """Publishes events to EventBridge for async agent-to-agent messaging."""

    def __init__(self, bus_name: Optional[str] = None):
        self.bus_name = bus_name or EVENT_BUS_NAME
        self._client = boto3.client("events", region_name=AWS_REGION)

    def publish(
        self,
        source_agent: str,
        event_type: str,
        detail: dict,
        target_agent: Optional[str] = None,
    ) -> dict:
        """
        Publish an event to EventBridge.

        Args:
            source_agent: Name of the agent publishing the event
            event_type: Type of event (e.g., 'PatientUpdated', 'SurgeryScheduled')
            detail: Event payload
            target_agent: Optional target agent for routing

        Returns:
            EventBridge PutEvents response
        """
        detail["source_agent"] = source_agent
        detail["event_type"] = event_type
        detail["timestamp"] = datetime.utcnow().isoformat()

        if target_agent:
            detail["target_agent"] = target_agent

        entry = {
            "Source": f"cdss.agent.{source_agent}",
            "DetailType": event_type,
            "Detail": json.dumps(detail),
            "EventBusName": self.bus_name,
        }

        try:
            response = self._client.put_events(Entries=[entry])
            failed = response.get("FailedEntryCount", 0)
            if failed > 0:
                logger.error(f"Failed to publish {failed} events: {response['Entries']}")
            else:
                logger.info(f"Published event: {source_agent} → {event_type}")
            return response
        except ClientError as e:
            logger.error(f"EventBridge publish failed: {e}")
            raise

    def publish_patient_update(self, patient_id: str, update_type: str, data: dict) -> dict:
        """Convenience method for patient-related events."""
        return self.publish(
            source_agent="patient",
            event_type="PatientUpdated",
            detail={
                "patient_id": patient_id,
                "update_type": update_type,
                **data,
            },
        )

    def publish_surgery_event(self, surgery_id: str, status: str, data: dict) -> dict:
        """Convenience method for surgery-related events."""
        return self.publish(
            source_agent="surgery_planning",
            event_type="SurgeryStatusChanged",
            detail={
                "surgery_id": surgery_id,
                "status": status,
                **data,
            },
        )

    def publish_alert(self, alert_type: str, severity: str, message: str, patient_id: Optional[str] = None) -> dict:
        """Publish a clinical alert event."""
        return self.publish(
            source_agent="engagement",
            event_type="ClinicalAlert",
            detail={
                "alert_type": alert_type,
                "severity": severity,
                "message": message,
                "patient_id": patient_id,
            },
            target_agent="engagement",
        )
