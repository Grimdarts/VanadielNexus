"""Staged consumer proof reusing Nexus's isolated worker conventions/helpers.

No application routing is changed. The spawned worker receives bounded source
bytes, executes the trusted maintained module, and calls its pure reader. It
never evaluates profile source. Keep this harness outside production packaging.
"""
from pathlib import Path

from vanadiel_nexus.core import gs_worker

MODULE = Path(__file__).parent / 'PlayerSystem' / 'core' / 'managed_data.lua'


def run(args):
    from lupa import luajit21 as lupa

    lua = lupa.LuaRuntime(
        encoding=None, register_eval=False, register_builtins=False,
        unpack_returned_tuples=True, attribute_filter=gs_worker._deny_attributes,
    )
    # Only maintained code is compiled. Instruction budget also bounds resolver
    # and parser work; the parent still enforces the worker wall-clock timeout.
    budget = min(int(args.get('instruction_limit', gs_worker.INSTRUCTION_LIMIT)), gs_worker.INSTRUCTION_LIMIT)
    if budget < 1:
        return {'error': 'instruction_limit must be positive'}
    lua.execute(b'jit.off(); debug.sethook(function() error("managed instruction limit",0) end,"",...)', budget)

    def table(value):
        if isinstance(value, dict):
            return lua.table_from({table(k): table(v) for k, v in value.items()})
        if isinstance(value, (list, tuple)):
            return lua.table_from([table(v) for v in value])
        return value.encode('utf-8') if isinstance(value, str) else value

    def python(value):
        if lupa.lua_type(value) == 'table':
            return {python(k): python(v) for k, v in value.items()}
        return value.decode('utf-8') if isinstance(value, bytes) else value

    try:
        module = lua.execute(MODULE.read_bytes())
        if args.get('operation') == 'parse':
            doc = module[b'parse'](args['source'], b'consumer.lua', table(args.get('limits', {})))
            # AST has no runtime aliases and is safe for generic serialization.
            return {'document': python(doc), 'error': ''}
        result = module[b'prepare'](table(args['sources']), table(args['options']))
        # Runtime aliases may cycle. Transfer canonical equipment/provenance,
        # never serialize the materialized runtime graph.
        resolved = result[b'resolved']
        canonical = {key: {field: value for field, value in python(record).items()}
                     for key, record in resolved[b'definitions'].items()}
        return {'canonical': {k.decode(): v for k, v in canonical.items()},
                'settings': python(result[b'settings']), 'hotkeys': python(result[b'hotkeys']), 'error': ''}
    except lupa.LuaError as exc:
        return {'error': str(exc).split('\nstack traceback:')[0]}


def main(sender, args):
    try:
        sender.send(run(args))
    except Exception as exc:
        sender.send({'error': str(exc)})
    finally:
        sender.close()
