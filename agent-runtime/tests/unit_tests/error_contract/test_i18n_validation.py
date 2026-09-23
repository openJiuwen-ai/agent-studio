"""COM-03 §3.5: i18n fail-fast 验证——所有 active definition 的中英文三段文案必须完整。

缺 key、空文案或目录冲突应在测试阶段失败，不在运行时静默产生空字段。
"""

import pytest

from agent_runtime.error_contract import catalog, factory


@pytest.mark.parametrize("defn", catalog.all_definitions())
@pytest.mark.parametrize("locale", ["zh_cn", "en_us"])
def test_i18n_three_segments_non_empty(defn, locale):
    """每个 definition 在每个 locale 的 message/reason/suggestion 均非空。"""
    msg, reason, suggestion = factory.runtime_i18n_resolver.resolve(
        locale, defn.message_key)
    assert msg, f"{defn.error_code} {locale} message is empty"
    assert reason, f"{defn.error_code} {locale} reason is empty"
    assert suggestion, f"{defn.error_code} {locale} suggestion is empty"


def test_i18n_zh_and_en_differ():
    """中英文文案必须不同（证明双语资源实际加载）。"""
    defn = catalog.INTERNAL_ERROR
    zh_msg, _, _ = factory.runtime_i18n_resolver.resolve("zh_cn", defn.message_key)
    en_msg, _, _ = factory.runtime_i18n_resolver.resolve("en_us", defn.message_key)
    assert zh_msg != en_msg
