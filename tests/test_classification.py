from scripts.tracker import classify_categories, classify_relevance, build_plain_summary


def test_privacy_and_retention_categories():
    categories = classify_categories(
        ["We retain your personal data after account deletion."],
        []
    )
    assert "Datos personales" in categories
    assert "Conservación y eliminación" in categories


def test_security_is_high_relevance():
    categories = classify_categories(["We changed our security measures and encryption."], [])
    assert "Seguridad" in categories
    assert classify_relevance(categories, 1, 0) == "Alta"


def test_plain_summary_does_not_claim_legal_effect():
    summary = build_plain_summary(["Transferencias internacionales"], 2, 1)
    assert "cómo puede trasladarse información entre países" in summary
    assert "texto exacto" in summary


def test_unknown_change_is_explicit():
    summary = build_plain_summary([], 3, 2)
    assert "no ha podido asociarlas con una materia concreta" in summary
