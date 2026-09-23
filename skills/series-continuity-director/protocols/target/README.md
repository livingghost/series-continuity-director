# Series Target Protocol

A target profile records durable facts about one generation model. It keeps two
kinds of fact apart:

- the top level describes the model, whichever service runs it;
- each offering describes the model as one service exposes it.

Profiles hold facts about a surface. A project's decisions about what to send
it live in the project.

## The model

The top level carries the facts that hold on every service:

- `target_id`, the name a submission uses, and `label`;
- `model`, the maker's `maker`, `name` and, where published, `version`;
- `media_kind`, `prompt_contract`, and the camera, multi-shot, duration, audio
  and frame controls;
- `input_modes`, each with its `mode` name, `limits`, `max_inputs` where the
  limits state a number, what the media supplies, what the text must still
  establish, and the modes it `excludes`;
- `anti_patterns`, `identity_reference`, and `evidence` about the model.

A mode is named for the model, such as `reference images` or `frame images`.
The top level carries no service's model identifier and no request key.

## Offerings

An offering carries what one service decides:

- `service`, and `model_identifier`, that service's identifier for the model;
- `request_keys`, the dotted request paths that carry each input mode;
- `request_shape`, how the service forms a request: `model_key`, `text_key`,
  an optional `negative_text_key`, `media_reference` (`uuid`, `url` or
  `data-uri`), and the `single_value_keys` that take one media value rather
  than a list;
- `constraints`, the limits the service enforces, `observed_at`, and an
  optional `schema_snapshot`, the parameter schema observed for this offering;
- `sources`, the evidence that belongs to the service.

A trimmed shipped profile (`profiles/xai-grok-imagine-2.json`):

```json
{
  "artifact_type": "target-profile",
  "target_id": "xai-grok-imagine-2",
  "model": {"maker": "xAI", "name": "Grok Imagine", "version": "2.0"},
  "media_kind": ["image"],
  "input_modes": [
    {"mode": "reference-images", "limits": "at most three references in one request", "max_inputs": 3}
  ],
  "offerings": [
    {
      "service": "runware",
      "model_identifier": "xai:grok-imagine@image-2.0",
      "request_keys": {"reference-images": ["inputs.referenceImages"]},
      "request_shape": {"model_key": "model", "text_key": "positivePrompt", "media_reference": "uuid", "single_value_keys": []},
      "observed_at": "2026-09-13",
      "schema_snapshot": "protocols/target/observed-schemas/xai-grok-imagine-2.runware.json",
      "sources": [{"kind": "surface-control", "reference": "Runware model schema for xai:grok-imagine@image-2.0"}]
    }
  ]
}
```

## How the gate reads a profile

`scripts/submission_gate.py` applies the model's rules to every submission: the
input modes, their counts and their exclusions. A submission that names a
`service` also meets that offering's request keys, limits and stored schema. The
gate forms the request from the offering's `request_shape`, so a service with
another shape needs a profile entry and no change to the gate. A submission that
names no service is checked against the model alone, and each service rule is
reported as unmeasured.

## Where profiles live

The suite ships the profiles under `profiles/`, listed in
`protocol-manifest.json`. A project keeps its own profiles in a directory of its
own, such as `target-profiles/`. `scripts/observe_schema.py schema --profiles
target-profiles` writes one there, with the offering pointing at a schema the
project observed. The gate and the draft command take `--profiles DIR` and search
those directories before the suite's.

`scripts/target_protocol.py` validates and seals a profile. `validate-catalog`
refuses a repeated `target_id`, and a service that names one model identifier in
two profiles.
