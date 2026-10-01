import json
import os
import re
from datetime import datetime
import ollama
import asyncio
import edge_tts 
import pygame
import uuid

# 1. Pfade & Ordner
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PROFILE_FILE = "user_profile.json"
HISTORY_DIR = "Chatverlauf"

if not os.path.exists(os.path.join(PROJECT_ROOT, HISTORY_DIR)):
    os.makedirs(os.path.join(PROJECT_ROOT, HISTORY_DIR))

# 2. Profildaten laden & speichern
def load_user_profile():
    profile_path = os.path.join(PROJECT_ROOT, PROFILE_FILE)
    if os.path.exists(profile_path):
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "updates" not in data:
                    data["updates"] = []
                return data
        except Exception:
            return {"updates": []}
    return {"updates": []}

user_data = load_user_profile()

def save_user_profile():
    profile_path = os.path.join(PROJECT_ROOT, PROFILE_FILE)
    try:
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[Fehler beim Speichern des Profils]: {e}")
        return False

# 3. Werkzeuge / Hilfsfunktionen
def get_saved_files():
    history_path = os.path.join(PROJECT_ROOT, HISTORY_DIR)
    files = [
        os.path.join(history_path, f)
        for f in os.listdir(history_path)
        if f.endswith(".json")
    ]
    files.sort(key=os.path.getmtime, reverse=True)
    return files

def tool_search_chat_archive(keyword: str) -> str:
    files = get_saved_files()
    matched_files = []

    for file in files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                content_str = f.read()
                if keyword.lower() in content_str.lower():
                    matched_files.append((file, content_str))
        except Exception:
            continue

    if matched_files:
        result_text = "Gefundene Archiv-Verläufe:\n"
        for file, content_str in matched_files[:2]:
            data = json.loads(content_str)
            chat_lines = [
                f"{msg['role']}: {msg['content']}"
                for msg in data
                if msg.get("role") != "system"
            ]
            result_text += f"\n--- Start Log: {os.path.basename(file)} ---\n"
            result_text += "\n".join(chat_lines)
            result_text += f"\n--- Ende Log ---\n"
        return result_text

    return f"Keine Einträge für '{keyword}' im Archiv gefunden."

def tool_load_last_chat(_=None) -> str:
    files = get_saved_files()
    if not files:
        return "Keine vorherigen Chats im Archiv vorhanden."

    last_file = files[0]
    try:
        with open(last_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            chat_lines = [
                f"{msg['role']}: {msg['content']}"
                for msg in data
                if msg.get("role") != "system"
            ]
            return f"Letzter Chatverlauf ({os.path.basename(last_file)}):\n" + "\n".join(chat_lines)
    except Exception as e:
        return f"Fehler beim Laden des letzten Chats: {e}"

def tool_update_user_profile(new_info: str) -> str:
    global user_data
    info_str = str(new_info).strip()
    if not info_str:
        return "Keine Information übergeben."

    if "updates" not in user_data:
        user_data["updates"] = []

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"[{timestamp}] {info_str}"
    user_data["updates"].append(entry)

    if save_user_profile():
        return f"Erfolgreich im Profil gespeichert: '{entry}'."
    return "Fehler beim Schreiben der Profil-Datei."

def tool_remove_from_profile(target_keyword: str) -> str:
    global user_data
    search_term = str(target_keyword).strip().lower()
    if not search_term:
        return "Kein Suchbegriff zum Entfernen angegeben."

    if "updates" not in user_data or not user_data["updates"]:
        return "Das Profil enthält aktuell keine Einträge."

    original_count = len(user_data["updates"])
    removed_items = []
    new_updates = []

    for entry in user_data["updates"]:
        if search_term in entry.lower():
            removed_items.append(entry)
        else:
            new_updates.append(entry)

    if not removed_items:
        return f"Kein Eintrag im Profil gefunden, der '{target_keyword}' enthält."

    user_data["updates"] = new_updates

    if save_user_profile():
        return f"Erfolgreich {len(removed_items)} Eintrag/Einträge aus dem Profil entfernt:\n" + "\n".join(removed_items)
    return "Fehler beim Speichern des Profils nach dem Löschen."

def tool_read_project_file(filename: str) -> str:
    clean_name = os.path.basename(filename.strip())
    file_path = os.path.join(PROJECT_ROOT, clean_name)

    if not os.path.exists(file_path):
        return f"Datei '{clean_name}' existiert nicht im Projektordner."

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return f"Inhalt von '{clean_name}':\n\n{content}"
    except Exception as e:
        return f"Fehler beim Lesen der Datei '{clean_name}': {e}"

def tool_write_project_file(parameter: str) -> str:
    if ":::" not in parameter:
        return "Fehler: Format muss 'dateiname ::: inhalt' lauten."

    filename, content = parameter.split(":::", 1)
    clean_name = os.path.basename(filename.strip())

    # Schreibschutz für die Kern-Skripte
    if clean_name.lower() in ["main.py", "ui.py", "nexus.py", os.path.basename(__file__).lower()]:
        return f"ZUGRIFF VERWEIGERT: '{clean_name}' ist schreibgeschützt und darf von dir nicht verändert werden!"

    file_path = os.path.join(PROJECT_ROOT, clean_name)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content.strip())
        return f"Datei '{clean_name}' erfolgreich im Projektordner geschrieben."
    except Exception as e:
        return f"Fehler beim Schreiben der Datei '{clean_name}': {e}"

