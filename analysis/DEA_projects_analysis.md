# DEA accredited projects analysis 2019-2025

## Executive summary
This analysis examines the UK government's £100+ million investment in data infrastructure accessed through the Digital Economy Act 2017 (DEA), which has enabled unprecedented access to linked administrative datasets for public benefit research. Using web-scraped data from the public register of DEA-accredited projects (2019-2025), this analysis quantifies dataset usage patterns and analyses research themes to inform infrastructure planning and investment decisions. Findings reveal explosive growth in demand: over 1,000 projects have been approved under the DEA since 2019, with requests for access to ADR England flagship datasets experiencing 345% growth from 2021-2024 (doubling every 1.4 years). Growth in demand for these datasets has been driven primarily by the Longitudinal Education Outcomes (LEO) and Data First collections, with Education and Child Health Insights from Linked Data (ECHILD) emerging as most rapidly growing in demand since it became available in 2024. Text analysis of project titles identified four dominant research clusters (business/productivity, inequalities, health/social care, and labour markets/education), with health and education topics quadrupling in prevalence, while COVID-19 research demonstrated the system's agility - rising to 13.5% of projects during the pandemic before declining to 2.7%. Trends indicate that current growth trajectories could generate 240 flagship dataset requests by 2026 and over 1,000 by 2029, requiring proactive infrastructure scaling, strategic resource allocation to high-demand datasets, and streamlined approval processes to prevent bottlenecks that could constrain high-value research supporting evidence-based policymaking.

## Strategic context
The UK government has begun positioning high-quality data as critical national infrastructure, investing over £100 million in the ADR UK program alone since 2018. The Digital Economy Act 2017 (DEA) has created unprecedented opportunities for streamlined access to survey and large-scale, linked public administrative datasets for research in the public good. As this data becomes increasingly important for evidence-based policymaking, particularly to address complex and cross-cutting challenges like productivity gaps and social and health inequalities, understanding how this investment translates into impact is crucial. 

Public funders need evidence that national datasets deliver research impact that justifies their development and maintenance costs, and help identify where future resources should be concentrated to support their use. Simultaneously, tracking the evolution of research themes provides early intelligence on emerging policy challenges and scientific opportunities, ensuring infrastructure keeps pace with researcher demand. With research access requests under the DEA steadily increasing (and likely to accelerate in future, given growth in the availability of valuable large-scale linked administrative data that programmes like ADR UK are driving forward), understanding demand trajectories is critical for capacity planning, from project approval pipelines to the secure environments that support data access, so that infrastructure does not become a bottleneck to the very research it was designed to support.

## Aims of the project 
This analysis aims to help understand how publicly-funded data infrastructure is supporting public policy research, what the relative demand for different sensitive datasets is, and how research interests using this data have evolved over time.

