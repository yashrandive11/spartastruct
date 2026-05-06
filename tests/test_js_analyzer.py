"""Tests for the JS/TS analyzer and multi-language file walking."""

from __future__ import annotations

from pathlib import Path

from spartastruct.analyzer.base import AnalysisResult, FileResult, ImportInfo
from spartastruct.analyzer.js_analyzer import JsAnalyzer
from spartastruct.utils.file_walker import SUPPORTED_EXTENSIONS, walk_project
from spartastruct.utils.framework_detector import detect_frameworks

FIXTURES = Path(__file__).parent / "fixtures"


def test_walk_project_finds_js_ts_files(tmp_path):
    (tmp_path / "app.js").write_text("console.log('hello')")
    (tmp_path / "types.ts").write_text("export type Foo = string")
    (tmp_path / "component.tsx").write_text("export default function App() {}")
    (tmp_path / "ignored.txt").write_text("not a source file")

    files, warnings = walk_project(tmp_path, extensions=frozenset({".js", ".ts", ".tsx"}))
    stems = {f.name for f in files}
    assert "app.js" in stems
    assert "types.ts" in stems
    assert "component.tsx" in stems
    assert "ignored.txt" not in stems
    assert warnings == []


def test_walk_project_default_still_finds_py_only(tmp_path):
    (tmp_path / "main.py").write_text("print('hi')")
    (tmp_path / "app.js").write_text("console.log('hi')")

    files, _ = walk_project(tmp_path)
    assert all(f.suffix == ".py" for f in files)


def test_supported_extensions_contains_js_ts():
    assert ".js" in SUPPORTED_EXTENSIONS
    assert ".ts" in SUPPORTED_EXTENSIONS
    assert ".jsx" in SUPPORTED_EXTENSIONS
    assert ".tsx" in SUPPORTED_EXTENSIONS
    assert ".py" in SUPPORTED_EXTENSIONS


def test_js_analyzer_extracts_class(tmp_path):
    f = tmp_path / "user.js"
    f.write_text("""
class User extends BaseModel {
  constructor(id, name) {
    this.id = id;
    this.name = name;
  }
  toJSON() { return { id: this.id }; }
  static fromRow(row) { return new User(row.id, row.name); }
}
""")
    analyzer = JsAnalyzer(tmp_path)
    result = analyzer.analyze([f])
    assert len(result.files_analyzed) == 1
    classes = result.files_analyzed[0].classes
    assert len(classes) == 1
    assert classes[0].name == "User"
    assert classes[0].bases == ["BaseModel"]
    method_names = {m.name for m in classes[0].methods}
    assert "constructor" in method_names
    assert "toJSON" in method_names
    assert "fromRow" in method_names


def test_js_analyzer_extracts_ts_interface_as_class(tmp_path):
    f = tmp_path / "types.ts"
    f.write_text("""
export interface IUser {
  id: number;
  name: string;
  greet(): void;
}
""")
    analyzer = JsAnalyzer(tmp_path)
    result = analyzer.analyze([f])
    classes = result.files_analyzed[0].classes
    assert any(c.name == "IUser" for c in classes)


def test_js_analyzer_extracts_named_function(tmp_path):
    f = tmp_path / "utils.js"
    f.write_text("""
function greet(name) {
  return 'Hello ' + name;
}
async function fetchData(url) {
  return await fetch(url);
}
""")
    analyzer = JsAnalyzer(tmp_path)
    result = analyzer.analyze([f])
    fns = result.files_analyzed[0].functions
    names = {fn.name for fn in fns}
    assert "greet" in names
    assert "fetchData" in names
    async_fns = [fn for fn in fns if fn.is_async]
    assert any(fn.name == "fetchData" for fn in async_fns)


def test_js_analyzer_extracts_arrow_function(tmp_path):
    f = tmp_path / "utils.js"
    f.write_text("""
const add = (a, b) => a + b;
const fetchUser = async (id) => {
  return await db.find(id);
};
export const helper = (x) => x * 2;
""")
    analyzer = JsAnalyzer(tmp_path)
    result = analyzer.analyze([f])
    fns = result.files_analyzed[0].functions
    names = {fn.name for fn in fns}
    assert "add" in names
    assert "fetchUser" in names
    assert "helper" in names


