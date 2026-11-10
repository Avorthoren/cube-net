from cube_net.ui.i18n import Language


def test_listed_in_their_own_language() -> None:
    assert [language.native_name for language in Language] == ["English", "Русский"]
    assert [language.value for language in Language] == ["en", "ru"]
