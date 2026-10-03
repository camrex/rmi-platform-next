"""Seam `hello.greeting` 1.0: say hello to someone. Offered by `hello`, used by `hello_friend`.

A contract is a Protocol plus frozen DTOs and no implementation (PROPOSAL §4.3). Consumers depend
on this file, never on the module that implements it.
"""

from typing import Protocol

from pydantic import BaseModel, ConfigDict

__all__ = ["Greeting", "GreetingV1"]


class Greeting(BaseModel):
    """What a greeting is: who it is for and the words."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    who: str
    message: str


class GreetingV1(Protocol):
    def greet(self, who: str) -> Greeting: ...
