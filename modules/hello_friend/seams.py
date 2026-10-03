"""Where `hello_friend` gets the seam it uses.

The core has no seam registry yet (`seams.get(Contract)`, PROPOSAL §4.3), so the provider is a
FastAPI dependency that answers `None` ("not loaded"). When the registry exists, change only
`greeting_provider` to ask it; the page and its tests stay as they are.
"""

from contracts.hello_greeting.v1 import GreetingV1


def greeting_provider() -> GreetingV1 | None:
    return None
