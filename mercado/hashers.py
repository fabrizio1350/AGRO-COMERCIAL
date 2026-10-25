import hashlib
from django.contrib.auth.hashers import PBKDF2PasswordHasher


class TriplePBKDF2PasswordHasher(PBKDF2PasswordHasher):
    """
    Encripta / indexa la contraseña en 3 capas sucesivas (SHA-256 -> SHA-512 -> PBKDF2-SHA256)
    para blindar las credenciales almacenadas en la base de datos.
    """
    algorithm = "pbkdf2_triple_sha256"

    def _pre_hash_tres_capas(self, password, salt):
        capa1 = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
        capa2 = hashlib.sha512(f"{capa1}:{salt}".encode("utf-8")).hexdigest()
        return capa2

    def encode(self, password, salt, iterations=None):
        password_blindada = self._pre_hash_tres_capas(password, salt)
        return super().encode(password_blindada, salt, iterations)
