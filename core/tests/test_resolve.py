"""Resolution (PROPOSAL §3.2): load order, unsatisfied `requires`, `uses` that disable a feature,
duplicate keys, cycles. Module keys here are invented; core names no real module."""

import pytest

from rmi_core.manifest import ModuleManifest, SeamImpl, SeamRef
from rmi_core.resolve import ResolutionError, resolve


class _Impl: ...


def _m(
    key: str,
    offers: dict[str, str] | None = None,
    requires: dict[str, str] | None = None,
    uses: dict[str, str] | None = None,
    core_revision: str | None = None,
) -> ModuleManifest:
    return ModuleManifest(
        key=key,
        version="1.0",
        display_name=key.title(),
        accent="blue",
        seams_offered=[SeamImpl(f"{key}.{n}", v, _Impl()) for n, v in (offers or {}).items()],
        requires=[SeamRef(n, r) for n, r in (requires or {}).items()],
        uses=[SeamRef(n, r) for n, r in (uses or {}).items()],
        core_revision=core_revision,
        db_schema=key if core_revision else None,
    )


def test_empty() -> None:
    result = resolve([])
    assert result.load_order == () and result.disabled == () and result.providers == {}


def test_providers_come_first() -> None:
    top = _m("top", requires={"mid.api": ">=1,<2"})
    mid = _m("mid", offers={"api": "1.2"}, requires={"base.api": ">=1"})
    base = _m("base", offers={"api": "1.0"})
    result = resolve([top, mid, base])
    assert result.load_order == ("base", "mid", "top")
    assert result.providers == {"base.api": "base", "mid.api": "mid"}
    assert result.disabled == ()


def test_order_is_deterministic_and_independent_of_input_order() -> None:
    mods = [
        _m("zeta"),
        _m("alpha"),
        _m("mid", offers={"x": "1"}),
        _m("late", requires={"mid.x": ">=1"}),
    ]
    expected = resolve(mods).load_order
    assert expected == ("alpha", "mid", "late", "zeta")
    assert resolve(list(reversed(mods))).load_order == expected


def test_requires_unsatisfied_names_module_seam_and_range() -> None:
    with pytest.raises(ResolutionError) as err:
        resolve([_m("shed", requires={"parts.items": ">=1,<2"})])
    message = str(err.value)
    assert "'shed'" in message and "'parts.items'" in message and "'>=1,<2'" in message
    assert "no loaded module offers it" in message


def test_requires_version_out_of_range_names_provider_and_version() -> None:
    parts = _m("parts", offers={"items": "2.0"})
    shed = _m("shed", requires={"parts.items": ">=1,<2"})
    with pytest.raises(
        ResolutionError, match=r"'shed' requires seam 'parts.items' '>=1,<2'.*'parts'.*'2.0'"
    ):
        resolve([parts, shed])


def test_every_problem_is_reported() -> None:
    mods = [_m("a", requires={"x.y": ">=1"}), _m("b", requires={"z.w": ">=2"})]
    with pytest.raises(ResolutionError) as err:
        resolve(mods)
    assert len(err.value.problems) == 2


def test_uses_absent_disables_feature_with_reason() -> None:
    result = resolve([_m("shed", uses={"planner.phase": ">=1,<2"})])
    assert result.load_order == ("shed",)
    (item,) = result.disabled
    assert (item.module, item.seam, item.range) == ("shed", "planner.phase", ">=1,<2")
    assert "planner.phase" in item.reason and "no loaded module offers" in item.reason


def test_uses_out_of_range_disables_feature() -> None:
    result = resolve(
        [_m("planner", offers={"phase": "3.0"}), _m("shed", uses={"planner.phase": ">=1,<2"})]
    )
    (item,) = result.disabled
    assert item.module == "shed" and "'3.0'" in item.reason and "'>=1,<2'" in item.reason


def test_uses_present_orders_and_does_not_disable() -> None:
    result = resolve([_m("a_user", uses={"zz.api": ">=1"}), _m("zz", offers={"api": "1.0"})])
    assert result.disabled == ()
    assert result.load_order == ("zz", "a_user")


def test_duplicate_module_key_rejected() -> None:
    with pytest.raises(ResolutionError, match="duplicate module key 'shed'"):
        resolve([_m("shed"), _m("shed")])


def test_cycle_rejected_naming_modules() -> None:
    a = _m("a", offers={"x": "1.0"}, requires={"b.x": ">=1"})
    b = _m("b", offers={"x": "1.0"}, requires={"a.x": ">=1"})
    c = _m("c")
    with pytest.raises(ResolutionError, match=r"cycle.*'a', 'b'") as err:
        resolve([a, b, c])
    assert "'c'" not in str(err.value)


def test_cycle_through_a_satisfied_uses_is_rejected() -> None:
    a = _m("a", offers={"x": "1.0"}, uses={"b.x": ">=1"})
    b = _m("b", offers={"x": "1.0"}, requires={"a.x": ">=1"})
    with pytest.raises(ResolutionError, match="cycle"):
        resolve([a, b])


def test_unsatisfied_uses_does_not_make_a_cycle() -> None:
    a = _m("a", offers={"x": "1.0"}, uses={"b.x": ">=2"})
    b = _m("b", offers={"x": "1.0"}, requires={"a.x": ">=1"})
    result = resolve([a, b])
    assert result.load_order == ("a", "b")
    assert [d.module for d in result.disabled] == ["a"]


def test_core_revision_checked_when_given() -> None:
    shed = _m("shed", core_revision=">=0005")
    assert resolve([shed]).load_order == ("shed",)
    assert resolve([shed], core_revision="0007").load_order == ("shed",)
    with pytest.raises(
        ResolutionError, match=r"'shed' needs core revision '>=0005', but core is at '0003'"
    ):
        resolve([shed], core_revision="0003")
