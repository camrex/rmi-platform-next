"""The implementation of seam `hello.greeting` 1.0 (contract: contracts/hello_greeting/v1.py)."""

from contracts.hello_greeting.v1 import Greeting


class Greeter:
    def greet(self, who: str) -> Greeting:
        return Greeting(who=who, message=f"Hello, {who}!")
