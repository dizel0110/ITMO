import os
import base64

new_key = base64.urlsafe_b64encode(os.urandom(32))
print(new_key.decode())  # noqa T201
