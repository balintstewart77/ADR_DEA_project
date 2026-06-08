import re
import unicodedata

import pandas as pd


_DASH_TRANSLATION = str.maketrans({
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2015": "-",
    "\u2212": "-",
})
_ZERO_WIDTH_RE = re.compile(r"[\u00ad\u200b\u200c\u200d\ufeff]")
_MULTISPACE_RE = re.compile(r"\s+")
_WRAPPED_NAME_LINE_RE = re.compile(
    r"(?m)^([A-Z][A-Za-z'`.-]+(?:[ \t]+[A-Z][A-Za-z'`.-]+){0,3})[ \t]*\n[ \t]*"
    r"([A-Z][A-Za-z'`.-]+(?:[ \t]+[A-Z][A-Za-z'`.-]+){0,3}[ \t]*,)"
)
_OPEN_INSTITUTION_TAIL_RE = re.compile(
    r"\b(?:for|of|and)$",
    re.IGNORECASE,
)
_INSTITUTION_CONTINUATION_TAIL_RE = re.compile(
    r"\b(?:Department|Education|Institute|University|Office|School|College|Centre|Center|Public Health)\b"
    r"(?:\s+(?:for|of|and))?$"
)
_NOT_INSTITUTION_RE = re.compile(
    r"^\s*$|^\d+$|^(and|the|of|for|in|at|to)\s*$",
    re.IGNORECASE,
)

