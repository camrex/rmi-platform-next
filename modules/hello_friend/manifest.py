"""hello_friend: shows a greeting when `hello.greeting` is present, says so when it is not."""

from modules.hello_friend.web import router
from rmi_core.manifest import ModuleManifest, Nav, SeamRef

manifest = ModuleManifest(
    key="hello_friend",
    version="0.1.0",
    display_name="Hello Friend",
    accent="violet",
    description="Uses the seam hello.greeting; with it absent the page says the feature is off.",
    routers=[router],
    nav=[Nav("Hello Friend", "/hello_friend")],
    uses=[SeamRef("hello.greeting", ">=1,<2")],
)
