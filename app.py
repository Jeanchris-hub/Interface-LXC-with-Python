from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, login_required, login_user, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from modules.auth import login_manager, login_user_admin, logout_user_admin
from modules.contenaires import get_all_containers, create_new_container, stop_the_container, start_the_container, delete_the_container,get_available_images, get_container_details
from flask import flash,  jsonify
from pylxd import Client
from datetime import datetime
from dateutil import parser
import pylxd
from flask_socketio import SocketIO, emit


app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Initialisation de Flask-Login
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."

# Simuler des utilisateurs avec des mots de passe hachés
users = {
    'admin': {'password': generate_password_hash('password')}
}

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Vérifie si l'utilisateur existe et si le mot de passe est correct
        if username in users and check_password_hash(users[username]['password'], password):
            login_user_admin()
            return redirect(url_for('admin_dashboard'))
        else:
            # Si les identifiants sont invalides, afficher un message d'erreur
            return render_template('login.html', error="Identifiants invalides")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user_admin()
    return redirect(url_for('login'))

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    """Route pour le tableau de bord admin (création de conteneurs et gestion d'images)."""
    container_data = get_all_containers()  # Get the list of containers
    images = get_available_images()  # Get the available images

    # Handle creating a new container if the form is submitted
    if request.method == 'POST':
        selected_image = request.form['image']  # Image selected in the form
        container_name = request.form['name']
        cpu_limit = request.form['cpu_limit']
        memory_limit = request.form['memory_limit']
        
        create_new_container(container_name, selected_image, cpu_limit, memory_limit)
        return redirect(url_for('admin_dashboard'))  # Redirect to the dashboard after creation

    # Return the admin dashboard template with container and image data
    return render_template('index.html', data=container_data, images=images)


@app.route('/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    """Route pour ajouter un nouvel utilisateur"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Vérifie si l'utilisateur existe déjà
        if username in users:
            return render_template('add_user.html', error="L'utilisateur existe déjà.")
        
        # Hache le mot de passe avant de l'ajouter
        users[username] = {'password': generate_password_hash(password)}
        return redirect(url_for('admin_dashboard'))
    
    return render_template('add_user.html')

@app.route('/create_container', methods=['GET', 'POST'])
@login_required
def create_container():
    """Route pour créer un conteneur"""
    if request.method == 'POST':
        # Récupérer les données envoyées depuis le formulaire
        container_name = request.form.get('name')
        container_image = request.form.get('image')
        cpu_limit = request.form.get('cpu_limit')
        memory_limit = request.form.get('memory_limit')
        
        # Appeler la fonction pour créer un nouveau conteneur
        create_new_container(container_name, container_image, cpu_limit, memory_limit)
        return redirect(url_for('admin_dashboard'))  # Redirige vers le tableau de bord après création
    
    return render_template('index.html.html')  # Page de création du conteneur



@app.route('/stop_container/<container_name>', methods=['POST'])
@login_required
def stop_container(container_name):
    stop_the_container(container_name)
    return redirect(url_for('admin_dashboard'))

@app.route('/start_container/<container_name>', methods=['POST'])
@login_required
def start_container(container_name):
    start_the_container(container_name)
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_container/<container_name>', methods=['POST'])
@login_required
def delete_container(container_name):
    delete_the_container(container_name)
    return redirect(url_for('admin_dashboard'))





###################details conteneur##########################################

@app.route('/container/<container_name>', methods=['GET'])
@login_required
def container_details(container_name):
    try:
        print(f"Accès aux détails pour : {container_name}")  # Log pour vérifier l'entrée
        details = get_container_details(container_name)
        return render_template('container_details.html', container=details)
    except Exception as e:
        flash(f"Erreur : {e}", 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/api/container/<container_name>', methods=['GET'])
@login_required
def api_container_details(container_name):
    try:
        details = get_container_details(container_name)
        return jsonify(details)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


###################IMAGES##########################################
@app.route('/images', methods=['GET'])
@login_required
def images_dashboard():
    """Route pour afficher les images disponibles dans LXD."""
    available_images = get_available_images()  # Retrieve available images
    return render_template('images_dashboard.html', images=available_images)
    
###################SNAPSHOT##########################################
lxd_client = Client()
@app.route('/snapshots/<container_name>', methods=['GET', 'POST'])
def snapshots(container_name):
    container = lxd_client.containers.get(container_name)
    if request.method == 'POST':
        # Handle snapshot creation
        snapshot_name = request.form.get('snapshot_name')
        if snapshot_name:
            container.snapshots.create(name=snapshot_name)
            flash(f"Snapshot '{snapshot_name}' created successfully!", 'success')
        return redirect(url_for('snapshots', container_name=container_name))
    
    snapshots = [
        {
            'name': snapshot.name,
            'created_at': parser.parse(snapshot.created_at)
            if hasattr(snapshot, 'created_at') else None
        }
        for snapshot in container.snapshots.all()
    ]
    return render_template('snapshots.html', container=container, snapshots=snapshots)


@app.route('/snapshots/restore/<container_name>/<snapshot_name>', methods=['POST'])
def restore_snapshot(container_name, snapshot_name):
    container = lxd_client.containers.get(container_name)
    snapshot = container.snapshots.get(snapshot_name)
    snapshot.restore()
    flash(f"Snapshot '{snapshot_name}' restored successfully!", 'success')
    return redirect(url_for('snapshots', container_name=container_name))

@app.route('/snapshots/delete/<container_name>/<snapshot_name>', methods=['POST'])
def delete_snapshot(container_name, snapshot_name):
    container = lxd_client.containers.get(container_name)
    snapshot = container.snapshots.get(snapshot_name)
    snapshot.delete()
    flash(f"Snapshot '{snapshot_name}' deleted successfully!", 'success')
    return redirect(url_for('snapshots', container_name=container_name))


# Les autres routes restent inchangées

if __name__ == '__main__':
    app.run(debug=True)
