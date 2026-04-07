import re

import pandas as pd


DATASET_PROVIDER_RE = re.compile(
    r"(?=(?:Office for National Statistics|Department for [^:\n]{1,120}|"
    r"Ministry of Justice|Home Office(?:; NHS)?|NHS(?:; DfE)?|"
    r"Understanding Society|Institute for [^:\n]{1,120}|"
    r"SAIL Databank(?: Databank)?|UCAS|Northern Ireland [^:\n]{1,120}|"
    r"Intellectual Property Office|IPO|Department for Transport|"
    r"HM Revenue and Customs|HMRC|Data First|MoJ Data First)"
    r"[^:\n]{0,120}:)"
)

ALLOWED_SHORT_DATASET_NAMES = {
    "ASHE", "BHPS", "EOL", "LEO", "NN4B",
}

PROVIDER_ALIASES = {
    "": "Unknown / Unspecified",
    "DfE": "Department for Education",
    "Department For Education": "Department for Education",
    "DfT": "Department for Transport",
    "MOJ": "Ministry of Justice",
    "Office For National Statistics": "Office for National Statistics",
    "Office for national Statistics": "Office for National Statistics",
    "Office of National Statistics": "Office for National Statistics",
    "Offcie for National Statistics": "Office for National Statistics",
    "Department for Business, Energy & Industrial Strategy": "Department for Business, Energy and Industrial Strategy",
    "Institute for Social and Economic Research": "Institute for Economic and Social Research",
    "University and Colleges Admission Service": "Universities and Colleges Admissions Service (UCAS)",
    "UCAS": "Universities and Colleges Admissions Service (UCAS)",
    "NISRA": "Northern Ireland Statistics and Research Agency (NISRA)",
    "Northern Ireland Statistics and Research Agency": "Northern Ireland Statistics and Research Agency (NISRA)",
    "Northern Ireland Statitiscs and Research Agency": "Northern Ireland Statistics and Research Agency (NISRA)",
    "Northern Ireland Statistics and Reserach Agency": "Northern Ireland Statistics and Research Agency (NISRA)",
    "Northern Ireland Statistics Research Agency": "Northern Ireland Statistics and Research Agency (NISRA)",
    "SAIL Databank Databank": "SAIL Databank",
    "NHSD": "NHS Digital",
    "NMC": "Nursing and Midwifery Council",
    "Intellectual Property Office - UK DBT": "Intellectual Property Office",
    "HMRC": "HM Revenue and Customs",
    "UKHSA": "UK Health Security Agency",
    "Ofqual": "Office of Qualifications and Examinations Regulation (Ofqual)",
}

SECURE_RESEARCH_SERVICE_PROVIDER_ALIASES = {
    "Office for National Statistics Secure Research Service": "Office for National Statistics",
    "Office of National Statistics Secure Research Service": "Office for National Statistics",
    "Office for National Statisticts Secure Research Service": "Office for National Statistics",
    "Office of Office of National Statistics Secure Research Service": "Office for National Statistics",
    "Northern Ireland Statistics and Research Agency": "Northern Ireland Statistics and Research Agency (NISRA)",
    "Northern Ireland Statistics Research Agency": "Northern Ireland Statistics and Research Agency (NISRA)",
}

INVALID_DATASET_FRAGMENTS = {
    "_x000D_", "amp", "and 2021", "britain", "britain,", "census", "data",
    "d wales", "database", "dwp and", "england", "index", "index,", "ireland", "ireland,",
    "level", "panel", "person", "person,", "scotland", "survey", "visa,",
    "wales",
    "standard extract england", "standard extract - england",
    "wales indexed", "wales with geography",
    "longitudinal and person",
    "office for national statistics /", "office for national statistics &",
    "office for national statistics/", "office for national",
    "census 2021 attributes - england and wales with geography",
    # Broken dataset fragments / geography-only leftovers / provider bleed-through
    "england and wales",
    "great britain",
    "wales and scotland",
    "wales and northern ireland",
    "home office",
    "food and rural affairs",
    "university of oxford",
    "business structure",
    "business register",
    "business impact of",
    "research and",
    "development",
    "economy survey",
    "employment survey",
    "food survey",
    "death",
    "labour force",
    "trace",
    "occurrences",
    "and earnings",
    "household",
    "households",
    "structure for",
    "udinal busin ess database",
    "udinal business database",
    "ed criminal courts",
    "low carbon and",
    "annual survey of hours and earnings annual",
    "producer price index (ppi",
    "annual population survey &amp",
    "ofqual/dfe/",
    "patents",
    "children looked after",
    "waves 1-18",
    "waves 1-5",
    "data given for all available years unless otherwise stated",
    "designs and trade marks",
    "prisons",
    "prisons and probation",
    "and harmonised bhps",
    "and probation",
    "waves 1-10 and harmonised bhps: waves 1-18",
    "waves 1-13",
    "waves 1-14",
    "waves 1-27",
    "waves 1-9",
    "all future releases",
    "impacts on great britain",
    "pension funds and trusts",
    "household sample",
    "infection survey",
    "living costs and food",
    "consumer prices",
    "offending",
    "department for environment",
    "rounds 5-7",
    "wales: household sample",
    "pay as you earn real time information in the",
    "business structure database in the",
    "offending data",
    "prisons and probation - england and wales",
    "pay as you earn real time information in the uk",
    "business structure database in the uk",
    "office for national statistics",
    "structure database",
    "business enterprise",
    "renewable energy",
    "family man",
    "designs and trade marks from",
    "designs and trade marks from intellectual property office",
    "maternal deaths",
    "national energy efficiency",
    "foreign direct investment",
}

