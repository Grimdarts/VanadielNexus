"""Opening a script for editing never runs it, even if .lua is associated with a Lua interpreter."""
import os

import pytest

from vanadiel_nexus.ui import context


@pytest.mark.parametrize('exe, runs', [('lua.exe', True), ('lua5.1.exe', True), ('wlua.exe', True),
                                       ('luajit.exe', True), ('Code.exe', False), ('notepad++.exe', False),
                                       ('LuaStudio.exe', False)])
def test_interpreter_names(exe, runs):
    assert bool(context._INTERPRETER.match(exe)) is runs


def test_lua_associated_with_an_interpreter_is_opened_with_edit_not_run(tmp_path, monkeypatch):
    script = tmp_path / 'Alice_BLU.lua'
    script.write_text('-- sets', encoding='utf-8')
    calls = []
    monkeypatch.setattr(context.os, 'name', 'nt')
    monkeypatch.setattr(context, '_opens_with_interpreter', lambda _p: True)
    monkeypatch.setattr(context.os, 'startfile', lambda p, verb='open': calls.append(('startfile', verb)),
                        raising=False)
    monkeypatch.setattr(context.QDesktopServices, 'openUrl', lambda *_a: calls.append(('default',)))
    context.AppContext.edit_file(str(script))
    assert calls == [('startfile', 'edit')]


def test_no_edit_verb_falls_back_to_notepad(tmp_path, monkeypatch):
    script = tmp_path / 'Alice_BLU.lua'
    script.write_text('-- sets', encoding='utf-8')
    launched = []

    def no_edit(_path, verb='open'):
        raise OSError('no edit verb')
    monkeypatch.setattr(context.os, 'name', 'nt')
    monkeypatch.setattr(context, '_opens_with_interpreter', lambda _p: True)
    monkeypatch.setattr(context.os, 'startfile', no_edit, raising=False)
    monkeypatch.setattr(context.subprocess, 'Popen', lambda args: launched.append(args))
    context.AppContext.edit_file(str(script))
    assert launched == [['notepad.exe', str(script)]]


def test_an_editor_association_keeps_the_normal_open(tmp_path, monkeypatch):
    script = tmp_path / 'init.txt'
    script.write_text('bind f9 x', encoding='utf-8')
    calls = []
    monkeypatch.setattr(context, '_opens_with_interpreter', lambda _p: False)
    monkeypatch.setattr(context.QDesktopServices, 'openUrl', lambda *_a: calls.append('default'))
    context.AppContext.edit_file(str(script))
    context.AppContext.edit_file(str(tmp_path / 'missing.lua'))  # missing files are ignored
    assert calls == ['default']


@pytest.mark.skipif(os.name != 'nt', reason='Windows file associations')
def test_the_association_lookup_runs_on_this_pc():
    assert context._opens_with_interpreter('x.txt') is False  # .txt opens in an editor, never Lua
