#contenaires.py
import pylxd
from datetime import datetime
from dateutil import parser
# Connexion au client LXD
try:
    client = pylxd.Client()
except Exception as e:
    raise RuntimeError("Impossible de se connecter au client LXD : {0}".format(e))


def get_all_containers():
    """Récupérer tous les conteneurs avec leurs états, IP et snapshots."""
    try:
        containers = client.containers.all()
        container_data = []
        
        for container in containers:
            container_state = container.state()  # Obtenir l'état du conteneur
            networks = container_state.network

            ipv4 = ipv6 = "N/A"
            if networks and 'eth0' in networks:
                addresses = networks['eth0'].get('addresses', [])
                for address in addresses:
                    if address.get('family') == 'inet':  # IPv4
                        ipv4 = address.get('address', "N/A")
                    elif address.get('family') == 'inet6':  # IPv6
                        ipv6 = address.get('address', "N/A")

            snapshots = container.snapshots.all()  # Récupérer les snapshots du conteneur
            snapshot_count = len(snapshots)  # Nombre de snapshots

            container_data.append({
                "name": container.name,
                "state": container_state.status,
                "ipv4": ipv4,
                "ipv6": ipv6,
                "snapshot": snapshot_count
            })

        return container_data
    except Exception as e:
        print(f"Erreur lors de la récupération des conteneurs : {e}")
        return []


def create_new_container(name, image, cpu_limit=None, memory_limit=None):
    try:
        container_config = {
            "name": name,
            "source": {"type": "image", "alias": image},
            "config": {}
        }
        if cpu_limit:
            container_config['config']['limits.cpu'] = str(cpu_limit)
        if memory_limit:
            container_config['config']['limits.memory'] = memory_limit

        container = client.containers.create(container_config, wait=True)
        return container
    except pylxd.exceptions.LXDAPIException as e:
        return {"error": f"Erreur LXD : {e}"}
    except Exception as e:
        return {"error": f"Erreur inconnue : {e}"}



def stop_the_container(container_name):
    """Arrêter un conteneur."""
    try:
        container = client.containers.get(container_name)
        if container.status == "Running":
            container.stop(wait=True)
        else:
            print(f"Le conteneur '{container_name}' est déjà arrêté.")
    except pylxd.exceptions.NotFound:
        print(f"Conteneur '{container_name}' introuvable.")
    except Exception as e:
        print(f"Erreur lors de l'arrêt du conteneur '{container_name}' : {e}")


def start_the_container(container_name):
    """Démarrer un conteneur."""
    try:
        container = client.containers.get(container_name)
        if container.status == "Stopped":
            container.start(wait=True)
        else:
            print(f"Le conteneur '{container_name}' est déjà démarré.")
    except pylxd.exceptions.NotFound:
        print(f"Conteneur '{container_name}' introuvable.")
    except Exception as e:
        print(f"Erreur lors du démarrage du conteneur '{container_name}' : {e}")


def delete_the_container(container_name):
    """Supprimer un conteneur."""
    try:
        container = client.containers.get(container_name)
        if container.status == "Running":
            container.stop(wait=True)  # Arrêter le conteneur avant de le supprimer
        container.delete(wait=True)
        print(f"Conteneur '{container_name}' supprimé avec succès.")
    except pylxd.exceptions.NotFound:
        print(f"Conteneur '{container_name}' introuvable.")
    except Exception as e:
        print(f"Erreur lors de la suppression du conteneur '{container_name}' : {e}")



