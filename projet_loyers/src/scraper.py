import os
import time
import random
import pandas as pd
# Charger les variables d'environnement depuis .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Variables d'environnement chargées depuis .env")
except ImportError:
    print("python-dotenv non installé. Les variables d'environnement système seront utilisées.")
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import re
import json

# Configuration
# Utiliser des variables d'environnement pour les identifiants
# Peut être un email ou un numéro de téléphone
USERNAME = os.environ.get("FB_USERNAME", "")
EMAIL = os.environ.get("FB_EMAIL", "") 
PHONE = os.environ.get("FB_PHONE", "")
PASSWORD = os.environ.get("FB_PASSWORD", "")  # Ne jamais versionner ce mot de passe

# Utiliser le premier identifiant disponible (téléphone, email ou username)
LOGIN_ID = PHONE or EMAIL or USERNAME or "votre_identifiant"  # Fallback pour le développement

SEARCH_QUERY = "Location Antananarivo"
MAX_ANNOUNCEMENTS = 20
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'raw')
os.makedirs(OUTPUT_DIR, exist_ok=True)

def setup_driver():
    """Configure et retourne une instance de Chrome WebDriver"""
    chrome_options = Options()
    #chrome_options.add_argument("--headless")  # Décommentez pour le mode sans interface
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    
    # Chemins possibles vers Chrome
    chrome_paths = [
        os.environ.get("CHROME_PATH", "C:\Program Files\Google\Chrome\Application\chrome.exe"),  # Chemin personnalisé depuis les variables d'environnement
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Users\\%s\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe" % os.getenv("USERNAME"),
    ]
    
    # Trouver le premier chemin valide
    chrome_binary = next((path for path in chrome_paths if path and os.path.exists(path)), None)
    
    if chrome_binary:
        print(f"Utilisation de Chrome depuis: {chrome_binary}")
        chrome_options.binary_location = chrome_binary
    else:
        print("ATTENTION: Chrome non trouvé. Assurez-vous que Chrome est installé ou définissez CHROME_PATH.")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        print(f"Erreur lors de l'initialisation du WebDriver: {e}")
        print("\nSuggestions de dépannage:")
        print("1. Installez Google Chrome: https://www.google.com/chrome/")
        print("2. Définissez la variable d'environnement CHROME_PATH dans votre fichier .env")
        print("3. Vérifiez que ChromeDriver est compatible avec votre version de Chrome")
        raise

def login_facebook(driver, login_id, password):
    """Connecte l'utilisateur à Facebook avec email/téléphone/username"""
    print("Connexion à Facebook...")
    driver.get("https://www.facebook.com/")
    time.sleep(3)
    
    # Accepter les cookies si nécessaire
    try:
        accept_cookies = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(string(), 'Autoriser les cookies') or contains(string(), 'Accepter')]"))
        )
        accept_cookies.click()
        time.sleep(2)
    except Exception as e:
        print(f"Pas de popup de cookies ou erreur: {e}")
    
    # Remplir le formulaire de connexion
    try:
        email_field = driver.find_element(By.ID, "email")
        password_field = driver.find_element(By.ID, "pass")
        
        # Vérifier si les identifiants sont disponibles
        if not login_id or not password:
            raise ValueError("Identifiants Facebook manquants. Définissez FB_EMAIL/FB_PHONE/FB_USERNAME et FB_PASSWORD comme variables d'environnement.")
        
        email_field.send_keys(login_id)
        password_field.send_keys(password)
        password_field.send_keys(Keys.RETURN)
        time.sleep(5)
        
        # Vérifier si la connexion a réussi
        if "login" in driver.current_url.lower() or "connexion" in driver.current_url.lower():
            print("Échec de la connexion. Vérifiez vos identifiants.")
            return False
        return True
    except Exception as e:
        print(f"Erreur lors de la connexion: {e}")
        return False