_INSTITUTION_KEYWORDS = (
    "academy",
    "agency",
    "authority",
    "bank",
    "business school",
    "centre",
    "center",
    "college",
    "commission",
    "council",
    "databank",
    "department",
    "economics",
    "foundation",
    "government",
    "hospital",
    "institute",
    "laboratory",
    "ministry",
    "office",
    "public health",
    "research",
    "school",
    "service",
    "services",
    "statistics",
    "trust",
    "university",
)
_NAME_PARTICLES = {"al", "bin", "da", "de", "del", "der", "di", "dos", "du", "la", "le", "st", "van", "von"}
_NON_PERSON_WORDS = {
    "academy",
    "administrative",
    "agency",
    "authority",
    "bank",
    "belfast",
    "biosciences",
    "business",
    "cardiff",
    "centre",
    "center",
    "college",
    "commission",
    "communities",
    "council",
    "databank",
    "data",
    "department",
    "economics",
    "education",
    "energy",
    "england",
    "fiscal",
    "food",
    "foundation",
    "frontier",
    "government",
    "health",
    "housing",
    "institute",
    "international",
    "justice",
    "king's",
    "london",
    "markets",
    "media",
    "ministry",
    "national",
    "office",
    "policy",
    "public",
    "queen's",
    "research",
    "resolution",
    "royal",
    "school",
    "science",
    "service",
    "simetrica",
    "statistics",
    "strategy",
    "swansea",
    "trade",
    "uk",
    "university",
    "wales",
    "welsh",
}
_ALIASES = {
    "ons": "Office for National Statistics",
    "office for national": "Office for National Statistics",
    "office for national statistics": "Office for National Statistics",
    "dfe": "Department for Education",
    "dwp": "Department for Work and Pensions",
    "department for business and trade": "Department for Business and Trade (DBT)",
    "department for business and trade (dbt)": "Department for Business and Trade (DBT)",
    "department for levelling up, housing & communities": "Department for Levelling Up, Housing and Communities (DLUHC)",
    "department for levelling up, housing and communities": "Department for Levelling Up, Housing and Communities (DLUHC)",
    "department for levelling up, housing and communities (dluhc)": "Department for Levelling Up, Housing and Communities (DLUHC)",
    "department for transport": "Department for Transport (DfT)",
    "department for transport (dft)": "Department for Transport (DfT)",
    "dft": "Department for Transport (DfT)",
    "hmrc": "HM Revenue and Customs (HMRC)",
    "hm revenue & customs": "HM Revenue and Customs (HMRC)",
    "hm revenue and customs": "HM Revenue and Customs (HMRC)",
    "moj": "Ministry of Justice",
    "administrative data research wales": "Administrative Data Research Wales",
    "ads group limited": "ADS (Aerospace, Defence, Security, Space) Group Limited",
    "aqa education": "AQA Education",
    "aston business school": "Aston University",
    "aston university": "Aston University",
    "barcelona university": "University of Barcelona",
    "bath university": "University of Bath",
    "bayes business school": "City, University of London",
    "be the business": "Be the Business",
    "behavioural insights team": "Behavioural Insights Team",
    "belmana ltd": "Belmana",
    "birkbeck, university of london": "Birkbeck, University of London",
    "british psychological society": "British Psychological Society",
    "british sociological society": "British Sociological Society",
    "cambridge ocr": "Cambridge OCR",
    "cambridge policy consultants": "Cambridge Policy Consultants",
    "cancer research uk": "Cancer Research UK",
    "cardiff and vale university health board": "Cardiff and Vale University Health Board",
    "cardiff metropolitan university": "Cardiff Metropolitan University",
    "cebr": "Centre for Economic and Business Research (CEBR)",
    "centre for economic and business research": "Centre for Economic and Business Research (CEBR)",
    "centre for economic and business research ltd": "Centre for Economic and Business Research (CEBR)",
    "centre for economic and business research ltd (cber)": "Centre for Economic and Business Research (CEBR)",
    "centre for economic performance, london school of economics": "London School of Economics and Political Science (LSE)",
    "centre for economic performance, london school of economics and political science": "London School of Economics and Political Science (LSE)",
    "cedar": "Centre for Healthcare Evaluation, Device Assessment, and Research (CEDAR)",
    "centre for inclusive trade policy (citp), university of sussex": "University of Sussex",
    "cranfield school of management": "Cranfield University",
    "cristina sechel": "",
    "dascrose limited": "DASCROSE Limited",
    "department for business, innovation and skills": "Department for Business, Innovation and Skills",
    "department for culture, media and sport": "Department for Culture, Media and Sport",
    "department for digital, culture, media and sport": "Department for Digital, Culture, Media and Sport",
    "department for the economy (northern ireland)": "Department for the Economy (Northern Ireland)",
    "dundee university": "University of Dundee",
    "durham university": "Durham University",
    "economic and social research institute (esri)": "Economic and Social Research Institute (ESRI)",
    "ecorys uk": "Ecorys UK",
    "ecibt": "Engineering Construction Industry Training Board (ECITB)",
    "ecitb": "Engineering Construction Industry Training Board (ECITB)",
    "ehrc": "Equality and Human Rights Commission (EHRC)",
    "equality and human rights commission": "Equality and Human Rights Commission (EHRC)",
    "equality and human rights comission": "Equality and Human Rights Commission (EHRC)",
    "esri": "Economic and Social Research Institute (ESRI)",
    "experian": "Experian",
    "federal reserve bank of philadelphia": "Federal Reserve Bank of Philadelphia",
    "federal reserve board of governors": "Federal Reserve Board of Governors",
    "financial conduct authority": "Financial Conduct Authority",
    "frazer-nash consultancy": "Frazer-Nash Consultancy",
    "hackney council": "Hackney Council",
    "home office": "Home Office",
    "icf international": "ICF International",
    "iff research": "IFF Research",
    "ifo institute for economic research": "Ifo Institute for Economic Research",
    "incomes data research": "Incomes Data Research",
    "independent research": "",
    "independent researcher": "Independent Researcher",
    "infact systems limited": "Infact Systems Limited",
    "insead": "Institut Européen d'Administration des Affaires (INSEAD)",
    "insead / institut européen d'administration des affaires": "Institut Européen d'Administration des Affaires (INSEAD)",
    "insead / institut europã©en d'administration des affaires": "Institut Européen d'Administration des Affaires (INSEAD)",
    "institue for employment studies": "Institute for Employment Studies",
    "institute for government": "Institute for Government",
    "institute for the future of work": "Institute for the Future of Work",
    "institute of the motor industry": "Institute of the Motor Industry",
    "international monetary fund": "International Monetary Fund",
    "joint biosecurity, centre": "Joint Biosecurity Centre",
    "king's college london dimitris vallis, king's college london julia ellingwood, king's college london": "King's College London",
    "king's fund": "King's Fund",
    "kingston university": "Kingston University",
    "knowledge transfer network": "Knowledge Transfer Network",
    "lancaster university": "Lancaster University",
    "leeds university": "University of Leeds",
    "lightcast": "Lightcast",
    "natcen social research": "National Centre for Social Research",
    "marie curie": "Marie Curie",
    "methods analytics": "Methods Analytics",
    "middlesex university": "Middlesex University",
    "ministry of justice": "Ministry of Justice",
    "national infrastructure commission": "National Infrastructure Commission",
    "netherlands interdisciplinary demographic institute": "Netherlands Interdisciplinary Demographic Institute",
    "nevin economic research institute": "Nevin Economic Research Institute",
    "nhs improvement and nhs england": "NHS England",
    "northumbria university at newcastle": "Northumbria University",
    "nuffield department of medicine": "University of Oxford",
    "nuffield foundation": "Nuffield Foundation",
    "oecd": "OECD",
    "office for health improvement and disparities": "Office for Health Improvement and Disparities",
    "oxford university": "University of Oxford",
    "pearson": "Pearson",
    "pensions policy institute": "Pensions Policy Institute",
    "perspective economics": "Perspective Economics",
    "public health scotland": "Public Health Scotland",
    "publishers association": "Publishers Association",
    "rand europe uk limited": "RAND Europe",
    "research center in applied economics for development cread - algeria": "Research Center in Applied Economics for Development CREAD - Algeria",
    "rsm uk consulting llp": "RSM UK",
    "saga city research": "Saga City Research",
    "scaleup institute": "ScaleUp Institute",
    "school for policy studies, university of bristol": "University of Bristol",
    "school of education, university of bristol": "University of Bristol",
    "sentencing acadamey": "Sentencing Academy",
    "sgn": "SGN",
    "sheffield teaching hospitals nhs foundation trust": "Sheffield Teaching Hospitals NHS Foundation Trust",
    "social care wales": "Social Care Wales",
    "social market foundation": "Social Market Foundation",
    "social mobility commission, the cabinet office": "Social Mobility Commission",
    "sqw": "SQW - Economic and Management Consultants",
    "state of life": "State of Life",
    "stripe partners": "Stripe Partners",
    "swansea bay university health board": "Swansea Bay University Health Board",
    "swansea university medical school": "Swansea University",
    "tees valley combined authority": "Tees Valley Combined Authority",
    "teeside university": "Teesside University",
    "the equality and human rights commission": "Equality and Human Rights Commission (EHRC)",
    "the lesbian project": "The Lesbian Project",
    "the police foundation": "The Police Foundation",
    "the policy institute, king's college london": "King's College London",
    "the productivity institute, university of manchester": "University of Manchester",
    "the alan turing, institute": "Alan Turing Institute",
    "the university of texas at austin": "University of Texas at Austin",
    "the young foundation - institute for community studies": "The Young Foundation - Institute for Community Studies",
    "tu dublin": "Technological University Dublin",
    "ucl centre for longitudinal studies": "University College London",
    "ucl institute for global health": "University College London",
    "ucl institute for epidemiology and health": "University College London",
    "ucl institute of epidemiology and health": "University College London",
    "ucl institute of health informatics": "University College London",
    "uk export finance": "UK Export Finance",
    "ucl": "University College London",
    "umea university": "Umeå University",
    "university of aston": "Aston University",
    "university of bournemouth": "Bournemouth University",
    "university of california": "University of California",
    "university of cambridge - department of land economy": "University of Cambridge",
    "university of cardiff": "Cardiff University",
    "university of coventry": "Coventry University",
    "university of durham": "Durham University",
    "university of illinois urbana campaign": "University of Illinois Urbana-Champaign",
    "university of kingston": "Kingston University",
    "university of lancaster": "Lancaster University",
    "university of leeds jose pina-sanchez, university of leeds": "University of Leeds",
    "university of leeds jose pina-sánchez, university of leeds": "University of Leeds",
    "university of loughborough": "Loughborough University",
    "university of middlesex": "Middlesex University",
    "university of northumbria at newcastle": "Northumbria University",
    "university of plymouth - school of law and social science": "University of Plymouth",
    "university of swansea": "Swansea University",
    "university of texas": "University of Texas",
    "university of texas at austin": "University of Texas at Austin",
    "university of yale": "Yale University",
    "lse": "London School of Economics and Political Science (LSE)",
    "lshtm": "London School of Hygiene and Tropical Medicine",
    "kcl": "King's College London",
    "kings college london": "King's College London",
    "king's college london": "King's College London",
    "king's college london dimitris vallis, king's college london": "King's College London",
    "london school of economics": "London School of Economics and Political Science (LSE)",
    "london school of economics and political science": "London School of Economics and Political Science (LSE)",
    "london school of economics & political science": "London School of Economics and Political Science (LSE)",
    "london school of economics and polictical science": "London School of Economics and Political Science (LSE)",
    "the london school of economics and political science": "London School of Economics and Political Science (LSE)",
    "the london school of economics": "London School of Economics and Political Science (LSE)",
    "london school of hygiene and tropical medicine rochelle schneider dos": "London School of Hygiene and Tropical Medicine",
    "the university of manchester": "University of Manchester",
    "the university of sheffield": "University of Sheffield",
    "the university of edinburgh": "University of Edinburgh",
    "the university of warwick": "University of Warwick",
    "the university of york": "University of York",
    "the university of nottingham": "University of Nottingham",
    "the university of liverpool": "University of Liverpool",
    "the university of westminster": "University of Westminster",
    "the alan turing institute": "Alan Turing Institute",
    "agri-food biosciences institute": "Agri-Food and Biosciences Institute",
    "agri-food bioscience institute": "Agri-Food and Biosciences Institute",
    "agri-food & biosciences institute": "Agri-Food and Biosciences Institute",
    "agri-food and biosciences institute": "Agri-Food and Biosciences Institute",
    "agrifood biosciences institute": "Agri-Food and Biosciences Institute",
    "agri food biosciences institute": "Agri-Food and Biosciences Institute",
    "cardiff business school": "Cardiff University",
    "city university": "City, University of London",
    "city university london": "City, University of London",
    "city university of london": "City, University of London",
    "city university jannis stã¶ckel, london school of economics and political science": "City, University of London",
    "city, university of london": "City, University of London",
    "casa university college london": "University College London",
    "royal holloway": "Royal Holloway, University of London",
    "royal holloway, university of london": "Royal Holloway, University of London",
    "royal holloway university of london": "Royal Holloway, University of London",
    "university of london - royal holloway": "Royal Holloway, University of London",
    "university of london - kings college": "King's College London",
    "university of london kings college": "King's College London",
    "university of london - queen mary": "Queen Mary University of London",
    "university of london queen mary": "Queen Mary University of London",
    "university of london - birkbeck college": "Birkbeck, University of London",
    "university of london - university college": "University College London",
    "university of london university college": "University College London",
    "university of london / university college": "University College London",
    "university of london-university college": "University College London",
    "university of london - imperial college": "Imperial College London",
    "university of london imperial college": "Imperial College London",
    "university of london “ imperial college": "Imperial College London",
    "london school of economics and political science, university of london": "London School of Economics and Political Science (LSE)",
    "northern ireland statistics and research agency": "Northern Ireland Statistics and Research Agency (NISRA)",
    "northern ireland statistics and research agency (nisra)": "Northern Ireland Statistics and Research Agency (NISRA)",
    "department for digital, culture, media and sport (dcms)": "Department for Digital, Culture, Media and Sport",
    "dhsc": "Department of Health and Social Care (DHSC)",
    "department of health": "Department of Health and Social Care (DHSC)",
    "department of health and social care": "Department of Health and Social Care (DHSC)",
    "department of health and social care (dhsc)": "Department of Health and Social Care (DHSC)",
    "department of health - ni": "Department of Health (Northern Ireland)",
    "beis": "Department for Business, Energy and Industrial Strategy",
    "department for business, inovation and skills - enterprise directorate": "Department for Business, Innovation and Skills",
    "administrative data research, wales": "Administrative Data Research Wales",
    "sail databank databank, swansea university": "SAIL Databank, Swansea University",
    "sail databank, swansea university": "SAIL Databank, Swansea University",
    "education policy institute niccolã2 babbini, education policy institute": "Education Policy Institute",
    "fft education limited": "FFT Education Ltd",
    "frontier economics": "Frontier Economics Ltd",
    "frontier economics ltd margheritaserena ferrara, frontier economics ltd": "Frontier Economics Ltd",
    "institute of fiscal studies": "Institute for Fiscal Studies",
    "insitute for fiscal studies": "Institute for Fiscal Studies",
    "insititute of occupational medicine": "Institute of Occupational Medicine",
    "institute of education": "UCL Institute of Education",
    "national institute of economic and social research": "National Institute for Economic and Social Research",
    "greater london authority": "Greater London Authority (GLA)",
    "health data research uk": "Health Data Research UK (HDR UK)",
    "henley business school": "Henley Business School (University of Reading)",
    "institute for social and economic research": "Institute for Social and Economic Research (University of Essex)",
    "institute for social and economic research, university of essex": "Institute for Social and Economic Research (University of Essex)",
    "johannes kepler, university": "Johannes Kepler University Linz",
    "johannes kepler university": "Johannes Kepler University Linz",
    "johannes kepler university linz": "Johannes Kepler University Linz",
    "learning and work": "Learning and Work Institute",
    "london metropolitan, university": "London Metropolitan University",
    "m&g": "Municipal & General (M&G)",
    "national foundation for education research": "National Foundation for Education Research (NFER)",
    "national foundation for educational research": "National Foundation for Education Research (NFER)",
    "national foundation for educational research (nfer)": "National Foundation for Education Research (NFER)",
    "nfer": "National Foundation for Education Research (NFER)",
    "london economics ltd": "London Economics",
    "ipsos": "Ipsos",
    "ipsos mori": "Ipsos",
    "ipsos uk": "Ipsos",
    "pwc llp": "PwC LLP",
    "pwc": "PwC LLP",
    "pricewaterhousecoopers llp": "PwC LLP",
    "price water house coopers": "PwC LLP",
    "the university of surrey": "University of Surrey",
    "the university of kent": "University of Kent",
    "the university of aston": "Aston University",
    "university of west anglia": "University of East Anglia",
    "queen mary university london": "Queen Mary University of London",
    "queen mary univeristy london": "Queen Mary University of London",
    "queen mary, university of london": "Queen Mary University of London",
    "heriot watt university": "Heriot-Watt University",
    "manchester metropolitan, university": "Manchester Metropolitan University",
    "nottingham trent, university": "Nottingham Trent University",
    "economic statistics, centre of excellence": "Economic Statistics Centre of Excellence",
    "european university, institute": "European University Institute",
    "netherlands interdisciplinary demographic, institute": "Netherlands Interdisciplinary Demographic Institute",
    "office for health improvement and disparities (ohid)": "Office for Health Improvement and Disparities",
    "office for national statistics </span>": "Office for National Statistics",
    "sheffield hallam univeristy": "Sheffield Hallam University",
    "stanford univeristy": "Stanford University",
    "warwick business school": "University of Warwick",
    "cardiff metropolitan, university": "Cardiff Metropolitan University",
    "fraser of allander institute": "Fraser of Allander Institute (University of Strathclyde)",
    "fraser of allander institute (university of strathclyde)": "Fraser of Allander Institute (University of Strathclyde)",
    "fraser of allander institute james black, university of strathclyde": "Fraser of Allander Institute (University of Strathclyde)",
    "lancaster university management, school": "Lancaster University Management School",
    "st andrews, university": "University of St Andrews",
    "ucl institute of education": "UCL Institute of Education",
    "university of oxford sociology": "University of Oxford - Sociology",
    "university of london - university college rui miguel vieira marques da costa, london school of economics": "University College London",
    "university of southampton cristian": "University of Southampton",
    "university of west england": "University of the West of England",
    "sqw economic and management consultants": "SQW - Economic and Management Consultants",
    "sqw-economic and management consultants": "SQW - Economic and Management Consultants",
    "whole life consultants ltd": "Whole Life Consultants",
    "arup": "ARUP",
    "cambridge university": "University of Cambridge",
    "univeristy college london": "University College London",
    "univeristy of cambridge": "University of Cambridge",
    "univeristy of bath": "University of Bath",
    "univeraity of exeter": "University of Exeter",
    "univeristy of exeter": "University of Exeter",
    "swansea univeristy": "Swansea University",
    "edniburgh napier university": "Edinburgh Napier University",
    "utrecht university school of economics": "Utrecht University",
    "vanguard": "Vanguard",
    "wavehill limited": "Wavehill Limited",
    "warwick economics and development": "University of Warwick",
    "what works for children's social care": "What Works for Children's Social Care",
    "wpi economics": "WPI Economics",
    "university college lonfon": "University College London",
    "university of northampton": "University of Northampton",
    "university of southampt on": "University of Southampton",
    "university of west of england": "University of the West of England",
    "university": "",
}