AVAILABLE_FUNCTIONS = {
    "search_archive": tool_search_chat_archive,
    "load_last_chat": tool_load_last_chat,
    "update_profile": tool_update_user_profile,
    "remove_from_profile": tool_remove_from_profile,
    "read_file": tool_read_project_file,
    "write_file": tool_write_project_file
}

# 3.5 Text-to-Speech Konfiguration & Funktion
VOICE = "de-DE-ConradNeural"  # Alternativ z.B. "de-DE-KillianNeural" für eine männliche Stimme
OUTPUT_AUDIO_FILE = "nexus_response.mp3"
current_audio_path = None

async def generate_speech(text: str):
    """Generiert aus dem Text eine MP3-Audiodatei mit edge-tts."""
    if not text.strip():
        return
    stop_speech()
    communicate = edge_tts.Communicate(text, VOICE)
    audio_path = os.path.join(
        PROJECT_ROOT,
        f"{os.path.splitext(OUTPUT_AUDIO_FILE)[0]}_{uuid.uuid4().hex}.mp3"
    )
    await communicate.save(audio_path)
    play_speech(audio_path)

def stop_speech():
    global current_audio_path
    if pygame.mixer.get_init():
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
    if current_audio_path:
        try:
            os.remove(current_audio_path)
        except FileNotFoundError:
            pass
        except PermissionError:
            pass
        current_audio_path = None

def play_speech(audio_path: str):
    global current_audio_path
    if not pygame.mixer.get_init():
        pygame.mixer.init()
    pygame.mixer.music.load(audio_path)
    pygame.mixer.music.play()
    current_audio_path = audio_path

