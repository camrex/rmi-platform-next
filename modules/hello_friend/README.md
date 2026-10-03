# hello_friend

Consumes seam **`hello.greeting`** (`uses`, range `>=1,<2`). With `hello` absent the module still
loads and its page (`web.py`, `/hello_friend`) says the feature is off.

- Imports the contract `contracts/hello_greeting/v1.py`, never `modules/hello`.
- `seams.py` is the one place that fetches the provider; it is a stub until the core has a seam
  registry. Test: `pytest modules/hello_friend`.
