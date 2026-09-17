from finance_app.ui.preferences import DEFAULT_PREFERENCES, PreferencesStore


def test_preferences_round_trip(tmp_path) -> None:
    store = PreferencesStore(tmp_path)
    preferences = DEFAULT_PREFERENCES.copy()
    preferences["compact_mode"] = True
    preferences["overview_layout"] = "graphiques"
    preferences["chart_type"] = "area"
    preferences["sidebar_color"] = "#112233"

    store.save(42, preferences)

    loaded = store.load(42)
    assert loaded["compact_mode"] is True
    assert loaded["overview_layout"] == "graphiques"
    assert loaded["chart_type"] == "area"
    assert loaded["sidebar_color"] == "#112233"


def test_preferences_ignore_unknown_keys(tmp_path) -> None:
    directory = tmp_path / "preferences"
    directory.mkdir(parents=True)
    (directory / "user_7.json").write_text(
        '{"theme":"light","unexpected_secret":"ignored"}',
        encoding="utf-8",
    )

    loaded = PreferencesStore(tmp_path).load(7)

    assert loaded["theme"] == "light"
    assert "unexpected_secret" not in loaded
