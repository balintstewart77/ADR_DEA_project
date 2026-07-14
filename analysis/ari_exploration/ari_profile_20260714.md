# UK Government Areas of Research Interest: exploratory profile

> **Scope warning:** This is a descriptive profile, not an ARI-to-project matching evaluation. The ARI API's embedded Gateway to Research associations are described throughout as **existing system-generated related-project links**. They are not evidence that a project answered an ARI or influenced policy.

## Live schema and retrieval checks

- API source: `https://ari.org.uk/api/questions`
- Documentation: `https://help.overton.io/article/the-ari-org-uk-dataset/`
- Retrieved: 2026-07-14T13:03:19+00:00 UTC (2026-07-14T14:03:19+01:00 Europe/London)
- Top-level response keys found: `data`, `meta`
- Unexpected top-level keys: none
- Pages retrieved: 20; metadata pages: 20; page sequence: 1–20
- Records downloaded: 4,956; metadata total: 4,956; match: **True**
- All metadata-listed pages retrieved exactly once: **True**

### Record fields

| Field | Records containing key | Key absent | Null/empty | Observed Python types |
| --- | --- | --- | --- | --- |
| backgroundInformation | 4956 | 0 | 133 | {"NoneType": 133, "str": 4823} |
| contactDetails | 4956 | 0 | 0 | {"str": 4956} |
| dateUpdated | 4956 | 0 | 0 | {"str": 4956} |
| department | 4956 | 0 | 0 | {"str": 4956} |
| expiryDate | 4956 | 0 | 4950 | {"NoneType": 4950, "str": 6} |
| fieldsOfResearch | 4956 | 0 | 0 | {"list": 4956} |
| isArchived | 4956 | 0 | 0 | {"bool": 4956} |
| pageViewCount | 4956 | 0 | 0 | {"int": 4956} |
| postDate | 4956 | 0 | 0 | {"str": 4956} |
| publicationDate | 4956 | 0 | 0 | {"str": 4956} |
| question | 4956 | 0 | 0 | {"str": 4956} |
| questionGroup | 4956 | 0 | 0 | {"str": 4956} |
| questionId | 4956 | 0 | 0 | {"int": 4956} |
| relatedQuestions | 4956 | 0 | 0 | {"list": 4956} |
| relatedUKRIProjects | 4956 | 0 | 0 | {"list": 4956} |
| tags | 4956 | 0 | 0 | {"list": 4956} |
| topics | 4956 | 0 | 0 | {"list": 4956} |
| url | 4956 | 0 | 0 | {"str": 4956} |

Fields absent from at least one record: none.
Unexpected relative to the documented record list: `dateUpdated`, `postDate`.
Documented fields not found anywhere: none.

### Nested link structures

**`relatedQuestions`:** 4,602 total list items; 4,602 objects and 0 scalar items.

| Subfield | Objects containing key | Key absent | Null/empty | Observed types |
| --- | --- | --- | --- | --- |
| questionId | 4602 | 0 | 0 | {"int": 4602} |

Example item (verbatim structure):

```json
{
  "questionId": 1159402
}
```

**`relatedUKRIProjects`:** 38,424 total list items; 38,424 objects and 0 scalar items.

| Subfield | Objects containing key | Key absent | Null/empty | Observed types |
| --- | --- | --- | --- | --- |
| endDate | 38424 | 0 | 0 | {"str": 38424} |
| leadResearchOrganisation | 38424 | 0 | 7 | {"NoneType": 7, "str": 38417} |
| projectId | 38424 | 0 | 0 | {"str": 38424} |
| startDate | 38424 | 0 | 0 | {"str": 38424} |
| title | 38424 | 0 | 0 | {"str": 38424} |
| url | 38424 | 0 | 0 | {"str": 38424} |

Example item (verbatim structure):

```json
{
  "projectId": "3F001C7D-599F-4566-A6F0-9CCCE64FDD7A",
  "title": "Universal Credit and Employers: exploring the demand side of UK active labour market policy",
  "url": "http://gtr.ukri.org/projects?ref=ES%2FV004093%2F1",
  "leadResearchOrganisation": "Manchester Metropolitan University",
  "startDate": "2021-04-30 01:00:00",
  "endDate": "2023-08-30 01:00:00"
}
```

The live schema differs from the documentation in three visible ways: `postDate` and `dateUpdated` are additional record fields; dates include time components rather than only `YYYY-MM-DD`; and `relatedQuestions` contains objects with a `questionId` subfield rather than bare ID values. The raw snapshot preserves these structures unchanged.

## A. Dataset overview

- Total ARIs: **4,956**
- Current: **3,434**; archived: **1,522**
- Publication dates: **2018-01-15** to **2026-06-19**; unparseable non-empty values: 0
- Departments/agencies with non-empty names: **38**
- Distinct non-empty question groups: **703**
- Duplicate `questionId` values: **0 groups / 0 records**
- Exact duplicates after case/whitespace/punctuation normalisation: **142 groups / 288 records (146 excess records)**
- Limited near-duplicate check after also removing a leading question number: **142 groups / 288 records (146 excess records)**