GEOGRAPHY_SUFFIX_FALLBACK_NAMES = {
    "benefits", "earnings", "income", "services", "trace",
}

DATASET_ALIASES = [
    # -- Explicit manual aliases for reviewed problem cases --
    (re.compile(r"(?i)^2011 census data welsh(?: residents)?$"), "Census Wales 2011"),
    (re.compile(r"(?i)^welsh census 2011$"), "Census Wales 2011"),
    (re.compile(r"(?i)^census 2011 welsh(?: records| residents)?$"), "Census Wales 2011"),
    (re.compile(r"(?i)^2011 census(?: data)?$"), "Census 2011"),
    (re.compile(r"(?i)^2021 \(welsh residents\)$"), "Census Wales 2021"),
    (re.compile(r"(?i)^2021 census data welsh(?: residents)?$"), "Census Wales 2021"),
    (re.compile(r"(?i)^census 2021 welsh(?: records)?$"), "Census Wales 2021"),
    (re.compile(r"(?i)^census \(2021\)$"), "Census 2021"),
    (re.compile(r"(?i)^2021 census$"), "Census 2021"),
    (re.compile(r"(?i)^2022 census$"), "Census 2022"),
    (re.compile(r"(?i)^2001 census$"), "Census 2001"),
    (re.compile(r"(?i)^2001 census: household sample of anonymised(?: records)?$"), "Census 2001 Household"),
    (re.compile(r"(?i)^census 2001 household(?: for the)?$"), "Census 2001 Household"),
    (re.compile(r"(?i)^(?:census )?2001 controlled(?: access microdata samples)?$"), "Census 2001 Individual"),
    (re.compile(r"(?i)^access microdata samples$"), "Census 2001 Individual"),
    (re.compile(r"(?i)^census 2001 individual$"), "Census 2001 Individual"),
    (re.compile(r"(?i)^census 2011 household$"), "Census 2011 Household"),
    (re.compile(r"(?i)^census 2011:\s*household$"), "Census 2011 Household"),
    (re.compile(r"(?i)^census 2011:\s*household sample$"), "Census 2011 Household Sample"),
    (re.compile(r"(?i)^secure census 2011 england and wales:\s*household sample$"), "Census 2011 Household Sample England and Wales"),
    (re.compile(r"(?i)^household sample scottish government:\s*secure census 2011 scotland$"), "Census 2011 Household Sample Scotland"),
    (re.compile(r"(?i)^census 2011 individual england and wales$"), "Census 2011 Individual England and Wales"),
    (re.compile(r"(?i)^census 2011 individual northern ireland$"), "Census 2011 Individual Northern Ireland"),
    (re.compile(r"(?i)^census 2011 individual scotland$"), "Census 2011 Individual Scotland"),
    (re.compile(r"(?i)^census 2011 individual secure sample in england and wales$"), "Census 2011 Individual Secure Sample England and Wales"),
    (re.compile(r"(?i)^census 2011 england and wales:\s*individual sample$"), "Census 2011 Individual Sample England and Wales"),
    (re.compile(r"(?i)^secure census 2011 origin\s*/\s*destination$"), "Census 2011 Origin-Destination"),
    (re.compile(r"(?i)^census 2011 origin\s*/\s*destination$"), "Census 2011 Origin-Destination"),
    (re.compile(r"(?i)^census 2011 origin-destination$"), "Census 2011 Origin-Destination"),
    (re.compile(r"(?i)^census 2011 origin/destination:\s*flow$"), "Census 2011 Origin-Destination Flow"),
    (re.compile(r"(?i)^2011 census:\s*aggregate$"), "Census 2011 Aggregate"),
    (re.compile(r"(?i)^2011 census ethnicity$"), "Census 2011 Ethnicity"),
    (re.compile(r"(?i)^census 2011 england$"), "Census 2011 England"),
    (re.compile(r"(?i)^census 2011 ni$"), "Census 2011 Northern Ireland"),
    (re.compile(r"(?i)^secure census 2011 england$"), "Census 2011 England"),
    (re.compile(r"(?i)^census 2011 e&w household structure for covid-19 models$"), "Census 2011 England and Wales Household Structure for COVID-19 Models"),
    (re.compile(r"(?i)^census 2011 england and wales household structure for covid-19 models$"), "Census 2011 England and Wales Household Structure for COVID-19 Models"),
    (re.compile(r"(?i)^census 2021 england and wales$"), "Census 2021 England and Wales"),
    (re.compile(r"(?i)^2021 census data welsh household$"), "Census Wales 2021 Household"),
    (re.compile(r"(?i)^indexed census 2021$"), "Census 2021 Indexed"),
    (re.compile(r"(?i)^census 2021 10% sample$"), "Census 2021 10% Sample"),
    (re.compile(r"(?i)^census 2021 comprehensive microdata \(c21cm\)$"), "Census 2021 Comprehensive Microdata"),
    (re.compile(r"(?i)^census 21 comprehensive microdata$"), "Census 2021 Comprehensive Microdata"),
    (re.compile(r"(?i)^census 2021 household secure microdata sample$"), "Census 2021 Household Secure Microdata Sample"),
    (re.compile(r"(?i)^census 2021 household secure microdata sample in england and wales$"), "Census 2021 Household Secure Microdata Sample England and Wales"),
    (re.compile(r"(?i)^census 2021 secure origin destination tables for england and wales$"), "Census 2021 Origin-Destination Tables England and Wales"),
    (re.compile(r"(?i)^census non response link study 2021 england and wales$"), "Census 2021 Non-Response Link Study England and Wales"),
    (re.compile(r"(?i)^census non response link study 2021 england and wales indexed$"), "Census 2021 Non-Response Link Study England and Wales Indexed"),
    (re.compile(r"(?i)^northern ireland census 2021 census microdata$"), "Northern Ireland Census 2021 Microdata"),
    (re.compile(r"(?i)^absences and english school census$"), "English School Census Absences"),
    (re.compile(r"(?i)^northern ireland school census$"), "Northern Ireland School Census"),
    (re.compile(r"(?i)^annual survey of hours and earnings linked to 2011 census$"), "Annual Survey of Hours and Earnings linked to Census 2011"),
    (re.compile(r"(?i)^annual survey of hours and earnings census 2011 linked$"), "Annual Survey of Hours and Earnings linked to Census 2011"),
    (re.compile(r"(?i)^annual survey of hours and earnings linked to 2011 census england and wales$"), "Annual Survey of Hours and Earnings linked to Census 2011 England and Wales"),
    (re.compile(r"(?i)^annual survey for hours and earnings / census 2011 linked datase$"), "Annual Survey of Hours and Earnings linked to Census 2011"),
    (re.compile(r"(?i)^2011 census linked to benefits and income$"), "Census 2011 linked to Benefits and Income"),
    (re.compile(r"(?i)^linked ni census-ashe$"), "Northern Ireland Census linked to ASHE"),
    (re.compile(r"(?i)^nursing and midwifery council register - uk linked to census 2021$"), "Nursing and Midwifery Council Register linked to Census 2021"),
    (re.compile(r"(?i)^census 2011 and 2021 england and wales$"), "Census 2011 and Census 2021 England and Wales"),
    (re.compile(r"(?i)^census 2011 100% household and individual - england an$"), "Census 2011 Household and Individual England and Wales"),
    (re.compile(r"(?i)^integrated census microdata(?: .*)?$"), "Integrated Census Microdata"),
    (re.compile(r"(?i)^census data 1981$"), "Census 1981"),
    (re.compile(r"(?i)^census microdata 9% sample$"), "Census Microdata 9% Sample"),
    (re.compile(r"(?i)^census 2001$"), "Census 2001"),
    (re.compile(r"(?i)^ashe$"), "Annual Survey of Hours and Earnings (ASHE)"),
    (re.compile(r"(?i)^annual survey of hours$"), "Annual Survey of Hours and Earnings (ASHE)"),
    (re.compile(r"(?i)^annual survey of hours and earnings longitudinal(?: and linked to hmrc)?$"), "Annual Survey of Hours and Earnings Longitudinal"),
    (re.compile(r"(?i)^ashe longitudinal(?: data(?: england(?: and wales)?| great britain england)?)?$"), "Annual Survey of Hours and Earnings Longitudinal"),
    (
        re.compile(
            r"(?i)^(?:administrative data \| )?agricultural research collection"
            r"(?: \(ad\|arc\))?$"
        ),
        "Administrative Data | Agricultural Research Collection (AD|ARC)",
    ),
    (
        re.compile(r"(?i)^ad\|arc phase 2 - census 21 unlinked$"),
        "Administrative Data | Agricultural Research Collection (AD|ARC)",
    ),
    (
        re.compile(r"(?i)^education and child health insights from linked(?: data)?$"),
        "Education and Child Health Insights from Linked Data (ECHILD)",
    ),
    (
        re.compile(r"(?i)^education and child health insights from linked data research data$"),
        "Education and Child Health Insights from Linked Data (ECHILD)",
    ),
    (
        re.compile(r"(?i)^education and child health insights from linked data research database$"),
        "Education and Child Health Insights from Linked Data (ECHILD)",
    ),
    (re.compile(r"(?i)^annual business survey$"), "Annual Business Survey (ABS)"),
    (re.compile(r"(?i)^annual population survey$"), "Annual Population Survey (APS)"),
    (re.compile(r'(?i)^annual population survey\s*"*\s*aps persons$'), "Annual Population Survey Persons"),
    (re.compile(r"(?i)^annual population survey persons?$"), "Annual Population Survey Persons"),
    (re.compile(r"(?i)^annual survey of hours and earnings$"), "Annual Survey of Hours and Earnings (ASHE)"),
    (re.compile(r"(?i)^business enterprise research and development$"), "Business Enterprise Research and Development (BERD)"),
    (re.compile(r"(?i)^business insights and conditions survey$"), "Business Insights and Conditions Survey (BICS)"),
    (re.compile(r"(?i)^business structure database$"), "Business Structure Database (BSD)"),
    (re.compile(r"(?i)^business register and employment survey$"), "Business Register and Employment Survey (BRES)"),
    (re.compile(r"(?i)^crime survey for england and wales$"), "Crime Survey for England and Wales (CSEW)"),
    (re.compile(r"(?i)^covid-19 infection survey$"), "COVID-19 Infection Survey (CIS)"),
    (re.compile(r"(?i)^covid-19 schools infection survey linked to test and trace$"), "COVID-19 Infection Survey linked to NHS Test and Trace"),
    (re.compile(r"(?i)^inter-departmental business register$"), "Inter-Departmental Business Register (IDBR)"),
    (re.compile(r"(?i)^labour force survey$"), "Labour Force Survey (LFS)"),
    (re.compile(r"(?i)^living costs and food survey$"), "Living Costs and Food Survey (LCF)"),
    (re.compile(r"(?i)^longitudinal education outcomes$"), "Longitudinal Education Outcomes (LEO)"),
    (re.compile(r"(?i)^longitudinal education$"), "Longitudinal Education Outcomes (LEO)"),
    (re.compile(r"(?i)^longitudinal small business survey$"), "Longitudinal Small Business Survey (LSBS)"),
    (re.compile(r"(?i)^management and expectations survey$"), "Management and Expectations Survey (MES)"),
    (re.compile(r"(?i)^new earnings survey$"), "New Earnings Survey (NES)"),
    (re.compile(r"(?i)^ons longitudinal study$"), "ONS Longitudinal Study (LS)"),
    (re.compile(r"(?i)^longitudinal study$"), "ONS Longitudinal Study (LS)"),
    (re.compile(r"(?i)^longitudinal study of england and wales$"), "ONS Longitudinal Study (LS)"),
    (re.compile(r"(?i)^longitudinal study 1971$"), "ONS Longitudinal Study 1971"),
    (re.compile(r"(?i)^opinions and lifestyle survey$"), "Opinions and Lifestyle Survey (OPN)"),
    (re.compile(r"(?i)^uk innovation survey$"), "UK Innovation Survey (UKIS)"),
    (re.compile(r"(?i)^universities and colleges admissions service(?: \(UCAS\))?$"), "Universities and Colleges Admissions Service (UCAS)"),
    (re.compile(r"(?i)^wealth and assets survey$"), "Wealth and Assets Survey (WAS)"),
    (re.compile(r"(?i)^workplace employment relations study$"), "Workplace Employment Relations Study (WERS)"),
    (re.compile(r"(?i)^interdepartmental business register$"), "Inter-Departmental Business Register (IDBR)"),
    (re.compile(r"(?i)^registered deaths$"), "Death Registrations"),
    (re.compile(r'(?i)^community innovation survey\s*"\s*united kingdom innovation survey$'), "Community Innovation Survey"),
    # -- LEO --
    (re.compile(r"(?i)^longitudinal education outcomes.*"), "Longitudinal Education Outcomes (LEO)"),
    (re.compile(r"(?i)^leo\b.*"), "Longitudinal Education Outcomes (LEO)"),
    # -- ASHE --
    (re.compile(r"(?i)^annual survey (?:for|of) hours and earnings$"), "Annual Survey of Hours and Earnings (ASHE)"),
    (re.compile(r"(?i)^annual survey (?:for|of) hours and earnings \(ASHE\)$"), "Annual Survey of Hours and Earnings (ASHE)"),
    (re.compile(r"(?i)^annual survey (?:for|of) hours and earnings longitudinal(?:\s.*)?$"), "Annual Survey of Hours and Earnings Longitudinal"),
    (re.compile(r"(?i)^annual survey (?:for|of) hours and earnings\s*/\s*census(?:\s.*)?$"), "Annual Survey of Hours and Earnings linked to Census 2011"),
    # -- BRES --
    (re.compile(r"(?i)^business register (?:and )?employment surveys?(?:\s*\(BRES\))?$"), "Business Register and Employment Survey (BRES)"),
    # -- Monthly wages survey --
    (re.compile(r"(?i)^monthly wages? and salari?(?:y|es) surveys?$"), "Monthly Wages and Salary Survey"),
    # -- Employer skills survey --
    (re.compile(r"(?i)^employer skills? surveys?$"), "Employer Skills Survey"),
    (re.compile(r"(?i)^national employers? skills? survey.*"), "National Employer Skills Survey"),
    # -- Wealth and Assets Survey --
    (re.compile(r"(?i)^wealth and assets? survey$"), "Wealth and Assets Survey (WAS)"),
    # -- Living Costs and Food Survey --
    (re.compile(r"(?i)^living costs? and food surveys?$"), "Living Costs and Food Survey (LCF)"),
    (re.compile(r"(?i)^safeguarded living costs? and food surveys?$"), "Safeguarded Living Costs and Food Survey"),
    # -- UK Manufacturers Sales (apostrophe, special char, and spacing variants) --
    (re.compile(r"(?i)^uk manufacturers['\u2019\u00e8\u00b4]?\s*(?:['\u2019]?\s*)sales by products? survey"), "UK Manufacturers' Sales by Product Survey"),
    # -- Death registrations base forms --
    (re.compile(r"(?i)^births? registrations?$"), "Birth Registrations in England and Wales"),
    (re.compile(r"(?i)^deaths? registrations?$"), "Death Registrations"),
    (re.compile(r"(?i)^deaths? registrations?\s+(?:in\s+)?england and wales$"), "Death Registrations in England and Wales"),
    (re.compile(r"(?i)^deaths? registrations?\s+(?:in\s+)?england and wales\s+indexed$"), "Death Registrations in England and Wales Indexed"),
    (re.compile(r"(?i)^(?:ons )?deaths? registrations? finalised$"), "Death Registrations Finalised"),
    (re.compile(r"(?i)^(?:ons )?deaths? registrations?$"), "Death Registrations"),
    (re.compile(r"(?i)^births? registrations?\s+(?:in\s+)?england and wales$"), "Birth Registrations in England and Wales"),
    # (Death registration data provisional monthly extracts — handled below at line ~179)
    # -- International Trade in Services --
    (re.compile(r"(?i)^international trade in services(?:\s+survey)?$"), "International Trade in Services"),
    (re.compile(r"(?i)^annual international trade in services(?:\s+survey)?$"), "Annual International Trade in Services"),
    # -- Capital Stock --
    (re.compile(r"(?i)^capital stocks?$"), "Capital Stock Dataset"),
    # -- Opinions and Lifestyle Survey --
    (re.compile(r"(?i)^(?:ONS )?opinions and lifestyle survey$"), "Opinions and Lifestyle Survey (OPN)"),
    # -- Coronavirus social impacts --
    (re.compile(r"(?i)^coronavirus and the social impacts? on (?:Great Britain|GB)$"), "Coronavirus and the Social Impacts on Great Britain"),
    (re.compile(r"(?i)^coronavirus and the social(?:\s+impacts?\s+on)?$"), "Coronavirus and the Social Impacts on Great Britain"),
    # -- Quarterly Acquisitions survey --
    (re.compile(r"(?i)^quarterly a[cq]uisitions and disposals of capital assets survey"), "Quarterly Acquisitions and Disposals of Capital Assets Survey"),
    # -- Inter-Departmental Business Register --
    (re.compile(r"(?i)^longitudinal inter[- ]?departmental business register"), "Longitudinal Inter-Departmental Business Register"),
    (re.compile(r"(?i)^linked trade-in-goods/inter[- ]?departmental business register$"), "Linked Trade-in-Goods/Inter-Departmental Business Register"),
    (re.compile(r"(?i)^linked trade-in-goods/idbr dataset$"), "Linked Trade-in-Goods/IDBR"),
    # -- Annual Respondents Database --
    (re.compile(r"(?i)^annual respondents? database\s*(?:\(ARD\s*[X2x]\))?$"), "Annual Respondents Database"),
    (re.compile(r"(?i)^annual respondents? database\s*(?:ARD\s*)?[Xx]$"), "Annual Respondents Database X"),
    (re.compile(r"(?i)^annual respondents? database\s*[Xx]\s*\(ARD\s*[Xx]\)$"), "Annual Respondents Database X"),
    (re.compile(r"(?i)^annual respondents? database\s*(?:ARD\s*)?2$"), "Annual Respondents Database 2"),
    (re.compile(r"(?i)^annual respondents? database\s*(?:\(ARD\s*2\))$"), "Annual Respondents Database 2"),
    # -- Broad Economy Sales --
    (re.compile(r"(?i)^(?:broad|board) economy sales and exports"), "Broad Economy Sales and Exports"),
    # -- Mergers and Acquisitions --
    (re.compile(r"(?i)^(?:RETIRED )?mergers and acquisitions(?:\s+survey)?$"), "Mergers and Acquisitions Survey"),
    # -- Consumer Prices --
    (re.compile(r"(?i)^consumer (?:and retail )?prices? (?:indices|indicies|index)$"), "Consumer Prices Index"),
    # -- E-Commerce Survey --
    (re.compile(r"(?i)^E-Commerce surveys?$"), "E-Commerce Survey"),
    (re.compile(r"(?i)^E-Commerce and digital economy survey$"), "E-Commerce and Digital Economy Survey"),
    # -- GRADE --
    (re.compile(r"(?i)^GRading and Admissions Data England"), "GRading and Admissions Data England (GRADE)"),
    # -- Prices survey Microdata --
    (re.compile(r"(?i)^prices survey microdata"), "Prices Survey Microdata"),
    # -- Death registration data provisional monthly extracts (various dash/space styles) --
    (re.compile(r"(?i)^death registration\s*(?:data)?\s*[-\s]*provisional monthly extracts"), "Death Registration Data - Provisional Monthly Extracts"),
    # -- Business Structure Database Longitudinal --
    (re.compile(r"(?i)^business structure database \(BSD\)$"), "Business Structure Database (BSD)"),
    (re.compile(r"(?i)^business structure database[\s:/-]+longitudinal$"), "Business Structure Database Longitudinal"),
    # -- Business Enterprise Research (and)? Development --
    (re.compile(r"(?i)^business enterprise research (?:and )?development$"), "Business Enterprise Research and Development (BERD)"),
    # -- DBT prefix leaking into dataset name --
    (re.compile(r"(?i)^DBT:\s*"), None),
    # -- Annual gas and electricity consumption --
    (re.compile(r"(?i)^annual gas and electricity consumption at (?:the )?meter level$"), "Annual Gas and Electricity Consumption at Meter Level"),
    # -- Growing Up in England dash variants --
    (re.compile(r"(?i)^growing up in england wave 1$"), "Growing Up in England Wave 1 (GUIE)"),
    (re.compile(r"(?i)^growing up in england wave 2$"), "Growing Up in England Wave 2 (GUIE)"),
    (re.compile(r"(?i)^growing up in england wave 2\s*[-\s]+exclusions$"), "Growing Up in England Wave 2 - Exclusions"),
    (re.compile(r"(?i)^growing up in england wave 2\s*[-\s]+children in need$"), "Growing Up in England Wave 2 (GUIE)"),
    # -- Linked Census and death (truncated) --
    (re.compile(r"(?i)^linked census and death$"), "Linked Census and Death Occurrences"),
    (re.compile(r"(?i)^linked census and death occurrences$"), "Linked Census and Death Occurrences"),
    (re.compile(r"(?i)^moj data first cross-justice system linking dataset england and wales$"), "MoJ Data First Cross-Justice System Linking Dataset"),
    (re.compile(r"(?i)^moj data first cross-justice system linking$"), "MoJ Data First Cross-Justice System Linking Dataset"),
    (re.compile(r"(?i)^administrative data \| agriculture research collection$"), "Administrative Data | Agricultural Research Collection (AD|ARC)"),
    (re.compile(r"(?i)^annual survey of hours and earnings linked to paye and self-assessment(?: data)?(?: great britain)?$"), "Annual Survey of Hours and Earnings linked to PAYE and Self-Assessment"),
    # -- ONS COVID-19 Weekly Opinions Survey --
    (re.compile(r"(?i)^(?:ONS )?COVID-19 Weekly Opinions Survey$"), "COVID-19 Weekly Opinions Survey"),
    # -- KIntegrated Data Service (leading K artifact) --
    (re.compile(r"(?i)^KIntegrated Data Service"), "Integrated Data Service"),
    # -- Department for Education prefix leak --
    (re.compile(r"(?i)^Department for Education:?\s*"), None),
    # -- Bespoke NCVO --
    (re.compile(r"(?i)^bespoke\s*-?\s*national council for voluntary organisations?$"), "Bespoke National Council for Voluntary Organisations"),
    # -- EOL --
    (re.compile(r"(?i)^eol(?:\s+dataset)?(?:\s*\(\d{4}[-\u2013]\d{4}\))?$"), "EOL"),
    # -- ABS with household suffix --
    (re.compile(r"(?i)^annual business survey household$"), "Annual Business Survey (ABS)"),
    (re.compile(r"(?i)^annual business survey in great britain$"), "Annual Business Survey (ABS)"),
    # -- MoJ Data First Prisoner Custodial Journey Level --
    (re.compile(r"(?i)^moj data first prisoner custodial journey(?:\s+level)?$"), "MoJ Data First Prisoner Custodial Journey"),
]

