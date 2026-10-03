"""hello: the smallest module. One page, one nav item, one seam (`hello.greeting` 1.0)."""

from modules.hello.seams import Greeter
from modules.hello.web import router
from rmi_core.manifest import ModuleManifest, Nav, SeamImpl

manifest = ModuleManifest(
    key="hello",
    version="0.1.0",
    display_name="Hello",
    accent="teal",
    description="The smallest module: one page, one nav item, and the seam hello.greeting.",
    routers=[router],
    nav=[Nav("Hello", "/hello")],
    seams_offered=[SeamImpl("hello.greeting", "1.0", Greeter())],
)
