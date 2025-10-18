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
   - **KEPT codes**: Select codes that are clinically appropriate and billable (rank by relevance)
   - **EXCLUDED codes**: List codes that are NOT appropriate with clear medical coding rationale
   - **Reasons to EXCLUDE (be very restrictive)**:
     * **NLP Misinterpretation**: Patient name mistaken for disease (e.g., "Rose" → rose fever), common words misidentified as medical terms
     * **Social History**: Conditions mentioned in social context (e.g., "patient's cat has diabetes", "family owns animals", "works with chemicals")
     * **Family History**: Conditions affecting family members, not the patient (e.g., "mother has diabetes", "father died of MI")
     * **Past Medical History**: Conditions explicitly stated as "history of" without current evidence or treatment
     * **Negated Findings**: Conditions stated as denied, ruled out, or absent (e.g., "denies chest pain", "no history of diabetes")
     * **Insufficient Documentation**: Code cannot be supported by clinical note content
     * **Symptom vs Diagnosis**: Not a billable diagnosis when underlying cause is known (symptom code when diagnosis available)
     * **Duplicate/Non-Specific**: More specific code available or duplicate representation
     * **Contextual Errors**: Code extracted from wrong section (e.g., differential diagnosis, patient education, hypothetical scenarios)
   - Do NOT add any new ICD-10 codes not provided by NLP
   - Prioritize codes that impact VERA complexity and MS-DRG assignment
   - **Be highly critical** - when in doubt about NLP extraction accuracy, EXCLUDE the code with explanation

2. **Assign MS-DRG Code** (if applicable for inpatient encounters):
   - Determine the appropriate MS-DRG based on selected ICD-10 codes
   - Consider principal diagnosis, secondary diagnoses, and complications/comorbidities (CC/MCC)
   - Provide DRG description and rationale for assignment
   - If outpatient encounter, note "Not Applicable - Outpatient"

3. **Determine VHA Complexity Code** (VERA System):
   - Assign the appropriate **VHA/VA Complexity Level** based on VERA (Veterans Equitable Resource Allocation) guidelines
   - VHA Complexity Levels: **1 (Low), 2 (Moderate), 3 (High), 4 (Very High), 5 (Extremely High)**
   - Consider:
     * Number and severity of chronic conditions
     * Service-connected disabilities
     * Mental health comorbidities
     * Age and functional status
     * Resource utilization and care intensity
     * Pharmacy complexity
     * Multiple provider involvement
   - Provide detailed rationale for the assigned VHA complexity level

4. **Provide VA-Specific Coding Recommendations**:
   - **Maximize VERA Complexity**: Suggest strategies to accurately capture higher complexity for VA resource allocation
   - **Documentation Improvements**: Recommend clinical documentation that supports appropriate VERA complexity scores
   - **Service-Connected Conditions**: Identify opportunities to properly document VA service-connected disabilities and conditions
   - **Better Coding**: General suggestions for more accurate and complete VA coding practices

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

**Response Format:**
Return a JSON object with this structure:
```json
{
    "selected_icd10_codes": [
        {
            "code": "I10",
            "description": "Essential hypertension",
            "rank": 1,
            "reason_kept": "Primary diagnosis, well-documented, impacts DRG assignment"
        }
    ],
    "excluded_icd10_codes": [
        {
            "code": "R00.0",
            "description": "Tachycardia, unspecified",
            "reason_excluded": "Symptom of underlying condition (heart failure), not separately billable when cause is identified"
        },
        {
            "code": "Z79.4",
            "description": "Long term use of insulin",
            "reason_excluded": "Not documented in clinical note, NLP extraction error"
        },
        {
            "code": "E11.9",
            "description": "Type 2 diabetes mellitus without complications",
            "reason_excluded": "Family history only - note states 'mother has diabetes', not patient diagnosis"
        },
        {
            "code": "M79.3",
            "description": "Panniculitis, unspecified",
            "reason_excluded": "NLP misinterpreted patient surname 'Panniculitis' as medical condition"
        },
        {
            "code": "Z91.19",
            "description": "Patient's noncompliance with other medical treatment",
            "reason_excluded": "Social history context - 'patient's dog requires insulin', NLP confused pet care with patient treatment"
        },
        {
            "code": "J45.909",
            "description": "Unspecified asthma, uncomplicated",
            "reason_excluded": "Negated finding - note states 'denies asthma', no current evidence"
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
    "clinical_reasoning": "<p><strong>MS-DRG Determination:</strong><br>Principal diagnosis of heart failure with documented MCC (acute kidney injury) supports DRG 291. This is appropriate for inpatient encounter.<br><br><strong>Code Validation:</strong><br>Reviewed all NLP-extracted codes for clinical validity and billing appropriateness. Excluded symptom codes and undocumented conditions.</p>",
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
            prompt_parts.append("\n")
        
        if clinical_context:
            # Truncate context if too long
            context = clinical_context[:1500] + "..." if len(clinical_context) > 1500 else clinical_context
            prompt_parts.append(f"**Clinical Note:**\n{context}\n\n")
        
        # Present ICD-10 codes extracted by NLP for review
        prompt_parts.append("**ICD-10 Codes Extracted by Prior NLP Routine:**\n")
        prompt_parts.append("(Please review and select ONLY appropriate codes from this list. Do NOT add new codes.)\n")
        prompt_parts.append("**CRITICAL**: Carefully review the clinical note above to verify each code is:\n")
        prompt_parts.append("  - Actually about the PATIENT (not family members, pets, or social contacts)\n")
        prompt_parts.append("  - Not a patient/provider NAME misinterpreted as a disease\n")
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
        prompt_parts.append("1. **CAREFULLY** review the clinical note context for each ICD-10 code above\n")
        prompt_parts.append("2. **EXCLUDE** codes that are:\n")
        prompt_parts.append("   - Patient/provider names misinterpreted as diseases\n")
        prompt_parts.append("   - Social history mentions (pets, family members, occupational exposures without patient diagnosis)\n")
        prompt_parts.append("   - Family history (conditions of relatives, not patient)\n")
        prompt_parts.append("   - Negated or ruled out conditions\n")
        prompt_parts.append("   - Simple word misinterpretations by NLP\n")
        prompt_parts.append("3. **KEEP** only codes with clear clinical documentation supporting PATIENT diagnosis\n")
        prompt_parts.append("4. Determine the most appropriate MS-DRG code(s) based on your selected ICD-10 codes\n")
        prompt_parts.append("5. Assess VHA VERA complexity level and provide coding recommendations\n")
        prompt_parts.append("6. Return your analysis in the specified JSON format\n")
        prompt_parts.append("\n**Remember**: When uncertain about NLP extraction accuracy, EXCLUDE the code with clear reasoning.\n")
        
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
            
            # Combine all parts with HTML formatting (exclude codes will be shown below the table)
            clinical_reasoning_html = response_data.get('clinical_reasoning', '')
            full_reasoning = f"{clinical_reasoning_html}{drg_summary_html}{codes_summary_html}{vha_summary_html}{recommendations_html}"
            
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