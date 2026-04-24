"""Seed Italy tech company watchlist."""
from __future__ import annotations

from sqlalchemy.orm import Session

from job_agent.models import CareerPageSource


ITALY_TECH_COMPANIES: list[dict[str, str | None]] = [
    {"company": "Bending Spoons", "career_url": "https://jobs.bendingspoons.com", "country": "Italy", "ats_type": "greenhouse", "ats_slug": "bendingspoons"},
    {"company": "Satispay", "career_url": "https://jobs.lever.co/satispay", "country": "Italy", "ats_type": "lever", "ats_slug": "satispay"},
    {"company": "Scalapay", "career_url": "https://careers.scalapay.com", "country": "Italy", "ats_type": "greenhouse", "ats_slug": "scalapay"},
    {"company": "Musixmatch", "career_url": "https://musixmatch.com/company/careers", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "TeamSystem", "career_url": "https://www.teamsystem.com/lavora-con-noi", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Engineering Group", "career_url": "https://www.eng.it/careers", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Agos", "career_url": "https://www.agos.it/lavora-con-noi", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Flowe", "career_url": "https://www.flowe.com/careers", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Prima.it", "career_url": "https://www.prima.it/careers", "country": "Italy", "ats_type": "greenhouse", "ats_slug": "prima"},
    {"company": "Tannico", "career_url": "https://tannico.it/pages/lavora-con-noi", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Wolters Kluwer Italy", "career_url": "https://career.wolterskluwer.com/search/?q=italy", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Jakala", "career_url": "https://www.jakala.com/careers", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Cerved", "career_url": "https://www.cerved.com/careers", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Almaviva", "career_url": "https://www.almaviva.it/it/lavora-con-noi", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "SECO", "career_url": "https://www.seco.com/careers", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "iGenius", "career_url": "https://igenius.ai/careers", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Casavo", "career_url": "https://casavo.com/careers", "country": "Italy", "ats_type": "greenhouse", "ats_slug": "casavo"},
    {"company": "Soisy", "career_url": "https://soisy.it/careers", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Ideandum", "career_url": "https://ideandum.com/lavora-con-noi", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Reply", "career_url": "https://www.reply.com/en/job-openings", "country": "Italy", "ats_type": "greenhouse", "ats_slug": "reply"},
    {"company": "Telepass", "career_url": "https://www.telepass.com/careers", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Eni", "career_url": "https://www.eni.com/en-IT/careers.html", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Leonardo S.p.A.", "career_url": "https://careers.leonardocompany.com", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "STMicroelectronics", "career_url": "https://www.st.com/content/st_com/en/careers.html", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Bosch Italy", "career_url": "https://www.bosch.it/careers", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "SNAM", "career_url": "https://careers.snam.it", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Fastweb", "career_url": "https://www.fastweb.it/corporate/lavora-con-noi", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "TIM (Telecom Italia)", "career_url": "https://careers.tim.it", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Enel", "career_url": "https://jobs.enel.com", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Intesa Sanpaolo Innovation Center", "career_url": "https://www.intesasanpaolo.com/careers", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Amazon Italy", "career_url": "https://www.amazon.jobs/en/locations/milan-italy", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Google Italy", "career_url": "https://careers.google.com/locations/milan/", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Microsoft Italy", "career_url": "https://careers.microsoft.com/us/en/search-results?location=Italy", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "IBM Italy", "career_url": "https://www.ibm.com/employment/it-it/", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Accenture Italy", "career_url": "https://www.accenture.com/it-it/careers", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Deloitte Italy", "career_url": "https://www2.deloitte.com/it/it/careers.html", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "PwC Italy", "career_url": "https://www.pwc.com/it/it/careers.html", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "McKinsey Italy", "career_url": "https://www.mckinsey.com/it/careers", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "BCG Italy", "career_url": "https://careers.bcg.com/location/italy", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Capgemini Italy", "career_url": "https://www.capgemini.com/it-en/careers/", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "SAP Italy", "career_url": "https://jobs.sap.com/search/?q=&location=Italy", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Oracle Italy", "career_url": "https://careers.oracle.com/jobs/#en/sites/jobsearch/requisitions?location=Italy", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Cisco Italy", "career_url": "https://jobs.cisco.com/jobs/SearchJobs/?21178=%5B188563%5D&21178_format=6020", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Siemens Italy", "career_url": "https://jobs.siemens.com/careers?query=&location=Italy", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "ABB Italy", "career_url": "https://careers.abb/global/en/search-results?keywords=&location=Italy", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Vodafone Italy", "career_url": "https://careers.vodafone.com/search/?q=&location=Italy", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Fincons Group", "career_url": "https://www.finconsgroup.com/careers", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Nagarro Italy", "career_url": "https://www.nagarro.com/en/careers", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "NTT Data Italy", "career_url": "https://it.nttdata.com/careers", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Minsait Italy", "career_url": "https://www.minsait.com/en/careers", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Generative Bionics", "career_url": "https://generativebionics.com/careers", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Cyberwave", "career_url": "https://cyberwave.io/careers", "country": "Italy", "ats_type": None, "ats_slug": None},
    {"company": "Exein", "career_url": "https://exein.io/careers", "country": "Italy", "ats_type": "greenhouse", "ats_slug": "exein"},
    {"company": "Translated", "career_url": "https://translated.com/careers", "country": "Italy", "ats_type": None, "ats_slug": None},
]


def seed_italy_companies(session: Session) -> int:
    """Insert companies not already in the DB. Returns count of new rows inserted."""
    existing_urls = {
        source.career_url
        for source in session.query(CareerPageSource).all()
    }
    new_count = 0
    for entry in ITALY_TECH_COMPANIES:
        if entry["career_url"] in existing_urls:
            continue
        session.add(
            CareerPageSource(
                company=str(entry["company"]),
                career_url=str(entry["career_url"]),
                country=str(entry["country"]),
                ats_type=entry["ats_type"],
                ats_slug=entry["ats_slug"],
                active=True,
            )
        )
        new_count += 1
    if new_count:
        session.commit()
    return new_count