def human_readable_size(byte_size):
    """Convert bytes to a human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if byte_size < 1024.0:
            return f"{byte_size:.2f} {unit}"
        byte_size /= 1024.0
    return f"{byte_size:.2f} PB"

def get_available_images():
    """Récupérer les images disponibles dans LXD."""
    try:
        # Récupérer toutes les images disponibles
        images = client.images.all()
        if not images:
            print("Aucune image disponible.")  # Ajouter un print pour le débogage

        available_images = []
        for img in images:
            # Récupérer l'alias
            alias = img.aliases[0]['name'] if img.aliases else "No alias"
            
            # Récupérer la description détaillée, l'architecture et autres infos
            description = getattr(img, 'description', None)
            architecture = getattr(img, 'architecture', 'Unknown')
            fingerprint = getattr(img, 'fingerprint', 'No fingerprint')
            image_type = getattr(img, 'type', None)  # Check type here
            size = getattr(img, 'size', 'Unknown size')

            # If no type is found, set it to "CONTAINER" or another default
            if image_type is None:
                image_type = "CONTAINER"  # Set a default type, e.g., "CONTAINER" or "VM"
            
            # Convertir la taille en format lisible (en MB ou GB)
            size = human_readable_size(size)

            # Formater la description en utilisant l'alias et la description détaillée
            if description is None or description == 'No description':
                description = f"{alias} | {architecture}"

            detailed_description = f"{description}"

            # Récupérer et formater la date de téléchargement
            upload_date = getattr(img, 'uploaded_at', None)
            if upload_date:
                try:
                    # Utiliser dateutil.parser pour analyser la date ISO 8601
                    upload_date = parser.parse(upload_date)
                    # Formater la date dans un format plus lisible
                    upload_date = upload_date.strftime('%b %d, %Y at %I:%M%p (UTC)')
                except ValueError:
                    upload_date = 'Invalid date format'
            else:
                upload_date = 'Unknown date'

            # Ajouter toutes les informations dans la liste
            available_images.append({
                "alias": alias,
                "fingerprint": fingerprint,
                "public": "no",  # Assuming no images are public
                "description": detailed_description,
                "architecture": architecture,
                "type": image_type,
                "size": size,
                "upload_date": upload_date
            })

        return available_images

    except Exception as e:
        print(f"Erreur lors de la récupération des images : {e}")
        return []




# Récupérer les détails d'un conteneur
def get_container_details(container_name):
    try:
        container = client.containers.get(container_name)
        state = container.state()

        # Vérification de l'existence des données du CPU
        cpu_usage_ns = state.cpu.get('usage', 0)  # Utilisation CPU en nanosecondes
        cpu_count = state.cpu.get('total', 1)  # Nombre total de cœurs CPU (au moins 1 pour éviter la division par zéro)
        cpu_usage_percent = (cpu_usage_ns / (cpu_count * 1e9)) * 100 if cpu_count else 0  # Utilisation CPU en %

        # Vérification de l'existence des données de la mémoire
        memory_usage = state.memory.get('usage', 0)  # Mémoire utilisée en octets
        memory_total = state.memory.get('total', 1)  # Mémoire totale en octets (au moins 1 pour éviter la division par zéro)
        memory_usage_percent = (memory_usage / memory_total) * 100 if memory_total else 0  # Utilisation mémoire en %

        # Récupération des adresses IP (en prenant eth0 comme interface par défaut)
        network_info = state.network.get('eth0', {}).get('addresses', [])
        ipv4 = next((addr['address'] for addr in network_info if addr['family'] == 'inet'), "N/A")
        ipv6 = next((addr['address'] for addr in network_info if addr['family'] == 'inet6'), "N/A")

        # Construction de l'objet de retour
        details = {
            "name": container.name,
            "status": container.status.capitalize(),
            "cpu_usage_percent": round(cpu_usage_percent, 2),
            "memory_usage_percent": round(memory_usage_percent, 2),
            "ipv4": ipv4,
            "ipv6": ipv6
        }
        return details
    except pylxd.exceptions.LXDAPIException as e:
        raise Exception(f"Erreur lors de l'accès au conteneur LXD : {str(e)}")
    except AttributeError as e:
        raise Exception(f"Attribut manquant ou mal formé dans l'état du conteneur : {str(e)}")
    except KeyError as e:
        raise Exception(f"Clé manquante dans l'état du conteneur : {str(e)}")
    except Exception as e:
        raise Exception(f"Erreur lors de la récupération des détails du conteneur : {str(e)}")

   


