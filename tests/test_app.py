from app import Offer, deal_score, matches_product, should_alert


def product() -> dict:
    return {
        "required_terms": ["ddj", "flx4"],
        "blocked_terms": ["case", "capa", "defeito"],
        "target_price": 2500,
        "median_discount_trigger": 0.88,
    }


def test_matches_product_aliases_and_blocks_accessories() -> None:
    assert matches_product("Pioneer DJ DDJ-FLX4 nova", product())
    assert not matches_product("Case para Pioneer DDJ-FLX4", product())


def test_alerts_at_target_price() -> None:
    offer = Offer("test", "DDJ FLX4", 2400, "https://example.com", "1")
    assert should_alert(offer, product(), [])


def test_alerts_below_historical_median() -> None:
    offer = Offer("test", "DDJ FLX4", 2600, "https://example.com", "1")
    assert should_alert(offer, product(), [3000, 3100, 3200])


def test_deal_score_is_bounded() -> None:
    offer = Offer("test", "DDJ FLX4", 1800, "https://example.com", "1")
    assert 0 <= deal_score(offer, 2500, [3000, 3100]) <= 100
