# -*- coding: utf-8 -*-
"""Domain errors for report pipeline."""


class ReportError(Exception):
    """Base exception for report generation."""


class ConfigValidationError(ReportError):
    """Invalid config or profile meta."""


class DataReadError(ReportError):
    """Failed to read required data source."""


class DataSchemaError(ReportError):
    """Data schema mismatch."""


class IndicatorBuildError(ReportError):
    """Indicator build failure."""


class RenderError(ReportError):
    """Chart or html render failure."""


class OutputWriteError(ReportError):
    """Output write failure."""

