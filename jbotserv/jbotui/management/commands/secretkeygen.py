from django.core.management.base import BaseCommand, CommandError
from django.utils.crypto import get_random_string
import os 

class Command(BaseCommand):
    help = 'Generates a new Secret Key'

    def handle(self, *args, **options):
        chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
        SECRET_KEY = get_random_string(50, chars)
        key_file = open('jbotserv/key.py', 'w')
        key_file.write("KEY = '" + SECRET_KEY + "'")
        key_file.close()
        self.stdout.write(self.style.SUCCESS('Generated Secret Key'))