def extract_announcement_data(announcement):
    """Extrait les données d'une annonce individuelle"""
    try:
        # Cliquer sur l'annonce pour ouvrir la vue détaillée
        announcement.click()
        time.sleep(2)
        
        # Attendre que la fenêtre modale s'ouvre
        time.sleep(3)
        
        # Extraire les informations de base
        data = {
            'titre': "Non spécifié",
            'quartier': "Non spécifié",
            'superficie': None,
            'nombre_chambres': None,
            'douche_wc': None,
            'type_d_acces': None,
            'meublé': None,
            'etat_general': None,
            'loyer_mensuel': None,
            'description': "Non spécifiée",
            'lien': driver.current_url,
            'date_extraction': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            # Titre
            title_elem = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//h1"))
            )
            data['titre'] = title_elem.text.strip()
        except:
            pass
            
        # Prix (loyer mensuel)
        try:
            price_elem = driver.find_element(By.XPATH, "//div[contains(@class, 'x1y332')]//span[contains(text(), 'MGA')]")
            price_text = price_elem.text
            data['loyer_mensuel'] = int(re.sub(r'[^\d]', '', price_text))
        except:
            pass
            
        # Localisation (quartier)
        try:
            location_elems = driver.find_elements(By.XPATH, "//span[contains(@class, 'x1lliihq')]")
            for elem in location_elems:
                text = elem.text.strip()
                if any(q.lower() in text.lower() for q in ['analakely', 'isoraka', 'andraharo', 'ankadifotsy', 'ankadikely']):
                    data['quartier'] = text
                    break
        except:
            pass
            
        # Description complète
        try:
            desc_elem = driver.find_element(By.XPATH, "//div[contains(@class, 'xz9dl7a')]")
            description = desc_elem.text.lower()
            data['description'] = description
            
            # Extraire les informations spécifiques de la description
            # Surface
            surface_match = re.search(r'(\d+)\s*(?:m²|m2|m\s*2)', description)
            if surface_match:
                data['superficie'] = int(surface_match.group(1))
                
            # Nombre de chambres
            chambres_match = re.search(r'(\d+)\s*(?:chambre|chbr|ch|chb)', description)
            if chambres_match:
                data['nombre_chambres'] = int(chambres_match.group(1))
                
            # Douche/WC
            if 'salle de bain' in description or 'sdb' in description:
                data['douche_wc'] = 'interieur' if any(x in description for x in ['intérieur', 'int.']) else 'exterieur'
                
            # Type d'accès
            if 'parking' in description:
                data['type_d_acces'] = 'voiture_avec_par_parking'
            elif 'voiture' in description:
                data['type_d_acces'] = 'voiture'
            elif 'moto' in description:
                data['type_d_acces'] = 'moto'
            else:
                data['type_d_acces'] = 'sans'
                
            # Meublé
            data['meublé'] = 'oui' if any(x in description for x in ['meublé', 'meuble', 'fourni']) else 'non'
            
            # État général
            if any(x in description for x in ['neuf', 'nouveau', 'neuve']):
                data['etat_general'] = 'bon'
            elif any(x in description for x in ['bon état', 'bon etat', 'bien entretenu']):
                data['etat_general'] = 'bon'
            elif any(x in description for x in ['moyen', 'moyenne']):
                data['etat_general'] = 'moyen'
            elif any(x in description for x in ['mauvais', 'à rénover', 'a renover']):
                data['etat_general'] = 'mauvais'
                
        except Exception as e:
            print(f"Erreur lors de l'extraction des détails: {e}")
            
        # Fermer la fenêtre modale
        try:
            close_btn = driver.find_element(By.XPATH, "//div[@aria-label='Fermer']")
            close_btn.click()
            time.sleep(1)
        except:
            pass
            
        return data
        
    except Exception as e:
        print(f"Erreur lors de l'extraction de l'annonce: {e}")
        return None

def scrape_facebook_marketplace(search_query, max_announcements=20):
    """Fonction principale de scraping pour Facebook Marketplace"""
    print("Démarrage du scraping Facebook Marketplace...")
    driver = setup_driver()
    announcements_data = []
    
    try:
        # Connexion
        login_success = login_facebook(driver, LOGIN_ID, PASSWORD)
        if not login_success:
            print("Impossible de se connecter à Facebook. Vérifiez vos identifiants.")
            return pd.DataFrame()
        time.sleep(5)

        # Accès à Marketplace
        print("Accès à Marketplace...")
        try:
            driver.get("https://www.facebook.com/marketplace/")
            time.sleep(5)
        except Exception as e:
            print(f"Erreur lors de l'accès à Marketplace: {e}")
            return pd.DataFrame()

        # Recherche
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Rechercher sur Marketplace']"))
        )
        search_box.send_keys(search_query)
        search_box.send_keys(Keys.RETURN)
        time.sleep(5)

        # Filtrer pour les locations
        try:
            filter_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Filtres')]"))
            )
            filter_btn.click()
            time.sleep(2)

            # Sélectionner "Location"
            location_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Location')]"))
            )
            location_btn.click()
            time.sleep(2)

            # Appuyer sur le bouton Appliquer
            apply_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Appliquer')]"))
            )
            apply_btn.click()
            time.sleep(5)
        except Exception as e:
            print(f"Impossible d'appliquer les filtres: {e}")

        # Faire défiler pour charger plus d'annonces
        print("Chargement des annonces...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scroll_attempts = 10

        while len(announcements_data) < max_announcements and scroll_attempts < max_scroll_attempts:
            # Faire défiler vers le bas
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)  # Attendre le chargement

            # Récupérer les annonces visibles
            announcements = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//a[contains(@href, '/marketplace/item/')]"))
            )

            # Parcourir les annonces
            for ann in announcements:
                if len(announcements_data) >= max_announcements:
                    break

                try:
                    ann_data = extract_announcement_data(driver, ann)
                    if ann_data:
                        announcements_data.append(ann_data)
                        print(f"Annonce {len(announcements_data)}/{max_announcements} extraite")
                    
                    # Pause aléatoire plus longue pour éviter les blocages
                    time.sleep(random.uniform(2, 4))
                except Exception as e:
                    print(f"Erreur lors de l'extraction d'une annonce: {e}")
                    # Essayer de fermer toute modale qui pourrait être ouverte
                    try:
                        webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                        time.sleep(1)
                    except:
                        pass
                    continue
                    
            # Vérifier si on a atteint le bas de la page
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                scroll_attempts += 1
            last_height = new_height
                
    except Exception as e:
        print(f"Une erreur est survenue: {e}")
    finally:
        driver.quit()
    
    return pd.DataFrame(announcements_data)

