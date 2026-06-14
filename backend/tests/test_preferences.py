from models.db import get_or_create_preferences


async def test_creates_default_row_on_first_access(db):
    prefs = await get_or_create_preferences(db)
    assert prefs.id == 1
    assert prefs.user_name == "User"
    assert prefs.conv_model == "google/gemma-4-31b-it:free"
    assert prefs.analysis_model == "deepseek/deepseek-v4-flash"
    assert prefs.onboarding_complete is False


async def test_returns_same_row_on_second_access(db):
    first = await get_or_create_preferences(db)
    first.user_name = "Lo"
    await db.commit()
    second = await get_or_create_preferences(db)
    assert second.id == 1
    assert second.user_name == "Lo"
