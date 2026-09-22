# Adjudication rule reference: Taxonomy Data Dictionary -- DEA Project Classification Ontology v3.4 rc2

Generated 2026-09-22 from `taxonomy_data_dictionary.yaml`, dictionary version 1.0-rc2, ontology v3.4-rc2.
Source SHA-256 `7ddbf1bb5ae4588c82c7c23f90bd96885684ff1ec71382f6403c36c4b89e31de`.

This is the rule text the production model and the scratch coders worked to, and
protocol §9.2 makes it an input to Stage 1. The primary adjudicator and the second
reviewer use this same version. Do not edit it, and do not substitute a later
dictionary; cite it by category and rule type when a finding rests on a rule.

It contains rules, not worked answers. The coders' keyed training examples are
excluded, because they were selected from records where the two models agreed.

**Older names in the quoted rules.** The frozen dictionary names its layers
internally, and the rule text below is reproduced exactly, so those names
remain. Read Layer A as Research Domains, Layer C as Analytical Purposes, and
Layer B as the retired linkage categories, which are no longer assignable.
Headings in this document use the current names.

## Assignment principles

### Layer cardinality

- **Layer A -- domain:** one or more
- **Layer C -- purpose:** one or two
- **Cross-cutting tag:** zero or more / boolean facets

### Assigning a Research Domain

Assign every Layer A domain where the register entry gives substantive evidence that the project analyses that domain; domains are non-hierarchical, so where more than one applies, assign all of them with no primary/secondary ordering. For example, a project about how employment changes affect household debt may receive both Labour Market & Employment and Poverty, Wealth & Living Standards.

### Assigning an Analytical Purpose

Assign a Layer C purpose according to the analytical operation visible from the register entry: monitoring patterns, tracking exposure-outcome relationships, evaluating a policy or intervention, analysing trajectories, studying service-system interaction, predicting or identifying risk, or developing methods or infrastructure. Assign one or two purposes where more than one operation is central; assign two only where both are genuinely substantive.

### Unclear from Register Entry

"Unclear from Register Entry" appears in Layer A and Layer C. In each active layer the label describes insufficient evidence in the public register entry — not research that is inherently unclassifiable. Assign it only where the relevant register fields genuinely do not determine the domain or purpose; if the evidence resolves the category, assign the resolved category instead.

### Across layers

- **layer_independence:** Layer A, Layer C, and cross-cutting tags answer different questions. The same element — a policy, dataset, population group, method, or service setting — may inform more than one layer without merging them. Assign the substantive domain, analytical purpose, and any cross-cutting tags independently.
- **evidence_not_keyword_rule:** Do not assign any category solely because a word, dataset, variable, population group, method, or service setting appears in the register entry. Assign a category only where the register fields provide enough evidence that the category is central to the research question, analytical operation, or cross-cutting lens. This rule applies to every layer.
- **register_field_evidence_rule:** Classification draws on the register entry's informative fields — the project title and the dataset field — read together. The title usually provides the research question or analytical framing, while the dataset field can resolve the substantive domain and sometimes the analytical purpose. Do not treat the dataset field as irrelevant to active LLM outputs merely because linkage is now deterministic.
- **domain_purpose_separation:** Domain and purpose are assigned independently. The domain follows the substantive object of the research visible from the register entry — the outcome, system, population process, institution, sector, or mechanism being studied. The purpose follows the analytical operation performed on that object — what the project does with it (for example, monitoring, evaluation, prediction, or trajectory analysis). Because these are different questions, a named policy or programme fixes the purpose without displacing the domain: a study evaluating a housing subsidy is a housing study by domain and a policy-evaluation study by purpose.
- **setting_vs_purpose_rule:** Do not assign a Layer C purpose solely because of where a dataset comes from or where an outcome occurs. The source, provider, or service setting of the data is not the analytical operation. Assign a purpose only when the operation itself matches it. For example, a dataset drawn from a service system does not by itself imply Service Interaction / Systems Analysis — assign that purpose only where service uptake, referrals, pathways, case progression, utilisation, or movement through systems is central to the analysis.
- **tag_lens_rule:** Cross-cutting tags describe analytical lenses, not substantive domains or purposes. Tags should not replace the domain or purpose label. Assign every active cross-cutting tag whose lens or condition is central to the research question; multiple tags may apply to the same project. Do not assign a tag merely because tag-relevant variables or background conditions appear as controls, covariates, sample descriptors, routine stratifiers, or incidental context.

