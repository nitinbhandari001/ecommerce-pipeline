"""Exception hierarchy for ecommerce-pipeline."""


class PipelineError(Exception):
    """Base exception for all pipeline errors."""


class ValidationError(PipelineError):
    """Order failed validation — contains list of error messages."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(f"Validation failed: {'; '.join(errors)}")


class InventoryError(PipelineError):
    """Inventory check failed."""


class AnomalyDetectionError(PipelineError):
    """Anomaly detection failed."""


class InvoiceError(PipelineError):
    """Invoice generation failed."""


class NotificationError(PipelineError):
    """Notification sending failed (non-fatal — logged and skipped)."""


class ShopifyError(PipelineError):
    """Shopify API request failed."""


class WebhookAuthError(PipelineError):
    """Webhook HMAC-SHA256 signature verification failed."""


class AIServiceError(PipelineError):
    """All configured LLM providers failed."""


class OrderNotFoundError(PipelineError):
    """Order ID not found in the order store."""
