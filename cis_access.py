import requests
import json
import os
import argparse
from datetime import datetime, timedelta

# Basis-URL für die SecureSuite Member API
BASE_URL = "https://workbench.cisecurity.org/api/vendor/v1"
LICENSE_ENDPOINT = "/license"
TOKEN_FILE = "securesuite_token.json"
BENCHMARK_LIST = "available_benchmarks.json"


def lizenz_aus_datei_lesen(dateipfad):
    """
    Liest den SecureSuite-Lizenzschlüssel aus einer Datei (XML oder JSON).
    
    Args:
        dateipfad (str): Pfad zur Datei mit dem Lizenzschlüssel
        
    Returns:
        str: Der Lizenzschlüssel als String
        str: Der Content-Type ('application/xml' oder 'application/json')
    """
    try:
        with open(dateipfad, 'r') as datei:
            inhalt = datei.read()
            
        # Bestimmen des Content-Types basierend auf Dateiendung
        if dateipfad.lower().endswith('.xml'):
            content_type = 'application/xml'
        elif dateipfad.lower().endswith('.json'):
            content_type = 'application/json'
        else:
            # Versuchen, den Content-Type anhand des Inhalts zu bestimmen
            if inhalt.strip().startswith('<'):
                content_type = 'application/xml'
            elif inhalt.strip().startswith('{'):
                content_type = 'application/json'
            else:
                print("Warnung: Konnte Content-Type nicht bestimmen, verwende 'application/xml'")
                content_type = 'application/xml'
        
        return inhalt, content_type
    except FileNotFoundError:
        print(f"Fehler: Lizenzdatei wurde nicht gefunden unter {dateipfad}")
        return None, None
    except Exception as e:
        print(f"Fehler beim Lesen der Lizenzdatei: {e}")
        return None, None

def neues_token_abrufen(lizenzschluessel, content_type='application/xml'):
    """
    Erhält ein neues Token von der SecureSuite Member API durch Senden des Lizenzschlüssels.
    
    Args:
        lizenzschluessel (str): Der SecureSuite-Lizenzschlüssel
        content_type (str): Der Content-Type der Lizenz ('application/xml' oder 'application/json')
        
    Returns:
        dict: Ein Dictionary mit dem Token und seiner Ablaufzeit
    """
    url = BASE_URL + LICENSE_ENDPOINT
    
    try:
        response = requests.post(url, data=lizenzschluessel, headers={'Content-Type': content_type})
        
        # Überprüfen auf HTTP-Fehler
        if response.status_code != 200:
            print(f"Fehler: API antwortete mit Status-Code {response.status_code}")
            print(f"Antwort: {response.text}")
            return None
        
        # Versuchen, die Antwort als JSON zu parsen
        try:
            token_daten = response.json()
        except json.JSONDecodeError:
            print(f"Fehler: Die API-Antwort ist kein gültiges JSON. Antwort: {response.text}")
            return None
        
        if 'token' in token_daten:
            # Berechnung der Ablaufzeit (20 Minuten ab jetzt)
            ablaufzeit = datetime.now() + timedelta(minutes=20)
            
            token_info = {
                'token': token_daten['token'],
                'expires_at': ablaufzeit.timestamp()
            }
            
            # Token in Datei speichern
            token_speichern(token_info)
            
            return token_info
        else:
            print(f"Fehler: Kein Token in der Antwort gefunden. Antwort: {token_daten}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Fehler bei der Anfrage an die API: {e}")
        return None

def token_speichern(token_info):
    """
    Speichert die Token-Informationen in einer Datei.
    
    Args:
        token_info (dict): Dictionary mit dem Token und seiner Ablaufzeit
    """
    try:
        with open(TOKEN_FILE, 'w') as datei:
            json.dump(token_info, datei)
    except Exception as e:
        print(f"Warnung: Konnte Token nicht speichern: {e}")

