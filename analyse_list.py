import json

def analyse_benchmarks(dateiname):
    """
    Analysiert die Benchmark-Datei und erstellt eine Tabelle mit den wichtigsten Informationen.
    
    Args:
        dateiname (str): Pfad zur JSON-Datei mit den Benchmark-Daten
    
    Returns:
        bool: True bei Erfolg, False bei Fehlern
    """
    try:
        # Benchmark-Daten aus Datei laden
        with open(dateiname, 'r', encoding='utf-8') as datei:
            benchmarks_daten = json.load(datei)
        
        # Überprüfen, ob die erforderliche Struktur vorhanden ist
        if 'Benchmarks' not in benchmarks_daten:
            print(f"Fehler: Ungültiges Dateiformat - 'Benchmarks' Feld fehlt in {dateiname}")
            return False
        
        # Ausgabedatei öffnen
        with open('benchmarks.txt', 'w', encoding='utf-8') as ausgabe:
            # Tabellenkopf schreiben
            ausgabe.write(f"{'workbenchId':<15} {'benchmarkTitle':<50} {'benchmarkVersion':<15} "
                         f"{'assessmentStatus':<15} {'availableFormats':<30} {'profiles':<50}\n")
            ausgabe.write('-' * 175 + '\n')
            
            # Durch alle Benchmarks iterieren und Daten extrahieren
            for benchmark in benchmarks_daten['Benchmarks']:
                # Extrahieren der benötigten Felder
                workbench_id = benchmark.get('workbenchId', 'N/A')
                title = benchmark.get('benchmarkTitle', 'N/A')
                version = benchmark.get('benchmarkVersion', 'N/A')
                status = benchmark.get('assessmentStatus', 'N/A')
                if status == 'Manual':
                    continue
                
                # Formate als kommagetrennte Liste
                formats = ', '.join(benchmark.get('availableFormats', ['N/A']))
                
                # Profile-Titel extrahieren
                profile_titles = []
                for profile in benchmark.get('profiles', []):
                    if 'profileTitle' in profile:
                        profile_titles.append(profile['profileTitle'])
                
                # Wenn keine Profile vorhanden sind
                if not profile_titles:
                    profile_titles = ['N/A']
                
                # Profile als kommagetrennte Liste
                profiles = ', '.join(profile_titles)
                
                # Zeile in Tabelle schreiben (mit Kürzung für bessere Lesbarkeit)
                ausgabe.write(f"{workbench_id:<15} {title[:47]+'...' if len(title)>50 else title:<50} "
                             f"{version:<15} {status:<15} {formats[:27]+'...' if len(formats)>30 else formats:<30} "
                             f"{profiles[:47]+'...' if len(profiles)>50 else profiles:<50}\n")
        
        print("Analyse abgeschlossen. Ergebnisse wurden in 'benchmarks.txt' gespeichert.")
        return True
        
    except FileNotFoundError:
        print(f"Fehler: Die Datei '{dateiname}' wurde nicht gefunden.")
        return False
    except json.JSONDecodeError:
        print(f"Fehler: Die Datei '{dateiname}' enthält kein gültiges JSON-Format.")
        return False
    except Exception as e:
        print(f"Unerwarteter Fehler bei der Analyse: {e}")
        return False

def main():
    # Benchmark-Liste abrufen und speichern
    try:
        analyse_benchmarks('available_benchmarks.json')        
    except Exception as e:
        print(e)
        
if __name__ == "__main__":
    main()
    