"""How each span was anchored is counted, so that the share anchored by a method that may have chosen the wrong place is a measured number.

Every anchor is counted, the sure ones too: a count of the doubtful ones
alone has nothing to be a share of.
"""

import logging
from collections import Counter
from typing import get_args

import pytest
from counted import counted
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from telemetry_rows import worker_metrics
from xynolog.annotations import AnchorMethod

from xynolog_worker.detection.anchor_audit import note_anchor
from xynolog_worker.telemetry import DetectionLabel

ANCHORS = "xynolog.detection.anchors"

# The SDK states the ways a span is found as a described Literal: its values are the Literal's.
(_METHOD, _) = get_args(AnchorMethod.__value__)
METHODS = get_args(_METHOD)


def anchors(reader: InMemoryMetricReader) -> Counter[tuple[object, ...]]:
    """How many anchors have been counted so far, by what was anchored and how. A point carries those and its knowledge base."""
    return counted(reader, ANCHORS, "detection.label", "anchor.method")


def warnings_of(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [record for record in caplog.records if record.name == "xynolog_worker"]


@pytest.mark.parametrize("method", ["unique-match", "context-recovered"])
def test_an_anchor_that_is_sure_is_counted_and_nothing_is_said_of_it(
    method: AnchorMethod, metric_reader: InMemoryMetricReader, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="xynolog_worker")
    before = anchors(metric_reader)
    note_anchor("reference", "Paris", method)
    assert anchors(metric_reader) - before == Counter({("reference", method): 1})
    assert warnings_of(caplog) == []


@pytest.mark.parametrize("method", ["first-of-many", "fuzzy-match"])
def test_an_anchor_that_may_be_the_wrong_place_is_counted_and_warned_of(
    method: AnchorMethod, metric_reader: InMemoryMetricReader, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="xynolog_worker")
    before = anchors(metric_reader)
    note_anchor("comment", "the engine", method)
    assert anchors(metric_reader) - before == Counter({("comment", method): 1})
    (warned,) = warnings_of(caplog)
    assert warned.levelno == logging.WARNING
    assert warned.getMessage() == "Annotation anchored via degraded method"
    assert {key: vars(warned)[key] for key in ("label", "text", "anchorMethod")} == {
        "label": "comment",
        "text": "the engine",
        "anchorMethod": method,
    }


def test_what_is_counted_is_what_the_table_lists(metric_reader: InMemoryMetricReader) -> None:
    (row,) = worker_metrics(ANCHORS).values()
    assert row.name == ANCHORS
    assert row.instrument == "counter"
    listed = {attribute.key: attribute.values for attribute in row.attributes}
    # Every kind of mark job by every way a span is found: the two lists are the worker's own and the SDK's, and each is the table's.
    assert listed == {
        "detection.label": list(get_args(DetectionLabel.__value__)),
        "anchor.method": list(METHODS),
        "xynolog.kb": None,
    }
    assert all(attribute.only is None for attribute in row.attributes)

    before = anchors(metric_reader)
    for label in get_args(DetectionLabel.__value__):
        for method in METHODS:
            note_anchor(label, "x", method)
    assert anchors(metric_reader) - before == Counter(
        {(label, method): 1 for label in get_args(DetectionLabel.__value__) for method in METHODS}
    )