_APPROVED_ACRONYM_RENAMES = {
    "Department for Education": "Department for Education (DfE)",
    "Department for Work and Pensions": "Department for Work and Pensions (DWP)",
    "Ministry of Justice": "Ministry of Justice (MoJ)",
    "Office for National Statistics": "Office for National Statistics (ONS)",
    "Financial Conduct Authority": "Financial Conduct Authority (FCA)",
    "Competition and Markets Authority": "Competition and Markets Authority (CMA)",
    "Intellectual Property Office": "Intellectual Property Office (IPO)",
    "Office for Health Improvement and Disparities": (
        "Office for Health Improvement and Disparities (OHID)"
    ),
    "Public Health England": "Public Health England (PHE)",
    "Public Health Scotland": "Public Health Scotland (PHS)",
    "Public Health Wales": "Public Health Wales (PHW)",
    "Low Pay Commission": "Low Pay Commission (LPC)",
    "Social Mobility Commission": "Social Mobility Commission (SMC)",
    "National Centre for Social Research": "National Centre for Social Research (NatCen)",
    "National Institute for Economic and Social Research": (
        "National Institute for Economic and Social Research (NIESR)"
    ),
    "Chartered Institute of Personnel and Development": (
        "Chartered Institute of Personnel and Development (CIPD)"
    ),
    "Institute for Fiscal Studies": "Institute for Fiscal Studies (IFS)",
    "Institute for Government": "Institute for Government (IfG)",
    "Institute for Employment Studies": "Institute for Employment Studies (IES)",
    "Institute for the Future of Work": "Institute for the Future of Work (IFOW)",
    "International Monetary Fund": "International Monetary Fund (IMF)",
    "University College London": "University College London (UCL)",
    "King's College London": "King's College London (KCL)",
    "London School of Hygiene and Tropical Medicine": (
        "London School of Hygiene and Tropical Medicine (LSHTM)"
    ),
    "Massachusetts Institute of Technology": "Massachusetts Institute of Technology (MIT)",
    "National Physical Laboratory": "National Physical Laboratory (NPL)",
}