def token_ueberpruefen(token):
    """
    Überprüft die Gültigkeit eines Tokens über den SecureSuite API-Endpunkt.
    
    Args:
        token (str): Das zu überprüfende API-Token
        
    Returns:
        bool: True wenn gültig, False wenn ungültig, None bei Überprüfungsfehlern
    """
    url = BASE_URL + "/token/check"
    headers = {"X-SecureSuite-Token": token}
    
    try:
        response = requests.get(url, headers=headers)
        
        # HTTP-Statuscode Analyse
        if response.status_code == 200:
            antwort = response.json()
            if 'status' in antwort and antwort['status'] == "Token Validation Check Successful.":
                return True
            return False
        elif response.status_code == 401:
            print("Fehler: Ungültiges oder abgelaufenes Token")
            return False
        else:
            print(f"Unerwarteter Statuscode: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Netzwerkfehler bei der Token-Überprüfung: {e}")
        return None
    except json.JSONDecodeError:
        print("Ungültiges JSON-Format in der Antwort")
        return None

def token_laden():
    """
    Lädt die Token-Informationen aus einer Datei.
    
    Returns:
        dict: Dictionary mit dem Token und seiner Ablaufzeit oder None, wenn nicht gefunden
    """
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as datei:
                return json.load(datei)
        return None
    except Exception as e:
        print(f"Warnung: Konnte Token nicht laden: {e}")
        return None

def ist_token_gueltig(token_info):
    """
    Kombinierte Gültigkeitsprüfung mit lokaler Zeitprüfung und Servervalidierung
    
    Args:
        token_info (dict): Gespeicherte Token-Informationen
        
    Returns:
        bool: True wenn sowohl lokal als auch serverseitig gültig
    """
    # Lokale Zeitprüfung
    if not token_info or 'expires_at' not in token_info:
        return False
        
    if datetime.now().timestamp() > token_info['expires_at'] - 30:
        return False
    
    # Serverseitige Validierung
    return token_ueberpruefen(token_info['token'])

def token_abrufen(lizenz_dateipfad=None, force_refresh=False):
    """
    Holt ein gültiges SecureSuite API-Token. Wenn ein gültiges zwischengespeichertes Token existiert,
    wird dieses verwendet. Andernfalls wird ein neues Token angefordert.
    
    Args:
        lizenz_dateipfad (str, optional): Pfad zur Datei mit dem Lizenzschlüssel
        force_refresh (bool, optional): Erzwingt das Anfordern eines neuen Tokens, auch wenn ein gültiges existiert
        
    Returns:
        str: Das Token als String oder None, wenn kein gültiges Token abgerufen werden konnte
    """
    # Prüfen, ob wir ein gültiges zwischengespeichertes Token haben
    if not force_refresh:
        token_info = token_laden()
        if token_info and ist_token_gueltig(token_info):
            print("Verwende zwischengespeichertes Token (gültig)")
            return token_info['token']
    
    # Wenn kein gültiges Token gefunden wurde oder Refresh erzwungen wird, holen wir ein neues
    if lizenz_dateipfad:
        lizenzschluessel, content_type = lizenz_aus_datei_lesen(lizenz_dateipfad)
        if lizenzschluessel and content_type:
            print(f"Fordere neues Token an mit Content-Type: {content_type}")
            token_info = neues_token_abrufen(lizenzschluessel, content_type)
            if token_info:
                return token_info['token']
    
    print("Fehler: Es konnte kein gültiges Token abgerufen werden")
    return None