TRUNCATION_HINTS = (
    "datase",
    "england an",
    "for the",
)

REVIEW_CLEARED_ALIASES = {
    "annual survey for hours and earnings / census 2011 linked datase",
    "census 2011 100% household and individual - england an",
    "2022 census",
}

MULTI_DATASET_PATTERNS = (
    re.compile(r";"),
    re.compile(r"\b[A-Z]{3,}\);"),
)

ESCAPED_PROVIDER_COMPOUND_PATTERNS = (
    re.compile(r"\bEconomic and Social Research Council\s*:", re.IGNORECASE),
    re.compile(r"\bDBT\s*:", re.IGNORECASE),
    re.compile(r"\bDepartment For Education\s*:", re.IGNORECASE),
    re.compile(r"\bCompanies House\s*-\s*Census\s+\d{4}\b", re.IGNORECASE),
)

UNUSUAL_PUNCTUATION_RE = re.compile(r"[:;/]{2,}|[()]{2,}")


def _clean_datasets_text(raw: str) -> str:
    text = re.sub(r"_x000D_", " ", raw)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\r", "\n")
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    text = DATASET_PROVIDER_RE.sub(lambda m: ("\n" if m.start() > 0 else "") + m.group(0), text)
    return text.strip()


def _split_dataset_parts(rest: str) -> list[str]:
    parts = re.split(r"\s*,\s*|\s*;\s*|\s+&\s+", rest.strip())
    return [part.strip(" ,;:") for part in parts if part.strip(" ,;:")]


