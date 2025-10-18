# UI Layout Update - October 17, 2025

## Summary of Changes

The medical coding application UI has been reorganized to improve workflow clarity and separate DRG functionality from the main analysis process.

---

## Key Changes

### 1. **Inpatient Checkbox Relocated**
- **Previous Location**: Top of form, before "Extract Codes" button
- **New Location**: Bottom of results section in "Additional Options" panel
- **Behavior**: 
  - ✅ **Unchecked by default** (no localStorage persistence)
  - Only controls display of "INPATIENT" badge
  - No longer part of form submission
  - Does NOT automatically show/hide DRG sections

### 2. **AI Analysis Button Renamed**
- **Previous**: "🧠 Analyze with AI" / "AI-Powered DRG Analysis"
- **New**: "🧠 AI Analysis"
- **Description Updated**: "Clean up ICD-10 codes and add VHA VERA complexity scoring with OpenAI GPT-4o"
- **Functionality**:
  - Refines ICD-10 code selection from NLP results
  - Adds VHA VERA complexity scoring (Levels 1-5)
  - Shows VHA Complexity column after analysis completes
  - Does NOT show DRG information

### 3. **DRG Column Hidden by Default**
- **Previous Behavior**: DRG section shown when inpatient checkbox was enabled
- **New Behavior**: 
  - DRG section **hidden by default**
  - Revealed only by clicking "📊 Show DRG Classifications" button
  - Button located in "Additional Options" section at bottom
  - Button toggles to "📊 Hide DRG Classifications" when active

### 4. **VHA Complexity Column**
- **Behavior**: Unchanged
- Still hidden by default
- Appears automatically after "🧠 AI Analysis" completes
- Shows VHA VERA complexity levels with color coding:
  - **Level 5/4**: 🔴 Red (Extremely High/Very High)
  - **Level 3**: 🟠 Orange (High)
  - **Level 1/2**: 🟢 Green (Low/Moderate)

---

## New UI Flow

### Initial State
```
1. Clinical Note Textarea
2. Extract Codes Button
3. [Results appear after extraction]
4. → AI Analysis Button (Step 2)
5. → Additional Options (Bottom):
   - [ ] Inpatient Mode (unchecked)
   - [Show DRG Classifications] button
```

### After "Extract Codes"
```
✅ Results Table Shown
   - ICD-10, SNOMED, Similarity, Semantic Types, CUI, Term
   - VHA Complexity column HIDDEN

🤖 AI Analysis button visible and active
📊 DRG section still HIDDEN
```

### After "AI Analysis"
```
✅ VHA Complexity column appears
✅ ICD-10 codes refined
✅ AI recommendations displayed
📊 DRG section still HIDDEN (unless button clicked)
```

### After "Show DRG Classifications"
```
✅ DRG section expands below the table
✅ Shows DRG codes with complexity indicators
✅ Button changes to "Hide DRG Classifications"
```

---

## Technical Details

### Files Modified
- `/app/templates/index.html`: UI layout, button placement, JavaScript handlers

### JavaScript Changes
1. **Removed**: Automatic DRG section showing based on inpatient toggle
2. **Added**: `showDrgBtn` click handler to toggle DRG section visibility
3. **Modified**: Inpatient toggle now only controls badge display (no form submission)
4. **Simplified**: Removed localStorage persistence for inpatient preference

### Form Changes
- Inpatient checkbox removed from form (now standalone UI element)
- Form only submits clinical text for NLP extraction
- No DRG processing during initial extraction

---

## User Benefits

1. **Clearer Workflow**: Two-step process is more explicit (NLP → AI)
2. **Focused Analysis**: AI Analysis focuses on ICD-10 refinement and VHA complexity
3. **On-Demand DRG**: DRG information available only when needed
4. **Default to Outpatient**: Most common use case (outpatient) is the default
5. **Reduced Clutter**: DRG section hidden unless explicitly requested

---

## Testing Checklist

- [x] Application starts successfully
- [ ] Extract Codes works (NLP only)
- [ ] AI Analysis button appears after extraction
- [ ] AI Analysis adds VHA Complexity column
- [ ] Inpatient checkbox is unchecked by default
- [ ] Inpatient checkbox shows badge when checked
- [ ] DRG section hidden by default
- [ ] "Show DRG Classifications" button reveals DRG section
- [ ] Button toggles to "Hide" when DRG section is visible
- [ ] VHA Complexity shows correct color coding (Level 1-5)

---

## Access

Application running at: **http://localhost:5000**

Container: `medicode-web-1`

Rebuild command:
```bash
cd "/media/frasod/4T NVMe/Code_Projects/Medicode"
docker compose down
docker compose up --build -d
```