def list_available_benchmarks(ausfuehrlich=False, token=None):
    """
    Ruft alle verfügbaren Benchmarks ab und verwendet dabei bei Bedarf ein Authentifizierungstoken.
    Response Element

    Description
    -----------
    workbenchId:

    The unique identifier for a benchmark per CIS WorkBench. This ID can be used in
    subsequent requests to download benchmark content.

    benchmarkTitle:

    The title of the published benchmark, e.g. “CIS Microsoft Windows 10 Enterprise
    Release 2004 Benchmark”.

    benchmarkVersion:

    The release version of the published benchmark, e.g. “1.3.0”.

    benchmarkStatus:

    The current benchmark status value and date it was applied.

    assessmentStatus:

    The benchmark assessment status value. Indicates whether the benchmark is
    Manual or Automated.

    availableFormats:

    A JSON array containing the available download formats, 
    such as “SCAP”, “YAML”, “JSON”, “XCCDFPLUSAE”, and/or “DATASTREAM”.

    profile:

    The available profile(s) for any given benchmark.

    platformId:

    The primary Common Platform Enumeration (CPE) for a given benchmark.

    assets:

    All assets relevant for a given benchmark including the assetName and
    assetCpe (asset specific Common Platform Enumeration (CPE)).

    benchmarksUrl:

    The path to the benchmark in WorkBench.

    ciscat:

    If the benchmark is supported for use with CIS-CAT Pro Assessor and the
    metadata is available, the applicable versions are listed here.

    """
    endpoint = "/benchmarks"
    url = BASE_URL + endpoint
    headers = {}
    speicherdatei = BENCHMARK_LIST
    
    # Token-Handling
    if token:
        headers["X-SecureSuite-Token"] = token
    else:
        # Automatischen Token-Abruf nur bei erforderlichen Endpunkten
        pass  # Dieser Endpunkt ist öffentlich und benötigt kein Token
    
    try:
        if ausfuehrlich:
            print(f"Starte Benchmark-Abruf von: {url}")
            
        response = requests.get(url, headers=headers)
        
        # HTTP-Statuscode Validierung
        if response.status_code != 200:
            print(f"Fehler: API antwortete mit Status-Code {response.status_code}")
            if ausfuehrlich:
                print(f"Antwortinhalt: {response.text[:500]}...")
            return False
                
        # JSON-Verarbeitung mit erweiterter Fehlerbehandlung
        try:
            benchmarks_daten = response.json()
            
            # Validierung der Antwortstruktur
            if 'Benchmarks' not in benchmarks_daten:
                print("Fehler: Ungültiges Antwortformat - 'Benchmarks' Feld fehlt")
                return False
                
        except json.JSONDecodeError as e:
            print(f"JSON Decode Fehler: {e}")
            if ausfuehrlich:
                print(f"Rohe Antwort: {response.text[:500]}...")
            return False
            
        # Speicherung der Daten mit Versionierung
        try:
            with open(speicherdatei, 'w', encoding='utf-8') as datei:
                json.dump(benchmarks_daten, datei, indent=2, ensure_ascii=False)
                
            if ausfuehrlich:
                print(f"Erfolgreich gespeichert: {speicherdatei}")
                print(f"Anzahl Benchmarks: {benchmarks_daten.get('Total number of results', 0)}")
                
            return True
            
        except IOError as e:
            print(f"Dateizugriffsfehler: {e}")
            return False
        except Exception as e:
            print(f"Unerwarteter Fehler beim Speichern: {e}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Netzwerkfehler: {e}")
        return False
    except Exception as e:
        print(f"Kritischer Fehler: {e}")
        return False
        
def handle_error(response):
    """Behandelt Authentifizierungsfehler mit automatischem Token-Refresh"""
    if response.status_code == 401:
        print("Token ungültig/abgelaufen - Versuche Token-Refresh...")
        new_token = token_abrufen(force_refresh=True)
        if new_token:
            return {'token': new_token, 'retry': True}
    return {'error': 'Permanent authentication failure'}

def get_benchmark_details(workbench_id, token):
    """Holt detaillierte Metadaten unter Verwendung des Member-Tokens"""
    print(token)
    
    url = BASE_URL + f"/benchmarks/{workbench_id}"
    headers = {"X-SecureSuite-Token": token}
    
    print(url, headers)
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 401:
            token_abrufen(force_refresh=True)
            return get_benchmark_details(workbench_id)
        # return response.json()
        print(response.json())
    except requests.exceptions.RequestException as e:
        print(f"Fehler bei der Anfrage: {e}")
        return None