def _with_approved_acronym(canonical: str) -> str:
    return _APPROVED_ACRONYM_RENAMES.get(canonical, canonical)


_COMPOUND_INSTITUTION_SPLITS = {
    "health foundation/ academy of medical sciences": [
        "Health Foundation",
        "Academy of Medical Sciences",
    ],
    "health foundation / academy of medical sciences": [
        "Health Foundation",
        "Academy of Medical Sciences",
    ],
    "imperial college business, school/london school of economics": [
        "Imperial College London",
        "London School of Economics and Political Science (LSE)",
    ],
    "imperial college business school/london school of economics": [
        "Imperial College London",
        "London School of Economics and Political Science (LSE)",
    ],
    "london school of economics; and university college london": [
        "London School of Economics and Political Science (LSE)",
        "University College London",
    ],
    "university of warwick/london school of economics": [
        "University of Warwick",
        "London School of Economics and Political Science (LSE)",
    ],
    "university of warwick / london school of economics": [
        "University of Warwick",
        "London School of Economics and Political Science (LSE)",
    ],
}

_PARSER_CLEANUP_ALIAS_KEYS = {
    "cristina sechel",
    "independent research",
    "king's college london dimitris vallis, king's college london",
    "king's college london dimitris vallis, king's college london julia ellingwood, king's college london",
    "london school of hygiene and tropical medicine rochelle schneider dos",
    "university",
    "university of leeds jose pina-sanchez, university of leeds",
    "university of leeds jose pina-sánchez, university of leeds",
}

