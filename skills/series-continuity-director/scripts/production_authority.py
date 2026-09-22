#!/usr/bin/env python3
"""Bound explicit authorizations to immutable production inputs and receipts.

These records describe the supplied authority; they do not authenticate a human
identity. A permission to spend never implies permission to choose or adopt.
Reservations count even after failure: uncertainty is not permission to retry.
The caller holds the production lock and persists a reservation before acting.
"""
from __future__ import annotations
import datetime as dt
from decimal import Decimal, localcontext
import re
from typing import Any
import execution_contract as c
from production_direction import strings

OPERATIONS = frozenset({'decide', 'edit', 'submit', 'select', 'adopt'})
HALT_CONDITIONS = frozenset({'failed-hard-review', 'unresolved-review'})
MONEY = re.compile(r'^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$')


def money(value: Any) -> Decimal:
    if not isinstance(value, str) or not MONEY.fullmatch(value):
        raise ValueError('cost must be a non-negative decimal string, without exponent notation')
    return Decimal(value)


def count(value: Any, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f'{label}: integer >= {minimum} required')
    return value


def validate(grant: Any, prepared: dict[str, Any]) -> None:
    c.exact(grant, {'input_sha256', 'principal', 'actor', 'purpose', 'permissions',
                    'preserve_sources', 'stop_conditions', 'halt_on', 'expires_at', 'evidence'}, 'authorization')
    if grant['input_sha256'] != prepared['input_sha256']:
        raise ValueError('authorization belongs to a different prepared input')
    for key in ('principal', 'actor', 'purpose'):
        c.text(grant[key], 'authorization ' + key)
    preserved = strings(grant['preserve_sources'], 'preserved sources')
    if not set(preserved) <= {s['id'] for s in prepared['task']['sources']}:
        raise ValueError('authorization names an unknown protected source')
    strings(grant['stop_conditions'], 'stop conditions')
    halts = strings(grant['halt_on'], 'machine stop conditions')
    if not set(halts) <= HALT_CONDITIONS:
        raise ValueError('unknown machine stop condition')
    if grant['expires_at'] is not None:
        c.text(grant['expires_at'], 'authorization expiry')
        if not grant['expires_at'].endswith('Z'):
            raise ValueError('authorization expiry must be a UTC timestamp ending in Z')
        expiry = dt.datetime.fromisoformat(grant['expires_at'][:-1] + '+00:00')
        if expiry <= dt.datetime.now(dt.timezone.utc):
            raise ValueError('authorization has expired')
    evidence = grant['evidence']
    c.exact(evidence, {'path', 'locator'}, 'approval evidence')
    c.text(evidence['path'], 'approval evidence path')
    c.text(evidence['locator'], 'approval evidence locator')
    permissions = grant['permissions']
    if not isinstance(permissions, list) or not permissions:
        raise ValueError('authorization needs explicit permissions')
    seen = set()
    for permission in permissions:
        c.exact(permission, {'operation', 'scopes', 'max_calls', 'max_outputs', 'max_cost', 'currency',
                              'request_scope', 'submission_validation_modes'}, 'permission')
        if permission['operation'] not in OPERATIONS:
            raise ValueError('unknown authorized operation')
        import request_scope
        request_scope.validate(permission['request_scope'], submit=permission['operation'] == 'submit',
                               modes=permission['submission_validation_modes'])
        scopes = strings(permission['scopes'], 'permission scopes', nonempty=True)
        if any('*' in s for s in scopes):
            raise ValueError('wildcard scopes are not supported; task means this exact prepared task')
        key = (permission['operation'], tuple(sorted(scopes)))
        if key in seen:
            raise ValueError('duplicate permission')
        seen.add(key)
        count(permission['max_calls'], 'maximum calls', 1)
        count(permission['max_outputs'], 'maximum outputs')
        maximum = money(permission['max_cost'])
        c.text(permission['currency'], 'currency')
        if permission['currency'] == 'none' and maximum != 0:
            raise ValueError('a nonzero spending limit needs an explicit currency')


def authority_key(grant: dict, proof_sha256: str = '') -> str:
    """Same supplied approval across preparations has one accounting identity.

    Input hashes deliberately do not identify permission budgets. This is an
    integrity/accounting key, not authentication of the principal or evidence.
    """
    return c.content_id({'principal': grant['principal'], 'actor': grant['actor'],
                         'evidence': grant['evidence'], 'proof_sha256': proof_sha256})


