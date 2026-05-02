from __future__ import annotations

import json
from pathlib import Path
import textwrap


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"

ROLE_REFERENCES = [
    {
        "role_family": "software",
        "label": "Software developers",
        "url": "https://www.bls.gov/ooh/computer-and-information-technology/software-developers.htm",
    },
    {
        "role_family": "data",
        "label": "Data scientists",
        "url": "https://www.bls.gov/ooh/math/data-scientists.htm",
    },
    {
        "role_family": "finance",
        "label": "Accountants and auditors",
        "url": "https://www.bls.gov/ooh/business-and-financial/accountants-and-auditors.htm",
    },
    {
        "role_family": "finance",
        "label": "Financial analysts",
        "url": "https://www.bls.gov/ooh/business-and-financial/financial-analysts.htm",
    },
    {
        "role_family": "marketing",
        "label": "Market research analysts",
        "url": "https://www.bls.gov/ooh/business-and-financial/market-research-analysts.htm",
    },
    {
        "role_family": "architecture",
        "label": "Architects",
        "url": "https://www.bls.gov/ooh/architecture-and-engineering/architects.htm",
    },
    {
        "role_family": "engineering",
        "label": "Materials engineers",
        "url": "https://www.bls.gov/ooh/architecture-and-engineering/materials-engineers.htm",
    },
    {
        "role_family": "engineering",
        "label": "Industrial engineers",
        "url": "https://www.bls.gov/ooh/architecture-and-engineering/industrial-engineers.htm",
    },
    {
        "role_family": "engineering",
        "label": "Mechanical engineers",
        "url": "https://www.bls.gov/ooh/architecture-and-engineering/mechanical-engineers.htm",
    },
    {
        "role_family": "europe_skills",
        "label": "ESCO occupation classification",
        "url": "https://esco.ec.europa.eu/en/classification/occupation-main",
    },
]