_INSTITUTION_SECTORS = {
    "Academy of Medical Sciences": "third-sector",
    "Administrative Data Research Wales": "government",
    "ADS (Aerospace, Defence, Security, Space) Group Limited": "commercial",
    "Agri-Food and Biosciences Institute": "government",
    "Alan Turing Institute": "third-sector",
    "Alma Economics": "commercial",
    "AQA Education": "third-sector",
    "ARUP": "commercial",
    "Aston University": "academic",
    "Bank of England": "government",
    "Be the Business": "third-sector",
    "Behavioural Insights Team": "third-sector",
    "Belmana": "commercial",
    "Birkbeck, University of London": "academic",
    "BOP Consulting": "commercial",
    "Bournemouth University": "academic",
    "British Psychological Society": "third-sector",
    "British Sociological Society": "third-sector",
    "Brunel University London": "academic",
    "Cabinet Office": "government",
    "Cambridge OCR": "commercial",
    "Cambridge Econometrics": "commercial",
    "Cambridge Policy Consultants": "commercial",
    "Cancer Research UK": "third-sector",
    "Cardiff Metropolitan University": "academic",
    "Cardiff University": "academic",
    "Cardiff and Vale University Health Board": "government",
    "Centre for Cities": "third-sector",
    "Centre for Economic and Business Research (CEBR)": "commercial",
    "Centre for Healthcare Evaluation, Device Assessment, and Research (CEDAR)": "unclassified",
    "Chartered Institute of Personnel and Development (CIPD)": "third-sector",
    "City, University of London": "academic",
    "Columbia University": "academic",
    "Competition and Markets Authority (CMA)": "government",
    "Coventry University": "academic",
    "Cranfield University": "academic",
    "DASCROSE Limited": "commercial",
    "Department for Business and Trade": "government",
    "Department for Business and Trade (DBT)": "government",
    "Department for Business, Energy and Industrial Strategy": "government",
    "Department for Business, Innovation and Skills": "government",
    "Department for Culture, Media and Sport": "government",
    "Department for Digital, Culture, Media and Sport": "government",
    "Department for Education (DfE)": "government",
    "Department for International Trade": "government",
    "Department for Levelling Up, Housing and Communities": "government",
    "Department for Levelling Up, Housing and Communities (DLUHC)": "government",
    "Department for Transport (DfT)": "government",
    "Department for the Economy (Northern Ireland)": "government",
    "Department for Work and Pensions (DWP)": "government",
    "Department of Health (Northern Ireland)": "government",
    "Department of Health and Social Care (DHSC)": "government",
    "Digital Health and Care Wales": "government",
    "Durham University": "academic",
    "Ecorys UK": "commercial",
    "Economic Statistics Centre of Excellence": "third-sector",
    "Economic and Social Research Institute (ESRI)": "third-sector",
    "Education Policy Institute": "third-sector",
    "Engineering Construction Industry Training Board (ECITB)": "government",
    "Environmental Systems Research Institute (ESRI)": "commercial",
    "Edinburgh Napier University": "academic",
    "Equality and Human Rights Commission (EHRC)": "government",
    "European University Institute": "academic",
    "Experian": "commercial",
    "FFT Education Ltd": "commercial",
    "Federal Reserve Bank of Philadelphia": "government",
    "Federal Reserve Board of Governors": "government",
    "Financial Conduct Authority (FCA)": "government",
    "Fraser of Allander Institute (University of Strathclyde)": "academic",
    "Frazer-Nash Consultancy": "commercial",
    "Frontier Economics Ltd": "commercial",
    "Greater London Authority (GLA)": "government",
    "Greater Manchester Combined Authority": "government",
    "Georgetown University": "academic",
    "Glasgow City Council": "government",
    "Hackney Council": "government",
    "Happy City Initiative": "third-sector",
    "Harvard University": "academic",
    "Hardisty Jones Associates": "commercial",
    "Health Data Research UK (HDR UK)": "third-sector",
    "Health Foundation": "third-sector",
    "Henley Business School (University of Reading)": "academic",
    "Heriot-Watt University": "academic",
    "HM Revenue and Customs (HMRC)": "government",
    "Home Office": "government",
    "ICF International": "commercial",
    "IFF Research": "commercial",
    "Ifo Institute for Economic Research": "third-sector",
    "Imperial College London": "academic",
    "Incomes Data Research": "commercial",
    "Independent Researcher": "unclassified",
    "Infact Systems Limited": "commercial",
    "Innovate UK": "government",
    "Institut Européen d'Administration des Affaires (INSEAD)": "academic",
    "Institute for Employment Studies (IES)": "third-sector",
    "Institute for Fiscal Studies (IFS)": "third-sector",
    "Institute for Government (IfG)": "third-sector",
    "Institute for Social and Economic Research (University of Essex)": "academic",
    "Institute for the Future of Work (IFOW)": "third-sector",
    "Institute of Occupational Medicine": "third-sector",
    "Institute of the Motor Industry": "third-sector",
    "Intellectual Property Office (IPO)": "government",
    "International Monetary Fund (IMF)": "government",
    "Ipsos": "commercial",
    "Joint Biosecurity Centre": "government",
    "Johannes Kepler University Linz": "academic",
    "King's College London (KCL)": "academic",
    "King's Fund": "third-sector",
    "Kingston University": "academic",
    "Knowledge Transfer Network": "third-sector",
    "Lancaster University": "academic",
    "Lancaster University Management School": "academic",
    "Learning and Work Institute": "third-sector",
    "Lightcast": "commercial",
    "London Economics": "commercial",
    "London Metropolitan University": "academic",
    "London School of Economics and Political Science (LSE)": "academic",
    "London School of Hygiene and Tropical Medicine (LSHTM)": "academic",
    "Loughborough University": "academic",
    "Marie Curie": "third-sector",
    "Manchester Metropolitan University": "academic",
    "Massachusetts Institute of Technology (MIT)": "academic",
    "Methods Analytics": "commercial",
    "Middlesex University": "academic",
    "Ministry of Justice (MoJ)": "government",
    "MIME Consulting Ltd": "commercial",
    "Municipal & General (M&G)": "commercial",
    "National Centre for Social Research (NatCen)": "third-sector",
    "National Foundation for Education Research (NFER)": "third-sector",
    "National Infrastructure Commission": "government",
    "National Physical Laboratory (NPL)": "government",
    "National Institute for Economic and Social Research (NIESR)": "third-sector",
    "National Institute of Social and Economic Research": "third-sector",
    "Nesta": "third-sector",
    "Netherlands Interdisciplinary Demographic Institute": "third-sector",
    "Nevin Economic Research Institute": "third-sector",
    "New Economics Foundation": "third-sector",
    "Newcastle University": "academic",
    "NHS England": "government",
    "Northern Ireland Statistics and Research Agency": "government",
    "Northern Ireland Statistics and Research Agency (NISRA)": "government",
    "Northumbria University": "academic",
    "Nottingham Trent University": "academic",
    "Nuffield Family Justice Observatory": "third-sector",
    "Nuffield Foundation": "third-sector",
    "OECD": "government",
    "Office for Health Improvement and Disparities (OHID)": "government",
    "Office for National Statistics (ONS)": "government",
    "Office of the Victims' Commissioner for England and Wales": "government",
    "OFSTED": "government",
    "HM Treasury": "government",
    "Low Pay Commission (LPC)": "government",
    "Oxford Economics Ltd": "commercial",
    "Oxford Economics": "commercial",
    "PA Consulting": "commercial",
    "Pearson": "commercial",
    "Pensions Policy Institute": "third-sector",
    "Perspective Economics": "commercial",
    "Pro Bono Economics": "third-sector",
    "Public Health England (PHE)": "government",
    "Public Health Scotland (PHS)": "government",
    "Public Health Wales (PHW)": "government",
    "Publishers Association": "third-sector",
    "PwC LLP": "commercial",
    "Queen Mary University of London": "academic",
    "Queen's University Belfast": "academic",
    "Queen's University Belfast Management, School": "academic",
    "RAND Europe": "third-sector",
    "Resolution Foundation": "third-sector",
    "Research Center in Applied Economics for Development CREAD - Algeria": "third-sector",
    "Royal Holloway, University of London": "academic",
    "RSM UK": "commercial",
    "Saga City Research": "commercial",
    "SAIL Databank, Swansea University": "academic",
    "ScaleUp Institute": "third-sector",
    "Scottish Government": "government",
    "Sentencing Academy": "third-sector",
    "SGN": "commercial",
    "Sheffield Hallam University": "academic",
    "Sheffield Teaching Hospitals NHS Foundation Trust": "government",
    "Simetrica": "commercial",
    "Skills Development Scotland": "government",
    "Social Care Wales": "government",
    "Social Market Foundation": "third-sector",
    "Social Mobility Commission (SMC)": "government",
    "SQW - Economic and Management Consultants": "commercial",
    "State of Life": "commercial",
    "St Mungo's": "third-sector",
    "Stanford University": "academic",
    "Stripe Partners": "commercial",
    "Swansea Bay University Health Board": "government",
    "Swansea University": "academic",
    "Tech City UK": "government",
    "Technological University Dublin": "academic",
    "Technopolis": "commercial",
    "Tees Valley Combined Authority": "government",
    "Teesside University": "academic",
    "The Lesbian Project": "third-sector",
    "The Police Foundation": "third-sector",
    "The Work Foundation": "third-sector",
    "The Young Foundation - Institute for Community Studies": "third-sector",
    "UCL Institute of Education": "academic",
    "UK Export Finance": "government",
    "UK Health Security Agency": "government",
    "UK Research and Innovation": "government",
    "UK Space Agency": "government",
    "Ulster University": "academic",
    "University College London (UCL)": "academic",
    "University of Aston": "academic",
    "Anglia Ruskin University Higher Education Corporation": "academic",
    "University of Barcelona": "academic",
    "University of Bath": "academic",
    "University of Birmingham": "academic",
    "University of Brighton": "academic",
    "University of Bristol": "academic",
    "University of California": "academic",
    "University of Cambridge": "academic",
    "University of Central Lancashire": "academic",
    "University of Dundee": "academic",
    "University of Derby": "academic",
    "University of East Anglia": "academic",
    "University of Edinburgh": "academic",
    "University of Essex": "academic",
    "University of Exeter": "academic",
    "University of Glasgow": "academic",
    "University of Hertfordshire": "academic",
    "University of Hull": "academic",
    "University of Illinois Urbana-Champaign": "academic",
    "University of Kent": "academic",
    "University of Leeds": "academic",
    "University of Leicester": "academic",
    "University of Liverpool": "academic",
    "University of London": "academic",
    "University of Manchester": "academic",
    "University of Northampton": "academic",
    "University of Nottingham": "academic",
    "University of Oxford": "academic",
    "University of Oxford - Sociology": "academic",
    "University of Padova": "academic",
    "University of Plymouth": "academic",
    "University of Reading": "academic",
    "University of Sheffield": "academic",
    "University of Southampton": "academic",
    "University of St Andrews": "academic",
    "University of Stirling": "academic",
    "University of Strathclyde": "academic",
    "University of Suffolk": "academic",
    "University of Surrey": "academic",
    "University of Sussex": "academic",
    "University of Texas": "academic",
    "University of Texas at Austin": "academic",
    "University of the West of England": "academic",
    "University of Warwick": "academic",
    "University of Westminster": "academic",
    "University of York": "academic",
    "Umeå University": "academic",
    "Utrecht University": "academic",
    "Vanguard": "commercial",
    "Wavehill Limited": "commercial",
    "Welsh Government": "government",
    "West Midlands Combined Authority": "government",
    "What Works for Children's Social Care": "third-sector",
    "Whole Life Consultants": "commercial",
    "WPI Economics": "commercial",
    "Yale University": "academic",
}