The near-duplicate count is deliberately conservative and transparent; no pairwise fuzzy or semantic comparison was run.

## B. Coverage

### Counts by department

| Department/agency | Total | Current | Archived |
| --- | --- | --- | --- |
| Department for Transport | 537 | 298 | 239 |
| Department for Science, Innovation & Technology | 511 | 511 | 0 |
| Department for Culture, Media & Sport | 333 | 17 | 316 |
| Ministry of Justice | 333 | 200 | 133 |
| Department for Education | 271 | 147 | 124 |
| Health and Safety Executive | 248 | 78 | 170 |
| Ministry of Housing, Communities and Local Government | 213 | 52 | 161 |
| Department for Business, Energy & Industrial Strategy | 206 | 0 | 206 |
| Foreign, Commonwealth & Development Office | 184 | 184 | 0 |
| Department for International Trade | 171 | 0 | 171 |
| Department for Environment, Food & Rural Affairs | 163 | 163 | 0 |
| Department for Work and Pensions | 118 | 118 | 0 |
| NCA | 113 | 113 | 0 |
| Ofsted | 111 | 111 | 0 |
| Scottish Government Justice Analytical Services | 109 | 109 | 0 |
| Scottish Government Marine Directorate | 107 | 107 | 0 |
| HMT | 102 | 102 | 0 |
| Department for Business and Trade | 101 | 101 | 0 |
| Scottish Government Social Care | 94 | 94 | 0 |
| Home Office | 86 | 86 | 0 |
| UK Policing: Office of Police Chief Scientific Adviser | 86 | 86 | 0 |
| Industrial Strategy Advisory Council | 81 | 81 | 0 |
| Welsh Government | 81 | 81 | 0 |
| Cabinet Office | 77 | 77 | 0 |
| MCA | 73 | 73 | 0 |
| Food Standards Agency | 66 | 66 | 0 |
| Scottish Government Environment, Natural Resources and Agriculture | 54 | 54 | 0 |
| Metropolitan Police | 53 | 53 | 0 |
| Sport England | 53 | 53 | 0 |
| Office for Product Safety & Standards | 36 | 36 | 0 |
| Food Standards Scotland | 35 | 35 | 0 |
| HMRC | 35 | 35 | 0 |
| Nuclear Decommissioning Authority | 30 | 30 | 0 |
| Ministry of Defence | 22 | 22 | 0 |
| Scottish Government Department for Tax and Revenues | 21 | 21 | 0 |
| The National Archives | 16 | 16 | 0 |
| Department of Health and Social Care | 15 | 13 | 2 |
| Office for Statistics Regulation | 11 | 11 | 0 |

### Counts by publication year and department

| Department/agency | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Department for Transport | 0 | 0 | 0 | 239 | 0 | 298 | 0 | 0 | 0 | 537 |
| Department for Science, Innovation & Technology | 0 | 0 | 0 | 0 | 0 | 0 | 511 | 0 | 0 | 511 |
| Department for Culture, Media & Sport | 87 | 0 | 0 | 0 | 0 | 229 | 0 | 0 | 17 | 333 |
| Ministry of Justice | 0 | 0 | 133 | 0 | 0 | 0 | 0 | 200 | 0 | 333 |
| Department for Education | 20 | 0 | 0 | 0 | 0 | 0 | 104 | 147 | 0 | 271 |
| Health and Safety Executive | 0 | 0 | 0 | 83 | 0 | 77 | 0 | 88 | 0 | 248 |
| Ministry of Housing, Communities and Local Government | 0 | 0 | 0 | 0 | 161 | 0 | 0 | 52 | 0 | 213 |
| Department for Business, Energy & Industrial Strategy | 0 | 0 | 206 | 0 | 0 | 0 | 0 | 0 | 0 | 206 |
| Foreign, Commonwealth & Development Office | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 184 | 184 |
| Department for International Trade | 0 | 0 | 171 | 0 | 0 | 0 | 0 | 0 | 0 | 171 |
| Department for Environment, Food & Rural Affairs | 0 | 0 | 0 | 163 | 0 | 0 | 0 | 0 | 0 | 163 |
| Department for Work and Pensions | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 118 | 118 |
| NCA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 113 | 0 | 113 |
| Ofsted | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 111 | 111 |
| Scottish Government Justice Analytical Services | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 109 | 0 | 109 |
| Scottish Government Marine Directorate | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 107 | 0 | 107 |
| HMT | 0 | 0 | 0 | 0 | 0 | 0 | 102 | 0 | 0 | 102 |
| Department for Business and Trade | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 101 | 101 |
| Scottish Government Social Care | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 94 | 94 |
| Home Office | 0 | 86 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 86 |
| UK Policing: Office of Police Chief Scientific Adviser | 0 | 0 | 0 | 0 | 0 | 0 | 86 | 0 | 0 | 86 |
| Industrial Strategy Advisory Council | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 81 | 81 |
| Welsh Government | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 73 | 81 |
| Cabinet Office | 0 | 77 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 77 |
| MCA | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 73 | 0 | 73 |
| Food Standards Agency | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 66 | 0 | 66 |
| Scottish Government Environment, Natural Resources and Agriculture | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 54 | 54 |
| Metropolitan Police | 0 | 53 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 53 |
| Sport England | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 53 | 0 | 53 |
| Office for Product Safety & Standards | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 36 | 36 |
| Food Standards Scotland | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 35 | 0 | 35 |
| HMRC | 0 | 0 | 0 | 0 | 0 | 0 | 35 | 0 | 0 | 35 |
| Nuclear Decommissioning Authority | 0 | 0 | 0 | 0 | 0 | 30 | 0 | 0 | 0 | 30 |
| Ministry of Defence | 22 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 22 |
| Scottish Government Department for Tax and Revenues | 0 | 0 | 0 | 0 | 0 | 0 | 21 | 0 | 0 | 21 |
| The National Archives | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 16 | 0 | 16 |
| Department of Health and Social Care | 0 | 0 | 0 | 0 | 0 | 15 | 0 | 0 | 0 | 15 |
| Office for Statistics Regulation | 0 | 0 | 0 | 0 | 0 | 11 | 0 | 0 | 0 | 11 |