SEEDS = [
    ("Ari Leone", "junior_data_engineer_english_only", "Junior Data Engineer", "data", "junior", ["Italy", "Germany"], [{"name": "English", "level": "C1"}], "BSc Computer Engineering", "Politecnico di Torino", ["Python", "SQL", "Git", "Pandas", "PostgreSQL"], "Built ETL coursework pipelines and a capstone analytics warehouse.", "Prefers English-only job descriptions."),
    ("Bianca Serra", "analytics_engineer_bilingual", "Analytics Engineer", "data", "mid", ["Italy", "Netherlands"], [{"name": "English", "level": "C1"}, {"name": "Italian", "level": "C2"}], "MSc Data Science", "University of Bologna", ["SQL", "dbt", "Looker", "Airflow", "Python"], "Owned KPI models, transformed warehouse tables, and shipped dashboards for business teams.", "Can review Italian and English job descriptions."),
    ("Carlo Valli", "backend_engineer_mid", "Backend Software Engineer", "software", "mid", ["Italy", "Spain"], [{"name": "English", "level": "C1"}], "BSc Software Engineering", "Sapienza University of Rome", ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"], "Built service APIs, background workers, and test automation for internal platforms.", "English-only filter should exclude Italian-only postings."),
    ("Daria Neri", "qa_automation_junior", "QA Automation Engineer", "software", "junior", ["Italy"], [{"name": "English", "level": "B2"}, {"name": "Italian", "level": "C2"}], "BSc Information Systems", "University of Padua", ["Python", "Playwright", "API testing", "SQL", "GitHub Actions"], "Created regression suites and bug reports for web releases.", "Useful for CV one-page junior tests."),
    ("Elio Ferri", "product_designer_mid", "Product Designer", "marketing", "mid", ["Italy", "France"], [{"name": "English", "level": "C1"}], "BA Design", "Politecnico di Milano", ["Figma", "User research", "Prototyping", "Design systems", "Accessibility"], "Led research interviews and shipped B2B dashboard redesigns.", "Tests non-technical but evidence-heavy intake."),
    ("Farah Lodi", "accountant_junior", "Junior Accountant", "finance", "junior", ["Italy"], [{"name": "English", "level": "B2"}, {"name": "Italian", "level": "B2"}], "BSc Accounting", "University of Turin", ["Excel", "SAP", "Reconciliation", "Financial reporting", "VAT"], "Handled reconciliations, invoice checks, and month-end support during internship.", "Tests accounting flow."),
    ("Giorgio Palmieri", "financial_analyst_mid", "Financial Analyst", "finance", "mid", ["Italy", "Ireland"], [{"name": "English", "level": "C1"}], "MSc Finance", "LUISS Guido Carli", ["Excel", "Power BI", "Financial modeling", "Forecasting", "SQL"], "Built revenue forecasts and management decks for regional planning.", "Tests finance analyst and readiness map."),
    ("Hana Costa", "market_research_junior", "Market Research Analyst", "marketing", "junior", ["Italy", "Germany"], [{"name": "English", "level": "C1"}], "BA Economics", "University of Trento", ["Surveys", "Excel", "SPSS", "Consumer analysis", "Presentation"], "Ran survey analysis and competitor research for student consulting projects.", "Useful for non-engineering language filtering."),
    ("Ivo Ricci", "hr_operations_junior", "HR Operations Specialist", "marketing", "junior", ["Italy"], [{"name": "English", "level": "B2"}, {"name": "Italian", "level": "C2"}], "BA Business Administration", "University of Verona", ["HRIS", "Excel", "Recruiting coordination", "Documentation", "Onboarding"], "Supported hiring coordination and onboarding administration.", "Tests broad office-role intake."),
    ("Lina Moretti", "architect_senior", "Architect", "architecture", "senior", ["Italy", "Switzerland"], [{"name": "English", "level": "C1"}, {"name": "Italian", "level": "C2"}], "MArch Architecture", "IUAV Venice", ["AutoCAD", "Revit", "BIM", "Construction documents", "Client presentations"], "Managed concept-to-permit deliverables and coordinated consultants on mixed-use projects.", "Two-page CV candidate."),
    ("Marco De Santis", "civil_engineer_junior", "Civil Engineer", "engineering", "junior", ["Italy"], [{"name": "English", "level": "B2"}, {"name": "Italian", "level": "C2"}], "BSc Civil Engineering", "University of Naples Federico II", ["AutoCAD", "Site inspections", "Structural basics", "Excel", "Technical reports"], "Supported quantity checks and site coordination during internship.", "Entry-level engineering case."),
    ("Nadia Bruni", "mechanical_engineer_mid", "Mechanical Engineer", "engineering", "mid", ["Italy", "Germany"], [{"name": "English", "level": "C1"}], "MSc Mechanical Engineering", "University of Pisa", ["SolidWorks", "CAD", "DFMEA", "Testing", "Root cause analysis"], "Designed fixtures, tested components, and improved prototype reliability.", "Good for materials/mechanical overlap."),
    ("Omar Bellini", "materials_engineer_junior", "Materials Engineer", "engineering", "junior", ["Italy", "Belgium"], [{"name": "English", "level": "C1"}], "MSc Materials Science", "University of Padua", ["Lab testing", "Materials characterization", "Python", "Microscopy", "Reporting"], "Worked on polymer sample testing and failure analysis during university lab work.", "Directly grounded on materials-engineer reference."),
    ("Petra Gallo", "industrial_engineer_mid", "Industrial Engineer", "engineering", "mid", ["Italy", "Netherlands"], [{"name": "English", "level": "C1"}], "BSc Industrial Engineering", "Politecnico di Bari", ["Process improvement", "Lean", "Time studies", "Excel", "Power BI"], "Mapped factory workflows and recommended cycle-time reductions.", "Good for operations improvement scoring."),
    ("Quinn Esposito", "chemist_lab_analyst", "Laboratory Analyst", "engineering", "junior", ["Italy", "France"], [{"name": "English", "level": "B2"}, {"name": "Italian", "level": "C2"}], "MSc Chemistry", "University of Parma", ["Wet lab", "Chromatography", "Data analysis", "Documentation", "QA"], "Ran sample preparation and documented deviations in regulated lab settings.", "Tests science roles."),
    ("Rina Fabris", "supply_chain_analyst_mid", "Supply Chain Analyst", "engineering", "mid", ["Italy", "Germany"], [{"name": "English", "level": "C1"}], "BSc Management Engineering", "University of Bergamo", ["Excel", "SQL", "Demand planning", "Inventory analysis", "Power BI"], "Tracked stock health and automated replenishment reporting.", "Business-operations hybrid."),
    ("Sami Lucchi", "business_analyst_junior", "Business Analyst", "finance", "junior", ["Italy", "Spain"], [{"name": "English", "level": "C1"}], "BSc Economics and Management", "Ca' Foscari University", ["Requirements gathering", "Excel", "SQL", "Process mapping", "Presentations"], "Documented workflows and translated stakeholder needs into user stories.", "Generalist office-role coverage."),
    ("Tara Giordano", "research_assistant_bio", "Research Assistant", "europe_skills", "junior", ["Italy", "Austria"], [{"name": "English", "level": "C1"}], "MSc Biotechnology", "University of Milan", ["Literature review", "Lab protocols", "Data logging", "Statistics", "Scientific writing"], "Supported experiments and literature synthesis for an academic lab.", "Useful for thesis and traineeship flows."),
    ("Ugo Rizzi", "project_manager_senior", "Project Manager", "software", "senior", ["Italy", "Ireland"], [{"name": "English", "level": "C1"}], "MBA", "Bologna Business School", ["Stakeholder management", "Roadmaps", "Agile", "Budget tracking", "Risk management"], "Led cross-functional delivery for multi-country software rollouts.", "Strong senior candidate with broad evidence."),
    ("Vera Nocera", "data_scientist_mid", "Data Scientist", "data", "mid", ["Italy", "Germany"], [{"name": "English", "level": "C1"}], "MSc Statistics", "University of Florence", ["Python", "Machine learning", "SQL", "Experimentation", "Visualization"], "Built churn models and experimentation readouts for product teams.", "Grounded on data-scientist reference."),
]


def slugify(value: str) -> str:
    return value.lower().replace(" ", "_").replace("/", "_")


def cv_text(seed: tuple) -> str:
    name, _slug, role, _family, seniority, countries, languages, degree, institution, skills, proof, note = seed
    languages_text = ", ".join(f"{item['name']} ({item['level']})" for item in languages)
    countries_text = ", ".join(countries)
    skills_text = ", ".join(skills)
    return textwrap.dedent(
        f"""
        {name}
        {role}
        Email: {slugify(name)}@example.test

        Summary
        {seniority.title()} candidate targeting {role} opportunities in {countries_text}. {note}

        Education
        {degree}
        {institution}

        Evidence
        {proof}

        Core skills
        {skills_text}

        Languages
        {languages_text}
        """
    ).strip() + "\n"


def notes_text(seed: tuple) -> str:
    name, _slug, role, family, seniority, countries, languages, degree, institution, skills, proof, note = seed
    return textwrap.dedent(
        f"""
        Candidate: {name}
        Target role: {role}
        Role family: {family}
        Seniority: {seniority}
        Preferred countries: {", ".join(countries)}
        Languages: {", ".join(f"{item['name']} {item['level']}" for item in languages)}
        Most relevant proof: {proof}
        Testing note: {note}
        """
    ).strip() + "\n"


def job_payload(seed: tuple) -> list[dict[str, object]]:
    name, slug, role, family, seniority, countries, languages, degree, institution, skills, proof, _note = seed
    primary_language = languages[0]["name"]
    return [
        {
            "title": role,
            "company": f"{role.split()[0]}Works Europe",
            "country": countries[0],
            "job_language": primary_language,
            "seniority": seniority,
            "must_have_keywords": skills[:5],
            "summary": f"Synthetic job brief for {role} based on public occupational requirement themes.",
            "source_reference_role_family": family,
        },
        {
            "title": f"{role} - Operations Focus",
            "company": f"{role.split()[0]}Scale Labs",
            "country": countries[-1],
            "job_language": primary_language,
            "seniority": seniority,
            "must_have_keywords": skills[1:6],
            "summary": f"Variant job brief for {role} with more cross-functional and delivery emphasis.",
            "source_reference_role_family": family,
        },
    ]


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_simple_pdf(path: Path, text: str) -> None:
    lines = [line.rstrip() for line in text.splitlines()]
    content = ["BT", "/F1 10 Tf", "50 780 Td", "12 TL"]
    first = True
    for line in lines:
        safe = _pdf_escape(line or " ")
        if first:
            content.append(f"({safe}) Tj")
            first = False
        else:
            content.append("T*")
            content.append(f"({safe}) Tj")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", errors="replace")

    objects: list[bytes] = []
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objects.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
    objects.append(
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
    )
    objects.append(b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
    objects.append(f"5 0 obj << /Length {len(stream)} >> stream\n".encode("latin-1") + stream + b"\nendstream endobj\n")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    pdf.extend(
        f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("latin-1")
    )
    path.write_bytes(pdf)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "users").mkdir(parents=True, exist_ok=True)

    manifest = []
    for index, seed in enumerate(SEEDS, start=1):
        name, slug, role, family, seniority, countries, languages, degree, institution, skills, proof, note = seed
        user_dir = OUT / "users" / f"{index:02d}_{slug}"
        user_dir.mkdir(parents=True, exist_ok=True)

        resume = cv_text(seed)
        notes = notes_text(seed)
        candidate_json = {
            "candidate_name": name,
            "email": f"{slugify(name)}@example.test",
            "target_role": role,
            "role_family": family,
            "seniority": seniority,
            "preferred_countries": countries,
            "job_languages": languages,
            "education": {"degree": degree, "institution": institution},
            "skills": skills,
            "proof_summary": proof,
            "testing_note": note,
        }

        (user_dir / "candidate_resume.txt").write_text(resume, encoding="utf-8")
        (user_dir / "candidate_notes.txt").write_text(notes, encoding="utf-8")
        (user_dir / "candidate_profile.json").write_text(
            json.dumps(candidate_json, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        (user_dir / "target_jobs.json").write_text(
            json.dumps(job_payload(seed), indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        write_simple_pdf(user_dir / "candidate_resume.pdf", resume)

        manifest.append(
            {
                "index": index,
                "slug": slug,
                "candidate_name": name,
                "target_role": role,
                "seniority": seniority,
                "job_languages": languages,
                "preferred_countries": countries,
            }
        )

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (OUT / "role_sources.json").write_text(
        json.dumps(ROLE_REFERENCES, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