### Domain or purpose for methodology

Data Infrastructure & Methodology (Layer A, a domain) and Methodological / Infrastructure Research (Layer C, a purpose) are related but not equivalent. Assign the Layer A domain when data, methods, measurement, classification, linkage, or statistical infrastructure are the substantive object of the research — what the project is about. Assign the Layer C purpose when the project's analytical operation is to develop, test, validate, improve, document, or demonstrate such a method, measure, data asset, linkage process, or infrastructure — what the project does. The mere use of administrative data, advanced methods, or linkage is not sufficient for either: those are how most modern research is done. They often co-occur, but neither label automatically triggers the other.

### How the dictionary uses examples

The dictionary is rule-driven: category meaning is carried by the definitions, assignment by the inclusion and exclusion rules and metadata principles, and difficult boundaries are illustrated by counterexamples. The examples field is therefore empty for most categories. It is reserved for rare concrete instances that do work the rules cannot easily do in their own prose, such as showing how a cross-cutting tag operates alongside a substantive domain. Examples and counterexamples are authored illustrations, true by construction; they are not validated project-level classifications. A counterexample shows a similar-looking case that falls outside the category and may name an alternative label where that gives useful boundary guidance. Boundary-drawing belongs in the inclusion and exclusion rules; examples and counterexamples illustrate those boundaries but do not define them. Worked classifications of real register projects are not held in this dictionary; they are a separate, validation-track artefact.

## Research Domains

### Labour Market & Employment

**Definition.** Research concerning work, employment, labour-market participation, and workforce dynamics. Includes wages and earnings; employment, unemployment, inactivity and underemployment; job quality; working hours, contracts, gig or platform work, and working conditions; labour supply and demand; occupational, sectoral and geographic mobility; workforce recruitment and retention; skills demand and mismatch; and transitions into, through, or out of work.

**Assign when.** Assign when work, employment, earnings, labour supply or demand, workforce composition, job quality, occupational structure, or labour-market transitions are central to the project, even where the study population is defined by another characteristic.

**Do not assign when.** Do not assign solely because a project mentions income, education, productivity, health, migration, or workers, or where employment or earnings data are used only as background context. Use **Education & Skills** for education systems and qualifications unless labour-market outcomes are central. Use **Poverty, Wealth & Living Standards** for household resources, poverty, wealth, debt, or living standards unless employment, earnings, job quality, or labour-market progression are substantively analysed.

**Counterexample.** Studies whose central object is household resources, saving, debt, wealth, poverty, or living standards, where earnings or employment variables are used only as background characteristics, controls, or contextual measures.

*Why:* Labour-market data can support analysis of household resources without making the project labour-market research. This domain should be assigned only when work, employment, earnings, job quality, labour-market participation, or workforce progression are substantively analysed.

*Instead consider:* Poverty, Wealth & Living Standards

### Education & Skills

**Definition.** Research concerning education, learning, training, skills formation, and transitions through education systems. Includes early years, schools, colleges, universities, qualifications, apprenticeships, admissions, attainment, attendance, teacher workforce issues, childcare, and education-to-work pathways.

**Assign when.** Assign when the project's substantive focus is educational participation, attainment, qualifications, admissions, skills acquisition, training provision, apprenticeship pathways, school absence, teacher supply, education-to-work pathways, or educational progression. This includes projects where later employment or earnings outcomes are used to study the consequences of education, training, or skills pathways.

**Do not assign when.** Do not assign merely because a project uses education data, or where education level is only a subgroup, covariate, or explanatory characteristic and the research question is mainly about employment, earnings, job quality, or occupational progression.

**Counterexample.** Studies of wages or employment progression where education level is only a worker characteristic or subgroup definition.

*Why:* Educational attainment can describe a population without making education systems, skills formation, or educational progression the substantive object of the project.

*Instead consider:* Labour Market & Employment

### Health & Social Care

**Definition.** Research concerning health, illness, mortality, wellbeing, clinical outcomes, health services, public health, mental health, social care, and care-system use. Includes NHS services, hospitals, GP care, palliative care, maternity, morbidity, mortality where health is the research object, and adult or children's social care.