### Top question groups

| Question group | ARIs |
| --- | --- |
| Improve transport for the user | 120 |
| Reduce environmental impacts | 88 |
| Grow and level up the economy | 73 |
| Industrial Strategy, Business Regulation and Growth | 43 |
| Schools: Continue to drive up academic standards so that children and young people in every part of the country are 11 prepared with the knowledge, skills and qualifications they need. | 37 |
| Science and Innovation | 33 |
| Enable people to get into work, improve skills, support young people and boost employment and productivity | 32 |
| Increasing the number of Welsh speakers | 30 |
| Enable industry to innovate safely to prevent major incidents, supporting the move to net zero | 29 |
| 4. Conflict, Humanitarian and Emergencies | 28 |
| Creating favourable conditions—infrastructure and context | 26 |
| Inclusion | 25 |
| 2. Growth and Investment | 24 |
| Energy Security, Systems and Strategy | 24 |
| Deliver high quality, efficient services, ensuring that people are treated with dignity and respect | 23 |
| Research about adult care homes and residents | 23 |
| Social and behavioural science | 23 |
| Delivering sustainable and regenerative agriculture and food systems | 22 |
| Growth | 22 |
| Skills: Drive economic growth through improving the skills pipeline, levelling up productivity and supporting people to work. | 22 |
| Foodborne Disease and Antimicrobial Resistance | 21 |
| Public Spending & Public Services | 20 |
| International | 20 |
| Road safety for users | 20 |
| 10. Politics and Governance | 19 |

### Sparse departments and missing coverage fields

“Very few” is defined here as five or fewer records.

| Department/agency | ARIs |
| --- | --- |
| None | 0 |

| Field | Missing/empty | Proportion |
| --- | --- | --- |
| department | 0 | 0.0% |
| publicationDate | 0 | 0.0% |
| expiryDate | 4950 | 99.9% |
| questionGroup | 0 | 0.0% |
| backgroundInformation | 133 | 2.7% |

## C. Text available for matching

Length statistics are calculated on non-empty values. Threshold proportions use all ARIs, with missing text treated as zero characters. Combined text is the non-empty concatenation `questionGroup + backgroundInformation + question`.

| Field | Missing | Min | Q1 | Median | Q3 | Max | <50 | <100 | <250 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| question | 0 (0.0%) | 6 | 108 | 147 | 201 | 1,925 | 85 (1.7%) | 975 (19.7%) | 4,305 (86.9%) |
| questionGroup | 0 (0.0%) | 3 | 27 | 41 | 65 | 247 | 2,971 (59.9%) | 4,523 (91.3%) | 4,956 (100.0%) |
| backgroundInformation | 133 (2.7%) | 34 | 367 | 615 | 1,027 | 4,042 | 136 (2.7%) | 164 (3.3%) | 631 (12.7%) |
| combinedText | 0 (0.0%) | 101 | 551 | 801 | 1,226.2 | 4,393 | 0 (0.0%) | 0 (0.0%) | 128 (2.6%) |

### Ten shortest combined usable texts

