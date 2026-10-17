from tangthu_crawler.registry import SourceRegistry
def test_vnexpress_registered():
    source = SourceRegistry().get("vnexpress")
    assert source["name"] == "VnExpress"
    assert source["status"] == "active"
