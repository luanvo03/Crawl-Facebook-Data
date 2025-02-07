import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import base64

class SecureConfig:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Initialize encryption key
        self._init_encryption()
        
    def _init_encryption(self):
        # Generate or load encryption key
        key_file = ".secret.key"
        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                self.key = f.read()
        else:
            self.key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(self.key)
        
        self.cipher_suite = Fernet(self.key)
    
    def get_credentials(self):
        """Get decrypted credentials"""
        email = os.getenv('FB_EMAIL')
        password = os.getenv('FB_PASSWORD')
        
        if not email or not password:
            raise ValueError("Missing credentials in .env file")
            
        return {
            'email': email,
            'password': password
        }
    
    def encrypt_text(self, text):
        """Encrypt sensitive text"""
        return self.cipher_suite.encrypt(text.encode()).decode()
    
    def decrypt_text(self, encrypted_text):
        """Decrypt sensitive text"""
        return self.cipher_suite.decrypt(encrypted_text.encode()).decode()