| ARI ID | Department | Characters | Question |
| --- | --- | --- | --- |
| 15374 | Department for Culture, Media & Sport | 101 | Further research into philanthropy and sustainable business models. |
| 15368 | Department for Culture, Media & Sport | 125 | Research into the impact of digital culture and levels of digital maturity and skills gaps. |
| 15372 | Department for Culture, Media & Sport | 128 | Research into the diversity of those working within the cultural sector and barriers to entry. |
| 1114160 | Department for Work and Pensions | 133 | How is climate change affecting vulnerable groups in the UK? What is DWP’s role in supporting these groups? |
| 1114158 | Department for Work and Pensions | 134 | How can DWP policies be used to reduce negative environmental impacts and support environmental enhancement? |
| 723991 | Ministry of Housing, Communities and Local Government | 145 | What are the long-term impacts/implications of community-based sponsorship? |
| 1114128 | Department for Work and Pensions | 149 | How can DWP support carers in their caring roles? |
| 1114166 | Department for Work and Pensions | 150 | What are the organisational conditions that support the successful use of design in services for disabled people and carers? |
| 17320 | Home Office | 150 | Developing non-animal technologies. |
| 1114156 | Department for Work and Pensions | 153 | How can we adapt research methodologies to robustly measure the impact of technology, such as AI, given its fast-moving nature? |

### Ten longest combined texts

| ARI ID | Department | Characters | Question |
| --- | --- | --- | --- |
| 345977 | Department for Science, Innovation & Technology | 4393 | In what ways is the UK regulatory environment helping / hindering the plans and activities of innovators? Is it becoming more friendly or less friend… |
| 345076 | Department of Health and Social Care | 4289 | ARI 1: early action to prevent poor health outcomes Research objective: Research to understand and deliver prevention, timely diagnosis and appropria… |
| 719266 | Health and Safety Executive | 3935 | What are the building safety implications of widespread adoption (including retrofitting) across the built environment of Modern Methods of Construct… |
| 719282 | Health and Safety Executive | 3874 | Are there significant implications for building users’ and construction workers’ health and safety arising from carbon reduction involving: retrofitt… |
| 719268 | Health and Safety Executive | 3843 | How can BSR ensure the needs of future building users are reflected in current standards and guidance to improve and maintain safety and standards lo… |
| 719274 | Health and Safety Executive | 3786 | What are the building safety implications of widespread adoption (including retrofitting) across the built environment from renewable energy and ener… |
| 719270 | Health and Safety Executive | 3786 | How can low frequency impact noise within buildings and its subjective effect on adverse health impacts on residents be measured and evaluated, and h… |
| 719293 | Health and Safety Executive | 3782 | What are the new methods of determining and managing risk being developed and what is their potential impact on regulatory assessments carried out fo… |
| 719280 | Health and Safety Executive | 3776 | Are there significant implications for construction worker health and safety arising from widespread adoption across this diverse sector of: Modern M… |
| 719257 | Health and Safety Executive | 3765 | How can BSR most effectively baseline and evaluate industry competence levels and also evaluate regulatory competence, including performance with oth… |

### Transparent qualitative spot checks

These are rule-generated candidates, intended for human inspection rather than labels. “Intelligible alone” requires a 100–400 character question containing `?` and no explicit context-reference phrase. “Context-dependent” uses explicit references such as “this” or a question under 80 characters paired with at least 250 background characters. A fragment has no `?` and at most 14 words or 90 characters. A broad candidate has at most 22 words and a generic term such as impact, role, future, opportunities, challenges, or effectiveness.
The 20 displayed candidates were manually spot-checked against their full group and background fields after generation. Borderline cases were retained to expose the limits of the rules: some short questions are intelligible alone but gain material scope from context.

**Questions likely intelligible alone**

| ARI ID | Department | Question |
| --- | --- | --- |
| 1000000 | Scottish Government Environment, Natural Resources and Agriculture | How can evidence be used to understand the nature, distribution and impacts of public, private and community investment in rural and island communities in Scotland? |
| 1000044 | MCA | What is the potential to utilise carbon intensity measures to reduce UK maritime emissions? Are these enforceable? Is there a more effective carbon intensity metric? |
| 1000432 | Department for Business and Trade | Which foreign countries lead in attracting and securing foreign direct investment (FDI) into professional and business services, what do companies gain from going there, and how can the UK replicate those conditions? |
| 1094806 | Scottish Government Social Care | What are the evidence-based approaches to improving and supporting recruitment and retention in the adult social care workforce? |
| 1095219 | Office for Product Safety & Standards | How do different regulators align priorities, share data, learn from each other when their regulatory remits overlap or operate in similar fields? |

**Questions likely to depend on group/background context**

| ARI ID | Department | Question |
| --- | --- | --- |
| 1000025 | Scottish Government Environment, Natural Resources and Agriculture | How can we further develop our understanding of key waste materials? |
| 1000272 | MCA | What are the optimal UK ship trade routes for wind-based vessels? |
| 1000443 | Department for Business and Trade | What are the distributional impacts of DBT’s growth policies, and vice versa? |
| 1094794 | Scottish Government Social Care | How is community-based social care defined and understood? |
| 1095262 | Office for Product Safety & Standards | How can OPSS understand the extent and range of consumer decisions? |

