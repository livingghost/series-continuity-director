"""The interface every transport implements, independent of any one service.

A transport turns a sealed dispatch request into the request one service
accepts and reads that service's answers back. The generic dispatcher calls only
the functions named here, so a new service needs one new module and no other
change. A service record selects its transport by name: `"transport": "<name>"`
loads `scripts/transport_<name>.py`, and several service records may name one
transport. `load` refuses any other module, and `check` refuses a module that
lacks a required function. The dispatcher runs both before any claim or
reservation is recorded.

Required functions:

    compile_request(spec, offering, service, media_ids) -> dict
        {"request", "layout", "request_trace"}. `layout` names the request
        fields that carry each value: "model", "operation", "primary_text",
        "negative_text" (or null), "output_count" (or null with
        "fixed_output_count"), "seed" (or null), "media" ({"index", "field"}
        per input), "management" (envelope fields such as a task identifier),
        "content" (authored text slots) and "fields" ({"id", "field", "kind"}).
        The renderer seals the request against this layout.

    media_paths(spec, offering) -> list[str]
        The selected input files, in the order the request carries them.

    upload_bytes(data, media_type, service, key) -> str
        Register one verified input snapshot and return the identifier the
        request carries. Raises ValueError when the upload is refused or its
        outcome is unknown.

    send(request, service, key) -> dict
        Perform the request once and return the answer to record. A transport
        records a failed exchange as an answer instead of raising.

    rejections(answer) -> list
        The service's refusals, empty when it did not refuse.

    results(answer) -> list[dict]
        One entry per returned artifact: {"url", "seed", "id", "pending"}.
        `pending` is true when the service accepted the task and the artifact
        is not ready yet.

    observation_outcome(answer) -> str
        One of OUTCOMES: ACCEPTED, REFUSED or UNKNOWN.

Optional function:

    poll(task_ids, service, key) -> dict
        Ask again for accepted tasks that were pending. A synchronous service
        omits it.

Outcomes:

- ACCEPTED ("accepted"): the service took the request and names a task or output.
- REFUSED ("rejected"): the service refused the request, so nothing ran.
- UNKNOWN ("indeterminate"): the answer does not say whether the request ran.
  Recovery reconciles it with the service and never resends it.

Every transport follows these network rules, and `post_json` implements them:

- it reads the endpoint through `service_profile.endpoint_url`, which accepts
  https and plain http only for a loopback host;
- it waits no longer than `service_profile.http_timeout` on any network step;
- it sends the credential only to that endpoint and never follows a redirect;
- a 4xx status is a refusal; a redirect, a server error, a transport failure,
  a timeout and a success without a JSON object are unknown outcomes.
"""
from __future__ import annotations

import base64
import hashlib
import http.client
import importlib
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import execution_contract as c
import service_profile

SCRIPTS = Path(__file__).resolve().parent
NAME = re.compile(r'[a-z][a-z0-9_]*')
REQUIRED = ('compile_request', 'media_paths', 'upload_bytes', 'send', 'rejections', 'results',
            'observation_outcome')
OPTIONAL = ('poll',)
ACCEPTED, REFUSED, UNKNOWN = 'accepted', 'rejected', 'indeterminate'
OUTCOMES = frozenset({ACCEPTED, REFUSED, UNKNOWN})


def module_name(service: Any) -> str:
    """Return the module a service record selects, refusing any other spelling."""
    name = service.get('transport') if isinstance(service, dict) else None
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise ValueError('the service record must name its transport as "transport": "<name>", '
                         'lowercase letters, digits and underscores, which selects scripts/transport_<name>.py')
    return 'transport_' + name


def load(service: dict) -> Any:
    """Import the transport a service record names, only from this skill's scripts."""
    name = module_name(service)
    path = SCRIPTS / f'{name}.py'
    if not path.is_file():
        raise ValueError(f'no transport module scripts/{name}.py. Write one against '
                         'scripts/transport_contract.py, or send this submission by hand.')
    module = importlib.import_module(name)
    if Path(module.__file__).resolve() != path.resolve():
        raise ValueError(f'the transport {name} resolves outside this skill: {module.__file__}')
    return check(module)


