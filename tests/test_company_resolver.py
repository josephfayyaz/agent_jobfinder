from job_agent.services import company_resolver


def test_domain_matches_company_accepts_direct_brand_match():
    assert company_resolver._domain_matches_company("Honeywell", "https://www.honeywell.com")
    assert company_resolver._domain_matches_company("Mediatica Digital SpA", "https://mediaticadigital.it")


def test_domain_matches_company_rejects_unrelated_allowed_domain():
    assert not company_resolver._domain_matches_company("Honeywell", "https://voxxeddays.com")
    assert not company_resolver._domain_matches_company("Qualcomm", "https://www.italyonthisday.com")
    assert not company_resolver._domain_matches_company("Olivetti", "http://en.apuliafilmcommission.it")