def _clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_DASH_TRANSLATION)
    text = _ZERO_WIDTH_RE.sub("", text)
    text = text.replace("_x000D_", " ")
    text = text.replace("\r", "\n").replace("\t", " ")
    text = text.replace("|", "\n")
    text = re.sub(
        r"(?m)^([A-Z][A-Za-z'`.-]+(?:\s+[A-Z][A-Za-z'`.-]+){1,3})\s+(?=(?:Department|Institute|University|Office|School|College|Bank|Government|Agency|Databank|Centre|Center|Ministry|Hospital|Public Health)\b)",
        r"\1, ",
        text,
    )
    text = re.sub(
        r"([A-Za-z\)])\s{2,}([A-Z][A-Za-z'`.-]+(?:\s+[A-Z][A-Za-z'`.-]+){1,4}\s*,)",
        r"\1\n\2",
        text,
    )
    text = re.sub(
        r"\b(Ltd|LLP)\s+([A-Z][A-Za-z'`.-]+(?:\s+[A-Z][A-Za-z'`.-]+){1,4}\s*,)",
        r"\1\n\2",
        text,
    )
    text = _join_wrapped_name_lines(text)
    text = re.sub(r",\s*\n\s*", ", ", text)
    text = re.sub(r"\n+", "\n", text)
    return text


def _join_wrapped_name_lines(text: str) -> str:
    while True:
        updated = _WRAPPED_NAME_LINE_RE.sub(
            lambda match: _join_wrapped_name_match(match, text),
            text,
        )
        if updated == text:
            return text
        text = updated


def _join_wrapped_name_match(match: re.Match, source_text: str) -> str:
    previous_line = source_text[: match.start()].rstrip("\n").split("\n")[-1]
    if previous_line.rstrip().endswith(","):
        return match.group(0)
    previous_tail = _clean_fragment(previous_line.split(",")[-1])
    if _INSTITUTION_CONTINUATION_TAIL_RE.search(previous_tail):
        return match.group(0)

    candidate = f"{match.group(1)} {match.group(2).rstrip(' ,')}"
    prefix_words = _clean_fragment(match.group(1)).split()
    suffix_words = _clean_fragment(match.group(2).rstrip(" ,")).split()
    if len(prefix_words) > 1 and len(suffix_words) > 1:
        return match.group(0)
    if _looks_like_name(candidate):
        return f"{match.group(1)} {match.group(2)}"
    return match.group(0)