### Part 1: Quantifying dataset usage in DEA-accredited research
- Measure how many research projects have been approved under the DEA since the public register of projects began (Q4 2019).
- Track which datasets have been requested most often to identify demand patterns across all available data resources.
- Assess the uptake and growth of ADR UK flagship datasets specifically. These are large-scale, linked administrative datasets representing significant public investment and research value. This analysis focuses on [ADR England flagship datasets](https://www.adruk.org/data-access/flagship-datasets/?tx_llcatalog_pi%5Bfilters%5D%5Bpartners%5D=766&cHash=352fa45e86742c514f344c3d0b418a73) (as flagship datasets from other ADR UK partners from the devolved administration are largely not present in the public register dataset), examining both overall usage trends and patterns within individual collections.

### Part 2: Understanding shifts in research focus over time
- Use text analysis of project titles to identify dominant themes in research.
- Track emerging and declining research topics using frequency and TF-IDF metrics to understand how research priorities evolve.
- Provide visual summaries to show how topic focus has changed over time, revealing trends in policy research interests.

## Approach:

### Part 1: Dataset access trends
(All code available on [github](https://github.com/balintstewart77/ADR_DEA_project)), main project notebook [here](https://github.com/balintstewart77/ADR_DEA_project/blob/main/analysis/DEA_projects_analysis.ipynb)
- Scraped and cleaned public data on all research projects approved under the DEA from 2019 (when records in the public register began) onward from the public register provided on the [UK Statistics Authority website](https://uksa.statisticsauthority.gov.uk/digitaleconomyact-research-statistics/better-useofdata-for-research-information-for-researchers/list-of-accredited-researchers-and-research-projects-under-the-research-strand-of-the-digital-economy-act/)
- Filtered to exclude projects under a different legal gateway (SRSA 2007 - a gateway limited to research for purely statistical purposes) to ensure a focus on Digital Economy Act approved-research. 
- Categorised datasets and grouped some into collections (e.g., “Data First” and “Wage and Employment Dynamics”) for clarity.
- Visualised the growth in use of ADR UK flagship datasets as a whole and split by collection, quarter by quarter.
- Calculated compounded growth rates for these.
- Created summary tables and visualisations showing trends and growth over time, which can be easily copied into reports.

### Part 2: Topic trends in research 
- Analysed the titles of research projects to understand what topics are being studied.
- Applied natural language processing to clean and process this text data.
- Used TF-IDF scoring to identify the most distinctive keywords per year or quarter.
- Tracked which terms are growing or declining in usage across time.
- Presented topic trends visually via word clouds and line charts.

## Summary of findings
### Part 1: Dataset access trends
**Overall Dataset Popularity**
- Over 1000 projects have been approved under the DEA between 2019 and 14 May 2025 (Figure 1)
- The Business Structure Database (220 requests), Annual Business Survey (191 requests) and the Annual Survey of Hours and Earnings (158) are the three most frequently requested datasets across all of these projects (Figure 2)

**ADR England Flagship Datasets**
- The number of requests for ADR England flagship datasets **more than quadrupled** from 20 approved requests in 2021 to 89 requests in 2024 (growth rate of 345%) (Figure 3). Growth in access requests has been itself accelerating, with year-on-year growth rate increases of +40% (2021 -> 2022), +57% (2022 -> 2023), and 102% (2023 -> 2024) (Figure 4)
- This equates to a **doubling in the use of flagship datasets around every 1.4 years** on average over the observed annual time period.

The demand for these datasets can be split into roughly 3 phases:
- **2021-2022: Foundation phase**. Started with 20 requests in 2021, saw 40% growth in access requests in year two
- **2023: Breakthrough year**. Saw 57% growth, reaching 44 projects in that year and more consistency in access requests (volatility fell from 84% (2021 coefficient of variation = 0.84) to 26% (2023 coefficient of variation = 0.26))
- **2024: Acceleration phase**. Doubling of requests for flagship datasets to 89, with the steady quarterly growth (11 → 21 → 26 → 31 access requests) maintained into Q1 of 2025 (37 access requests)

The Longitudinal Education Outcomes (37% of all ADR England flagship dataset access requests) and Data First collections (22% of all ADR England flagship dattaset access requests, although this count doesn't include the popular MoJ-DfE linkage dataset which is not accessed through the DEA) are the most accessed flagship datasets overall. ECHILD shows the most rapid growth in use among flagship dataset collections, with a total of 23 access requests in just the three quarters its been available.


### Part 2: Topic trends in research 
**Research Theme Clusters**
Analysis of project title distinctiveness by year reveals that DEA-accredited research over the past six years broadly speaking falls into four distinct thematic clusters:

- Cluster 1: Business, growth, and productivity
- Cluster 2: Gender and ethnic inequalities and gaps
- Cluster 3: Health, social care, and children
- Cluster 4: Labour market, skills, and education

**Evolving Research Priorities**
Tracking term frequency over time reveals three distinct patterns in research focus:
- Stable research areas maintain consistent presence, with terms like 'labour', 'market', 'employment', and 'productivity' appearing at steady rates across all years, indicating sustained policy interest in economic research.
- Growing research areas show dramatic expansion, particularly health and education topics. The term 'health' has more than tripled from appearing in 3.8% of project titles in 2021 to 12% in 2025, while 'education' has quadrupled from 3.4% in 2020 to 14% in 2025. 
- Research areas showing both growth and decline demonstrate the system's responsiveness to changing priorities. COVID-19 research peaked at 13.5% of all project titles during the pandemic but has since declined sharply to just 2.7% in 2024, showing how the research ecosystem adapts as policy priorities evolve.

# Strategic Implications 

**Infrastructure Investment Requirements**:
The 345% growth in flagship dataset usage over the observed time period demonstrates exceptional return on public investment, but may also signal upcoming capacity pressures. Although projects using ADR England flasghip datasets have historically represented a small fraction of overall projects approved through the DEA, if current trends continue, ADR UK and the ONS Secure Research Service can expect approximately 240 access requests for ADR England flagship datasets in 2026, and in the absence of the emergence of other limitations (e.g. research funding, trained researcher capacity etc.) potentially rising to over 1000 by 2029 — representing a 50-fold increase from 2021 baseline levels. This explosive growth is likely to considerably increase future demand on the ONS SRS, requiring proactive infrastructure scaling to prevent approval bottlenecks that could constrain high-value research. 

**Resource Allocation Priorities**
LEO and Data First collections account for 59% of all flagship access requests, suggesting opportunities for further investment and enhancement of these datasets with new linkages, training, metadata enhancement etc. Conversely, datasets with much fewer requests may warrant review for useability and utility or targeted promotion to increase use. The shift toward health and education research themes, indicates growing demand for linked administrative data in these sectors.

**Policy Research Readiness**
The rapid emergence and decline of COVID-19 research (from 13.5% to 2.7% of project titles in just 2 years) demonstrates the system's ability to respond to urgent policy needs. However, maintaining this agility at a much greater scale will require streamlined approval processes and enhanced secure environment capacity.


```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.api as sm

```


```python
df = pd.read_csv('C:/Users/balin/Desktop/ADR_DEA_project/data/dea_accredited_projects.csv')
```


```python
df.head()
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>Project ID</th>
      <th>Title</th>
      <th>Researchers</th>
      <th>Legal Basis</th>
      <th>Datasets Used</th>
      <th>Secure Research Service</th>
      <th>Accreditation Date</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>2019/003</td>
      <td>The fall of the labour share and rise of the s...</td>
      <td>Carolin Ioramashvili, London School of Economics</td>
      <td>Digital Economy Act (2017)</td>
      <td>Office for National Statistics: Annual Respond...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>10/25/2019</td>
    </tr>
    <tr>
      <th>1</th>
      <td>2019/004</td>
      <td>The changing nature of the HR and training pra...</td>
      <td>Jonathan Boys, Chartered Institute of Personne...</td>
      <td>Digital Economy Act (2017)</td>
      <td>Office for National Statistics: Annual Populat...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>10/25/2019</td>
    </tr>
    <tr>
      <th>2</th>
      <td>2019/006</td>
      <td>Analysis of victimisation data from the Crime ...</td>
      <td>Julian Molina, Office of the Victims' Commissi...</td>
      <td>Digital Economy Act (2017)</td>
      <td>Office for National Statistics: Crime Survey f...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>10/14/2019</td>
    </tr>
    <tr>
      <th>3</th>
      <td>2019/007</td>
      <td>Thriving Places index – indicators of wellbein...</td>
      <td>Soraya Safazadeh, Happy City Initiative\nSaama...</td>
      <td>Digital Economy Act (2017)</td>
      <td>Office for National Statistics: Labour Force S...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>10/14/2019</td>
    </tr>
    <tr>
      <th>4</th>
      <td>2019/008</td>
      <td>Class in UK creative industries: Beyond partic...</td>
      <td>Rebecca Florisson, The Work Foundation</td>
      <td>Digital Economy Act (2017)</td>
      <td>Office for National Statistics: Labour Force S...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>11/19/2019</td>
    </tr>
  </tbody>
</table>
</div>




```python
df.isna().sum()
```




    Project ID                 0
    Title                      0
    Researchers                2
    Legal Basis                0
    Datasets Used              1
    Secure Research Service    0
    Accreditation Date         0
    dtype: int64




```python
missing_researchers = df[df['Researchers'].isna()]
```


```python
missing_datasets = df[df['Datasets Used'].isna()]
```


```python
# Drop rows with missing datasets used
df = df.dropna(subset=['Datasets Used'])
```


```python
df.head()
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>Project ID</th>
      <th>Title</th>
      <th>Researchers</th>
      <th>Legal Basis</th>
      <th>Datasets Used</th>
      <th>Secure Research Service</th>
      <th>Accreditation Date</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>2019/003</td>
      <td>The fall of the labour share and rise of the s...</td>
      <td>Carolin Ioramashvili, London School of Economics</td>
      <td>Digital Economy Act (2017)</td>
      <td>Office for National Statistics: Annual Respond...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>10/25/2019</td>
    </tr>
    <tr>
      <th>1</th>
      <td>2019/004</td>
      <td>The changing nature of the HR and training pra...</td>
      <td>Jonathan Boys, Chartered Institute of Personne...</td>
      <td>Digital Economy Act (2017)</td>
      <td>Office for National Statistics: Annual Populat...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>10/25/2019</td>
    </tr>
    <tr>
      <th>2</th>
      <td>2019/006</td>
      <td>Analysis of victimisation data from the Crime ...</td>
      <td>Julian Molina, Office of the Victims' Commissi...</td>
      <td>Digital Economy Act (2017)</td>
      <td>Office for National Statistics: Crime Survey f...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>10/14/2019</td>
    </tr>
    <tr>
      <th>3</th>
      <td>2019/007</td>
      <td>Thriving Places index – indicators of wellbein...</td>
      <td>Soraya Safazadeh, Happy City Initiative\nSaama...</td>
      <td>Digital Economy Act (2017)</td>
      <td>Office for National Statistics: Labour Force S...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>10/14/2019</td>
    </tr>
    <tr>
      <th>4</th>
      <td>2019/008</td>
      <td>Class in UK creative industries: Beyond partic...</td>
      <td>Rebecca Florisson, The Work Foundation</td>
      <td>Digital Economy Act (2017)</td>
      <td>Office for National Statistics: Labour Force S...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>11/19/2019</td>
    </tr>
  </tbody>
</table>
</div>




```python
df['Legal Basis'].value_counts()
```




    Legal Basis
    Digital Economy Act (2017)                                                                                                                                                                                                                                                       1023
    Statistics and Registration Services Act 2007 (SRSA) - Approved Researcher Gateway: added data after 9 September 2021                                                                                                                                                              98
    Digital Economy Act 2017                                                                                                                                                                                                                                                           18
    Statistics and Registration Services Act 2007 (SRSA) - Approved Researcher Gateway: added data after 9 September 2021s Act 2007 (SRSA) - Approved Researcher Gateway: added data after 9 September 2021                                                                             5
    Digital Economy Act (2017)\n\nStatistics and Registration Services Act 2007 (SRSA) - Approved Researcher Gateway: added data after 9 September 2021s Act 2007 - Approved Researcher Gateway: added data after 9 September 2021                                                      3
    Statistics and Registration Services Act 2007 (SRSA) - Approved Researcher Gateway: added data after 9 September 2021s Act 2007 (SRSA) - Approved Researcher Gateway: added data after 9 September 2021s Act 2007 - Approved Researcher Gateway                                     1
    Digital Economy Act (2017)\n\nStatistics and Registration Services Act 2007 (SRSA) - Approved Researcher Gateway: added data after 9 September 2021s Act 2007 (SRSA) - Approved Researcher Gateway: added data after 9 September 2021s Act 2007 - Approved Researcher Gateway       1
    Digital Economy Act (2017) & Statistics and Registration Services Act 2007 (SRSA) - Approved Researcher Gateway: added data after 9 September 2021s Act 2007 (SRSA) - Approved Researcher Gateway: added data after 9 September 2021s Act 2007 - Approved Researcher Gateway        1
    Statistics and Registration Services Act 2007 (SRSA) - Approved Researcher Gateway: added data after 9 September 2021s Act 2007 (SRSA) - Approved Researcher Gateway: added data after 9 September 2021s Act 2007 - Approved Researcher Gatway                                      1
    Statistics and Registration Services Act 2007 (SRSA) - Approved Researcher Gateway: added data after 9 September 2021s Act 2007 (SRSA) - Approved Researcher Gateway: added data after 9 September 2021 Act                                                                         1
    Name: count, dtype: int64




```python
# Clean Legal Basis column by removing SRSA rows
df = df[~df['Legal Basis'].str.contains('SRSA', na=False)]
# tidy up DEA labels
df['Legal Basis'] = df['Legal Basis'].str.replace('Digital Economy Act (2017)', 'Digital Economy Act 2017')
df['Legal Basis'].value_counts()
```




    Legal Basis
    Digital Economy Act 2017    1041
    Name: count, dtype: int64






```python
df.isna().sum()
```




    Project ID                 0
    Title                      0
    Researchers                2
    Legal Basis                0
    Datasets Used              0
    Secure Research Service    0
    Accreditation Date         0
    dtype: int64




```python
problematic_dates = df[pd.isna(pd.to_datetime(df['Accreditation Date'], errors='coerce'))]
print(problematic_dates['Accreditation Date'].unique())
```

    ['2020-06-11' '2020-12-07' '2021-11-02' '2021-09-14' '2021-09-24'
     '2021-09-17' '2021-10-05' '2021-10-13' '2021-10-26' '2021-10-12'
     '2021-12-10' '2021-03-15' '2023-01-18' '2023-03-06' '2023-03-09'
     '2023-01-03' '2023-04-05' '2023-01-30' '2023-01-17' '2023-04-19'
     '2023-01-20' '2023-02-03' '2023-01-19' '2023-03-02' '2023-03-05'
     '2023-03-21' '2023-04-11' '2023-03-31' '2023-01-11' '2023-03-07'
     '2023-04-04' '2023-02-10' '2023-01-04' '2023-03-20' '2023-01-23'
     '2023-03-03' '2023-02-16' '2023-02-07' '2023-03-23' '2023-02-13'
     '2023-02-24' '2023-04-18' '2023-02-15' '2023-01-22' '2023-03-27'
     '2023-02-22' '2023-01-06' '2023-04-13' '2023-01-13' '2023-01-16'
     '2023-02-02' '2023-03-08' '2023-04-06' '2023-03-24' '2023-03-30'
     '2023-05-02' '2023-05-09' '2023-05-24' '2023-06-02' '2023-06-07'
     '2023-06-13' '2023-06-19' '2023-06-20' '2023-06-22' '2023-05-12'
     '2023-06-05' '13/07/2023' '28/07/2023' '31/07/2023' '17/08/2023'
     '18/08/2023' '30/08/2023' '18/09/2023' '19/09/2023' '20/09/2023'
     '27/09/2023' '16/11/2023' '31/10/2023' '17/11/2023' '17/10/2023'
     '25/10/2023' '29/09/2023' '26/10/2023' '21/12/2023' '23/11/2023'
     '15/12/2023' '18/12/2023' '19/12/2023' '16/01/2024' '20/12/2023'
     '22/12/2023' '23/01/2024' '22/02/2024' '26/01/2024' '30/01/2024'
     '20/02/2024' '23/02/2024' '25/03/2024' '25/04/2024' '15/04/2024'
     '29/01/2024' '13/10/2023' '29/04/2024' '30/05/2024' '13/05/2024'
     '17/05/2024' '13/06/2024' '31/05/2024' '22/05/2024' '18/07/2024'
     '15/07/2024' '22/07/2024' '30/07/2024' '18/06/2024' '26/07/2023'
     '27/07/2023' '29/08/2023' '30/10/2023' '14/11/2023' '21/08/2023'
     '22/01/2024' '27/03/2024' '29/05/2024' '29/07/2024' '31/07/2024'
     '16/08/2024' '14/08/2024' '28/08/2024' '27/08/2024' '23/10/2024'
     '16/10/2024' '15/10/2024' '18/10/2024' '22/10/2024' '30/09/2024'
     '31/10/2024' '19/09/2024' '18/09/2024' '17/10/2024' '13/09/2024'
     '24/10/2024' '30/10/2024' '13/08/2024' '22/08/2024' '26/09/2024'
     '28/10/2024' '22/11/2024' '31/01/2025' '27/11/2024' '28/01/2025'
     '25/11/2024' '15/11/2024' '20/11/2024' '14/01/2025' '21/01/2025'
     '18/12/2024' '13/11/2024' '20/01/2025' '16/12/2024' '15/01/2025'
     '27/01/2025' '13/01/2025' '14/11/2024' '22/01/2025' '19/11/2024'
     '16/01/2025' '17/02/2025' '18/02/2025' '24/02/2025' '26/02/2025'
     '21/02/2025' '27/02/2025' '28/02/2025' '15/04/2025' '17/03/2025'
     '28/03/2025' '16/04/2025' '18/03/2025' '31/03/2025' '14/02/2025'
     '20/02/2025' '13/03/2025' '22/04/2025' '24/04/2025' '23/04/2025'
     '25/04/2025' '30/04/2025' '14/03/2025' '21/03/2025' '14/04/2025'
     '13/05/2025' '19/02/2025' '24/03/2025' '27/03/2025' '14/05/2025']
    


```python
def parse_mixed_dates(date_str):
    """Parse dates that could be in YYYY-MM-DD or DD/MM/YYYY format"""
    if pd.isna(date_str):
        return pd.NaT
    
    date_str = str(date_str).strip()
    
    # Try ISO format first (YYYY-MM-DD)
    if '-' in date_str:
        try:
            return pd.to_datetime(date_str, format='%Y-%m-%d')
        except:
            pass
    
    # Try DD/MM/YYYY format
    if '/' in date_str:
        try:
            return pd.to_datetime(date_str, format='%d/%m/%Y')
        except:
            pass
    
    # Fallback to pandas inference
    try:
        return pd.to_datetime(date_str)
    except:
        return pd.NaT

# Apply the custom parser
df['Accreditation Date'] = df['Accreditation Date'].apply(parse_mixed_dates)

# Create quarter and year columns
df['Accreditation Date Quarter'] = df['Accreditation Date'].dt.to_period('Q')
df['Accreditation Date Year'] = df['Accreditation Date'].dt.year
df['quarter_date'] = df['Accreditation Date Quarter'].dt.to_timestamp(how='start')
df['Quarter Label'] = df['Accreditation Date Quarter'].apply(
    lambda p: f"Q{p.quarter} {p.year}" if pd.notna(p) else None
)

# Check for any remaining problematic dates
remaining_nans = df[df['Accreditation Date'].isna()]
print(f"Remaining NaN dates: {len(remaining_nans)}")
if len(remaining_nans) > 0:
    print("Original values that couldn't be parsed:")
    print(remaining_nans['Accreditation Date'].unique())
```

    Remaining NaN dates: 0
    


```python
df.isna().sum()
```




    Project ID                    0
    Title                         0
    Researchers                   2
    Legal Basis                   0
    Datasets Used                 0
    Secure Research Service       0
    Accreditation Date            0
    Accreditation Date Quarter    0
    Accreditation Date Year       0
    quarter_date                  0
    Quarter Label                 0
    dtype: int64




```python
# Dataset has single entry in 2019Q1, likely a typo (rest of data starts from 2019Q4), fix manually
df.loc[16, 'Accreditation Date Quarter'] = '2019Q4'
```


```python
import re

def extract_datasets(row):
    """
    Extract dataset names from the 'Datasets Used' column.
    Handles multiple data sources and newlines, but doesn't filter values.
    """
    if pd.isna(row) or row == "":
        return []
    
    # Replace newlines and normalize other separators
    processed = row.replace("\n", ";").replace("\\n", ";")
    
    results = []
    
    # Split by semicolons to handle multiple data sources
    for entry in processed.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        
        # Handle the case with or without a data source (colon)
        if ":" in entry:
            # Split only on the first colon
            parts = entry.split(":", 1)
            datasets = parts[1].strip()
            
            # Skip if there's nothing after the colon
            if not datasets:
                continue
        else:
            datasets = entry
        
        # Split by commas and process each dataset
        for ds in datasets.split(","):
            ds = ds.strip()
            
            # Only skip empty strings
            if not ds:
                continue
            
            results.append(ds)
    
    return results
```


```python
# lowercase the datasets used column
df["datasets_clean"] = df["Datasets Used"].str.lower()

# apply the function to create a list of dataset names
df["dataset_list"] = df["datasets_clean"].apply(lambda x: extract_datasets(x) if pd.notnull(x) else [])

# explode the dataset list to one dataset per row
df_exploded = df.explode("dataset_list")
```


```python
df_exploded[df_exploded['Datasets Used'].str.contains("Wales")]
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>Project ID</th>
      <th>Title</th>
      <th>Researchers</th>
      <th>Legal Basis</th>
      <th>Datasets Used</th>
      <th>Secure Research Service</th>
      <th>Accreditation Date</th>
      <th>Accreditation Date Quarter</th>
      <th>Accreditation Date Year</th>
      <th>quarter_date</th>
      <th>Quarter Label</th>
      <th>datasets_clean</th>
      <th>dataset_list</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>2</th>
      <td>2019/006</td>
      <td>Analysis of victimisation data from the Crime ...</td>
      <td>Julian Molina, Office of the Victims' Commissi...</td>
      <td>Digital Economy Act 2017</td>
      <td>Office for National Statistics: Crime Survey f...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2019-10-14</td>
      <td>2019Q4</td>
      <td>2019</td>
      <td>2019-10-01</td>
      <td>Q4 2019</td>
      <td>office for national statistics: crime survey f...</td>
      <td>crime survey for england and wales</td>
    </tr>
    <tr>
      <th>24</th>
      <td>2020/003</td>
      <td>Spatial sorting in housing and employment: imp...</td>
      <td>Lars Nesheim, University College London</td>
      <td>Digital Economy Act 2017</td>
      <td>Office for National Statistics: Annual Survey ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2020-01-17</td>
      <td>2020Q1</td>
      <td>2020</td>
      <td>2020-01-01</td>
      <td>Q1 2020</td>
      <td>office for national statistics: annual survey ...</td>
      <td>annual survey of hours and earnings</td>
    </tr>
    <tr>
      <th>24</th>
      <td>2020/003</td>
      <td>Spatial sorting in housing and employment: imp...</td>
      <td>Lars Nesheim, University College London</td>
      <td>Digital Economy Act 2017</td>
      <td>Office for National Statistics: Annual Survey ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2020-01-17</td>
      <td>2020Q1</td>
      <td>2020</td>
      <td>2020-01-01</td>
      <td>Q1 2020</td>
      <td>office for national statistics: annual survey ...</td>
      <td>census 2011 england and wales: individual sample</td>
    </tr>
    <tr>
      <th>24</th>
      <td>2020/003</td>
      <td>Spatial sorting in housing and employment: imp...</td>
      <td>Lars Nesheim, University College London</td>
      <td>Digital Economy Act 2017</td>
      <td>Office for National Statistics: Annual Survey ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2020-01-17</td>
      <td>2020Q1</td>
      <td>2020</td>
      <td>2020-01-01</td>
      <td>Q1 2020</td>
      <td>office for national statistics: annual survey ...</td>
      <td>census 2011 origin/destination: flow data &amp; bu...</td>
    </tr>
    <tr>
      <th>33</th>
      <td>2020/013</td>
      <td>Firm-level analysis of research and development</td>
      <td>Joelle Tasker, Office for National Statistics\...</td>
      <td>Digital Economy Act 2017</td>
      <td>Office for National Statistics: Business Expen...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2020-03-16</td>
      <td>2020Q1</td>
      <td>2020</td>
      <td>2020-01-01</td>
      <td>Q1 2020</td>
      <td>office for national statistics: business expen...</td>
      <td>business expenditure on research and developme...</td>
    </tr>
    <tr>
      <th>...</th>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
    </tr>
    <tr>
      <th>1128</th>
      <td>2025/104</td>
      <td>Dissociative seizures in Wales - epidemiology,...</td>
      <td>Owen Pickrell, Swansea University\nArron Lacey...</td>
      <td>Digital Economy Act 2017</td>
      <td>SAIL Databank: Census Wales 2021</td>
      <td>SAIL</td>
      <td>2025-04-14</td>
      <td>2025Q2</td>
      <td>2025</td>
      <td>2025-04-01</td>
      <td>Q2 2025</td>
      <td>sail databank: census wales 2021</td>
      <td>census wales 2021</td>
    </tr>
    <tr>
      <th>1129</th>
      <td>2025/109</td>
      <td>Researching intimate partner violence and abus...</td>
      <td>Valeria Skafida, University of Edinburgh\nChri...</td>
      <td>Digital Economy Act 2017</td>
      <td>Office for National Statistics: Crime Survey f...</td>
      <td>UK Data Service</td>
      <td>2025-05-08</td>
      <td>2025Q2</td>
      <td>2025</td>
      <td>2025-04-01</td>
      <td>Q2 2025</td>
      <td>office for national statistics: crime survey f...</td>
      <td>crime survey for england and wales</td>
    </tr>
    <tr>
      <th>1138</th>
      <td>2025/027</td>
      <td>Migration Observatory analysis of internationa...</td>
      <td>Ben Brindle, University of Oxford\nMadeleine \...</td>
      <td>Digital Economy Act 2017</td>
      <td>Office for National Statistics: Census 2021 \n...</td>
      <td>IDS</td>
      <td>2025-02-04</td>
      <td>2025Q1</td>
      <td>2025</td>
      <td>2025-01-01</td>
      <td>Q1 2025</td>
      <td>office for national statistics: census 2021 \n...</td>
      <td>census 2021</td>
    </tr>
    <tr>
      <th>1138</th>
      <td>2025/027</td>
      <td>Migration Observatory analysis of internationa...</td>
      <td>Ben Brindle, University of Oxford\nMadeleine \...</td>
      <td>Digital Economy Act 2017</td>
      <td>Office for National Statistics: Census 2021 \n...</td>
      <td>IDS</td>
      <td>2025-02-04</td>
      <td>2025Q1</td>
      <td>2025</td>
      <td>2025-01-01</td>
      <td>Q1 2025</td>
      <td>office for national statistics: census 2021 \n...</td>
      <td>england and wales</td>
    </tr>
    <tr>
      <th>1151</th>
      <td>2025/114</td>
      <td>Marie Curie End of Life Transformation</td>
      <td>Lynne Hughes, Marie Curie\nMichelle Vermeulen</td>
      <td>Digital Economy Act 2017</td>
      <td>SAIL Databank: Census Wales 2021</td>
      <td>SAIL</td>
      <td>2025-05-12</td>
      <td>2025Q2</td>
      <td>2025</td>
      <td>2025-04-01</td>
      <td>Q2 2025</td>
      <td>sail databank: census wales 2021</td>
      <td>census wales 2021</td>
    </tr>
  </tbody>
</table>
<p>454 rows × 13 columns</p>
</div>




```python
# Handle common suffixes in dataset names to simplify and standardise them (at the cost of some geographic coverage information)
def remove_suffixes(dataset_name):
    """
    Remove common suffixes from dataset names to standardise them.
    """
     # Normalize dashes
    dataset_name = dataset_name.replace("–", "-").replace("—", "-")
    suffixes = ["- uk",
                "- england",
                "- great britain",
                "- gb",
                "- england and wales",
                "- wales",
                "srs iteration 1 standard extract",
                "srs iteration 2 standard extract",
                "uk",
                "person",
                "-ofqual-dfe-ucas",
                "wave 1",
                "wave 2 - exclusions",
                "wave 2",
                " - ",
                "finalised",
                "individual"]
    for suffix in suffixes:
        if dataset_name.endswith(suffix):
            dataset_name = dataset_name[:-len(suffix)].strip()
    return dataset_name
```


```python
# Clean up dataset abbreviated names and mismatches
def clean_dataset_names_replace(dataset_name):
    """
    Clean up dataset names with common abbreviations or mismatches.
    """
    replacements = {
        "leo via": "longitudinal education outcomes",
        "leo": "longitudinal education outcomes",
        "longitudinal education outcomes srs iteration 1 standard extract - englanddfe": "longitudinal education outcomes",
        "longitudinal study": "ons longitudinal study",
        "ucas grading and admissions data": "grading and admissions data england",
        "2011 census": "census 2011",
        "labour force survey & labour force survey": "labour force survey",
        "ministry of justice data first crown court defendant": "data first: crown court dataset",
        "moj data first crown court defendant case level dataset": "data first: crown court dataset",
        "moj data first crown court defendant": "data first: crown court dataset",
        "retired ministry of justice data first crown court defendant": "data first: crown court dataset",
        "moj data first magistrates' court defendant": "data first: magistrates court dataset",
        "retired ministry of justice data first magistrates court defendant": "data first: magistrates court dataset",
        "ministry of justice data first magistrates court iteration 2": "data first: magistrates court dataset",
        "ministry of justice data first prisoner custodial journey": "data first: prisoner dataset",
        "moj data first prisoner custodial journey": "data first: prisoner dataset",
        "moj data first prisoner custodial journey level dataset": "data first: prisoner dataset",
        "moj data first linked criminal courts defendant case level dataset & moj data first magistrates' court defendant case level dataset": "data first: cross-justice system linking dataset",
        "data first: linked criminal courts dataset": "data first: cross-justice system linking dataset",
        "moj data first linked criminal courts and prisons defendant": "data first: cross-justice system linking dataset",
        "moj data first linked criminal courts defendant case level dataset": "data first: cross-justice system linking dataset",
        "moj data first prisoner custodial journey dataset": "data first: prisoner dataset",
        "data first prison iteration 2": "data first: prison dataset",
        "ministry of justice data first probation iteration 2": "data first: probation dataset",
        "ministry of justice data first crown court iteration 2": "data first: crown court dataset",
        "data first family court": "data first: family court dataset",
        "moj data first family court data extract": "data first: family court dataset",
        "data first familyman family court data": "data first: family court dataset",
        "ministry of justice data first probation": "data first: probation dataset",
        "quarterly labour force survey": "labour force survey",
        "business structure database: longitudinal": "business structure database longitudinal",
        "labour force survey five-quarter longitudinal dataset": "labour force survey longitudinal",
        "labour force survey two-quarter longitudinal dataset": "labour force survey longitudinal",
        "annual survey of hours": "annual survey of hours and earnings",
        "moj data first cross-justice system linking dataset – england and wales": "data first: cross-justice system linking dataset",
        "labour force survey -": "labour force survey",
        "moj data first probation": "data first: probation dataset",
        "longitudinal inter-departmental business register": "inter-departmental business register longitudinal",
        "growing up in england wave 2 - children in need": "growing up in england",
        "growing up in england wave 2 vulnerability measures": "growing up in england",
        "annual respondents": "annual respondents database",
        "annual respondents database x": "annual respondents database",
        "annual respondents database 2": "annual respondents database",
        "longitudinal inter­departmental business register": "inter-departmental business register longitudinal",
        "administrative data | agriculture research collection": "agricultural research collection",
        "administrative data | agriculture research collection - england": "agricultural research collection",
        "bespoke admin data: agricultural research collection - england": "agricultural research collection",
        "bespoke admin data: agricultural research collection": "agricultural research collection",
        "ashe longitudinal data england and wales": "annual survey of hours and earnings longitudinal",
        "ashe longitudinal data england": "annual survey of hours and earnings longitudinal",
        "ashe longitudinal": "annual survey of hours and earnings longitudinal",
        "ashe longitudinal data great britain": "annual survey of hours and earnings longitudinal",
        "annual survey for hours and earnings longitudinal": "annual survey of hours and earnings longitudinal",
        "annual survey for hours and earnings / census 2011 linked datase": "annual survey of hours and earnings linked to census 2011",
        "education and child health insights from linked data research database": "education and child health insights from linked data",
        }
    
    for key, value in replacements.items():
        if dataset_name == key:
            return value
    return dataset_name
```


```python
# Apply the remove_suffixes and clean_dataset_names_replace function to the dataset list
df_exploded['dataset_list_clean'] = df_exploded['dataset_list'].apply(remove_suffixes)
df_exploded['dataset_list_clean'] = df_exploded['dataset_list_clean'].apply(clean_dataset_names_replace)
```


```python
# Drop some place names and other commonly occuring words from the exploded dataset names
df_exploded = df_exploded[~df_exploded['dataset_list_clean'].isin(["", "nhs", "england", "england and wales", "index", "great britain", "patents", "survey", "wales and scotland", "ons","covid-19","and earnings", "wales", "university of oxford"])]
```


```python
# Check the cleaned dataset names
all_datasets_df = df_exploded['dataset_list_clean'].value_counts().reset_index()
all_datasets_df.columns = ['dataset', 'count']
all_datasets_df
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>dataset</th>
      <th>count</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>business structure database</td>
      <td>220</td>
    </tr>
    <tr>
      <th>1</th>
      <td>annual business survey</td>
      <td>191</td>
    </tr>
    <tr>
      <th>2</th>
      <td>annual survey of hours and earnings</td>
      <td>158</td>
    </tr>
    <tr>
      <th>3</th>
      <td>labour force survey</td>
      <td>151</td>
    </tr>
    <tr>
      <th>4</th>
      <td>annual population survey</td>
      <td>132</td>
    </tr>
    <tr>
      <th>...</th>
      <td>...</td>
      <td>...</td>
    </tr>
    <tr>
      <th>505</th>
      <td>census 2011 &amp; 2021 (welsh residents)</td>
      <td>1</td>
    </tr>
    <tr>
      <th>506</th>
      <td>secure origin</td>
      <td>1</td>
    </tr>
    <tr>
      <th>507</th>
      <td>destination</td>
      <td>1</td>
    </tr>
    <tr>
      <th>508</th>
      <td>tables for</td>
      <td>1</td>
    </tr>
    <tr>
      <th>509</th>
      <td>kids environment health cohort spine</td>
      <td>1</td>
    </tr>
  </tbody>
</table>
<p>510 rows × 2 columns</p>
</div>



## Analysis of all projects and datasets accessed through the DEA
- Over 1000 projects have been approved under the DEA between 2019 and 2025, applying for access to use an overall total of >2800 datasets

### Figure 1: New DEA accredited projects by year
Note that 2019 data only includes Q4, and 2025 data is only Q1 and partial Q2 (to mid-May 2025)


```python
# Set plot style
sns.set_style("darkgrid")

plt.figure(figsize=(10, 6))

# Sort the years
year_order = sorted(df['Accreditation Date Year'].dropna().unique())

# Plot the countplot
ax = sns.countplot(
    data=df,
    x='Accreditation Date Year',
    order=year_order,
    color='#4472C4',
    alpha=0.8,
    edgecolor='white'
)

# Set titles and labels
plt.title('New DEA Accredited Projects by Year*')
plt.xlabel('Year')
plt.ylabel('Number of Projects')
plt.xticks(rotation=45)

# Add asterisk above the 2025 bar
if 2025 in year_order:
    index_2025 = year_order.index(2025)
    height_2025 = ax.patches[index_2025].get_height()
    ax.text(index_2025, height_2025 + 3, '*', 
            ha='center', va='bottom', fontsize=14, color='black', weight='bold')

# Add footnote
plt.figtext(0.5, -0.05, '*2025 data includes projects approved up to 14 May only',
            ha='center', fontsize=10, style='italic')

plt.tight_layout()
plt.show()
```


    
![png](DEA_projects_analysis_files/DEA_projects_analysis_33_0.png)
    


### Figure 2: Top 25 datasets accessed under the DEA between end 2019 - mid May 2025
| Rank | Dataset                                                         | # Count |
|------|------------------------------------------------------------------|--------:|
| 1    | Business Structure Database                                      |     220 |
| 2    | Annual Business Survey                                           |     191 |
| 3    | Annual Survey of Hours and Earnings                              |     158 |
| 4    | Labour Force Survey                                              |     151 |
| 5    | Annual Population Survey                                         |     132 |
| 6    | Annual Respondents Database                                      |      98 |
| 7    | Longitudinal Education Outcomes                                  |      82 |
| 8    | UK Innovation Survey                                             |      67 |
| 9    | Business Enterprise Research and Development                     |      54 |
| 10   | Understanding Society                                            |      54 |
| 11   | Labour Force Survey Longitudinal                                 |      37 |
| 12   | Business Register Employment Survey                              |      33 |
| 13   | Crime Survey for England and Wales                               |      31 |
| 14   | International Trade in Services                                  |      29 |
| 15   | Labour Force Survey Household                                    |      29 |
| 16   | Annual Survey of Hours and Earnings Longitudinal                 |      29 |
| 17   | Longitudinal Small Business Survey                               |      28 |
| 18   | ONS Longitudinal Study                                           |      27 |
| 19   | Living Costs and Food Survey                                     |      27 |
| 20   | Education and Child Health Insights from Linked Data             |      25 |
| 21   | Growing Up in England                                            |      23 |
| 22   | Wealth and Assets Survey                                         |      21 |
| 23   | Data First: Crown Court Dataset                                  |      20 |
| 24   | Longitudinal Study of England and Wales                          |      19 |
| 25   | Business Insights and Conditions Survey                          |      19 |


```python
# All projects accessed a total number of datasets over 2800
all_datasets_df['count'].sum()
```




    np.int64(2757)




```python
def map_collection(dataset):
    """
    Map a single dataset name to its respective collection.
    """
    if pd.isna(dataset):
        return np.nan

    collection_mapping = {
        'agricultural research collection': 'Agricultural Research Collection',
        'annual survey of hours and earnings linked to census 2011': 'Wage and Employment Dynamics',
        'annual survey of hours and earnings longitudinal': 'Wage and Employment Dynamics',
        'annual survey of hours and earnings linked to paye and self-assessment data': 'Wage and Employment Dynamics',
        'data first: cross-justice system linking dataset': 'Data First',
        'data first: family court linked to cafcass and census 2021': 'Data First',
        'moj and dfe linked dataset': 'Data First',
        'data first: magistrates court dataset': 'Data First',
        'data first: crown court dataset': 'Data First',
        'data first: family court dataset': 'Data First',
        'data first: civil court data': 'Data First',
        'data first: prisoner dataset': 'Data First',
        'data first: probation dataset': 'Data First',
        'education and child health insights from linked data': 'ECHILD',
        'grading and admissions data england': 'GRADE',
        'growing up in england': 'Growing up in England',
        'longitudinal education outcomes': 'LEO'
    }

    return collection_mapping.get(dataset, np.nan)
        
df_exploded['collection'] = df_exploded['dataset_list_clean'].map(map_collection)
```


```python
df_exploded[df_exploded['dataset_list_clean'] == 'education and child health insights from linked data']
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>Project ID</th>
      <th>Title</th>
      <th>Researchers</th>
      <th>Legal Basis</th>
      <th>Datasets Used</th>
      <th>Secure Research Service</th>
      <th>Accreditation Date</th>
      <th>Accreditation Date Quarter</th>
      <th>Accreditation Date Year</th>
      <th>quarter_date</th>
      <th>Quarter Label</th>
      <th>datasets_clean</th>
      <th>dataset_list</th>
      <th>dataset_list_clean</th>
      <th>collection</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>965</th>
      <td>2024/163</td>
      <td>Exploring the Impact of Clinical Diagnosis on ...</td>
      <td>Elizabeth Camacho, The University of Liverpool...</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2024-08-27</td>
      <td>2024Q3</td>
      <td>2024</td>
      <td>2024-07-01</td>
      <td>Q3 2024</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>education and child health insights from linke...</td>
      <td>education and child health insights from linke...</td>
      <td>ECHILD</td>
    </tr>
    <tr>
      <th>972</th>
      <td>2024/197</td>
      <td>Evaluating the effects of the growing and unev...</td>
      <td>David Frayman, The London School of Economics\...</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2024-10-16</td>
      <td>2024Q4</td>
      <td>2024</td>
      <td>2024-10-01</td>
      <td>Q4 2024</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>education and child health insights from linke...</td>
      <td>education and child health insights from linke...</td>
      <td>ECHILD</td>
    </tr>
    <tr>
      <th>984</th>
      <td>2024/188</td>
      <td>Pathways through support services in neurodive...</td>
      <td>Simona Skripkauskaite, University of Oxford</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2024-10-02</td>
      <td>2024Q4</td>
      <td>2024</td>
      <td>2024-10-01</td>
      <td>Q4 2024</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>education and child health insights from linke...</td>
      <td>education and child health insights from linke...</td>
      <td>ECHILD</td>
    </tr>
    <tr>
      <th>985</th>
      <td>2024/187</td>
      <td>Educational Outcomes after Paediatric Brain In...</td>
      <td>Hope Kent, University of Exeter\nHuw Wiliams, ...</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2024-10-01</td>
      <td>2024Q4</td>
      <td>2024</td>
      <td>2024-10-01</td>
      <td>Q4 2024</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>education and child health insights from linke...</td>
      <td>education and child health insights from linke...</td>
      <td>ECHILD</td>
    </tr>
    <tr>
      <th>997</th>
      <td>2024/210</td>
      <td>MATCHED (Maternal mental health, Child Health ...</td>
      <td>Stuart Jarvis, University of York</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2024-10-30</td>
      <td>2024Q4</td>
      <td>2024</td>
      <td>2024-10-01</td>
      <td>Q4 2024</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>education and child health insights from linke...</td>
      <td>education and child health insights from linke...</td>
      <td>ECHILD</td>
    </tr>
    <tr>
      <th>1009</th>
      <td>2024/243</td>
      <td>Ethnic and migration variation and impact of a...</td>
      <td>Alua Yeskendir, University College London\nKat...</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2024-12-06</td>
      <td>2024Q4</td>
      <td>2024</td>
      <td>2024-10-01</td>
      <td>Q4 2024</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>education and child health insights from linke...</td>
      <td>education and child health insights from linke...</td>
      <td>ECHILD</td>
    </tr>
    <tr>
      <th>1015</th>
      <td>2025/017</td>
      <td>Out of Sight: Exclusions, Alternative Provisio...</td>
      <td>Kalyan Kumar Kameshwara, University of Notting...</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2025-01-28</td>
      <td>2025Q1</td>
      <td>2025</td>
      <td>2025-01-01</td>
      <td>Q1 2025</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>education and child health insights from linke...</td>
      <td>education and child health insights from linke...</td>
      <td>ECHILD</td>
    </tr>
    <tr>
      <th>1024</th>
      <td>2024/237</td>
      <td>The Burden of Child Sexual Exploitation and Ab...</td>
      <td>Patricio Troncoso, The University of Edinburgh...</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2024-12-05</td>
      <td>2024Q4</td>
      <td>2024</td>
      <td>2024-10-01</td>
      <td>Q4 2024</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>education and child health insights from linke...</td>
      <td>education and child health insights from linke...</td>
      <td>ECHILD</td>
    </tr>
    <tr>
      <th>1031</th>
      <td>2024/216</td>
      <td>Psychosocial disadvantage in pregnancy: risk o...</td>
      <td>Rema Ramakrishnan, University of Oxford\nNicol...</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2024-11-08</td>
      <td>2024Q4</td>
      <td>2024</td>
      <td>2024-10-01</td>
      <td>Q4 2024</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>education and child health insights from linke...</td>
      <td>education and child health insights from linke...</td>
      <td>ECHILD</td>
    </tr>
    <tr>
      <th>1042</th>
      <td>2024/230</td>
      <td>Health-related Outcomes, alternative Provision...</td>
      <td>Justin Yang, University College London</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2024-12-03</td>
      <td>2024Q4</td>
      <td>2024</td>
      <td>2024-10-01</td>
      <td>Q4 2024</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>education and child health insights from linke...</td>
      <td>education and child health insights from linke...</td>
      <td>ECHILD</td>
    </tr>
    <tr>
      <th>1046</th>
      <td>2025/001</td>
      <td>Health and Educational Outcomes of Children wi...</td>
      <td>Alastair Sutcliffe, University College London\...</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2025-01-13</td>
      <td>2025Q1</td>
      <td>2025</td>
      <td>2025-01-01</td>
      <td>Q1 2025</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>education and child health insights from linke...</td>
      <td>education and child health insights from linke...</td>
      <td>ECHILD</td>
    </tr>
    <tr>
      <th>1051</th>
      <td>2024/215</td>
      <td>Tackling child health inequality. An intervent...</td>
      <td>Lateef Akanni, The University of Liverpool\nYu...</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2024-11-11</td>
      <td>2024Q4</td>
      <td>2024</td>
      <td>2024-10-01</td>
      <td>Q4 2024</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>education and child health insights from linke...</td>
      <td>education and child health insights from linke...</td>
      <td>ECHILD</td>
    </tr>
    <tr>
      <th>1052</th>
      <td>2025/018</td>
      <td>Women’s mental illness in pregnancy: Exploring...</td>
      <td>Jayati Das-Munshi, King's College London\nMatt...</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2025-01-22</td>
      <td>2025Q1</td>
      <td>2025</td>
      <td>2025-01-01</td>
      <td>Q1 2025</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>education and child health insights from linke...</td>
      <td>education and child health insights from linke...</td>
      <td>ECHILD</td>
    </tr>
    <tr>
      <th>1054</th>
      <td>2024/226</td>
      <td>Understanding Anxiety, Stress and Depression i...</td>
      <td>Stephen Gorard, University of Durham\nNadia Si...</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2024-11-19</td>
      <td>2024Q4</td>
      <td>2024</td>
      <td>2024-10-01</td>
      <td>Q4 2024</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>education and child health insights from linke...</td>
      <td>education and child health insights from linke...</td>
      <td>ECHILD</td>
    </tr>
    <tr>
      <th>1065</th>
      <td>2025/045</td>
      <td>Effects of Air Quality on health and human cap...</td>
      <td>Ludovica Gazze, University of Warwick\nLorenzo...</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2025-02-24</td>
      <td>2025Q1</td>
      <td>2025</td>
      <td>2025-01-01</td>
      <td>Q1 2025</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>education and child health insights from linke...</td>
      <td>education and child health insights from linke...</td>
      <td>ECHILD</td>
    </tr>
    <tr>
      <th>1071</th>
      <td>2025/047</td>
      <td>Exploring Neurodivergence in Education: A Comp...</td>
      <td>Emily Lowthian, Swansea University\nJennifer K...</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2025-02-21</td>
      <td>2025Q1</td>
      <td>2025</td>
      <td>2025-01-01</td>
      <td>Q1 2025</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>education and child health insights from linke...</td>
      <td>education and child health insights from linke...</td>
      <td>ECHILD</td>
    </tr>
    <tr>
      <th>1073</th>
      <td>2025/050</td>
      <td>Early Childhood Health Shocks and Education Ou...</td>
      <td>Angel Marcos Vera Hernandez, University Colleg...</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2025-02-24</td>
      <td>2025Q1</td>
      <td>2025</td>
      <td>2025-01-01</td>
      <td>Q1 2025</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>education and child health insights from linke...</td>
      <td>education and child health insights from linke...</td>
      <td>ECHILD</td>
    </tr>
    <tr>
      <th>1079</th>
      <td>2025/032</td>
      <td>Risk factors for severe mental health outcomes...</td>
      <td>Jessica Griffiths, King's College London\nNeil...</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2025-02-03</td>
      <td>2025Q1</td>
      <td>2025</td>
      <td>2025-01-01</td>
      <td>Q1 2025</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>education and child health insights from linke...</td>
      <td>education and child health insights from linke...</td>
      <td>ECHILD</td>
    </tr>
    <tr>
      <th>1080</th>
      <td>2025/034</td>
      <td>Educational Attainment and Chronic Conditions ...</td>
      <td>Keyao Deng, University College London\nRichard...</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2025-02-05</td>
      <td>2025Q1</td>
      <td>2025</td>
      <td>2025-01-01</td>
      <td>Q1 2025</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>education and child health insights from linke...</td>
      <td>education and child health insights from linke...</td>
      <td>ECHILD</td>
    </tr>
    <tr>
      <th>1097</th>
      <td>2025/079</td>
      <td>“Birth and Beyond: Delivery Modes, Maternal He...</td>
      <td>Emilia Del Bono, University of Essex\nEmily Gr...</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2025-03-18</td>
      <td>2025Q1</td>
      <td>2025</td>
      <td>2025-01-01</td>
      <td>Q1 2025</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>education and child health insights from linke...</td>
      <td>education and child health insights from linke...</td>
      <td>ECHILD</td>
    </tr>
    <tr>
      <th>1100</th>
      <td>2025/094</td>
      <td>The long-term impact of school exclusion on ri...</td>
      <td>Joan Madia, University of Oxford\nAlice Wicker...</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2025-04-02</td>
      <td>2025Q2</td>
      <td>2025</td>
      <td>2025-04-01</td>
      <td>Q2 2025</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>education and child health insights from linke...</td>
      <td>education and child health insights from linke...</td>
      <td>ECHILD</td>
    </tr>
    <tr>
      <th>1135</th>
      <td>2025/006</td>
      <td>The Human Capital Cost of Air Pollution</td>
      <td>Lucie Gadenne, Institute for Fiscal Studies\nS...</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2025-01-13</td>
      <td>2025Q1</td>
      <td>2025</td>
      <td>2025-01-01</td>
      <td>Q1 2025</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>education and child health insights from linke...</td>
      <td>education and child health insights from linke...</td>
      <td>ECHILD</td>
    </tr>
    <tr>
      <th>1137</th>
      <td>2025/010</td>
      <td>Effects of preconception health on improving a...</td>
      <td>Danielle Schoenaker, University of Southampton...</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2025-01-15</td>
      <td>2025Q1</td>
      <td>2025</td>
      <td>2025-01-01</td>
      <td>Q1 2025</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>education and child health insights from linke...</td>
      <td>education and child health insights from linke...</td>
      <td>ECHILD</td>
    </tr>
    <tr>
      <th>1141</th>
      <td>2025/039</td>
      <td>Decoding the Signals from Classrooms: Early Wa...</td>
      <td>Huamao Wang, University of Nottingham</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2025-02-12</td>
      <td>2025Q1</td>
      <td>2025</td>
      <td>2025-01-01</td>
      <td>Q1 2025</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>education and child health insights from linke...</td>
      <td>education and child health insights from linke...</td>
      <td>ECHILD</td>
    </tr>
    <tr>
      <th>1149</th>
      <td>2025/098</td>
      <td>The NoRePF Project: Improving maternal and chi...</td>
      <td>Hannah Rayment-Jones, King's College London\nS...</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2025-04-09</td>
      <td>2025Q2</td>
      <td>2025</td>
      <td>2025-04-01</td>
      <td>Q2 2025</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>education and child health insights from linke...</td>
      <td>education and child health insights from linke...</td>
      <td>ECHILD</td>
    </tr>
  </tbody>
</table>
</div>




```python
df_exploded.isna().sum()
```




    Project ID                       0
    Title                            0
    Researchers                      2
    Legal Basis                      0
    Datasets Used                    0
    Secure Research Service          0
    Accreditation Date               0
    Accreditation Date Quarter       0
    Accreditation Date Year          0
    quarter_date                     0
    Quarter Label                    0
    datasets_clean                   0
    dataset_list                     0
    dataset_list_clean               0
    collection                    2530
    dtype: int64




```python
# ADR UK flagship datasets
flagship_datasets = ['agricultural research collection', 
                     'annual survey of hours and earnings linked to census 2011',
                     'annual survey of hours and earnings longitudinal',
                     'annual survey of hours and earnings linked to paye and self-assessment data',
                     'data first: cross-justice system linking dataset',
                     'data first: family court linked to cafcass and census 2021',
                     'education and child health insights from linked data',
                     'grading and admissions data england',
                     'growing up in england',
                     'longitudinal education outcomes',
                     'moj and dfe linked dataset', # note that this data is not accessed under the DEA so isn't in this dataset
                     'nursing and midwifery council register linked to census 2021',
                     'data first: magistrates court dataset', 
                     'data first: crown court dataset', 
                     'data first: family court dataset', 
                     'data first: civil court data', 
                     'data first: prisoner dataset',
                     'data first: probation dataset']
```


```python
data_flagship = df_exploded[df_exploded['dataset_list_clean'].isin(flagship_datasets)]
data_flagship[data_flagship['dataset_list_clean'] == 'agricultural research collection']
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>Project ID</th>
      <th>Title</th>
      <th>Researchers</th>
      <th>Legal Basis</th>
      <th>Datasets Used</th>
      <th>Secure Research Service</th>
      <th>Accreditation Date</th>
      <th>Accreditation Date Quarter</th>
      <th>Accreditation Date Year</th>
      <th>quarter_date</th>
      <th>Quarter Label</th>
      <th>datasets_clean</th>
      <th>dataset_list</th>
      <th>dataset_list_clean</th>
      <th>collection</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>425</th>
      <td>2022/129</td>
      <td>AD|ARC : Linking Individual and Farm Level Dat...</td>
      <td>Nicholas Webster, Welsh Government\nMatthew Ke...</td>
      <td>Digital Economy Act 2017</td>
      <td>Office for National Statistics: Agricultural R...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2022-09-11</td>
      <td>2022Q3</td>
      <td>2022</td>
      <td>2022-07-01</td>
      <td>Q3 2022</td>
      <td>office for national statistics: agricultural r...</td>
      <td>agricultural research collection</td>
      <td>agricultural research collection</td>
      <td>Agricultural Research Collection</td>
    </tr>
    <tr>
      <th>575</th>
      <td>2023/076</td>
      <td>AD|ARC (Administrative Data Agri-Research Coll...</td>
      <td>Nicholas Webster, Welsh Government\nSian Morri...</td>
      <td>Digital Economy Act 2017</td>
      <td>Department for Environment, Food &amp; Rural Affai...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2023-05-24</td>
      <td>2023Q2</td>
      <td>2023</td>
      <td>2023-04-01</td>
      <td>Q2 2023</td>
      <td>department for environment, food &amp; rural affai...</td>
      <td>bespoke admin data: agricultural research coll...</td>
      <td>agricultural research collection</td>
      <td>Agricultural Research Collection</td>
    </tr>
    <tr>
      <th>1017</th>
      <td>2024/224</td>
      <td>Sustaining their family, community and nation....</td>
      <td>Sian Morrison-Rees, Swansea University\nPaul C...</td>
      <td>Digital Economy Act 2017</td>
      <td>Department for Environment, Food &amp; Rural Affai...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2024-11-15</td>
      <td>2024Q4</td>
      <td>2024</td>
      <td>2024-10-01</td>
      <td>Q4 2024</td>
      <td>department for environment, food &amp; rural affai...</td>
      <td>administrative data | agriculture research col...</td>
      <td>agricultural research collection</td>
      <td>Agricultural Research Collection</td>
    </tr>
    <tr>
      <th>1050</th>
      <td>2024/236</td>
      <td>Farm household Resilience, Income Source and E...</td>
      <td>Sian Morrison-Rees, Swansea University\nPaul W...</td>
      <td>Digital Economy Act 2017</td>
      <td>Department for Environment, Food &amp; Rural Affai...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2024-12-03</td>
      <td>2024Q4</td>
      <td>2024</td>
      <td>2024-10-01</td>
      <td>Q4 2024</td>
      <td>department for environment, food &amp; rural affai...</td>
      <td>administrative data | agriculture research col...</td>
      <td>agricultural research collection</td>
      <td>Agricultural Research Collection</td>
    </tr>
  </tbody>
</table>
</div>




```python
data_flagship.groupby('dataset_list_clean').size().reset_index(name='count').sort_index(ascending=False)
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>dataset_list_clean</th>
      <th>count</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>13</th>
      <td>longitudinal education outcomes</td>
      <td>82</td>
    </tr>
    <tr>
      <th>12</th>
      <td>growing up in england</td>
      <td>23</td>
    </tr>
    <tr>
      <th>11</th>
      <td>grading and admissions data england</td>
      <td>10</td>
    </tr>
    <tr>
      <th>10</th>
      <td>education and child health insights from linke...</td>
      <td>25</td>
    </tr>
    <tr>
      <th>9</th>
      <td>data first: probation dataset</td>
      <td>6</td>
    </tr>
    <tr>
      <th>8</th>
      <td>data first: prisoner dataset</td>
      <td>8</td>
    </tr>
    <tr>
      <th>7</th>
      <td>data first: magistrates court dataset</td>
      <td>6</td>
    </tr>
    <tr>
      <th>6</th>
      <td>data first: family court dataset</td>
      <td>3</td>
    </tr>
    <tr>
      <th>5</th>
      <td>data first: crown court dataset</td>
      <td>20</td>
    </tr>
    <tr>
      <th>4</th>
      <td>data first: cross-justice system linking dataset</td>
      <td>6</td>
    </tr>
    <tr>
      <th>3</th>
      <td>annual survey of hours and earnings longitudinal</td>
      <td>29</td>
    </tr>
    <tr>
      <th>2</th>
      <td>annual survey of hours and earnings linked to ...</td>
      <td>4</td>
    </tr>
    <tr>
      <th>1</th>
      <td>annual survey of hours and earnings linked to ...</td>
      <td>1</td>
    </tr>
    <tr>
      <th>0</th>
      <td>agricultural research collection</td>
      <td>4</td>
    </tr>
  </tbody>
</table>
</div>




```python
df_exploded[df_exploded['dataset_list'].str.contains('agricultural research collection', case=False, na=False)]
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>Project ID</th>
      <th>Title</th>
      <th>Researchers</th>
      <th>Legal Basis</th>
      <th>Datasets Used</th>
      <th>Secure Research Service</th>
      <th>Accreditation Date</th>
      <th>Accreditation Date Quarter</th>
      <th>Accreditation Date Year</th>
      <th>quarter_date</th>
      <th>Quarter Label</th>
      <th>datasets_clean</th>
      <th>dataset_list</th>
      <th>dataset_list_clean</th>
      <th>collection</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>425</th>
      <td>2022/129</td>
      <td>AD|ARC : Linking Individual and Farm Level Dat...</td>
      <td>Nicholas Webster, Welsh Government\nMatthew Ke...</td>
      <td>Digital Economy Act 2017</td>
      <td>Office for National Statistics: Agricultural R...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2022-09-11</td>
      <td>2022Q3</td>
      <td>2022</td>
      <td>2022-07-01</td>
      <td>Q3 2022</td>
      <td>office for national statistics: agricultural r...</td>
      <td>agricultural research collection</td>
      <td>agricultural research collection</td>
      <td>Agricultural Research Collection</td>
    </tr>
    <tr>
      <th>575</th>
      <td>2023/076</td>
      <td>AD|ARC (Administrative Data Agri-Research Coll...</td>
      <td>Nicholas Webster, Welsh Government\nSian Morri...</td>
      <td>Digital Economy Act 2017</td>
      <td>Department for Environment, Food &amp; Rural Affai...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2023-05-24</td>
      <td>2023Q2</td>
      <td>2023</td>
      <td>2023-04-01</td>
      <td>Q2 2023</td>
      <td>department for environment, food &amp; rural affai...</td>
      <td>bespoke admin data: agricultural research coll...</td>
      <td>agricultural research collection</td>
      <td>Agricultural Research Collection</td>
    </tr>
  </tbody>
</table>
</div>




```python
flagship_projects = df[df['Project ID'].isin(data_flagship['Project ID'].unique())]
flagship_projects
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>Project ID</th>
      <th>Title</th>
      <th>Researchers</th>
      <th>Legal Basis</th>
      <th>Datasets Used</th>
      <th>Secure Research Service</th>
      <th>Accreditation Date</th>
      <th>Accreditation Date Quarter</th>
      <th>Accreditation Date Year</th>
      <th>quarter_date</th>
      <th>Quarter Label</th>
      <th>datasets_clean</th>
      <th>dataset_list</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>157</th>
      <td>2021/035</td>
      <td>Shaping, testing and demonstrating the value o...</td>
      <td>Polina Obolenskaya,\nLondon School of Economic...</td>
      <td>Digital Economy Act 2017</td>
      <td>Office for National Statistics: Growing Up in ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2021-11-05</td>
      <td>2021Q4</td>
      <td>2021</td>
      <td>2021-10-01</td>
      <td>Q4 2021</td>
      <td>office for national statistics: growing up in ...</td>
      <td>[growing up in england wave 1]</td>
    </tr>
    <tr>
      <th>159</th>
      <td>2021/038</td>
      <td>Using linked Magistrates and Crown Court data ...</td>
      <td>Rebecca Pattinson, University of Lancaster</td>
      <td>Digital Economy Act 2017</td>
      <td>Ministry of Justice: MoJ Data First Crown cour...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2021-04-21</td>
      <td>2021Q2</td>
      <td>2021</td>
      <td>2021-04-01</td>
      <td>Q2 2021</td>
      <td>ministry of justice: moj data first crown cour...</td>
      <td>[moj data first crown court defendant case lev...</td>
    </tr>
    <tr>
      <th>160</th>
      <td>2021/039</td>
      <td>A ticking social timebomb?' An investigation i...</td>
      <td>Angela Sorsby, University of Sheffield</td>
      <td>Digital Economy Act 2017</td>
      <td>Ministry of Justice: MoJ Data First Crown cour...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2021-11-05</td>
      <td>2021Q4</td>
      <td>2021</td>
      <td>2021-10-01</td>
      <td>Q4 2021</td>
      <td>ministry of justice: moj data first crown cour...</td>
      <td>[moj data first crown court defendant case lev...</td>
    </tr>
    <tr>
      <th>161</th>
      <td>2021/040</td>
      <td>Understanding the nature, extent and outcomes ...</td>
      <td>Tim McSweeney, University of Hertfordshire</td>
      <td>Digital Economy Act 2017</td>
      <td>Ministry of Justice: MoJ Data First Crown cour...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2021-04-16</td>
      <td>2021Q2</td>
      <td>2021</td>
      <td>2021-04-01</td>
      <td>Q2 2021</td>
      <td>ministry of justice: moj data first crown cour...</td>
      <td>[moj data first crown court defendant case lev...</td>
    </tr>
    <tr>
      <th>162</th>
      <td>2021/041</td>
      <td>Ethnic inequalities in the Criminal Justice Sy...</td>
      <td>Kitty Lymperopoulou, Manchester Metropolitan U...</td>
      <td>Digital Economy Act 2017</td>
      <td>Ministry of Justice: MoJ Data First Crown cour...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2021-04-21</td>
      <td>2021Q2</td>
      <td>2021</td>
      <td>2021-04-01</td>
      <td>Q2 2021</td>
      <td>ministry of justice: moj data first crown cour...</td>
      <td>[moj data first crown court defendant case lev...</td>
    </tr>
    <tr>
      <th>...</th>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
    </tr>
    <tr>
      <th>1141</th>
      <td>2025/039</td>
      <td>Decoding the Signals from Classrooms: Early Wa...</td>
      <td>Huamao Wang, University of Nottingham</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2025-02-12</td>
      <td>2025Q1</td>
      <td>2025</td>
      <td>2025-01-01</td>
      <td>Q1 2025</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>[nhs, education and child health insights from...</td>
    </tr>
    <tr>
      <th>1142</th>
      <td>2025/042</td>
      <td>Understanding Household and Parental Predictor...</td>
      <td>Yu Cui, University of Reading\nHolly Joseph, U...</td>
      <td>Digital Economy Act 2017</td>
      <td>Office for National Statistics &amp; Department fo...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2025-02-19</td>
      <td>2025Q1</td>
      <td>2025</td>
      <td>2025-01-01</td>
      <td>Q1 2025</td>
      <td>office for national statistics &amp; department fo...</td>
      <td>[growing up in england wave 1, growing up in e...</td>
    </tr>
    <tr>
      <th>1143</th>
      <td>2025/056</td>
      <td>The Heterogeneous Impact of Urban Renewal Prog...</td>
      <td>Edoardo Badii, University of Warwick\nPaul Dav...</td>
      <td>Digital Economy Act 2017</td>
      <td>Office for National Statistics: Annual Respond...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2025-02-26</td>
      <td>2025Q1</td>
      <td>2025</td>
      <td>2025-01-01</td>
      <td>Q1 2025</td>
      <td>office for national statistics: annual respond...</td>
      <td>[annual respondents, database x ­ uk, annual s...</td>
    </tr>
    <tr>
      <th>1145</th>
      <td>2025/074</td>
      <td>Examining Associations between Disability with...</td>
      <td>Lijie Zeng, University of Edinburgh\nJasmin We...</td>
      <td>Digital Economy Act 2017</td>
      <td>Office for National Statistics &amp; Department fo...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2025-03-12</td>
      <td>2025Q1</td>
      <td>2025</td>
      <td>2025-01-01</td>
      <td>Q1 2025</td>
      <td>office for national statistics &amp; department fo...</td>
      <td>[growing up in england wave 1, growing up in e...</td>
    </tr>
    <tr>
      <th>1149</th>
      <td>2025/098</td>
      <td>The NoRePF Project: Improving maternal and chi...</td>
      <td>Hannah Rayment-Jones, King's College London\nS...</td>
      <td>Digital Economy Act 2017</td>
      <td>NHS; DfE: Education and Child Health Insights ...</td>
      <td>Office for National Statistics Secure Research...</td>
      <td>2025-04-09</td>
      <td>2025Q2</td>
      <td>2025</td>
      <td>2025-04-01</td>
      <td>Q2 2025</td>
      <td>nhs; dfe: education and child health insights ...</td>
      <td>[nhs, education and child health insights from...</td>
    </tr>
  </tbody>
</table>
<p>185 rows × 13 columns</p>
</div>



## Analysis of ADR UK flagship dataset demand

- Since Q1 2021 to end of Q1 2025, there have been 173 projects requesting access to a total of 218 ADR UK flagship datasets


```python
# Truncate data up to (end of) Q1 2025, as we don't have all the data for Q2 2025 yet
# Define the cutoff: start of Q2 2025 = 1 April 2025
cutoff = pd.to_datetime("2025-04-01")

# Filter data_flagship to keep only rows before Q2 2025
data_flagship = data_flagship[data_flagship['Accreditation Date'] < cutoff]
```

### Figure 3: Growth in overall ADR England flagship data requests 
This figure shows the number of research projects accessing ADR UK flagship datasets over time, aggregated by year (left) and quarter (right). The bar chart on the left indicates annual totals, with a marked increase in 2024. The 2025 value reflects only Q1 data (as noted by the asterisk). The right-hand chart provides a more granular quarterly view, revealing a clear upward trend beginning in early 2023 and accelerating through 2024 and Q1 2025. The data illustrate rising research interest and engagement with ADR England flagship datasets.



```python
# Prepare data for both plots
year_order = sorted(data_flagship['Accreditation Date Year'].dropna().unique())

# Create quarter labels and ordering
quarter_periods = data_flagship['Accreditation Date Quarter'].dropna().unique()
quarter_periods_sorted = sorted(quarter_periods)
quarter_labels_ordered = [f"Q{q.quarter} {q.year}" for q in quarter_periods_sorted]
data_flagship['Quarter Label Clean'] = (
    'Q' + data_flagship['Accreditation Date Quarter'].dt.quarter.astype(str) + 
    ' ' + data_flagship['Accreditation Date Quarter'].dt.year.astype(str)
)

# Create side-by-side subplots
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

# Annual plot
sns.countplot(
    data=data_flagship,
    x='Accreditation Date Year',
    order=year_order,
    color='#4472C4',
    alpha=0.8,
    edgecolor='white',
    ax=ax1
)
ax1.set_title('ADR UK Flagship Datasets Accessed by Year')
ax1.set_xlabel('Year')
ax1.set_ylabel('Number of Projects')
ax1.tick_params(axis='x', rotation=45)

# Add asterisk above the 2025 bar and footnote below
if 2025 in year_positions:
    pos_2025 = year_positions[2025]
    # Get height of the bar at that position
    bar_patch = ax1.patches[pos_2025]
    bar_height = bar_patch.get_height()

    # Place asterisk above the bar
    ax1.text(pos_2025, bar_height + 1, '*', ha='center', va='bottom', fontsize=14, weight='bold')

    # Add footnote below the axis
    x_pos = pos_2025 / (len(year_order) - 1) if len(year_order) > 1 else 0.5
    ax1.text(x_pos, -0.15, '*2025 data only includes Q1', transform=ax1.transAxes,
             fontsize=9, style='italic', ha='center', verticalalignment='top')

# Quarterly plot
sns.countplot(
    data=data_flagship,
    x='Quarter Label Clean',
    order=quarter_labels_ordered,
    color='#4472C4',
    alpha=0.8,
    edgecolor='white',
    ax=ax2
)
ax2.set_title('ADR UK Flagship Datasets Accessed by Quarter')
ax2.set_xlabel('Quarter')
ax2.set_ylabel('Number of Projects')
ax2.tick_params(axis='x', rotation=45)

plt.tight_layout()
plt.show()
```


    
![png](DEA_projects_analysis_files/DEA_projects_analysis_48_0.png)
    



```python
# Some quarters have zero counts, so we need to create a full quarterly index
# Create full quarterly index from min to max quarter
full_quarters = pd.period_range(
    start=data_flagship['Accreditation Date Quarter'].min(),
    end=data_flagship['Accreditation Date Quarter'].max(),
    freq='Q'
)

# Create full multi-index with all collections
collections = data_flagship['collection'].dropna().unique()
full_index = pd.MultiIndex.from_product([full_quarters, collections], names=['Accreditation Date Quarter', 'collection'])

# Reindex to fill missing quarters with zero
collection_quarter_counts = (
    data_flagship
    .groupby(['Accreditation Date Quarter', 'collection'])
    .size()
    .reindex(full_index, fill_value=0)
    .reset_index(name='count')
)

# Add quarter_date and labels again
collection_quarter_counts['quarter_date'] = collection_quarter_counts['Accreditation Date Quarter'].dt.to_timestamp(how = 'start')
collection_quarter_counts['Quarter Label'] = collection_quarter_counts['Accreditation Date Quarter'].apply(
    lambda p: f"Q{p.quarter} {p.year}"
)

# Create pivot table from collection_quarter_counts
count_pivot = collection_quarter_counts.pivot_table(
    index='Quarter Label',
    columns='collection',
    values='count',
    aggfunc='sum'
)
count_pivot['Total'] = count_pivot.sum(axis=1)

# Basic summary row
summary_df = pd.DataFrame({
    'Total': [count_pivot['Total'].sum()],
}, index=['Total'])

# Combine
count_table = pd.concat([count_pivot, summary_df])
```


```python
# Extract quarterly totals from the count_table
# Filter out summary rows and get only quarterly data
summary_stats_to_exclude = ['Total', 'Mean', 'Median', 'Std_Dev', 'CV', 'Quarterly_Growth_Rate', 'Active_Quarters']
quarterly_rows = count_table[~count_table.index.isin(summary_stats_to_exclude)]
quarterly_totals = quarterly_rows['Total']

# Create a clean dataframe for analysis
quarters_df = pd.DataFrame({
    'Quarter': quarterly_totals.index,
    'Projects': quarterly_totals.values
})

# Convert quarter labels to datetime for proper analysis
def quarter_to_date(quarter_str):
    """Convert 'Q1 2021' format to datetime"""
    parts = quarter_str.split()
    quarter = int(parts[0][1:])  # Remove 'Q' and convert
    year = int(parts[1])
    month = (quarter - 1) * 3 + 1  # Q1=1, Q2=4, Q3=7, Q4=10
    return pd.Timestamp(year, month, 1)

quarters_df['Date'] = quarters_df['Quarter'].apply(quarter_to_date)
quarters_df = quarters_df.sort_values('Date').reset_index(drop=True)
quarters_df['Year'] = quarters_df['Date'].dt.year

# Group by year and calculate annual totals (only for complete years)
annual_data = quarters_df.groupby('Year').agg({
    'Projects': ['sum', 'mean', 'std', 'count']
}).round(1)

annual_data.columns = ['Annual_Total', 'Quarterly_Mean', 'Quarterly_Std', 'Quarters_Count']

# Only include years with 4 complete quarters
complete_years = annual_data[annual_data['Quarters_Count'] == 4].copy()

# Calculate additional metrics
complete_years['CV'] = (complete_years['Quarterly_Std'] / complete_years['Quarterly_Mean']).round(3)
complete_years['YoY_Growth'] = complete_years['Annual_Total'].pct_change() * 100

print("# ADR UK Flagship Collections - Annual Performance Analysis")
print()
print(f"**Analysis Period:** {quarters_df['Quarter'].iloc[0]} to {quarters_df['Quarter'].iloc[-1]}")
print(f"**Total Quarters:** {len(quarters_df)}")
print()

# ========================================
# MARKDOWN TABLE 1: ANNUAL PERFORMANCE
# ========================================
print("## Annual Performance Summary")
print()
print("| Year | Annual Total | Avg per Quarter | Quarterly Std Dev | CV | YoY Growth |")
print("|------|--------------|-----------------|-------------------|----|-----------:|")

for year, row in complete_years.iterrows():
    annual_total = int(row['Annual_Total'])
    quarterly_mean = f"{row['Quarterly_Mean']:.1f}"
    quarterly_std = f"{row['Quarterly_Std']:.1f}"
    cv = f"{row['CV']:.3f}"
    
    # Handle YoY growth (first year will be NaN)
    if pd.isna(row['YoY_Growth']):
        yoy_growth = "—"
    else:
        yoy_growth = f"{row['YoY_Growth']:+.1f}%"
    
    print(f"| {year} | {annual_total} | {quarterly_mean} | {quarterly_std} | {cv} | {yoy_growth} |")

print()

# ========================================
# MARKDOWN TABLE 2: QUARTERLY BREAKDOWN
# ========================================
print("## Quarterly Breakdown")
print()

# Create quarterly pivot table
quarterly_pivot = quarters_df.pivot_table(
    index='Year', 
    columns=quarters_df['Quarter'].str.split().str[0],  # Extract Q1, Q2, etc.
    values='Projects', 
    aggfunc='first'
).fillna('—')

# Reorder columns to Q1, Q2, Q3, Q4
quarter_cols = ['Q1', 'Q2', 'Q3', 'Q4']
available_cols = [col for col in quarter_cols if col in quarterly_pivot.columns]
quarterly_pivot = quarterly_pivot[available_cols]

# Add annual total column
quarterly_pivot['Annual Total'] = quarterly_pivot.replace('—', 0).sum(axis=1)
quarterly_pivot = quarterly_pivot.replace(0, '—')  # Convert back zeros to dashes for display

print("| Year | Q1 | Q2 | Q3 | Q4 | Annual Total |")
print("|------|----|----|----|----|-------------:|")

for year, row in quarterly_pivot.iterrows():
    if year in complete_years.index:  # Only show complete years
        q_values = []
        for col in available_cols:
            val = row[col]
            q_values.append(str(int(val)) if val != '—' else '—')
        
        annual_val = int(complete_years.loc[year, 'Annual_Total'])
        q_str = " | ".join(q_values)
        print(f"| {year} | {q_str} | {annual_val} |")

print()

# ========================================
# KEY METRICS SUMMARY
# ========================================
if len(complete_years) > 1:
    print("## Key Growth Metrics")
    print()
    
    # Calculate CAGR
    first_year_total = complete_years.iloc[0]['Annual_Total']
    last_year_total = complete_years.iloc[-1]['Annual_Total']
    years_span = len(complete_years) - 1
    
    if years_span > 0 and first_year_total > 0:
        cagr = (((last_year_total / first_year_total) ** (1/years_span)) - 1) * 100
    
    # Summary stats
    total_growth = ((last_year_total / first_year_total) - 1) * 100
    avg_annual_projects = complete_years['Annual_Total'].mean()
    most_stable_year = complete_years.loc[complete_years['CV'].idxmin()].name
    most_volatile_year = complete_years.loc[complete_years['CV'].idxmax()].name
    
    print("| Metric | Value |")
    print("|--------|------:|")
    print(f"| **CAGR ({complete_years.index[0]}-{complete_years.index[-1]})** | **{cagr:.1f}%** |")
    print(f"| Total Growth | {total_growth:.1f}% |")
    print(f"| Average Annual Projects | {avg_annual_projects:.0f} |")
    print(f"| Most Stable Year (lowest CV) | {most_stable_year} |")
    print(f"| Most Volatile Year (highest CV) | {most_volatile_year} |")
    
    print()
    print("**Notes:**")
    print("- CV = Coefficient of Variation (volatility measure)")
    print("- Lower CV indicates more consistent quarterly performance")
    print("- YoY = Year-over-Year growth rate")

 
```

    # ADR UK Flagship Collections - Annual Performance Analysis
    
    **Analysis Period:** Q1 2021 to Q1 2025
    **Total Quarters:** 17
    
    ## Annual Performance Summary
    
    | Year | Annual Total | Avg per Quarter | Quarterly Std Dev | CV | YoY Growth |
    |------|--------------|-----------------|-------------------|----|-----------:|
    | 2021 | 20 | 5.0 | 4.2 | 0.840 | — |
    | 2022 | 28 | 7.0 | 3.5 | 0.500 | +40.0% |
    | 2023 | 44 | 11.0 | 2.9 | 0.264 | +57.1% |
    | 2024 | 89 | 22.2 | 8.5 | 0.383 | +102.3% |
    
    ## Quarterly Breakdown
    
    | Year | Q1 | Q2 | Q3 | Q4 | Annual Total |
    |------|----|----|----|----|-------------:|
    | 2021 | 2 | 10 | 1 | 7 | 20 |
    | 2022 | 10 | 10 | 4 | 4 | 28 |
    | 2023 | 13 | 8 | 9 | 14 | 44 |
    | 2024 | 11 | 21 | 26 | 31 | 89 |
    
    ## Key Growth Metrics
    
    | Metric | Value |
    |--------|------:|
    | **CAGR (2021-2024)** | **64.5%** |
    | Total Growth | 345.0% |
    | Average Annual Projects | 45 |
    | Most Stable Year (lowest CV) | 2023 |
    | Most Volatile Year (highest CV) | 2021 |
    
    **Notes:**
    - CV = Coefficient of Variation (volatility measure)
    - Lower CV indicates more consistent quarterly performance
    - YoY = Year-over-Year growth rate
    

    C:\Users\balin\AppData\Local\Temp\ipykernel_12468\322116584.py:90: FutureWarning: Downcasting behavior in `replace` is deprecated and will be removed in a future version. To retain the old behavior, explicitly call `result.infer_objects(copy=False)`. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`
      quarterly_pivot['Annual Total'] = quarterly_pivot.replace('—', 0).sum(axis=1)
    

### Figure 4: Growth Metrics for ADR UK Flagship Dataset Access (2021–2024)
This figure summarises the rising demand for ADR England flagship datasets through three related tables:

- The Annual Performance Summary table (top) shows yearly totals, average projects per quarter, standard deviation, and coefficient of variation (CV). Notably, dataset access more than quadrupled from 2021 to 2024, with a +102.3% year-over-year increase in 2024 alone. The falling CV from 2021 to 2023 indicates increasingly stable quarterly uptake.
- The Quarterly Breakdown (middle) provides granular counts per quarter. This reveals surges in late 2023 and sustained growth across all quarters of 2024.
- The Key Growth Metrics table (bottom) quantifies the overall trend: a Compound Annual Growth Rate (CAGR) of 64.5% from 2021 to 2024 and 345% total growth over that period.

#### Annual Performance Summary

| Year | Annual Total | Avg per Quarter | Quarterly Std Dev | CV | Year-over-Year Growth |
|------|--------------|-----------------|-------------------|----|-----------:|
| 2021 | 20 | 5.0 | 4.2 | 0.840 | — |
| 2022 | 28 | 7.0 | 3.5 | 0.500 | +40.0% |
| 2023 | 44 | 11.0 | 2.9 | 0.264 | +57.1% |
| 2024 | 89 | 22.2 | 8.5 | 0.383 | +102.3% |

#### Quarterly Breakdown

| Year | Q1 | Q2 | Q3 | Q4 | Annual Total |
|------|----|----|----|----|-------------:|
| 2021 | 2 | 10 | 1 | 7 | 20 |
| 2022 | 10 | 10 | 4 | 4 | 28 |
| 2023 | 13 | 8 | 9 | 14 | 44 |
| 2024 | 11 | 21 | 26 | 31 | 89 |

#### Key Growth Metrics

| Metric | Value |
|--------|------:|
| **Compound Annual Growth Rate (2021-2024)** | **64.5%** |
| Total Growth | 345.0% |
| Average Annual Requests | 45 |

**Notes:**
- CV = Coefficient of Variation (volatility measure). Lower CV indicates more consistent quarterly performance


```python
quarterly_pivot.index.name = 'Year'
quarterly_pivot = quarterly_pivot.reset_index()

quarterly_long = quarterly_pivot.melt(
    id_vars='Year',
    value_vars=['Q1', 'Q2', 'Q3', 'Q4'],
    var_name='Quarter',
    value_name='Access Count'
).dropna(subset=['Access Count'])

# Create quarterly timestamps (optional, but useful for plotting)
quarterly_long['Quarter Period'] = pd.PeriodIndex(
    quarterly_long['Year'].astype(str) + quarterly_long['Quarter'],
    freq='Q'
).to_timestamp()

# Sort chronologically
quarterly_long = quarterly_long.sort_values('Quarter Period').reset_index(drop=True)
```


```python
import statsmodels.api as sm
import statsmodels.formula.api as smf
import numpy as np
import pandas as pd

# Ensure clean copy and numeric data
df = quarterly_long.copy()
df["Access Count"] = pd.to_numeric(df["Access Count"], errors="coerce")
df = df.dropna(subset=["Access Count"]).reset_index(drop=True)
df["Quarter Index"] = range(len(df))
df["Log Access"] = np.log1p(df["Access Count"])

# Compare different models for the quarterly access counts

# Model 1: Linear
linear_model = smf.ols("Q('Access Count') ~ Q('Quarter Index')", data=df).fit()

# Model 2: Log-linear
loglin_model = smf.ols("Q('Log Access') ~ Q('Quarter Index')", data=df).fit()

# Model 3: Poisson
poisson_model = smf.glm("Q('Access Count') ~ Q('Quarter Index')", data=df,
                        family=sm.families.Poisson()).fit()

# Compare models
comparison = pd.DataFrame({
    "Model": ["Linear", "Log-linear", "Poisson"],
    "R-squared": [
        linear_model.rsquared,
        loglin_model.rsquared,
        np.nan  # Poisson doesn't have R-squared
    ],
    "AIC": [
        linear_model.aic,
        loglin_model.aic,
        poisson_model.aic
    ],
    "BIC": [
        linear_model.bic,
        loglin_model.bic,
        poisson_model.bic
    ],
    "P-value (Index)": [
        linear_model.pvalues["Q('Quarter Index')"],
        loglin_model.pvalues["Q('Quarter Index')"],
        poisson_model.pvalues["Q('Quarter Index')"]
    ]
})
print(comparison)

```

            Model  R-squared         AIC         BIC  P-value (Index)
    0      Linear   0.673285  111.196235  112.862661     5.459291e-05
    1  Log-linear   0.649698   25.541040   27.207467     9.347735e-05
    2     Poisson        NaN  103.366930  -12.425846     3.610071e-19
    

    c:\Users\balin\Desktop\ADR_DEA_project\venv\Lib\site-packages\statsmodels\genmod\generalized_linear_model.py:1923: FutureWarning: The bic value is computed using the deviance formula. After 0.13 this will change to the log-likelihood based formula. This change has no impact on the relative rank of models compared using BIC. You can directly access the log-likelihood version using the `bic_llf` attribute. You can suppress this message by calling statsmodels.genmod.generalized_linear_model.SET_USE_BIC_LLF with True to get the LLF-based version now or False to retainthe deviance version.
      warnings.warn(
    

### Figure 5: Model comparison of forecasting approaches for ADR England flagship access requests
This table compares three fitted models—linear, log-linear (exponential growth), and Poisson—based on R-squared, Akaike Information Criterion (AIC), Bayesian Information Criterion (BIC), and the significance of the time trend (Quarter Index). The log-linear model yields the lowest AIC and BIC, indicating the best trade-off between fit and complexity. The Poisson model has the most statistically significant time trend (p < 0.001), while the linear model has the highest R². However, caution is advised when comparing BIC values across model types due to differing likelihood formulations.

| Model       | R-squared | AIC       | BIC        | P-value (Index) |
|-------------|-----------|-----------|------------|-----------------|
| Linear      | 0.6733    | 111.1962  | 112.8627   | 5.46e-05        |
| Log-linear  | 0.6497    | 25.5410   | 27.2075    | 9.35e-05        |
| Poisson     | —         | 103.3669  | -12.4258   | 3.61e-19        |



```python
# log-linear and exponential models are equivalent in this case
# log-linear model is preferred for interpretability, and has a good fit
# Poisson model is also a good fit, but less interpretable for quarterly data
# Plot the log-linear model fit, ahd forecast
```


```python
quarterly_long
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>Year</th>
      <th>Quarter</th>
      <th>Access Count</th>
      <th>Quarter Period</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>2021</td>
      <td>Q1</td>
      <td>2.0</td>
      <td>2021-01-01</td>
    </tr>
    <tr>
      <th>1</th>
      <td>2021</td>
      <td>Q2</td>
      <td>10.0</td>
      <td>2021-04-01</td>
    </tr>
    <tr>
      <th>2</th>
      <td>2021</td>
      <td>Q3</td>
      <td>1.0</td>
      <td>2021-07-01</td>
    </tr>
    <tr>
      <th>3</th>
      <td>2021</td>
      <td>Q4</td>
      <td>7.0</td>
      <td>2021-10-01</td>
    </tr>
    <tr>
      <th>4</th>
      <td>2022</td>
      <td>Q1</td>
      <td>10.0</td>
      <td>2022-01-01</td>
    </tr>
    <tr>
      <th>5</th>
      <td>2022</td>
      <td>Q2</td>
      <td>10.0</td>
      <td>2022-04-01</td>
    </tr>
    <tr>
      <th>6</th>
      <td>2022</td>
      <td>Q3</td>
      <td>4.0</td>
      <td>2022-07-01</td>
    </tr>
    <tr>
      <th>7</th>
      <td>2022</td>
      <td>Q4</td>
      <td>4.0</td>
      <td>2022-10-01</td>
    </tr>
    <tr>
      <th>8</th>
      <td>2023</td>
      <td>Q1</td>
      <td>13.0</td>
      <td>2023-01-01</td>
    </tr>
    <tr>
      <th>9</th>
      <td>2023</td>
      <td>Q2</td>
      <td>8.0</td>
      <td>2023-04-01</td>
    </tr>
    <tr>
      <th>10</th>
      <td>2023</td>
      <td>Q3</td>
      <td>9.0</td>
      <td>2023-07-01</td>
    </tr>
    <tr>
      <th>11</th>
      <td>2023</td>
      <td>Q4</td>
      <td>14.0</td>
      <td>2023-10-01</td>
    </tr>
    <tr>
      <th>12</th>
      <td>2024</td>
      <td>Q1</td>
      <td>11.0</td>
      <td>2024-01-01</td>
    </tr>
    <tr>
      <th>13</th>
      <td>2024</td>
      <td>Q2</td>
      <td>21.0</td>
      <td>2024-04-01</td>
    </tr>
    <tr>
      <th>14</th>
      <td>2024</td>
      <td>Q3</td>
      <td>26.0</td>
      <td>2024-07-01</td>
    </tr>
    <tr>
      <th>15</th>
      <td>2024</td>
      <td>Q4</td>
      <td>31.0</td>
      <td>2024-10-01</td>
    </tr>
    <tr>
      <th>16</th>
      <td>2025</td>
      <td>Q1</td>
      <td>37.0</td>
      <td>2025-01-01</td>
    </tr>
    <tr>
      <th>17</th>
      <td>2025</td>
      <td>Q2</td>
      <td>—</td>
      <td>2025-04-01</td>
    </tr>
    <tr>
      <th>18</th>
      <td>2025</td>
      <td>Q3</td>
      <td>—</td>
      <td>2025-07-01</td>
    </tr>
    <tr>
      <th>19</th>
      <td>2025</td>
      <td>Q4</td>
      <td>—</td>
      <td>2025-10-01</td>
    </tr>
  </tbody>
</table>
</div>



### Figure 6: Forecast of ADR England Flagship Access Requests 
The line marked with circles shows observed quarterly access request counts from 2021 onwards. The dashed black line represents model predictions from a log-linear regression model fitted to historical data. The orange dashed line and x-marks indicate forecasted access requests for eight quarters beyond the most recent observation. The shaded region denotes the 95% confidence interval for the forecast, and the vertical red dotted line marks the point at which the forecast period begins.


```python
# Plot the fitted model
# Forecast 8 quarters ahead
n_forecast = 8
last_index = quarterly_long["Quarter Index"].max()
future_indices = np.arange(last_index + 1, last_index + 1 + n_forecast)

# Build future design matrix
future_df = pd.DataFrame({"Quarter Index": future_indices})
X_future = sm.add_constant(future_df)

# Predict with confidence intervals
pred = model.get_prediction(X_future)
pred_summary = pred.summary_frame(alpha=0.05)

# Add predictions to future_df
future_df["Predicted Access"] = np.expm1(pred_summary["mean"])
future_df["Lower CI"] = np.expm1(pred_summary["mean_ci_lower"])
future_df["Upper CI"] = np.expm1(pred_summary["mean_ci_upper"])
future_df["Quarter Period"] = pd.date_range(
    start=quarterly_long["Quarter Period"].max() + pd.offsets.QuarterBegin(),
    periods=n_forecast,
    freq="Q"
)

# Create forecast dataframe
forecast = future_df[["Quarter Period", "Predicted Access", "Lower CI", "Upper CI"]].copy()
forecast["Access Count"] = forecast["Predicted Access"]
forecast["Type"] = "Forecast"

# Add predicted values to existing data using the same model
X_existing = sm.add_constant(quarterly_long["Quarter Index"])
quarterly_long["Predicted Access"] = np.expm1(model.get_prediction(X_existing).summary_frame()["mean"])
# Observed dataframe with predictions already added
observed = quarterly_long[["Quarter Period", "Access Count", "Predicted Access"]].copy()
observed["Type"] = "Observed"

# Combine for plotting full prediction line
combined = pd.concat([
    observed[["Quarter Period", "Predicted Access"]],
    forecast[["Quarter Period", "Predicted Access"]]
], ignore_index=True)

# Plot
plt.figure(figsize=(14, 7))

# Plot observed and forecast points
plt.plot(observed["Quarter Period"], observed["Access Count"], label="Observed", marker="o")
plt.plot(forecast["Quarter Period"], forecast["Access Count"], label="Forecast", linestyle="--", marker="x")

# Full prediction line (observed + forecast)
plt.plot(combined["Quarter Period"], combined["Predicted Access"], linestyle="--", color="black", label="Model Prediction")

# Confidence interval shading
plt.fill_between(forecast["Quarter Period"], forecast["Lower CI"], forecast["Upper CI"],
                 color="gray", alpha=0.3, label="95% Confidence Interval")

# Forecast divider
plt.axvline(x=observed["Quarter Period"].iloc[-1], color='red', linestyle=':', label='Forecast begins')

# Labels and formatting
plt.title("Forecast of ADR England Flagship Access Requests")
plt.xlabel("Quarter")
plt.ylabel("Number of Access Requests")
plt.xticks(rotation=45)
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()

```

    C:\Users\balin\AppData\Local\Temp\ipykernel_12468\4030525790.py:19: FutureWarning: 'Q' is deprecated and will be removed in a future version, please use 'QE' instead.
      future_df["Quarter Period"] = pd.date_range(
    


    
![png](DEA_projects_analysis_files/DEA_projects_analysis_62_1.png)
    


## Breakdowns by individual ADR UK flagship datatset collections

**Datasets included in WED collection**:
- Annual Survey of Hours and Earnings Longitudinal
- Annual Survey of Hours and Earnings Linked to Census 2011  
- Annual Survey of Hours and Earnings Linked to PAYE and Self-Assessment Data  

**Datasets included in Data First collection**:
- Data First: Crown Court Dataset  
- Data First: Cross-Justice System Linking Dataset  
- Data First: Prisoner Dataset  
- Data First: Probation Dataset  
- Data First: Family Court Dataset  
- Data First: Magistrates Court Dataset  
- *Note: MoJ-DfE linkage is not included in this analysis as it is accessed via a different legal gateway and is not listed in the public register*


```python
# Generate summary tables of the data for the ADR UK flagship collections
# Create the full quarterly range
full_quarters = pd.period_range(
    start=data_flagship['Accreditation Date Quarter'].min(),
    end=data_flagship['Accreditation Date Quarter'].max(),
    freq='Q'
)

# Get all collections
collections = data_flagship['collection'].dropna().unique()

# Create the complete combinations
full_combinations = []
for quarter in full_quarters:
    for collection in collections:
        full_combinations.append({
            'Accreditation Date Quarter': quarter,
            'collection': collection,
            'quarter_date': quarter.to_timestamp(how='start'),
            'Quarter Label': f"Q{quarter.quarter} {quarter.year}"
        })

# Create the base dataframe with all combinations
base_df = pd.DataFrame(full_combinations)

# Get actual counts from original data
actual_counts = (
    data_flagship
    .groupby(['Accreditation Date Quarter', 'collection'])
    .size()
    .reset_index(name='count')
)

# Merge with base dataframe, filling missing with 0
collection_quarter_counts_new = base_df.merge(
    actual_counts,
    on=['Accreditation Date Quarter', 'collection'],
    how='left'
)
collection_quarter_counts_new['count'] = collection_quarter_counts_new['count'].fillna(0).astype(int)

# Find first appearance of each collection
first_appearance = (
    collection_quarter_counts_new[collection_quarter_counts_new['count'] > 0]
    .groupby('collection')['quarter_date']
    .min()
    .reset_index()
    .rename(columns={'quarter_date': 'first_quarter'})
)

# Merge back
collection_quarter_counts_new = collection_quarter_counts_new.merge(
    first_appearance,
    on='collection',
    how='left'
)

# Apply the logic
def assign_values(row):
    if pd.isna(row['first_quarter']):
        return np.nan  # Collection never appeared
    elif row['quarter_date'] < row['first_quarter']:
        return np.nan  # Before first appearance
    else:
        return row['count']  # Use actual count (0 or positive)

collection_quarter_counts_new['adjusted_count'] = collection_quarter_counts_new.apply(assign_values, axis=1)

# Remove incomplete Q2 2025 data
collection_quarter_counts_new = collection_quarter_counts_new[
    ~((collection_quarter_counts_new['quarter_date'].dt.year == 2025) & 
      (collection_quarter_counts_new['quarter_date'].dt.quarter == 2))
]

# Create the pivot tables with proper chronological ordering
collection_quarter_counts_new = collection_quarter_counts_new.sort_values('quarter_date')

# Create count pivot using quarter_date as index, then map to Quarter Label
count_pivot = collection_quarter_counts_new.pivot_table(
    values='adjusted_count',
    index='quarter_date',
    columns='collection',
    aggfunc='first'
)

# Create a mapping from quarter_date to Quarter Label in chronological order
quarter_label_mapping = (
    collection_quarter_counts_new[['quarter_date', 'Quarter Label']]
    .drop_duplicates()
    .sort_values('quarter_date')
    .set_index('quarter_date')['Quarter Label']
)

# Map the index to Quarter Labels while preserving order
count_pivot.index = count_pivot.index.map(quarter_label_mapping)
count_pivot.index.name = 'Quarter Label'

# Add row totals column
count_pivot['Total'] = count_pivot.sum(axis=1, skipna=True)

# ========================================
# ENHANCED SUMMARY STATISTICS WITH GROWTH METRICS
# ========================================

# Calculate summary statistics as rows (not mixing columns and rows)
def calculate_summary_row(df, stat_name, func):
    """Calculate a summary statistic row across all collection columns"""
    summary_row = {}
    for col in df.columns:
        if col == 'Total':
            # For the Total column, sum all quarterly totals
            if stat_name == 'Total':
                summary_row[col] = df[col].sum()
            elif stat_name == 'Mean':
                summary_row[col] = df[col].mean()
            elif stat_name == 'Std_Dev':
                summary_row[col] = df[col].std()
            else:
                summary_row[col] = func(df[col].dropna()) if len(df[col].dropna()) > 0 else 0
        else:
            # For individual collections
            valid_data = df[col].dropna()
            if len(valid_data) == 0:
                summary_row[col] = 0
            else:
                if stat_name == 'Total':
                    summary_row[col] = valid_data.sum()
                elif stat_name == 'Mean':
                    summary_row[col] = valid_data.mean()
                elif stat_name == 'Std_Dev':
                    summary_row[col] = valid_data.std()
                elif stat_name == 'CV':
                    mean_val = valid_data.mean()
                    std_val = valid_data.std()
                    summary_row[col] = std_val / mean_val if mean_val > 0 else 0
                elif stat_name == 'Quarterly_Growth_Rate':
                    # Calculate average quarterly growth rate
                    if len(valid_data) > 1:
                        non_zero_data = valid_data[valid_data > 0]
                        if len(non_zero_data) > 1:
                            growth_rates = []
                            for i in range(1, len(non_zero_data)):
                                prev_val = non_zero_data.iloc[i-1]
                                curr_val = non_zero_data.iloc[i]
                                if prev_val > 0:
                                    growth_rate = ((curr_val / prev_val) - 1) * 100
                                    growth_rates.append(growth_rate)
                            summary_row[col] = np.mean(growth_rates) if growth_rates else 0
                        else:
                            summary_row[col] = 0
                    else:
                        summary_row[col] = 0
                elif stat_name == 'Active_Quarters':
                    summary_row[col] = len(valid_data)
                else:
                    summary_row[col] = func(valid_data)
    
    return pd.Series(summary_row, name=stat_name)

# Create summary statistics rows
summary_rows = []
summary_rows.append(calculate_summary_row(count_pivot, 'Total', lambda x: x.sum()))
summary_rows.append(calculate_summary_row(count_pivot, 'Mean', lambda x: x.mean()))
summary_rows.append(calculate_summary_row(count_pivot, 'Std_Dev', lambda x: x.std()))
summary_rows.append(calculate_summary_row(count_pivot, 'CV', lambda x: x.std()/x.mean() if x.mean() > 0 else 0))
summary_rows.append(calculate_summary_row(count_pivot, 'Quarterly_Growth_Rate', lambda x: 0))
summary_rows.append(calculate_summary_row(count_pivot, 'Active_Quarters', lambda x: len(x)))

# Create summary DataFrame
summary_df = pd.DataFrame(summary_rows)

# Round the summary statistics for display
summary_df = summary_df.round({
    col: 2 if col != 'Total' else 0 for col in summary_df.columns
})

# Apply consistent rounding: 2 decimal places for most metrics, whole numbers for growth rate
for metric in ['Mean', 'Std_Dev', 'CV']:
    if metric in summary_df.index:
        summary_df.loc[metric] = summary_df.loc[metric].round(2)

# Round Quarterly_Growth_Rate to whole numbers
if 'Quarterly_Growth_Rate' in summary_df.index:
    summary_df.loc['Quarterly_Growth_Rate'] = summary_df.loc['Quarterly_Growth_Rate'].round(0)

# Keep Active_Quarters as integers
if 'Active_Quarters' in summary_df.index:
    summary_df.loc['Active_Quarters'] = summary_df.loc['Active_Quarters'].round(0)

# Combine quarterly data with summary statistics
count_table = pd.concat([count_pivot, summary_df])

print("=== ADR UK FLAGSHIP COLLECTIONS - INDIVIDUAL DATASET ANALYSIS ===")
print(f"Analysis period: {count_pivot.index[0]} to {count_pivot.index[-1]}")
print(f"Total collections analyzed: {len(collections)}")
print()

# ========================================
# COLLECTION PERFORMANCE SUMMARY
# ========================================
print("COLLECTION PERFORMANCE SUMMARY")
print("=" * 60)
print(f"{'Collection':<25} {'Total':<6} {'Avg/Q':<6} {'CV':<6} {'QGR%':<6} {'Quarters':<8}")
print("-" * 60)

# Get summary statistics for individual collections (exclude 'Total' column)
collection_columns = [col for col in count_pivot.columns if col != 'Total']
collection_summary = summary_df[collection_columns].T
collection_summary = collection_summary.sort_values('Total', ascending=False)

for collection, row in collection_summary.iterrows():
    total = int(row['Total'])
    mean_val = f"{row['Mean']:.2f}"
    cv = f"{row['CV']:.2f}"
    qgr = f"{row['Quarterly_Growth_Rate']:+.0f}"
    quarters = int(row['Active_Quarters'])
    
    print(f"{collection:<25} {total:<6} {mean_val:<6} {cv:<6} {qgr:<6} {quarters:<8}")

print()
print("Legend:")
print("- Total: Total projects across all quarters")
print("- Avg/Q: Average projects per active quarter")
print("- CV: Coefficient of Variation (volatility measure)")
print("- QGR%: Average quarterly growth rate")
print("- Quarters: Number of active quarters")
print()

# ========================================
# TOP PERFORMERS ANALYSIS
# ========================================
print("TOP PERFORMERS ANALYSIS")
print("=" * 40)

# Top by volume
top_volume = collection_summary.nlargest(3, 'Total')
print("🏆 TOP 3 BY TOTAL VOLUME:")
for i, (collection, row) in enumerate(top_volume.iterrows(), 1):
    print(f"  {i}. {collection}: {int(row['Total'])} projects")

print()

# Top by average quarterly access requests
top_avg_quarterly = collection_summary.nlargest(3, 'Mean')
print("TOP 3 BY AVG QUARTERLY ACCESS REQUESTS:")
for i, (collection, row) in enumerate(top_avg_quarterly.iterrows(), 1):
    print(f"  {i}. {collection}: {row['Mean']:.2f} projects per quarter")

# Top by growth rate (minimum 2 active quarters)
eligible_for_growth = collection_summary[collection_summary['Active_Quarters'] >= 2]
if len(eligible_for_growth) > 0:
    top_growth = eligible_for_growth.nlargest(3, 'Quarterly_Growth_Rate')
    print("TOP 3 BY QUARTERLY GROWTH RATE:")
    for i, (collection, row) in enumerate(top_growth.iterrows(), 1):
        print(f"  {i}. {collection}: {row['Quarterly_Growth_Rate']:+.0f}% per quarter")

print()

# Most consistent (lowest CV, minimum 3 quarters and >0 total)
eligible_for_consistency = collection_summary[
    (collection_summary['Active_Quarters'] >= 3) & 
    (collection_summary['Total'] > 0)
]
if len(eligible_for_consistency) > 0:
    most_consistent = eligible_for_consistency.nsmallest(3, 'CV')
    print("🎯 TOP 3 MOST CONSISTENT (Lowest CV):")
    for i, (collection, row) in enumerate(most_consistent.iterrows(), 1):
        print(f"  {i}. {collection}: CV = {row['CV']:.2f}")

print()

# Summary insights
total_projects = int(summary_df.loc['Total', 'Total'])
active_collections = len(collection_summary[collection_summary['Total'] > 0])
avg_projects_per_collection = collection_summary['Total'].mean()

print("SUMMARY INSIGHTS:")
print(f"- {active_collections} collections have delivered projects")
print(f"- Average of {avg_projects_per_collection:.1f} projects per active collection")
print(f"- Combined total: {total_projects} projects across all collections")

# Display the full table
print()
print("DETAILED QUARTERLY DATA:")
print("=" * 40)
print(count_table)
```

    === ADR UK FLAGSHIP COLLECTIONS - INDIVIDUAL DATASET ANALYSIS ===
    Analysis period: Q1 2021 to Q1 2025
    Total collections analyzed: 7
    
    COLLECTION PERFORMANCE SUMMARY
    ============================================================
    Collection                Total  Avg/Q  CV     QGR%   Quarters
    ------------------------------------------------------------
    LEO                       80     5.00   0.97   +98    16      
    Data First                49     3.06   1.13   +95    16      
    Wage and Employment Dynamics 31     1.82   0.65   +33    17      
    ECHILD                    23     7.67   0.76   +460   3       
    Growing up in England     21     1.50   1.19   +38    14      
    GRADE                     10     3.33   0.62   -48    3       
    Agricultural Research Collection 4      0.36   1.85   +50    11      
    
    Legend:
    - Total: Total projects across all quarters
    - Avg/Q: Average projects per active quarter
    - CV: Coefficient of Variation (volatility measure)
    - QGR%: Average quarterly growth rate
    - Quarters: Number of active quarters
    
    TOP PERFORMERS ANALYSIS
    ========================================
    🏆 TOP 3 BY TOTAL VOLUME:
      1. LEO: 80 projects
      2. Data First: 49 projects
      3. Wage and Employment Dynamics: 31 projects
    
    TOP 3 BY AVG QUARTERLY ACCESS REQUESTS:
      1. ECHILD: 7.67 projects per quarter
      2. LEO: 5.00 projects per quarter
      3. GRADE: 3.33 projects per quarter
    TOP 3 BY QUARTERLY GROWTH RATE:
      1. ECHILD: +460% per quarter
      2. LEO: +98% per quarter
      3. Data First: +95% per quarter
    
    🎯 TOP 3 MOST CONSISTENT (Lowest CV):
      1. GRADE: CV = 0.62
      2. Wage and Employment Dynamics: CV = 0.65
      3. ECHILD: CV = 0.76
    
    SUMMARY INSIGHTS:
    - 7 collections have delivered projects
    - Average of 31.1 projects per active collection
    - Combined total: 218 projects across all collections
    
    DETAILED QUARTERLY DATA:
    ========================================
                           Agricultural Research Collection  Data First  ECHILD  \
    Q1 2021                                             NaN         NaN     NaN   
    Q2 2021                                             NaN        7.00     NaN   
    Q3 2021                                             NaN        0.00     NaN   
    Q4 2021                                             NaN        6.00     NaN   
    Q1 2022                                             NaN        3.00     NaN   
    Q2 2022                                             NaN        4.00     NaN   
    Q3 2022                                            1.00        0.00     NaN   
    Q4 2022                                            0.00        0.00     NaN   
    Q1 2023                                            0.00        0.00     NaN   
    Q2 2023                                            1.00        1.00     NaN   
    Q3 2023                                            0.00        0.00     NaN   
    Q4 2023                                            0.00        8.00     NaN   
    Q1 2024                                            0.00        2.00     NaN   
    Q2 2024                                            0.00       11.00     NaN   
    Q3 2024                                            0.00        0.00    1.00   
    Q4 2024                                            2.00        5.00   10.00   
    Q1 2025                                            0.00        2.00   12.00   
    Total                                              4.00       49.00   23.00   
    Mean                                               0.36        3.06    7.67   
    Std_Dev                                            0.67        3.45    5.86   
    CV                                                 1.85        1.13    0.76   
    Quarterly_Growth_Rate                             50.00       95.00  460.00   
    Active_Quarters                                   11.00       16.00    3.00   
    
                           GRADE  Growing up in England    LEO  \
    Q1 2021                  NaN                    NaN    NaN   
    Q2 2021                  NaN                    NaN   3.00   
    Q3 2021                  NaN                    NaN   0.00   
    Q4 2021                  NaN                   1.00   0.00   
    Q1 2022                  NaN                   0.00   6.00   
    Q2 2022                  NaN                   1.00   2.00   
    Q3 2022                  NaN                   0.00   2.00   
    Q4 2022                  NaN                   2.00   1.00   
    Q1 2023                  NaN                   3.00   8.00   
    Q2 2023                  NaN                   3.00   1.00   
    Q3 2023                  NaN                   2.00   4.00   
    Q4 2023                  NaN                   0.00   2.00   
    Q1 2024                  NaN                   0.00   7.00   
    Q2 2024                  NaN                   0.00   8.00   
    Q3 2024                 5.00                   0.00  18.00   
    Q4 2024                 4.00                   3.00   6.00   
    Q1 2025                 1.00                   6.00  12.00   
    Total                  10.00                  21.00  80.00   
    Mean                    3.33                   1.50   5.00   
    Std_Dev                 2.08                   1.79   4.87   
    CV                      0.62                   1.19   0.97   
    Quarterly_Growth_Rate -48.00                  38.00  98.00   
    Active_Quarters         3.00                  14.00  16.00   
    
                           Wage and Employment Dynamics  Total  
    Q1 2021                                        2.00    2.0  
    Q2 2021                                        0.00   10.0  
    Q3 2021                                        1.00    1.0  
    Q4 2021                                        0.00    7.0  
    Q1 2022                                        1.00   10.0  
    Q2 2022                                        3.00   10.0  
    Q3 2022                                        1.00    4.0  
    Q4 2022                                        1.00    4.0  
    Q1 2023                                        2.00   13.0  
    Q2 2023                                        2.00    8.0  
    Q3 2023                                        3.00    9.0  
    Q4 2023                                        4.00   14.0  
    Q1 2024                                        2.00   11.0  
    Q2 2024                                        2.00   21.0  
    Q3 2024                                        2.00   26.0  
    Q4 2024                                        1.00   31.0  
    Q1 2025                                        4.00   37.0  
    Total                                         31.00  218.0  
    Mean                                           1.82   13.0  
    Std_Dev                                        1.19   10.0  
    CV                                             0.65    1.0  
    Quarterly_Growth_Rate                         33.00    0.0  
    Active_Quarters                               17.00   17.0  
    

### Figure 7: Summary results table for individual collections
This figure presents a comparative summary of individual ADR England flagship collections based on access volume and growth dynamics:
The summary table ranks collections by total requests, average quarterly activity, variation in demand (coefficient of variation), growth rate, and number of active quarters.
- LEO leads in total requests (80) and shows strong and consistent growth.
- ECHILD, although recently introduced, shows the highest average access per quarter (7.7) and the most rapid growth (+460%), though this may be artificially inflated due to the short baseline.
- GRADE and Wage and Employment Dynamics display more stable or declining trends.

| Collection                     | Total | Avg Requests per Active Quarter |   Coefficient of Variation  | Avg Quarterly Growth Rate (%)   | # Active Quarters |
|-------------------------------|--------|-------|-------|--------|----------|
| LEO                           | 80     | 5.0   | 0.97 | +98% | 16       |
| Data First                    | 49     | 3.1   | 1.13 | +95% | 16       |
| Wage and Employment Dynamics | 31     | 1.8   | 0.650 | +33% | 17       |
| ECHILD                        | 23     | 7.7   | 0.76 | +460%| 3        |
| Growing up in England         | 21     | 1.5   | 1.19 | +38% | 14       |
| GRADE                         | 10     | 3.3   | 0.62 | -48% | 3        |
| Agricultural Research Collection | 4  | 0.4   | 1.85 | +50% | 11       |

### Figure 8: Graphs showing total volume and average quarterly requests for each ADR England flagship dataset collection 
This dual horizontal bar chart compares access volume and intensity across individual ADR England flagship collections:
The left panel shows total requests per dataset.
- LEO is the most accessed dataset (80 requests), followed by Data First (49) and Wage and Employment Dynamics (31).
- ECHILD, despite being a newer entry, has already received 23 requests, surpassing some longer-established datasets.

The right panel presents average requests per quarter, a measure of sustained demand intensity.
- ECHILD leads with ~7.7 average requests per quarter, reflecting rapid uptake over a short period.
- LEO (5.0) and GRADE (3.3) also show strong quarterly engagement despite differences in total volume.


```python
data = {
    "Dataset": [
        "Agricultural Research Collection", "Data First", "ECHILD", "GRADE",
        "Growing up in England", "LEO", "Wage and Employment Dynamics", "Total"
    ],
    "Quarters": [
        11, 16, 3, 3,
        14, 16, 17, 19
    ],
    "Total Requests": [
        4, 49, 23, 10,
        21, 80, 31, 218
    ],
    "Avg per Quarter": [
        round(4 / 11, 2),    # 0.36
        round(49 / 16, 2),   # 3.06
        round(23 / 3, 2),    # 7.67
        round(10 / 3, 2),    # 3.33
        round(21 / 14, 2),   # 1.5
        round(80 / 16, 2),   # 5.0
        round(31 / 17, 2),   # 1.82
        round(218 / 19, 2)   # 11.47
    ]
}


# Create DataFrame and exclude "Total"
df_ADR_counts = pd.DataFrame(data)
df_ADR_counts = df_ADR_counts[df_ADR_counts["Dataset"] != "Total"]

# Sort by total requests descending
df_ADR_counts_sorted = df_ADR_counts.sort_values("Total Requests", ascending=False)

# Create side-by-side plots
fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)

# Total Requests plot (inverted y-axis to show most popular at top)
axes[0].barh(df_ADR_counts_sorted["Dataset"], df_ADR_counts_sorted["Total Requests"], color='steelblue')
axes[0].set_title("Total Requests per Dataset (until end Q1 2025)")
axes[0].set_xlabel("Total Requests")
axes[0].invert_yaxis()

# Avg per Quarter plot (matching y-axis order)
axes[1].barh(df_ADR_counts_sorted["Dataset"], df_ADR_counts_sorted["Avg per Quarter"], color='skyblue')
axes[1].set_title("Average Requests per Quarter")
axes[1].set_xlabel("Avg per Quarter")

plt.tight_layout()
plt.show()
```


    
![png](DEA_projects_analysis_files/DEA_projects_analysis_68_0.png)
    


### Figure 9: Quarterly trends for ADR England flagship datasets split by collection
This faceted line plot shows quarterly access patterns for each of the ADR England flagship datasets from Q1 2021 to Q1 2025. Each subplot represents a single dataset, with the vertical axis indicating the number of projects accessing that dataset per quarter:
- LEO and Data First exhibit sustained and growing usage, with LEO peaking in late 2024.
- ECHILD shows a steep rise following its recent introduction in Q3 2024, reflecting rapid uptake (though caution is advised interpreting long-term significance).
- GRADE and the Agricultural Research Collection show limited and irregular engagement, with GRADE use dropping after Q3 2024.
- Wage and Employment Dynamics and Growing up in England demonstrate modest but consistent interest over time.


```python
# Get unique collections and the full quarter range
collections = collection_quarter_counts['collection'].unique()
all_quarters = collection_quarter_counts['quarter_date'].unique()
all_quarter_labels = collection_quarter_counts.drop_duplicates('quarter_date')['Quarter Label'].tolist()
n_collections = len(collections)

# Create subplots
fig, axes = plt.subplots(nrows=4, ncols=2, figsize=(8, 16), sharey=True)
axes = axes.flatten()  # Make it easier to iterate

for i, collection in enumerate(collections):
    # Filter data for this collection
    collection_data = collection_quarter_counts[collection_quarter_counts['collection'] == collection].copy()
    
    # Find the first quarter where this collection had any activity (count > 0)
    first_active_quarter = collection_data[collection_data['count'] > 0]['quarter_date'].min()
    
    # If the collection has never been active, skip plotting
    if pd.isna(first_active_quarter):
        axes[i].set_title(f"{collection}\n(No activity)", fontsize=12, fontweight='bold', color='gray')
        axes[i].set_xlabel(None)
        axes[i].set_ylabel('Count' if i % 4 == 0 else '')
        continue
    
    # Filter to only include data from the first active quarter onwards
    filtered_data = collection_data[collection_data['quarter_date'] >= first_active_quarter]
    
    # Plot on the specific subplot
    sns.lineplot(
        data=filtered_data,
        x='quarter_date',
        y='count',
        marker='o',
        ax=axes[i],
        color='steelblue'
    )
    
    # Format the subplot
    axes[i].set_title(collection, fontsize=12, fontweight='bold')
    axes[i].set_xlabel(None)
    axes[i].set_ylabel('Count' if i % 4 == 0 else '')  # Only show y-label on leftmost plots
    axes[i].yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    
    # Set ALL quarters on x-axis (same scale for all subplots)
    step = max(1, len(all_quarters) // 8)  # Show every nth quarter to avoid crowding
    axes[i].set_xticks(all_quarters[::step])
    axes[i].set_xticklabels(all_quarter_labels[::step], rotation=45)
    
    # Set x-axis limits to full range for consistency across all subplots
    time_range = all_quarters[-1] - all_quarters[0]
    padding = time_range * 0.02  # 2% padding on each side
    axes[i].set_xlim(all_quarters[0] - padding, all_quarters[-1] + padding)
    
    # Add small padding to y-axis as well
    axes[i].margins(y=0.05)  # 5% padding on y-axis

# Hide any unused subplots
for i in range(n_collections, len(axes)):
    axes[i].set_visible(False)

plt.suptitle('ADR England Flagship collections accessed by quarter', fontsize=16, y=1.0)
plt.tight_layout()
plt.show()
```


    
![png](DEA_projects_analysis_files/DEA_projects_analysis_70_0.png)
    


# Part 2: How have research topics and priorities evolved over time?

## Analysis of all DEA approved projects


```python
# Simple count of word frequencies across all project titles
from collections import Counter
import re
import nltk
from nltk.corpus import stopwords

# stopwrods
nltk.download('stopwords')
stop_words = set(stopwords.words('english'))
custom_stopwords = stop_words.union({'uk', 'england', 'analysis', 'data', 'wales', 'northern', 'ireland', 'scotland', 'outcome', 'outcomes', 'effect', 'evaluation', 'impact',
                                     'understanding', 'research', 'study', 'project', 'use', 'used', 'useful', 'using', 'dataset', 'datasets', 'collection', 'effects'})

# Tokenize project titles
def tokenize(text):
    return re.sub(r'[^\w\s]', ' ', #remove punctuation/replace these with a space
                  text.lower()).split()

# Flatten all tokenized words from project titles
all_words = [word for title in df['Title'] for word in tokenize(title) if word not in custom_stopwords]

word_counts = Counter(all_words)

# Display top 20 word counts
print("Most common words in project titles:")
print(word_counts.most_common(20))
```

    Most common words in project titles:
    [('labour', 85), ('health', 75), ('market', 74), ('education', 68), ('social', 60), ('covid', 55), ('productivity', 53), ('19', 53), ('economic', 52), ('employment', 44), ('local', 41), ('business', 39), ('innovation', 39), ('level', 38), ('children', 38), ('firm', 36), ('inequalities', 36), ('mobility', 36), ('firms', 32), ('evidence', 31)]
    

    [nltk_data] Downloading package stopwords to
    [nltk_data]     C:\Users\balin\AppData\Roaming\nltk_data...
    [nltk_data]   Package stopwords is already up-to-date!
    


```python
# Cluster analysis
# pre-process the project titles
def preprocess_text(text):
    # Remove punctuation and convert to lowercase
    text = re.sub(r'[^\w\s]', '', text)
    text = text.lower()
    #remove stopwords
    text = ' '.join([word for word in text.split() if word not in custom_stopwords])
    return text
# Apply the preprocessing function to the project titles
df['processed_titles'] = df['Title'].apply(preprocess_text)

# Create a list of all project titles
project_titles = df['processed_titles'].tolist()
```


```python
# Vectorise with TF-IDF
from sklearn.feature_extraction.text import TfidfVectorizer
vectorizer = TfidfVectorizer(stop_words=list(custom_stopwords))

# Fit the vectorizer on your processed titles and transform to TF-IDF matrix
X = vectorizer.fit_transform(project_titles)
```


```python
#from sklearn.cluster import KMeans
# Try a range of cluster counts
inertia = []
K_range = range(2, 21)  # Try from 2 to 20 clusters

for k in K_range:
    km = KMeans(n_clusters=k, random_state=42)
    km.fit(X)
    inertia.append(km.inertia_)  # Inertia = sum of squared distances to nearest centroid

# Plot the inertia values to find the "elbow"
#plt.figure(figsize=(8, 5))
#plt.plot(K_range, inertia, marker='o')
#plt.xlabel('Number of clusters (k)')
#plt.ylabel('Inertia')
#plt.title('Elbow Method for Optimal k')
#plt.grid(True)
#plt.show()
```


```python
# Cluster with KMeans
from sklearn.cluster import KMeans

n_clusters = 4
kmeans = KMeans(n_clusters=n_clusters, random_state=42) # n_clusters as determined from elbow method
kmeans.fit(X)

labels = kmeans.labels_

# generarte dataframe with keywords and their cluster labels
clustered = pd.DataFrame({
    'title': project_titles,
    'cluster': labels
})
```

### Figure 10: Thematic clusters of DEA research project titles
This figure presents word clouds for four thematic clusters (Cluster 0, 1, and 2, 3) identified through KMeans clustering of TF-IDF vectorized project titles. Each cluster groups titles with similar keyword patterns. Word size reflects each term’s importance within the cluster, as measured by TF-IDF — capturing both frequency and uniqueness.


```python
#visualise with wordcloud
from wordcloud import WordCloud

for i in range(n_clusters):
    text = ' '.join(clustered[clustered['cluster'] == i]['title'])
    wc = WordCloud(width=800, height=400, background_color='white').generate(text)
    
    plt.figure()
    plt.imshow(wc, interpolation='bilinear')
    plt.axis('off')
    plt.title(f"Title Cluster {i}")
    plt.show()
```


    
![png](DEA_projects_analysis_files/DEA_projects_analysis_79_0.png)
    



    
![png](DEA_projects_analysis_files/DEA_projects_analysis_79_1.png)
    



    
![png](DEA_projects_analysis_files/DEA_projects_analysis_79_2.png)
    



    
![png](DEA_projects_analysis_files/DEA_projects_analysis_79_3.png)
    


- Distinctive research terms across all DEA accredited project titles over the past 6 years can be split very broadly into four clusters:
    - Cluster 1: project titles on business, growth, and productivity; 
    - Cluster 2: gender and ethnic inequalities and gaps, 
    - Cluster 3: includes terms on health, social and children;
    - Cluster 4: labour market, skills and education terms.

### Figure 11: Individual term trends for top 10 terms by year
Graphs track annual TF-IDF scores for ten most prominent research terms: labour, market, education, health, productivity, social, employment, covid19, economic, business; in project titles from the public register between 2020 and 2024. TF-IDF (Term Frequency–Inverse Document Frequency) reflects how important a term is in a specific year relative to other years, highlighting changes in salience over time. An upward trend indicates growing distinctiveness or emphasis of a term in that year's projects, while a decline suggests decreasing thematic prominence. Each panel shows the term’s yearly score, helping identify evolving research interests within the DEA-accredited landscape


```python
# Function to calculate TF-IDF scores for a set of documents
def top_tfidf_dict(docs, n=20):
    """Calculate top n TF-IDF terms for a collection of documents"""
    vectorizer = TfidfVectorizer(stop_words=list(custom_stopwords))
    X = vectorizer.fit_transform(docs)
    scores = X.sum(axis=0).A1
    terms = vectorizer.get_feature_names_out()
    sorted_terms = sorted(zip(terms, scores), key=lambda x: x[1], reverse=True)
    return dict(sorted_terms[:n])

# Filter data - exclude 2019, include 2020-2024 (excluding 2025)
df_filtered = df[(df['Accreditation Date Year'] >= 2020) & (df['Accreditation Date Year'] < 2025)]

# Calculate documents per year
docs_per_year = df_filtered['Accreditation Date Year'].value_counts().to_dict()

# Print number of documents per year
print("\nDocuments per year (2020-2024):")
for year in sorted(docs_per_year.keys()):
    print(f"{year}: {docs_per_year[year]} projects")

# Calculate TF-IDF scores by year
tfidf_dict_by_year = {}
for year, group in df_filtered.groupby('Accreditation Date Year'):
    tfidf_dict_by_year[year] = top_tfidf_dict(group['processed_titles'])
    print(f"\nTop 10 terms for {year}:")
    top_terms = list(tfidf_dict_by_year[year].items())[:10]
    for term, score in top_terms:
        print(f"  {term}: {score:.3f}")

# Get all unique terms across all years
all_terms = set()
for year_dict in tfidf_dict_by_year.values():
    all_terms.update(year_dict.keys())

# Find top 10 terms by total TF-IDF score across all years
term_totals = {}
for term in all_terms:
    total = sum(year_dict.get(term, 0) for year_dict in tfidf_dict_by_year.values())
    term_totals[term] = total

top_10_terms = sorted(term_totals.items(), key=lambda x: x[1], reverse=True)[:10]
top_10_term_names = [term for term, _ in top_10_terms]

print("\nTop 10 terms across all years (2020-2025):")
for term, total in top_10_terms:
    print(f"  {term}: {total:.3f}")

# Create DataFrame for plotting
years = sorted(tfidf_dict_by_year.keys())
data_for_plot = []
for term in top_10_term_names:
    for year in years:
        score = tfidf_dict_by_year[year].get(term, 0)
        data_for_plot.append({
            'Year': year,
            'Term': term,
            'TF-IDF Score': score
        })

plot_df = pd.DataFrame(data_for_plot)
```

    
    Documents per year (2020-2024):
    2020: 116 projects
    2021: 156 projects
    2022: 197 projects
    2023: 211 projects
    2024: 224 projects
    
    Top 10 terms for 2020:
      covid19: 4.024
      business: 3.509
      firm: 3.166
      inequalities: 3.051
      local: 2.942
      social: 2.890
      labour: 2.860
      market: 2.655
      evidence: 2.509
      productivity: 2.470
    
    Top 10 terms for 2021:
      covid19: 5.533
      social: 4.527
      productivity: 3.727
      labour: 3.326
      wellbeing: 3.309
      market: 2.925
      economic: 2.921
      employment: 2.773
      inequalities: 2.720
      gap: 2.634
    
    Top 10 terms for 2022:
      education: 4.419
      business: 4.387
      productivity: 3.719
      labour: 3.511
      covid19: 3.388
      market: 3.268
      firms: 3.259
      local: 3.211
      trade: 3.199
      crime: 3.089
    
    Top 10 terms for 2023:
      market: 6.504
      labour: 6.255
      productivity: 5.378
      innovation: 4.389
      education: 4.319
      health: 4.273
      social: 3.670
      economic: 3.638
      wellbeing: 3.611
      business: 3.174
    
    Top 10 terms for 2024:
      labour: 6.209
      market: 6.123
      education: 5.777
      health: 5.268
      employment: 4.059
      mobility: 4.059
      social: 3.795
      university: 3.542
      economic: 3.351
      role: 3.235
    
    Top 10 terms across all years (2020-2025):
      labour: 22.161
      market: 21.476
      education: 18.076
      health: 16.377
      productivity: 15.293
      social: 14.882
      employment: 14.355
      covid19: 12.945
      economic: 12.384
      business: 11.070
    


```python
# Set up color palette
colors = sns.color_palette("husl", 10)

# Create individual subplots for each term
fig, axes = plt.subplots(5, 2, figsize=(16, 20))
axes = axes.flatten()

for i, term in enumerate(top_10_term_names):
    ax = axes[i]
    term_data = plot_df[plot_df['Term'] == term]
    
    ax.plot(term_data['Year'], term_data['TF-IDF Score'], 
            marker='o', linewidth=3, markersize=10,
            color=colors[i])
    
    # Fill area under the line
    ax.fill_between(term_data['Year'], term_data['TF-IDF Score'], 
                    alpha=0.3, color=colors[i])
    
    # Add value labels
    for x, y in zip(term_data['Year'], term_data['TF-IDF Score']):
        if y > 0:
            ax.annotate(f'{y:.2f}', (x, y), 
                       textcoords="offset points", xytext=(0,5), 
                       ha='center', fontsize=10)
    
    ax.set_title(f'"{term}"', fontsize=14, fontweight='bold')
    ax.set_xlabel('Year', fontsize=12)
    ax.set_ylabel('TF-IDF Score', fontsize=12)
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Set y-axis to start at 0
    ax.set_ylim(bottom=0)
    
    # Set x-axis to show all years
    ax.set_xticks(years)

# Add main title with extra padding
fig.suptitle('Individual Term Trends: TF-IDF Scores for Top 10 Terms by Year (2020-2024)', 
             fontsize=18, fontweight='bold', y=0.98)

# Adjust layout with extra top padding
plt.tight_layout(rect=[0, 0.02, 1, 0.96])
plt.show()


```


    
![png](DEA_projects_analysis_files/DEA_projects_analysis_83_0.png)
    


### Figure 12: Annual shifts in research emphasis (2020–2024): TF-IDF heatmap of top 10 terms in DEA project titles
This heatmap visualises annual TF-IDF scores for the top 10 research terms found in project titles between 2020 and 2024. Each cell shows the TF-IDF score of a term in a given year, with warmer colors (orange to deep red) indicating higher relative importance of the term in that year’s corpus of titles. For example, covid19 peaked in importance in 2021 before disappearing in later years, while terms like education and labour grew more prominent over time. The color gradient helps highlight shifts in thematic focus across DEA-accredited research.


```python
# Additional analysis: Create a heatmap of term scores by year
plt.figure(figsize=(12, 8))

# Create matrix for heatmap
heatmap_data = []
for term in top_10_term_names:
    row = []
    for year in years:
        score = tfidf_dict_by_year[year].get(term, 0)
        row.append(score)
    heatmap_data.append(row)

# Create heatmap
sns.heatmap(heatmap_data, 
            xticklabels=years, 
            yticklabels=top_10_term_names,
            cmap='YlOrRd',
            annot=True,
            fmt='.2f',
            cbar_kws={'label': 'TF-IDF Score'})

plt.title('TF-IDF Score Heatmap: Top 10 Terms by Year', fontsize=16, fontweight='bold')
plt.xlabel('Year', fontsize=12)
plt.ylabel('Terms', fontsize=12)
plt.tight_layout()
plt.show()
```


    
![png](DEA_projects_analysis_files/DEA_projects_analysis_85_0.png)
    


- Some terms like 'labour', 'market', 'employment' and 'productivity' reasonably consistent over time
- Others like 'health' and 'education' steadily growing (presumably tracking growth in datasets containing information in these domains accessible through the DEA)
- The term 'covid19' rose and fell rapidly in project titles over the course of the observed time period


```python
# Word frequency analysis instead of TF-IDF
def top_frequency_dict(docs, n=20):
    """Count word frequencies across all documents"""
    # Combine all documents into one text
    all_text = ' '.join(docs)
    
    # Split into words and count frequencies
    words = all_text.split()
    word_counts = Counter(words)
    
    # Remove custom stopwords
    filtered_counts = {word: count for word, count in word_counts.items() 
                      if word not in custom_stopwords}
    
    # Get top n terms
    top_terms = dict(word_counts.most_common(n))
    return top_terms

def calculate_word_percentages(docs, target_words):
    """Calculate what percentage of documents contain specific target words"""
    total_docs = len(docs)
    word_percentages = {}
    
    for word in target_words:
        # Count documents containing this word
        count = sum(1 for doc in docs if word in doc.lower())
        percentage = (count / total_docs) * 100
        word_percentages[word] = {
            'count': count,
            'total_docs': total_docs,
            'percentage': percentage
        }
    
    return word_percentages

# Filter data - exclude 2019 and 2025, include 2020-2024
df_filtered = df[(df['Accreditation Date Year'] >= 2020) & (df['Accreditation Date Year'] < 2025)]

# Calculate frequency dictionaries by year
freq_dict_by_year = {}
docs_per_year = {}

for year, group in df_filtered.groupby('Accreditation Date Year'):
    freq_dict_by_year[year] = top_frequency_dict(group['processed_titles'])
    docs_per_year[year] = len(group)

# Print number of documents per year
print("Documents per year:")
for year in sorted(docs_per_year.keys()):
    print(f"{year}: {docs_per_year[year]} projects")

# Get all unique terms across all years
all_terms = set()
for year_dict in freq_dict_by_year.values():
    all_terms.update(year_dict.keys())

# Find top 10 terms by total frequency across all years
term_totals = {}
for term in all_terms:
    total = sum(year_dict.get(term, 0) for year_dict in freq_dict_by_year.values())
    term_totals[term] = total

top_10_terms = sorted(term_totals.items(), key=lambda x: x[1], reverse=True)[:10]
top_10_term_names = [term for term, _ in top_10_terms]

print(f"\nTop 10 most frequent terms across all years:")
for term, count in top_10_terms:
    print(f"{term}: {count} total occurrences")

# Create DataFrame for plotting (absolute frequencies)
years = sorted(freq_dict_by_year.keys())
data_for_plot = []

for term in top_10_term_names:
    for year in years:
        count = freq_dict_by_year[year].get(term, 0)
        data_for_plot.append({
            'Year': year,
            'Term': term,
            'Frequency': count
        })

plot_df = pd.DataFrame(data_for_plot)

# Create DataFrame for plotting (percentage of projects)
percentage_data = []
for term in top_10_term_names:
    for year in years:
        year_group = df_filtered[df_filtered['Accreditation Date Year'] == year]
        total_projects = len(year_group)
        projects_with_term = sum(1 for title in year_group['processed_titles'] if term in title)
        percentage = (projects_with_term / total_projects) * 100 if total_projects > 0 else 0
        
        percentage_data.append({
            'Year': year,
            'Term': term,
            'Percentage': percentage,
            'Count': projects_with_term,
            'Total_Projects': total_projects
        })

percentage_df = pd.DataFrame(percentage_data)

# Special analysis for COVID-19 terms
covid_terms = ['covid', 'covid19', 'coronavirus', 'pandemic']
print(f"\n=== COVID-19 RESEARCH ANALYSIS ===")

covid_analysis = {}
for year in years:
    year_group = df_filtered[df_filtered['Accreditation Date Year'] == year]
    total_projects = len(year_group)
    
    # Count projects with any COVID-related term
    covid_projects = 0
    for title in year_group['processed_titles']:
        if any(covid_term in title.lower() for covid_term in covid_terms):
            covid_projects += 1
    
    covid_percentage = (covid_projects / total_projects) * 100 if total_projects > 0 else 0
    covid_analysis[year] = {
        'covid_projects': covid_projects,
        'total_projects': total_projects,
        'percentage': covid_percentage
    }
    
    print(f"{year}: {covid_projects}/{total_projects} projects ({covid_percentage:.1f}%) mentioned COVID-related terms")

# Find peak and current COVID research levels
covid_percentages = [data['percentage'] for data in covid_analysis.values()]
peak_covid_year = max(covid_analysis.keys(), key=lambda year: covid_analysis[year]['percentage'])
current_covid_percentage = covid_analysis[2024]['percentage']  # 2024 is most recent year
peak_covid_percentage = covid_analysis[peak_covid_year]['percentage']

print(f"\nCOVID Research Peak: {peak_covid_percentage:.1f}% in {peak_covid_year}")
print(f"COVID Research in 2024: {current_covid_percentage:.1f}%")
print(f"Decline: {peak_covid_percentage - current_covid_percentage:.1f} percentage points")

```

    Documents per year:
    2020: 116 projects
    2021: 156 projects
    2022: 197 projects
    2023: 211 projects
    2024: 224 projects
    
    Top 10 most frequent terms across all years:
    labour: 72 total occurrences
    market: 68 total occurrences
    health: 57 total occurrences
    social: 56 total occurrences
    education: 54 total occurrences
    covid19: 46 total occurrences
    productivity: 42 total occurrences
    economic: 36 total occurrences
    employment: 32 total occurrences
    business: 30 total occurrences
    
    === COVID-19 RESEARCH ANALYSIS ===
    2020: 16/116 projects (13.8%) mentioned COVID-related terms
    2021: 26/156 projects (16.7%) mentioned COVID-related terms
    2022: 14/197 projects (7.1%) mentioned COVID-related terms
    2023: 3/211 projects (1.4%) mentioned COVID-related terms
    2024: 6/224 projects (2.7%) mentioned COVID-related terms
    
    COVID Research Peak: 16.7% in 2021
    COVID Research in 2024: 2.7%
    Decline: 14.0 percentage points
    

### Figure 13: Term usage trends in DEA Projects: Percentage of project titles mentioning top 10 terms
This figure shows the proportion of DEA-accredited research projects each year (2020–2024) that mention selected key terms in their titles. Each subplot tracks a different term from the top 10 most frequent across the dataset, highlighting the share of projects in which that term appears. Unlike TF-IDF, this metric reflects raw occurrence rates (% of total projects) and provides a straightforward view of term popularity over time. For example, covid19 peaked in 2021 and declined thereafter, while education and health steadily gained prominence. This helps communicate a more-easily understandable metric than TF-IDF scores.


```python
# Plotting
colors = sns.color_palette("husl", 10)

# Create individual subplots for each term (showing percentages)
fig, axes = plt.subplots(5, 2, figsize=(16, 20))
axes = axes.flatten()

for i, term in enumerate(top_10_term_names):
    ax = axes[i]
    term_data = percentage_df[percentage_df['Term'] == term]
    
    ax.plot(term_data['Year'], term_data['Percentage'],
            marker='o', linewidth=3, markersize=10,
            color=colors[i])
    
    # Fill area under the line
    ax.fill_between(term_data['Year'], term_data['Percentage'],
                    alpha=0.3, color=colors[i])
    
    # Add value labels
    for x, y in zip(term_data['Year'], term_data['Percentage']):
        if y > 0:
            ax.annotate(f'{y:.1f}%', (x, y),
                       textcoords="offset points", xytext=(0,5),
                       ha='center', fontsize=10)
    
    ax.set_title(f'"{term}"', fontsize=14, fontweight='bold')
    ax.set_xlabel('Year', fontsize=12)
    ax.set_ylabel('% of Projects', fontsize=12)
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Set y-axis to start at 0
    ax.set_ylim(bottom=0)
    
    # Set x-axis to show all years
    ax.set_xticks(years)
    ax.set_xticklabels(years)

# Add main title with extra padding
fig.suptitle('Individual Term Trends: Percentage of Projects Mentioning Top 10 Terms by Year (2020-2024)',
             fontsize=18, fontweight='bold', y=0.98)

# Adjust layout with extra top padding
plt.tight_layout(rect=[0, 0.02, 1, 0.96])
plt.show()

# Create a summary table for easy reference
print(f"\n=== SUMMARY TABLE: TERM USAGE BY YEAR ===")
summary_table = percentage_df.pivot(index='Term', columns='Year', values='Percentage').round(1)
print(summary_table)
```


    
![png](DEA_projects_analysis_files/DEA_projects_analysis_89_0.png)
    


    
    === SUMMARY TABLE: TERM USAGE BY YEAR ===
    Year          2020  2021  2022  2023  2024
    Term                                      
    business      11.2   2.6   5.6   6.2   2.7
    covid19       12.1  13.5   5.1   1.4   2.7
    economic       5.2   7.7   5.1   8.1   5.8
    education      3.4   5.1   6.6   9.0  12.5
    employment     4.3   5.1   4.6   2.8   5.4
    health         5.2   3.8   4.6   6.6   9.4
    labour         6.9   7.7   5.1  10.4   8.5
    market         7.8   6.4   5.1  10.9   9.4
    productivity   5.2   7.1   5.6   6.6   1.3
    social         7.8   9.6   5.1   6.2   5.4
    

# Future possible directions

## Part 1: Dataset access trends
**Methodological improvements**:
- Fit a more complex model for growth in the use of different linked datasets to improve forecasts on future demand for flagship datasets and support better capacity planning 
    - Add significance test for growth trends
    - Cross-dataset synergies (network analysis of dataset combinations)
- Analyse growth in projects using ADR England flagship datasets rather than simply number of requests for flagship datasets within those projects (there will always be slightly fewer projects than access requests because a single project will soemtimes request more than one flagship dataset, and capacity pressure for approvals and secure environment usage arises from projects, rather than datasets)
- Incorporate flagship datasets from ADR UK partners in the devolved administrations
- Incorporate the popular MoJ-DfE linkage dataset into the Data First collection counts

**Additional questions**:
- Look at flagship dataset investment level to better understand the value for money in supporting different linkages in terms of their demand
- Develop the impact measurement with the addition of known research outputs (publications, policy briefs etc.) linked to approved project data
- User segmentation: what kind of research organisations (universities, government, third sector) are using these data? Understanding institutional patterns could inform targeted outreach and capacity building efforts
- Are there centres of research activity using particular datasets hat could serve as hubs for training and best practice sharing?

**Other potential developments**:
- Improve the transparency and accessibility of the public register, providing a fully searchable and filterable web-based dataset for the public to better understand the research that is being undertaken using their data
- Produce a web-based dashboard live-fed with data from the register to allow for automatically updated and easy-to-interpret visualisations of dataset use and research themes
- Develop public engagement tools that allow individuals to understand how their data contributes to research (noting that direct personal data matching would require careful consideration of privacy and security implications)

## Part 2: Topic trends in research
**Methodological improvements**:
- N-gram analysis to find commonly co-occurring terms for a richer thematic analysis
- Clustering analysis using advanced computational approaches (such as density-based spatial clustering) to improve cluster separation and identify research themes more precisely
- Dynamic topic modelling using established frameworks for more detailed analysis of how research themes evolve over time

**Additional questions**:
- How do topic trends align with stated government priorities and policy agendas? This analysis could help identify research gaps or areas where policy interest exceeds current research activity
- What factors drive the emergence of new research themes, and how quickly does the research ecosystem respond to policy priorities?

**Other potential developments**:
- Produce a recommendation system for researchers, suggesting relevant datasets based on their research questions and helping to optimise dataset use across the research community

# Some limitations in this work
## Data collection and coverage limitations
- The public register only begins in Q4 2019, so early DEA usage and adoption trends since 2017 are not captured
- The public register only includes approved projects. We have no visibility into rejected applications, abandoned projects, or researchers discouraged by perceived barriers who never apply
- The focus on ADR England flagship datasets excludes those from Scotland, Wales, and Northern Ireland, limiting UK-wide insights
- The MoJ-DfE linked dataset is omitted from Data First collection counts as it is not accessed via the DEA, potentially understating demand for justice-education data
- Web scraping introduces risks of missed entries or parsing errors due to formatting changes which are not always easy to detect

## Technical and methodological constraints
- Growth projection assumptions: exponential forecasts assume continued trends, but may become limited by other factors (funding, researcher capacity, processing delays, policy shifts, or demand saturation)
- Title-based topic analysis limitations: project titles may misrepresent research content, leading to misclassification, especially for generic or interdisciplinary studies
- Classification subjectivity: dataset grouping and thematic clustering involved subjective choices that may influence interpretation of trends
- Simple modeling approach: exponential models do not account for seasonality, structural breaks, capacity limits, or network effects across datasets
- TF-IDF limitations: Lacks ability to detect semantic similarity or shifts in term meaning over time; more advanced NLP methods could yield different insights

These limitations suggest findings should be treated as indicative rather than definitive. The dramatic growth rates observed may not be sustainable, and infrastructure planning should incorporate uncertainty ranges and scenario planning. Future work should address these limitations.


```python
from datetime import datetime
import nbformat
import os


# Load the notebook
input_path = r"C:\Users\balin\Desktop\ADR_DEA_project\analysis\DEA_projects_analysis.ipynb"
nb = nbformat.read(input_path, as_version=4)

# Keep only matplotlib/seaborn outputs (image/png)
for cell in nb.cells:
    if cell.cell_type == "code" and "outputs" in cell:
        cell["outputs"] = [
            output for output in cell["outputs"]
            if "data" in output and "image/png" in output["data"]
        ]

# Save cleaned notebook with today's date
today_str = datetime.now().strftime("%Y%m%d")
output_path = fr"C:\Users\balin\Desktop\ADR_DEA_project\analysis\DEA_projects_analysis_figures_only_{today_str}.ipynb"

with open(output_path, "w", encoding="utf-8") as f:
    nbformat.write(nb, f)

# Convert to HTML
!jupyter nbconvert --to html --no-input "{output_path}"
```

    [NbConvertApp] Converting notebook C:\Users\balin\Desktop\ADR_DEA_project\analysis\DEA_projects_analysis_figures_only_20250528.ipynb to html
    [NbConvertApp] WARNING | Alternative text is missing on 12 image(s).
    [NbConvertApp] Writing 2297552 bytes to C:\Users\balin\Desktop\ADR_DEA_project\analysis\DEA_projects_analysis_figures_only_20250528.html
    
