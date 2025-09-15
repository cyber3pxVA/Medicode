def export_to_csv(data, filename):
    """Export list[dict] to CSV with ICD-10 columns before SNOMED columns where possible.

    If standard keys are present, enforce order:
    [cui, term, similarity|rag_relevance, semtypes, icd10_codes, snomed_codes, *rest]
    """
    import csv

    if not data:
        return

    # Determine canonical key order
    first = data[0]
    keys = list(first.keys())
    # Map possible score field
    score_field = 'rag_relevance' if 'rag_relevance' in first else ('similarity' if 'similarity' in first else None)
    preferred_order = ['cui', 'term']
    if score_field:
        preferred_order.append(score_field)
    preferred_order.extend(['semtypes', 'icd10_codes', 'snomed_codes'])
    # Append any remaining keys preserving their original order
    remaining = [k for k in keys if k not in preferred_order]
    final_header = preferred_order + remaining

    with open(filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=final_header)
        writer.writeheader()
        for row in data:
            writer.writerow(row)


def export_to_json(data, filename):
    """Export list[dict] to JSON ensuring ICD-10 precedes SNOMED inside each object if both present.

    We rebuild each dict with desired ordering for readability (though JSON objects are unordered by spec).
    """
    import json
    if not data:
        with open(filename, 'w') as file:
            json.dump([], file, indent=4)
        return

    reordered = []
    for item in data:
        score_field = 'rag_relevance' if 'rag_relevance' in item else ('similarity' if 'similarity' in item else None)
        ordered = {}
        for key in ['cui', 'term']:
            if key in item: ordered[key] = item[key]
        if score_field:
            ordered[score_field] = item[score_field]
        for key in ['semtypes', 'icd10_codes', 'snomed_codes']:
            if key in item: ordered[key] = item[key]
        # Add any remaining keys
        for k, v in item.items():
            if k not in ordered:
                ordered[k] = v
        reordered.append(ordered)

    with open(filename, 'w') as file:
        json.dump(reordered, file, indent=4)