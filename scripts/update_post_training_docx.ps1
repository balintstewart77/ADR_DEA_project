param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$RenderRoot = "C:\tmp\adr_dea_docx_render_20260717"
)

$ErrorActionPreference = "Stop"
# HISTORICAL REPRODUCTION ONLY: this script created the superseded v0.10 and
# candidate-0.4 materials. It is not the v0.11 implementation or finalisation path.
$word = $null
$report = @()

function Text-Of {
    param($Range)
    return $Range.Text.Trim([char[]]@([char]13, [char]7))
}

function Set-ExactParagraph {
    param($Document, [string]$OldText, [string]$NewText, [int]$Expected = 1)
    $found = 0
    for ($index = 1; $index -le $Document.Paragraphs.Count; $index++) {
        $paragraph = $Document.Paragraphs.Item($index)
        if ((Text-Of $paragraph.Range) -eq $OldText) {
            try {
                $paragraph.Range.Text = $NewText + [char]13
            }
            catch {
                throw "Cannot replace protected paragraph: $OldText. $($_.Exception.Message)"
            }
            $found++
        }
    }
    if ($found -ne $Expected) {
        throw "Expected $Expected paragraph match(es), found $found for: $OldText"
    }
}

function Replace-AllText {
    param($Document, [string]$OldText, [string]$NewText, [int]$Minimum = 1)
    $count = 0
    $searchStart = 0
    while ($searchStart -lt $Document.Content.End) {
        $range = $Document.Range($searchStart, $Document.Content.End)
        $find = $range.Find
        $find.ClearFormatting()
        $find.Text = $OldText
        $find.Forward = $true
        $find.Wrap = 0
        $find.Format = $false
        $find.MatchCase = $true
        $find.MatchWholeWord = $false
        $find.MatchWildcards = $false
        if (-not $find.Execute()) {
            break
        }
        $range.Text = $NewText
        $searchStart = $range.End
        $count++
    }
    if ($count -lt $Minimum) {
        throw "Expected at least $Minimum text replacement(s), found $count for: $OldText"
    }
}

function Add-VersionNote {
    param($Document, [string]$Text)
    $range = $Document.Paragraphs.Item(1).Range.Duplicate
    $range.Collapse(0)
    $range.InsertAfter($Text + [char]13)
}

function Set-CellText {
    param($Document, [int]$Table, [int]$Row, [int]$Column, [string]$Text)
    $range = $Document.Tables.Item($Table).Rows.Item($Row).Cells.Item($Column).Range
    $range.End = $range.End - 1
    $range.Text = $Text
}

function New-VersionedDocument {
    param(
        [string]$SourceRelative,
        [string]$TargetRelative,
        [scriptblock]$Editor
    )
    $source = Join-Path $RepositoryRoot $SourceRelative
    $target = Join-Path $RepositoryRoot $TargetRelative
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Source DOCX not found: $source"
    }
    if (Test-Path -LiteralPath $target) {
        throw "Refusing to overwrite existing versioned DOCX: $target"
    }
    $sourceDocument = $word.Documents.Open($source, $false, $true, $false)
    $sourceDocument.SaveAs2($target, 16)
    $sourceDocument.Close(0)
    $document = $word.Documents.Open($target, $false, $false, $false)
    if ($document.ProtectionType -ne -1) {
        $document.Unprotect()
    }
    for ($controlIndex = $document.ContentControls.Count; $controlIndex -ge 1; $controlIndex--) {
        $control = $document.ContentControls.Item($controlIndex)
        $control.LockContents = $false
        $control.LockContentControl = $false
    }
    & $Editor $document
    $document.Fields.Update() | Out-Null
    $document.Repaginate()
    $document.Save()
    $pages = $document.ComputeStatistics(2)
    $pdf = Join-Path $RenderRoot ((Split-Path -LeafBase $target) + ".pdf")
    $document.ExportAsFixedFormat($pdf, 17)
    $script:report += [pscustomobject]@{
        docx = $TargetRelative
        pages = $pages
        rendered_pdf = $pdf
    }
    $document.Close(0)
}