**Programme headings or fragments**

| ARI ID | Department | Question |
| --- | --- | --- |
| 1000039 | Scottish Government Environment, Natural Resources and Agriculture | Understanding patterns of land ownership/land data improvements |
| 139776 | Department for Culture, Media & Sport | Analyse the value of AHT sector work on public health. |
| 14666 | Department for Business, Energy & Industrial Strategy | Understanding the economic impact (direct and indirect) of major research infrastructures on their location. |
| 15540 | Department for Environment, Food & Rural Affairs | Risk management: Novel approaches to assessment and analysis of risk and resilience |
| 16396 | Department for International Trade | What are the sub-regional implications of future trade agreements and trade policy more broadly |

**Unusually broad candidates**

| ARI ID | Department | Question |
| --- | --- | --- |
| 1000009 | Scottish Government Environment, Natural Resources and Agriculture | What does the evidence tell us about future models for Public Service Delivery in Rural and Island Communities? |
| 1000141 | MCA | Are the current stability regulations appropriate for the future UK fleet? |
| 1000438 | Department for Business and Trade | What role can cost of capital play, for example in economic regulation sectors, and what is its relative importance? |
| 1094800 | Scottish Government Social Care | What is the future role of care homes as part of the provision of social care and support? |
| 1095255 | Office for Product Safety & Standards | What impact do we anticipate on product manufacturing from geopolitical disruption (for example around availability of materials or overseas manufacturing bases)? |

## D. Existing classifications

Frequencies below count the number of ARIs containing each value after case-insensitive within-record deduplication; raw assignment counts expose repeated values inside arrays.

### `topics`

Missing/empty: **791 (16.0%)**. Median assigned per ARI: **5 raw / 5 unique**. Non-list values: **0**. Records with within-list duplicates: **180**.

| Value | ARIs | Raw assignments |
| --- | --- | --- |
| economy, business and finance | 2226 | 2226 |
| science and technology | 1694 | 1823 |
| society | 1561 | 1561 |
| politics | 1363 | 1363 |
| environment | 783 | 783 |
| crime, law and justice | 779 | 779 |
| technology and engineering | 681 | 681 |
| government policy | 573 | 573 |
| education | 547 | 592 |
| health | 517 | 569 |
| labour | 491 | 491 |
| transport | 414 | 414 |
| economic policy | 399 | 399 |
| social condition | 335 | 335 |
| employment | 330 | 330 |
| economic sector | 322 | 322 |
| information technology and computer science | 301 | 301 |
| arts, culture, entertainment and media | 261 | 261 |
| international trade | 235 | 235 |
| research and development | 232 | 232 |
| demographics | 228 | 228 |
| welfare | 222 | 222 |
| social services | 214 | 214 |
| economy | 212 | 212 |
| economic development incentive | 201 | 201 |

Examples with broad/noisy assignment patterns:

| ARI ID | Duplicate assignments | Unique values | Question | Values |
| --- | --- | --- | --- | --- |
| 1127509 | 5 | 16 | 6.4b What are the most effective ways to close the digital divide and address technology-facilitated gender-b… | crime, law and justice; law; health sciences; public health; psychology; health; public health; politics; health; discrimination; science and technology; science and technology; social sciences; psychology; technology and engineering; information technology and computer science; society; discrimination; gender; women; social problem |
| 1168441 | 4 | 16 | 2.1i How can we better quantify the need and demand for youth service provision? | education; health sciences; public health; education; health; mental health and disorder; public health; labour; health; science and technology; science and technology; social sciences; society; communities; demographics; children; teenagers; social condition; social problem; welfare |
| 1127624 | 4 | 16 | 11.1d How can emerging technologies amplify or control misinformation, how are vulnerable people impacted, an… | health sciences; public health; information and computing sciences; artificial intelligence; health; public health; politics; health; science and technology; government policy; science and technology; social sciences; technology and engineering; information technology and computer science; artificial intelligence; society; disabilities; women; social condition; ethics |

Examples with compact, relatively specific values that may aid candidate retrieval:

| ARI ID | Question | Values |
| --- | --- | --- |
| 140062 | Are creative businesses obtaining the finance they need for investments in growth? | arts, culture, entertainment and media; economy, business and finance; financial and business service |
| 139898 | What are the possible technical solutions to link AHT-related datasets together, particularly given the lack… | arts, culture, entertainment and media; science and technology; information technology and computer science |
| 346469 | What are the economic incentives that drive cyber security? | economy, business and finance; science and technology; information technology and computer science |

### `fieldsOfResearch`