def test_js_analyzer_extracts_es_imports(tmp_path):
    f = tmp_path / "app.ts"
    f.write_text("""
import express from 'express';
import { Router, Request } from 'express';
import { UserService } from './services/UserService';
""")
    analyzer = JsAnalyzer(tmp_path)
    result = analyzer.analyze([f])
    imports = result.files_analyzed[0].imports
    third_party = imports.third_party
    local = imports.local
    assert any("express" in i for i in third_party)
    assert any("UserService" in i for i in local)


def test_js_analyzer_extracts_require_imports(tmp_path):
    f = tmp_path / "app.js"
    f.write_text("""
const express = require('express');
const User = require('./models/User');
""")
    analyzer = JsAnalyzer(tmp_path)
    result = analyzer.analyze([f])
    imports = result.files_analyzed[0].imports
    assert any("express" in i for i in imports.third_party)
    assert any("User" in i for i in imports.local)


def test_js_analyzer_extracts_express_routes(tmp_path):
    f = tmp_path / "routes.js"
    f.write_text("""
const express = require('express');
const router = express.Router();

router.get('/users', async (req, res) => { res.json([]); });
router.post('/users', async (req, res) => { res.json({}); });
router.put('/users/:id', async (req, res) => { res.json({}); });
router.delete('/users/:id', async (req, res) => { res.status(204).send(); });
""")
    analyzer = JsAnalyzer(tmp_path)
    result = analyzer.analyze([f])
    routes = result.files_analyzed[0].routes
    methods = {r.method for r in routes}
    paths = {r.path for r in routes}
    assert "GET" in methods
    assert "POST" in methods
    assert "PUT" in methods
    assert "DELETE" in methods
    assert "/users" in paths


def test_js_analyzer_extracts_app_get_routes(tmp_path):
    f = tmp_path / "index.js"
    f.write_text("""
const app = require('express')();
app.get('/health', (req, res) => res.json({ ok: true }));
app.post('/login', (req, res) => res.json({ token: 'x' }));
""")
    analyzer = JsAnalyzer(tmp_path)
    result = analyzer.analyze([f])
    routes = result.files_analyzed[0].routes
    assert any(r.path == "/health" and r.method == "GET" for r in routes)
    assert any(r.path == "/login" and r.method == "POST" for r in routes)


def test_js_analyzer_extracts_nestjs_controller_routes(tmp_path):
    f = tmp_path / "users.controller.ts"
    f.write_text("""
import { Controller, Get, Post, Delete } from '@nestjs/common';

@Controller('users')
export class UsersController {
  @Get()
  findAll() { return []; }

  @Post()
  create() { return {}; }

  @Delete(':id')
  remove() { return null; }
}
""")
    analyzer = JsAnalyzer(tmp_path)
    result = analyzer.analyze([f])
    routes = result.files_analyzed[0].routes
    methods = {r.method for r in routes}
    assert "GET" in methods
    assert "POST" in methods
    assert "DELETE" in methods


def test_framework_detector_finds_express(tmp_path):
    fr = FileResult(
        path="index.js",
        imports=ImportInfo(third_party=["express"], local=[]),
    )
    result = AnalysisResult(files_analyzed=[fr])
    frameworks = detect_frameworks(result)
    assert "Express" in frameworks


def test_framework_detector_finds_nestjs():
    fr = FileResult(
        path="app.module.ts",
        imports=ImportInfo(third_party=["@nestjs/common", "@nestjs/core"], local=[]),
    )
    result = AnalysisResult(files_analyzed=[fr])
    frameworks = detect_frameworks(result)
    assert "NestJS" in frameworks


def test_framework_detector_finds_nextjs():
    fr = FileResult(
        path="pages/index.tsx",
        imports=ImportInfo(third_party=["next", "next/router"], local=[]),
    )
    result = AnalysisResult(files_analyzed=[fr])
    frameworks = detect_frameworks(result)
    assert "Next.js" in frameworks


def test_framework_detector_finds_react():
    fr = FileResult(
        path="App.tsx",
        imports=ImportInfo(third_party=["react", "react-dom"], local=[]),
    )
    result = AnalysisResult(files_analyzed=[fr])
    frameworks = detect_frameworks(result)
    assert "React" in frameworks
