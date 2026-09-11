from __future__ import annotations

from app.services.ocr import cache


def test_key_for_differs_by_extractor_mode():
    # Two tenants with different OCR_EXTRACTOR overrides uploading the same bytes (or the
    # same tenant before/after an admin changes its override) must not share a cache entry —
    # otherwise one could get back an `extraction` computed under someone else's mode.
    data = b"same bytes"
    k_none = cache.key_for(data, "es", 5, None)
    k_rules = cache.key_for(data, "es", 5, "rules")
    k_llm = cache.key_for(data, "es", 5, "llm")

    assert len({k_none, k_rules, k_llm}) == 3


def test_key_for_stable_for_same_inputs():
    data = b"same bytes"
    assert cache.key_for(data, "es", 5, "rules") == cache.key_for(data, "es", 5, "rules")


def test_key_for_still_varies_by_lang_and_max_pages():
    data = b"same bytes"
    assert cache.key_for(data, "es", 5, "rules") != cache.key_for(data, "en", 5, "rules")
    assert cache.key_for(data, "es", 5, "rules") != cache.key_for(data, "es", 3, "rules")
