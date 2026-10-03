from modules.{{MODULE_KEY}}.pages import example

def test_example_render():
    assert "Hello from" in example.render(None)
