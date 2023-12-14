import os
import subprocess
import sys

APP = os.environ.get('APP', 'miqa-demo')

for env_var, var_name in [('CLOUDAMQP_URL', 'cloudamqp_url'), ('DATABASE_URL', 'database_url')]:
    result = subprocess.run(
        ['heroku', 'run', '-a', APP, 'echo', f'${env_var}'],
        capture_output=True
    )
    plaintext = result.stdout.decode().strip()
    print(f'{env_var}={plaintext}')

    subprocess.run(
        [
            'ansible-vault', 'encrypt_string',
            '--vault-password-file=vault-password',
            plaintext,
            '--name',
            var_name,
        ],
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