def _clean_fragment(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_DASH_TRANSLATION)
    text = _ZERO_WIDTH_RE.sub("", text)
    text = _MULTISPACE_RE.sub(" ", text)
    return text.strip(" \t\r\n,;.")


def _build_logical_lines(text: str) -> list[str]:
    logical_lines: list[str] = []
    for raw_line in text.split("\n"):
        line = _clean_fragment(raw_line)
        if not line:
            continue
        tokens = [_clean_fragment(part) for part in line.split(",") if _clean_fragment(part)]
        if logical_lines:
            previous_tail = _clean_fragment(logical_lines[-1].split(",")[-1])
            if "," in line:
                split_line = _split_leading_institution_continuation(line)
                if split_line:
                    continuation, remainder = split_line
                    if _same_fragment(continuation, previous_tail):
                        line = _clean_fragment(remainder)
                        tokens = [_clean_fragment(part) for part in line.split(",") if _clean_fragment(part)]
                        if not line:
                            continue
                    elif (
                        _OPEN_INSTITUTION_TAIL_RE.search(previous_tail)
                        or (
                            _INSTITUTION_CONTINUATION_TAIL_RE.search(previous_tail)
                            and not _looks_like_single_name_token(continuation)
                        )
                    ):
                        logical_lines[-1] = _clean_fragment(f"{logical_lines[-1]} {continuation}")
                        line = _clean_fragment(remainder)
                        tokens = [_clean_fragment(part) for part in line.split(",") if _clean_fragment(part)]
                        if not line:
                            continue
            if _OPEN_INSTITUTION_TAIL_RE.search(previous_tail):
                split_line = _split_leading_institution_continuation(line)
                if split_line:
                    continuation, remainder = split_line
                    logical_lines[-1] = _clean_fragment(f"{logical_lines[-1]} {continuation}")
                    line = _clean_fragment(remainder)
                    tokens = [_clean_fragment(part) for part in line.split(",") if _clean_fragment(part)]
                    if not line:
                        continue
                if not _starts_name(tokens, 0):
                    logical_lines[-1] = _clean_fragment(f"{logical_lines[-1]} {line}")
                    continue
            if "," not in line and _INSTITUTION_CONTINUATION_TAIL_RE.search(previous_tail):
                logical_lines[-1] = _clean_fragment(f"{logical_lines[-1]} {line}")
                continue
        if (
            logical_lines
            and tokens
            and not _starts_name(tokens, 0)
            and _looks_like_institution_fragment(tokens[0])
        ):
            logical_lines[-1] = _clean_fragment(f"{logical_lines[-1]} {line}")
            continue
        if logical_lines and "," not in line and not _starts_name(line.split(","), 0):
            logical_lines[-1] = _clean_fragment(f"{logical_lines[-1]} {line}")
            continue
        logical_lines.append(line)
    return logical_lines


def _same_fragment(left: str, right: str) -> bool:
    return _clean_fragment(left).casefold() == _clean_fragment(right).casefold()


def _split_leading_institution_continuation(line: str) -> tuple[str, str] | None:
    if "," not in line:
        return None
    head, tail = line.split(",", 1)
    words = head.split()
    for cut in range(1, len(words) - 1):
        continuation = " ".join(words[:cut])
        name = " ".join(words[cut:])
        if _looks_like_name(name):
            return continuation, _clean_fragment(f"{name}, {tail}")
    return None


def _looks_like_name_word(word: str) -> bool:
    cleaned = word.strip("()")
    if not cleaned:
        return False
    if cleaned.lower() in _NAME_PARTICLES:
        return True
    if cleaned.lower() in _NON_PERSON_WORDS:
        return False
    return bool(re.fullmatch(r"[A-Z][A-Za-z'`.-]*", cleaned))


def _looks_like_name(token: str) -> bool:
    token = _clean_fragment(token)
    words = token.split()
    if len(words) < 2 or len(words) > 5:
        return False
    if any(any(keyword in word.lower() for keyword in _INSTITUTION_KEYWORDS) for word in words):
        return False
    return all(_looks_like_name_word(word) for word in words)


def _looks_like_single_name_token(token: str) -> bool:
    token = _clean_fragment(token)
    words = token.split()
    return len(words) == 1 and _looks_like_name_word(words[0])


def _looks_like_institution_fragment(token: str) -> bool:
    token = _clean_fragment(token)
    if not token:
        return False
    lower = token.lower()
    if lower in _ALIASES:
        return True
    return any(keyword in lower for keyword in _INSTITUTION_KEYWORDS)


def _starts_name(tokens: list[str], index: int) -> int:
    token = tokens[index]
    if _looks_like_name(token):
        return 1
    if (
        _looks_like_single_name_token(token)
        and index + 1 < len(tokens)
        and _looks_like_single_name_token(tokens[index + 1])
    ):
        return 2
    return 0


def _normalise_institution(name: str) -> str:
    return _normalise_institution_with_status(name)[0]


def _normalise_institution_with_status(name: str) -> tuple[str, str]:
    name = _clean_fragment(name)
    if not name:
        return "", "empty"

    lowered = name.lower()
    if lowered in _ALIASES:
        canonical = _with_approved_acronym(_ALIASES[lowered])
        if not canonical:
            return "", "empty"
        if lowered in _PARSER_CLEANUP_ALIAS_KEYS:
            return canonical, "parser_cleanup"
        return canonical, "alias"

    repeated_alias = _normalise_repeated_alias_with_researcher(name)
    if repeated_alias is not None:
        return _with_approved_acronym(repeated_alias), "parser_cleanup"

    if "," in name:
        head, tail = name.rsplit(",", 1)
        if _looks_like_institution_fragment(head) and _looks_like_name(tail):
            name = _clean_fragment(head)

    lowered = name.lower()
    if lowered in _ALIASES:
        canonical = _with_approved_acronym(_ALIASES[lowered])
        if not canonical:
            return "", "empty"
        if lowered in _PARSER_CLEANUP_ALIAS_KEYS:
            return canonical, "parser_cleanup"
        return canonical, "alias"

    institution_prefix = _normalise_known_institution_prefix(name)
    if institution_prefix is not None:
        return _with_approved_acronym(institution_prefix), "parser_cleanup"

    return _with_approved_acronym(name), "identity"


