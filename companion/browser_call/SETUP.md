# Browser transport extras

Optional. Physical-microphone transport loads without these packages.

Install into the same Python that runs Hermes and the companion:

```
python -m pip install -r companion/browser_call/requirements.txt
```

The Windows process-loopback helper compiles on demand from `companion/process_loopback/` using the C# compiler included with Windows. Generated binaries stay under `companion/process_loopback/build/`, which git ignores.

This slice binds only to `http://127.0.0.1:8765/`. Do not expose the unauthenticated page beyond loopback.