**Assign when.** Assign when health status, illness, clinical outcomes, healthcare access, hospital use, mental health, mortality where health is the research object, morbidity, care needs, social care, clinical risk, or health-focused wellbeing are central to the research question, including where social, housing, educational, or demographic factors are analysed as exposures.

**Do not assign when.** Do not assign mortality projects automatically; assign this domain only where mortality is treated as a health outcome. Use **Migration & Demographics** for mortality as a demographic/population outcome, and use the appropriate Layer C purpose where the focus is service pathways, policy evaluation, or exposure-outcome analysis rather than health/care as the substantive domain.

**Counterexample.** Studies using mortality as a population-composition or migration-comparison measure rather than as a clinical, care, or public-health outcome.

*Why:* Mortality evidence can support demographic research. Assign Health & Social Care only where mortality is treated as a health, clinical, care, or public-health outcome.

*Instead consider:* Migration & Demographics

### Crime & Justice

**Definition.** Research concerning crime, victimisation, public safety, offending, policing, courts, prisons, probation, sentencing, family justice, civil justice, reoffending, and criminal records.

**Assign when.** Assign when the project's substantive focus is offending, victimisation, domestic abuse, policing, courts, sentencing, imprisonment, probation, youth justice, family justice, civil justice, or justice-system outcomes.

**Do not assign when.** Do not assign merely because a project studies risk, fairness, violence, families, children, or public services unless offending, victimisation, legal proceedings, justice-system institutions, or criminal/civil/family justice outcomes are central.

**Counterexample.** Studies about harm, vulnerability, substance misuse, or high-risk groups where the outcome is health, wellbeing, or support need rather than crime or justice-system involvement.

*Why:* Harm or risk language can resemble public-safety research, but the Crime & Justice domain requires criminal behaviour, victimisation, legal proceedings, or justice-system outcomes to be central.

*Instead consider:* Health & Social Care

### Business & Productivity

**Definition.** Research concerning firms, business activity, industrial structure, innovation, productivity, entrepreneurship, trade, exports, foreign direct investment, research and development, business support, and firm-level performance.

**Assign when.** Assign when firms, business behaviour, productivity, innovation, investment, exporting, enterprise support, start-ups, industrial policy, business surveys, enterprise growth, firm performance, or other firm-level outcomes are central, including where a programme, policy, or economic condition defines the analytical design.

**Do not assign when.** Do not assign simply because a project uses firm-level data if the substantive question is mainly about workers, wages, public finance, or environmental impacts. Do not assign where firms are only a data source, setting, delivery channel, or contextual unit rather than the substantive object of analysis.

**Counterexample.** Studies of worker skills, occupational roles, or training needs where firms are not the main object of analysis.

*Why:* Skills or workforce data can be relevant to business research, but this domain requires firm behaviour, productivity, enterprise activity, or business performance to be central.

*Instead consider:* Education & Skills, Labour Market & Employment

### Poverty, Wealth & Living Standards

*Status: relabelled v3.4.*

**Definition.** Research concerning material resources, economic hardship, household living standards, poverty, wealth, debt, savings, benefits, deprivation, food security, cost of living, household income, and distribution of resources.

**Assign when.** Assign when the project's substantive focus is household resources, poverty, household income, wealth, savings, debt, benefits, deprivation, food insecurity, cost-of-living pressures, living standards, economic hardship, or material living conditions.

**Do not assign when.** Do not assign solely because a title mentions pay gaps, employment, socioeconomic status, deprivation indices, or area-level disadvantage. Do not assign where the central question is employment, earnings, job quality, productivity, tax/public spending, or demographic disparity and household resources or material living standards are only contextual.

**Counterexample.** Studies whose object is pay, earnings gaps, or labour-market inequality rather than household resources or material living standards.

*Why:* Pay and earnings inequality can affect living standards, but this domain should be assigned only where household resources, poverty, wealth, debt, benefits, deprivation, or material living standards are central.

*Instead consider:* Labour Market & Employment

### Housing & Planning

**Definition.** Research concerning housing, homelessness, residential conditions, tenure, home ownership, planning systems, neighbourhoods, gentrification, residential mobility, and place-based housing or planning interventions.

**Assign when.** Assign when housing, homelessness, residential tenure, home ownership, housing markets, planning decisions, neighbourhood or residential conditions, residential mobility, or dwelling/residential-environment mechanisms are central to the research question.

