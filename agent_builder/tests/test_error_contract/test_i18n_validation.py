# pylint: disable=protected-access
"""COM-03 §3.5: i18n fail-fast 验证——Builder 所有 definition 的中英文三段文案完整。"""

import pytest

from agent_builder.common.error_contract import catalog, factory


@pytest.mark.parametrize("defn", catalog.all_definitions())
@pytest.mark.parametrize("locale", ["zh_cn", "en_us"])
def test_i18n_three_segments_non_empty(defn, locale):
    msg, reason, suggestion = factory.builder_i18n_resolver.resolve(
        locale, defn.message_key)
    assert msg, f"{defn.error_code} {locale} message is empty"
    assert reason, f"{defn.error_code} {locale} reason is empty"
    assert suggestion, f"{defn.error_code} {locale} suggestion is empty"


def test_i18n_resolver_loads_both_locales():
    assert "zh_cn" in factory.builder_i18n_resolver._locales
    assert "en_us" in factory.builder_i18n_resolver._locales
    assert factory.builder_i18n_resolver._locales["zh_cn"]
    assert factory.builder_i18n_resolver._locales["en_us"]

  # pylint: disable=protected-access  # noqa
def test_i18n_zh_and_en_differ():  # pylint: disable=protected-access  # noqa
    defn = catalog.INTERNAL_ERROR  # pylint: disable=protected-access  # noqa
    zh_msg, _, _ = factory.builder_i18n_resolver.resolve("zh_cn", defn.message_key)  # pylint: disable=protected-access  # noqa
    en_msg, _, _ = factory.builder_i18n_resolver.resolve("en_us", defn.message_key)
    assert zh_msg != en_msg
