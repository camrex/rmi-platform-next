"""Where `hello_friend` gets the seam it uses.

The core has no seam registry yet (`seams.get(Contract)`, PROPOSAL §4.3). Until it exists the
provider is read from `app.state.seams` (`{seam name: implementation}`), which the contract test
helper (`rmi_core.testing.contract.build_app`) fills from the modules that are loaded; `None`
means "not loaded". When the registry exists, change only `greeting_provider` to ask it; the page
and its tests stay as they are.
"""

from typing import Any, cast

from fastapi import Request

from contracts.hello_greeting.v1 import GreetingV1


def greeting_provider(request: Request) -> GreetingV1 | None:
    seams = cast("dict[str, Any]", getattr(request.app.state, "seams", {}))
    return cast("GreetingV1 | None", seams.get("hello.greeting"))
