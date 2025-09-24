from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField, BooleanField
from wtforms.validators import DataRequired

class ClinicalNoteForm(FlaskForm):
    clinical_note = TextAreaField('Clinical Note', validators=[DataRequired()])
    inpatient = BooleanField('Inpatient Encounter (enable DRG mapping)')
    submit = SubmitField('Extract Codes')
    
    # Temporarily disable CSRF for debugging
    class Meta:
        csrf = False