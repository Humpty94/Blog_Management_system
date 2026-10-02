import pytest

from accounts.selectors import (
    get_active_profile_by_username,
    get_profile_by_user,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
)
from accounts.services import register_user


@pytest.mark.django_db
def test_user_and_profile_selectors():
    user, _ = register_user(
        email="selector_test@example.com",
        username="selector_user",
        password="ValidPassword123!",
        display_name="Selector Display",
        bio="Selector Bio",
    )

    # get_user_by_id
    assert get_user_by_id(user.id) == user
    assert get_user_by_id(999999) is None

    # get_user_by_email
    assert get_user_by_email("SELECTOR_TEST@EXAMPLE.COM") == user
    assert get_user_by_email("nonexistent@example.com") is None
    assert get_user_by_email("") is None

    # get_user_by_username
    assert get_user_by_username("SELECTOR_USER") == user
    assert get_user_by_username("nonexistent_user") is None
    assert get_user_by_username("") is None

    # get_profile_by_user
    profile = get_profile_by_user(user)
    assert profile is not None
    assert profile.display_name == "Selector Display"

    # get_active_profile_by_username
    active_profile = get_active_profile_by_username("selector_user")
    assert active_profile is not None
    assert active_profile.user == user
    assert get_active_profile_by_username("") is None
    assert get_active_profile_by_username("does_not_exist") is None