New-Item -ItemType Directory -Force -Path $RenderRoot | Out-Null

try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0

    New-VersionedDocument "preregistration\package\00_protocol\Validation_Protocol_PreReg_v0.9.docx" "preregistration\package\00_protocol\Validation_Protocol_PreReg_v0.10.docx" {
        param($doc)
        Add-VersionNote $doc "Draft 0.10 — post-training preregistration candidate — 17 July 2026"
        Set-ExactParagraph $doc "The pilot is not a test of coder accuracy. It tests the instrument, taxonomy rules, conditional fields, sufficiency and confidence judgements, and note prompts. The 10 pilot records are included in the 22-record exclusion set and do not enter formal validation, hard-case analysis, project-owner review, or reserve samples. Post-pilot changes are logged; substantive changes require a protocol amendment and refreezing before formal sampling or coding." "The pilot is not a test of coder accuracy. It tests the instrument, taxonomy rules, conditional fields, sufficiency and confidence judgements, and note prompts. The 10 pilot records are included in the 22-record exclusion set and do not enter formal validation, hard-case analysis, project-owner review, or reserve samples. The pilot was launched under redcap-candidate-0.3. The two post-training diagnostic-instrument changes recorded on 17 July 2026 were made before formal validation coding and before preregistration submission, so they are incorporated directly into this unregistered protocol candidate rather than documented as an amendment. Candidate 0.4 is used for formal coding only after all candidate-0.3 pilot responses are complete, exported and archived and candidate-0.4 repository validation and live runtime QA have passed."
        Set-ExactParagraph $doc "The scratch-coder and project-owner instruments will be implemented as separate instruments within one REDCap project. Each assignment of a reviewer to a register record will form one REDCap record and export row with frozen public-register fields pre-populated. Pilot assignments use the same scratch-coder fields as formal validation but are marked administratively and excluded from analysis." "The scratch-coder and project-owner instruments will be implemented as separate instruments within one REDCap project. Each reviewer-record assignment forms one REDCap record and export row with frozen public-register fields pre-populated. The excluded pilot used redcap-candidate-0.3. Formal coding uses the post-training redcap-candidate-0.4 scratch fields; instrument_ver identifies the applicable schema, and pilot assignments and responses remain unchanged under candidate 0.3."
        Set-ExactParagraph $doc "The versioned REDCap data dictionary archived with the registration specifies field definitions, option coding, branching logic, required-field rules, and hidden administrative variables. The instrument version used for formal collection will be frozen before coding, and later changes will be recorded in the instrument-change log." "The versioned REDCap data dictionary archived with the registration specifies field definitions, option coding, branching logic, required-field rules, hidden administrative variables, and the candidate-0.3 historical response mapping. Redcap-candidate-0.4 will be frozen for formal collection only after repository validation and live runtime QA. Later changes will be recorded in the instrument-change log."
        Set-ExactParagraph $doc "Scratch coders record Research Domains, one or two Analytical Purposes, both cross-cutting tags, public-register sufficiency, taxonomy fit and issue type, classification confidence, and a conditional explanatory note. Options are generated from the frozen taxonomy rather than hand-entered." "Scratch coders record Research Domains, one or two Analytical Purposes, both cross-cutting tags, public-register sufficiency, taxonomy fit and issue type, classification confidence, and a conditional explanatory note. Scratch taxonomy fit is coded Fit, Partial Fit, No Fit, or Cannot assess from register entry. Fit means the available categories adequately express the project. Partial Fit and No Fit require that the project is sufficiently understood: Partial Fit means that the taxonomy only approximates the project or fails to represent an important aspect cleanly, while No Fit means that the taxonomy cannot adequately express it. Cannot assess means that the visible title and dataset field are too thin to judge taxonomy fit. It is available only in the scratch-coder register-only stream, is not a taxonomy defect, does not trigger taxonomy-issue type, and is expected primarily with Partial or Insufficient register sufficiency. Partial or Insufficient sufficiency does not require Cannot assess where fit can still be judged."
        Set-ExactParagraph $doc "Within each classification dimension, Unclear from Register Entry is mutually exclusive with substantive labels. Notes are required where confidence is low, register sufficiency is partial or insufficient, taxonomy fit is partial or absent, or the response pattern would otherwise appear incoherent. Potentially contradictory responses are queried once before analysis lock where feasible." "Within each classification dimension, Unclear from Register Entry is mutually exclusive with substantive labels. Taxonomy issue is shown and required only for Partial Fit or No Fit and permits one or more of: Missing or inadequately represented category; Ambiguous or overlapping category boundaries; Other taxonomy problem. Other taxonomy problem requires an explanatory note. The issue field is hidden for Fit and Cannot assess. Notes are required where confidence is low, register sufficiency is Partial or Insufficient, taxonomy fit is Partial or No Fit, Other taxonomy problem is selected, or the response pattern would otherwise appear incoherent. Potentially contradictory responses are queried once before analysis lock where feasible."
        Set-ExactParagraph $doc "Owners record Fits, Does not fit, or Unsure for each proposed domain, purpose, and tag, with an explanation required for disagreement or uncertainty. They may select missing domains, purposes, or tags; assess public-entry sufficiency; and report taxonomy-fit problems. The instrument distinguishes actual-project fit from whether the public entry visibly supports the label. Detailed field structure and branching are specified in the archived REDCap dictionary." "Owners record Fits, Does not fit, or Unsure for each proposed domain, purpose, and tag, with an explanation required for disagreement or uncertainty. They may select missing domains, purposes, or tags; assess public-entry sufficiency; and report taxonomy-fit problems. po_sufficiency assesses the public entry, whereas po_taxonomy_fit assesses actual-project taxonomy fit using owner knowledge and remains Fit, Partial Fit, or No Fit. Cannot assess from register entry is not added to the owner fit field. Owner taxonomy issues use the same retained codes 1, 2 and 5 as candidate 0.4. Detailed field structure and branching are specified in the archived REDCap dictionary."
        Set-ExactParagraph $doc "Taxonomy fit: individual and record-level majority ratings of Fit, Partial fit, and No fit; structured taxonomy-issue frequencies." "Taxonomy fit: individual and record-level majority ratings of Fit, Partial Fit, No Fit, and Cannot assess from register entry. Where useful, an assessable-fit distribution will be reported after restricting to Fit, Partial Fit and No Fit. Cannot assess will be reported alongside register-sufficiency diagnostics; it will not be counted as No Fit, as a taxonomy defect, or in the denominator for taxonomy-issue frequencies. Taxonomy-issue frequencies will be reported only among cases with Partial Fit or No Fit."
        Set-ExactParagraph $doc "4. Taxonomy problem: a missing category, overlapping categories, unclear boundary, or a label that is too broad or too narrow." "4. Taxonomy problem: a missing or inadequately represented category, ambiguous or overlapping category boundaries, or another taxonomy problem. Cannot assess from register entry is an evidence limitation and is not assigned this code."
        Set-ExactParagraph $doc "4. Scratch-coder, owner, or adjudication evidence identifies the same missing, overlapping, too broad, or too narrow taxonomy issue from more than one independent source." "4. Scratch-coder, owner, or adjudication evidence identifies the same missing or inadequately represented category, ambiguous or overlapping boundary, or other taxonomy problem from more than one independent source."
        Set-ExactParagraph $doc "Revise taxonomy and retest where coders, owners, or adjudicators repeatedly identify missing, overlapping, too broad, or too narrow categories or rules." "Revise taxonomy and retest where coders, owners, or adjudicators repeatedly identify missing or inadequately represented categories, ambiguous or overlapping category boundaries, or another recurring taxonomy problem."
        Set-ExactParagraph $doc "the protocol-deviation log and instrument-change log." "the protocol-deviation log, instrument-change log, and dated pilot-feedback log."
        Set-ExactParagraph $doc "Any substantive amendment will be versioned and documented before the affected sampling, coding, or analysis step. Sampling artefacts for the active validation samples may be released after initial coding is complete. Reserve-sample Record IDs, allocation fields and related sampling artefacts will remain embargoed and unexamined until the relevant reserve retest has been completed or the reserve has been formally retired without use. Raw owner comments will not be published without permission where they reveal non-public information or identify individuals beyond the public register." "Before preregistration submission, approved protocol changes are incorporated directly into the active draft and its version history. After submission, any substantive amendment will be versioned and documented before the affected sampling, coding, or analysis step. Sampling artefacts for the active validation samples may be released after initial coding is complete. Reserve-sample Record IDs, allocation fields and related sampling artefacts will remain embargoed and unexamined until the relevant reserve retest has been completed or the reserve has been formally retired without use. Raw owner comments will not be published without permission where they reveal non-public information or identify individuals beyond the public register."
    }

    New-VersionedDocument "preregistration\package\05_training_and_pilot\DEA_coder_training_handout_v2.docx" "preregistration\package\05_training_and_pilot\DEA_coder_training_handout_v3.docx" {
        param($doc)
        Add-VersionNote $doc ("Post-pilot formal-coding reference v3 | redcap-candidate-0.4" + [char]13 + "REDCap visibility: assignment_id is visible and uses a neutral opaque code, for example A7K3M9Q2. project_title is visible read-only. datasets_used is visible read-only. reviewer_id / coder_id is hidden. record_id is hidden. official_project_id is hidden. sample and stratum fields are hidden.")
        Set-ExactParagraph $doc "Taxonomy fit asks whether the available categories can express the project: Fit, Partial Fit or No Fit." "Taxonomy fit asks whether the taxonomy can adequately express a project that you understand from the register entry. Fit: the categories adequately express the project. Partial Fit: the project is sufficiently understood, but the taxonomy represents it only approximately or incompletely. No Fit: the project is sufficiently understood, but the taxonomy cannot adequately express it. Cannot assess from register entry: the title and dataset field do not provide enough information to judge whether the taxonomy fits. This is an evidence limitation, not a taxonomy problem."
        Set-ExactParagraph $doc "A thin register entry is not automatically a taxonomy problem; a difficult rule is not automatically an insufficient entry." "A thin register entry is not automatically a taxonomy problem; a difficult rule is not automatically an insufficient entry. Do not select a taxonomy-issue type when Cannot assess from register entry is selected."
        Set-ExactParagraph $doc "Taxonomy fit: ☐ Fit ☐ Partial Fit ☐ No Fit" "Taxonomy fit: ☐ Fit ☐ Partial Fit ☐ No Fit ☐ Cannot assess from register entry" 3
        Set-ExactParagraph $doc "Taxonomy issue (if applicable): ☐ Missing category ☐ Ambiguous/overlapping ☐ Too broad ☐ Too narrow ☐ Other" "Taxonomy issue (if applicable): ☐ Missing or inadequately represented category ☐ Ambiguous or overlapping category boundaries ☐ Other taxonomy problem"
        Set-ExactParagraph $doc "Fit / Partial Fit / No Fit" "Fit / Partial Fit / No Fit / Cannot assess from register entry"
        Set-ExactParagraph $doc "Missing category; Ambiguous/overlapping; Too broad; Too narrow; Other" "Missing or inadequately represented category; Ambiguous or overlapping category boundaries; Other taxonomy problem"
        Set-ExactParagraph $doc "Insufficient register entry: the title + dataset field do not support confident classification. Pairs naturally with Unclear from Register Entry, but you can also flag insufficiency where you made a best-effort classification." "Insufficient register entry: the title and dataset field do not support confident classification. This pairs naturally with Unclear from Register Entry and may support Cannot assess from register entry, but neither response is automatic where a best-effort classification or taxonomy-fit judgement remains possible."
        Set-ExactParagraph $doc "Taxonomy fit problem: the taxonomy itself lacks the right category, or two categories overlap in a way that makes the decision difficult. This is a finding about the taxonomy, not a mistake by you." "Taxonomy fit problem: the taxonomy is missing or inadequately represents an important category, has ambiguous or overlapping category boundaries, or has another expressiveness problem. This is a finding about the taxonomy, not a mistake by you and not the same as Cannot assess from register entry."
        Set-ExactParagraph $doc "Complete ten additional projects in REDCap independently, using the links in the order provided. Use only the title, dataset field and frozen training materials. Do not discuss cases, search online or see an answer key before submission." "Historical pilot procedure: the ten-project pilot was launched under redcap-candidate-0.3 using the title, dataset field and as-delivered training materials. Candidate 0.4 adds Cannot assess from register entry in response to the debrief; that option was not available in the collected pilot form."
        Set-ExactParagraph $doc "During debrief, distinguish problems caused by the form, the public evidence, the taxonomy boundary and your own uncertainty." "During debrief and formal coding, distinguish problems caused by the form, the public evidence, the taxonomy boundary and your own uncertainty. Candidate 0.4 uses Cannot assess only for the public-evidence limitation."
        Set-ExactParagraph $doc "9. During formal coding" "9. During formal coding — redcap-candidate-0.4"
    }

    New-VersionedDocument "preregistration\package\05_training_and_pilot\DEA_trainer_handout_v1.docx" "preregistration\package\05_training_and_pilot\DEA_trainer_handout_v2.docx" {
        param($doc)
        Add-VersionNote $doc "Post-pilot trainer guide v2 | formal coding uses redcap-candidate-0.4"
        Set-ExactParagraph $doc "Taxonomy fit asks whether the available categories can express the project: Fit, Partial Fit or No Fit." "Taxonomy fit asks whether the taxonomy can adequately express a project understood from the register entry. Fit means the categories adequately express it. Partial Fit means the project is sufficiently understood but represented only approximately or incompletely. No Fit means the project is sufficiently understood but cannot be adequately expressed. Cannot assess from register entry means the title and dataset field are too thin to judge fit; it is an evidence limitation, not a taxonomy problem."
        Set-ExactParagraph $doc "A thin register entry is not automatically a taxonomy problem; a difficult rule is not automatically an insufficient entry." "A thin register entry is not automatically a taxonomy problem; a difficult rule is not automatically an insufficient entry. Cannot Assess is coherent only with Partial or Insufficient register sufficiency and never triggers a taxonomy-issue type. When the issue field appears, the retained types are Missing or inadequately represented category; Ambiguous or overlapping category boundaries; Other taxonomy problem."
        Set-ExactParagraph $doc "Distinction to enforce. Insufficient evidence concerns the register entry. Low confidence concerns the coder's certainty. Taxonomy fit concerns whether the category system can express the project. Do not let coders use Unclear as a substitute for a difficult rule." "Distinction to enforce. Insufficient evidence concerns the register entry. Low confidence concerns the coder's certainty. Taxonomy fit concerns whether the category system can express a project that is understood. Cannot assess from register entry is an evidence limitation; No Fit is a genuine taxonomy limitation. Do not let coders use Unclear or Cannot Assess as a substitute for a difficult rule."
        Set-ExactParagraph $doc "Show conditional issue-type field for Partial or No Fit." "Show Fit / Partial Fit / No Fit / Cannot assess from register entry. Show the conditional issue-type field only for Partial Fit or No Fit."
        Set-ExactParagraph $doc "Hidden debrief reading: Settled: Poverty, Wealth & Living Standards; purpose Unclear from Register Entry; no tags. Expected Partial sufficiency and Low/Medium confidence with a note." "Post-pilot debrief reading: Research Domain(s) Unclear from Register Entry; Analytical Purpose(s) Unclear from Register Entry; Equity No; COVID No; Register sufficiency Insufficient; Taxonomy fit Cannot assess from register entry; Confidence Low. The underlying project is not sufficiently understood, so this is a register-evidence limitation rather than evidence that the taxonomy fails. This response was added after the candidate-0.3 pilot and is used in candidate 0.4 formal coding."
        Set-ExactParagraph $doc "Instrument feature tested: Layer-specific Unclear, conditional sufficiency/confidence notes, and distinction between thin evidence and taxonomy failure." "Instrument feature tested: Layer-specific Unclear, conditional sufficiency/confidence notes, and the post-pilot distinction between Cannot assess and No Fit."
        Set-ExactParagraph $doc "Version and log any substantive rule, taxonomy or instrument change prompted by training/pilot." "Version and log any substantive rule, taxonomy or instrument change prompted by training/pilot. The 17 July changes are diagnostic-instrument changes in redcap-candidate-0.4, made before formal coding and preregistration submission."
    }

    New-VersionedDocument "preregistration\package\05_training_and_pilot\DEA_pilot_projects_trainer_debrief_reference.docx" "preregistration\package\05_training_and_pilot\DEA_pilot_projects_trainer_debrief_reference_v2.docx" {
        param($doc)
        Add-VersionNote $doc "Post-pilot debrief reference v2 | candidate 0.3 collected the pilot; candidate 0.4 applies to formal coding"
        Set-CellText $doc 2 5 3 ("Research Domain(s): Unclear from Register Entry" + [char]13 + "Analytical Purpose(s): Unclear from Register Entry" + [char]13 + "Equity No; COVID No")
        Set-CellText $doc 9 2 2 "Unclear from Register Entry"
        Set-CellText $doc 9 3 2 "Unclear from Register Entry"
        Set-CellText $doc 9 4 2 "No"
        Set-CellText $doc 9 5 2 "No"
        Set-CellText $doc 9 6 2 "Insufficient"
        Set-CellText $doc 9 7 2 "Cannot assess from register entry"
        Set-CellText $doc 9 8 2 "Low"
        Set-ExactParagraph $doc "Research Domain(s): The acronym title supplies no substantive information. The Living Costs and Food Survey nevertheless provides enough register evidence to support a household living-costs and living-standards domain reading." 'Rationale: "AMPHoRA" is an opaque acronym and does not identify the substantive object or analytical operation. The Living Costs and Food Survey provides contextual information about the data but cannot, on its own, establish the project''s domain or purpose. Because the underlying project is not sufficiently understood, taxonomy fit cannot be assessed. This is a register-evidence limitation rather than evidence that the taxonomy fails.'
        Set-ExactParagraph $doc 'Analytical Purpose(s): Neither “AMPHoRA” nor the dataset name reveals what the project does analytically. No specific operation can be inferred without outside information, so Unclear from Register Entry is the appropriate purpose.' "Boundary lesson: A dataset may corroborate or disambiguate evidence in a title, but should not ordinarily be the sole basis for assigning a substantive domain when the title contains no research-object information."
        Set-ExactParagraph $doc "Tags: Nothing in the visible fields identifies a demographic/equality comparison or pandemic focus." "Post-pilot instrument note: Cannot assess from register entry was not available in the candidate-0.3 pilot. It was added to candidate 0.4 for formal coding in response to this case. Candidate-0.4 taxonomy issue types are Missing or inadequately represented category; Ambiguous or overlapping category boundaries; Other taxonomy problem."
        Set-ExactParagraph $doc "Sufficiency, taxonomy fit and confidence: The entry is only partly classifiable: the dataset supports a domain, while the analytical purpose remains unresolved. This is an evidence limitation rather than a taxonomy failure." "Do not select a taxonomy-issue type when Cannot assess from register entry is selected."
        Set-ExactParagraph $doc "A Low-confidence response is also understandable if a coder is less comfortable using dataset knowledge. Unclear should be applied only to the unresolved purpose, not automatically to both dimensions." "The title and dataset field do not establish either substantive domain or analytical purpose. Do not infer Poverty, Wealth and Living Standards solely from the Living Costs and Food Survey."
        Set-ExactParagraph $doc "Dimension-specific Unclear, partial sufficiency, and conditional confidence/evidence notes." "Evidence-versus-taxonomy distinction; Cannot assess branching; Insufficient-evidence and Low-confidence note."
    }

    $report | Export-Csv -LiteralPath (Join-Path $RenderRoot "render_report.csv") -NoTypeInformation -Encoding UTF8
}
finally {
    if ($word -ne $null) {
        $word.Quit()
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
    }
}

$report | Format-Table -AutoSize