def save_to_csv(df, filename='donnees_facebook_marketplace.csv'):
    """Sauvegarde les données dans un fichier CSV"""
    # Créer le dossier de sortie s'il n'existe pas
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Ajouter un timestamp au nom du fichier
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename_with_timestamp = f"facebook_marketplace_{timestamp}.csv"
    filepath = os.path.join(OUTPUT_DIR, filename_with_timestamp)
    
    # Sélectionner uniquement les colonnes demandées
    columns = [
        'quartier', 'superficie', 'nombre_chambres', 'douche_wc',
        'type_d_acces', 'meublé', 'etat_general', 'loyer_mensuel'
    ]
    
    # Créer un nouveau DataFrame avec uniquement les colonnes demandées
    df_filtered = pd.DataFrame()
    for col in columns:
        if col in df.columns:
            df_filtered[col] = df[col]
        else:
            df_filtered[col] = None
    
    # Sauvegarder en CSV
    df_filtered.to_csv(filepath, index=False, encoding='utf-8-sig')
    print(f"\nDonnées sauvegardées dans {filepath}")
    return filepath

if __name__ == "__main__":
    print("Démarrage du scraping Facebook Marketplace...")
    
    # Vérifier si les identifiants sont définis
    if not LOGIN_ID or not PASSWORD:
        print("\nATTENTION: Identifiants Facebook non définis!")
        print("Définissez les variables d'environnement suivantes avant d'exécuter le script:")
        print("  - FB_EMAIL ou FB_PHONE ou FB_USERNAME: Votre identifiant Facebook")
        print("  - FB_PASSWORD: Votre mot de passe Facebook")
        print("\nExemple sous Windows:")
        print("  set FB_EMAIL=votre_email@example.com")
        print("  set FB_PASSWORD=votre_mot_de_passe")
        print("\nExemple sous Linux/Mac:")
        print("  export FB_EMAIL=votre_email@example.com")
        print("  export FB_PASSWORD=votre_mot_de_passe")
        print("\nContinuation avec les valeurs par défaut pour le développement...")
    
    df_annonces = scrape_facebook_marketplace(SEARCH_QUERY, MAX_ANNOUNCEMENTS)
    
    if not df_annonces.empty:
        print("\nRésumé des données collectées :")
        print(f"Nombre d'annonces : {len(df_annonces)}")
        print("\nAperçu des données :")
        
        # Afficher un aperçu des colonnes importantes
        preview_cols = ['quartier', 'superficie', 'nombre_chambres', 'loyer_mensuel']
        available_cols = [col for col in preview_cols if col in df_annonces.columns]
        if available_cols:
            print(df_annonces[available_cols].head())
        
        # Nettoyage basique des données
        # Convertir les types de données appropriés
        if 'superficie' in df_annonces.columns:
            df_annonces['superficie'] = pd.to_numeric(df_annonces['superficie'], errors='coerce')
        
        if 'nombre_chambres' in df_annonces.columns:
            df_annonces['nombre_chambres'] = pd.to_numeric(df_annonces['nombre_chambres'], errors='coerce')
        
        if 'loyer_mensuel' in df_annonces.columns:
            df_annonces['loyer_mensuel'] = pd.to_numeric(df_annonces['loyer_mensuel'], errors='coerce')
        
        # Sauvegarder les données
        save_to_csv(df_annonces)
        
        print("\nStatistiques des données collectées :")
        numeric_cols = ['superficie', 'nombre_chambres', 'loyer_mensuel']
        available_numeric = [col for col in numeric_cols if col in df_annonces.columns]
        if available_numeric:
            print(df_annonces[available_numeric].describe())
            
        print("\nRépartition par quartier :")
        if 'quartier' in df_annonces.columns:
            print(df_annonces['quartier'].value_counts())
            
        print("\nScraping terminé avec succès!")
    else:
        print("Aucune donnée n'a pu être collectée. Vérifiez les identifiants ou les paramètres de recherche.")