def download_benchmark(workbench_id, token):
    """Holt detaillierte Metadaten unter Verwendung des Member-Tokens"""
    print(token)
    
    url = BASE_URL + f"/benchmarks/{workbench_id}/JSON"
    headers = {
        "X-SecureSuite-Token": token,
        "Accept": "application/zip"
    }
    
    print(url, headers)
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 401:
            token_abrufen(force_refresh=True)
            return get_benchmark_details(workbench_id)
        # return response.json()
        filename = f"benchmark_{workbench_id}_{datetime.now().strftime('%Y%m%d')}"+".zip"
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(filename)
        return filename
    except requests.exceptions.RequestException as e:
        print(f"Fehler bei der Anfrage: {e}")
        return None


def main():
    """
    Beispielverwendung der SecureSuite-Token-Funktionen.
    """
    
    # parse command line arguments, if --gettoken is provides it will get a new token
    # if --getbenchmarks is provided it will get the benchmarks list
    # if --download <benchmarkID> is provided it will download the benchmark with the given ID
    # if --getdetails <benchmarkID> is provided it will get the details of the benchmark with the given ID
    # if --help is provided it will show the help message
    parser = argparse.ArgumentParser(description="SecureSuite Token und Benchmark Management")
    parser.add_argument('--gettoken', action='store_true', help="Fordert ein neues Token an und überprüft damit die Validität der Lizenz")
    parser.add_argument('--getbenchmarks', action='store_true', help="Ruft die Liste der verfügbaren Benchmarks ab")
    parser.add_argument('--download', type=str, help="Lädt den Benchmark mit der angegebenen ID herunter")
    parser.add_argument('--getdetails', type=str, help="Ruft die Details des Benchmarks mit der angegebenen ID ab")
    args = parser.parse_args()
    
    # Pfad zu Ihrer Lizenzdatei (XML oder JSON)
    lizenz_dateipfad = "license.xml"
    
    # if --gettoken is provided get a new token
    if args.gettoken:
        # Token abrufen
        token = token_abrufen(lizenz_dateipfad)
        
        if token:
            print(f"Token erfolgreich abgerufen: {token}")
            print("Sie können dieses Token jetzt für authentifizierte API-Anfragen verwenden.")
            print("Das Token ist 20 Minuten gültig.")
        else:
            print("Fehler beim Abrufen eines gültigen Tokens.")
 
    # if --getbenchmarks is provided get the benchmarks list
    elif args.getbenchmarks:
        # Token abrufen
        token = token_abrufen(lizenz_dateipfad)
        
        if token:
            print(f"Token erfolgreich abgerufen: {token}")
            print("Sie können dieses Token jetzt für authentifizierte API-Anfragen verwenden.")
            print("Das Token ist 20 Minuten gültig.")
            # Benchmark-Liste abrufen (öffentlicher Endpunkt)
            list_available_benchmarks(ausfuehrlich=True, token=token)
            
        else:
            print("Fehler beim Abrufen eines gültigen Tokens.")
    elif args.getdetails:
        # Token abrufen
        token = token_abrufen(lizenz_dateipfad)
        
        if token:
            print(f"Token erfolgreich abgerufen: {token}")
            print("Sie können dieses Token jetzt für authentifizierte API-Anfragen verwenden.")
            print("Das Token ist 20 Minuten gültig.")
            # Benchmark-Details abrufen (öffentlicher Endpunkt)
            get_benchmark_details(args.getdetails, token)
            
        else:
            print("Fehler beim Abrufen eines gültigen Tokens.")
            
    elif args.download:
        # Token abrufen
        token = token_abrufen(lizenz_dateipfad)
        
        if token:
            print(f"Token erfolgreich abgerufen: {token}")
            print("Sie können dieses Token jetzt für authentifizierte API-Anfragen verwenden.")
            print("Das Token ist 20 Minuten gültig.")
            # Benchmark-Details abrufen (öffentlicher Endpunkt)
            download_benchmark(args.download, token)
            
        else:
            print("Fehler beim Abrufen eines gültigen Tokens.")


if __name__ == "__main__":
    main()