def _is_valid_dataset_fragment(name: str) -> bool:
    cleaned = name.strip()
    if not cleaned:
        return False
    lowered = cleaned.lower()
    bare = re.sub(r"[^A-Za-z0-9]+", "", cleaned)
    if lowered in INVALID_DATASET_FRAGMENTS:
        return False
    if re.fullmatch(r"(19|20)\d{2}", cleaned):
        return False
    if len(cleaned.split()) == 1 and len(bare) <= 8 and cleaned not in ALLOWED_SHORT_DATASET_NAMES:
        return False
    return True


def _basic_cleanup(name: str) -> str:
    name = name.strip()
    if not name:
        return name

    name = (
        name
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u00a0", " ")
        .replace("\u00ad", "")
        .replace("\u2122", "'")
    )
    name = re.sub(r"\s+", " ", name).strip()
    name = name.rstrip(".,;:'\"&")
    return name


def _apply_systematic_normalisation(name: str) -> str:
    original = name
    if re.fullmatch(
        r"(?i)education and child health insights from linked data research data(?:base)?",
        name.strip(),
    ):
        return "Education and Child Health Insights from Linked Data (ECHILD)"

    name = re.sub(
        r"\s*-\s*(UK|GB|Great Britain|England|England and Wales|Wales|Scotland|Northern Ireland)\s*$",
        "",
        name,
        flags=re.IGNORECASE,
    ).strip()
    if name.lower() in GEOGRAPHY_SUFFIX_FALLBACK_NAMES:
        name = original

    noise_re = re.compile(r"\s+(?:data|dataset|datasets|statistics|records?)\s*$", re.IGNORECASE)
    prev = None
    while name != prev:
        prev = name
        name = noise_re.sub("", name).strip()

    geo_nodash = re.sub(r"\s+(UK|GB)\s*$", "", name).strip()
    if geo_nodash and geo_nodash.lower() not in GEOGRAPHY_SUFFIX_FALLBACK_NAMES and len(geo_nodash) > 5:
        name = geo_nodash

    # Strip trailing year-ranges: "(1997-2024)", "2005-2022", "1973 onwards)", "(2004-2023 secure access)"
    name = re.sub(r"\s*\(?\d{4}\s*[-\u2013]\s*\d{4}(?:\s*\))?\s*$", "", name).strip()
    name = re.sub(r"\s*\(?\d{4}\s+onwards\)?\s*$", "", name).strip()
    name = re.sub(r"\s*\(\d{4}[-\u2013]\d{4}\s+secure access\)\s*$", "", name).strip()

    name = re.sub(r"(?i)^MOJ\b", "MoJ", name)
    name = re.sub(r"(?i)^RETIRED\s+MOJ\b", "RETIRED MoJ", name)
    name = re.sub(
        r"(?i)^(RETIRED\s+)?Ministry of Justice Data First\b",
        lambda m: (m.group(1).upper() if m.group(1) else "") + "MoJ Data First",
        name,
    )
    name = re.sub(
        r"(?i)^(RETIRED\s+)?Data First\b",
        lambda m: (m.group(1).upper() if m.group(1) else "") + "MoJ Data First",
        name,
    )

    moj_match = re.match(r"^((?:RETIRED )?MoJ Data First )(.*)", name)
    if moj_match:
        name = moj_match.group(1) + moj_match.group(2).title()

    name = re.sub(r"(?i)\bCovid[\s-]*19\b", "COVID-19", name)
    name = re.sub(r"(?i)\bE[\s-]+[Cc]ommerce\b", "E-Commerce", name)
    name = name.replace("Developement", "Development")
    name = name.replace("Probabation", "Probation")
    name = re.sub(r"\bAquisitions\b", "Acquisitions", name)
    name = re.sub(r"\bLongit?udunal\b", "Longitudinal", name)
    name = re.sub(r"\bLongistudinal\b", "Longitudinal", name)
    name = re.sub(r"\bIndicies\b", "Indices", name)
    name = re.sub(r"Surv\s+ey\b", "Survey", name)
    name = re.sub(r"Busin\s+ess\b", "Business", name)
    name = re.sub(r"InnovationSurvey\b", "Innovation Survey", name)
    name = re.sub(r"\bInter\s?Departmental\b", "Inter-Departmental", name)
    name = re.sub(r"Inter-Departmental-Business-Register", "Inter-Departmental Business Register", name)

    lfs_match = re.match(r"^(Labour Force Survey)\s*[-(/]?\s*(Person|Household|Longitudinal)s?\)?(.*)", name)
    if lfs_match:
        name = f"{lfs_match.group(1)} {lfs_match.group(2)}{lfs_match.group(3)}"

    aps_match = re.match(r"^(Annual Population Survey)\s*[-(/]?\s*(Person|Household)\)?(.*)", name)
    if aps_match:
        name = f"{aps_match.group(1)} {aps_match.group(2)}{aps_match.group(3)}"

    # Understanding Society sub-type delimiter: "- BHPS" / "- UKHLS" → "BHPS" / "UKHLS"
    us_match = re.match(r"^(Understanding Society)\s*-\s*(BHPS|UKHLS)\b(.*)", name)
    if us_match:
        name = f"{us_match.group(1)} {us_match.group(2)}{us_match.group(3)}"

    # ONS prefix on Longitudinal Study
    name = re.sub(r"^ONS Longitudinal Study of England and Wales$", "Longitudinal Study of England and Wales", name)

    name = re.sub(r"\bWell-?[Bb]eing\b", "Well-Being", name)
    name = re.sub(r"^(Annual Population) Surveys$", r"\1 Survey", name)
    name = re.sub(r"^(Living Costs and Food) Surveys$", r"\1 Survey", name)

    lower = name.lower()
    case_canonical = {
        "business structure database": "Business Structure Database",
        "annual population survey": "Annual Population Survey",
        "annual purchases survey": "Annual Purchases Survey",
        "low carbon and renewable energy economy survey": "Low Carbon and Renewable Energy Economy Survey",
        "business enterprise research and development": "Business Enterprise Research and Development",
    }
    if lower in case_canonical:
        name = case_canonical[lower]

    name = re.sub(r"(?i)\blinked with\b", "linked to", name)
    name = re.sub(r"(?i)\bLinked to\b", "linked to", name)
    name = re.sub(r"(?i)\bself[- ]assessment\b", "Self-Assessment", name)
    name = re.sub(r"(?i)\bcross[- ]justice system linking\b", "Cross-Justice System Linking", name)
    return name