Missing/empty: **1,059 (21.4%)**. Median assigned per ARI: **5 raw / 5 unique**. Non-list values: **0**. Records with within-list duplicates: **196**.

| Value | ARIs | Raw assignments |
| --- | --- | --- |
| human society | 2027 | 2027 |
| economics | 1401 | 1524 |
| policy and administration | 1211 | 1211 |
| information and computing sciences | 1085 | 1085 |
| commerce, management, tourism and services | 907 | 907 |
| engineering | 855 | 855 |
| psychology | 689 | 759 |
| sociology | 635 | 655 |
| environmental sciences | 584 | 584 |
| education | 518 | 566 |
| data management and data science | 514 | 514 |
| applied economics | 471 | 471 |
| health sciences | 411 | 411 |
| law and legal studies | 393 | 393 |
| transportation, logistics and supply chains | 352 | 352 |
| built environment and design | 307 | 307 |
| criminology | 295 | 295 |
| social work | 292 | 292 |
| environmental management | 265 | 265 |
| education policy, sociology and philosophy | 246 | 246 |
| public health | 231 | 253 |
| artificial intelligence | 214 | 238 |
| science and technology | 195 | 195 |
| cybersecurity and privacy | 195 | 195 |
| climate change impacts and adaptation | 193 | 193 |

Examples with broad/noisy assignment patterns:

| ARI ID | Duplicate assignments | Unique values | Question | Values |
| --- | --- | --- | --- | --- |
| 1113933 | 4 | 14 | 1.5f. How do local services identify and meet the support, welfare and wellbeing needs of care leavers who ar… | education; health sciences; health services and systems; public health; human society; policy and administration; social work; sociology; other human society; law and legal studies; psychology; clinical and health psychology; education; health; public health; science and technology; psychology; sociology |
| 1127413 | 4 | 12 | 4.1c What drives violent and peaceful behaviour, and which resilience factors buffer communities from cycles… | education; health sciences; human society; criminology; development studies; political science; social work; sociology; other human society; law and legal studies; psychology; education; science and technology; political science; psychology; sociology |
| 1127393 | 4 | 12 | 3.2b What are the attitudes to migration in the UK as it relates to feasible responses? | economics; human society; demography; human geography; policy and administration; political science; sociology; other human society; language, communication and culture; law and legal studies; psychology; science and technology; economics; political science; psychology; sociology |

Examples with compact, relatively specific values that may aid candidate retrieval:

| ARI ID | Question | Values |
| --- | --- | --- |
| 16412 | How important are imports from developing countries for UK supply chains and what role can they play in diver… | commerce, management, tourism and services; transportation, logistics and supply chains; other commerce, management, tourism and services |
| 16222 | What are the key drivers / barriers to consumers’ adoption of technology that adds stability for the grid? Ho… | commerce, management, tourism and services; strategy, management and organisational behaviour; transportation, logistics and supply chains |
| 16218 | What are the most effective ways that businesses can encourage sustainable travel? For example, what role can… | commerce, management, tourism and services; strategy, management and organisational behaviour; transportation, logistics and supply chains |

### `tags`

Missing/empty: **642 (13.0%)**. Median assigned per ARI: **3 raw / 3 unique**. Non-list values: **0**. Records with within-list duplicates: **17**.

| Value | ARIs | Raw assignments |
| --- | --- | --- |
| transport | 386 | 386 |
| technology | 336 | 336 |
| environment | 301 | 301 |
| economy | 225 | 225 |
| education | 176 | 176 |
| innovation | 156 | 156 |
| trade | 125 | 125 |
| health | 118 | 118 |
| security | 107 | 107 |
| society | 103 | 103 |
| safety | 103 | 103 |
| economic crime | 92 | 92 |
| sustainability | 86 | 86 |
| Industrial Strategy | 81 | 81 |
| investment | 79 | 79 |
| regulation | 77 | 77 |
| Social Care | 73 | 73 |
| justice system | 73 | 73 |
| productivity | 71 | 71 |
| wellbeing | 69 | 69 |
| infrastructure | 68 | 68 |
| resilience | 67 | 67 |
| energy | 67 | 67 |
| data | 63 | 63 |
| business | 63 | 63 |

Examples with broad/noisy assignment patterns:

