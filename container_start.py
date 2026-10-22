"""Start the CDS-only Streamlit app in the persistent data directory."""
import os
import sys
from settings import DATA_DIR


def main():
    email = os.getenv('NCBI_EMAIL', '').strip()
    if not email or email == 'your-email@example.com' or '@' not in email:
        raise SystemExit('.envのNCBI_EMAILに自分の連絡先メールアドレスを設定してください。')
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    os.chdir(DATA_DIR)
    os.execv(sys.executable, [sys.executable, '-m', 'streamlit', 'run', '/app/app.py',
                            '--server.address=0.0.0.0', '--server.port=8501',
                            '--server.headless=true', '--browser.gatherUsageStats=false'])


if __name__ == '__main__':
    main()