def check(module: Any) -> Any:
    """Refuse a transport that lacks a required function."""
    missing = [name for name in REQUIRED if not callable(getattr(module, name, None))]
    if missing:
        raise ValueError(f"the transport {getattr(module, '__name__', module)!r} lacks "
                         + ', '.join(missing) + '; see scripts/transport_contract.py')
    return module


class _RefuseRedirect(urllib.request.HTTPRedirectHandler):
    """Return a redirect as the answer so the credential never leaves the endpoint."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _opener(url: str) -> urllib.request.OpenerDirector:
    handlers: list[Any] = [_RefuseRedirect]
    if service_profile.is_loopback(url):
        # A loopback exchange never passes through a configured proxy.
        handlers.append(urllib.request.ProxyHandler({}))
    return urllib.request.build_opener(*handlers)


def body_evidence(raw: bytes, content_type: str | None) -> dict[str, Any]:
    """Record a response body completely, as JSON, text or base64."""
    evidence: dict[str, Any] = {'content_type': content_type, 'size': len(raw),
                                'sha256': hashlib.sha256(raw).hexdigest()}
    try:
        value = c.decode(raw)
        c.encoded(value)
        evidence['json'] = value
    except (ValueError, UnicodeError):
        try:
            evidence['text'] = raw.decode('utf-8')
        except UnicodeError:
            evidence['base64'] = base64.b64encode(raw).decode('ascii')
    return evidence


def classify(status: int, body: dict[str, Any]) -> str | None:
    """REFUSED or UNKNOWN from the status alone, or None when the body decides."""
    if 400 <= status < 500:
        return REFUSED
    if 200 <= status < 300 and isinstance(body.get('json'), dict):
        return None
    return UNKNOWN


def _timed_out(error: BaseException) -> bool:
    return isinstance(error, TimeoutError) or (
        isinstance(error, urllib.error.URLError) and isinstance(error.reason, TimeoutError))


def post_json(service: dict, payload: Any, headers: dict[str, str]) -> dict[str, Any]:
    """Send one credentialed JSON request under the network rules above.

    Returns {"status", "location", "body", "outcome"} for any answer that arrived,
    where "outcome" is REFUSED, UNKNOWN, or None when the JSON object decides.
    Returns {"status": None, "outcome": UNKNOWN, "reason", ...} when none did.
    The credential stays in `headers` and is never part of the result.
    """
    target = service_profile.endpoint_url(service)
    seconds, source = service_profile.http_timeout(service)
    request = urllib.request.Request(target, data=json.dumps(payload).encode('utf-8'),
                                     headers={'Content-Type': 'application/json', **headers}, method='POST')
    try:
        with _opener(target).open(request, timeout=seconds) as response:
            status, answer_headers, raw = response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        try:
            status, answer_headers, raw = error.code, error.headers, error.read()
        except (OSError, http.client.HTTPException) as failure:
            return {'status': error.code, 'outcome': UNKNOWN, 'reason': 'the answer body could not be read: ' + repr(failure)}
        finally:
            error.close()
    except (OSError, http.client.HTTPException) as error:
        if _timed_out(error):
            return {'status': None, 'outcome': UNKNOWN, 'reason': 'no complete answer arrived within the network deadline',
                    'timeout_seconds': seconds, 'timeout_source': source}
        return {'status': None, 'outcome': UNKNOWN,
                'reason': 'the exchange failed before a complete answer arrived: ' + repr(error)}
    body = body_evidence(raw, answer_headers.get('Content-Type') if answer_headers is not None else None)
    location = answer_headers.get('Location') if answer_headers is not None and 300 <= status < 400 else None
    return {'status': status, 'location': location, 'body': body, 'outcome': classify(status, body)}
