from modules.hello_friend.pages import example

def test_example_render():
    assert "Hello from" in example.render(None)