def _looks_compound_or_linked(name: str) -> bool:
    if any(pattern.search(name) for pattern in MULTI_DATASET_PATTERNS):
        return True
    if any(pattern.search(name) for pattern in ESCAPED_PROVIDER_COMPOUND_PATTERNS):
        return True
    return False


def _has_truncation_hint(raw: str) -> bool:
    lowered = raw.lower().strip()
    return any(lowered.endswith(hint) for hint in TRUNCATION_HINTS)


def _looks_unresolved(raw: str, canonical: str, match_type: str) -> bool:
    lowered = raw.lower()
    if lowered in REVIEW_CLEARED_ALIASES:
        return False
    if match_type == "unresolved":
        return True
    year_only_census = re.fullmatch(r"(19|20)\d{2}\s+census", lowered)
    if year_only_census and lowered not in {"2001 census", "2011 census", "2021 census"}:
        return True
    if _has_truncation_hint(raw):
        return True
    if any(pattern.search(raw) for pattern in MULTI_DATASET_PATTERNS):
        return True
    if UNUSUAL_PUNCTUATION_RE.search(raw):
        return True
    if canonical == raw and ("..." in raw or "  " in raw):
        return True
    return False


def describe_dataset_normalisation(raw_name: str) -> dict[str, object]:
    raw = raw_name.strip()
    if not raw:
        return {
            "raw_dataset": raw_name,
            "canonical_dataset_name": raw,
            "match_type": "identity",
            "needs_review": 0,
        }

    cleaned = _basic_cleanup(raw)
    system_normalised = _apply_systematic_normalisation(cleaned)

    if _looks_compound_or_linked(raw):
        needs_review = 1
        return {
            "raw_dataset": raw,
            "canonical_dataset_name": system_normalised,
            "match_type": "compound_or_multi_dataset",
            "needs_review": needs_review,
        }

    for pattern, canonical in DATASET_ALIASES:
        match = pattern.match(system_normalised)
        if not match:
            continue
        if canonical is not None:
            match_type = "alias"
            final_name = canonical
        else:
            remainder = system_normalised[match.end():].strip()
            final_name = remainder if remainder else system_normalised
            match_type = "normalised_format"
        needs_review = 1 if _looks_unresolved(raw, final_name, match_type) else 0
        return {
            "raw_dataset": raw,
            "canonical_dataset_name": final_name,
            "match_type": match_type,
            "needs_review": needs_review,
        }

    if system_normalised != raw:
        match_type = "normalised_format"
        final_name = system_normalised
    elif _looks_unresolved(raw, raw, "identity"):
        match_type = "unresolved"
        final_name = raw
    else:
        match_type = "identity"
        final_name = raw

    needs_review = 1 if _looks_unresolved(raw, final_name, match_type) else 0
    return {
        "raw_dataset": raw,
        "canonical_dataset_name": final_name,
        "match_type": match_type,
        "needs_review": needs_review,
    }


