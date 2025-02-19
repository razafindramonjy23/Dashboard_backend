import random
import string
from django.core.mail import send_mail
from django.conf import settings

def generate_verification_token(length=32):
    """Génère un token aléatoire pour la vérification de l'email"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def send_verification_email(user, verification_url):
    """Envoie l'email de vérification avec le lien généré"""
    subject = "Vérification de votre adresse email"
    message = f"Bonjour {user.username},\n\nVeuillez vérifier votre email en cliquant sur le lien suivant :\n{verification_url}\n\nMerci."
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user.email]
    
    send_mail(subject, message, from_email, recipient_list)
