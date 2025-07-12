from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.validators import DataRequired

class ClinicalNoteForm(FlaskForm):
    clinical_note = TextAreaField('Clinical Note', validators=[DataRequired()])
    submit = SubmitField('Extract Codes')