def normalise_dataset_name(name: str) -> str:
    meta = describe_dataset_normalisation(name)
    return str(meta["canonical_dataset_name"])


def dataset_family_for(canonical_name: str) -> str | None:
    if not canonical_name:
        return None

    name = canonical_name.strip()
    lowered = name.lower()

    if ";" in name:
        if lowered.startswith("moj data first"):
            return "Data First"
        return None

    if "covid-19" in lowered:
        return "COVID-19"

    if (
        lowered.startswith("census ")
        or lowered.startswith("census wales ")
        or lowered.startswith("northern ireland census ")
        or lowered.startswith("integrated census microdata")
        or lowered.startswith("census microdata ")
    ):
        return "Census"

    if lowered == "linked census and death occurrences":
        return "Census"

    if lowered in {
        "death registrations",
        "death registrations in england and wales",
        "death registrations in england and wales indexed",
        "death registrations finalised",
        "ons death registrations",
    }:
        return "Death Registrations"

    if "school census" in lowered:
        return "School Census"

    if lowered.startswith("annual business survey"):
        return "ABS"

    if lowered.startswith("annual population survey"):
        return "APS"

    if "labour force survey" in lowered or lowered.startswith("quarterly labour force survey") or lowered.startswith("longitudinal labour force survey"):
        return "Labour Force Survey"

    if lowered.startswith("growing up in england wave"):
        return "GUIE"

    if lowered.startswith("annual survey of hours and earnings linked to paye and self-assessment"):
        return "ASHE"

    if lowered.startswith("annual survey of hours and earnings linked to census"):
        return "ASHE-linked"

    if (
        lowered == "annual survey of hours and earnings (ashe)"
        or lowered.startswith("ashe longitudinal")
        or lowered.startswith("annual survey of hours and earnings")
        or lowered.startswith("annual survey for hours and earnings")
    ):
        return "ASHE"

    if lowered.startswith("longitudinal education outcomes"):
        return "LEO"

    if lowered.startswith("moj data first"):
        return "Data First"

    if lowered.startswith("retired moj data first"):
        return "Data First"

    if (
        lowered.startswith("administrative data | agricultural research collection")
        or lowered.startswith("bespoke admin data - agricultural research collection")
        or lowered.startswith("bespoke admin data: agricultural research collection")
    ):
        return "AD|ARC"

    if (
        lowered.startswith("understanding society")
        or lowered.startswith("uk household longitudinal study")
        or "bhps" in lowered
    ):
        return "Understanding Society"

    return None


