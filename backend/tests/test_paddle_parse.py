from __future__ import annotations

from app.services.ocr.engine import _parse_paddle_page


def test_parse_paddle_3x_dict_format():
    raw = [
        {
            "rec_texts": ["FACTURA", "Total 121"],
            "rec_scores": [0.99, 0.95],
            "rec_polys": [
                [[10, 10], [110, 10], [110, 30], [10, 30]],
                [[10, 40], [130, 40], [130, 60], [10, 60]],
            ],
        }
    ]
    lines = _parse_paddle_page(raw)
    assert [ln.text for ln in lines] == ["FACTURA", "Total 121"]
    assert lines[0].confidence == 0.99
    assert lines[1].box == [[10.0, 40.0], [130.0, 40.0], [130.0, 60.0], [10.0, 60.0]]


def test_parse_paddle_2x_list_format():
    raw = [[[[[0, 0], [50, 0], [50, 20], [0, 20]], ("Hola", 0.9)]]]
    lines = _parse_paddle_page(raw)
    assert lines[0].text == "Hola"
    assert lines[0].confidence == 0.9


def test_parse_paddle_empty():
    assert _parse_paddle_page(None) == []
    assert _parse_paddle_page([None]) == []
    assert _parse_paddle_page([]) == []