**Do not assign when.** Do not assign merely because a project mentions home, place, local area, geography, neighbourhood, or stay-at-home behaviour unless housing, residential conditions, dwelling environments, or planning are substantive objects. Do not assign domestic energy or environmental-exposure cases unless the housing or residential mechanism is central.

**Counterexample.** Studies where home is only the location of pandemic behaviour, remote activity, public-health guidance, or other activity not substantively about housing or residential conditions.

*Why:* The word home should not trigger this domain unless housing quality, tenure, residential conditions, dwelling environments, or planning are the research object. If pandemic framing is central, record it with the COVID-19 & Pandemic cross-cutting tag rather than treating home location as housing research.

*Instead consider:* COVID-19 & Pandemic

### Migration & Demographics

**Definition.** Research concerning population structure, population change, migration, immigration, population mobility, fertility, ageing, mortality as a demographic outcome, census-based population analysis, and demographic composition.

**Assign when.** Assign when the project studies migration flows, immigration policy, population movement, demographic change, fertility, ageing, census populations, population projections, or mortality as a demographic outcome.

**Do not assign when.** Do not assign solely because a project includes ethnicity, age, or migrant status as a subgroup. Use **Labour Market & Employment** for migrant employment or earnings if labour-market outcomes are central. Use **Health & Social Care** for mortality or morbidity where the research question is health-focused.

**Counterexample.** Studies comparing outcomes by ethnicity, nationality, or other demographic characteristics within a labour, justice, health, or education question.

*Why:* Demographic subgroup comparison is not the same as studying population structure, migration, or demographic change. The demographic-disparities/equity tag may still apply where the group comparison is central.

*Instead consider:* Demographic disparities / equity tag

### Environment & Agriculture

**Definition.** Research concerning the natural environment, climate, climate adaptation or resilience, energy, agriculture, farming, land use, pollution, decarbonisation, environmental policy, domestic or industrial energy use, and environmental impacts of economic or social activity.

**Assign when.** Assign when the project studies energy consumption, climate policy, decarbonisation, agriculture, farms, land use, environmental exposure, pollution, green transitions, or environmental dimensions of households, firms, or places.

**Do not assign when.** Do not assign because the word "environment" appears in a non-natural-environment sense, such as "economic environment". Use **Business & Productivity** where an energy or climate programme is primarily framed as firm innovation or productivity rather than environmental outcomes.

**Counterexample.** Studies using environment to mean a social, economic, family, or institutional context rather than the natural environment.

*Why:* The category excludes non-natural-environment uses of environment unless climate, energy, land, pollution, agriculture, or ecological exposure is central.

### Public Finance & Taxation

**Definition.** Research concerning government revenue, taxation, tax compliance, tax credits, public expenditure, public spending, fiscal transfers, business rates, tax reliefs, and fiscal policy.

**Assign when.** Assign when the project studies tax policy, tax behaviour, tax compliance, government expenditure, public spending, fiscal transfers, tax credits, business rates, or distributional impacts of fiscal policy.

**Do not assign when.** Do not assign to private wealth transfers, household wealth, firm investment, or business outcomes unless the public finance/tax mechanism is central. Use **Business & Productivity** for firm outcomes of business-support schemes unless fiscal design or tax/public spending is the main object.

**Counterexample.** Studies of private debt, saving, wealth, or household finances without a tax, benefit, spending, or fiscal-policy mechanism.

*Why:* Household financial circumstances are not public finance unless a public revenue or expenditure mechanism is central.

*Instead consider:* Poverty, Wealth & Living Standards

### Data Infrastructure & Methodology

**Definition.** Research primarily focused on the methods, measures, tools, classifications, linkage processes, data quality, survey design, statistical infrastructure, or dataset development needed to produce, improve, validate, or use research data.

**Assign when.** Assign when the data asset, linkage process, measurement approach, classification, survey method, statistical method, or research infrastructure is itself the substantive object of the project.

**Do not assign when.** Do not assign solely because a project uses linked data, administrative data, statistical methods, or a secure research environment to study another substantive domain. In those cases, assign the substantive domain and, where appropriate, Methodological / Infrastructure Research in Layer C.

**Counterexample.** Studies in a substantive domain that use linked data, administrative records, or advanced methods only as tools for the main research question.

*Why:* Methodological sophistication does not make this the domain unless data or methods are the research object.