def institution_sector_for(canonical_institution: str) -> str:
    return _INSTITUTION_SECTORS.get(
        _with_approved_acronym(canonical_institution),
        "unclassified",
    )


def describe_institution_normalisation(raw_name: str) -> dict[str, object]:
    canonical, match_status = _normalise_institution_with_status(raw_name)
    sector = institution_sector_for(canonical)
    needs_review = int(bool(canonical) and sector == "unclassified")
    return {
        "raw_institution": raw_name,
        "institution": canonical,
        "institution_sector": sector,
        "match_status": match_status,
        "needs_review": needs_review,
    }


def _normalise_repeated_alias_with_researcher(name: str) -> str | None:
    if "," not in name:
        return None

    head, tail = (_clean_fragment(part) for part in name.rsplit(",", 1))
    tail_canonical = _canonical_from_alias_or_name(tail)
    if tail_canonical is None:
        return None

    head_lower = head.lower()
    tail_lower = tail.lower()
    if not head_lower.startswith(f"{tail_lower} "):
        return None

    suffix = _clean_fragment(head[len(tail):])
    if _looks_like_name(suffix):
        return tail_canonical
    return None


def _normalise_known_institution_prefix(name: str) -> str | None:
    name_lower = name.lower()
    for alias, canonical in _known_institution_prefixes():
        if name_lower.startswith(f"{alias} "):
            suffix = _clean_fragment(name[len(alias):])
            if _looks_like_name(suffix):
                return canonical
    return None


def _known_institution_prefixes() -> list[tuple[str, str]]:
    candidates: dict[str, str] = {}
    for alias, canonical in _ALIASES.items():
        if canonical:
            original = canonical
            canonical = _with_approved_acronym(canonical)
            candidates[alias] = canonical
            candidates.setdefault(original.lower(), canonical)
            candidates.setdefault(canonical.lower(), canonical)
    return sorted(candidates.items(), key=lambda item: len(item[0]), reverse=True)


def _canonical_from_alias_or_name(name: str) -> str | None:
    lowered = name.lower()
    if lowered in _ALIASES:
        return _with_approved_acronym(_ALIASES[lowered]) or None
    for value in {value for value in _ALIASES.values() if value}:
        canonical = _with_approved_acronym(value)
        if lowered in {value.lower(), canonical.lower()}:
            return canonical
    return None


def _split_compound_institution(name: str) -> list[str]:
    lowered = name.lower()
    if lowered in _COMPOUND_INSTITUTION_SPLITS:
        return [
            _with_approved_acronym(institution)
            for institution in _COMPOUND_INSTITUTION_SPLITS[lowered]
        ]
    return [_with_approved_acronym(name)]


def _parse_institution_rows(df: pd.DataFrame, *, include_metadata: bool = False) -> list[dict[str, object]]:
    rows = []

    for _, proj in df.iterrows():
        raw = proj.get("Researchers", "")
        if not isinstance(raw, str) or not raw.strip():
            continue

        project_id = proj["Project ID"]
        year = proj["Year"]
        text = _clean_text(raw)
        institutions_seen = set()

        for line in _build_logical_lines(text):
            if not line or "," not in line:
                continue

            tokens = [_clean_fragment(part) for part in line.split(",")]
            tokens = [token for token in tokens if token]
            i = 0
            while i < len(tokens):
                consumed = _starts_name(tokens, i)
                if not consumed:
                    i += 1
                    continue

                i += consumed
                institution_parts = []

                while i < len(tokens):
                    next_consumed = _starts_name(tokens, i)
                    if institution_parts and next_consumed:
                        break
                    token = tokens[i]
                    if institution_parts and _looks_like_name(token) and i == len(tokens) - 1:
                        break
                    institution_parts.append(token)
                    i += 1

                raw_institution = ", ".join(institution_parts)
                normalisation = describe_institution_normalisation(raw_institution)
                institution = str(normalisation["institution"])
                for split_institution in _split_compound_institution(institution):
                    if (
                        split_institution
                        and not _NOT_INSTITUTION_RE.match(split_institution)
                        and len(split_institution) > 2
                        and split_institution not in institutions_seen
                    ):
                        institutions_seen.add(split_institution)
                        if include_metadata:
                            sector = institution_sector_for(split_institution)
                            match_status = str(normalisation["match_status"])
                            if split_institution != institution:
                                match_status = "parser_cleanup"
                            rows.append({
                                "Project ID": project_id,
                                "Year": year,
                                "raw_institution": raw_institution,
                                "institution": split_institution,
                                "institution_sector": sector,
                                "match_status": match_status,
                                "needs_review": int(sector == "unclassified"),
                            })
                        else:
                            rows.append({
                                "Project ID": project_id,
                                "Year": year,
                                "institution": split_institution,
                            })

    return rows


def parse_institutions(df: pd.DataFrame) -> pd.DataFrame:
    rows = _parse_institution_rows(df)

    return pd.DataFrame(rows, columns=["Project ID", "Year", "institution"])


def parse_institutions_with_metadata(df: pd.DataFrame) -> pd.DataFrame:
    rows = _parse_institution_rows(df, include_metadata=True)
    return pd.DataFrame(
        rows,
        columns=[
            "Project ID",
            "Year",
            "raw_institution",
            "institution",
            "institution_sector",
            "match_status",
            "needs_review",
        ],
    )


def institution_normalisation_review_table(df: pd.DataFrame) -> pd.DataFrame:
    parsed = parse_institutions_with_metadata(df)
    columns = [
        "raw_institution",
        "normalised_institution",
        "mentions",
        "project_count",
        "matched_reference",
        "sector",
        "needs_review",
    ]
    if not len(parsed):
        return pd.DataFrame(columns=columns)

    grouped = (
        parsed.groupby(
            ["raw_institution", "institution", "institution_sector", "needs_review"],
            sort=True,
            dropna=False,
        )
        .agg(
            mentions=("institution", "size"),
            project_count=("Project ID", "nunique"),
        )
        .reset_index()
    )
    grouped["matched_reference"] = grouped["institution_sector"].ne("unclassified")
    grouped = grouped.rename(columns={
        "institution": "normalised_institution",
        "institution_sector": "sector",
    })
    return grouped[
        [
            "raw_institution",
            "normalised_institution",
            "mentions",
            "project_count",
            "matched_reference",
            "sector",
            "needs_review",
        ]
    ].sort_values(
        by=["needs_review", "mentions", "raw_institution"],
        ascending=[False, False, True],
        kind="stable",
    ).reset_index(drop=True)
