## What does this change?

<!-- A short description, and the issue it fixes if there is one (e.g. "Fixes #12"). -->

## How was it tested?

- [ ] `python -m unittest discover -s tests` passes
- [ ] Tested on Windows
- [ ] Tested on Linux
- [ ] Tested a real Windows ↔ Linux transfer (needed if the network protocol changed)

## Checklist

- [ ] Changes to the network protocol keep older versions working, or raise `PROTOCOL_VERSION`
- [ ] Doesn't weaken file-name safety (`pathsafe.py`) or update checks (`updates.py`)
- [ ] No built files (`dist/`, `build/`) or secrets included

See [CONTRIBUTING.md](../CONTRIBUTING.md) for details.
