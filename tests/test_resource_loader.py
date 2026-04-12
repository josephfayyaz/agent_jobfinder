from __future__ import annotations


def test_load_fact_sheet_schema_returns_valid_jsonschema():
    from job_agent.services.resource_loader import load_fact_sheet_schema

    schema = load_fact_sheet_schema()
    assert isinstance(schema, dict)
    assert any(key in schema for key in ("$schema", "properties", "type", "definitions"))


def test_load_prompt_pack_contains_prompt_1_header():
    from job_agent.services.resource_loader import load_prompt_pack

    pack = load_prompt_pack()
    assert "Prompt 1" in pack or "prompt 1" in pack.lower()


def test_load_renderer_spec_is_nonempty():
    from job_agent.services.resource_loader import load_renderer_spec

    spec = load_renderer_spec()
    assert len(spec) > 100


def test_extract_prompt_section_returns_nonempty_text():
    from job_agent.services.resource_loader import extract_prompt_section, load_prompt_pack

    pack = load_prompt_pack()
    section = extract_prompt_section(pack, 1)
    assert len(section) > 10


def test_load_render_template_nonempty():
    from job_agent.services.resource_loader import load_render_template

    template = load_render_template()
    assert len(template) > 100
