# Agent Runtime Performance Optimizations

This page records the hot-path optimizations currently landed in agent-runtime,
the dependency baseline, and the rollback switch.

## Dependency baseline

The runtime consistently uses `openjiuwen==0.1.18`. The local project dependency
is declared in `agent-runtime/pyproject.toml`, while container dependencies are
declared in `agent-runtime/requirements.txt`; both must remain on the same
release.

The development image explicitly removes the `openjiuwen` line from its copied
requirements file and installs the selected `agent-core` source through the
existing CI flow. This source override is limited to development images and
does not change the formal runtime version baseline.

## Landed hot-path optimizations

### Workflow component registration

openjiuwen 0.1.18 supports the `name` argument on both `Workflow` and
`LoopGroup`. IR conversion now forwards node names directly instead of calling
`inspect.signature` for every component. The compatibility reflection used by
workflow start/end components remains in place.

### IR cache-hit logging

Normal memory, Redis, and OBS cache hits are logged at DEBUG. Slow Redis/OBS
hits (over 50 ms by default) additionally emit an INFO diagnostic.
The `ir_load|elapsed|source` performance metric remains at INFO for continuous
monitoring, with `memory`, `redis`, or `obs` as the source value.

### AdvancedLoop state commits

AdvancedLoop per-round state initialization and cleanup can use the
`update_by_id_and_commit` API introduced by openjiuwen 0.1.18, avoiding the
unnecessary deepcopy in the staging queue. The path is disabled by default and
can be enabled for a gray rollout with:

```text
LOOP_STATE_DIRECT_COMMIT_ENABLED=true
```

Restart the runtime process after changing the environment variable; set it to
`false` to roll back to the original path. Before enabling it in a target deployment, validate ordinary and nested loops,
skipped branches, exceptions, interrupt/resume, Redis recovery, and isolation
from input-object mutation before commit.

## Deferred from this batch

Node-level performance-detail sampling and the openjiuwen core `copy=False` API
change remain deferred. This avoids changing observability semantics or a
public API without a complete P95/P99 baseline and cross-version validation.

## Verification and remeasurement

At minimum, run
`agent-runtime/tests/unit_tests/serve/test_performance_optimizations.py`.
Before rollout, repeat the baseline workload with the same concurrency,
workflow, and dataset, then compare TPS, P95/P99, error rate, and log volume
before expanding the AdvancedLoop rollout.
