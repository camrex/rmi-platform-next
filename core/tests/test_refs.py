import pytest

from rmi_core.refs import Ref


def test_ref_gis():
    s = "gis:dataset1:guid123"
    ref = Ref.parse(s)
    assert str(ref) == s
    assert ref.scheme == "gis"
    assert ref.value == "dataset1:guid123"
    assert ref.dataset == "dataset1"
    assert ref.identifier == "guid123"
    assert repr(ref) == f"Ref({s!r})"

def test_ref_oid():
    s = "oid:dataset2:12345"
    ref = Ref.parse(s)
    assert str(ref) == s
    assert ref.scheme == "oid"
    assert ref.value == "dataset2:12345"
    assert ref.dataset == "dataset2"
    assert ref.identifier == "12345"

def test_ref_module_kind():
    s = "tivs.asset:turnout/abc"
    ref = Ref.parse(s)
    assert str(ref) == s
    assert ref.scheme == "tivs.asset"
    assert ref.value == "turnout/abc"
    assert ref.dataset is None
    assert ref.identifier == "turnout/abc"

def test_ref_catalog_item():
    s = "catalog.item:item_99"
    ref = Ref.parse(s)
    assert str(ref) == s
    assert ref.scheme == "catalog.item"
    assert ref.value == "item_99"
    assert ref.dataset is None
    assert ref.identifier == "item_99"

def test_ref_pricing_price():
    s = "pricing.price:price_123"
    ref = Ref.parse(s)
    assert str(ref) == s
    assert ref.scheme == "pricing.price"
    assert ref.value == "price_123"
    assert ref.dataset is None
    assert ref.identifier == "price_123"

def test_ref_malformed():
    with pytest.raises(ValueError, match="Ref string cannot be empty"):
        Ref.parse("")
    
    with pytest.raises(ValueError, match="Malformed ref: .* Expected format 'scheme:value'"):
        Ref.parse("noscheme")
    
    with pytest.raises(ValueError, match="Scheme and value must both be present"):
        Ref.parse(":value")
    
    with pytest.raises(ValueError, match="Scheme and value must both be present"):
        Ref.parse("scheme:")
    
    with pytest.raises(ValueError, match="Malformed gis ref: .* Expected format 'gis:dataset:id'"):
        Ref.parse("gis:nodatasetid")
        
    with pytest.raises(ValueError, match="Malformed oid ref: .* Expected format 'oid:dataset:id'"):
        Ref.parse("oid:nodatasetid")

def test_ref_frozen():
    ref = Ref.parse("gis:d:i")
    with pytest.raises(Exception):
        # Pydantic frozen models raise ValidationError or AttributeError on set
        ref.scheme = "new"
