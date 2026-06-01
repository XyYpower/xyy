from app.services.review_service import calculate_next_review


def test_sm2_first_success_review_schedules_tomorrow():
    result = calculate_next_review(
        quality=5,
        ease_factor=2.5,
        interval_days=0,
        review_count=0,
    )

    assert result.interval_days == 1
    assert result.review_count == 1
    assert result.ease_factor > 2.5


def test_sm2_second_success_review_schedules_six_days():
    result = calculate_next_review(
        quality=4,
        ease_factor=2.5,
        interval_days=1,
        review_count=1,
    )

    assert result.interval_days == 6
    assert result.review_count == 2


def test_sm2_failed_review_resets_count_and_keeps_minimum_ease():
    result = calculate_next_review(
        quality=0,
        ease_factor=1.35,
        interval_days=12,
        review_count=4,
    )

    assert result.interval_days == 1
    assert result.review_count == 0
    assert result.ease_factor >= 1.3

