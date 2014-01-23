#-------------------------------------------------------------------------------
# Name:        forms
# Purpose:     Forms used in Colorado College's TIGER Catalog Web App
#
# Author:      Jeremy Nelson
#
# Created:     2014-01-22
# Copyright:   (c) Jeremy Nelson, Colorado College 2014
# Licence:     MIT
#-------------------------------------------------------------------------------


from flask_wtf import Form
from wtforms import TextField, SubmitField
from wtforms.validators import DataRequired

class BasicSearch(Form):
    "Provides Basic Search Form that is available on all views"
    query = TextField('query', validators=[DataRequired(),])
    go = SubmitField('Go')