### Unclear from Register Entry

**Definition.** Use only where the project title and dataset field together do not provide enough evidence to assign any substantive domain.

**Assign when.** Assign only where the title is an opaque acronym, internal project name, or otherwise non-descriptive, and the datasets are domain-agnostic or absent, so that neither field resolves the substantive domain.

**Do not assign when.** Do not assign if the dataset field reveals a clear domain. Do not assign alongside a real domain. If any domain can be inferred with reasonable confidence, use that domain.

**Counterexample.** Acronym-bearing or branded entries where the dataset field lists domain-specific datasets that identify the substantive area, such as court records, hospital admissions, or school census data.

*Why:* An opaque title is not enough for this fallback when the dataset field resolves the domain. The fallback applies only where neither the title nor the datasets identify a substantive area; domain-specific datasets resolve it, whereas domain-agnostic datasets (such as the Census or Labour Force Survey, used across many domains) may not.

## Analytical Purposes

### Descriptive Monitoring

**Definition.** Research whose analytical purpose is to measure and characterise a phenomenon — its level, prevalence, distribution, composition, profile, trend, or pattern — including how it varies across places, populations, or time, without primarily testing an exposure-outcome relationship or evaluating a named intervention.

**Assign when.** Assign where the project's visible analytical operation is to measure prevalence, levels, counts, profiles, distributions, characteristics, indicators, trends, or patterns, including variation across places, populations, organisations, or time, without primarily testing an exposure-outcome relationship or evaluating a named intervention.

**Do not assign when.** Do not assign where the project primarily tests whether X leads to Y, evaluates a named policy/programme/intervention, predicts or identifies future risk, analyses movement through services, or develops/validates methods or infrastructure. Use **Outcome Tracking** for exposure-outcome designs and **Policy Evaluation / Impact Analysis** for named policies, programmes, or interventions.

**Counterexample.** Studies designed to estimate whether a condition, exposure, or characteristic is associated with a downstream outcome.

*Why:* That design goes beyond description because it links X to Y.

*Instead consider:* Outcome Tracking

### Outcome Tracking

**Definition.** Research that links a naturally occurring exposure, condition, event, status, characteristic, or circumstance to a downstream outcome.

**Assign when.** Assign where the project links a naturally occurring exposure, condition, event, status, characteristic, or circumstance to a downstream outcome, and the exposure is not a deliberate named policy, programme, or intervention.

**Do not assign when.** Do not assign where the exposure is a named policy, programme, reform, or intervention; use **Policy Evaluation / Impact Analysis**. Do not assign if the project only measures patterns or trends; use **Descriptive Monitoring**. Do not assign where the aim is prospective prediction, risk scoring, screening, or early identification; use **Risk Prediction / Early Identification**. Do not assign where the main focus is extended life-stage progression or movement through service systems.

**Counterexample.** Studies estimating the effect of a named policy, programme, scheme, fund, levy, reform, or intervention.

*Why:* When the exposure is a deliberate named intervention, the analytical purpose is policy evaluation rather than generic outcome tracking. Some broad statutory parameters may require judgement where the project framing is ambiguous.

*Instead consider:* Policy Evaluation / Impact Analysis

### Life-Course / Trajectory Analysis

**Definition.** Research that follows individuals, cohorts, households, firms, or cases across extended time periods, transitions, or life stages to understand trajectories, progression, mobility, or cumulative outcomes.

**Assign when.** Assign where the project follows individuals, households, firms, or cases through sequences, stages, transitions, pathways, or trajectories over an extended period, such as childhood-to-adulthood, education-to-work, offending careers, family trajectories, employment histories, intergenerational mobility, social mobility, health trajectories, or long-run outcomes.

**Do not assign when.** Do not assign merely because longitudinal data are used. Do not assign where the study is mainly a single exposure-outcome test or a named policy evaluation over time. Where the pathway is movement through public-service or institutional systems (courts, family justice, support services, emergency departments, referrals, or case processing), **Service Interaction / Systems Analysis** is the primary reading; Life-Course / Trajectory Analysis may additionally apply where extended life-stage progression or long-run trajectory analysis is also central.

**Counterexample.** Studies using longitudinal data to estimate one exposure-outcome relationship without analysing extended progression or sequence.

*Why:* Longitudinal data are not sufficient; the purpose depends on whether trajectories or life-stage movement are central.

