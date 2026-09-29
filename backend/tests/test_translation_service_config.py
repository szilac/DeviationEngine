"""LLM translation must not require a DeepL API key."""

import pytest

from app.exceptions import TranslationNotConfiguredError
from app.services.translation_service import TranslationMethod, get_translation_service


@pytest.mark.asyncio
async def test_llm_translation_works_without_deepl_config(db_session):
    service = await get_translation_service(db_session, TranslationMethod.LLM)
    assert service.deepl is None


@pytest.mark.asyncio
async def test_deepl_translation_still_requires_config(db_session):
    with pytest.raises(TranslationNotConfiguredError):
        await get_translation_service(db_session, TranslationMethod.DEEPL)
