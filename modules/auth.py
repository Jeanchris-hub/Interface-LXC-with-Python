# modules/auth.py
from flask_login import LoginManager, UserMixin, login_user, logout_user

login_manager = LoginManager()

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

def login_user_admin(user_id='admin'):
    user = User(id=user_id)
    login_user(user)

def logout_user_admin():
    logout_user()
