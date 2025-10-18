"""
OpenAI GPT-4o powered DRG and Complexity Analysis

This module uses OpenAI's GPT-4o model to intelligently analyze medical concepts
extracted by NLP and determine appropriate DRG codes and complexity levels.
This replaces the heuristic-based approach with sophisticated AI reasoning.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import openai
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DRGAnalysis:
    """Structured result from OpenAI DRG analysis."""
    primary_drg: Optional[str]
    drg_description: Optional[str]
    complexity_level: str  # "Low", "Medium", "High" or "VHA Level X - Description"
    complexity_rationale: str
    secondary_drgs: List[Dict[str, str]]
    clinical_reasoning: str
    confidence_score: float
    supporting_concepts: List[str]
    selected_codes: Optional[List[Dict[str, Any]]] = None  # Ranked ICD-10 codes from AI
    excluded_codes: Optional[List[Dict[str, Any]]] = None  # Excluded ICD-10 codes with reasons

class OpenAIDRGAnalyzer:
    """
    OpenAI GPT-4o powered DRG and complexity analyzer.
    
    This class takes NLP-extracted medical concepts and uses GPT-4o to:
    1. Determine the most appropriate primary DRG code
    2. Assess complexity level (Low/Medium/High) based on comorbidities
    3. Provide clinical reasoning for the decisions
    4. Identify supporting secondary DRGs
    """
    
    def __init__(self):
        """Initialize the OpenAI client."""
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o"  # Use GPT-4o for advanced reasoning
        
        logger.info("OpenAI DRG Analyzer initialized with GPT-4o")
    
    def analyze_concepts_for_drg(self, 
                               extracted_concepts: List[Dict[str, Any]], 
                               clinical_context: str = "",
                               patient_demographics: Dict[str, Any] = None) -> DRGAnalysis:
        """
        Analyze extracted medical concepts to determine DRG and complexity.
        
        Args:
            extracted_concepts: List of concepts from NLP extraction
            clinical_context: Original clinical text for context
            patient_demographics: Age, gender, etc. if available
            
        Returns:
            DRGAnalysis with DRG codes, complexity, and reasoning
        """
        try:
            # Prepare the prompt with structured data
            prompt = self._build_analysis_prompt(
                extracted_concepts, 
                clinical_context, 
                patient_demographics
            )
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.2,  # Low temperature for consistent medical analysis
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            result = json.loads(response.choices[0].message.content)
            logger.info(f"OpenAI response parsed successfully")
            return self._parse_openai_response(result)
            
        except Exception as e:
            logger.error(f"Error in OpenAI DRG analysis: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._create_fallback_analysis(extracted_concepts)
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the OpenAI model."""
        return """You are an expert medical coding professional working at the Department of Veterans Affairs (VA) with deep knowledge of ICD-10 coding, MS-DRG classification, and Veterans Health Administration (VHA) VERA complexity scoring system.

**Your Role:** You are a certified medical coder working in the Health Information Management (HIM) department at a VA Medical Center. Your expertise includes accurate ICD-10-CM coding, MS-DRG assignment, and optimizing VERA complexity scores for appropriate resource allocation and reimbursement.

**Your Task:**

1. **Review and Validate ALL ICD-10 Codes** from the prior NLP routine:
   - Review ALL ICD-10 codes provided by the NLP extraction
   - For EACH code, determine if it should be KEPT or EXCLUDED
   - **KEPT codes**: ONLY conditions that are:
     * **Actively addressed in THIS visit** by the provider (treatment, evaluation, or monitoring)
     * **Patient's current concern** mentioned as chief complaint or reason for visit
     * **Being actively managed** with prescriptions, procedures, or clinical decisions TODAY
   - **Target**: Aim for 5-10 primary diagnoses IF clinically supported and relevant to THIS encounter
   - **EXCLUDED codes**: MUST be excluded if ANY of these apply:
     * **PATIENT NAME**: Code matches patient surname or first name (e.g., patient "John Smith" → Smith fracture MUST be excluded)
     * **PROVIDER NAME**: Code matches provider's name in signature or header
     * **PATIENT NAME**: Code matches patient surname or first name (e.g., patient "John Smith" → Smith fracture MUST be excluded)
     * **PROVIDER NAME**: Code matches provider's name in signature or header
     * **NLP Misinterpretation**: Common words misidentified as medical terms (e.g., "may" → May disease)
     * **Family History ONLY**: Conditions of relatives NOT the patient (e.g., "mother has diabetes", "father died of MI") - EXCLUDE unless patient also has the condition
     * **Social History**: Pets, family members, occupational exposures mentioned in passing without patient diagnosis
     * **Past Medical History ONLY**: "History of" conditions with NO current evidence, treatment, or monitoring in this visit
     * **Negated/Ruled Out**: Explicitly denied or ruled out (e.g., "denies chest pain", "no diabetes", "rules out MI")
     * **Not Addressed This Visit**: Condition mentioned but NOT evaluated, treated, or managed in this encounter
     * **Differential Diagnosis**: Conditions considered but ruled out or not confirmed
     * **Patient Education**: Conditions discussed hypothetically for prevention/education, not actual diagnoses
     * **Insufficient Documentation**: Cannot confirm patient actually has this condition based on note
     * **Symptom Code**: Use diagnosis code instead when underlying cause is documented
     * **Duplicate/Non-Specific**: More specific code available
   - Do NOT add any new ICD-10 codes not provided by NLP
   - Prioritize codes for conditions actively managed in THIS encounter
   - **Default to EXCLUDE** - Only keep codes with crystal-clear evidence that the patient HAS this condition AND it's relevant to this visit
   - **CRITICAL**: Do NOT make up diagnoses, complications, or severity levels not explicitly documented in the clinical note
   - **CRITICAL**: Do NOT upgrade severity (e.g., "uncomplicated" to "with complications") unless explicitly stated
   - **CRITICAL**: Use ONLY the ICD-10 codes provided by NLP - do NOT invent new codes or modify existing ones

2. **Assign MS-DRG Code** (if applicable for inpatient encounters):
   - Determine the appropriate MS-DRG based ONLY on selected ICD-10 codes that are explicitly documented
   - Consider principal diagnosis, secondary diagnoses, and complications/comorbidities (CC/MCC)
   - **CRITICAL**: Do NOT maximize DRG by inventing complications or upgrading severity
   - **CRITICAL**: Only assign CC/MCC if explicitly documented with supporting clinical evidence in the note
   - Provide DRG description and rationale for assignment
   - If outpatient encounter, note "Not Applicable - Outpatient"

3. **Determine VHA Complexity Code** (VERA System):
   - Assign the appropriate **VHA/VA Complexity Level** based on VERA (Veterans Equitable Resource Allocation) guidelines
   - VHA Complexity Levels: **1 (Low), 2 (Moderate), 3 (High), 4 (Very High), 5 (Extremely High)**
   - **CRITICAL**: Base complexity ONLY on documented conditions in the clinical note - do NOT assume or invent conditions
   - **CRITICAL**: Do NOT upgrade complexity by assuming severity not explicitly stated
   - Consider ONLY what is documented:
     * Number and severity of chronic conditions (as documented)
     * Service-connected disabilities (if mentioned)
     * Mental health comorbidities (if documented)
     * Age and functional status (if stated)
     * Resource utilization and care intensity (based on visit content)
     * Pharmacy complexity (based on medications listed)
     * Multiple provider involvement (if documented)
   - Provide detailed rationale for the assigned VHA complexity level based on actual documentation

4. **Provide VA-Specific Coding Recommendations**:
   - **Maximize VERA Complexity**: Suggest strategies to accurately capture complexity based on what IS documented (not by inventing conditions)
   - **Documentation Improvements**: Recommend clinical documentation that would support appropriate VERA complexity IF those conditions exist
   - **Service-Connected Conditions**: Identify opportunities to document VA service-connected disabilities IF they exist
   - **Better Coding**: Suggest more accurate and complete coding based ONLY on documented information
   - **CRITICAL**: Recommendations should be for FUTURE documentation improvements, NOT to add information to THIS visit's coding

**VHA VERA Complexity Scoring Guidelines:**
- **Level 5 (Extremely High)**: Multiple severe chronic conditions, high pharmacy burden, frequent admissions, intensive care needs
- **Level 4 (Very High)**: Several chronic conditions with complications, significant mental health issues, high resource use
- **Level 3 (High)**: Multiple chronic conditions, some complications/comorbidities, moderate resource utilization
- **Level 2 (Moderate)**: Few chronic conditions, stable, routine care needs
- **Level 1 (Low)**: Minimal chronic conditions, preventive care, low resource utilization

**IMPORTANT - Output Formatting:**
- Use HTML tags for structure (p, strong, em, ul, li, br)
- Do NOT use markdown asterisks (*) or dashes (-)
- Use HTML lists (<ul><li>) instead of bullet points
- Use <strong> for emphasis instead of **bold**
- Use <br> for line breaks instead of blank lines
- **clinical_reasoning field**: Focus ONLY on code validation summary, do NOT include MS-DRG information here (DRG has its own separate fields)

**Response Format:**
Return a JSON object with this structure:
```json
{
    "selected_icd10_codes": [
        {
            "code": "I50.9",
            "description": "Heart failure, unspecified",
            "rank": 1,
            "reason_kept": "Principal diagnosis, well-documented acute decompensation, impacts DRG assignment"
        },
        {
            "code": "N17.9",
            "description": "Acute kidney failure, unspecified",
            "rank": 2,
            "reason_kept": "Major complication/comorbidity (MCC), acute on chronic renal insufficiency documented"
        },
        {
            "code": "E11.65",
            "description": "Type 2 diabetes mellitus with hyperglycemia",
            "rank": 3,
            "reason_kept": "Active diagnosis with current treatment, impacts VERA complexity"
        },
        {
            "code": "I10",
            "description": "Essential hypertension",
            "rank": 4,
            "reason_kept": "Chronic condition on active medication, contributes to overall complexity"
        },
        {
            "code": "J44.1",
            "description": "Chronic obstructive pulmonary disease with acute exacerbation",
            "rank": 5,
            "reason_kept": "Secondary diagnosis with current exacerbation, requires treatment"
        }
    ],
    "excluded_icd10_codes": [
        {
            "code": "S52.541A",
            "description": "Smith's fracture of right radius, initial encounter",
            "reason_excluded": "Patient name is 'John Smith' - NLP misinterpreted patient surname as Smith fracture. No fracture documented in clinical note."
        },
        {
            "code": "R00.0",
            "description": "Tachycardia, unspecified",
            "reason_excluded": "Symptom of underlying heart failure, not separately billable when cause is identified"
        },
        {
            "code": "Z79.4",
            "description": "Long term use of insulin",
            "reason_excluded": "Not documented in this visit, no insulin prescription or discussion in current note"
        },
        {
            "code": "E11.9",
            "description": "Type 2 diabetes mellitus without complications",
            "reason_excluded": "Family history only - note states 'mother has diabetes', patient does not have diabetes diagnosis"
        },
        {
            "code": "I25.10",
            "description": "Atherosclerotic heart disease of native coronary artery without angina",
            "reason_excluded": "Past medical history mentioned but NOT addressed, evaluated, or treated in this visit"
        },
        {
            "code": "J45.909",
            "description": "Unspecified asthma, uncomplicated",
            "reason_excluded": "Negated - note explicitly states 'patient denies asthma', no evidence of asthma"
        },
        {
            "code": "N18.3",
            "description": "Chronic kidney disease, stage 3",
            "reason_excluded": "Mentioned in differential diagnosis but ruled out by lab results, not confirmed diagnosis"
        }
    ],
    "primary_drg": "291",
    "drg_description": "Heart Failure and Shock with MCC",
    "drg_rationale": "<p>Patient has documented heart failure with acute kidney injury qualifying as MCC. Principal diagnosis I50.9 groups to MDC 5 (Circulatory System). Presence of MCC N17.9 qualifies for DRG 291.</p>",
    "secondary_drgs": [
        {"drg": "292", "description": "Heart Failure and Shock with CC", "note": "If MCC downgraded to CC"}
    ],
    "vha_complexity_level": "4",
    "vha_complexity_description": "Very High",
    "vha_complexity_rationale": "<p>Multiple severe chronic conditions including heart failure, diabetes with complications, chronic kidney disease. High pharmacy burden. Requires intensive monitoring and frequent follow-up.</p>",
    "clinical_reasoning": "<p><strong>Code Validation Summary:</strong><br>Reviewed all NLP-extracted codes for clinical validity and billing appropriateness. Selected codes with clear documentation support. Excluded symptom codes, family history mentions, and undocumented conditions. Principal diagnosis and comorbidities appropriately captured for accurate VERA complexity assessment.</p>",
    "confidence_score": 0.92,
    "supporting_concepts": ["Heart failure", "Acute kidney injury", "Diabetes with complications"],
    "recommendations": {
        "maximize_vera_complexity": "<p>Document all chronic conditions and active medications. Ensure service-connected disabilities are noted. Capture mental health comorbidities if present.</p>",
        "better_coding": "<p>Use most specific ICD-10 codes available. Document laterality and severity. Ensure principal diagnosis is clearly identified.</p>",
        "documentation_improvements": "<p>Clinical note should specify: <ul><li>Chronic vs acute conditions</li><li>Complications and comorbidities</li><li>Service-connected status for each condition</li><li>Current treatment plans and medications</li></ul></p>",
        "service_connected_opportunities": "<p>If heart failure or kidney disease are service-connected, ensure this is documented for proper VA compensation and resource allocation.</p>"
    }
}
```"""
    
    def _build_analysis_prompt(self, 
                             concepts: List[Dict[str, Any]], 
                             clinical_context: str,
                             demographics: Dict[str, Any] = None) -> str:
        """Build the analysis prompt with extracted concepts."""
        
        # Extract key information from concepts
        diagnoses = []
        procedures = []
        symptoms = []
        medications = []
        
        for concept in concepts:
            term = concept.get('term', '')
            cui = concept.get('cui', '')
            semtypes = concept.get('semtypes', [])
            icd10_codes = concept.get('icd10_codes', [])
            snomed_codes = concept.get('snomed_codes', [])
            
            # Categorize by semantic types
            if any(st in ['T047', 'T191', 'T046'] for st in semtypes):  # Disease/Disorder
                diagnoses.append({
                    'term': term,
                    'cui': cui,
                    'icd10_codes': [c.get('code') for c in icd10_codes if isinstance(c, dict)],
                    'similarity': concept.get('similarity', 0)
                })
            elif any(st in ['T060', 'T061'] for st in semtypes):  # Procedures
                procedures.append({
                    'term': term,
                    'cui': cui,
                    'similarity': concept.get('similarity', 0)
                })
            elif any(st in ['T184', 'T033'] for st in semtypes):  # Symptoms/Findings
                symptoms.append({
                    'term': term,
                    'cui': cui,
                    'similarity': concept.get('similarity', 0)
                })
            elif any(st in ['T121', 'T109'] for st in semtypes):  # Medications
                medications.append({
                    'term': term,
                    'cui': cui,
                    'similarity': concept.get('similarity', 0)
                })
        
        # Build structured prompt
        prompt_parts = [
            "Please analyze the following information and provide your expert coding assessment.\n\n"
        ]
        
        if demographics:
            prompt_parts.append(f"**Patient Demographics:**\n")
            for key, value in demographics.items():
                prompt_parts.append(f"- {key}: {value}\n")
            
            # HIGHLIGHT patient name if present
            if 'patient_name' in demographics:
                prompt_parts.append(f"\n⚠️ **PATIENT NAME: {demographics['patient_name']}** ⚠️\n")
                prompt_parts.append(f"YOU MUST EXCLUDE any ICD-10 codes that match this name!\n")
                prompt_parts.append(f"For example: If patient is '{demographics['patient_name']}', exclude any codes with '{demographics['patient_name']}' in the description.\n")
            prompt_parts.append("\n")
        
        if clinical_context:
            # Truncate context if too long
            context = clinical_context[:1500] + "..." if len(clinical_context) > 1500 else clinical_context
            prompt_parts.append(f"**Clinical Note:**\n{context}\n\n")
        
        # ADD CRITICAL FIRST STEP: Extract patient/provider names
        prompt_parts.append("**CRITICAL FIRST STEP - IDENTIFY PATIENT AND PROVIDER NAMES:**\n")
        prompt_parts.append("Before reviewing any ICD-10 codes, carefully read the clinical note above and identify:\n")
        prompt_parts.append("1. PATIENT NAME: Look for patient name in the note (commonly appears at top, or phrases like 'Patient:', 'Pt:', 'Mr.', 'Ms.', 'Mrs.')\n")
        prompt_parts.append("2. PROVIDER NAME: Look for provider name (commonly in signature, 'Electronically signed by', 'Dr.', physician name)\n")
        prompt_parts.append("3. Once you identify these names, you MUST EXCLUDE any ICD-10 codes that match these names\n")
        prompt_parts.append("   Examples:\n")
        prompt_parts.append("   - Patient name 'John Smith' → EXCLUDE Smith's fracture (S52.541A)\n")
        prompt_parts.append("   - Patient name 'Robert Parkinson' → EXCLUDE Parkinson's disease (G20)\n")
        prompt_parts.append("   - Provider 'Dr. Bell' → EXCLUDE Bell's palsy (G51.0)\n")
        prompt_parts.append("   - Patient surname 'May' → EXCLUDE May disease codes\n")
        prompt_parts.append("   - Patient name 'Turner' → EXCLUDE Turner syndrome\n")
        prompt_parts.append("**This is the MOST COMMON NLP ERROR - always check names first!**\n\n")
        
        # Present ICD-10 codes extracted by NLP for review
        prompt_parts.append("**ICD-10 Codes Extracted by Prior NLP Routine:**\n")
        prompt_parts.append("(Please review and select ONLY appropriate codes from this list. Do NOT add new codes.)\n")
        prompt_parts.append("**CRITICAL**: Carefully review the clinical note above to verify each code is:\n")
        prompt_parts.append("  - NOT matching patient name, provider name, or any person's name mentioned\n")
        prompt_parts.append("  - Actually about the PATIENT (not family members, pets, or social contacts)\n")
        prompt_parts.append("  - Not from social history, family history, or past medical history sections\n")
        prompt_parts.append("  - Not negated or ruled out in the clinical note\n")
        prompt_parts.append("  - Supported by current clinical documentation\n\n")
        
        if diagnoses:
            for dx in sorted(diagnoses, key=lambda x: x['similarity'], reverse=True)[:20]:
                codes_str = ", ".join(dx['icd10_codes']) if dx['icd10_codes'] else "No ICD-10 mapping"
                prompt_parts.append(f"- {codes_str}: {dx['term']} (NLP Confidence: {dx['similarity']:.2f})\n")
            prompt_parts.append("\n")
        else:
            prompt_parts.append("- No ICD-10 codes were extracted by the NLP routine\n\n")
        
        if procedures:
            prompt_parts.append("**Procedures Mentioned:**\n")
            for proc in sorted(procedures, key=lambda x: x['similarity'], reverse=True)[:5]:
                prompt_parts.append(f"- {proc['term']} (Confidence: {proc['similarity']:.2f})\n")
            prompt_parts.append("\n")
        
        if medications:
            prompt_parts.append("**Medications:**\n")
            for med in sorted(medications, key=lambda x: x['similarity'], reverse=True)[:5]:
                prompt_parts.append(f"- {med['term']}\n")
            prompt_parts.append("\n")
        
        prompt_parts.append("**Instructions:**\n")
        prompt_parts.append("**STEP 0 - IDENTIFY NAMES (DO THIS FIRST!):**\n")
        prompt_parts.append("   a. Read the clinical note and write down the PATIENT'S NAME (first name, last name, any nicknames)\n")
        prompt_parts.append("   b. Write down the PROVIDER'S NAME (doctor, nurse, any staff mentioned)\n")
        prompt_parts.append("   c. Write down any OTHER PERSON'S NAMES mentioned (family members, emergency contacts)\n")
        prompt_parts.append("   d. For EACH ICD-10 code below, check if the code description contains ANY of these names\n")
        prompt_parts.append("   e. If ANY name matches an ICD-10 code description → IMMEDIATELY EXCLUDE IT\n")
        prompt_parts.append("   Examples of NAME-based exclusions:\n")
        prompt_parts.append("      • Patient: 'John Smith' → Smith's fracture (S52.541A) = EXCLUDE\n")
        prompt_parts.append("      • Patient: 'Sarah Parkinson' → Parkinson's disease (G20) = EXCLUDE\n")
        prompt_parts.append("      • Provider: 'Dr. Bell' → Bell's palsy (G51.0) = EXCLUDE\n")
        prompt_parts.append("      • Mother: 'Mary Crohn' → Crohn's disease (K50.90) = EXCLUDE (if mother's name)\n")
        prompt_parts.append("      • Patient: 'Turner' → Turner syndrome (Q96.9) = EXCLUDE\n")
        prompt_parts.append("\n")
        prompt_parts.append("1. **AFTER checking names**, review the clinical note context for each remaining ICD-10 code\n")
        prompt_parts.append("2. **EXCLUDE** codes that are:\n")
        prompt_parts.append("   - Matching ANY person's name mentioned in the note (MOST IMPORTANT CHECK)\n")
        prompt_parts.append("   - Family history ONLY (relatives' conditions, NOT patient's unless also documented for patient)\n")
        prompt_parts.append("   - Social history mentions (pets, family activities, occupational context without patient diagnosis)\n")
        prompt_parts.append("   - Past medical history NOT addressed in this visit (mentioned but no current treatment/evaluation)\n")
        prompt_parts.append("   - Negated, denied, or ruled out conditions\n")
        prompt_parts.append("   - Differential diagnosis that was ruled out or not confirmed\n")
        prompt_parts.append("   - Simple word misinterpretations by NLP\n")
        prompt_parts.append("3. **KEEP** ONLY if condition is:\n")
        prompt_parts.append("   - NOT matching any person's name AND\n")
        prompt_parts.append("   - Actively addressed/treated/monitored by provider in THIS visit\n")
        prompt_parts.append("   - Patient's chief complaint or current concern\n")
        prompt_parts.append("   - Being managed with medications, procedures, or clinical decisions TODAY\n")
        prompt_parts.append("4. **DO NOT** make up diagnoses, complications, or severity levels not in the note\n")
        prompt_parts.append("5. **DO NOT** upgrade ICD-10 codes (e.g., don't change 'uncomplicated' to 'with complications')\n")
        prompt_parts.append("6. **DO NOT** add CC/MCC/complications to maximize DRG unless explicitly documented\n")
        prompt_parts.append("7. Rank ALL kept codes by importance (1=most important for billing/DRG)\n")
        prompt_parts.append("8. Determine MS-DRG based ONLY on documented codes and severity\n")
        prompt_parts.append("9. Assess VHA VERA complexity based ONLY on what is documented\n")
        prompt_parts.append("10. Return your analysis in the specified JSON format\n")
        prompt_parts.append("\n**CRITICAL RULES**:\n")
        prompt_parts.append("- FIRST: Check ALL ICD-10 codes against patient/provider/family member names - EXCLUDE any matches\n")
        prompt_parts.append("- When uncertain if a code is for THIS PATIENT in THIS VISIT, EXCLUDE it with clear reasoning\n")
        prompt_parts.append("- Default to EXCLUDE, not include\n")
        prompt_parts.append("- Use ONLY codes provided by NLP - do NOT invent or modify codes\n")
        prompt_parts.append("- Do NOT upgrade severity, complications, or DRG assignment beyond what is explicitly documented\n")
        prompt_parts.append("- Be conservative and honest - code what is documented, not what might maximize reimbursement\n")
        prompt_parts.append("- NAME MATCHING IS THE #1 PRIORITY - if a code description contains a person's name from the note, EXCLUDE IT\n")
        
        return "".join(prompt_parts)
    
    def _parse_openai_response(self, response_data: Dict[str, Any]) -> DRGAnalysis:
        """Parse the OpenAI JSON response into a DRGAnalysis object."""
        try:
            # Extract recommendations if present
            recommendations = response_data.get('recommendations', {})
            recommendations_html = f"""
<div style="margin-top: 1em;">
    <h4 style="color: #558b2f; margin-bottom: 0.5em;">VHA VERA RECOMMENDATIONS</h4>
    <div style="margin-bottom: 1em;">
        <strong>Maximize VERA Complexity:</strong><br>
        {recommendations.get('maximize_vera_complexity', 'N/A')}
    </div>
    <div style="margin-bottom: 1em;">
        <strong>Better Coding:</strong><br>
        {recommendations.get('better_coding', 'N/A')}
    </div>
    <div style="margin-bottom: 1em;">
        <strong>Documentation Improvements:</strong><br>
        {recommendations.get('documentation_improvements', 'N/A')}
    </div>
    <div style="margin-bottom: 1em;">
        <strong>Service-Connected Opportunities:</strong><br>
        {recommendations.get('service_connected_opportunities', 'N/A')}
    </div>
</div>
"""
            
            # Format selected codes for display - TOP 5 ONLY
            selected_codes = response_data.get('selected_icd10_codes', [])
            # Sort by rank if provided and limit to top 5
            selected_codes_sorted = sorted(selected_codes, key=lambda x: x.get('rank', 999))[:5]
            
            codes_summary_html = """
<div style="margin-bottom: 1em;">
    <h4 style="color: #558b2f; margin-bottom: 0.5em;">Top 5 Primary Diagnoses (Ranked by Relevance)</h4>
    <ol style="margin: 0; padding-left: 1.5em;">
"""
            for code_info in selected_codes_sorted:
                codes_summary_html += f"""
        <li style="margin-bottom: 0.5em;">
            <strong>{code_info.get('code')}</strong>: {code_info.get('description')}<br>
            <em style="font-size: 0.9em; color: #666;">{code_info.get('reason_kept', 'N/A')}</em>
        </li>
"""
            codes_summary_html += "    </ol>\n</div>"
            
            # Format excluded codes for display
            excluded_codes = response_data.get('excluded_icd10_codes', [])
            excluded_codes_html = ""
            if excluded_codes:
                excluded_codes_html = """
<div style="margin-bottom: 1em;">
    <h4 style="color: #d32f2f; margin-bottom: 0.5em;">⚠️ Excluded ICD-10 Codes</h4>
    <div style="background: #ffebee; padding: 1em; border-radius: 4px; border-left: 4px solid #d32f2f;">
        <ul style="margin: 0; padding-left: 1.5em;">
"""
                for excluded in excluded_codes:
                    excluded_codes_html += f"""
            <li style="margin-bottom: 0.8em;">
                <strong style="color: #c62828;">{excluded.get('code')}</strong>: {excluded.get('description')}<br>
                <em style="font-size: 0.9em; color: #c62828;">Reason excluded: {excluded.get('reason_excluded', 'N/A')}</em>
            </li>
"""
                excluded_codes_html += """
        </ul>
    </div>
</div>
"""
            
            # Extract and format MS-DRG information
            primary_drg = response_data.get('primary_drg')
            drg_description = response_data.get('drg_description', 'Not determined')
            drg_rationale = response_data.get('drg_rationale', '')
            secondary_drgs = response_data.get('secondary_drgs', [])
            
            drg_summary_html = f"""
<div style="margin-bottom: 1em;">
    <h4 style="color: #1976d2; margin-bottom: 0.5em;">MS-DRG Classification</h4>
    <div style="background: #e3f2fd; padding: 1em; border-radius: 4px; border-left: 4px solid #1976d2;">
        <p><strong>Primary DRG:</strong> {primary_drg or 'Not Applicable'}</p>
        <p><strong>Description:</strong> {drg_description}</p>
        <p><strong>Rationale:</strong><br>{drg_rationale}</p>
"""
            if secondary_drgs:
                drg_summary_html += """
        <p><strong>Alternative DRGs:</strong></p>
        <ul style="margin: 0; padding-left: 1.5em;">
"""
                for sec_drg in secondary_drgs:
                    note = sec_drg.get('note', '')
                    drg_summary_html += f"""
            <li><strong>{sec_drg.get('drg')}</strong>: {sec_drg.get('description')} {f'({note})' if note else ''}</li>
"""
                drg_summary_html += """
        </ul>
"""
            drg_summary_html += """
    </div>
</div>
"""
            
            # Extract VHA complexity information
            vha_complexity = response_data.get('vha_complexity_level', 'N/A')
            vha_complexity_desc = response_data.get('vha_complexity_description', 'N/A')
            vha_rationale = response_data.get('vha_complexity_rationale', '')
            
            # Build VHA complexity summary
            vha_summary_html = f"""
<div style="margin-bottom: 1em;">
    <h4 style="color: #558b2f; margin-bottom: 0.5em;">📊 VHA VERA Complexity Assessment</h4>
    <p><strong>Level:</strong> {vha_complexity} ({vha_complexity_desc})</p>
    <p><strong>Rationale:</strong><br>{vha_rationale}</p>
</div>
"""
            
            # Combine all parts with HTML formatting (DRG will be at bottom, hidden by default)
            # Order: Clinical Reasoning -> Top 5 Codes -> VHA Complexity -> Recommendations -> DRG (collapsible)
            clinical_reasoning_html = response_data.get('clinical_reasoning', '')
            
            # Add DRG toggle button and collapsible section
            drg_section_html = f"""
<div style="margin-top: 1.5em; padding-top: 1em; border-top: 2px solid #e0e0e0;">
    <button id="toggle-drg-assessment" type="button" style="padding: 0.8em 1.5em; background: #1976d2; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 1em; font-weight: bold;">
        📋 Show MS-DRG Assessment
    </button>
    <div id="drg-assessment-content" style="display: none; margin-top: 1em;">
        {drg_summary_html}
    </div>
</div>
"""
            
            full_reasoning = f"{clinical_reasoning_html}{codes_summary_html}{vha_summary_html}{recommendations_html}{drg_section_html}"
            
            # Store VHA complexity in the complexity_level field (format: "Level X - Description")
            complexity_display = f"VHA Level {vha_complexity} - {vha_complexity_desc}"
            
            return DRGAnalysis(
                primary_drg=response_data.get('primary_drg'),
                drg_description=response_data.get('drg_description'),
                complexity_level=complexity_display,
                complexity_rationale=vha_rationale,
                secondary_drgs=response_data.get('secondary_drgs', []),
                clinical_reasoning=full_reasoning,
                confidence_score=float(response_data.get('confidence_score', 0.5)),
                supporting_concepts=response_data.get('supporting_concepts', []),
                selected_codes=selected_codes_sorted,  # Include ranked codes
                excluded_codes=excluded_codes  # Include excluded codes for filtering
            )
        except Exception as e:
            logger.error(f"Error parsing OpenAI response: {e}")
            return self._create_fallback_analysis([])
    
    def _create_fallback_analysis(self, concepts: List[Dict[str, Any]]) -> DRGAnalysis:
        """Create a fallback analysis when OpenAI fails."""
        return DRGAnalysis(
            primary_drg=None,
            drg_description="Analysis unavailable - OpenAI API error",
            complexity_level="Medium",
            complexity_rationale="Fallback analysis due to API error",
            secondary_drgs=[],
            clinical_reasoning="Unable to perform AI analysis",
            confidence_score=0.0,
            supporting_concepts=[]
        )

