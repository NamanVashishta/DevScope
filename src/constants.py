import os

# Single-organization builds default to NYU Team. Environment override remains
# for legacy compatibility, but the UI no longer exposes this knob.
DEFAULT_ORG_ID = os.environ.get("HIVEMIND_ORG_ID", "NYU-Team")