def grant_body(grant: dict) -> dict:
    return {k: v for k, v in grant.items() if k != 'input_sha256'}


def select_permission(grant: dict, operation: str, scopes: list[str], currency: str) -> tuple[int, dict]:
    """Select the one declared operation, scope and currency used by accounting."""
    matches = []
    for index, permission in enumerate(grant['permissions']):
        if permission['operation'] != operation:
            continue
        if 'task' not in permission['scopes'] and not set(scopes) <= set(permission['scopes']):
            continue
        if currency != permission['currency']:
            continue
        matches.append((index, permission))
    if len(matches) != 1:
        raise ValueError('exactly one permission must cover operation, scope and currency')
    index, permission = matches[0]
    return index, permission


def reservation(prepared: dict[str, Any], records: list[dict[str, Any]], *, authorization: str,
                actor: str, operation: str, scopes: list[str], request_sha256: str,
                outputs: int = 0, cost: str = '0', currency: str = 'none',
                history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    c.sha(authorization)
    c.sha(request_sha256)
    c.text(actor, 'acting principal')
    strings(scopes, 'requested scopes', nonempty=True)
    count(outputs, 'requested outputs')
    requested_cost = money(cost)
    if operation not in OPERATIONS:
        raise ValueError('unknown requested operation')
    grants = [r for r in records if r['event'] == 'authorization' and r['sha256'] == authorization]
    if len(grants) != 1:
        raise ValueError('operation needs a recorded explicit authorization')
    grant_record = grants[0]
    grant = grant_record['data']['authorization']
    key = grant_record['data'].get('authority_key') or authority_key(grant)
    history = records if history is None else history
    validate(grant, prepared)
    if actor != grant['actor']:
        raise ValueError('authorization was issued to another actor')
    if any(r['event'] == 'revocation' and (r['data'].get('authority_key') == key or r['data']['authorization'] == authorization) for r in history):
        raise ValueError('authorization is revoked')
    hard = {x['id'] for x in prepared['task']['criteria'] if x['strength'] == 'hard'}
    starts = {}
    for row in history:
        if row['event']=='authorization' and (row['data'].get('authority_key') or authority_key(row['data']['authorization']))==key:
            coordinate=row.get('input_sha256')
            starts[coordinate]=min(starts.get(coordinate,row['sequence']),row['sequence'])
    for r in history:
        if r['event']!='review' or r.get('input_sha256') not in starts or r['sequence']<=starts[r.get('input_sha256')]:
            continue
        reviewed = r['data']['review']
        reviewed_hard=set(r.get('hard_criteria',hard))
        if 'unresolved-review' in grant['halt_on'] and reviewed['unresolved']:
            raise ValueError('authorization stopped on unresolved review issues')
        if 'failed-hard-review' in grant['halt_on'] and any(x['criterion'] in reviewed_hard and x['verdict'] == 'fail' for x in reviewed['checks']):
            raise ValueError('authorization stopped on a failed hard criterion')
    index, permission = select_permission(grant, operation, scopes, currency)
    result = {'authorization': authorization, 'authority_key': key, 'permission': index, 'actor': actor,
              'operation': operation, 'scopes': sorted(scopes), 'request_sha256': request_sha256,
              'outputs': outputs, 'cost': cost, 'currency': currency}
    released={r['data']['reservation']['reservation_sha256'] for r in history if r['event']=='reservation-release'}
    all_used=[r for r in history if r['event']=='reservation' and r['data']['authority_key']==key and r['data']['permission']==index]
    if any(r['sha256'] in released and r['data']['request_sha256']==request_sha256 and r['data']['authorization']==authorization for r in all_used):
        raise ValueError('reservation was released; prepare a new run for a new action')
    used=[r['data'] for r in all_used if r['sha256'] not in released]
    repeated = [x for x in used if x['request_sha256'] == request_sha256 and x['authorization'] == authorization]
    if repeated:
        if len(repeated) != 1 or repeated[0] != result:
            raise ValueError('the same action identity was reused with different limits or scope')
        return result
    if len(used) + 1 > permission['max_calls']:
        raise ValueError('authorized call limit exhausted')
    if sum(x['outputs'] for x in used) + outputs > permission['max_outputs']:
        raise ValueError('authorized output limit exhausted')
    with localcontext() as context:
        context.prec = 170 + len(str(len(used) + 1))
        total = sum((money(x['cost']) for x in used), Decimal(0)) + requested_cost
    if total > money(permission['max_cost']):
        raise ValueError('authorized spending limit exhausted')
    return result