# Global instance for singleton pattern
_openai_analyzer_instance: Optional[OpenAIDRGAnalyzer] = None

def get_openai_drg_analyzer() -> Optional[OpenAIDRGAnalyzer]:
    """Get singleton instance of OpenAI DRG analyzer."""
    global _openai_analyzer_instance
    
    # Check if OpenAI is enabled
    if not os.getenv('OPENAI_API_KEY'):
        logger.warning("OpenAI API key not found - AI DRG analysis disabled")
        return None
    
    if not os.getenv('ENABLE_OPENAI_DRG', '0') == '1':
        logger.info("OpenAI DRG analysis disabled by environment variable")
        return None
    
    try:
        if _openai_analyzer_instance is None:
            _openai_analyzer_instance = OpenAIDRGAnalyzer()
        return _openai_analyzer_instance
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI DRG analyzer: {e}")
        return None

def analyze_concepts_with_openai(concepts: List[Dict[str, Any]], 
                               clinical_text: str = "",
                               patient_info: Dict[str, Any] = None) -> Optional[DRGAnalysis]:
    """
    Convenience function to analyze concepts with OpenAI.
    
    Args:
        concepts: Extracted medical concepts from NLP
        clinical_text: Original clinical text
        patient_info: Patient demographics/info
        
    Returns:
        DRGAnalysis or None if disabled/error
    """
    logger.info(f"analyze_concepts_with_openai called with {len(concepts)} concepts")
    logger.info(f"OPENAI_API_KEY present: {bool(os.getenv('OPENAI_API_KEY'))}")
    logger.info(f"ENABLE_OPENAI_DRG: {os.getenv('ENABLE_OPENAI_DRG')}")
    
    analyzer = get_openai_drg_analyzer()
    if not analyzer:
        logger.error("Failed to get OpenAI analyzer instance")
        return None
    
    logger.info("Got OpenAI analyzer, calling analyze_concepts_for_drg...")
    result = analyzer.analyze_concepts_for_drg(concepts, clinical_text, patient_info)
    logger.info(f"Analysis result: {result is not None}")
    return result