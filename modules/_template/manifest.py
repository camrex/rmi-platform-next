"""{{MODULE_KEY}}: what this module declares to the core (docs/CONTRACT.md)."""

from rmi_core.manifest import ModuleManifest, Nav

from .web import router

manifest = ModuleManifest(
    key="{{MODULE_KEY}}",
    version="0.1.0",
    display_name="{{MODULE_NAME}}",
    accent="slate",
    description="Description of {{MODULE_KEY}}",
    routers=[router],
    nav=[Nav("{{MODULE_NAME}}", "/{{MODULE_KEY}}")],
)
