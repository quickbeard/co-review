"""Background workers for PR-Agent.

Each sub-module is a long-running process intended to be the entrypoint of
a dedicated container (see ``docker-compose.yml``). They share the same
codebase as the webhook/API services but run in their own Python process so
crashes do not affect webhook latency and they can scale independently.
"""
