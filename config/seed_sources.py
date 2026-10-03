"""
Seed sources for discovery and continuous crawling.
Categorized into Central Government, State Government, Statutory Bodies, Corporate CSR, and Universities.
The crawler autonomously traverses ALL of these portals and their outbound links to discover new schemes.
"""

SEED_SOURCES = [
    # ── TIER 1: CENTRAL GOVERNMENT PORTALS ──────────────────────────────────
    {
        "name": "National Scholarship Portal (NSP)",
        "url": "https://scholarships.gov.in",
        "category": "Central Government",
        "priority": "HIGH",
        "is_authoritative": True
    },
    {
        "name": "Ministry of Education - Scholarship Schemes",
        "url": "https://www.education.gov.in/scholarships-education-loan",
        "category": "Central Government",
        "priority": "HIGH",
        "is_authoritative": True
    },
    {
        "name": "Ministry of Social Justice - Scholarship Portal",
        "url": "https://socialjustice.gov.in/schemes/list",
        "category": "Central Government",
        "priority": "HIGH",
        "is_authoritative": True
    },
    {
        "name": "Ministry of Tribal Affairs - Scholarships",
        "url": "https://tribal.gov.in/scholarship",
        "category": "Central Government",
        "priority": "HIGH",
        "is_authoritative": True
    },
    {
        "name": "Ministry of Minority Affairs - Scholarship Schemes",
        "url": "https://www.minorityaffairs.gov.in/schemes",
        "category": "Central Government",
        "priority": "HIGH",
        "is_authoritative": True
    },
    {
        "name": "MOMA Scholarship Portal (Maulana Azad Foundation)",
        "url": "https://maef.nic.in",
        "category": "Central Government",
        "priority": "HIGH",
        "is_authoritative": True
    },
    {
        "name": "Prime Minister Research Fellowship (PMRF)",
        "url": "https://www.pmrf.in",
        "category": "Central Government / Premier Academic",
        "priority": "HIGH",
        "is_authoritative": True
    },
    {
        "name": "ICMR Fellowships & Scholarships",
        "url": "https://www.icmr.gov.in/training-fellowship.html",
        "category": "Central Government",
        "priority": "HIGH",
        "is_authoritative": True
    },
    {
        "name": "CSIR Junior Research Fellowship",
        "url": "https://csirhrdg.res.in",
        "category": "Central Government",
        "priority": "HIGH",
        "is_authoritative": True
    },
    {
        "name": "DBT Biotechnology Fellowship Schemes",
        "url": "https://www.dbtindia.gov.in/schemes-programmes/research-and-development/scholarships-fellowships",
        "category": "Central Government",
        "priority": "MEDIUM",
        "is_authoritative": True
    },
    {
        "name": "DRDO Scholarship Schemes",
        "url": "https://www.drdo.gov.in",
        "category": "Central Government",
        "priority": "MEDIUM",
        "is_authoritative": True
    },

    # ── TIER 2: STATUTORY BODIES ─────────────────────────────────────────────
    {
        "name": "AICTE Student Development Schemes",
        "url": "https://www.aicte-india.org/schemes/students-development-schemes",
        "category": "Statutory Body / Ministry",
        "priority": "HIGH",
        "is_authoritative": True
    },
    {
        "name": "UGC Schemes and Fellowships",
        "url": "https://www.ugc.gov.in/page/Scholarships-and-Fellowships.aspx",
        "category": "Statutory Body / Ministry",
        "priority": "HIGH",
        "is_authoritative": True
    },
    {
        "name": "UGC NET / JRF NTA Portal",
        "url": "https://ugcnet.nta.ac.in",
        "category": "Statutory Body / Ministry",
        "priority": "HIGH",
        "is_authoritative": True
    },
    {
        "name": "DST INSPIRE Portal",
        "url": "https://online-inspire.gov.in",
        "category": "Central Government",
        "priority": "HIGH",
        "is_authoritative": True
    },
    {
        "name": "DST Women Scientist Scheme (WOS-A)",
        "url": "https://dst.gov.in/scientific-programmes/scientific-engineering-research/women-scientists-programs",
        "category": "Central Government",
        "priority": "HIGH",
        "is_authoritative": True
    },

    # ── TIER 3: UNIVERSITIES & PREMIER INSTITUTIONS ──────────────────────────
    {
        "name": "IISc Bangalore Financial Support",
        "url": "https://iisc.ac.in",
        "category": "University / Premier Institution",
        "priority": "MEDIUM",
        "is_authoritative": True
    },
    {
        "name": "IIT Delhi Financial Aid",
        "url": "https://home.iitd.ac.in",
        "category": "University / Premier Institution",
        "priority": "MEDIUM",
        "is_authoritative": True
    },
    {
        "name": "IIT Bombay Scholarships",
        "url": "https://www.iitb.ac.in/newacadhome/scholarship.jsp",
        "category": "University / Premier Institution",
        "priority": "MEDIUM",
        "is_authoritative": True
    },
    {
        "name": "IIT Madras Merit-cum-Means Scholarship",
        "url": "https://www.iitm.ac.in/academics/scholarships",
        "category": "University / Premier Institution",
        "priority": "MEDIUM",
        "is_authoritative": True
    },
    {
        "name": "AIIMS New Delhi Fellowships",
        "url": "https://www.aiims.edu/en/departments-of-aiims-new-delhi/academic-programmes.html",
        "category": "University / Premier Institution",
        "priority": "MEDIUM",
        "is_authoritative": True
    },
    {
        "name": "NIT Trichy Scholarship Portal",
        "url": "https://www.nitt.edu/home/students/facilitiesforstu/scholarships/",
        "category": "University / Premier Institution",
        "priority": "MEDIUM",
        "is_authoritative": True
    },

    # ── TIER 4: CORPORATE CSR & FOUNDATIONS ──────────────────────────────────
    {
        "name": "Reliance Foundation Scholarships Portal",
        "url": "https://scholarships.reliancefoundation.org",
        "category": "Corporate CSR",
        "priority": "HIGH",
        "is_authoritative": True
    },
    {
        "name": "Tata Trusts Education Grants",
        "url": "https://www.tatatrusts.org/our-work/individual-grants-programme/education-grants",
        "category": "Corporate CSR / Foundation",
        "priority": "HIGH",
        "is_authoritative": True
    },
    {
        "name": "ONGC Scholar Portal",
        "url": "https://www.ongcscholar.org",
        "category": "Corporate CSR",
        "priority": "HIGH",
        "is_authoritative": True
    },
    {
        "name": "Infosys Foundation Programs",
        "url": "https://www.infosys.org/infosys-foundation/programs.html",
        "category": "Corporate CSR",
        "priority": "HIGH",
        "is_authoritative": True
    },
    {
        "name": "Wipro Foundation Education Grants",
        "url": "https://www.wipro.com/sustainability/wipro-foundation",
        "category": "Corporate CSR",
        "priority": "MEDIUM",
        "is_authoritative": True
    },
    {
        "name": "HDFC Bank Parivartan Scholarships",
        "url": "https://www.hdfcbank.com/personal/resources/learning-centre/welfare-schemes/hdfc-bank-parivartan-scholarship",
        "category": "Corporate CSR",
        "priority": "MEDIUM",
        "is_authoritative": True
    },
    {
        "name": "Kotak Education Foundation Scholarships",
        "url": "https://kotakeducation.org/scholarships",
        "category": "Corporate CSR",
        "priority": "MEDIUM",
        "is_authoritative": True
    },
    {
        "name": "L'Oreal India For Women in Science",
        "url": "https://www.loreal.com/en/india/pages/group/fwis",
        "category": "Corporate CSR",
        "priority": "MEDIUM",
        "is_authoritative": True
    },
    {
        "name": "Azim Premji Foundation Fellowships",
        "url": "https://azimpremjifoundation.org/fellowship",
        "category": "Corporate CSR",
        "priority": "MEDIUM",
        "is_authoritative": True
    },
    {
        "name": "Mahindra Education Trust Scholarships",
        "url": "https://www.mahindrarise.com/rise-stories/mahindra-scholarships",
        "category": "Corporate CSR",
        "priority": "MEDIUM",
        "is_authoritative": True
    },

    # ── TIER 5: STATE GOVERNMENT PORTALS ─────────────────────────────────────
    {
        "name": "MahaDBT Scholarship Portal",
        "url": "https://mahadbt.maharashtra.gov.in",
        "category": "State Government",
        "priority": "MEDIUM",
        "is_authoritative": True
    },
    {
        "name": "West Bengal OASIS Portal",
        "url": "https://oasis.gov.in",
        "category": "State Government",
        "priority": "MEDIUM",
        "is_authoritative": True
    },
    {
        "name": "Tamil Nadu e-District Scholarship Portal",
        "url": "https://tnscholarship.gov.in",
        "category": "State Government",
        "priority": "MEDIUM",
        "is_authoritative": True
    },
    {
        "name": "Rajasthan Social Justice Scholarship Portal",
        "url": "https://sje.rajasthan.gov.in/Schemes",
        "category": "State Government",
        "priority": "MEDIUM",
        "is_authoritative": True
    },
    {
        "name": "UP Scholarship Portal",
        "url": "https://scholarship.up.gov.in",
        "category": "State Government",
        "priority": "MEDIUM",
        "is_authoritative": True
    },
    {
        "name": "Bihar E-Kalyan Scholarship Portal",
        "url": "https://ekalyan.bih.nic.in",
        "category": "State Government",
        "priority": "MEDIUM",
        "is_authoritative": True
    },
    {
        "name": "Odisha Scholarship Portal",
        "url": "https://scholarship.odisha.gov.in",
        "category": "State Government",
        "priority": "MEDIUM",
        "is_authoritative": True
    },
    {
        "name": "Jharkhand E-Scholarship Portal",
        "url": "https://escholarship.jharkhand.gov.in",
        "category": "State Government",
        "priority": "MEDIUM",
        "is_authoritative": True
    },
    {
        "name": "Assam Scholarship Portal",
        "url": "https://scholarships.assam.gov.in",
        "category": "State Government",
        "priority": "MEDIUM",
        "is_authoritative": True
    },
    {
        "name": "Karnataka SC/ST Scholarship Portal",
        "url": "https://sw.kar.nic.in/scholarship",
        "category": "State Government",
        "priority": "MEDIUM",
        "is_authoritative": True
    },
    {
        "name": "Gujarat Scholarship Portal",
        "url": "https://esamajkalyan.gujarat.gov.in",
        "category": "State Government",
        "priority": "MEDIUM",
        "is_authoritative": True
    },
    {
        "name": "Madhya Pradesh Scholarship Portal",
        "url": "https://scholarshipportal.mp.nic.in",
        "category": "State Government",
        "priority": "MEDIUM",
        "is_authoritative": True
    },
]