def _yield_dataset_parts(line: str, provider: str, rest: str):
    for part in _split_dataset_parts(rest):
        if _is_valid_dataset_fragment(part):
            yield line, provider, part


def iter_dataset_entries(raw: str):
    if not isinstance(raw, str) or not raw.strip():
        return
    cleaned = _clean_datasets_text(raw)
    current_provider = ""
    current_rest_parts: list[str] = []
    current_line_parts: list[str] = []

    def flush_current():
        nonlocal current_rest_parts, current_line_parts
        if not current_rest_parts:
            return
        rest = " ".join(part.strip() for part in current_rest_parts if part.strip())
        line = " ".join(part.strip() for part in current_line_parts if part.strip())
        for emitted in _yield_dataset_parts(line, current_provider, rest):
            yield emitted
        current_rest_parts = []
        current_line_parts = []

    for line in cleaned.split("\n"):
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            yield from flush_current()
            provider, rest = line.split(":", 1)
            current_provider = provider.strip()
            current_rest_parts = [rest]
            current_line_parts = [line]
        else:
            current_rest_parts.append(line)
            current_line_parts.append(line)
    yield from flush_current()


def normalise_provider_name(name: str) -> str:
    provider = str(name or "").strip()
    return PROVIDER_ALIASES.get(provider, provider)


def infer_provider_name(name: str) -> str:
    provider = str(name or "").strip()
    return SECURE_RESEARCH_SERVICE_PROVIDER_ALIASES.get(provider, normalise_provider_name(provider))


def parse_datasets(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, proj in df.iterrows():
        raw = proj.get("Datasets Used", "")
        if not isinstance(raw, str) or not raw.strip():
            continue
        pid = proj["Project ID"]
        year = proj["Year"]
        quarter_date = proj["quarter_date"]
        secure_research_service = proj.get("Secure Research Service", "")
        for _, provider, part in iter_dataset_entries(raw):
            dataset = normalise_dataset_name(part)
            if not _is_valid_dataset_fragment(dataset):
                continue
            provider_name = normalise_provider_name(provider)
            if provider_name == "Unknown / Unspecified":
                provider_name = infer_provider_name(secure_research_service)
            rows.append({
                "Project ID": pid,
                "Year": year,
                "quarter_date": quarter_date,
                "provider": provider_name,
                "dataset": dataset,
                "dataset_full": f"{provider}: {part}" if provider else part,
            })
    return pd.DataFrame(rows)
