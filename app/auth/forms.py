from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from app.models import User


class LoginForm(FlaskForm):
    """Login form."""
    email = StringField('Email', validators=[
        DataRequired(message='Email è richiesta'),
        Email(message='Inserisci un email valido')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password è richiesta')
    ])
    remember_me = BooleanField('Ricordami')
    submit = SubmitField('Accedi')


class RegistrationForm(FlaskForm):
    """Registration form."""
    email = StringField('Email', validators=[
        DataRequired(message='Email è richiesta'),
        Email(message='Inserisci un email valido')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password è richiesta'),
        Length(min=8, message='Password deve essere di almeno 8 caratteri')
    ])
    password2 = PasswordField('Conferma Password', validators=[
        DataRequired(message='Conferma password è richiesta'),
        EqualTo('password', message='Le password non corrispondono')
    ])
    submit = SubmitField('Registrati')

    def validate_email(self, email):
        """Check if email already exists."""
        user = User.query.filter_by(email=email.data.lower()).first()
        if user:
            raise ValidationError('Questo email è già registrato.')


class ForgotPasswordForm(FlaskForm):
    """Forgot password form."""
    email = StringField('Email', validators=[
        DataRequired(message='Email è richiesta'),
        Email(message='Inserisci un email valido')
    ])
    submit = SubmitField('Invia link di reset')


class ResetPasswordForm(FlaskForm):
    """Reset password form."""
    password = PasswordField('Nuova Password', validators=[
        DataRequired(message='Password è richiesta'),
        Length(min=8, message='Password deve essere di almeno 8 caratteri')
    ])
    password2 = PasswordField('Conferma Nuova Password', validators=[
        DataRequired(message='Conferma password è richiesta'),
        EqualTo('password', message='Le password non corrispondono')
    ])
    submit = SubmitField('Reimposta Password')