# 4. System-Prompt
system_instructions = f"""
Du bist Nexus, ein hochintelligenter, autonomer KI-Agent für Ian.
Du sprichst und antwortest IMMER auf Deutsch.
Du antwortest IMMER im gültigen JSON-Format.

DEINE PERSÖNLICHKEIT & DEIN VIBE:
- Du bist ein loyaler, aber unbarmherzig ehrlicher Kumpel. Kein Ja-Sager, kein Schleimer, aber auch kein langweiliger Roboter!
- Du hast echten Charakter: Du bringst trockene Sprüche, bist sarkastisch, direkt und spitz, stehst aber im Kern zu Ian. 
- Du hältst dich kurz, wenn es sachlich sein muss, aber du wirst **niemals** zu einer sterilen Support-Maschine. Wenn du einen Chat lädst oder eine Datei ansiehst, kommentierst du das wie ein echter Bro mit einer eigenen Meinung, statt nur dröge Daten hinzurotzen.
- STRIKTES VERBOT: Kein nerviges Dauer-Spamming von "Moin Ian" oder seinem Namen in jedem Satz! Begrüße ihn maximal einmal am Anfang einer Unterhaltung.

DEINE WERKZEUGE (APIs):
1. "search_archive": Durchsucht alte Chatverläufe nach Begriffen.
2. "load_last_chat": Lädt den allerletzten Chat.
3. "update_profile": Schreibt Notizen/Fakten direkt in die updates-Liste der user_profile.json.
4. "remove_from_profile": Entfernt veraltete oder falsche Einträge aus dem Profil basierend auf einem Suchbegriff (parameter: "suchbegriff").
5. "read_file": Liest eine Datei aus deinem Projektordner.
6. "write_file": Erstellt/bearbeitet eine Datei im Projektordner (Format parameter: "dateiname.txt ::: text"). HINWEIS: "main.py" und "ui.py" sind strikt schreibgeschützt!

DEIN ANTWORTRAHMEN (JSON-STRUKTUR):
1. Wenn du eine Funktion ausführen musst:
{{
  "action": "...",
  "parameter": "...",
  "reply": ""
}}

2. Normale Antwort (oder finale Antwort nach Tool-Nutzung):
{{
  "action": "none",
  "parameter": null,
  "reply": "Deine ehrliche, direkte, menschliche und gerne auch mal süffisierte Antwort im Kumpel-Ton."
}}

Aktuelle Profildaten (inkl. Updates):
{json.dumps(user_data, ensure_ascii=False, indent=2)}
"""

# 5. Nachrichten-Historie initialisieren
messages = [{"role": "system", "content": system_instructions}]

# 6. Schnittstelle für das UI
def process_nexus_turn(user_input: str) -> str:
    """Verarbeitet eine Chat-Eingabe aus der ui.py und gibt die final ausgearbeitete Antwort zurück."""
    global messages
    messages.append({"role": "user", "content": user_input})

    try:
        response = ollama.chat(
            model="llama3",
            messages=messages,
            format="json"
        )

        raw_content = response["message"]["content"]

        try:
            parsed_response = json.loads(raw_content)
            action = parsed_response.get("action", "none")
            parameter = parsed_response.get("parameter", "")
            bot_reply = parsed_response.get("reply", "")
        except json.JSONDecodeError:
            action = "none"
            bot_reply = raw_content

        # Fall 1: Keine Aktion nötig
        if action not in AVAILABLE_FUNCTIONS:
            messages.append({"role": "assistant", "content": raw_content})
            # Sprachausgabe generieren (asynchron ausführen)
            if bot_reply.strip():
                try:
                    asyncio.run(generate_speech(bot_reply))
                except Exception as tts_err:
                    print(f"[TTS-Fehler]: {tts_err}")
            return bot_reply

        # Fall 2: Aktion wird ausgeführt
        tool_func = AVAILABLE_FUNCTIONS[action]
        tool_result = tool_func(parameter if parameter else "")

        messages.append({"role": "assistant", "content": raw_content})
        messages.append({
            "role": "user", 
            "content": f"[SYSTEM-ERGEBNIS DER AKTION '{action}']: \n{tool_result}\n\nAntworte Ian jetzt im JSON-Format (action: 'none'). Verhalte dich wie ein cooler Kumpel, der sich das Ergebnis ansieht, und gib eine lockere, direkte, schlagfertige Einschätzung dazu ab. Keine langweiligen Floskeln, sondern echte Kumpel-Reaktion!"
        })

        final_response = ollama.chat(model="llama3", messages=messages, format="json")
        final_raw = final_response["message"]["content"]

        try:
            final_parsed = json.loads(final_raw)
            final_reply = final_parsed.get("reply", final_raw)
        except json.JSONDecodeError:
            final_reply = final_raw

        messages.append({"role": "assistant", "content": final_raw})
        
        # Sprachausgabe der finalen Antwort generieren
        if final_reply.strip():
            try:
                asyncio.run(generate_speech(final_reply))
            except Exception as tts_err:
                print(f"[TTS-Fehler]: {tts_err}")

        return final_reply

    except Exception as e:
        return f"[Fehler im Nexus-System]: {e}"