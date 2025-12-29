from setuptools import setup, find_packages

setup(
    name="ateker_voices",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'Flask==2.3.3',
        'Flask-Migrate==4.0.5',
        'Flask-SQLAlchemy==3.0.3',
        'Flask-Login==0.6.2',
        'Flask-WTF==1.1.1',
        'gunicorn==21.2.0',
        'Werkzeug==2.3.7',
        'email-validator==2.0.0.post2',
        'python-dotenv==1.0.0',
        'Pillow==10.0.0',
        'pandas==2.0.3',
        'python-multipart==0.0.6',
    ],
)
