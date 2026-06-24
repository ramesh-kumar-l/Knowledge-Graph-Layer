"""OpenTelemetry distributed tracing — graceful no-op if SDK is not installed.

Install: pip install opentelemetry-sdk opentelemetry-instrumentation-fastapi
         pip install opentelemetry-exporter-otlp-proto-http  # for OTLP export

Environment variables:
  OTEL_SERVICE_NAME            — service name in traces (default: scp-knowledge-graph)
  OTEL_EXPORTER_OTLP_ENDPOINT — OTLP collector URL (e.g. http://localhost:4318)
                                  If unset, spans are created but not exported.
"""
import logging
import os
from contextlib import contextmanager
from typing import Any, Generator

log = logging.getLogger(__name__)

_SERVICE = os.getenv("OTEL_SERVICE_NAME", "scp-knowledge-graph")
_OTLP = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
_tracer: Any = None


class _NoOpSpan:
    """Stub span used when OTel SDK is not available."""
    def __enter__(self): return self
    def __exit__(self, *_): pass
    def set_attribute(self, *_): pass
    def set_status(self, *_): pass
    def record_exception(self, *_): pass


class _NoOpTracer:
    @contextmanager
    def start_as_current_span(self, name: str, **__) -> Generator[_NoOpSpan, None, None]:
        yield _NoOpSpan()


def setup_tracing(app: Any = None) -> None:
    """Initialize OTel SDK. Safe to call even when SDK is absent."""
    global _tracer
    try:
        from opentelemetry import trace  # type: ignore[import]
        from opentelemetry.sdk.resources import Resource  # type: ignore[import]
        from opentelemetry.sdk.trace import TracerProvider  # type: ignore[import]
        from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore[import]

        resource = Resource.create({"service.name": _SERVICE})
        provider = TracerProvider(resource=resource)

        if _OTLP:
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # type: ignore[import]
                    OTLPSpanExporter,
                )
                provider.add_span_processor(
                    BatchSpanProcessor(OTLPSpanExporter(endpoint=_OTLP))
                )
                log.info("tracing.otlp_enabled endpoint=%s", _OTLP)
            except ImportError:
                log.warning(
                    "tracing.otlp_not_available -- "
                    "pip install opentelemetry-exporter-otlp-proto-http"
                )

        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer(_SERVICE)
        log.info("tracing.initialized service=%s", _SERVICE)

        if app is not None:
            try:
                from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # type: ignore[import]
                FastAPIInstrumentor.instrument_app(app)
                log.info("tracing.fastapi_instrumented")
            except ImportError:
                log.warning(
                    "tracing.fastapi_instrumentor_not_available -- "
                    "pip install opentelemetry-instrumentation-fastapi"
                )
    except ImportError:
        log.info("tracing.disabled — pip install opentelemetry-sdk to enable")


def get_tracer() -> Any:
    return _tracer if _tracer is not None else _NoOpTracer()