| ARI ID | Duplicate assignments | Unique values | Question | Values |
| --- | --- | --- | --- | --- |
| 1127566 | 1 | 5 | 9.2c Which policy responses and donor interventions best address the changing burden of disease linked to cli… | climate change; Climate Change; disease burden; global health; international development; policy responses |
| 1127545 | 1 | 5 | 8.1g How can policies and interventions, supported by capacity building and research, support the food system… | biodiversity; capacity building; climate change; Climate Change; food systems; policy |
| 1127533 | 1 | 5 | 8.1a Which interventions and technologies (such as climate resilient crops, livestock health treatments, vacc… | agriculture; climate change; Climate Change; environment; food security; technology |

Examples with compact, relatively specific values that may aid candidate retrieval:

| ARI ID | Question | Values |
| --- | --- | --- |
| 1000266 | How could the UK canal system be used effectively for the onward distribution of freight from UK ports? | Inland waterways for freight distribution; Integration of ports and canal networks; Modal shift from road to water; Capacity and constraints of the UK canal system |
| 1000231 | What is the potential impact of debris from upcoming space launches over/ near to the UK EEZ? | Space launch debris and maritime risk; Emerging hazards in the UK EEZ; Impact of space activity on maritime safety; Monitoring and detection of space debris; Emergency response to non‑traditional maritime incidents |
| 1000218 | How may the use of future fuels in shipping change the response to incidents? | Incident response for alternative fuels; Emergency response to novel fuel hazards; Safety and response implications of future fuels; Training and capability for fuel‑related incidents |

## E. Existing links

### Related questions

ARIs with at least one related question: **4,578 (92.4%)**. Median among linked records: **1**; maximum: **10**.

| Related-question count | ARIs |
| --- | --- |
| 0 | 378 |
| 1 | 4571 |
| 2 | 3 |
| 3 | 1 |
| 5 | 1 |
| 7 | 1 |
| 10 | 1 |

### Existing system-generated related-project links

ARIs with at least one embedded UKRI project: **4,635 (93.5%)**. Median among linked records: **10**; maximum: **10**.
There are **38,424** embedded project-link objects and **8,239** unique projects using `projectId`, then grant reference/URL fallbacks where needed.

| Related-UKRI-project count | ARIs |
| --- | --- |
| 0 | 321 |
| 1 | 240 |
| 2 | 178 |
| 3 | 193 |
| 4 | 149 |
| 5 | 138 |
| 6 | 145 |
| 7 | 157 |
| 8 | 117 |
| 9 | 122 |
| 10 | 3196 |

**Observed ceiling:** 3,196 ARIs have exactly the maximum of 10 embedded projects. This strongly suggests a top-results cap (an inference from the distribution, not an API guarantee), so the embedded counts should not be treated as exhaustive numbers of relevant projects.

#### Identifier and URL availability

| Feature | Embedded link objects | Proportion |
| --- | --- | --- |
| `projectId` present | 38424 | 100.0% |
| Grant reference extractable from URL `ref` | 38424 | 100.0% |
| Clickable HTTP(S) URL present | 38424 | 100.0% |

`projectId` is a project identifier in the live object, but the supplied documentation does not explicitly guarantee its stability. Grant references are not separate fields; they can be losslessly parsed from the `ref` query parameter when present.

**4,665 unique UKRI projects** appear against more than one ARI. Those shared projects account for **34,850** embedded link occurrences. Examples:

| Project ID | Grant ref | ARI count | Link occurrences | Project title | Example ARI IDs |
| --- | --- | --- | --- | --- | --- |
| 9C76FAEB-6885-4BAA-B007-FABE328673C9 | ES/J010235/1 | 115 | 115 | Plymouth Community Justice Court: A Case Study of Problem Solving Interventions, Reducing Re-offending and Public Confidence | 17290, 17538, 17550, 17554, 17682 |
| 648501B8-7CBB-46B0-A8FD-29E1905DA400 | ES/Z503289/1 | 107 | 107 | Understanding Offender Rehabilitation and Supervision | 17290, 17682, 17684, 17686, 17688 |
| 6A90239C-1050-41EB-9EF8-12C49FD3F1DD | ES/T000732/1 | 105 | 105 | UK in a Changing Europe Fellowship | 1000471, 1000475, 1000476, 1000477, 1000478 |
| 49AFBFCF-9109-4A57-8F5D-8CF504630F03 | ES/V011243/1 | 104 | 104 | Understanding Children's Lives and Outcomes | 1103375, 1103381, 1103386, 1103389, 1103392 |
| 135158BB-8D1A-4A7D-8A1B-8D187CA6FA66 | 10009205 | 100 | 100 | Make Time Count Today - Reducing criminal reoffending on probation through data analytics, predictive behaviour recognition and optimised interventions | 17290, 17682, 17684, 17686, 17688 |
| C2E4D3CC-FE67-4F41-808C-361334972D20 | ES/N018494/1 | 95 | 95 | Strategic Hub for Organised Crime Research | 17152, 17156, 17158, 17160, 17174 |
| 9301D1CF-9D2D-477C-BD35-B6A7AB0751C8 | ES/R000980/1 | 93 | 93 | The Economic Impacts of Post-Brexit Trade Options | 1000471, 1000475, 1000476, 1000477, 1000478 |
| BBCD2884-F0D1-4DAD-9515-BEFBEA3E2A9F | ES/X011348/1 | 92 | 92 | ADR UK Data First Evaluation Fellowship | 17290, 17684, 17688, 17690, 17698 |
| E51ECB9D-5BF5-4446-AAAF-18A8E6915A36 | 10054923 | 85 | 85 | Carers Assessment Support | 1094794, 1094800, 1094811, 1094838, 1094843 |
| 3EF7EA8B-2243-42DE-A3EE-3AACB8D7525E | ES/J02340X/1 | 85 | 85 | Regulating Justice: The Dynamics of Compliance and Breach in Criminal Justice Social Work in Scotland | 17682, 17684, 17686, 17688, 17690 |

#### Five ARIs with no related UKRI projects

| ARI ID | Department | Projects | Question |
| --- | --- | --- | --- |
| 1000141 | MCA | 0 | Are the current stability regulations appropriate for the future UK fleet? |
| 1000453 | Department for Business and Trade | 0 | What are the potential impacts of recent and proposed reforms to corporate law and governance frameworks on UK companies, including to the Companies… |
| 1095226 | Office for Product Safety & Standards | 0 | Which products are currently associated with consumer harm across the UK, and to what extent can this harm be quantified? Are there identifiable tren… |
| 1103006 | Industrial Strategy Advisory Council | 0 | Does the impact of government support on investment decisions differ between firms of different characteristics? |
| 1113981 | Department for Work and Pensions | 0 | How can we capture the wider impacts of being NEET on young people, society and future generations to estimate the long-term value of interventions t… |

#### Five ARIs with one or two related UKRI projects

| ARI ID | Department | Projects | Question |
| --- | --- | --- | --- |
| 1000059 | MCA | 1 | How should onboard captured carbon be categorised as a cargo? What risks are associated with improper storage? |
| 1000438 | Department for Business and Trade | 1 | What role can cost of capital play, for example in economic regulation sectors, and what is its relative importance? |
| 1094929 | Scottish Government Social Care | 1 | What evidence is there of using person centred approaches to support staff and improve recruitment and retention? |
| 1095219 | Office for Product Safety & Standards | 2 | How do different regulators align priorities, share data, learn from each other when their regulatory remits overlap or operate in similar fields? |
| 1103016 | Industrial Strategy Advisory Council | 1 | What are the most important factors determining international investment and multinational location decisions? |

#### Five ARIs with many related UKRI projects

| ARI ID | Department | Projects | Question |
| --- | --- | --- | --- |
| 1000000 | Scottish Government Environment, Natural Resources and Agriculture | 10 | How can evidence be used to understand the nature, distribution and impacts of public, private and community investment in rural and island communiti… |
| 1000044 | MCA | 10 | What is the potential to utilise carbon intensity measures to reduce UK maritime emissions? Are these enforceable? Is there a more effective carbon i… |
| 1000433 | Department for Business and Trade | 10 | What new artificial intelligence (AI) based business-to-business services and sectors are emerging globally, particularly in the US and Europe, that… |
| 1094794 | Scottish Government Social Care | 10 | How is community-based social care defined and understood? |
| 1095221 | Office for Product Safety & Standards | 10 | How do other countries’ National Quality Infrastructure operate with respect to systems integration across National Quality Infrastructure institutes? |

## F. Small meeting sample

`ari_sample_20260714.csv` contains **30** deliberately selected ARIs across **27** departments/agencies. Selection used deterministic quotas and writes all applicable reasons into `selectionReasons`.

| Selection property | Sample records |
| --- | --- |
| archived | 5 |
| background | 25 |
| current | 25 |
| dea overlap department | 7 |
| health related | 9 |
| long text | 7 |
| no background | 5 |
| short text | 9 |
| ukri few | 5 |
| ukri many | 15 |
| ukri zero | 7 |

Short/long are the bottom/top deciles of combined-text length (cutoffs 405 and 1,750 characters). “Many” means at least 10 embedded UKRI projects, the larger of five and the linked-record upper quartile.

## G. Questions raised

## Questions for Kathryn Oliver

1. Are the existing UKRI links intended to indicate topical relevance, researcher expertise, or both?
2. How were the system-generated UKRI links produced, thresholded, and evaluated, and against what notion of relevance?
3. Should archived ARIs remain searchable in an activity-mapping exercise, and how should supersession be represented?
4. Do departments actively review or use the linked-project feature, and are corrections or relevance judgements retained anywhere?
5. Which combination of question, group, and background should form the semantic representation of an ARI when context is uneven?
6. Should topics, fields of research, and tags be used as retrieval signals, filters, or only explanatory metadata given their duplication and breadth?
7. Which department has enough ARIs, sufficiently usable text, and a credible DEA overlap to serve as a bounded pilot?
8. How should health ARIs be handled when their research and data ecosystem may sit substantially outside the DEA accredited-project register?
9. What language and display safeguards are needed so an unmatched ARI is not misread as an evidence gap or lack of relevant research?
10. Would departments accept activity links as candidate associations requiring review, rather than as claims that research answered an ARI?
