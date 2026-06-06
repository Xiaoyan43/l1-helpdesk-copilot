"""KB loader + BM25 retriever tests."""
from app.kb import Retriever, load_articles


def test_load_articles_finds_all_kb_files():
    articles = load_articles("kb")
    assert len(articles) == 12
    assert {a.id for a in articles} == {
        "KB001", "KB002", "KB003", "KB004", "KB005", "KB006",
        "KB007", "KB008", "KB009", "KB010", "KB011", "KB012",
    }


def test_retriever_prefers_password_article():
    retriever = Retriever(load_articles("kb"))
    hits = retriever.search("locked out password reset account unlock", k=1)
    assert len(hits) == 1
    article, score = hits[0]
    assert article.id == "KB001"
    assert score > 0


def test_retriever_prefers_vpn_article():
    retriever = Retriever(load_articles("kb"))
    hits = retriever.search("vpn disconnect wifi network connection drops", k=1)
    assert hits[0][0].id == "KB002"


def test_retriever_prefers_phishing_article():
    retriever = Retriever(load_articles("kb"))
    hits = retriever.search("phishing suspicious email malware report", k=1)
    assert hits[0][0].id == "KB006"


def test_retriever_prefers_shared_drive_article():
    retriever = Retriever(load_articles("kb"))
    hits = retriever.search("access denied shared drive SharePoint permissions", k=1)
    assert hits[0][0].id == "KB007"


def test_retriever_prefers_mfa_article():
    retriever = Retriever(load_articles("kb"))
    hits = retriever.search("MFA Authenticator new phone registration", k=1)
    assert hits[0][0].id == "KB008"