*Instead consider:* Outcome Tracking

### Service Interaction / Systems Analysis

**Definition.** Research focused on how people, cases, families, or organisations move through, use, access, or are processed by public service systems.

**Assign when.** Assign where service uptake, help-seeking, referrals, support pathways, repeated or high-intensity use, case progression, institutional processing, utilisation, welfare administration, benefit-service pathways, or cross-service movement are central to the analytical operation. Pathways through public-service or institutional systems (courts, family justice, welfare administration, support services, emergency departments, referrals, or case processing) are the primary reading for this category; **Life-Course / Trajectory Analysis** may additionally apply where extended life-stage progression is also central.

**Do not assign when.** Do not assign merely because an outcome occurs in a public service context. If the service is only the setting and the focus is an individual outcome, use **Outcome Tracking**. If the project evaluates a named service reform, programme, or intervention, use **Policy Evaluation / Impact Analysis**.

**Counterexample.** Studies where a public-service dataset — such as hospital, benefits, tax, or court administrative records — is merely the data source for estimating an individual outcome or descriptive pattern.

*Why:* Use of service records does not make the purpose service-system analysis unless pathways, access, uptake, referrals, processing, utilisation, or movement through systems are central.

*Instead consider:* Outcome Tracking, Descriptive Monitoring

### Policy Evaluation / Impact Analysis

**Definition.** Research that evaluates the effects, impacts, implementation, or consequences of a specific named policy, programme, regulation, intervention, scheme, or institutional change.

**Assign when.** Assign when the project evaluates, estimates the impact of, or compares outcomes before, after, or around a deliberate policy action, programme, intervention, reform, scheme, tax/relief, subsidy, public investment, business-support programme, school/apprenticeship policy, transport scheme, or similar designed change.

**Do not assign when.** Do not assign where the exposure is a naturally occurring event, condition, characteristic, or broad context rather than a deliberate policy, programme, reform, or intervention. Use **Outcome Tracking** for non-policy exposures and **Descriptive Monitoring** where the project only profiles or monitors a phenomenon.

**Counterexample.** Studies of naturally occurring conditions or characteristics, such as illness, debt, housing conditions, or family context.

*Why:* These may involve outcome analysis, but they are not policy evaluation unless a named intervention is the exposure.

*Instead consider:* Outcome Tracking

### Risk Prediction / Early Identification

**Definition.** Research with an explicit predictive or early-identification design focused on predicting risk, identifying at-risk individuals or groups, building risk scores, developing screening tools, or prospectively targeting people or places before or as an adverse outcome emerges.

**Assign when.** Assign only where the project explicitly involves prediction, risk scoring, screening, early identification, triage, a prediction model, or prospective targeting of at-risk individuals, groups, places, firms, or cases. The design must aim to identify who or where is at elevated risk before or as the outcome emerges.

**Do not assign when.** Do not assign merely because a project uses risk, risk factor, predictor, determinants, or similar vocabulary, or estimates associations between exposures and outcomes. Use **Outcome Tracking** where the project analyses predictors or risk factors without a prediction, screening, early-identification, triage, or prospective-targeting aim.

**Counterexample.** Studies estimating associations between an exposure, condition, risk factor, or predictor and an outcome without building or using a prediction, screening, triage, or early-identification design.

*Why:* Risk-factor analysis can be outcome tracking when the design does not aim to prospectively identify who or where is at elevated risk.

*Instead consider:* Outcome Tracking

### Methodological / Infrastructure Research

**Definition.** Research whose primary purpose is to develop, test, validate, improve, or document methods, data infrastructure, measurement frameworks, linkage approaches, survey methods, or data assets.

**Assign when.** Assign when developing, testing, validating, improving, documenting, or demonstrating methods, measures, data quality, classifications, datasets, linkage approaches, statistical estimates, indicators, or research infrastructure is the main analytical operation.

**Do not assign when.** Do not assign solely because a project uses complex data, administrative data, linked data, advanced statistical methods, machine learning, or a secure research environment. Assign this purpose only where the methodological or infrastructural contribution is central, not merely instrumental to a substantive question.

**Counterexample.** Substantive studies that use administrative data, linkage, modelling, machine learning, or advanced statistical methods only as tools to answer another research question.

*Why:* Methods are instrumental in many projects. This purpose requires method, measure, data-quality, linkage, dataset, classification, or infrastructure development to be central to the analytical operation.

### Unclear from Register Entry

**Definition.** Use where the project title and datasets do not provide enough information to infer the analytical purpose.

**Assign when.** Assign only where the analytical design cannot be inferred from the public register entry. It may be possible to classify the domain while leaving purpose unclear.

**Do not assign when.** Do not assign if the title or dataset field indicates monitoring, impact/evaluation, prediction, pathways, trajectories, exposure-outcome analysis, service-system analysis, or method/infrastructure development. Do not assign alongside a valid Layer C purpose.

**Counterexample.** Opaque or branded entries that still contain clear evaluation, impact, prediction, pathway, monitoring, or method-development wording.

*Why:* A branded name does not make purpose unclear when the title also reveals the analytical design.

*Instead consider:* Policy Evaluation / Impact Analysis

## Cross-cutting tags

### Demographic disparities / equity tag

*Status: new v3.4.*

**Definition.** A cross-cutting tag for projects whose research question centres on comparing outcomes, experiences, risks, access, or trajectories across demographic or equality-relevant groups.

**Assign when.** Assign where demographic or equality-relevant comparison is central to the research question, especially comparison by age, cohort, sex, gender, race, ethnicity, religion, disability, migrant/refugee status, nationality, or similar group characteristics. Use this tag for the demographic or equality-relevant comparative lens while assigning the substantive domain according to the outcome, system, policy area, or mechanism being studied. Socioeconomic comparison qualifies only where the comparison is made across a demographic or equality-relevant group; socioeconomic position alone is not sufficient. The tag can be combined with any Layer A domain and any Layer C purpose.

**Do not assign when.** Do not assign merely because demographic variables are used as controls, covariates, sample descriptors, or routine stratifiers. Do not assign to poverty, income, wealth, deprivation, regional inequality, or socioeconomic-position projects where the comparison is not centrally across a demographic or equality-relevant group. Do not use this tag as a substitute for the substantive domain or analytical purpose.

**Counterexample.** Studies of socioeconomic inequality, household debt, cost-of-living, deprivation, regional disadvantage, or area-level inequality without a central comparison across a demographic or equality-relevant group.

*Why:* Socioeconomic or place-based inequality alone is not sufficient for this tag. Use the tag only where comparison across groups such as age, sex, gender, race, ethnicity, disability, nationality, or migrant/refugee status is central.

*Instead consider:* Poverty, Wealth & Living Standards

**Example.** Gender pay gap studies comparing earnings, employment progression, or occupational outcomes by sex or gender.

### COVID-19 & Pandemic

**Definition.** A cross-cutting tag for projects where COVID-19, the COVID-19 pandemic, pandemic conditions, infection surveillance, vaccination, lockdowns, social distancing, pandemic-related public support, or pandemic consequences are a central condition or lens for the research question.

**Assign when.** Assign where COVID-19 or pandemic conditions are central to the research question. Use this tag for the pandemic condition or lens while assigning the substantive domain according to the outcome, system, policy area, or mechanism being studied. If the project studies COVID-19 effects on employment, business, health, education, inequality, or households, assign this tag alongside the relevant substantive domain or domains. The tag can be combined with any Layer A domain, any Layer C purpose, and other cross-cutting tags.

**Do not assign when.** Do not assign simply because the project occurred during the pandemic period. Do not assign to infectious disease, health, or mortality studies unless COVID-19 or pandemic framing is explicit. Do not use this tag as a substitute for the substantive domain or analytical purpose.

**Counterexample.** Studies where COVID-19 is only a date range, background period, excluded cause, or incidental context for otherwise non-pandemic research.

*Why:* This falls outside the tag when COVID-19 is not the exposure, surveillance object, intervention context, substantive outcome frame, or central pandemic condition being studied.

## Retired categories, not assignable

These appear in the dictionary's history and must not be assigned:

- Single-Dataset (Layer B -- linkage, removed rc2)
- Within-Domain Linkage (Layer B -- linkage, removed rc2)
- Cross-Domain Linkage (Layer B -- linkage, removed rc2)
- Unclear from Register Entry (Layer B -- linkage, removed rc2)
- Gender, Race & Ethnicity (Layer A -- domain, removed v3.4)
- Inequality / Disparities Analysis (Layer C -- purpose, removed v3.4)
